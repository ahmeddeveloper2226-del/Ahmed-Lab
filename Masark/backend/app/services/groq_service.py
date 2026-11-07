"""
Groq AI service — four distinct features, each with its own prompt
contract and JSON schema where structured output matters:

  1. generate_study_plan   -> weekly plan for خطة الدراسة, JSON-only output
  2. procrastination_chat  -> تراكم coach, remembers past sessions (Firestore)
  3. subject_qa            -> plain text answer scoped to one subject
  4. lecture_explain_chat / lecture_explain_summary
                           -> "if you understood then explain": the student
                              teaches the AI one lecture, the AI plays a
                              curious classmate, then summarizes it

All three run on Groq's OpenAI-compatible chat.completions endpoint with
the `openai/gpt-oss-20b` model (see GROQ_MODEL / GROQ_MODEL_PRO in
app.core.config). Calls are wrapped with retries and a hard timeout;
failures raise AIServiceError so routes can return a clean 503 instead of
leaking a raw SDK traceback to the frontend.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import structlog
from groq import APIError, APITimeoutError, Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import AIServiceError
from app.models.user import WeeklyAvailability

log = structlog.get_logger()
settings = get_settings()

_REQUEST_TIMEOUT_SECONDS = 30

_client: Groq | None = None


def _get_client() -> Groq:
    """Lazily build (and cache) the Groq client. Lazy so importing this
    module never requires a valid API key — only calling it does."""
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def _to_chat_messages(
    history: list[dict] | None, prompt: str, *, system: str | None = None
) -> list[dict]:
    """Build an OpenAI-style messages list.

    History entries may still use Gemini-style role names ("model" for the
    assistant turn) if they were persisted before this migration, or by
    older callers — normalize those to "assistant" so Groq accepts them.
    """
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    for turn in history or []:
        role = "assistant" if turn["role"] in ("model", "assistant") else "user"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": prompt})
    return messages


def _is_reasoning_model(model_name: str) -> bool:
    return "gpt-oss" in model_name


@retry(reraise=True, stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def _generate(
    model_name: str,
    prompt: str,
    *,
    json_mode: bool = False,
    history: list[dict] | None = None,
    system: str | None = None,
    max_tokens: int = 2048,
    reasoning_effort: str = "low",
) -> str:
    client = _get_client()
    kwargs: dict = {
        "model": model_name,
        "messages": _to_chat_messages(history, prompt, system=system),
        "timeout": _REQUEST_TIMEOUT_SECONDS,
        # Reasoning models spend part of this budget "thinking". If it is too
        # small they can burn all of it and return empty text, which Groq then
        # reports as json_validate_failed with an empty failed_generation.
        "max_completion_tokens": max_tokens,
    }
    if _is_reasoning_model(model_name):
        kwargs["reasoning_effort"] = reasoning_effort
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except (APIError, APITimeoutError) as exc:
        log.error("groq.call_failed", error=str(exc), model=model_name, json_mode=json_mode)
        raise AIServiceError("The study assistant is unavailable right now, try again shortly.") from exc
    except Exception as exc:  # noqa: BLE001
        log.error("groq.call_failed", error=str(exc), model=model_name, json_mode=json_mode)
        raise AIServiceError("The study assistant is unavailable right now, try again shortly.") from exc


def _parse_json(raw: str) -> dict:
    """Parse a JSON object from model text, tolerating ``` fences or extra
    prose around it. Raises json.JSONDecodeError / ValueError if none found."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model output")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    return data


# --------------------------------------------------------------------- #
# 1. Weekly study plan (خطة الدراسة)
# --------------------------------------------------------------------- #
def generate_study_plan(
    *,
    student_name: str,
    academic_level: str,
    # [{subject_slug, subject_name, remaining,
    #   pending_lectures: [{"id": int, "title": str}], completed_lecture_titles: [str]}]
    subjects_remaining: list[dict],
    availability: WeeklyAvailability,
    week_start: date,
    extra_notes: str | None = None,
) -> dict:
    week_end = week_start + timedelta(days=6)
    prompt = f"""
You are an expert Egyptian school study-planning assistant for the "مسارك" app.
Build ONE week's study schedule ({week_start.isoformat()} to {week_end.isoformat()})
for a {academic_level} student named {student_name}.

Constraints:
- Weekday study budget: {availability.weekday_hours} hours/day.
- Weekend study budget: {availability.weekend_hours} hours/day.
- Days the student is completely unavailable (0=Mon..6=Sun): {availability.off_days}.
- Prioritize subjects with more remaining lectures and spread them across the
  week rather than clustering one subject on one day.
- Never schedule anything on an unavailable day.
- Extra notes from the student: {extra_notes or "none"}.

LECTURE ORDER (very important):
- Each subject lists its not-yet-finished lectures as {{"id", "title"}}. The order
  of that list is NOT reliable: it may be shuffled, reversed, or follow upload time.
- Read every title and work out its true position in the course yourself.
  Titles come in many styles and languages, for example "Ch1L5" (chapter 1,
  lecture 5), "Chapter 2 - Lesson 3", "المحاضرة الأولى", "المحاضرة الثانية",
  "الدرس 4", "الوحدة الثانية - الدرس الأول", "Part 2", Arabic-Indic digits (٣),
  or plain topic names that imply a logical order (basics before advanced).
  Compare the chapter/unit first, then the lecture number inside it. Use the
  already-completed titles as a hint for the numbering style and for where the
  student is up to.
- Within one subject, schedule lectures strictly in that true sequence: an earlier
  lecture must never be on a later day than a later lecture, and on the same day it
  must come first in the "tasks" array. Always take the earliest unfinished
  lectures first.
- Use each lecture at most once. Put the exact integer "id" from the list in
  "lecture_id" and copy that lecture's title exactly into "lecture_title".

Remaining work per subject (use these exact subject_slug values):
{json.dumps(subjects_remaining, ensure_ascii=False, indent=1)}

Respond with ONLY valid JSON (no markdown fences, no commentary) matching:
{{
  "summary_ar": "one short encouraging sentence in Egyptian-friendly Arabic",
  "summary_en": "same sentence in English",
  "tasks": [
    {{
      "day": "YYYY-MM-DD",
      "subject_slug": "...",
      "subject_name": "...",
      "lecture_id": 12,
      "lecture_title": "exact title from the list",
      "estimated_minutes": 45,
      "note": "short reason, e.g. 'falling behind in this subject'"
    }}
  ]
}}
Sort "tasks" by day, and by study order within each day.
""".strip()

    # Strict JSON mode first; if Groq rejects it (e.g. empty generation), retry
    # once in plain mode — the prompt already demands JSON-only output.
    raw = ""
    try:
        raw = _generate(settings.GROQ_MODEL, prompt, json_mode=True, max_tokens=8192, reasoning_effort="medium")
    except AIServiceError:
        log.warning("groq.json_mode_failed_retrying_plain")
        raw = _generate(settings.GROQ_MODEL, prompt, json_mode=False, max_tokens=8192, reasoning_effort="medium")
    try:
        return _parse_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("groq.bad_json", raw=raw[:500])
        raise AIServiceError("Could not build a study plan right now, please retry.") from exc


# --------------------------------------------------------------------- #
# 2. تراكم procrastination coach — remembers past sessions
# --------------------------------------------------------------------- #
_PROCRASTINATION_SYSTEM_PRIMER = """
You are a warm, non-judgmental Arabic-speaking study coach inside the
"مسارك" app, specialized in helping Egyptian secondary/prep students who
have fallen behind on their recorded lectures (تراكم الحصص). Always reply in
Egyptian-friendly Arabic unless the student writes in English. Ask what is
causing the backlog (motivation, a hard subject, time management, personal
issues, phone/social-media distraction, etc.), acknowledge it briefly, then
give ONE concrete, small, doable next action — never a long lecture. Keep
replies under ~80 words. You are shown the student's past sessions so you
can notice patterns (e.g. always mentioning the same subject, or the same
excuse) and gently reflect that back when it's genuinely helpful — do not
force a callback to old sessions if it doesn't naturally fit.
""".strip()


def procrastination_chat(*, history: list[dict], message: str) -> tuple[str, list[str]]:
    reply = _generate(
        settings.GROQ_MODEL,
        message,
        history=history,
        system=_PROCRASTINATION_SYSTEM_PRIMER,
    )
    # Lightweight heuristic action suggestions shown as quick-tap chips in the UI.
    suggestions = [
        "ابدأ بحصة واحدة بس دلوقتي",
        "حط تايمر ٢٥ دقيقة وذاكر لحد ما يخلص",
        "قفل التطبيقات المشتتة نص ساعة",
    ]
    return reply.strip(), suggestions


# --------------------------------------------------------------------- #
# 3. Subject Q&A
# --------------------------------------------------------------------- #
def subject_qa(*, subject_name: str, history: list[dict], question: str) -> str:
    primer = (
        f"You are a patient, encouraging tutor helping an Egyptian school "
        f"student with the subject '{subject_name}'. Answer clearly and "
        f"simply, in the same language as the question (Arabic or English). "
        f"If the question is unrelated to {subject_name}, politely redirect "
        f"the student to ask in the right subject's help chat instead."
    )
    reply = _generate(settings.GROQ_MODEL, question, history=history, system=primer)
    return reply.strip()


# --------------------------------------------------------------------- #
# 4. "If you understood, then explain" — per-lecture teach-the-AI chat
# --------------------------------------------------------------------- #
_EXPLAIN_MAX_TURNS = 40  # most recent messages sent to the model


def _explain_system_prompt(subject_name: str, lecture_title: str, lang_hint: str) -> str:
    fallback = "Egyptian-friendly Arabic" if lang_hint == "ar" else "English"
    return f"""
You are a friendly, curious classmate inside the "مسارك" study app. The student
in front of you just watched a lecture and is going to explain it to YOU so they
can check they really understood it.

Subject: {subject_name}
Lecture title: {lecture_title}

HOW YOU BEHAVE
1. LEARNER MODE (default). Act as if you have NOT seen this lecture and do not
   know its content. Learn only from what the student tells you. Never fill the
   gaps yourself and never lecture them. React briefly to what they said, then
   ask ONE or TWO short follow-up questions about the parts that are unclear,
   missing or too vague ("why does that happen?", "can you give me an example?").
2. CORRECTIONS. You are still allowed to know well-established facts of the
   subject. If the student says something that is wrong, do NOT accept it
   silently and do NOT build on it: kindly say that part isn't right, give the
   correct version in one or two sentences, and ask them to say it again in their
   own words. If you're not sure whether a lecture-specific claim is right, say
   you're not sure rather than guessing.
3. TEACHER MODE. If the student says they did NOT understand something from the
   lecture (for example "I didn't understand X", "مفهمتش X", "explain X to me"),
   switch to being a patient tutor for that point only: explain it in simple
   steps with a small concrete example. Then ALWAYS finish by asking them to
   explain it back to you in their own words to prove they got it.
4. CHECK-BACK. When they explain it back, tell them clearly what they got right,
   fix anything wrong or missing, and if they still seem lost, explain it again
   in a different way and ask for another try.
5. When the student has covered the lecture well, say in 2-3 lines what you now
   understand and tell them they can press the "Finish & summarize" button to get
   a clean summary. Do not write the full summary yourself.

STYLE
- Reply in the same language and dialect the student writes in; if it is unclear,
  use {fallback}.
- Keep replies short (under about 120 words), warm and encouraging, never
  condescending. Plain text; you may use **bold** for key terms and "- " bullets.
- Never invent what the lecture "said". If you don't know, ask.
""".strip()


def lecture_explain_chat(
    *, subject_name: str, lecture_title: str, history: list[dict], message: str, lang_hint: str = "ar"
) -> str:
    reply = _generate(
        settings.GROQ_MODEL,
        message,
        history=(history or [])[-_EXPLAIN_MAX_TURNS:],
        system=_explain_system_prompt(subject_name, lecture_title, lang_hint),
        max_tokens=2048,
    )
    return reply.strip()


def lecture_explain_summary(
    *, subject_name: str, lecture_title: str, history: list[dict], lang_hint: str = "ar"
) -> str:
    """Summarize the lecture from what the student taught during the chat,
    including the corrections the AI made."""
    transcript = "\n".join(
        f"{'STUDENT' if t['role'] == 'user' else 'CLASSMATE'}: {t['content']}" for t in history
    )
    fallback = "Egyptian-friendly Arabic" if lang_hint == "ar" else "English"
    prompt = f"""
Below is a conversation in which a student explained a lecture to a curious
classmate (an AI) who then asked questions, corrected mistakes and sometimes
re-explained points the student did not understand.

Subject: {subject_name}
Lecture title: {lecture_title}

Write a clear, well-organized study summary of THIS LECTURE, built only from the
information in the conversation (the student's explanations plus any corrections
or re-explanations the classmate gave). Do not add topics that never came up. If
the student said something wrong and it was corrected, write the CORRECT version.

Use the language the student mostly wrote in (if unclear, {fallback}) and this
structure, skipping any section that has nothing in it:
## Main idea
(1-2 sentences)
## Key points
- bullet points, short and clear
## Definitions, rules & formulas
- term: meaning
## Examples
- the examples that came up
## Watch out (corrected mistakes)
- the mistake -> the correct version
## Still unclear
- points the student never fully explained or understood

Use **bold** for key terms. No preamble and no closing remarks, only the summary.

CONVERSATION:
{transcript}
""".strip()
    return _generate(settings.GROQ_MODEL, prompt, max_tokens=4096, reasoning_effort="medium").strip()