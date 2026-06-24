"""Terminal styling helpers.

Color is enabled only when the output is a TTY and ``NO_COLOR`` is unset,
unless explicitly forced on/off. We keep this tiny and dependency-free so the
tool stays stdlib-only.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

_CODES = {
    "reset": "0",
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "gray": "90",
    "bright_green": "92",
    "bright_yellow": "93",
}


class Palette:
    """Resolves whether to emit ANSI codes and renders styled strings."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def style(self, text: str, *names: str) -> str:
        if not self.enabled or not names:
            return text
        prefix = "".join(f"\033[{_CODES[n]}m" for n in names if n in _CODES)
        return f"{prefix}{text}\033[0m"

    # convenience shortcuts -------------------------------------------------
    def green(self, t: str) -> str:
        return self.style(t, "green")

    def red(self, t: str) -> str:
        return self.style(t, "red")

    def yellow(self, t: str) -> str:
        return self.style(t, "yellow")

    def dim(self, t: str) -> str:
        return self.style(t, "dim")

    def bold(self, t: str) -> str:
        return self.style(t, "bold")

    def cyan(self, t: str) -> str:
        return self.style(t, "cyan")


def resolve(mode: str = "auto", stream: Optional[object] = None) -> Palette:
    """Build a :class:`Palette` from a mode of ``auto`` / ``always`` / ``never``."""
    stream = stream if stream is not None else sys.stdout
    if mode == "always":
        return Palette(True)
    if mode == "never":
        return Palette(False)
    # auto
    if os.environ.get("NO_COLOR") is not None:
        return Palette(False)
    if os.environ.get("FORCE_COLOR") is not None:
        return Palette(True)
    return Palette(bool(getattr(stream, "isatty", lambda: False)()))
