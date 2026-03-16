from __future__ import annotations

from decimal import Decimal, InvalidOperation


def format_money(amount: float) -> str:
    return f"{amount:.2f}"


def parse_amount(text: str) -> float | None:
    cleaned = text.replace(" ", "").replace(",", ".").strip()
    if not cleaned:
        return None
    try:
        value = float(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return None
    if value <= 0:
        return None
    return value
