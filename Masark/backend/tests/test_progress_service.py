from datetime import date

from app.services.progress_service import _status, _week_bounds


def test_status_threshold():
    assert _status(50.0) == "on_track"
    assert _status(49.9) == "behind"
    assert _status(0.0) == "behind"
    assert _status(100.0) == "on_track"


def test_week_bounds_saturday_start():
    # Wednesday 2026-09-23 -> week should start Saturday 2026-09-19
    start, end = _week_bounds(date(2026, 9, 23))
    assert start == date(2026, 9, 19)
    assert end == date(2026, 9, 25)
    assert start.strftime("%A") == "Saturday"
