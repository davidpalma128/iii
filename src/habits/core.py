"""Pure habit-domain logic: streaks, stats, and the heatmap.

Everything here is deliberately free of I/O and free of ``date.today()`` calls
so the behaviour is deterministic and easy to unit-test. The caller passes the
"today" reference date in.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Set


def parse_day(value: str) -> date:
    """Parse an ISO ``YYYY-MM-DD`` string into a :class:`datetime.date`."""
    return date.fromisoformat(value)


def _date_set(log: Iterable[str]) -> Set[date]:
    return {parse_day(d) for d in log}


def add_habit(store: Dict[str, Any], name: str, today: date) -> bool:
    """Add a habit. Returns ``False`` if it already exists."""
    name = name.strip()
    if not name:
        raise ValueError("habit name cannot be empty")
    if name in store["habits"]:
        return False
    store["habits"][name] = {
        "name": name,
        "created": today.isoformat(),
        "log": [],
    }
    return True


def remove_habit(store: Dict[str, Any], name: str) -> bool:
    """Delete a habit. Returns ``False`` if it does not exist."""
    return store["habits"].pop(name, None) is not None


def mark(store: Dict[str, Any], name: str, day: date) -> bool:
    """Mark ``name`` complete on ``day``. Returns ``False`` if already marked."""
    habit = store["habits"][name]
    iso = day.isoformat()
    if iso in habit["log"]:
        return False
    habit["log"].append(iso)
    habit["log"].sort()
    return True


def unmark(store: Dict[str, Any], name: str, day: date) -> bool:
    """Clear ``name`` on ``day``. Returns ``False`` if it was not marked."""
    habit = store["habits"][name]
    iso = day.isoformat()
    if iso not in habit["log"]:
        return False
    habit["log"].remove(iso)
    return True


def current_streak(log: Iterable[str], today: date) -> int:
    """Count consecutive completed days ending today or yesterday.

    A streak stays "alive" until a full day has been missed, so checking in
    yesterday but not yet today still counts.
    """
    days = _date_set(log)
    if not days:
        return 0

    if today in days:
        cursor = today
    elif (today - timedelta(days=1)) in days:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak(log: Iterable[str]) -> int:
    """Return the longest run of consecutive completed days, ever."""
    days = sorted(_date_set(log))
    if not days:
        return 0

    best = run = 1
    for prev, cur in zip(days, days[1:]):
        if cur - prev == timedelta(days=1):
            run += 1
        else:
            run = 1
        best = max(best, run)
    return best


def completion_rate(log: Iterable[str], today: date, window: int) -> float:
    """Fraction (0.0–1.0) of the last ``window`` days that were completed."""
    if window <= 0:
        raise ValueError("window must be positive")
    days = _date_set(log)
    span = {today - timedelta(days=i) for i in range(window)}
    return len(days & span) / window


def heatmap(log: Iterable[str], today: date, weeks: int = 15) -> str:
    """Render a GitHub-style contributions grid for the trailing ``weeks``.

    Rows are weekdays (Mon–Sun); columns are weeks. ``█`` marks a completed
    day, ``·`` an incomplete one, and future days in the current week are blank.
    """
    days = _date_set(log)
    # Anchor on the Sunday that ends this week so columns align to weeks.
    end = today + timedelta(days=(6 - today.weekday()))
    start = end - timedelta(weeks=weeks - 1, days=6)

    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    rows: List[str] = []
    for weekday in range(7):
        cells = []
        for w in range(weeks):
            cell_day = start + timedelta(weeks=w, days=weekday)
            if cell_day > today:
                cells.append(" ")
            elif cell_day in days:
                cells.append("█")
            else:
                cells.append("·")
        rows.append(f"{labels[weekday]} " + "".join(cells))
    return "\n".join(rows)
