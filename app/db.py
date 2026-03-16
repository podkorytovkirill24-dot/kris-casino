from __future__ import annotations

import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    created_at TEXT,
    balance REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game TEXT NOT NULL,
    bet_amount REAL NOT NULL,
    payout REAL NOT NULL,
    win INTEGER NOT NULL,
    meta TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    provider TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    status TEXT NOT NULL,
    pay_url TEXT,
    comment TEXT,
    created_at TEXT NOT NULL,
    confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    meta TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'off')"
            )
            await db.commit()

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, username, first_name, created_at, balance) VALUES (?, ?, ?, ?, 0)",
                (user_id, username, first_name, _now_iso()),
            )
            await db.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE id = ?",
                (username, first_name, user_id),
            )
            await db.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_balance(self, user_id: int) -> float:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return float(row[0]) if row else 0.0

    async def change_balance(self, user_id: int, amount: float, tx_type: str, meta: dict[str, Any] | None = None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN")
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
            await db.execute(
                "INSERT INTO transactions (user_id, type, amount, meta, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, tx_type, amount, json.dumps(meta or {}, ensure_ascii=False), _now_iso()),
            )
            await db.commit()

    async def add_bet(
        self,
        user_id: int,
        game: str,
        bet_amount: float,
        payout: float,
        win: bool,
        meta: dict[str, Any],
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO bets (user_id, game, bet_amount, payout, win, meta, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    game,
                    bet_amount,
                    payout,
                    1 if win else 0,
                    json.dumps(meta, ensure_ascii=False),
                    _now_iso(),
                ),
            )
            await db.commit()

    async def create_deposit(
        self,
        user_id: int,
        amount: float,
        provider: str,
        invoice_id: str,
        status: str,
        pay_url: str | None,
        comment: str | None,
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO deposits (user_id, amount, provider, invoice_id, status, pay_url, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, amount, provider, invoice_id, status, pay_url, comment, _now_iso()),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_pending_deposits(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM deposits WHERE status = 'pending' ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_deposit(self, deposit_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def confirm_deposit(self, deposit_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN")
            cursor = await db.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
            row = await cursor.fetchone()
            if not row:
                await db.commit()
                return None
            if row["status"] != "pending":
                await db.commit()
                return dict(row)

            await db.execute(
                "UPDATE deposits SET status = 'paid', confirmed_at = ? WHERE id = ?",
                (_now_iso(), deposit_id),
            )
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (row["amount"], row["user_id"]),
            )
            await db.execute(
                "INSERT INTO transactions (user_id, type, amount, meta, created_at) VALUES (?, 'deposit', ?, ?, ?)",
                (
                    row["user_id"],
                    row["amount"],
                    json.dumps({"deposit_id": deposit_id}, ensure_ascii=False),
                    _now_iso(),
                ),
            )
            await db.commit()
            return dict(row)

    async def set_deposit_status(self, deposit_id: int, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE deposits SET status = ? WHERE id = ?",
                (status, deposit_id),
            )
            await db.commit()

    async def create_withdrawal(self, user_id: int, amount: float) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO withdrawals (user_id, amount, status, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?)",
                (user_id, amount, _now_iso(), _now_iso()),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_withdrawal(self, withdrawal_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_pending_withdrawals(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def list_frozen_withdrawals(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM withdrawals WHERE status = 'frozen' ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def set_withdrawal_status(self, withdrawal_id: int, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE withdrawals SET status = ?, updated_at = ? WHERE id = ?",
                (status, _now_iso(), withdrawal_id),
            )
            await db.commit()

    async def get_last_bets(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM bets WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_recent_bets(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM bets ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_user_stats(self, user_id: int) -> dict[str, float]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT COALESCE(SUM(bet_amount), 0) AS bets, COALESCE(SUM(payout), 0) AS payouts FROM bets WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            bets = float(row["bets"]) if row else 0.0
            payouts = float(row["payouts"]) if row else 0.0
            profit = payouts - bets
            return {"bets": bets, "profit": profit}

    async def get_users_count(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        clean = username.lstrip("@")
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
                (clean,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_withdrawals_stats(self) -> dict[str, float]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT COALESCE(SUM(amount), 0) AS sum FROM withdrawals WHERE status = 'paid'")
            paid = await cursor.fetchone()
            cursor = await db.execute("SELECT COUNT(*) AS cnt FROM withdrawals WHERE status = 'pending'")
            pending = await cursor.fetchone()
            return {
                "paid_sum": float(paid["sum"]) if paid else 0.0,
                "pending_count": float(pending["cnt"]) if pending else 0.0,
            }

    async def get_users_overview(self, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    u.id,
                    u.username,
                    u.first_name,
                    u.balance,
                    COALESCE(b.bets_sum, 0) AS bets_sum,
                    COALESCE(b.payouts_sum, 0) AS payouts_sum,
                    COALESCE(b.bets_count, 0) AS bets_count,
                    COALESCE(d.deposits_sum, 0) AS deposits_sum
                FROM users u
                LEFT JOIN (
                    SELECT user_id, SUM(bet_amount) AS bets_sum, SUM(payout) AS payouts_sum, COUNT(*) AS bets_count
                    FROM bets
                    GROUP BY user_id
                ) b ON b.user_id = u.id
                LEFT JOIN (
                    SELECT user_id, SUM(amount) AS deposits_sum
                    FROM deposits
                    WHERE status = 'paid'
                    GROUP BY user_id
                ) d ON d.user_id = u.id
                ORDER BY u.id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            await db.commit()

    async def is_maintenance(self) -> bool:
        value = await self.get_setting("maintenance", "off")
        return value == "on"

    async def get_stats(self) -> dict[str, float]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT COUNT(*) AS cnt FROM users")
            users = await cursor.fetchone()
            cursor = await db.execute("SELECT COALESCE(SUM(amount), 0) AS sum FROM deposits WHERE status = 'paid'")
            deposits = await cursor.fetchone()
            cursor = await db.execute("SELECT COALESCE(SUM(bet_amount), 0) AS sum FROM bets")
            bets = await cursor.fetchone()
            cursor = await db.execute("SELECT COALESCE(SUM(payout), 0) AS sum FROM bets")
            payouts = await cursor.fetchone()
            total_bets = float(bets["sum"]) if bets else 0.0
            total_payouts = float(payouts["sum"]) if payouts else 0.0
            profit = total_bets - total_payouts
            return {
                "users": float(users["cnt"]) if users else 0.0,
                "deposits": float(deposits["sum"]) if deposits else 0.0,
                "bets": total_bets,
                "payouts": total_payouts,
                "profit": profit,
            }
