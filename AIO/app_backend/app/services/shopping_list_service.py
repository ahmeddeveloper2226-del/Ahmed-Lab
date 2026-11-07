"""
Backs the two Grocery-exclusive features:

  1. Smart Shopping Lists — plain CRUD lists a user builds/reuses/shares.
  2. AI Recipe Shopping — user types a dish name + servings, Claude expands
     it into an ingredient list scaled to servings, each ingredient is then
     matched against the real product catalog with the same deterministic
     keyword search used by the AI shopping assistant (see
     ai_assistant_service.py) — Claude never invents a product or price,
     it only names ingredients; matching against real stock/prices is
     always done in Postgres.
"""
import json
import logging
import re
import secrets
import uuid

import anthropic
from fastapi import HTTPException, status
from sqlalchemy import select, or_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.product import Product
from ..models.shop import Shop
from ..models.shopping_list import ShoppingList, ShoppingListItem
from ..schemas.shopping_list_schemas import (
    AddListToCartResult,
    RecipeIngredientMatch,
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListUpdate,
)
from .cart_service import add_product_to_raw_cart, get_raw_cart, save_raw_cart

logger = logging.getLogger("wasla.shopping_lists")

_RECIPE_SYSTEM_PROMPT = """أنت مساعد طبخ داخل تطبيق تسوق بقالة اسمه AIO. سيصلك اسم طبق وعدد الأفراد (servings).
أرجع فقط JSON بدون أي نص خارجه، بهذا الشكل بالضبط:

{"ingredients": [{"name": "اسم المكوّن مفرد وواضح (مثال: أرز، بصل، لحم مفروم)", "quantity_label": "الكمية بصيغة نصية مقروءة بعد ضبطها على عدد الأفراد المطلوب (مثال: 500 جم, 2 كوب, 3 حبات)"}]}

قواعد:
- استخدم أسماء مكوّنات بسيطة ومفردة تشبه أسماء المنتجات في محل بقالة، وليس وصفًا طويلاً.
- اضبط كل الكميات فعليًا حسب عدد الأفراد المطلوب، لا تكتب الكمية للوصفة الأساسية فقط.
- لا تكرر نفس المكوّن مرتين.
- 6 إلى 15 مكوّن كحد أقصى.
- أرجع JSON صالح فقط — بدون Markdown، بدون علامات ```."""


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def create_list(db: AsyncSession, uid: str, payload: ShoppingListCreate) -> ShoppingList:
    shopping_list = ShoppingList(
        id=_new_id("slist"),
        user_id=uid,
        name=payload.name,
        occasion=payload.occasion,
        share_code=secrets.token_urlsafe(8),
    )
    shopping_list.items = [
        ShoppingListItem(
            id=_new_id("sitem"),
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            product_id=item.product_id,
        )
        for item in payload.items
    ]
    db.add(shopping_list)
    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create shopping list for uid=%s: %s", uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إنشاء القائمة الآن.")
    await db.refresh(shopping_list, attribute_names=["items"])
    return shopping_list


async def list_lists(db: AsyncSession, uid: str) -> list[dict]:
    stmt = (
        select(
            ShoppingList,
            func.count(ShoppingListItem.id).label("item_count"),
            func.count(ShoppingListItem.id).filter(ShoppingListItem.is_checked.is_(True)).label("checked_count"),
        )
        .outerjoin(ShoppingListItem, ShoppingListItem.shopping_list_id == ShoppingList.id)
        .where(ShoppingList.user_id == uid)
        .group_by(ShoppingList.id)
        .order_by(ShoppingList.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": sl.id,
            "name": sl.name,
            "occasion": sl.occasion,
            "item_count": item_count,
            "checked_count": checked_count,
            "updated_at": sl.updated_at,
        }
        for sl, item_count, checked_count in rows
    ]


async def _get_owned_list(db: AsyncSession, uid: str, list_id: str) -> ShoppingList:
    result = await db.execute(select(ShoppingList).where(ShoppingList.id == list_id))
    shopping_list = result.scalar_one_or_none()
    if shopping_list is None or shopping_list.user_id != uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "القائمة غير موجودة.")
    await db.refresh(shopping_list, attribute_names=["items"])
    return shopping_list


async def get_list(db: AsyncSession, uid: str, list_id: str) -> ShoppingList:
    return await _get_owned_list(db, uid, list_id)


async def update_list(db: AsyncSession, uid: str, list_id: str, payload: ShoppingListUpdate) -> ShoppingList:
    shopping_list = await _get_owned_list(db, uid, list_id)
    if payload.name is not None:
        shopping_list.name = payload.name
    if payload.occasion is not None:
        shopping_list.occasion = payload.occasion
    await db.commit()
    await db.refresh(shopping_list, attribute_names=["items"])
    return shopping_list


async def delete_list(db: AsyncSession, uid: str, list_id: str) -> None:
    shopping_list = await _get_owned_list(db, uid, list_id)
    await db.delete(shopping_list)
    await db.commit()


