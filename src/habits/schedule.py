"""Habit schedules: when a habit is "due".

Three kinds, all stored as plain dicts so they serialize straight to JSON:

* ``{"type": "daily"}`` — due every day.
* ``{"type": "weekly", "days": [0, 2, 4]}`` — due on the given weekdays
  (Mon=0 … Sun=6).
* ``{"type": "times_per_week", "count": 3}`` — due *some* 3 days each week;
  no specific day is required.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def daily() -> Dict[str, Any]:
    return {"type": "daily"}


def parse(spec: str) -> Dict[str, Any]:
    """Parse a ``--every`` value into a schedule dict.

    Accepts ``daily``/``everyday``, a comma list of weekday names
    (``mon,wed,fri``), or an ``N/week`` / ``Nx/week`` count.
    """
    spec = spec.strip().lower()
    if spec in ("", "daily", "day", "everyday", "every day"):
        return daily()

    # N/week style
    normalized = spec.replace("x", "").replace(" per ", "/").replace(" ", "")
    if "/week" in normalized or normalized.endswith("/wk"):
        head = normalized.split("/")[0]
        if head.isdigit():
            count = int(head)
            if not 1 <= count <= 7:
                raise ValueError("times-per-week count must be between 1 and 7")
            return {"type": "times_per_week", "count": count}

    # weekday list
    parts = [p.strip()[:3] for p in spec.split(",") if p.strip()]
    if parts and all(p in WEEKDAYS for p in parts):
        days = sorted({WEEKDAYS.index(p) for p in parts})
        return {"type": "weekly", "days": days}

    raise ValueError(
        f"could not parse schedule {spec!r} "
        "(use 'daily', weekdays like 'mon,wed,fri', or 'N/week')"
    )


def label(sched: Dict[str, Any]) -> str:
    """Human-readable description of a schedule."""
    kind = sched.get("type", "daily")
    if kind == "daily":
        return "daily"
    if kind == "weekly":
        days = sched.get("days", [])
        if not days:
            return "weekly"
        return ", ".join(WEEKDAYS[d].capitalize() for d in days)
    if kind == "times_per_week":
        return f"{sched.get('count', 1)}x / week"
    return kind


def is_due(sched: Dict[str, Any], day: date) -> bool:
    """Whether the habit is expected on ``day``.

    ``times_per_week`` has no specific required day, so every day is a valid
    opportunity and this returns ``True``.
    """
    kind = sched.get("type", "daily")
    if kind == "weekly":
        return day.weekday() in sched.get("days", [])
    return True  # daily and times_per_week are due any day


def due_days(sched: Dict[str, Any], start: date, end: date) -> List[date]:
    """All due days in the inclusive range ``[start, end]``."""
    from datetime import timedelta

    if end < start:
        return []
    out = []
    cur = start
    while cur <= end:
        if is_due(sched, cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out
