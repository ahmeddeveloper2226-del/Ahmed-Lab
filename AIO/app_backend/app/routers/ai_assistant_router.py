import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..rate_limiter import limiter
from ..schemas.ai_assistant_schemas import AiChatRequest, AiChatResponse
from ..services.ai_assistant_service import run_ai_chat

logger = logging.getLogger("wasla.ai_assistant")

router = APIRouter()


@router.post("/chat", response_model=AiChatResponse)
@limiter.limit("20/minute")
async def ai_chat(
    request: Request,
    payload: AiChatRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        reply, choices, cart_additions = await run_ai_chat(db, uid, payload.mode, payload.messages)
    except RuntimeError as e:
        # Anthropic key not configured — a clear, specific error rather
        # than a generic 500, so this is obvious to fix on a fresh deploy.
        logger.error("AI assistant misconfigured: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="المساعد الذكي غير متاح حاليًا.",
        )
    except Exception as e:
        logger.error("AI chat failed for uid=%s: %s", uid, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر التواصل مع المساعد الذكي الآن. حاول مرة أخرى.",
        )

    return AiChatResponse(reply=reply, choices=choices, cart_additions=cart_additions)