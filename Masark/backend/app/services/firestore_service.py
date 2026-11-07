"""
Firestore data-access layer.

Collections:
  users/{uid}
  users/{uid}/subjects/{enrollmentId}
  users/{uid}/subjects/{enrollmentId}/lectures/{lectureId}
  users/{uid}/study_plans/{weekStartISO}
  users/{uid}/procrastination_chat/{messageId}
  users/{uid}/subject_chat/{subjectSlug}/messages/{messageId}
  users/{uid}/lecture_notes/{enrollmentId}__{lectureId}          <- notes + rules
  users/{uid}/lecture_explain/{enrollmentId}__{lectureId}        <- summary + status
  users/{uid}/lecture_explain/{enrollmentId}__{lectureId}/messages/{messageId}
  users/{uid}/notifications_log/{dateISO}
  platform_cache/{platform}/subjects/{subjectSlug}   <- shared scrape cache,
      re-used across students to avoid re-scraping the same public catalogue
      pages for every single student who picks the same teacher/pack.

Every method here is intentionally narrow and named for the use case that
calls it, rather than exposing a generic "get/set" — that keeps Firestore
security rules (firestore.rules) simple to reason about, since the shape of
every write is known up front.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Any

from google.cloud import firestore

from app.core.firebase import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------- #
def get_user(uid: str) -> dict | None:
    doc = get_db().collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def create_or_update_user(uid: str, data: dict) -> dict:
    ref = get_db().collection("users").document(uid)
    payload = {**data, "updated_at": _now()}
    if not ref.get().exists:
        payload["created_at"] = _now()
    ref.set(payload, merge=True)
    return ref.get().to_dict()


def add_fcm_token(uid: str, token: str) -> None:
    ref = get_db().collection("users").document(uid)
    ref.update({"fcm_tokens": firestore.ArrayUnion([token])})


# --------------------------------------------------------------------- #
# Subject enrollments
# --------------------------------------------------------------------- #
def create_enrollment(uid: str, enrollment: dict) -> str:
    ref = get_db().collection("users").document(uid).collection("subjects").document()
    ref.set({**enrollment, "created_at": _now(), "updated_at": _now()})
    return ref.id


def list_enrollments(uid: str) -> list[dict]:
    docs = get_db().collection("users").document(uid).collection("subjects").stream()
    out = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        out.append(item)
    return out


def get_enrollment(uid: str, enrollment_id: str) -> dict | None:
    ref = get_db().collection("users").document(uid).collection("subjects").document(enrollment_id)
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def update_enrollment(uid: str, enrollment_id: str, data: dict) -> None:
    ref = get_db().collection("users").document(uid).collection("subjects").document(enrollment_id)
    ref.update({**data, "updated_at": _now()})


def _delete_refs(refs: list) -> None:
    """Delete many documents in a few batched commits (400 per commit) instead of one
    network round-trip per document."""
    client = get_db()
    for i in range(0, len(refs), 400):
        batch = client.batch()
        for r in refs[i:i + 400]:
            batch.delete(r)
        batch.commit()


def delete_enrollment(uid: str, enrollment_id: str) -> None:
    """Remove a subject with all its lectures, notes and explain chats.

    Used to do ~4 sequential Firestore calls PER LECTURE (tens of seconds, with the
    subject itself deleted last). Now: a handful of reads, then batched deletes."""
    user = _user(uid)
    ref = user.collection("subjects").document(enrollment_id)
    refs: dict[str, Any] = {}

    def add(r) -> None:
        refs[r.path] = r

    for d in ref.collection("lectures").select([]).stream():
        add(d.reference)
        key = _study_key(enrollment_id, d.id)
        add(user.collection("lecture_notes").document(key))
        add(user.collection("lecture_explain").document(key))
    for d in user.collection("lecture_notes").where("enrollment_id", "==", enrollment_id).select([]).stream():
        add(d.reference)
    for d in user.collection("lecture_explain").where("enrollment_id", "==", enrollment_id).select([]).stream():
        for m in d.reference.collection("messages").select([]).stream():
            add(m.reference)
        add(d.reference)
    # Parent subject doc goes in the LAST batch so a half-finished delete never leaves a
    # visible subject with no lectures.
    others = [r for path, r in refs.items() if path != ref.path]
    _delete_refs(others + [ref])


# --------------------------------------------------------------------- #
# Lectures
# --------------------------------------------------------------------- #
def _firestore_safe(value: Any) -> Any:
    """Firestore can't store a plain `date` - only `datetime`. Scrapers return dates
    (e.g. Ednuva's created_at), so convert them to midnight-UTC datetimes."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return value


def bulk_upsert_lectures(uid: str, enrollment_id: str, lectures: list[dict]) -> None:
    batch = get_db().batch()
    coll = (
        get_db().collection("users").document(uid)
        .collection("subjects").document(enrollment_id)
        .collection("lectures")
    )
    for lec in lectures:
        doc_id = lec.pop("external_id_as_doc_id", None) or coll.document().id
        ref = coll.document(doc_id)
        row = {k: _firestore_safe(v) for k, v in lec.items()}
        batch.set(ref, {**row, "created_at": _now()}, merge=True)
    batch.commit()


def list_lectures(uid: str, enrollment_id: str) -> list[dict]:
    coll = (
        get_db().collection("users").document(uid)
        .collection("subjects").document(enrollment_id)
        .collection("lectures")
    )
    out = []
    for d in coll.order_by("order").stream():
        item = d.to_dict()
        item["id"] = d.id
        out.append(item)
    return out


def list_all_lectures_for_user(uid: str, enrollments: list[dict] | None = None) -> list[dict]:
    """Collection-group-free simple fan-out across the user's enrollments —
    fine at this scale (dozens of subjects/lectures per student, not
    millions), and keeps security rules simpler than a collection-group
    query would."""
    if enrollments is None:
        enrollments = list_enrollments(uid)
    if not enrollments:
        return []

    def one(enrollment: dict) -> list[dict]:
        lecs = list_lectures(uid, enrollment["id"])
        for lec in lecs:
            lec["enrollment_id"] = enrollment["id"]
            lec["subject_slug"] = enrollment.get("subject_slug")
        return lecs

    # One subject per worker: the reads run in parallel instead of one after another.
    with ThreadPoolExecutor(max_workers=min(8, len(enrollments))) as pool:
        return [lec for lecs in pool.map(one, enrollments) for lec in lecs]


def get_lecture(uid: str, enrollment_id: str, lecture_id: str) -> dict | None:
    ref = (
        get_db().collection("users").document(uid)
        .collection("subjects").document(enrollment_id)
        .collection("lectures").document(lecture_id)
    )
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def update_lecture(uid: str, enrollment_id: str, lecture_id: str, data: dict) -> None:
    ref = (
        get_db().collection("users").document(uid)
        .collection("subjects").document(enrollment_id)
        .collection("lectures").document(lecture_id)
    )
    payload = dict(data)
    if payload.get("is_completed"):
        payload["completed_at"] = _now()
    ref.update(payload)


# --------------------------------------------------------------------- #
# Platform scrape cache (shared across students)
# --------------------------------------------------------------------- #
def get_cached_catalog(platform: str, subject_slug: str) -> dict | None:
    ref = get_db().collection("platform_cache").document(platform) \
        .collection("subjects").document(subject_slug)
    doc = ref.get()
    return doc.to_dict() if doc.exists else None


def set_cached_catalog(platform: str, subject_slug: str, data: dict) -> None:
    ref = get_db().collection("platform_cache").document(platform) \
        .collection("subjects").document(subject_slug)
    ref.set({**data, "synced_at": _now()})


# --------------------------------------------------------------------- #
# Study plans
# --------------------------------------------------------------------- #
def save_study_plan(uid: str, week_start_iso: str, plan: dict) -> None:
    ref = get_db().collection("users").document(uid).collection("study_plans").document(week_start_iso)
    ref.set(plan)


def get_study_plan(uid: str, week_start_iso: str) -> dict | None:
    ref = get_db().collection("users").document(uid).collection("study_plans").document(week_start_iso)
    doc = ref.get()
    return doc.to_dict() if doc.exists else None


def update_study_plan_task(uid: str, week_start_iso: str, task_id: str, is_done: bool) -> None:
    ref = get_db().collection("users").document(uid).collection("study_plans").document(week_start_iso)
    doc = ref.get()
    if not doc.exists:
        return
    data = doc.to_dict()
    for task in data.get("tasks", []):
        if task["id"] == task_id:
            task["is_done"] = is_done
    ref.set(data)


# --------------------------------------------------------------------- #
# AI chat history (تراكم coach memory + per-subject Q&A history)
# --------------------------------------------------------------------- #
def append_procrastination_message(uid: str, role: str, content: str) -> None:
    coll = get_db().collection("users").document(uid).collection("procrastination_chat")
    coll.add({"role": role, "content": content, "created_at": _now()})


def get_procrastination_history(uid: str, limit: int = 20) -> list[dict]:
    coll = get_db().collection("users").document(uid).collection("procrastination_chat")
    docs = coll.order_by("created_at", direction="DESCENDING").limit(limit).stream()
    history = [d.to_dict() for d in docs]
    return list(reversed(history))


def append_subject_qa_message(uid: str, subject_slug: str, role: str, content: str) -> None:
    coll = (
        get_db().collection("users").document(uid)
        .collection("subject_chat").document(subject_slug)
        .collection("messages")
    )
    coll.add({"role": role, "content": content, "created_at": _now()})


def get_subject_qa_history(uid: str, subject_slug: str, limit: int = 10) -> list[dict]:
    coll = (
        get_db().collection("users").document(uid)
        .collection("subject_chat").document(subject_slug)
        .collection("messages")
    )
    docs = coll.order_by("created_at", direction="DESCENDING").limit(limit).stream()
    history = [d.to_dict() for d in docs]
    return list(reversed(history))



# --------------------------------------------------------------------- #
# Per-lecture study tools: notes & rules, and "explain it to the AI" chat
# --------------------------------------------------------------------- #
# Both live in their own top-level-per-user collections (not inside the
# lecture doc) so the big /home/calendar payload stays small and a re-scrape
# that upserts lectures can never wipe what the student wrote.
def _study_key(enrollment_id: str, lecture_id: str) -> str:
    return f"{enrollment_id}__{lecture_id}"


def _user(uid: str):
    return get_db().collection("users").document(uid)


def get_lecture_notes(uid: str, enrollment_id: str, lecture_id: str) -> dict:
    doc = _user(uid).collection("lecture_notes").document(_study_key(enrollment_id, lecture_id)).get()
    data = doc.to_dict() if doc.exists else {}
    return {
        "notes": data.get("notes", ""),
        "rules": data.get("rules", ""),
        "updated_at": data.get("updated_at"),
    }


def save_lecture_notes(uid: str, enrollment_id: str, lecture_id: str, notes: str, rules: str) -> dict:
    ref = _user(uid).collection("lecture_notes").document(_study_key(enrollment_id, lecture_id))
    now = _now()
    ref.set({
        "enrollment_id": enrollment_id,
        "lecture_id": lecture_id,
        "notes": notes,
        "rules": rules,
        "updated_at": now,
    })
    return {"notes": notes, "rules": rules, "updated_at": now}


def list_lecture_ids_with_notes(uid: str) -> set[str]:
    """Keys (enrollmentId__lectureId) of lectures that have non-empty notes or
    rules. Used to light up the little dot on the Notes button."""
    out: set[str] = set()
    for d in _user(uid).collection("lecture_notes").stream():
        data = d.to_dict() or {}
        if (data.get("notes") or "").strip() or (data.get("rules") or "").strip():
            out.add(d.id)
    return out


def get_lecture_explain(uid: str, enrollment_id: str, lecture_id: str) -> dict:
    """Full saved explain-chat for one lecture: every message in order plus the
    final summary (if the student already finished one)."""
    ref = _user(uid).collection("lecture_explain").document(_study_key(enrollment_id, lecture_id))
    doc = ref.get()
    meta = doc.to_dict() if doc.exists else {}
    msgs = []
    for m in ref.collection("messages").order_by("created_at").stream():
        item = m.to_dict()
        msgs.append({"role": item.get("role"), "content": item.get("content", ""), "created_at": item.get("created_at")})
    return {
        "messages": msgs,
        "summary": meta.get("summary", ""),
        "summary_at": meta.get("summary_at"),
    }


def append_lecture_explain_message(uid: str, enrollment_id: str, lecture_id: str, role: str, content: str) -> None:
    ref = _user(uid).collection("lecture_explain").document(_study_key(enrollment_id, lecture_id))
    ref.set({"enrollment_id": enrollment_id, "lecture_id": lecture_id, "updated_at": _now()}, merge=True)
    ref.collection("messages").add({"role": role, "content": content, "created_at": _now()})


def save_lecture_explain_summary(uid: str, enrollment_id: str, lecture_id: str, summary: str) -> None:
    ref = _user(uid).collection("lecture_explain").document(_study_key(enrollment_id, lecture_id))
    ref.set({
        "enrollment_id": enrollment_id,
        "lecture_id": lecture_id,
        "summary": summary,
        "summary_at": _now(),
        "updated_at": _now(),
    }, merge=True)


def list_lecture_ids_with_explain(uid: str) -> set[str]:
    return {d.id for d in _user(uid).collection("lecture_explain").stream()}


def reset_lecture_explain(uid: str, enrollment_id: str, lecture_id: str) -> None:
    """Start the explain session over (chat + summary). Notes are untouched."""
    ref = _user(uid).collection("lecture_explain").document(_study_key(enrollment_id, lecture_id))
    for m in ref.collection("messages").stream():
        m.reference.delete()
    ref.delete()


def delete_lecture_study_data(uid: str, enrollment_id: str, lecture_id: str) -> None:
    """Called when a subject is removed so no orphaned notes/chats are left."""
    _user(uid).collection("lecture_notes").document(_study_key(enrollment_id, lecture_id)).delete()
    reset_lecture_explain(uid, enrollment_id, lecture_id)