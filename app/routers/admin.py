from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile

from app.config import Config
from app.db import Database
from app.keyboards import admin_deposit_action, admin_menu, admin_withdraw_action, admin_freeze_action, back_to_admin
from app.services.access import is_admin
from app import texts
from app.utils import format_money, parse_amount
from app.states import AdminGrantState, AdminFreezeState, AdminSubscribeState, AdminDepositState

router = Router()

_SUBSCRIBE_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,}$")
_INVITE_LINK_RE = re.compile(r"(https?://)?t\.me/(joinchat/|\+)[A-Za-z0-9_-]+")


def _admin_only_callback(callback: CallbackQuery, config: Config) -> bool:
    return is_admin(callback.from_user.id, config)


def _admin_only_message(message: Message, config: Config) -> bool:
    return is_admin(message.from_user.id, config)


def _owner_only(callback_or_message: CallbackQuery | Message, config: Config) -> bool:
    return callback_or_message.from_user.id in config.owner_ids


def _parse_date_input(text: str) -> str | None:
    raw = text.strip().lower()
    today = datetime.now(timezone.utc).date()
    if raw in {"today", "сегодня"}:
        return today.isoformat()
    if raw in {"yesterday", "вчера"}:
        return (today - timedelta(days=1)).isoformat()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _deposit_status_label(status: str) -> str:
    mapping = {
        "paid": "✅ оплачено",
        "pending": "⏳ ожидает",
        "expired": "⌛ истек",
        "canceled": "❌ отменено",
        "failed": "❌ ошибка",
    }
    return mapping.get(status, status)


async def _send_blocks(message: Message, blocks: list[str], header: str | None = None, reply_markup=None) -> None:
    max_len = 3500
    parts: list[str] = []
    current = header or ""
    for block in blocks:
        candidate = current + ("\n\n" if current else "") + block
        if len(candidate) > max_len and current:
            parts.append(current)
            current = block
        else:
            current = candidate
    if current:
        parts.append(current)

    for idx, part in enumerate(parts):
        markup = reply_markup if idx == len(parts) - 1 else None
        await message.answer(part, reply_markup=markup)


def _extract_invite_link(text: str) -> str | None:
    match = _INVITE_LINK_RE.search(text)
    if not match:
        return None
    link = match.group(0)
    if not link.startswith("http"):
        link = "https://" + link
    return link


def _parse_public_chat(text: str) -> tuple[str, str] | None:
    value = text.strip()
    if not value:
        return None
    if "t.me/" in value:
        part = value.split("t.me/", 1)[1]
        part = part.split("?", 1)[0].strip("/")
    else:
        part = value
    part = part.lstrip("@")
    if part.startswith("+") or part.startswith("joinchat/"):
        return None
    if not _SUBSCRIBE_USERNAME_RE.match(part):
        return None
    chat_id = f"@{part}"
    url = f"https://t.me/{part}"
    return chat_id, url


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    stats = await db.get_stats()
    await callback.message.answer(
        texts.admin_stats(
            stats["users"],
            stats["deposits"],
            stats["bets"],
            stats["payouts"],
            stats["profit"],
            config.currency,
        ),
        reply_markup=admin_menu(),
    )

    game_stats = await db.get_game_stats()
    if game_stats:
        lines = []
        for item in game_stats:
            bets_sum = float(item["bets_sum"])
            payouts_sum = float(item["payouts_sum"])
            profit = bets_sum - payouts_sum
            bets_count = int(item["bets_count"])
            wins = int(item["wins"])
            win_rate = (wins / bets_count * 100) if bets_count else 0.0
            lines.append(
                f"🎮 {texts.game_title(item['game'])}: "
                f"ставки {format_money(bets_sum)} {config.currency}, "
                f"выплаты {format_money(payouts_sum)} {config.currency}, "
                f"профит {format_money(profit)} {config.currency}, "
                f"побед {wins}/{bets_count} ({win_rate:.1f}%)"
            )
        await _send_blocks(callback.message, lines, header="📊 <b>Игры</b>")

    users = await db.get_users_overview(limit=None)
    active_users = []
    for user in users:
        bets_sum = float(user.get("bets_sum", 0))
        payouts_sum = float(user.get("payouts_sum", 0))
        if bets_sum <= 0 and payouts_sum <= 0:
            continue
        profit = payouts_sum - bets_sum
        active_users.append((user, profit))

    if active_users:
        winners = sorted([item for item in active_users if item[1] >= 0], key=lambda x: x[1], reverse=True)
        losers = sorted([item for item in active_users if item[1] < 0], key=lambda x: x[1])

        if winners:
            win_lines = []
            for user, profit in winners:
                display = texts.display_user(user.get("username"), user.get("first_name"))
                sign = "+" if profit >= 0 else ""
                win_lines.append(f"✅ {display}: {sign}{format_money(profit)} {config.currency}")
            await _send_blocks(callback.message, win_lines, header="🏆 <b>Профит игроков</b>")

        if losers:
            lose_lines = []
            for user, profit in losers:
                display = texts.display_user(user.get("username"), user.get("first_name"))
                lose_lines.append(f"❌ {display}: {format_money(profit)} {config.currency}")
            await _send_blocks(callback.message, lose_lines, header="💸 <b>Слил (убыток)</b>")
    await callback.answer()


