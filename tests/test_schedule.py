from datetime import date

import pytest

from habits import schedule


def test_parse_daily_variants():
    for spec in ["daily", "day", "everyday", "", "DAILY"]:
        assert schedule.parse(spec) == {"type": "daily"}


def test_parse_weekdays():
    assert schedule.parse("mon,wed,fri") == {"type": "weekly", "days": [0, 2, 4]}
    # order-insensitive and dedupes
    assert schedule.parse("fri,mon,mon") == {"type": "weekly", "days": [0, 4]}


def test_parse_times_per_week():
    assert schedule.parse("3/week") == {"type": "times_per_week", "count": 3}
    assert schedule.parse("5x/week") == {"type": "times_per_week", "count": 5}
    assert schedule.parse("2 per week") == {"type": "times_per_week", "count": 2}


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        schedule.parse("funday")
    with pytest.raises(ValueError):
        schedule.parse("9/week")


def test_label():
    assert schedule.label({"type": "daily"}) == "daily"
    assert schedule.label({"type": "weekly", "days": [0, 2, 4]}) == "Mon, Wed, Fri"
    assert schedule.label({"type": "times_per_week", "count": 3}) == "3x / week"


def test_is_due():
    wed = date(2026, 6, 24)  # Wednesday
    thu = date(2026, 6, 25)
    sched = {"type": "weekly", "days": [2]}  # Wednesdays
    assert schedule.is_due(sched, wed) is True
    assert schedule.is_due(sched, thu) is False
    # daily & times_per_week are always "due"
    assert schedule.is_due({"type": "daily"}, thu) is True
    assert schedule.is_due({"type": "times_per_week", "count": 3}, thu) is True


def test_due_days_range():
    start = date(2026, 6, 22)  # Monday
    end = date(2026, 6, 28)  # Sunday
    sched = {"type": "weekly", "days": [0, 4]}  # Mon, Fri
    days = schedule.due_days(sched, start, end)
    assert days == [date(2026, 6, 22), date(2026, 6, 26)]