async def add_item(db: AsyncSession, uid: str, list_id: str, payload: ShoppingListItemCreate) -> ShoppingList:
    shopping_list = await _get_owned_list(db, uid, list_id)
    if len(shopping_list.items) >= 200:
        raise HTTPException(status.HTTP_409_CONFLICT, "القائمة وصلت للحد الأقصى من العناصر.")
    item = ShoppingListItem(
        id=_new_id("sitem"),
        shopping_list_id=list_id,
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        product_id=payload.product_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(shopping_list, attribute_names=["items"])
    return shopping_list


async def update_item(
    db: AsyncSession, uid: str, list_id: str, item_id: str, payload: ShoppingListItemUpdate
) -> ShoppingList:
    shopping_list = await _get_owned_list(db, uid, list_id)
    item = next((i for i in shopping_list.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "العنصر غير موجود.")
    if payload.name is not None:
        item.name = payload.name
    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.is_checked is not None:
        item.is_checked = payload.is_checked
    await db.commit()
    await db.refresh(shopping_list, attribute_names=["items"])
    return shopping_list


async def delete_item(db: AsyncSession, uid: str, list_id: str, item_id: str) -> ShoppingList:
    shopping_list = await _get_owned_list(db, uid, list_id)
    item = next((i for i in shopping_list.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "العنصر غير موجود.")
    await db.delete(item)
    await db.commit()
    await db.refresh(shopping_list, attribute_names=["items"])
    return shopping_list


async def duplicate_shared_list(db: AsyncSession, uid: str, share_code: str) -> ShoppingList:
    """Powers 'share with family and friends' — copies a list (by its
    share_code) into the requesting user's own account as a brand-new,
    independently-editable list, rather than granting shared write access
    to the original. Simpler and avoids two people's edits colliding."""
    result = await db.execute(select(ShoppingList).where(ShoppingList.share_code == share_code))
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "رابط المشاركة غير صالح.")
    await db.refresh(source, attribute_names=["items"])

    copy = ShoppingList(
        id=_new_id("slist"),
        user_id=uid,
        name=source.name,
        occasion=source.occasion,
        share_code=secrets.token_urlsafe(8),
    )
    copy.items = [
        ShoppingListItem(id=_new_id("sitem"), name=i.name, quantity=i.quantity, unit=i.unit, product_id=i.product_id)
        for i in source.items
    ]
    db.add(copy)
    await db.commit()
    await db.refresh(copy, attribute_names=["items"])
    return copy


# ---------------------------------------------------------------------------
# Add list to cart — reuses each item's pinned product_id if present,
# otherwise does a best-effort keyword match against the catalog (same
# search building block the AI assistant uses).
# ---------------------------------------------------------------------------

async def _keyword_match_product(db: AsyncSession, name: str) -> Product | None:
    terms = [w for w in re.findall(r"[\w\u0600-\u06FF]+", name) if len(w) > 1]
    if not terms:
        return None
    conditions = [Product.name.ilike(f"%{term}%") for term in terms]
    stmt = select(Product).where(or_(*conditions)).limit(20)
    result = await db.execute(stmt)
    products = result.scalars().all()
    if not products:
        return None
    name_lower = name.lower()
    products.sort(key=lambda p: sum(1 for t in terms if t.lower() in p.name.lower()), reverse=True)
    return products[0]


async def add_list_to_cart(db: AsyncSession, uid: str, list_id: str) -> AddListToCartResult:
    shopping_list = await _get_owned_list(db, uid, list_id)
    raw_cart = await get_raw_cart(uid)

    added, skipped = 0, []
    for item in shopping_list.items:
        product: Product | None = None
        if item.product_id:
            result = await db.execute(select(Product).where(Product.id == item.product_id))
            product = result.scalar_one_or_none()
        if product is None:
            product = await _keyword_match_product(db, item.name)
        if product is None or product.stock_quantity < 1:
            skipped.append(item.name)
            continue
        qty = max(1, int(item.quantity)) if item.unit in (None, "piece", "pack") else 1
        add_product_to_raw_cart(raw_cart, product, qty)
        added += 1

    await save_raw_cart(uid, raw_cart)
    return AddListToCartResult(added_count=added, skipped_count=len(skipped), skipped_names=skipped)


# ---------------------------------------------------------------------------
# AI Recipe Shopping
# ---------------------------------------------------------------------------

async def parse_recipe(db: AsyncSession, dish_name: str, servings: int) -> list[RecipeIngredientMatch]:
    if not settings.anthropic_api_key:
        raise RuntimeError("AI recipe shopping is not configured (ANTHROPIC_API_KEY missing).")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.ai_assistant_model,
        max_tokens=800,
        system=_RECIPE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"الطبق: {dish_name}\nعدد الأفراد: {servings}"}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()

    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
        ingredients = parsed.get("ingredients", [])
        if not ingredients:
            raise ValueError("empty ingredients list")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Recipe parse returned unusable JSON for dish=%r: %s | raw=%r", dish_name, e, raw_text[:300])
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "تعذر التعرف على مكونات هذا الطبق، جرّب اسمًا آخر.")

    matches: list[RecipeIngredientMatch] = []
    for ing in ingredients[:15]:
        ing_name = str(ing.get("name", "")).strip()
        quantity_label = str(ing.get("quantity_label", "")).strip()
        if not ing_name:
            continue
        product = await _keyword_match_product(db, ing_name)
        shop_name = None
        if product is not None:
            shop_result = await db.execute(select(Shop).where(Shop.id == product.shop_id))
            shop = shop_result.scalar_one_or_none()
            shop_name = shop.name if shop else None
        matches.append(
            RecipeIngredientMatch(
                ingredient_name=ing_name,
                quantity_label=quantity_label,
                product_id=product.id if product else None,
                product_name=product.name if product else None,
                shop_name=shop_name,
                price=float(product.price) if product else None,
                matched=product is not None,
            )
        )
    return matches


async def add_products_to_cart(db: AsyncSession, uid: str, product_ids: list[str]) -> AddListToCartResult:
    raw_cart = await get_raw_cart(uid)
    added, skipped = 0, []
    for product_id in product_ids:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None or product.stock_quantity < 1:
            skipped.append(product_id)
            continue
        add_product_to_raw_cart(raw_cart, product, 1)
        added += 1
    await save_raw_cart(uid, raw_cart)
    return AddListToCartResult(added_count=added, skipped_count=len(skipped), skipped_names=skipped)
