from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from app.models.lecture import (
    Lecture, MonthBucket, OverallProgress, SubjectProgress, WeekBucket,
)
from app.services import firestore_service as db

_AR_MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]
_EN_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_ACCENTS = ["#2DD4BF", "#22D3EE", "#38BDF8", "#A78BFA", "#F472B6", "#FBBF24", "#34D399"]


def _status(percent: float) -> str:
    return "on_track" if percent >= 50 else "behind"


def compute_overall_progress(uid: str) -> OverallProgress:
    enrollments = db.list_enrollments(uid)
    subjects: list[SubjectProgress] = []
    total = completed = 0

    for i, enr in enumerate(enrollments):
        t = enr.get("total_lectures", 0)
        c = enr.get("completed_lectures", 0)
        percent = round(100 * c / t, 1) if t else 0.0
        subjects.append(
            SubjectProgress(
                subject_slug=enr["subject_slug"],
                subject_name=enr["subject_name"],
                color_accent=_ACCENTS[i % len(_ACCENTS)],
                total=t,
                completed=c,
                remaining=max(t - c, 0),
                percent=percent,
                status=_status(percent),
            )
        )
        total += t
        completed += c

    overall_percent = round(100 * completed / total, 1) if total else 0.0
    return OverallProgress(
        total=total,
        completed=completed,
        remaining=max(total - completed, 0),
        percent=overall_percent,
        status=_status(overall_percent),
        subjects=subjects,
    )


def _week_bounds(d: date) -> tuple[date, date]:
    """Saturday-start week, matching the Egyptian school-week convention."""
    # Python weekday(): Mon=0..Sun=6. We want Saturday=0..Friday=6.
    offset = (d.weekday() + 2) % 7
    start = d - timedelta(days=offset)
    return start, start + timedelta(days=6)


def build_home_calendar(uid: str, language: str = "ar") -> list[MonthBucket]:
    """Groups every lecture the student has (across all enrolled subjects)
    into months -> weeks -> subject, using each lecture's `uploaded_on`
    date. Lectures with no known date are placed in an 'غير محدد/Unscheduled'
    bucket at the end of the current month, so nothing silently disappears
    from the home tab even when a platform didn't expose a real date."""
    enrollment_list = db.list_enrollments(uid)
    enrollments = {e["id"]: e for e in enrollment_list}
    with ThreadPoolExecutor(max_workers=3) as pool:  # three independent reads, run together
        f_lectures = pool.submit(db.list_all_lectures_for_user, uid, enrollment_list)
        f_notes = pool.submit(db.list_lecture_ids_with_notes, uid)
        f_explain = pool.submit(db.list_lecture_ids_with_explain, uid)
        lectures_raw, with_notes, with_explain = f_lectures.result(), f_notes.result(), f_explain.result()

    by_month: dict[str, list[Lecture]] = defaultdict(list)
    for raw in lectures_raw:
        lec = Lecture(
            id=raw["id"],
            enrollment_id=raw["enrollment_id"],
            uid=uid,
            subject_slug=raw.get("subject_slug", ""),
            title=raw.get("title", ""),
            lecture_url=raw.get("lecture_url") or raw.get("url"),
            uploaded_on=raw.get("uploaded_on") or date.today(),
            order=raw.get("order", 0),
            is_completed=raw.get("is_completed", False),
            homework_done=raw.get("homework_done"),
            has_notes=f"{raw['enrollment_id']}__{raw['id']}" in with_notes,
            has_explain=f"{raw['enrollment_id']}__{raw['id']}" in with_explain,
        )
        month_key = f"{lec.uploaded_on.year:04d}-{lec.uploaded_on.month:02d}"
        by_month[month_key].append(lec)

    months: list[MonthBucket] = []
    for month_key in sorted(by_month.keys()):
        year, month = map(int, month_key.split("-"))
        lectures = by_month[month_key]

        weeks_map: dict[tuple[date, date], WeekBucket] = {}
        for lec in lectures:
            start, end = _week_bounds(lec.uploaded_on)
            key = (start, end)
            if key not in weeks_map:
                weeks_map[key] = WeekBucket(
                    week_index=0, start_date=start, end_date=end, subjects={}
                )
            bucket = weeks_map[key]
            bucket.subjects.setdefault(lec.subject_slug, []).append(lec)

        ordered_weeks = sorted(weeks_map.values(), key=lambda w: w.start_date)
        for idx, w in enumerate(ordered_weeks, start=1):
            w.week_index = idx
            for subj_lectures in w.subjects.values():
                subj_lectures.sort(key=lambda l: (l.uploaded_on, l.order))

        total = len(lectures)
        completed = sum(1 for l in lectures if l.is_completed)

        months.append(
            MonthBucket(
                month_key=month_key,
                label_ar=f"{_AR_MONTHS[month - 1]} {year}",
                label_en=f"{_EN_MONTHS[month - 1]} {year}",
                weeks=ordered_weeks,
                total_lectures=total,
                completed_lectures=completed,
            )
        )
    return months