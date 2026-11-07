"""Tests for the per-lecture notes + explain-to-AI features (no network/Firestore)."""
from app.models.ai import LectureNotesUpdate
from app.services import groq_service as g


def test_notes_limits():
    LectureNotesUpdate(notes="x" * 20000, rules="")
    try:
        LectureNotesUpdate(notes="x" * 20001, rules="")
    except Exception:
        return
    raise AssertionError("oversized notes should be rejected")


def test_explain_prompt_has_all_behaviours():
    p = g._explain_system_prompt("Physics", "Lecture 3", "ar")
    assert "Physics" in p and "Lecture 3" in p
    for needle in ("LEARNER MODE", "CORRECTIONS", "TEACHER MODE", "CHECK-BACK", "explain it back"):
        assert needle in p
    assert "Egyptian" in p


def test_explain_chat_passes_history_and_trims(monkeypatch):
    seen = {}

    def fake_generate(model, prompt, **kw):
        seen["prompt"], seen["kw"] = prompt, kw
        return "  ok  "

    monkeypatch.setattr(g, "_generate", fake_generate)
    history = [{"role": "user" if i % 2 == 0 else "model", "content": str(i)} for i in range(100)]
    out = g.lecture_explain_chat(subject_name="S", lecture_title="T", history=history, message="hi")
    assert out == "ok"
    assert len(seen["kw"]["history"]) == g._EXPLAIN_MAX_TURNS
    assert seen["kw"]["history"][-1]["content"] == "99"


def test_summary_transcript_labels_roles(monkeypatch):
    seen = {}
    monkeypatch.setattr(g, "_generate", lambda model, prompt, **kw: seen.setdefault("p", prompt) and "sum")
    g.lecture_explain_summary(
        subject_name="S", lecture_title="T",
        history=[{"role": "user", "content": "A is B"}, {"role": "model", "content": "Not quite"}],
    )
    assert "STUDENT: A is B" in seen["p"] and "CLASSMATE: Not quite" in seen["p"]