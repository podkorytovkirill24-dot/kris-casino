from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.db import Database
from app.keyboards import admin_withdraw_action, back_to_main, back_to_withdraw
from app.services.access import is_admin
from app.states import WithdrawState
from app.utils import parse_amount
from app import texts

router = Router()


async def _update_withdraw_message(
    callback: CallbackQuery,
    withdrawal: dict,
    db: Database,
    config: Config,
    status_line: str,
) -> None:
    user = await db.get_user(withdrawal["user_id"])
    username = user.get("username") if user else None
    first_name = user.get("first_name") if user else None
    text = texts.withdraw_request_admin_text(
        withdrawal["id"],
        username,
        first_name,
        withdrawal["amount"],
        config.currency,
        status_line,
    )
    try:
        await callback.message.edit_text(text, reply_markup=None)
    except Exception:
        pass


async def _notify_withdrawal(message: Message, withdrawal_id: int, amount: float, db: Database, config: Config) -> None:
    user = await db.get_user(message.from_user.id)
    username = user.get("username") if user else None
    first_name = user.get("first_name") if user else None
    text = texts.withdraw_request_admin_text(
        withdrawal_id,
        username,
        first_name,
        amount,
        config.currency,
    )

    recipients: list[int] = []
    if config.withdraw_group_id:
        recipients.append(config.withdraw_group_id)
    recipients.extend(list(config.admin_ids))

    sent = set()
    for chat_id in recipients:
        if chat_id in sent:
            continue
        sent.add(chat_id)
        try:
            await message.bot.send_message(
                chat_id,
                text,
                reply_markup=admin_withdraw_action(withdrawal_id),
                disable_notification=False,
            )
        except Exception:
            continue


@router.message(WithdrawState.waiting_amount)
async def withdraw_amount(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    amount = parse_amount(message.text or "")
    if amount is None or amount < config.withdraw_min:
        await message.answer(texts.invalid_withdraw_amount(config.withdraw_min, config.currency), reply_markup=back_to_withdraw())
        return

    balance = await db.get_balance(message.from_user.id)
    if amount > balance:
        await message.answer(texts.insufficient_balance(), reply_markup=back_to_withdraw())
        return

    withdrawal_id = await db.create_withdrawal(message.from_user.id, amount)
    await db.change_balance(message.from_user.id, -amount, "withdraw_request", {"withdraw_id": withdrawal_id})

    await state.clear()
    await message.answer(texts.withdraw_created(amount, config.currency, withdrawal_id), reply_markup=back_to_main())
    await _notify_withdrawal(message, withdrawal_id, amount, db, config)


@router.callback_query(F.data.startswith("withdraw:"))
async def withdraw_action(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверная команда", show_alert=True)
        return

    action = parts[1]
    withdraw_id = int(parts[2])

    withdrawal = await db.get_withdrawal(withdraw_id)
    if not withdrawal:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if withdrawal["status"] != "pending":
        await callback.answer("Уже обработано", show_alert=True)
        return

    if action == "paid":
        await db.set_withdrawal_status(withdraw_id, "paid")
        try:
            await callback.bot.send_message(
                withdrawal["user_id"],
                texts.withdraw_paid(withdrawal["amount"], config.currency),
            )
        except Exception:
            pass
        await _update_withdraw_message(
            callback,
            withdrawal,
            db,
            config,
            texts.withdraw_status_paid(),
        )
        await callback.answer("Отмечено как оплачено")
        return

    if action == "error":
        await db.set_withdrawal_status(withdraw_id, "frozen")
        try:
            await callback.bot.send_message(
                withdrawal["user_id"],
                texts.withdraw_frozen(),
            )
        except Exception:
            pass
        await _update_withdraw_message(
            callback,
            withdrawal,
            db,
            config,
            texts.withdraw_status_frozen(),
        )
        await callback.answer("Отмечено как заморозка")
        return

    await callback.answer("Неизвестное действие", show_alert=True)
