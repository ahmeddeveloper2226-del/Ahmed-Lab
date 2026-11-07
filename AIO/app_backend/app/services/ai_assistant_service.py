"""
AI shopping assistant — powers POST /ai/chat (ai_assistant_router.py).

Rebuilt around a fixed, cheap pipeline instead of an agentic tool-use loop:

    user message
        -> deterministic keyword search (Postgres, NO LLM call at all)
        -> top ~10 candidate products
        -> ONE Claude call, given the candidates, must reply as strict JSON
        -> that JSON is applied to the cart deterministically (no LLM)

Why this is cheaper than the previous version: the old tool-use loop could
take several Claude round trips per user message (search, then decide,
then maybe search again, then add_to_cart, ...), and every round trip
re-sends the ENTIRE growing conversation history plus all tool
definitions — that's where a tool-loop's token cost actually comes from,
not the "thinking" itself. This version calls Claude exactly once per user
message, with a short, fixed-shape prompt: the recent conversation + up to
10 already-found candidates. No tool schemas sent at all, no multi-turn
back-and-forth billed per message.

Trade-off worth knowing: the search step is now a plain keyword/substring
match (see _search_products), not something that understands synonyms or
typos the way asking Claude to search would. If customers routinely type
things the keyword search can't find (heavy misspellings, brand
names vs generic terms, etc.), that shows up as "the assistant says it
can't find X" more often than the old version — worth watching in
practice and worth adding fuzzy matching (Postgres pg_trgm) if it becomes
a real problem, not a Claude call.
"""
import json
import logging
import re

from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import anthropic

from ..config import settings
from ..models.product import Product
from ..models.shop import Shop
from ..schemas.ai_assistant_schemas import AiCartAddition, AiChatMessage, AiChoiceOption
from ..services.cart_service import get_raw_cart, save_raw_cart

logger = logging.getLogger("wasla.ai_assistant")

_MAX_HISTORY_MESSAGES = 12  # only the most recent turns get sent — old context is dropped, not summarized
_MAX_SEARCH_RESULTS = 10

# Common filler words stripped before searching — mostly polite/quantity
# phrasing that never appears in a product name, so leaving them in would
# just make every candidate score lower without helping relevance at all.
_STOPWORDS = {
    "من", "في", "على", "و", "أو", "عايز", "عاوز", "أريد", "أحتاج", "محتاج",
    "كام", "حبة", "حبات", "قطعة", "قطع", "كيلو", "كيلوجرام", "لو", "سمحت",
    "سمحتوا", "هل", "ممكن", "عندكم", "فيه", "لي", "ليا", "الرجاء", "من فضلك",
    "واحد", "واحدة", "اثنين", "اتنين", "شكرا",
}

_QUESTION_SYSTEM_PROMPT = """أنت مساعد تسوق داخل تطبيق AIO، سوق إلكتروني متعدد التصنيفات (بقالة، ملابس، مطاعم، إلكترونيات، صيدليات) وعدة متاجر داخل كل تصنيف.
أجب عن سؤال العميل بإيجاز بالعربية. إن أُرفقت لك منتجات مطابقة من كتالوج المتجر استخدمها في إجابتك، وإلا أجب من معلوماتك العامة عن طريقة استخدام التطبيق."""

_ORDER_SYSTEM_PROMPT = """أنت مساعد تسوق داخل تطبيق AIO. سيصلك طلب العميل، وقائمة بأقرب المنتجات المطابقة من الكتالوج الفعلي (تم جلبها ببحث عادي، ليس منك).

مهمتك: حدد أي هذه المنتجات (إن وجد) يقصده العميل تحديدًا بلا لبس، وأرجع ردك **كـ JSON فقط وبدون أي نص خارجه**، بهذا الشكل بالضبط:

{"reply": "رسالة قصيرة للعميل بالعربية", "cart_items": [{"product_id": "...", "quantity": N}], "choices": null}

قواعد:
- إن كان أحد المنتجات المرفقة يطابق طلب العميل بوضوح تام (بلا اختيار بين متاجر أو مقاسات أو أوزان مختلفة)، ضعه في cart_items وقيمة choices تكون null.
- إن كانت هناك عدة خيارات ممكنة تحتاج قرار العميل (نفس المنتج من أكثر من متجر، مقاسات مختلفة، أوزان مختلفة) ولم يحدد العميل ذلك صراحة في رسالته، اترك cart_items فارغة [] وضع بدلاً منها:
  "choices": {"question": "سؤال قصير للعميل", "options": [{"option_id": "product_id هنا", "label": "وصف قصير", "detail": "تفاصيل إضافية أو السعر"}]}
- إن لم يكن أي من المنتجات المرفقة مطابقًا لما طلبه العميل، اترك cart_items فارغة وchoices تساوي null، واذكر في reply أنك لم تجد المنتج.
- لا تخترع منتجات أو product_id غير موجود في القائمة المرفقة أبدًا.
- أرجع JSON صالح فقط — بدون Markdown، بدون علامات ```، بدون أي شرح خارج كائن الـ JSON."""


def _extract_search_terms(text: str) -> list[str]:
    words = re.findall(r"[\w\u0600-\u06FF]+", text)
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


