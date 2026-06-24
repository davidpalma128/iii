"""Command-line interface for the habit tracker."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import __version__, core, storage


def _today() -> date:
    return date.today()


def _resolve_day(value: Optional[str], today: date) -> date:
    """Turn a user-supplied ``--date`` (ISO, 'today', or 'yesterday') into a date."""
    if value is None or value == "today":
        return today
    if value == "yesterday":
        return today - timedelta(days=1)
    try:
        return core.parse_day(value)
    except ValueError:
        raise SystemExit(f"error: invalid date {value!r} (use YYYY-MM-DD)")


def _require_habit(store: Dict[str, Any], name: str) -> None:
    if name not in store["habits"]:
        raise SystemExit(f"error: no such habit {name!r} (try `habits add {name}`)")


# --- commands ---------------------------------------------------------------


def cmd_add(args: argparse.Namespace, store: Dict[str, Any], today: date) -> bool:
    if core.add_habit(store, args.name, today):
        print(f"added habit {args.name!r}")
        return True
    print(f"habit {args.name!r} already exists")
    return False


def cmd_remove(args: argparse.Namespace, store: Dict[str, Any], today: date) -> bool:
    if core.remove_habit(store, args.name):
        print(f"removed habit {args.name!r}")
        return True
    print(f"no such habit {args.name!r}")
    return False


def cmd_done(args: argparse.Namespace, store: Dict[str, Any], today: date) -> bool:
    _require_habit(store, args.name)
    day = _resolve_day(args.date, today)
    if core.mark(store, args.name, day):
        streak = core.current_streak(store["habits"][args.name]["log"], today)
        print(f"✔ {args.name} on {day.isoformat()} — streak: {streak} day(s)")
        return True
    print(f"{args.name} was already marked on {day.isoformat()}")
    return False


def cmd_undo(args: argparse.Namespace, store: Dict[str, Any], today: date) -> bool:
    _require_habit(store, args.name)
    day = _resolve_day(args.date, today)
    if core.unmark(store, args.name, day):
        print(f"cleared {args.name} on {day.isoformat()}")
        return True
    print(f"{args.name} was not marked on {day.isoformat()}")
    return False


def cmd_list(args: argparse.Namespace, store: Dict[str, Any], today: date) -> bool:
    habits = store["habits"]
    if not habits:
        print("no habits yet — add one with `habits add <name>`")
        return False

    rows: List[Sequence[str]] = []
    for name in sorted(habits):
        log = habits[name]["log"]
        done_today = "✔" if today.isoformat() in log else " "
        streak = core.current_streak(log, today)
        rate = core.completion_rate(log, today, 30)
        rows.append((done_today, name, f"{streak}d", f"{rate * 100:3.0f}%"))

    name_w = max(len(r[1]) for r in rows)
    print(f"  {'habit':<{name_w}}  streak   30d")
    print(f"  {'-' * name_w}  ------  ----")
    for done, name, streak, rate in rows:
        print(f"{done} {name:<{name_w}}  {streak:>5}  {rate:>4}")
    return True


def cmd_stats(args: argparse.Namespace, store: Dict[str, Any], today: date) -> bool:
    _require_habit(store, args.name)
    habit = store["habits"][args.name]
    log = habit["log"]
    print(f"habit:           {args.name}")
    print(f"created:         {habit.get('created', '?')}")
    print(f"total check-ins: {len(log)}")
    print(f"current streak:  {core.current_streak(log, today)} day(s)")
    print(f"longest streak:  {core.longest_streak(log)} day(s)")
    print(f"last 7 days:     {core.completion_rate(log, today, 7) * 100:.0f}%")
    print(f"last 30 days:    {core.completion_rate(log, today, 30) * 100:.0f}%")
    print()
    print(core.heatmap(log, today, weeks=args.weeks))
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="habits",
        description="A fast, local-first habit tracker for your terminal.",
    )
    parser.add_argument("--version", action="version", version=f"habits {__version__}")
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="path to the habits data file (overrides HABITS_FILE)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="create a new habit")
    p_add.add_argument("name")
    p_add.set_defaults(func=cmd_add)

    p_rm = sub.add_parser("remove", aliases=["rm"], help="delete a habit")
    p_rm.add_argument("name")
    p_rm.set_defaults(func=cmd_remove)

    p_done = sub.add_parser("done", aliases=["check"], help="mark a habit complete")
    p_done.add_argument("name")
    p_done.add_argument("--date", help="ISO date, 'today', or 'yesterday'")
    p_done.set_defaults(func=cmd_done)

    p_undo = sub.add_parser("undo", aliases=["uncheck"], help="clear a check-in")
    p_undo.add_argument("name")
    p_undo.add_argument("--date", help="ISO date, 'today', or 'yesterday'")
    p_undo.set_defaults(func=cmd_undo)

    p_list = sub.add_parser("list", aliases=["ls"], help="list habits and streaks")
    p_list.set_defaults(func=cmd_list)

    p_stats = sub.add_parser("stats", help="show detailed stats and a heatmap")
    p_stats.add_argument("name")
    p_stats.add_argument(
        "--weeks", type=int, default=15, help="heatmap width in weeks (default 15)"
    )
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    path = args.file.expanduser() if args.file else storage.default_path()
    store = storage.load(path)
    today = _today()

    changed = args.func(args, store, today)
    if changed:
        storage.save(path, store)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
