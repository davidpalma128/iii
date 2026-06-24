"""Pure habit-domain logic: streaks, stats, completion rates.

Everything here is free of I/O and free of ``date.today()`` calls so behaviour
is deterministic and easy to unit-test — the caller passes "today" in. All
streak/rate maths is **schedule-aware**: a Mon/Wed/Fri habit isn't "broken" by
not doing it on Tuesday, and an *N-per-week* habit is measured in weeks.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set

from . import schedule

_MAX_GAP = 14  # max days to look back for the previous due day (weekly => 7)


def parse_day(value: str) -> date:
    """Parse an ISO ``YYYY-MM-DD`` string into a :class:`datetime.date`."""
    return date.fromisoformat(value)


def entry_dates(entries: Dict[str, Any]) -> Set[date]:
    """Return the set of completed dates from an ``entries`` map."""
    return {parse_day(d) for d in entries}


def week_start(day: date) -> date:
    """Monday of the ISO week containing ``day``."""
    return day - timedelta(days=day.weekday())


# --- mutations (operate on the store dict) ----------------------------------


def add_habit(
    store: Dict[str, Any],
    name: str,
    today: date,
    sched: Optional[Dict[str, Any]] = None,
    tags: Optional[Iterable[str]] = None,
    description: str = "",
) -> bool:
    """Add a habit. Returns ``False`` if it already exists."""
    from . import storage

    name = name.strip()
    if not name:
        raise ValueError("habit name cannot be empty")
    if name in store["habits"]:
        return False
    habit = storage.new_habit(name, today.isoformat(), sched)
    habit["tags"] = sorted({t.strip().lower() for t in (tags or []) if t.strip()})
    habit["description"] = description.strip()
    store["habits"][name] = habit
    return True


def remove_habit(store: Dict[str, Any], name: str) -> bool:
    """Delete a habit. Returns ``False`` if it does not exist."""
    return store["habits"].pop(name, None) is not None


def rename_habit(store: Dict[str, Any], old: str, new: str) -> None:
    """Rename a habit, preserving all history."""
    new = new.strip()
    if not new:
        raise ValueError("new name cannot be empty")
    if old not in store["habits"]:
        raise KeyError(old)
    if new in store["habits"]:
        raise ValueError(f"habit {new!r} already exists")
    habit = store["habits"].pop(old)
    habit["name"] = new
    store["habits"][new] = habit


def set_archived(store: Dict[str, Any], name: str, archived: bool) -> bool:
    """Set the archived flag. Returns ``True`` if it changed."""
    habit = store["habits"][name]
    if habit.get("archived", False) == archived:
        return False
    habit["archived"] = archived
    return True


def mark(store: Dict[str, Any], name: str, day: date, note: Optional[str] = None) -> bool:
    """Mark ``name`` complete on ``day``. Returns ``True`` if the store changed."""
    habit = store["habits"][name]
    entries = habit["entries"]
    iso = day.isoformat()
    payload = {"note": note.strip()} if note and note.strip() else {}
    if iso in entries and entries[iso] == payload:
        return False
    entries[iso] = payload
    return True


def unmark(store: Dict[str, Any], name: str, day: date) -> bool:
    """Clear ``name`` on ``day``. Returns ``False`` if it was not marked."""
    entries = store["habits"][name]["entries"]
    return entries.pop(day.isoformat(), None) is not None


# --- streaks & stats --------------------------------------------------------


def _prev_due(sched: Dict[str, Any], day: date) -> Optional[date]:
    """The most recent due day strictly before... well, on-or-before ``day``."""
    cur = day
    for _ in range(_MAX_GAP):
        if schedule.is_due(sched, cur):
            return cur
        cur -= timedelta(days=1)
    return None


def current_streak(entries: Dict[str, Any], sched: Dict[str, Any], today: date) -> int:
    """Consecutive completed *due* periods ending at (or pending) today."""
    done = entry_dates(entries)
    if not done:
        return 0

    if sched.get("type") == "times_per_week":
        return _week_current_streak(done, sched["count"], today)

    cur = _prev_due(sched, today)
    if cur is None:
        return 0
    if cur not in done:
        if cur == today:  # today's due day is still pending — don't break yet
            cur = _prev_due(sched, today - timedelta(days=1))
        else:
            return 0

    streak = 0
    while cur is not None and cur in done:
        streak += 1
        cur = _prev_due(sched, cur - timedelta(days=1))
    return streak


def _week_current_streak(done: Set[date], count: int, today: date) -> int:
    counts = Counter(week_start(d) for d in done)
    streak = 0
    w = week_start(today)
    if counts.get(w, 0) >= count:  # current week already met
        streak += 1
    w -= timedelta(days=7)  # current week, if unmet, gets grace
    while counts.get(w, 0) >= count:
        streak += 1
        w -= timedelta(days=7)
    return streak


def longest_streak(entries: Dict[str, Any], sched: Dict[str, Any], today: date) -> int:
    """Longest run of consecutive completed due periods, ever."""
    done = entry_dates(entries)
    if not done:
        return 0

    if sched.get("type") == "times_per_week":
        return _week_longest_streak(done, sched["count"], today)

    start = min(done)
    days = schedule.due_days(sched, start, today)
    best = run = 0
    for d in days:
        run = run + 1 if d in done else 0
        best = max(best, run)
    return best


def _week_longest_streak(done: Set[date], count: int, today: date) -> int:
    counts = Counter(week_start(d) for d in done)
    if not counts:
        return 0
    w = min(counts)
    end = week_start(today)
    best = run = 0
    while w <= end:
        run = run + 1 if counts.get(w, 0) >= count else 0
        best = max(best, run)
        w += timedelta(days=7)
    return best


def completion_rate(
    entries: Dict[str, Any], sched: Dict[str, Any], today: date, window: int
) -> float:
    """Fraction (0.0–1.0) of expected completions met over the last ``window`` days."""
    if window <= 0:
        raise ValueError("window must be positive")
    done = entry_dates(entries)
    span_start = today - timedelta(days=window - 1)

    if sched.get("type") == "times_per_week":
        count = sched["count"]
        in_window = sum(1 for d in done if span_start <= d <= today)
        expected = count * (window / 7.0)
        return min(1.0, in_window / expected) if expected else 1.0

    due = schedule.due_days(sched, span_start, today)
    if not due:
        return 1.0
    hit = sum(1 for d in due if d in done)
    return hit / len(due)


def total_checkins(entries: Dict[str, Any]) -> int:
    return len(entries)