async def _search_products(db: AsyncSession, message: str, category_id: str | None = None) -> list[dict]:
    """
    Plain deterministic keyword search — no LLM involved. Scores each
    candidate by how many of the message's significant words appear in
    its name, so a message mentioning several items still surfaces
    reasonable matches for each of them in one combined top-10, rather
    than needing a separate search call per item.
    """
    terms = _extract_search_terms(message)
    if not terms:
        return []

    try:
        conditions = [Product.name.ilike(f"%{term}%") for term in terms]
        stmt = select(Product, Shop).join(Shop, Product.shop_id == Shop.id).where(
            *([Shop.category_id == category_id] if category_id else []),
        )
        # OR across all term conditions
        stmt = stmt.where(or_(*conditions)).limit(60)  # broad candidate pool, scored+trimmed below

        result = await db.execute(stmt)
        rows = result.all()
    except SQLAlchemyError as e:
        logger.error("AI product search failed: %s", e)
        return []

    scored = []
    for product, shop in rows:
        name_lower = product.name.lower()
        score = sum(1 for term in terms if term.lower() in name_lower)
        scored.append((score, product, shop))

    scored.sort(key=lambda t: t[0], reverse=True)

    return [
        {
            "product_id": product.id,
            "name": product.name,
            "price": float(product.price),
            "shop_id": shop.id,
            "shop_name": shop.name,
            "stock_quantity": product.stock_quantity,
        }
        for _, product, shop in scored[:_MAX_SEARCH_RESULTS]
    ]


async def run_ai_chat(
    db: AsyncSession,
    uid: str,
    mode: str,
    history: list[AiChatMessage],
) -> tuple[str, list[AiChoiceOption] | None, list[AiCartAddition]]:
    if not settings.anthropic_api_key:
        raise RuntimeError("AI assistant is not configured (ANTHROPIC_API_KEY missing).")

    trimmed_history = history[-_MAX_HISTORY_MESSAGES:]
    latest_user_message = next((m.content for m in reversed(trimmed_history) if m.role == "user"), "")

    candidates = await _search_products(db, latest_user_message)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    if mode == "order":
        return await _run_order_turn(client, uid, trimmed_history, candidates)
    return await _run_question_turn(client, trimmed_history, candidates)


async def _run_question_turn(
    client: anthropic.AsyncAnthropic, history: list[AiChatMessage], candidates: list[dict]
) -> tuple[str, list[AiChoiceOption] | None, list[AiCartAddition]]:
    context_note = (
        f"\n\nمنتجات مطابقة من الكتالوج (إن كانت مفيدة لسؤال العميل):\n{json.dumps(candidates, ensure_ascii=False)}"
        if candidates
        else ""
    )
    messages = [{"role": m.role, "content": m.content} for m in history]
    if context_note:
        messages[-1] = {"role": "user", "content": messages[-1]["content"] + context_note}

    response = await client.messages.create(
        model=settings.ai_assistant_model,
        max_tokens=500,
        system=_QUESTION_SYSTEM_PROMPT,
        messages=messages,
    )
    reply_text = "".join(block.text for block in response.content if block.type == "text")
    return reply_text, None, []


async def _run_order_turn(
    client: anthropic.AsyncAnthropic, uid: str, history: list[AiChatMessage], candidates: list[dict]
) -> tuple[str, list[AiChoiceOption] | None, list[AiCartAddition]]:
    messages = [{"role": m.role, "content": m.content} for m in history]
    candidates_note = f"\n\nالمنتجات المطابقة المتاحة:\n{json.dumps(candidates, ensure_ascii=False)}"
    messages[-1] = {"role": "user", "content": messages[-1]["content"] + candidates_note}

    response = await client.messages.create(
        model=settings.ai_assistant_model,
        max_tokens=700,
        system=_ORDER_SYSTEM_PROMPT,
        messages=messages,
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()

    try:
        # Claude occasionally wraps JSON in a ```json fence despite being
        # told not to — stripping fences defensively is cheaper and more
        # reliable than a second call asking it to "just give me JSON".
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.error("AI order turn returned non-JSON for uid=%s: %r", uid, raw_text[:300])
        return "لم أفهم طلبك، هل يمكنك إعادة صياغته؟", None, []

    reply_text = parsed.get("reply", "")
    choices_data = parsed.get("choices")
    cart_items = parsed.get("cart_items") or []

    choices = None
    if choices_data:
        choices = [
            AiChoiceOption(option_id=o["option_id"], label=o["label"], detail=o.get("detail"))
            for o in choices_data.get("options", [])
        ]
        reply_text = choices_data.get("question", reply_text)

    cart_additions: list[AiCartAddition] = []
    # candidate_ids guards against a hallucinated product_id slipping
    # through despite the prompt's instruction not to invent one — this is
    # a deterministic backstop, not something we're trusting the model to
    # get right on its own.
    candidate_by_id = {c["product_id"]: c for c in candidates}
    for item in cart_items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        if product_id not in candidate_by_id:
            continue
        addition = await _apply_cart_addition(uid, candidate_by_id[product_id], quantity)
        if addition:
            cart_additions.append(addition)

    return reply_text, choices, cart_additions


async def _apply_cart_addition(uid: str, candidate: dict, quantity: int) -> AiCartAddition | None:
    if not isinstance(quantity, int) or quantity < 1:
        quantity = 1
    if quantity > candidate["stock_quantity"]:
        return None

    raw_cart = await get_raw_cart(uid)
    raw_cart[candidate["product_id"]] = quantity
    await save_raw_cart(uid, raw_cart)

    return AiCartAddition(
        product_id=candidate["product_id"],
        name=candidate["name"],
        shop_name=candidate["shop_name"],
        quantity=quantity,
        price=candidate["price"],
    )