from __future__ import annotations

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
from app.states import AdminGrantState, AdminFreezeState

router = Router()


def _admin_only_callback(callback: CallbackQuery, config: Config) -> bool:
    return is_admin(callback.from_user.id, config)


def _admin_only_message(message: Message, config: Config) -> bool:
    return is_admin(message.from_user.id, config)


def _owner_only(callback_or_message: CallbackQuery | Message, config: Config) -> bool:
    return callback_or_message.from_user.id in config.owner_ids


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
    await callback.answer()


@router.callback_query(F.data == "admin:deposits")
async def admin_deposits(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    if not _admin_only_callback(callback, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    pending = await db.list_pending_deposits(limit=10)
    if not pending:
        await callback.message.answer(texts.no_pending_deposits(), reply_markup=admin_menu())
        await callback.answer()
        return

    user_cache: dict[int, tuple[str | None, str | None]] = {}
    lines = []
    for item in pending:
        user_id = item["user_id"]
        if user_id in user_cache:
            username, first_name = user_cache[user_id]
        else:
            user = await db.get_user(user_id)
            username = user.get("username") if user else None
            first_name = user.get("first_name") if user else None
            user_cache[user_id] = (username, first_name)
        lines.append(
            texts.pending_deposit_line(item["id"], username, first_name, item["amount"], config.currency)
        )
    await callback.message.answer("🧾 Ожидают подтверждения:\n" + "\n".join(lines), reply_markup=admin_menu())
    for item in pending:
        username, first_name = user_cache.get(item["user_id"], (None, None))
        display = texts.display_user(username, first_name)
        await callback.message.answer(
            f"Пополнение #{item['id']} от пользователя {display}\n"
            f"Сумма: {item['amount']:.2f} {config.currency}",
            reply_markup=admin_deposit_action(item["id"]),
        )
    await callback.answer()


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
    users = await db.get_users_overview(limit=10)
    if not users:
        await callback.message.answer("Пока нет пользователей.", reply_markup=admin_menu())
        await callback.answer()
        return

    blocks: list[str] = []
    for user in users:
        name = texts.display_user(user.get("username"), user.get("first_name"))
        profit = float(user.get("payouts_sum", 0)) - float(user.get("bets_sum", 0))
        profit_sign = "+" if profit >= 0 else ""
        blocks.append(
            "\n".join(
                [
                    f"👤 <b>{name}</b>",
                    f"💎 Баланс: <b>{format_money(user['balance'])} {config.currency}</b>",
                    f"🎲 Ставки: <b>{format_money(user['bets_sum'])} {config.currency}</b> ({int(user['bets_count'])})",
                    f"🏆 Профит: <b>{profit_sign}{format_money(profit)} {config.currency}</b>",
                    f"💳 Пополнения: <b>{format_money(user['deposits_sum'])} {config.currency}</b>",
                ]
            )
        )

    await callback.message.answer("\n\n".join(blocks), reply_markup=admin_menu())
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