@router.callback_query(F.data == "admin:deposits")
async def admin_deposits(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    today = datetime.now(timezone.utc).date().isoformat()
    stats = await db.get_deposits_stats_by_date(today)
    deposits = await db.list_deposits_by_date(today)

    header = (
        f"💎 <b>Пополнения за {today} (UTC)</b>\n"
        f"✅ Оплачено: <b>{format_money(stats['paid_sum'])} {config.currency}</b> ({int(stats['paid_count'])})\n"
        f"⏳ Ожидает: <b>{format_money(stats['pending_sum'])} {config.currency}</b> ({int(stats['pending_count'])})\n"
        "Чтобы посмотреть другую дату, введи её в формате ДД.ММ.ГГГГ или YYYY-MM-DD."
    )

    if not deposits:
        await callback.message.answer(header + "\n\nПополнений за эту дату нет.", reply_markup=admin_menu())
        await state.set_state(AdminDepositState.waiting_date)
        await callback.answer()
        return

    user_cache: dict[int, tuple[str | None, str | None]] = {}
    lines = []
    for item in deposits:
        user_id = item["user_id"]
        if user_id in user_cache:
            username, first_name = user_cache[user_id]
        else:
            user = await db.get_user(user_id)
            username = user.get("username") if user else None
            first_name = user.get("first_name") if user else None
            user_cache[user_id] = (username, first_name)
        display = texts.display_user(username, first_name)
        status_label = _deposit_status_label(item["status"])
        lines.append(
            f"{status_label} | #{item['id']} | {display} | {format_money(item['amount'])} {config.currency}"
        )

    await _send_blocks(callback.message, lines, header=header, reply_markup=admin_menu())

    pending = await db.list_pending_deposits(limit=None)
    if pending:
        pending_lines = []
        for item in pending:
            user_id = item["user_id"]
            if user_id in user_cache:
                username, first_name = user_cache[user_id]
            else:
                user = await db.get_user(user_id)
                username = user.get("username") if user else None
                first_name = user.get("first_name") if user else None
                user_cache[user_id] = (username, first_name)
            pending_lines.append(
                texts.pending_deposit_line(item["id"], username, first_name, item["amount"], config.currency)
            )
        await callback.message.answer("🧾 Ожидают подтверждения:\n" + "\n".join(pending_lines), reply_markup=admin_menu())
        for item in pending:
            username, first_name = user_cache.get(item["user_id"], (None, None))
            display = texts.display_user(username, first_name)
            await callback.message.answer(
                f"Пополнение #{item['id']} от пользователя {display}\n"
                f"Сумма: {item['amount']:.2f} {config.currency}",
                reply_markup=admin_deposit_action(item["id"]),
            )

    await state.set_state(AdminDepositState.waiting_date)
    await callback.answer()


@router.message(AdminDepositState.waiting_date)
async def admin_deposits_date(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_message(message, config):
        return
    text = (message.text or "").strip()
    if text.lower() in {"/cancel", "cancel", "отмена"}:
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_menu())
        return

    date_str = _parse_date_input(text)
    if not date_str:
        await message.answer("⚠️ Неверный формат даты. Пример: 16.03.2026 или 2026-03-16.", reply_markup=back_to_admin())
        return

    stats = await db.get_deposits_stats_by_date(date_str)
    deposits = await db.list_deposits_by_date(date_str)
    header = (
        f"💎 <b>Пополнения за {date_str} (UTC)</b>\n"
        f"✅ Оплачено: <b>{format_money(stats['paid_sum'])} {config.currency}</b> ({int(stats['paid_count'])})\n"
        f"⏳ Ожидает: <b>{format_money(stats['pending_sum'])} {config.currency}</b> ({int(stats['pending_count'])})"
    )

    if not deposits:
        await state.clear()
        await message.answer(header + "\n\nПополнений за эту дату нет.", reply_markup=admin_menu())
        return

    user_cache: dict[int, tuple[str | None, str | None]] = {}
    lines = []
    for item in deposits:
        user_id = item["user_id"]
        if user_id in user_cache:
            username, first_name = user_cache[user_id]
        else:
            user = await db.get_user(user_id)
            username = user.get("username") if user else None
            first_name = user.get("first_name") if user else None
            user_cache[user_id] = (username, first_name)
        display = texts.display_user(username, first_name)
        status_label = _deposit_status_label(item["status"])
        lines.append(
            f"{status_label} | #{item['id']} | {display} | {format_money(item['amount'])} {config.currency}"
        )

    await state.clear()
    await _send_blocks(message, lines, header=header, reply_markup=admin_menu())


@router.callback_query(F.data == "admin:logs")
async def admin_logs(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    bets = await db.get_recent_bets(limit=10)
    if not bets:
        await callback.message.answer("Логов пока нет.", reply_markup=admin_menu())
        await callback.answer()
        return
    user_cache: dict[int, str] = {}
    lines = []
    for item in bets:
        status = "✅" if item["win"] else "❌"
        profit = item["payout"] - item["bet_amount"]
        sign = "+" if profit >= 0 else ""
        user_id = item["user_id"]
        if user_id in user_cache:
            display = user_cache[user_id]
        else:
            user = await db.get_user(user_id)
            display = texts.display_user(user.get("username") if user else None, user.get("first_name") if user else None)
            user_cache[user_id] = display
        lines.append(
            f"{status} 👤 {display} | {texts.game_title(item['game'])} | "
            f"{item['bet_amount']:.2f} → {sign}{profit:.2f} {config.currency}"
        )
    await callback.message.answer("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    users = await db.get_users_overview(limit=None)
    if not users:
        await callback.message.answer("Пока нет пользователей.", reply_markup=admin_menu())
        await callback.answer()
        return

    game_rows = await db.get_user_game_stats()
    user_games: dict[int, list[dict]] = {}
    for row in game_rows:
        user_games.setdefault(int(row["user_id"]), []).append(row)

    blocks: list[str] = []
    for user in users:
        name = texts.display_user(user.get("username"), user.get("first_name"))
        profit = float(user.get("payouts_sum", 0)) - float(user.get("bets_sum", 0))
        profit_sign = "+" if profit >= 0 else ""
        lines = [
            f"👤 <b>{name}</b>",
            f"💎 Баланс: <b>{format_money(user['balance'])} {config.currency}</b>",
            f"🎲 Ставки: <b>{format_money(user['bets_sum'])} {config.currency}</b> ({int(user['bets_count'])})",
            f"🏆 Профит: <b>{profit_sign}{format_money(profit)} {config.currency}</b>",
            f"💳 Пополнения: <b>{format_money(user['deposits_sum'])} {config.currency}</b>",
        ]

        per_games = user_games.get(int(user["id"]), [])
        for row in per_games:
            game_profit = float(row["payouts_sum"]) - float(row["bets_sum"])
            sign = "+" if game_profit >= 0 else ""
            lines.append(f"{texts.game_title(row['game'])}: {sign}{format_money(game_profit)} {config.currency}")

        blocks.append("\n".join(lines))

    await _send_blocks(callback.message, blocks, reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:withdrawals")
async def admin_withdrawals(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    stats = await db.get_withdrawals_stats()
    pending = await db.list_pending_withdrawals(limit=10)
    message = (
        "🏦 <b>Выводы</b>\n"
        f"💸 Выплачено: <b>{format_money(stats['paid_sum'])} {config.currency}</b>\n"
        f"⏳ В очереди: <b>{int(stats['pending_count'])}</b>"
    )
    if pending:
        lines = []
        for item in pending:
            user = await db.get_user(item["user_id"])
            username = user.get("username") if user else None
            first_name = user.get("first_name") if user else None
            lines.append(
                texts.withdraw_request_admin_line(
                    item["id"], username, first_name, item["amount"], config.currency
                )
            )
        message += "\n\n" + "\n".join(lines)
    await callback.message.answer(message, reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:freezes")
async def admin_freezes(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    frozen = await db.list_frozen_withdrawals(limit=10)
    if not frozen:
        await callback.message.answer("🧊 Замороженных заявок нет.", reply_markup=admin_menu())
        await callback.answer()
        return
    lines = []
    for item in frozen:
        user = await db.get_user(item["user_id"])
        username = user.get("username") if user else None
        first_name = user.get("first_name") if user else None
        lines.append(
            texts.withdraw_request_admin_line(
                item["id"], username, first_name, item["amount"], config.currency
            )
        )
    await callback.message.answer(
        "🧊 <b>Заморозки</b>\n" + "\n".join(lines) + "\n\nВведи номер заявки (например: #1).",
        reply_markup=back_to_admin(),
    )
    await state.set_state(AdminFreezeState.waiting_id)
    await callback.answer()


@router.message(AdminFreezeState.waiting_id)
async def admin_freeze_select(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_message(message, config):
        return
    text = (message.text or "").strip().lstrip("#")
    if not text.isdigit():
        await message.answer("⚠️ Введи номер заявки, например #1.", reply_markup=back_to_admin())
        return
    withdraw_id = int(text)
    withdrawal = await db.get_withdrawal(withdraw_id)
    if not withdrawal or withdrawal["status"] != "frozen":
        await message.answer("⚠️ Замороженная заявка не найдена.", reply_markup=back_to_admin())
        return
    await state.clear()
    await message.answer(
        f"Заявка #{withdraw_id} на сумму {withdrawal['amount']:.2f} {config.currency}",
        reply_markup=admin_freeze_action(withdraw_id),
    )


@router.callback_query(F.data.startswith("freeze:"))
async def admin_freeze_action_callback(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверная команда", show_alert=True)
        return
    action = parts[1]
    withdraw_id = int(parts[2])
    withdrawal = await db.get_withdrawal(withdraw_id)
    if not withdrawal or withdrawal["status"] != "frozen":
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if action == "unfreeze":
        await db.set_withdrawal_status(withdraw_id, "refunded")
        await db.change_balance(withdrawal["user_id"], withdrawal["amount"], "withdraw_refund", {"withdraw_id": withdraw_id})
        try:
            await callback.bot.send_message(
                withdrawal["user_id"],
                texts.withdraw_refunded(withdrawal["amount"], config.currency),
            )
        except Exception:
            pass
        await callback.answer("Разморозка выполнена")
        return

    if action == "delete":
        await db.set_withdrawal_status(withdraw_id, "rejected")
        try:
            await callback.bot.send_message(
                withdrawal["user_id"],
                texts.withdraw_deleted(withdrawal["amount"], config.currency),
            )
        except Exception:
            pass
        await callback.answer("Удалено")
        return

    await callback.answer("Неизвестное действие", show_alert=True)


@router.callback_query(F.data == "admin:grant")
async def admin_grant(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _owner_only(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminGrantState.waiting_username)
    await callback.message.answer("💸 Введи username пользователя (например: @nickname).", reply_markup=back_to_admin())
    await callback.answer()


@router.message(AdminGrantState.waiting_username)
async def admin_grant_username(message: Message, state: FSMContext, config: Config) -> None:
    if not _owner_only(message, config):
        return
    text = (message.text or "").strip()
    if text.lower() in {"/cancel", "cancel", "отмена"}:
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_menu())
        return
    if not text:
        await message.answer("⚠️ Введи username.", reply_markup=back_to_admin())
        return
    await state.update_data(username=text)
    await state.set_state(AdminGrantState.waiting_amount)
    await message.answer("💎 Введи сумму для зачисления.", reply_markup=back_to_admin())


@router.message(AdminGrantState.waiting_amount)
async def admin_grant_amount(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _owner_only(message, config):
        return
    amount = parse_amount(message.text or "")
    if amount is None or amount <= 0:
        await message.answer("⚠️ Неверная сумма. Введи число.", reply_markup=back_to_admin())
        return
    data = await state.get_data()
    username = data.get("username", "")
    user = await db.get_user_by_username(username)
    if not user:
        await state.clear()
        await message.answer("❌ Пользователь не найден. Убедись, что он писал боту хотя бы раз.", reply_markup=admin_menu())
        return
    await db.change_balance(user["id"], amount, "admin_grant", {"by": message.from_user.id})
    await state.clear()
    await message.answer(
        f"✅ Начислено {format_money(amount)} {config.currency} пользователю @{user['username']}",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "admin:maintenance")
async def admin_maintenance(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    current = await db.is_maintenance()
    await db.set_setting("maintenance", "off" if current else "on")
    await callback.message.answer(texts.maintenance_state(not current), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:db")
async def admin_db(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    db_path = Path(config.db_path)
    if not db_path.exists():
        await callback.message.answer("⚠️ База данных не найдена.", reply_markup=admin_menu())
        await callback.answer()
        return
    await callback.message.answer_document(
        FSInputFile(db_path),
        caption="💾 База данных Kris Casino.\nЧтобы восстановить, отправь сюда файл .db",
    )
    await callback.message.answer("Готово.", reply_markup=admin_menu())
    await callback.answer()


@router.message(F.document)
async def admin_db_upload(message: Message, config: Config) -> None:
    if not _admin_only_message(message, config):
        return
    document = message.document
    if not document or not document.file_name or not document.file_name.lower().endswith(".db"):
        await message.answer("⚠️ Отправь файл .db", reply_markup=admin_menu())
        return

    db_path = Path(config.db_path)
    backup_path = db_path.with_suffix(".bak")
    try:
        if db_path.exists():
            db_path.replace(backup_path)
        file = await message.bot.get_file(document.file_id)
        await message.bot.download_file(file.file_path, db_path)
    except Exception:
        await message.answer("⚠️ Не удалось обновить базу. Попробуй снова.", reply_markup=admin_menu())
        return

    await message.answer("✅ База данных обновлена. Перезапусти бота.", reply_markup=admin_menu())


@router.callback_query(F.data == "admin:subscribe")
async def admin_subscribe(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminSubscribeState.waiting_link)
    current_url = (await db.get_setting("subscribe_url", "") or "").strip()
    current_chat = (await db.get_setting("subscribe_chat", "") or "").strip()
    current = current_url or current_chat or "не задано"
    await callback.message.answer(
        "🔗 <b>Подписка на группу</b>\n"
        f"Текущая ссылка: {current}\n\n"
        "Публичная группа/канал:\n"
        "- отправь ссылку https://t.me/username или @username.\n\n"
        "Приватная группа:\n"
        "- отправь ID группы и инвайт-ссылку через пробел,\n"
        "  например: -1001234567890 https://t.me/+AbCdEf...\n"
        "- или просто пересылай сюда любое сообщение из группы,\n"
        "  бот сам возьмёт ID (ссылку можно добавить отдельно).\n\n"
        "Бот должен быть админом в этой группе/канале.\n"
        "Чтобы отключить проверку, отправь: off",
        reply_markup=back_to_admin(),
    )
    await callback.answer()


@router.message(AdminSubscribeState.waiting_link)
async def admin_subscribe_link(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_message(message, config):
        return
    text = (message.text or "").strip()
    if text.lower() in {"/cancel", "cancel", "отмена"}:
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_menu())
        return
    if text.lower() in {"off", "выкл", "disable", "0"}:
        await db.set_setting("subscribe_chat", "")
        await db.set_setting("subscribe_url", "")
        await state.clear()
        await message.answer("✅ Проверка подписки отключена.", reply_markup=admin_menu())
        return

    # Forwarded message from group/channel: use its chat id
    if message.forward_from_chat:
        chat_id = str(message.forward_from_chat.id)
        invite = _extract_invite_link(text) if text else None
        await db.set_setting("subscribe_chat", chat_id)
        if invite:
            await db.set_setting("subscribe_url", invite)
        await state.clear()
        note = " (ссылка сохранена)" if invite else ""
        await message.answer(f"✅ ID группы сохранен{note}.", reply_markup=admin_menu())
        return

    tokens = text.split()
    invite_link = _extract_invite_link(text)

    # Numeric chat id for private groups
    if tokens and tokens[0].lstrip("-").isdigit():
        chat_id = tokens[0]
        await db.set_setting("subscribe_chat", chat_id)
        await db.set_setting("subscribe_url", invite_link or "")
        await state.clear()
        if invite_link:
            await message.answer(f"✅ ID и ссылка сохранены: {invite_link}", reply_markup=admin_menu())
        else:
            await message.answer(
                "✅ ID группы сохранен. Если нужна кнопка «Подписаться», отправь инвайт-ссылку.",
                reply_markup=admin_menu(),
            )
        return

    # Public username or link
    parsed_public = _parse_public_chat(text)
    if parsed_public:
        chat_id, url = parsed_public
        await db.set_setting("subscribe_chat", chat_id)
        await db.set_setting("subscribe_url", url)
        await state.clear()
        await message.answer(f"✅ Ссылка сохранена: {url}", reply_markup=admin_menu())
        return

    # Invite link only (update url if chat_id already set)
    if invite_link:
        current_chat = (await db.get_setting("subscribe_chat", "") or "").strip()
        if not current_chat:
            await message.answer(
                "⚠️ Сначала укажи ID группы (например: -1001234567890), затем инвайт-ссылку.",
                reply_markup=back_to_admin(),
            )
            return
        await db.set_setting("subscribe_url", invite_link)
        await state.clear()
        await message.answer(f"✅ Ссылка сохранена: {invite_link}", reply_markup=admin_menu())
        return

    await message.answer(
        "⚠️ Не смог распознать данные.\n"
        "Публично: https://t.me/username или @username\n"
        "Приватно: -1001234567890 https://t.me/+AbCdEf...\n"
        "Или просто перешли сообщение из группы.",
        reply_markup=back_to_admin(),
    )


@router.callback_query(F.data == "admin:settings")
async def admin_settings(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.answer("⚙️ Настройки будут добавлены после тестов экономики.", reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:bans")
async def admin_bans(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.answer("🚫 Блокировки доступны в следующем обновлении.", reply_markup=admin_menu())
    await callback.answer()
