from datetime import date

import pytest

from habits import core, schedule, storage


def store_with(name="exercise", sched=None, today=date(2026, 6, 24)):
    store = storage.empty_store()
    core.add_habit(store, name, today, sched=sched)
    return store


def entries_for(dates):
    return {d: {} for d in dates}


# --- mutations --------------------------------------------------------------


def test_add_is_idempotent_and_sets_defaults():
    today = date(2026, 6, 24)
    store = storage.empty_store()
    assert core.add_habit(store, "read", today, tags=["Books", "books"]) is True
    assert core.add_habit(store, "read", today) is False
    habit = store["habits"]["read"]
    assert habit["schedule"] == {"type": "daily"}
    assert habit["tags"] == ["books"]  # normalized + deduped
    assert habit["entries"] == {}


def test_add_rejects_blank_name():
    with pytest.raises(ValueError):
        core.add_habit(storage.empty_store(), "   ", date(2026, 6, 24))


def test_rename_preserves_history():
    store = store_with("read")
    core.mark(store, "read", date(2026, 6, 24))
    core.rename_habit(store, "read", "reading")
    assert "read" not in store["habits"]
    assert store["habits"]["reading"]["entries"] == {"2026-06-24": {}}
    assert store["habits"]["reading"]["name"] == "reading"


def test_rename_conflict():
    store = store_with("read")
    core.add_habit(store, "write", date(2026, 6, 24))
    with pytest.raises(ValueError):
        core.rename_habit(store, "read", "write")


def test_mark_with_note_and_idempotency():
    store = store_with()
    day = date(2026, 6, 24)
    assert core.mark(store, "exercise", day) is True
    assert core.mark(store, "exercise", day) is False  # unchanged
    assert core.mark(store, "exercise", day, note="5k") is True  # note changes it
    assert store["habits"]["exercise"]["entries"]["2026-06-24"] == {"note": "5k"}


def test_unmark():
    store = store_with()
    day = date(2026, 6, 24)
    core.mark(store, "exercise", day)
    assert core.unmark(store, "exercise", day) is True
    assert core.unmark(store, "exercise", day) is False


def test_archive_toggle():
    store = store_with()
    assert core.set_archived(store, "exercise", True) is True
    assert core.set_archived(store, "exercise", True) is False
    assert store["habits"]["exercise"]["archived"] is True


# --- daily streaks ----------------------------------------------------------


def test_daily_current_streak():
    today = date(2026, 6, 24)
    e = entries_for(["2026-06-22", "2026-06-23", "2026-06-24"])
    assert core.current_streak(e, schedule.daily(), today) == 3


def test_daily_streak_grace_for_today():
    today = date(2026, 6, 24)
    e = entries_for(["2026-06-22", "2026-06-23"])  # not yet done today
    assert core.current_streak(e, schedule.daily(), today) == 2


def test_daily_streak_breaks_after_gap():
    today = date(2026, 6, 24)
    e = entries_for(["2026-06-20", "2026-06-21"])
    assert core.current_streak(e, schedule.daily(), today) == 0


def test_daily_longest_streak():
    today = date(2026, 6, 30)
    e = entries_for(["2026-06-01", "2026-06-02", "2026-06-03",
                     "2026-06-10", "2026-06-11"])
    assert core.longest_streak(e, schedule.daily(), today) == 3


# --- weekly (weekday) streaks ----------------------------------------------


def test_weekly_streak_ignores_non_due_days():
    # Mon/Wed/Fri habit. today = Fri 2026-06-26.
    sched = schedule.parse("mon,wed,fri")
    today = date(2026, 6, 26)  # Friday
    # completed Mon 22, Wed 24, Fri 26 — three due days in a row.
    e = entries_for(["2026-06-22", "2026-06-24", "2026-06-26"])
    assert core.current_streak(e, sched, today) == 3


def test_weekly_streak_survives_non_due_today():
    sched = schedule.parse("mon,wed,fri")
    today = date(2026, 6, 25)  # Thursday — not a due day
    e = entries_for(["2026-06-22", "2026-06-24"])  # Mon, Wed done
    # Thursday isn't due, so the most recent due day (Wed) is done -> streak 2.
    assert core.current_streak(e, sched, today) == 2


def test_weekly_streak_breaks_on_missed_due_day():
    sched = schedule.parse("mon,wed,fri")
    today = date(2026, 6, 26)  # Friday
    e = entries_for(["2026-06-22", "2026-06-26"])  # missed Wed 24
    # Friday done, but Wed missed -> streak only counts Friday.
    assert core.current_streak(e, sched, today) == 1


# --- times-per-week streaks -------------------------------------------------


def test_times_per_week_current_streak():
    sched = schedule.parse("3/week")
    today = date(2026, 6, 24)  # Wed, week of Mon 22
    e = entries_for([
        # this week: 3 done -> met
        "2026-06-22", "2026-06-23", "2026-06-24",
        # last week (Mon 15..Sun 21): 3 done -> met
        "2026-06-15", "2026-06-17", "2026-06-19",
    ])
    assert core.current_streak(e, sched, today) == 2


def test_times_per_week_grace_when_current_week_incomplete():
    sched = schedule.parse("3/week")
    today = date(2026, 6, 24)
    e = entries_for([
        "2026-06-22",  # this week: only 1 so far (not met) -> grace
        "2026-06-15", "2026-06-17", "2026-06-19",  # last week met
    ])
    assert core.current_streak(e, sched, today) == 1


def test_times_per_week_longest():
    sched = schedule.parse("2/week")
    today = date(2026, 6, 28)
    e = entries_for([
        "2026-06-01", "2026-06-02",  # week met
        "2026-06-08", "2026-06-09",  # week met
        # skip a week
        "2026-06-22", "2026-06-23",  # week met
    ])
    assert core.longest_streak(e, sched, today) == 2


# --- completion rate --------------------------------------------------------


def test_completion_rate_daily():
    today = date(2026, 6, 24)
    e = entries_for(["2026-06-24", "2026-06-23"])
    assert core.completion_rate(e, schedule.daily(), today, 7) == 2 / 7


def test_completion_rate_weekly_only_counts_due_days():
    sched = schedule.parse("mon,wed,fri")  # ~3 due days per week
    today = date(2026, 6, 26)  # Friday
    e = entries_for(["2026-06-22", "2026-06-24", "2026-06-26"])  # all 3 this week
    rate = core.completion_rate(e, sched, today, 7)
    assert rate == 1.0  # every due day in the last 7 days was hit


def test_completion_rate_empty_window_is_full():
    sched = schedule.parse("mon")  # only Mondays
    today = date(2026, 6, 25)  # Thu
    e = {}
    # window of 3 days (Tue-Thu) has no Mondays -> nothing required -> 1.0
    assert core.completion_rate(e, sched, today, 3) == 1.0


def test_completion_rate_rejects_bad_window():
    with pytest.raises(ValueError):
        core.completion_rate({}, schedule.daily(), date(2026, 6, 24), 0)
