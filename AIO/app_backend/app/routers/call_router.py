"""
REST endpoint providing WebRTC ICE server configuration. The actual call
signaling (offer/answer/ICE candidates/hangup/reject/busy/timeout) happens
over the WebSocket in realtime_ws_router.py — this is just the one-time
config a client fetches before starting/answering a call.
"""

from fastapi import APIRouter, Depends

from ..config import settings
from ..dependencies import get_current_user_id
from ..schemas.chat_schemas import IceServerConfig, IceServersResponse

router = APIRouter()


@router.get("/ice-servers", response_model=IceServersResponse)
async def get_ice_servers(uid: str = Depends(get_current_user_id)):
    """
    Returns the STUN server (always present — a public server, no
    credentials needed) plus a TURN server IF one has been configured via
    settings.turn_server_url/turn_username/turn_credential.

    Without a real TURN server configured, calls will still work when both
    peers have straightforward NAT (most home Wi-Fi), but will fail for a
    meaningful fraction of real users — particularly on mobile data behind
    carrier-grade NAT, or when either peer is behind symmetric NAT. A TURN
    server (self-hosted coturn, or a managed service like Twilio Network
    Traversal / Xirsys / Cloudflare Calls) needs to be provisioned and its
    credentials set in settings before this is reliable for all users.
    """
    ice_servers = [IceServerConfig(urls=settings.stun_server_url)]

    if settings.turn_server_url:
        ice_servers.append(
            IceServerConfig(
                urls=settings.turn_server_url,
                username=settings.turn_username or None,
                credential=settings.turn_credential or None,
            )
        )

    return IceServersResponse(ice_servers=ice_servers)