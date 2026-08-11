"""Dollar-string parsing and cents formatting. All amounts are integer cents."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_dollars(text: str) -> int:
    """'1,250.50' / '$300' -> cents. Raises ValueError on bad or non-positive input."""
    cleaned = (text or "").strip().lstrip("$").replace(",", "")
    if not cleaned:
        raise ValueError("Amount is required")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Not a valid dollar amount: {text!r}")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Amounts can have at most two decimal places")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    return int(amount * 100)


def format_cents(cents) -> str:
    cents = int(cents or 0)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"
