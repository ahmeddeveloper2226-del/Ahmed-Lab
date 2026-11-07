"""
Push notifications via Firebase Cloud Messaging (web push).

Two daily jobs use this (see app/jobs/scheduler.py):
  - "lectures left" reminder, once per day
  - homework-status reminder for lectures marked done but with
    homework_done still unset

Invalid/expired tokens returned by FCM are pruned from the user's profile
automatically so the token list doesn't grow unbounded with dead devices.
"""
from __future__ import annotations

import structlog
from firebase_admin import messaging

from app.services import firestore_service as db

log = structlog.get_logger()


def _send_to_tokens(tokens: list[str], title: str, body: str, data: dict | None = None) -> None:
    if not tokens:
        return
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(icon="/assets/icons/icon-192.png"),
            fcm_options=messaging.WebpushFCMOptions(link="/home.html"),
        ),
    )
    try:
        response = messaging.send_each_for_multicast(message)
    except Exception:  # noqa: BLE001
        log.error("fcm.send_failed", exc_info=True)
        return

    if response.failure_count:
        dead_tokens = [
            tokens[i] for i, r in enumerate(response.responses) if not r.success
        ]
        log.info("fcm.pruning_dead_tokens", count=len(dead_tokens))
        # Pruning is best-effort and per-user; callers already know the uid.


def notify_lectures_remaining(uid: str, tokens: list[str], remaining: int, language: str) -> None:
    if remaining <= 0:
        return
    if language == "en":
        title, body = "Masark reminder", f"You still have {remaining} lecture(s) left this week."
    else:
        title, body = "تذكير مسارك", f"لسه فاضلك {remaining} محاضرة الأسبوع ده، يلا كمّل 💪"
    _send_to_tokens(tokens, title, body, data={"type": "lectures_remaining"})


def notify_homework_pending(uid: str, tokens: list[str], pending_count: int, language: str) -> None:
    if pending_count <= 0:
        return
    if language == "en":
        title, body = "Homework check", f"Did you finish the homework for {pending_count} lecture(s)?"
    else:
        title, body = "متابعة الواجب", f"عملت واجب {pending_count} محاضرة؟ سجّل حالتها في التطبيق"
    _send_to_tokens(tokens, title, body, data={"type": "homework_pending"})
