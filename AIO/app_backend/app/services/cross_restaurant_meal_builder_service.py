"""
Backs the SECOND Meal Builder mode: 'From all restaurants'.

The per-restaurant one (meal_builder_service.py) picks a meal TYPE and
builds it from a single restaurant's own menu — cheap, one small prompt.

This one is different on purpose: the customer describes what they want
in free text (e.g. "غدا صحي لشخصين بحد أقصى ٣٠٠ جنيه"), and Claude can
pull items from SEVERAL different restaurants to build the best possible
meal for that request — not limited to what any one restaurant offers.

That's a much bigger, more expensive prompt if done naively (every food
product from every restaurant in the app). So instead of sending
everything to Claude, the flow is:

  1. Use the search engine (Elasticsearch, already indexes every food
     product — see search_service.py) to find products matching the
     customer's own text, scoped to category_id == "food".
  2. Aggregate those hits by shop_id and take the TOP 10 restaurants by
     match count — this is a free/cheap keyword search, not an AI call.
  3. Load only THOSE 10 restaurants' actual in-stock menus from Postgres.
  4. Send that bounded candidate list (still real Postgres rows, still
     capped) to Claude, which picks a coherent meal that can mix items
     from more than one of those 10 restaurants.

So the AI call only ever sees ~10 restaurants' worth of candidates
instead of the whole catalog, keeping the billing cost bounded and
predictable while still searching "the whole app" for what fits.

Same anti-hallucination guardrail as the single-restaurant version and
ai_assistant_service.py: Claude can only pick product_ids that are
actually in the candidate list built from real rows; anything else is
silently dropped.
"""
import json
import logging
import re
from collections import Counter

import anthropic
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.product import Product
from ..models.shop import Shop
from ..schemas.meal_builder_schemas import CrossRestaurantMealBuilderItem
from ..schemas.product_schemas import ProductResponse
from ..services.search_service import search_products

logger = logging.getLogger("wasla.cross_restaurant_meal_builder")

# How many restaurants the search step surfaces for Claude to choose from.
_TOP_RESTAURANTS = 10
# How many products, per restaurant, get sent to Claude — keeps the
# prompt bounded even for a restaurant with a huge menu.
_MAX_PRODUCTS_PER_SHOP = 12

_SYSTEM_PROMPT = """أنت خبير قوائم طعام داخل تطبيق توصيل AIO. سيصلك طلب وجبة بصيغة حرة من العميل (زي "غدا صحي لشخصين بحد أقصى ٣٠٠ جنيه")، عدد الأفراد، وقائمة أصناف فعلية متاحة الآن من عدة مطاعم مختلفة (كل صنف معه product_id، shop_id، اسم المطعم، اسم الصنف، وصفه، وسعره).

مهمتك: اختر مجموعة أصناف من هذه القائمة فقط (ولا شيء غيرها) تُكوّن وجبة متكاملة تلبي طلب العميل قدر الإمكان — يمكنك اختيار أصناف من أكثر من مطعم واحد إذا كان هذا يعطي نتيجة أفضل (مثلاً: طبق رئيسي من مطعم ومشروب أو حلو من مطعم آخر)، لكن لا داعي لتفريق الأصناف على مطاعم متعددة إلا إذا كان ذلك فعلاً يخدم الطلب.

أرجع ردك **كـ JSON فقط بدون أي نص خارجه**:

{"meal_title": "عنوان قصير وجذاب للوجبة بالعربية", "items": [{"product_id": "...", "quantity": N, "reason": "سبب مختصر جدًا لاختيار هذا الصنف (أقل من 8 كلمات)"}]}

قواعد:
- استخدم فقط product_id موجود فعليًا في القائمة المرفقة، ولا تخترع أصنافًا أو أسعارًا أو مطاعم أبدًا.
- اختر بين 2 و8 أصناف مختلفة (لا تكرر نفس الصنف كصنفين منفصلين، استخدم quantity بدلاً من ذلك).
- إن لم تجد في القائمة أي أصناف مناسبة فعليًا لطلب العميل، أرجع items كمصفوفة فارغة [].
- أرجع JSON صالح فقط — بدون Markdown، بدون علامات ```."""


