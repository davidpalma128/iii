"""Password hashing and signed-cookie helpers (sessions + flash messages)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeSerializer, URLSafeTimedSerializer

PBKDF2_ITERATIONS = 600_000
SESSION_COOKIE = "bwc_session"
FLASH_COOKIE = "bwc_flash"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


class CookieSigner:
    """Signs/reads the session and flash cookies with the app secret."""

    def __init__(self, secret_key: str):
        self._session = URLSafeTimedSerializer(secret_key, salt="bwc-session")
        self._flash = URLSafeSerializer(secret_key, salt="bwc-flash")

    def make_session(self, member_id: int) -> str:
        return self._session.dumps({"uid": member_id})

    def read_session(self, token: str):
        """Return the member id, or None for a missing/invalid/expired token."""
        if not token:
            return None
        try:
            data = self._session.loads(token, max_age=SESSION_MAX_AGE)
            return int(data["uid"])
        except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
            return None

    def make_flash(self, message: str, category: str = "success") -> str:
        return self._flash.dumps({"m": message, "c": category})

    def read_flash(self, token: str):
        if not token:
            return None
        try:
            data = self._flash.loads(token)
            return {"message": data["m"], "category": data.get("c", "success")}
        except (BadSignature, KeyError, TypeError):
            return None
