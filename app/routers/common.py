from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from app.config import Config
from app.db import Database
from app.keyboards import games_menu, main_menu, admin_menu as admin_menu_keyboard, back_to_main, back_to_withdraw
from app.services.access import is_admin
from app.services.subscription import ensure_subscribed, get_subscribe_target, is_subscribed
from app import texts
from app.states import WithdrawState

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, config: Config) -> None:
    if not await ensure_subscribed(message, db):
        return
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    balance = await db.get_balance(message.from_user.id)
    await message.answer("✨ Режим инлайн-кнопок включен.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        texts.welcome(balance, config.currency),
        reply_markup=main_menu(is_admin(message.from_user.id, config)),
    )


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    balance = await db.get_balance(callback.from_user.id)
    await callback.message.answer("✨ Режим инлайн-кнопок включен.", reply_markup=ReplyKeyboardRemove())
    await callback.message.answer(
        texts.welcome(balance, config.currency),
        reply_markup=main_menu(is_admin(callback.from_user.id, config)),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:games")
async def menu_games(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    if await db.is_maintenance():
        await callback.message.answer(texts.maintenance_notice(), reply_markup=back_to_main())
        await callback.answer()
        return
    await callback.message.answer("🎮 <b>Игровой зал</b> открыт. Выбери игру:", reply_markup=games_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:history")
async def menu_history(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    bets = await db.get_last_bets(callback.from_user.id, limit=10)
    items: list[str] = []
    for item in bets:
        status = "✅" if item["win"] else "❌"
        profit = item["payout"] - item["bet_amount"]
        sign = "+" if profit >= 0 else ""
        items.append(
            f"{status} {texts.game_title(item['game'])} — {item['bet_amount']:.2f} {config.currency}"
            f" → {sign}{profit:.2f} {config.currency}"
        )
    await callback.message.answer(texts.history(items), reply_markup=back_to_main())
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    balance = await db.get_balance(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)
    await callback.message.answer(
        texts.profile(balance, config.currency, stats["bets"], stats["profit"]),
        reply_markup=back_to_main(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    await callback.message.answer(texts.support(config.support_contact), reply_markup=back_to_main())
    await callback.answer()


@router.callback_query(F.data == "menu:withdraw")
async def menu_withdraw(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    await state.set_state(WithdrawState.waiting_amount)
    await callback.message.answer(texts.withdraw_prompt(config.withdraw_min, config.currency), reply_markup=back_to_withdraw())
    await callback.answer()


@router.callback_query(F.data == "menu:admin")
async def menu_admin(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    if not await ensure_subscribed(callback, db):
        return
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(texts.admin_menu(), reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "subscribe:check")
async def subscribe_check(callback: CallbackQuery, db: Database, config: Config) -> None:
    chat_id, _ = await get_subscribe_target(db)
    if not chat_id:
        await callback.answer("Проверка не нужна", show_alert=True)
        return
    ok = await is_subscribed(callback.bot, chat_id, callback.from_user.id)
    if not ok:
        await callback.answer("Подписка не найдена. Подпишись и попробуй снова.", show_alert=True)
        return

    await db.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    balance = await db.get_balance(callback.from_user.id)
    await callback.message.answer("✨ Режим инлайн-кнопок включен.", reply_markup=ReplyKeyboardRemove())
    await callback.message.answer(
        texts.welcome(balance, config.currency),
        reply_markup=main_menu(is_admin(callback.from_user.id, config)),
    )
    await callback.answer("Подписка подтверждена")
