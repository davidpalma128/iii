"""GitHub-style contribution heatmap rendering."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from . import schedule
from .core import entry_dates
from .render import Palette

_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
_WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render(
    entries: Dict[str, Any],
    sched: Dict[str, Any],
    today: date,
    palette: Palette,
    weeks: int = 15,
) -> str:
    """Render the trailing ``weeks`` as a weekday-by-week grid.

    Glyphs: ``█`` done (green), ``·`` a missed *due* day (dim), and a blank for
    non-due days and future days in the current week.
    """
    done = entry_dates(entries)
    # Anchor the right edge on the Sunday that ends this week.
    end = today + timedelta(days=(6 - today.weekday()))
    start = end - timedelta(weeks=weeks - 1, days=6)

    # --- month header: label the first week of each new month, but only when
    # there's room so adjacent labels don't mash together ("ApMay").
    month_row = [" "] * weeks
    last_month = None
    label_end = -1  # last column occupied by a previously-written label
    for w in range(weeks):
        col_month = (start + timedelta(weeks=w)).month
        if col_month != last_month:
            last_month = col_month
            name = _MONTHS[col_month - 1]
            if w > label_end and w + len(name) <= weeks:
                for i, ch in enumerate(name):
                    month_row[w + i] = ch
                label_end = w + len(name)
    header = "    " + "".join(month_row)

    rows: List[str] = []
    for weekday in range(7):
        cells = []
        for w in range(weeks):
            cell_day = start + timedelta(weeks=w, days=weekday)
            if cell_day > today:
                cells.append(" ")
            elif cell_day in done:
                cells.append(palette.green("█"))
            elif schedule.is_due(sched, cell_day):
                cells.append(palette.dim("·"))
            else:
                cells.append(" ")
        rows.append(f"{_WEEKDAY_LABELS[weekday]} " + "".join(cells))

    return header + "\n" + "\n".join(rows)
