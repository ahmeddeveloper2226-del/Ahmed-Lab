"""
Backs 'Meal Builder' (Food-exclusive): the customer picks a meal TYPE
(healthy / family / gym / kids / high_protein / spicy) instead of
individual menu items, and Claude assembles a complete meal FROM THAT
RESTAURANT'S ACTUAL MENU to fit it.

Same guardrail pattern as ai_assistant_service.py and
shopping_list_service.py's recipe parser: Claude only ever picks from a
candidate list built from real Postgres rows, and any product_id it
returns that isn't in that candidate list is silently dropped rather
than trusted — it can choose WHICH real items make a good "gym meal",
but it can never invent a menu item, a price, or stock that isn't real.
"""
import json
import logging
import re

import anthropic
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.product import Product
from ..models.shop import Shop
from ..schemas.meal_builder_schemas import MEAL_TYPES, MealBuilderItem
from ..schemas.product_schemas import ProductResponse

logger = logging.getLogger("wasla.meal_builder")

_MEAL_TYPE_GUIDANCE = {
    "healthy": "أصناف خفيفة ومتوازنة: مشوي بدل المقلي، خضار وسلطات، تجنّب الأطباق الدسمة أو المقالي الثقيلة قدر الإمكان.",
    "family": "كمية كافية لعدد الأفراد المطلوب، مع تنويع بين أكثر من نوع طبق حتى يناسب أذواق مختلفة.",
    "gym": "أعلى محتوى بروتين ممكن مع كارب متوازن (أرز، بطاطا)، وتقليل المقالي الدسمة والصلصات الثقيلة والحلويات.",
    "kids": "أصناف بسيطة ومحببة للأطفال، غير حارة إطلاقًا، أحجام صغيرة مناسبة لطفل.",
    "high_protein": "التركيز الكامل على أعلى الأصناف بروتينًا في القائمة (لحوم، دجاج، أسماك، بيض)، بأقل قدر من الكارب الزائد.",
    "spicy": "أصناف تحتوي فعليًا على حرارة/بهارات، أو تتيح اختيار مستوى حرارة عالٍ إن وُجد ذلك ضمن خيارات الصنف.",
}

_SYSTEM_PROMPT = """أنت خبير قوائم طعام داخل تطبيق توصيل AIO. سيصلك نوع وجبة مطلوب، إرشادات عن طبيعة هذا النوع، عدد الأفراد، وقائمة أصناف القائمة الفعلية لهذا المطعم فقط (id، اسم، وصف، سعر).

مهمتك: اختر مجموعة أصناف من هذه القائمة فقط (ولا شيء غيرها) تُكوّن وجبة متكاملة ومناسبة لما طُلب، وأرجع ردك **كـ JSON فقط بدون أي نص خارجه**:

{"meal_title": "عنوان قصير وجذاب للوجبة بالعربية", "items": [{"product_id": "...", "quantity": N, "reason": "سبب مختصر جدًا لاختيار هذا الصنف (أقل من 8 كلمات)"}]}

قواعد:
- استخدم فقط product_id موجود فعليًا في القائمة المرفقة، ولا تخترع أصنافًا أو أسعارًا أبدًا.
- اختر بين 2 و6 أصناف مختلفة (لا تكرر نفس الصنف كصنفين منفصلين، استخدم quantity بدلاً من ذلك).
- إن لم تجد في القائمة أي صنف مناسب فعليًا لنوع الوجبة المطلوب، أرجع items كمصفوفة فارغة [].
- أرجع JSON صالح فقط — بدون Markdown، بدون علامات ```."""


async def _load_food_products(db: AsyncSession, shop_id: str) -> tuple[Shop | None, list[Product]]:
    shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = shop_result.scalar_one_or_none()
    if shop is None or shop.category_id != "food":
        return shop, []

    result = await db.execute(
        select(Product).where(Product.shop_id == shop_id).where(Product.stock_quantity > 0)
    )
    return shop, list(result.scalars().all())


async def build_meal(
    db: AsyncSession, shop_id: str, meal_type: str, party_size: int
) -> tuple[str, list[MealBuilderItem], bool]:
    if meal_type not in _MEAL_TYPE_GUIDANCE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "نوع وجبة غير معروف.")
    if not settings.anthropic_api_key:
        raise RuntimeError("Meal Builder is not configured (ANTHROPIC_API_KEY missing).")

    shop, products = await _load_food_products(db, shop_id)
    if shop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "المطعم غير موجود.")
    if shop.category_id != "food" or not products:
        # Empty on purpose: either this isn't a food shop (frontend
        # already hides the entry point for that case), or it is but has
        # no in-stock products at all — has_menu=False lets the caller
        # tell those two "empty" cases apart from "AI found nothing that
        # fit THIS meal type" below.
        return "", [], False

    candidates = [
        {
            "product_id": p.id,
            "name": p.name,
            "description": p.description or "",
            "price": float(p.price),
        }
        for p in products
    ][:60]  # keep the prompt bounded even for a very large menu

    meal_label = next((m.label_ar for m in MEAL_TYPES if m.id == meal_type), meal_type)
    guidance = _MEAL_TYPE_GUIDANCE[meal_type]

    user_message = (
        f"نوع الوجبة المطلوب: {meal_label}\n"
        f"إرشادات هذا النوع: {guidance}\n"
        f"عدد الأفراد: {party_size}\n\n"
        f"قائمة الأصناف الفعلية المتاحة في هذا المطعم:\n{json.dumps(candidates, ensure_ascii=False)}"
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model=settings.ai_assistant_model,
            max_tokens=900,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        logger.error("Meal Builder Claude call failed for shop=%s meal_type=%s: %s", shop_id, meal_type, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر بناء الوجبة الآن، حاول مرة أخرى.")

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.error("Meal Builder returned non-JSON for shop=%s meal_type=%s: %r", shop_id, meal_type, raw_text[:300])
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "تعذر بناء وجبة مناسبة، جرّب نوعًا آخر.")

    meal_title = parsed.get("meal_title") or meal_label
    raw_items = parsed.get("items") or []

    candidate_by_id = {c["product_id"]: p for c, p in zip(candidates, products)}
    items: list[MealBuilderItem] = []
    for entry in raw_items[:8]:
        product_id = entry.get("product_id")
        product = candidate_by_id.get(product_id)
        if product is None:
            continue  # guards against a hallucinated id despite the prompt's instruction not to invent one
        quantity = entry.get("quantity", 1)
        if not isinstance(quantity, int) or quantity < 1:
            quantity = 1
        quantity = min(quantity, product.stock_quantity, 10)
        reason = str(entry.get("reason", "")).strip()[:80]
        items.append(MealBuilderItem(product=ProductResponse.from_product(product), quantity=quantity, reason=reason))

    return meal_title, items, True
