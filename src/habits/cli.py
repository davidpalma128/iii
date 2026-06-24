"""Command-line interface for the habit tracker."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import __version__, core, render, schedule, storage
from .heatmap import render as render_heatmap


# --- small helpers ----------------------------------------------------------


def _today() -> date:
    return date.today()


def _resolve_day(value: Optional[str], today: date) -> date:
    """Turn a user ``--date`` (ISO, 'today', 'yesterday') into a date."""
    if value is None or value == "today":
        return today
    if value == "yesterday":
        return today - timedelta(days=1)
    try:
        return core.parse_day(value)
    except ValueError:
        raise SystemExit(f"error: invalid date {value!r} (use YYYY-MM-DD)")


def _require(store: Dict[str, Any], name: str) -> Dict[str, Any]:
    if name not in store["habits"]:
        raise SystemExit(f"error: no such habit {name!r} (try `habits add {name}`)")
    return store["habits"][name]


def _emit(args: argparse.Namespace, human: str, payload: Any) -> None:
    """Print JSON when ``--json`` is set, otherwise the human string."""
    if getattr(args, "json", False):
        print(json.dumps(payload, default=str))
    elif human:
        print(human)


def _habit_summary(habit: Dict[str, Any], today: date) -> Dict[str, Any]:
    sched = habit["schedule"]
    entries = habit["entries"]
    return {
        "name": habit["name"],
        "schedule": schedule.label(sched),
        "tags": habit.get("tags", []),
        "archived": habit.get("archived", False),
        "done_today": today.isoformat() in entries,
        "due_today": schedule.is_due(sched, today),
        "current_streak": core.current_streak(entries, sched, today),
        "longest_streak": core.longest_streak(entries, sched, today),
        "rate_30d": round(core.completion_rate(entries, sched, today, 30), 4),
        "total": core.total_checkins(entries),
    }


# --- commands ---------------------------------------------------------------


def cmd_add(args, store, today, pal):
    try:
        sched = schedule.parse(args.every) if args.every else schedule.daily()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}")
    created = core.add_habit(
        store, args.name, today, sched=sched, tags=args.tag, description=args.desc or ""
    )
    if created:
        _emit(args, f"added {pal.bold(args.name)} ({schedule.label(sched)})",
              {"added": args.name, "schedule": schedule.label(sched)})
        return True
    _emit(args, f"habit {args.name!r} already exists", {"added": None})
    return False


def cmd_remove(args, store, today, pal):
    ok = core.remove_habit(store, args.name)
    _emit(args, f"removed {args.name!r}" if ok else f"no such habit {args.name!r}",
          {"removed": args.name if ok else None})
    return ok


def cmd_rename(args, store, today, pal):
    try:
        core.rename_habit(store, args.old, args.new)
    except KeyError:
        raise SystemExit(f"error: no such habit {args.old!r}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}")
    _emit(args, f"renamed {args.old!r} -> {args.new!r}",
          {"renamed": {"from": args.old, "to": args.new}})
    return True


def cmd_done(args, store, today, pal):
    _require(store, args.name)
    day = _resolve_day(args.date, today)
    changed = core.mark(store, args.name, day, note=args.note)
    habit = store["habits"][args.name]
    streak = core.current_streak(habit["entries"], habit["schedule"], today)
    if changed:
        msg = f"{pal.green('✔')} {pal.bold(args.name)} on {day.isoformat()} — streak: {pal.green(str(streak))} day(s)"
        if args.note:
            msg += f"\n  {pal.dim('note: ' + args.note)}"
    else:
        msg = f"{args.name} already marked on {day.isoformat()}"
    _emit(args, msg, {"name": args.name, "date": day.isoformat(), "streak": streak,
                      "changed": changed})
    return changed


def cmd_undo(args, store, today, pal):
    _require(store, args.name)
    day = _resolve_day(args.date, today)
    ok = core.unmark(store, args.name, day)
    _emit(args, f"cleared {args.name} on {day.isoformat()}" if ok
          else f"{args.name} was not marked on {day.isoformat()}",
          {"name": args.name, "date": day.isoformat(), "changed": ok})
    return ok


def _visible_habits(store, args):
    habits = list(store["habits"].values())
    if not getattr(args, "all", False):
        habits = [h for h in habits if not h.get("archived", False)]
    if getattr(args, "tag", None):
        want = args.tag.strip().lower()
        habits = [h for h in habits if want in h.get("tags", [])]
    return sorted(habits, key=lambda h: h["name"])


def cmd_list(args, store, today, pal):
    habits = _visible_habits(store, args)
    summaries = [_habit_summary(h, today) for h in habits]
    if args.json:
        print(json.dumps(summaries, default=str))
        return False
    if not summaries:
        print("no habits yet — add one with `habits add <name>`")
        return False

    name_w = max(len(s["name"]) for s in summaries)
    name_w = max(name_w, 5)
    print(f"  {'habit':<{name_w}}  {'schedule':<12}  streak   30d")
    print(f"  {'-' * name_w}  {'-' * 12}  ------  ----")
    for s in summaries:
        box = pal.green("✔") if s["done_today"] else (" " if s["due_today"] else pal.dim("·"))
        streak = f"{s['current_streak']}d"
        rate = s["rate_30d"] * 100
        rate_s = f"{rate:3.0f}%"
        if rate >= 80:
            rate_s = pal.green(rate_s)
        elif rate < 50:
            rate_s = pal.yellow(rate_s)
        print(f"{box} {s['name']:<{name_w}}  {s['schedule']:<12}  {streak:>5}  {rate_s:>4}")
    return False


def cmd_today(args, store, today, pal):
    habits = [h for h in _visible_habits(store, args)
              if schedule.is_due(h["schedule"], today)]
    rows = [{"name": h["name"],
             "done": today.isoformat() in h["entries"],
             "streak": core.current_streak(h["entries"], h["schedule"], today)}
            for h in habits]
    if args.json:
        print(json.dumps(rows, default=str))
        return False
    if not rows:
        print(f"nothing due today ({today.isoformat()}) 🎉")
        return False
    done = sum(1 for r in rows if r["done"])
    print(pal.bold(f"Today — {today.isoformat()}  ({done}/{len(rows)} done)"))
    for r in rows:
        box = pal.green("[✔]") if r["done"] else "[ ]"
        streak = pal.dim(f"  🔥 {r['streak']}") if r["streak"] else ""
        print(f"  {box} {r['name']}{streak}")
    return False


def cmd_stats(args, store, today, pal):
    habit = _require(store, args.name)
    entries, sched = habit["entries"], habit["schedule"]
    payload = _habit_summary(habit, today)
    payload.update({
        "created": habit.get("created"),
        "description": habit.get("description", ""),
        "rate_7d": round(core.completion_rate(entries, sched, today, 7), 4),
    })
    if args.json:
        print(json.dumps(payload, default=str))
        return False

    print(f"{pal.bold(args.name)}  {pal.dim('(' + schedule.label(sched) + ')')}")
    if habit.get("description"):
        print(f"  {habit['description']}")
    if habit.get("tags"):
        print(f"  tags: {', '.join(habit['tags'])}")
    print(f"  created:        {habit.get('created', '?')}")
    print(f"  total check-ins:{core.total_checkins(entries):>4}")
    print(f"  current streak: {pal.green(str(payload['current_streak']))} period(s)")
    print(f"  longest streak: {payload['longest_streak']} period(s)")
    print(f"  last 7 days:    {payload['rate_7d'] * 100:.0f}%")
    print(f"  last 30 days:   {payload['rate_30d'] * 100:.0f}%")
    print()
    print(render_heatmap(entries, sched, today, pal, weeks=args.weeks))
    return False


def cmd_log(args, store, today, pal):
    names = [args.name] if args.name else None
    if names:
        _require(store, args.name)
    rows: List[Dict[str, Any]] = []
    for habit in store["habits"].values():
        if names and habit["name"] not in names:
            continue
        for iso, meta in habit["entries"].items():
            rows.append({"date": iso, "name": habit["name"],
                         "note": meta.get("note", "")})
    rows.sort(key=lambda r: (r["date"], r["name"]), reverse=True)
    rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, default=str))
        return False
    if not rows:
        print("no check-ins yet")
        return False
    for r in rows:
        line = f"  {pal.dim(r['date'])}  {r['name']}"
        if r["note"]:
            line += f"  {pal.dim('— ' + r['note'])}"
        print(line)
    return False


def cmd_archive(args, store, today, pal):
    _require(store, args.name)
    changed = core.set_archived(store, args.name, True)
    _emit(args, f"archived {args.name!r}" if changed else f"{args.name!r} already archived",
          {"archived": args.name, "changed": changed})
    return changed


def cmd_unarchive(args, store, today, pal):
    _require(store, args.name)
    changed = core.set_archived(store, args.name, False)
    _emit(args, f"unarchived {args.name!r}" if changed else f"{args.name!r} not archived",
          {"unarchived": args.name, "changed": changed})
    return changed


def cmd_export(args, store, today, pal):
    if args.format == "json":
        print(json.dumps(store, indent=2, sort_keys=True))
        return False
    # CSV: one row per check-in
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["habit", "date", "note", "schedule", "tags"])
    for habit in sorted(store["habits"].values(), key=lambda h: h["name"]):
        sched = schedule.label(habit["schedule"])
        tags = ";".join(habit.get("tags", []))
        for iso in sorted(habit["entries"]):
            writer.writerow([habit["name"], iso,
                             habit["entries"][iso].get("note", ""), sched, tags])
    sys.stdout.write(buf.getvalue())
    return False


def cmd_import(args, store, today, pal):
    path = Path(args.source).expanduser()
    if not path.exists():
        raise SystemExit(f"error: no such file {path}")
    try:
        incoming = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid JSON: {exc}")
    incoming = storage._migrate(incoming if isinstance(incoming, dict)
                                else {"habits": {}})
    added = merged = 0
    for name, habit in incoming.get("habits", {}).items():
        if name in store["habits"]:
            store["habits"][name]["entries"].update(habit.get("entries", {}))
            merged += 1
        else:
            store["habits"][name] = habit
            added += 1
    _emit(args, f"imported {added} new, merged {merged} existing",
          {"added": added, "merged": merged})
    return added + merged > 0


def cmd_path(args, store, today, pal):
    print(args._datafile)
    return False


# --- parser -----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="habits",
        description="A fast, local-first habit tracker for your terminal.",
    )
    p.add_argument("--version", action="version", version=f"habits {__version__}")
    p.add_argument("--file", type=Path, default=None,
                   help="path to the habits data file (overrides HABITS_FILE)")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    p.add_argument("--color", choices=["auto", "always", "never"], default=None,
                   help="control ANSI color (default: auto)")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="create a new habit")
    a.add_argument("name")
    a.add_argument("--every", help="schedule: 'daily', 'mon,wed,fri', or 'N/week'")
    a.add_argument("--tag", action="append", help="tag (repeatable)")
    a.add_argument("--desc", help="description")
    a.set_defaults(func=cmd_add)

    r = sub.add_parser("remove", aliases=["rm"], help="delete a habit")
    r.add_argument("name")
    r.set_defaults(func=cmd_remove)

    rn = sub.add_parser("rename", help="rename a habit (keeps history)")
    rn.add_argument("old")
    rn.add_argument("new")
    rn.set_defaults(func=cmd_rename)

    d = sub.add_parser("done", aliases=["check"], help="mark a habit complete")
    d.add_argument("name")
    d.add_argument("--date", help="ISO date, 'today', or 'yesterday'")
    d.add_argument("--note", help="optional note for this check-in")
    d.set_defaults(func=cmd_done)

    u = sub.add_parser("undo", aliases=["uncheck"], help="clear a check-in")
    u.add_argument("name")
    u.add_argument("--date", help="ISO date, 'today', or 'yesterday'")
    u.set_defaults(func=cmd_undo)

    ls = sub.add_parser("list", aliases=["ls"], help="list habits and streaks")
    ls.add_argument("--all", action="store_true", help="include archived habits")
    ls.add_argument("--tag", help="filter by tag")
    ls.set_defaults(func=cmd_list)

    t = sub.add_parser("today", help="show what's due today")
    t.add_argument("--all", action="store_true")
    t.add_argument("--tag", help="filter by tag")
    t.set_defaults(func=cmd_today)

    s = sub.add_parser("stats", help="detailed stats and a heatmap")
    s.add_argument("name")
    s.add_argument("--weeks", type=int, default=15, help="heatmap width (default 15)")
    s.set_defaults(func=cmd_stats)

    lg = sub.add_parser("log", help="recent check-in history")
    lg.add_argument("name", nargs="?", help="limit to one habit")
    lg.add_argument("--limit", type=int, default=20, help="max rows (default 20)")
    lg.set_defaults(func=cmd_log)

    ar = sub.add_parser("archive", help="hide a habit without deleting it")
    ar.add_argument("name")
    ar.set_defaults(func=cmd_archive)

    un = sub.add_parser("unarchive", help="restore an archived habit")
    un.add_argument("name")
    un.set_defaults(func=cmd_unarchive)

    ex = sub.add_parser("export", help="export all data to stdout")
    ex.add_argument("--format", choices=["json", "csv"], default="json")
    ex.set_defaults(func=cmd_export)

    im = sub.add_parser("import", help="merge habits from a JSON export")
    im.add_argument("source", help="path to a JSON export to merge in")
    im.set_defaults(func=cmd_import)

    pa = sub.add_parser("path", help="print the data file path")
    pa.set_defaults(func=cmd_path)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    path = args.file.expanduser() if args.file else storage.default_path()
    store = storage.load(path)
    args._datafile = str(path)
    today = _today()

    color_mode = args.color or store.get("config", {}).get("color", "auto")
    if args.json:
        color_mode = "never"
    pal = render.resolve(color_mode)

    changed = args.func(args, store, today, pal)
    if changed:
        storage.save(path, store)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
