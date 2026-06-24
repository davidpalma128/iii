from datetime import date

from habits import core, storage


def make_store(today=date(2026, 6, 24)):
    store = storage.empty_store()
    core.add_habit(store, "exercise", today)
    return store


def test_add_is_idempotent():
    today = date(2026, 6, 24)
    store = storage.empty_store()
    assert core.add_habit(store, "read", today) is True
    assert core.add_habit(store, "read", today) is False
    assert "read" in store["habits"]


def test_add_rejects_blank_name():
    store = storage.empty_store()
    try:
        core.add_habit(store, "   ", date(2026, 6, 24))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_remove():
    store = make_store()
    assert core.remove_habit(store, "exercise") is True
    assert core.remove_habit(store, "exercise") is False


def test_mark_and_unmark():
    store = make_store()
    day = date(2026, 6, 24)
    assert core.mark(store, "exercise", day) is True
    assert core.mark(store, "exercise", day) is False  # already marked
    assert store["habits"]["exercise"]["log"] == ["2026-06-24"]
    assert core.unmark(store, "exercise", day) is True
    assert core.unmark(store, "exercise", day) is False


def test_log_stays_sorted():
    store = make_store()
    for d in ["2026-06-24", "2026-06-20", "2026-06-22"]:
        core.mark(store, "exercise", date.fromisoformat(d))
    assert store["habits"]["exercise"]["log"] == [
        "2026-06-20",
        "2026-06-22",
        "2026-06-24",
    ]


def test_current_streak_counts_today_backwards():
    today = date(2026, 6, 24)
    log = ["2026-06-22", "2026-06-23", "2026-06-24"]
    assert core.current_streak(log, today) == 3


def test_current_streak_survives_until_a_full_day_missed():
    today = date(2026, 6, 24)
    # checked in yesterday but not yet today -> streak still alive
    log = ["2026-06-22", "2026-06-23"]
    assert core.current_streak(log, today) == 2


def test_current_streak_breaks_after_a_gap():
    today = date(2026, 6, 24)
    log = ["2026-06-20", "2026-06-21"]  # two days ago -> broken
    assert core.current_streak(log, today) == 0


def test_current_streak_empty():
    assert core.current_streak([], date(2026, 6, 24)) == 0


def test_longest_streak():
    log = [
        "2026-06-01",
        "2026-06-02",
        "2026-06-03",  # run of 3
        "2026-06-10",
        "2026-06-11",  # run of 2
    ]
    assert core.longest_streak(log) == 3


def test_longest_streak_empty():
    assert core.longest_streak([]) == 0


def test_completion_rate():
    today = date(2026, 6, 24)
    log = ["2026-06-24", "2026-06-23", "2026-06-10"]
    # last 7 days: only the 23rd and 24th fall in range -> 2/7
    assert core.completion_rate(log, today, 7) == 2 / 7


def test_heatmap_shape_and_markers():
    today = date(2026, 6, 24)  # a Wednesday
    log = ["2026-06-24"]
    grid = core.heatmap(log, today, weeks=4)
    lines = grid.splitlines()
    assert len(lines) == 7  # one row per weekday
    assert lines[0].startswith("Mon")
    assert "█" in grid  # today is rendered as completed
