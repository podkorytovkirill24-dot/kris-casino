from __future__ import annotations

import uuid


def build_invoice_id() -> str:
    return uuid.uuid4().hex[:10]


def build_comment(invoice_id: str) -> str:
    return f"KRIS-{invoice_id}"


def build_pay_url(template: str | None, amount: float, comment: str, invoice_id: str) -> str | None:
    if not template:
        return None
    return template.format(amount=amount, comment=comment, invoice_id=invoice_id)
