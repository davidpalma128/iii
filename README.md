# iii

This repo contains two apps:

- **[`habits`](#habits)** — a local-first terminal habit tracker (`src/habits/`)
- **[`bwc`](#bwc--the-business-wealth-collective)** — a mobile-friendly web app for
  tracking a BNI-style networking chapter (`src/bwc/`)

## bwc — The Business Wealth Collective

A chapter tracker for a single networking group: referrals with a status
lifecycle and update thread, one-to-one meetings, TYFCB (Thank You For Closed
Business) dollars, a member directory with per-member scheduling links, and a
chapter dashboard with a leaderboard.

Built with FastAPI + Jinja2 + SQLite, server-rendered and mobile-first — members
open it on their phones at the weekly meeting.

### Running

```bash
pip install -e ".[dev]"
bwc init-db
bwc create-admin --email you@example.com --name "Your Name"   # prompts for password
bwc serve                       # or: uvicorn bwc.asgi:app --reload
```

Then log in at http://127.0.0.1:8000. The admin adds members (with temporary
passwords) from the **Admin** tab; there is no self-signup since it's a closed
group. Members edit their own profile — including their scheduling link (e.g.
Calendly), which shows as a "Book a 1-to-1" button on their profile.

### Configuration

| Env var | Meaning | Default |
| --- | --- | --- |
| `BWC_DB` | SQLite database path | `data/bwc.sqlite3` |
| `BWC_SECRET_KEY` | Cookie-signing secret (set this in production) | generated into `data/.secret_key` |
| `BWC_COOKIE_SECURE` | Set `1` when serving over HTTPS | off |

Data lives in a single SQLite file — back it up by copying `data/bwc.sqlite3`.

## habits

A fast, local-first habit tracker for your terminal. No accounts, no cloud, no
dependencies — just a single command and a plain-JSON file you fully own.

```
$ habits add exercise --every mon,wed,fri --tag health
$ habits done exercise --note "5k run"
✔ exercise on 2026-06-24 — streak: 8 day(s)
  note: 5k run

$ habits today
Today — 2026-06-24  (3/3 done)
  [✔] exercise  🔥 8
  [✔] read      🔥 15
  [✔] water     🔥 1
```

## Why

Most habit apps want a login, a subscription, and your data on their servers.
`habits` keeps everything in a single human-readable JSON file you can edit,
grep, back up, or sync however you like. It's a **stdlib-only** Python CLI, so
it runs anywhere Python 3.9+ does — and it's genuinely useful day to day:

- **Schedules** — daily, specific weekdays (`mon,wed,fri`), or *N times a week*
- **Schedule-aware streaks** — a Mon/Wed/Fri habit isn't broken by skipping
  Tuesday, and an *N-per-week* habit is measured in weeks
- **`today` view** — see exactly what's due and what's left
- **Tags, descriptions, notes** — organize habits and annotate check-ins
- **Archive** habits without losing history
- **Contribution heatmap** with month labels and color
- **JSON output** (`--json`) on every read command for scripting
- **CSV/JSON export & import** — your data is never trapped
- **Automatic schema migration** — older data files upgrade on load

## Install

```bash
pip install -e .        # from a clone of this repo
```

This puts a `habits` command on your `PATH`.

## Commands

| Command | What it does |
|---------|--------------|
| `add <name> [--every S] [--tag T]... [--desc D]` | Create a habit |
| `done <name> [--date D] [--note N]` | Mark complete (today, `yesterday`, or `YYYY-MM-DD`) |
| `undo <name> [--date D]` | Clear a check-in |
| `today [--tag T] [--all]` | What's due today, and what's done |
| `list [--tag T] [--all]` | All habits with schedule, streak, 30-day rate |
| `stats <name> [--weeks N]` | Detailed stats plus a contribution heatmap |
| `log [name] [--limit N]` | Recent check-in history |
| `rename <old> <new>` | Rename a habit (keeps history) |
| `archive <name>` / `unarchive <name>` | Hide / restore a habit |
| `remove <name>` | Delete a habit |
| `export [--format json\|csv]` | Dump all data to stdout |
| `import <file>` | Merge habits from a JSON export |
| `path` | Print the data file location |

Aliases: `check`=`done`, `uncheck`=`undo`, `ls`=`list`, `rm`=`remove`.

Global flags: `--file PATH`, `--json`, `--color auto|always|never`, `--version`.

## Schedules

Pass `--every` when adding a habit:

| Value | Meaning |
|-------|---------|
| `daily` (default) | Every day |
| `mon,wed,fri` | Only those weekdays |
| `3/week`, `5x/week`, `2 per week` | Any N days each week |

Schedules shape how streaks and completion rates are computed:

- **Weekday habits** only count *due* days. Skipping a non-due day never breaks
  a streak, and today's due day stays "pending" until the day fully passes.
- **N-per-week habits** are measured in weeks: a streak is consecutive weeks
  where you hit the target, and the current week won't break your streak until
  it's over.

## The heatmap

`habits stats` renders a GitHub-style grid of the trailing weeks, with month
labels across the top:

```
$ habits stats exercise --weeks 16
exercise  (Mon, Wed, Fri)
  current streak: 8 period(s)
  longest streak: 8 period(s)
  last 30 days:   62%

    Mar Apr May Jun
Mon ·······███
Wed ·······███
Fri ·······██
...
```

`█` = completed (green), `·` = a missed *due* day (dim), blank = a non-due or
future day. Color follows `--color`, the `NO_COLOR`/`FORCE_COLOR` conventions,
and whether stdout is a TTY.

## Scripting with `--json`

Every read command emits structured JSON with `--json`, so you can pipe into
`jq` or build dashboards:

```bash
$ habits --json today | jq '.[] | select(.done | not) | .name'
"water"

$ habits --json list | jq 'max_by(.current_streak).name'
"read"
```

## Data file

Resolution order:

1. `HABITS_FILE` environment variable (full path)
2. `$XDG_DATA_HOME/habits/habits.json`
3. `~/.local/share/habits/habits.json`

Override per-invocation with `habits --file ./my-habits.json list`, or print the
active path with `habits path`. Writes are atomic (temp file + rename), so an
interrupted run won't corrupt your data. Older files are migrated to the current
schema automatically on load.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The domain logic in `src/habits/core.py` and `src/habits/schedule.py` is pure
(no I/O, no `date.today()`), which keeps the 50+ test suite deterministic.

```
src/habits/
  __init__.py    version
  storage.py     load/save, schema migration, config, path resolution
  schedule.py    schedule parsing + "is it due?" logic
  core.py        streaks, longest streaks, completion rates (schedule-aware)
  heatmap.py     contribution-grid rendering
  render.py      TTY/NO_COLOR-aware ANSI styling
  cli.py         argparse command surface
```

## License

MIT — see [LICENSE](LICENSE).
