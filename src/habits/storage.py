"""Plain-JSON persistence for habits.

The data file is intentionally human-readable so you can edit, grep, version,
or sync it however you like. Location resolution order:

1. ``HABITS_FILE`` environment variable (full path to the JSON file)
2. ``$XDG_DATA_HOME/habits/habits.json``
3. ``~/.local/share/habits/habits.json``
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

SCHEMA_VERSION = 1


def default_path() -> Path:
    """Return the resolved path to the habits data file."""
    env = os.environ.get("HABITS_FILE")
    if env:
        return Path(env).expanduser()

    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "habits" / "habits.json"


def empty_store() -> Dict[str, Any]:
    """Return a fresh, empty data structure."""
    return {"version": SCHEMA_VERSION, "habits": {}}


def load(path: Path) -> Dict[str, Any]:
    """Load the store from ``path``, returning an empty store if it is absent."""
    if not path.exists():
        return empty_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover - defensive
        raise SystemExit(f"error: could not read habits file at {path}: {exc}")

    if not isinstance(data, dict) or "habits" not in data:
        raise SystemExit(f"error: {path} is not a valid habits file")
    data.setdefault("version", SCHEMA_VERSION)
    data.setdefault("habits", {})
    return data


def save(path: Path, data: Dict[str, Any]) -> None:
    """Atomically write ``data`` to ``path`` as pretty-printed JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
