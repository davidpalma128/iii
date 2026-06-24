# habits

A fast, local-first habit tracker for your terminal. No accounts, no cloud, no
dependencies — just a single command and a plain-JSON file you fully own.

```
$ habits add exercise
$ habits done exercise
✔ exercise on 2026-06-24 — streak: 3 day(s)

$ habits list
  habit     streak   30d
  --------  ------  ----
✔ exercise     3d   43%
  read         0d   20%
```

## Why

Most habit apps want a login, a subscription, and your data on their servers.
`habits` keeps everything in a single human-readable file
(`~/.local/share/habits/habits.json` by default) that you can edit, grep,
back up, or sync however you like. It's a stdlib-only Python CLI, so it runs
anywhere Python 3.9+ does.

## Install

```bash
pip install -e .        # from a clone of this repo
```

This puts a `habits` command on your `PATH`.

## Usage

| Command | What it does |
|---------|--------------|
| `habits add <name>` | Create a new habit |
| `habits done <name> [--date D]` | Mark it complete (today, `yesterday`, or `YYYY-MM-DD`) |
| `habits undo <name> [--date D]` | Clear a check-in |
| `habits list` | All habits with current streak and 30-day completion |
| `habits stats <name> [--weeks N]` | Detailed stats plus a contribution heatmap |
| `habits remove <name>` | Delete a habit |

Aliases: `check` = `done`, `uncheck` = `undo`, `ls` = `list`, `rm` = `remove`.

### The heatmap

`habits stats` renders a GitHub-style grid of the trailing weeks:

```
$ habits stats exercise --weeks 6
current streak:  3 day(s)
longest streak:  3 day(s)
last 30 days:    10%

Mon ·····█
Tue ·····█
Wed ·····█
Thu ·····
Fri ·····
Sat ·····
Sun ·····
```

`█` = completed, `·` = missed, blank = a future day in the current week.

### Streak rules

A streak counts consecutive completed days and stays alive until you miss a
*full* day — so checking in yesterday but not yet today still keeps your streak.

## Data file

Resolution order:

1. `HABITS_FILE` environment variable (full path)
2. `$XDG_DATA_HOME/habits/habits.json`
3. `~/.local/share/habits/habits.json`

Override per-invocation with `habits --file ./my-habits.json list`. Writes are
atomic (write-to-temp then rename), so an interrupted run won't corrupt the file.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The domain logic in `src/habits/core.py` is pure (no I/O, no `date.today()`),
which keeps the test suite deterministic.

## License

MIT — see [LICENSE](LICENSE).
