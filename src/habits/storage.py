"""Plain-JSON persistence, schema migration, and config.

The data file is intentionally human-readable so you can edit, grep, version,
or sync it however you like. Location resolution order:

1. ``HABITS_FILE`` environment variable (full path to the JSON file)
2. ``$XDG_DATA_HOME/habits/habits.json``
3. ``~/.local/share/habits/habits.json``

Schema history
--------------
* **v1** — each habit had a ``log`` list of ISO date strings.
* **v2** — habits gain ``schedule``, ``tags``, ``description``, ``archived``,
  and a ``entries`` map of ``{date: {"note": str}}`` (notes optional). A
  top-level ``config`` block holds defaults. v1 files migrate automatically on
  load.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from . import schedule

SCHEMA_VERSION = 2

DEFAULT_CONFIG = {
    "color": "auto",  # auto | always | never
}


def default_path() -> Path:
    """Return the resolved path to the habits data file."""
    env = os.environ.get("HABITS_FILE")
    if env:
        return Path(env).expanduser()

    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "habits" / "habits.json"


def empty_store() -> Dict[str, Any]:
    """Return a fresh, empty data structure at the current schema version."""
    return {"version": SCHEMA_VERSION, "config": dict(DEFAULT_CONFIG), "habits": {}}


def new_habit(name: str, created: str, sched: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Construct a v2 habit record."""
    return {
        "name": name,
        "created": created,
        "description": "",
        "tags": [],
        "schedule": sched or schedule.daily(),
        "archived": False,
        "entries": {},
    }


def _migrate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Bring an older store up to the current schema version in place."""
    version = data.get("version", 1)

    if version < 2:
        for habit in data.get("habits", {}).values():
            log = habit.pop("log", [])
            habit.setdefault("entries", {iso: {} for iso in log})
            habit.setdefault("description", "")
            habit.setdefault("tags", [])
            habit.setdefault("schedule", schedule.daily())
            habit.setdefault("archived", False)
        data["version"] = 2

    data.setdefault("config", dict(DEFAULT_CONFIG))
    for key, value in DEFAULT_CONFIG.items():
        data["config"].setdefault(key, value)
    return data


def load(path: Path) -> Dict[str, Any]:
    """Load (and migrate) the store from ``path``; empty store if absent."""
    if not path.exists():
        return empty_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover - defensive
        raise SystemExit(f"error: could not read habits file at {path}: {exc}")

    if not isinstance(data, dict) or "habits" not in data:
        raise SystemExit(f"error: {path} is not a valid habits file")
    data.setdefault("habits", {})
    return _migrate(data)


def save(path: Path, data: Dict[str, Any]) -> None:
    """Atomically write ``data`` to ``path`` as pretty-printed JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
