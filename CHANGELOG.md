# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0]

### Added
- **Schedules**: habits can be `daily`, specific weekdays (`mon,wed,fri`), or
  *N times per week* (`3/week`) via `--every`.
- **Schedule-aware streaks & completion rates** — weekday habits only count due
  days; N-per-week habits are measured in weeks.
- `today` command showing what's due and what's done.
- `log` command for recent check-in history.
- `rename`, `archive`, and `unarchive` commands.
- `export` (JSON/CSV) and `import` (merge) commands.
- `path` command to print the active data file location.
- Per-check-in `--note`, plus habit `--tag` and `--desc` metadata.
- `--json` output on every read command for scripting.
- TTY/`NO_COLOR`/`FORCE_COLOR`-aware colorized output and `--color` flag.
- Heatmap now shows month labels and colors completed vs. missed due days.
- Automatic v1 → v2 data-file migration on load.

### Changed
- Data schema upgraded to v2: habits now store `schedule`, `tags`,
  `description`, `archived`, and an `entries` map (with optional notes) instead
  of a flat `log` list.

## [0.1.0]

### Added
- Initial release: `add`, `done`, `undo`, `list`, `stats`, `remove`.
- Current and longest streaks, rolling completion rates, contribution heatmap.
- Plain-JSON local storage with atomic writes.
