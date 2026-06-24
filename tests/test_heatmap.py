from datetime import date

from habits import heatmap, schedule
from habits.render import Palette

PLAIN = Palette(False)  # no ANSI codes, easy to assert on


def test_grid_shape_and_markers():
    today = date(2026, 6, 24)  # Wednesday
    entries = {"2026-06-24": {}}
    grid = heatmap.render(entries, schedule.daily(), today, PLAIN, weeks=4)
    lines = grid.splitlines()
    # 1 month header + 7 weekday rows
    assert len(lines) == 8
    assert lines[1].startswith("Mon")
    assert "█" in grid  # today rendered as done


def test_weekly_schedule_blanks_non_due_days():
    today = date(2026, 6, 26)  # Friday
    sched = schedule.parse("mon,wed,fri")
    grid = heatmap.render({}, sched, today, PLAIN, weeks=3)
    rows = {line[:3]: line for line in grid.splitlines()[1:]}
    # Tue/Thu/Sat/Sun are never due -> only spaces after the label
    assert rows["Tue"][4:].strip() == ""
    # Mon is a due day in the past -> at least one missed marker
    assert "·" in rows["Mon"]


def test_future_days_blank():
    today = date(2026, 6, 24)  # Wednesday
    grid = heatmap.render({}, schedule.daily(), today, PLAIN, weeks=2)
    rows = grid.splitlines()[1:]
    # Sunday of the current week is in the future -> trailing blank, no marker
    sun = rows[6]
    assert sun.rstrip().endswith("Sun") or sun[-1] == " "


def test_month_labels_do_not_collide():
    today = date(2026, 6, 30)
    grid = heatmap.render({}, schedule.daily(), today, PLAIN, weeks=16)
    header = grid.splitlines()[0]
    # adjacent month names should be space-separated, never mashed ("ApMay")
    assert "ApMay" not in header and "MayJun" not in header
