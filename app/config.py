from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    owner_ids: set[int]
    db_path: Path
    min_deposit: float
    withdraw_min: float
    min_bet: float
    max_bet: float
    support_contact: str
    send_username: str
    send_pay_url_template: str | None
    currency: str
    crypto_pay_token: str | None
    crypto_pay_base_url: str
    crypto_pay_asset: str
    crypto_pay_description: str
    crypto_pay_allow_comments: bool
    crypto_pay_allow_anonymous: bool
    withdraw_group_id: int | None
    win_rate: float


def _parse_admin_ids(value: str) -> set[int]:
    ids: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            ids.add(int(part))
    return ids


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    owner_ids = _parse_admin_ids(os.getenv("OWNER_IDS", "")) or admin_ids
    db_path = Path(os.getenv("DB_PATH", "data/kris_casino.db"))
    min_deposit = float(os.getenv("MIN_DEPOSIT", "1"))
    withdraw_min = float(os.getenv("WITHDRAW_MIN", "5"))
    min_bet = float(os.getenv("MIN_BET", "0.20"))
    max_bet = float(os.getenv("MAX_BET", "200"))
    support_contact = os.getenv("SUPPORT_CONTACT", "@support").strip()
    send_username = os.getenv("SEND_USERNAME", "@send").strip()
    send_pay_url_template = os.getenv("SEND_PAY_URL_TEMPLATE", "").strip() or None
    currency = os.getenv("CURRENCY", "USDT").strip()
    crypto_pay_token = os.getenv("CRYPTO_PAY_API_TOKEN", "").strip() or None
    crypto_pay_base_url = os.getenv("CRYPTO_PAY_BASE_URL", "https://pay.crypt.bot/api").strip()
    crypto_pay_asset = os.getenv("CRYPTO_PAY_ASSET", currency).strip()
    crypto_pay_description = os.getenv("CRYPTO_PAY_DESCRIPTION", "Kris Casino top-up").strip()
    crypto_pay_allow_comments = os.getenv("CRYPTO_PAY_ALLOW_COMMENTS", "false").strip().lower() in {"1", "true", "yes", "y"}
    crypto_pay_allow_anonymous = os.getenv("CRYPTO_PAY_ALLOW_ANONYMOUS", "false").strip().lower() in {"1", "true", "yes", "y"}
    withdraw_group_raw = os.getenv("WITHDRAW_GROUP_ID", "").strip()
    withdraw_group_id = int(withdraw_group_raw) if withdraw_group_raw else None
    win_rate_raw = os.getenv("WIN_RATE", "0.30").strip()
    try:
        win_rate = float(win_rate_raw)
    except ValueError:
        win_rate = 0.30
    if win_rate > 1:
        win_rate = win_rate / 100
    if win_rate < 0:
        win_rate = 0.0
    if win_rate > 1:
        win_rate = 1.0

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        owner_ids=owner_ids,
        db_path=db_path,
        min_deposit=min_deposit,
        withdraw_min=withdraw_min,
        min_bet=min_bet,
        max_bet=max_bet,
        support_contact=support_contact,
        send_username=send_username,
        send_pay_url_template=send_pay_url_template,
        currency=currency,
        crypto_pay_token=crypto_pay_token,
        crypto_pay_base_url=crypto_pay_base_url,
        crypto_pay_asset=crypto_pay_asset,
        crypto_pay_description=crypto_pay_description,
        crypto_pay_allow_comments=crypto_pay_allow_comments,
        crypto_pay_allow_anonymous=crypto_pay_allow_anonymous,
        withdraw_group_id=withdraw_group_id,
        win_rate=win_rate,
    )
