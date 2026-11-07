"""
REST endpoints for chat: paginated history, voice message upload, and
authenticated media serving. Real-time delivery (new messages, typing,
presence, read/delivered receipts) happens over the WebSocket in
realtime_ws_router.py instead — this router is for the parts that are
naturally request/response (loading history when the screen opens,
uploading a recorded voice note, fetching an audio file).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..models.chat_message import ChatMessage, MessageStatus, MessageType
from ..schemas.chat_schemas import ChatHistoryResponse, ChatMessageResponse
from ..services.chat_service import (
    ALLOWED_AUDIO_EXTENSIONS,
    audio_storage_path,
    ensure_media_root,
    verify_participant,
)

router = APIRouter()
logger = logging.getLogger("wasla.chat")

_DEFAULT_PAGE_SIZE = 50


def _to_message_response(msg: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=msg.id,
        order_id=msg.order_id,
        sender_id=msg.sender_id,
        receiver_id=msg.receiver_id,
        message_type=msg.message_type.value,
        status=msg.status.value,
        content=msg.content,
        audio_url=f"/chat/media/{msg.id}" if msg.message_type == MessageType.voice else None,
        audio_duration_seconds=msg.audio_duration_seconds,
        created_at=msg.created_at,
    )


@router.get("/{order_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    order_id: str,
    before: str | None = Query(None, description="Message id cursor — returns messages older than this one"),
    limit: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Paginated chat history — load the newest page first, pass its
    next_cursor as `before` to load the page before it (typical
    "scroll up to load older messages" chat convention).
    """
    access = await verify_participant(db, order_id, uid)
    if access is None:
        # Same convention as the rest of the codebase: don't confirm the
        # order even exists to someone who isn't a participant in it.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    query = select(ChatMessage).where(ChatMessage.order_id == order_id)

    if before:
        cursor_result = await db.execute(select(ChatMessage).where(ChatMessage.id == before))
        cursor_msg = cursor_result.scalar_one_or_none()
        if cursor_msg is not None:
            query = query.where(ChatMessage.created_at < cursor_msg.created_at)

    query = query.order_by(ChatMessage.created_at.desc()).limit(limit)

    try:
        result = await db.execute(query)
        messages = list(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.error("Failed to load chat history for order=%s: %s", order_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load chat history right now. Please try again.",
        )

    # Re-ascend to chronological order for display.
    messages.reverse()

    next_cursor = messages[0].id if len(messages) == limit else None

    return ChatHistoryResponse(
        messages=[_to_message_response(m) for m in messages],
        next_cursor=next_cursor,
    )


@router.post("/{order_id}/voice-message", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def upload_voice_message(
    order_id: str,
    audio: UploadFile = File(...),
    duration_seconds: float = Form(..., gt=0),
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Uploads a recorded voice note. The audio itself is stored on local disk
    (see chat_service.py); this endpoint persists the ChatMessage row and
    returns it, with audio_url pointing at the authenticated
    GET /chat/media/{id} endpoint — never a raw file path.

    Delivery to the other participant if they're currently connected
    happens over the realtime WebSocket (realtime_ws_router.py) — the
    client should send a lightweight "voice_message" notice there right
    after this upload succeeds, referencing this message's id.
    """
    access = await verify_participant(db, order_id, uid)
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    order, other_uid = access

    extension = ""
    if audio.filename and "." in audio.filename:
        extension = "." + audio.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
        )

    message_id = str(uuid.uuid4())
    ensure_media_root()
    dest_path = audio_storage_path(message_id, extension)

    try:
        contents = await audio.read()
        with open(dest_path, "wb") as f:
            f.write(contents)
    except OSError as exc:
        logger.error("Failed to save voice message audio for order=%s: %s", order_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save the voice message right now. Please try again.",
        )

    try:
        message = ChatMessage(
            id=message_id,
            order_id=order_id,
            sender_id=uid,
            receiver_id=other_uid,
            message_type=MessageType.voice,
            status=MessageStatus.sent,
            audio_path=str(dest_path),
            audio_duration_seconds=duration_seconds,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
    except SQLAlchemyError as exc:
        await db.rollback()
        # Clean up the orphaned file — the DB row is the source of truth.
        try:
            dest_path.unlink(missing_ok=True)
        except OSError:
            pass
        logger.error("Failed to persist voice message for order=%s: %s", order_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save the voice message right now. Please try again.",
        )

    return _to_message_response(message)


@router.get("/media/{message_id}")
async def get_chat_media(
    message_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Serves a voice message's audio file — re-verifies the requester is a
    participant of the message's order on EVERY fetch, not just at upload
    time. This is what makes local-disk storage safe here: nothing is
    reachable without going through this check first.
    """
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one_or_none()

    if message is None or message.audio_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice message not found.")

    access = await verify_participant(db, message.order_id, uid)
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice message not found.")

    return FileResponse(message.audio_path, media_type="audio/*")