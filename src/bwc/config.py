"""Environment-driven settings for the BWC app."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

CHAPTER_NAME = "The Business Wealth Collective"

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_NAME = "bwc.sqlite3"
SECRET_FILE_NAME = ".secret_key"


@dataclass
class Settings:
    db_path: Path
    secret_key: str
    cookie_secure: bool


def resolve_db_path(db_path=None) -> Path:
    if db_path is not None:
        return Path(db_path)
    env = os.environ.get("BWC_DB")
    if env:
        return Path(env)
    return DEFAULT_DATA_DIR / DEFAULT_DB_NAME


def resolve_secret_key(secret_key=None, db_path: Path = None) -> str:
    """Explicit arg > BWC_SECRET_KEY env > persisted dev key next to the DB."""
    if secret_key:
        return secret_key
    env = os.environ.get("BWC_SECRET_KEY")
    if env:
        return env
    secret_file = (db_path.parent if db_path else DEFAULT_DATA_DIR) / SECRET_FILE_NAME
    if secret_file.exists():
        return secret_file.read_text().strip()
    key = secrets.token_urlsafe(32)
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(key)
    try:
        os.chmod(secret_file, 0o600)
    except OSError:
        pass
    return key


def load_settings(db_path=None, secret_key=None, cookie_secure=None) -> Settings:
    resolved_db = resolve_db_path(db_path)
    if cookie_secure is None:
        cookie_secure = os.environ.get("BWC_COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    return Settings(
        db_path=resolved_db,
        secret_key=resolve_secret_key(secret_key, resolved_db),
        cookie_secure=cookie_secure,
    )