async def _find_top_restaurants(query: str) -> list[str]:
    """Cheap keyword search step — no AI call. Returns up to _TOP_RESTAURANTS
    shop_ids, ranked by how many of their products matched the query."""
    try:
        hits = await search_products(query=query, category_id="food", limit=50)
    except Exception as e:
        logger.error("Search failed for cross-restaurant meal builder query=%r: %s", query, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر البحث عن مطاعم مناسبة الآن، حاول مرة أخرى.")

    shop_ids_by_hits = Counter(hit["shop_id"] for hit in hits if hit.get("shop_id"))
    return [shop_id for shop_id, _ in shop_ids_by_hits.most_common(_TOP_RESTAURANTS)]


async def _load_menus_for_shops(db: AsyncSession, shop_ids: list[str]) -> tuple[dict[str, Shop], list[Product]]:
    if not shop_ids:
        return {}, []

    shops_result = await db.execute(select(Shop).where(Shop.id.in_(shop_ids)))
    shops_by_id = {s.id: s for s in shops_result.scalars().all()}

    products_result = await db.execute(
        select(Product).where(Product.shop_id.in_(shop_ids)).where(Product.stock_quantity > 0)
    )
    all_products = list(products_result.scalars().all())

    # Cap per shop so one huge menu can't crowd out the other restaurants
    # in the prompt.
    capped: list[Product] = []
    seen_per_shop: dict[str, int] = {}
    for p in all_products:
        count = seen_per_shop.get(p.shop_id, 0)
        if count >= _MAX_PRODUCTS_PER_SHOP:
            continue
        seen_per_shop[p.shop_id] = count + 1
        capped.append(p)

    return shops_by_id, capped


async def build_cross_restaurant_meal(
    db: AsyncSession, query: str, party_size: int
) -> tuple[str, list[CrossRestaurantMealBuilderItem], bool]:
    if not settings.anthropic_api_key:
        raise RuntimeError("Cross-restaurant Meal Builder is not configured (ANTHROPIC_API_KEY missing).")

    top_shop_ids = await _find_top_restaurants(query)
    if not top_shop_ids:
        # has_results=False: the search itself found nothing — different
        # message from "found restaurants but nothing fit", handled below.
        return "", [], False

    try:
        shops_by_id, products = await _load_menus_for_shops(db, top_shop_ids)
    except SQLAlchemyError as e:
        logger.error("Failed to load menus for cross-restaurant meal builder: %s", e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل قوائم المطاعم الآن، حاول مرة أخرى.")

    if not products:
        return "", [], False

    candidates = [
        {
            "product_id": p.id,
            "shop_id": p.shop_id,
            "shop_name": shops_by_id[p.shop_id].name if p.shop_id in shops_by_id else "",
            "name": p.name,
            "description": p.description or "",
            "price": float(p.price),
        }
        for p in products
    ]

    user_message = (
        f"طلب العميل: {query}\n"
        f"عدد الأفراد: {party_size}\n\n"
        f"قائمة الأصناف الفعلية المتاحة الآن من أفضل المطاعم المطابقة للطلب:\n"
        f"{json.dumps(candidates, ensure_ascii=False)}"
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model=settings.ai_assistant_model,
            max_tokens=1100,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        logger.error("Cross-restaurant Meal Builder Claude call failed for query=%r: %s", query, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر بناء الوجبة الآن، حاول مرة أخرى.")

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.error("Cross-restaurant Meal Builder returned non-JSON for query=%r: %r", query, raw_text[:300])
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "تعذر بناء وجبة مناسبة، جرّب وصفًا مختلفًا.")

    meal_title = parsed.get("meal_title") or query
    raw_items = parsed.get("items") or []

    candidate_by_id = {c["product_id"]: p for c, p in zip(candidates, products)}
    items: list[CrossRestaurantMealBuilderItem] = []
    for entry in raw_items[:8]:
        product_id = entry.get("product_id")
        product = candidate_by_id.get(product_id)
        if product is None:
            continue  # guards against a hallucinated id despite the prompt's instruction not to invent one
        shop = shops_by_id.get(product.shop_id)
        if shop is None:
            continue
        quantity = entry.get("quantity", 1)
        if not isinstance(quantity, int) or quantity < 1:
            quantity = 1
        quantity = min(quantity, product.stock_quantity, 10)
        reason = str(entry.get("reason", "")).strip()[:80]
        items.append(
            CrossRestaurantMealBuilderItem(
                product=ProductResponse.from_product(product),
                quantity=quantity,
                reason=reason,
                shop_id=shop.id,
                shop_name=shop.name,
            )
        )

    return meal_title, items, True
