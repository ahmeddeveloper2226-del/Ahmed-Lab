from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageResponse(BaseModel):
    id: str
    order_id: str
    sender_id: str | None
    receiver_id: str
    message_type: str
    status: str
    content: str | None
    # Authenticated URL, not a raw file path — see chat_router.py's
    # GET /chat/media/{message_id}, which re-checks participant access on
    # every fetch rather than trusting a static, guessable path.
    audio_url: str | None
    audio_duration_seconds: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    # Cursor for the next page — pass as `before` on the next request.
    # None means there are no older messages left.
    next_cursor: str | None


class VoiceMessageUploadResponse(BaseModel):
    message: ChatMessageResponse


class IceServerConfig(BaseModel):
    urls: str
    username: str | None = None
    credential: str | None = None


class IceServersResponse(BaseModel):
    ice_servers: list[IceServerConfig]