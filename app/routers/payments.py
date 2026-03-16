from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.db import Database
from app.keyboards import deposit_amounts, deposit_pay_button, deposit_wait_button, admin_deposit_action, back_to_deposit
from app.services.send_provider import build_invoice_id, build_comment, build_pay_url
from app.services.crypto_pay import CryptoPayClient, CryptoPayError
from app.services.access import is_admin
from app import texts
from app.utils import format_money, parse_amount
from app.states import DepositState

router = Router()


async def _create_deposit(amount: float, user_id: int, message: Message, db: Database, config: Config) -> None:
    if config.crypto_pay_token:
        client = CryptoPayClient(config.crypto_pay_token, config.crypto_pay_base_url)
        try:
            invoice = await client.create_invoice(
                asset=config.crypto_pay_asset,
                amount=format_money(amount),
                description=config.crypto_pay_description,
                payload=f"user_id={user_id}",
                allow_comments=config.crypto_pay_allow_comments,
                allow_anonymous=config.crypto_pay_allow_anonymous,
            )
        except CryptoPayError:
            await message.answer("⚠️ Не удалось создать счет Crypto Pay. Попробуй позже.", reply_markup=back_to_deposit())
            return

        pay_url = (
            invoice.bot_invoice_url
            or invoice.web_app_invoice_url
            or invoice.mini_app_invoice_url
            or invoice.pay_url
        )
        if not pay_url:
            await message.answer("⚠️ Ссылка на оплату не пришла. Попробуй снова.", reply_markup=back_to_deposit())
            return

        deposit_id = await db.create_deposit(
            user_id=user_id,
            amount=amount,
            provider="cryptopay",
            invoice_id=str(invoice.invoice_id),
            status="pending",
            pay_url=pay_url,
            comment=None,
        )

        await message.answer(
            texts.cryptopay_invoice(amount, config.currency),
            reply_markup=deposit_pay_button(pay_url, deposit_id),
        )
        return

    invoice_id = build_invoice_id()
    comment = build_comment(invoice_id)
    pay_url = build_pay_url(config.send_pay_url_template, amount, comment, invoice_id)

    deposit_id = await db.create_deposit(
        user_id=user_id,
        amount=amount,
        provider="send",
        invoice_id=invoice_id,
        status="pending",
        pay_url=pay_url,
        comment=comment,
    )

    message_text = texts.deposit_created(amount, config.currency, comment, config.send_username)
    if pay_url:
        await message.answer(
            message_text + "\n\n" + texts.deposit_pay_url(pay_url),
            reply_markup=deposit_pay_button(pay_url, deposit_id),
        )
    else:
        await message.answer(
            message_text + f"\n\nПеревод через {config.send_username}",
            reply_markup=deposit_wait_button(deposit_id),
        )


@router.callback_query(F.data == "menu:deposit")
async def deposit_menu(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    await state.clear()
    await db.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    await callback.message.answer(
        texts.deposit_amount_prompt(config.min_deposit, config.currency),
        reply_markup=deposit_amounts(),
    )
    await callback.answer()


@router.callback_query(F.data == "deposit:custom")
async def deposit_custom(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.set_state(DepositState.waiting_amount)
    await callback.message.answer(texts.deposit_custom_prompt(config.min_deposit, config.currency), reply_markup=back_to_deposit())
    await callback.answer()


@router.callback_query(F.data.startswith("deposit:"))
async def deposit_create(callback: CallbackQuery, db: Database, config: Config) -> None:
    amount = float(callback.data.split(":", 1)[1])
    if amount < config.min_deposit:
        await callback.message.answer(texts.deposit_amount_prompt(config.min_deposit, config.currency))
        await callback.answer()
        return
    await _create_deposit(amount, callback.from_user.id, callback.message, db, config)
    await callback.answer()


@router.message(DepositState.waiting_amount)
async def deposit_custom_amount(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    amount = parse_amount(message.text or "")
    if amount is None or amount < config.min_deposit:
        await message.answer(texts.invalid_deposit_amount(config.min_deposit, config.currency), reply_markup=back_to_deposit())
        return

    await state.clear()
    await _create_deposit(amount, message.from_user.id, message, db, config)


@router.callback_query(F.data.startswith("deposit_paid:"))
async def deposit_paid(callback: CallbackQuery, db: Database, config: Config) -> None:
    deposit_id = int(callback.data.split(":", 1)[1])
    deposit = await db.get_deposit(deposit_id)
    if not deposit:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    if deposit["user_id"] != callback.from_user.id:
        await callback.answer("Это не ваша заявка", show_alert=True)
        return

    if deposit["provider"] == "cryptopay":
        if not config.crypto_pay_token:
            await callback.message.answer("⚠️ Crypto Pay не настроен. Обратись в поддержку.")
            await callback.answer()
            return

        await callback.message.answer(texts.cryptopay_checking())
        try:
            invoice_id = int(deposit["invoice_id"])
        except (TypeError, ValueError):
            await callback.message.answer("⚠️ Неверный счет. Создай новую заявку.")
            await callback.answer()
            return

        client = CryptoPayClient(config.crypto_pay_token, config.crypto_pay_base_url)
        try:
            invoices = await client.get_invoices([invoice_id])
        except CryptoPayError:
            await callback.message.answer("⚠️ Не удалось проверить оплату. Попробуй позже.")
            await callback.answer()
            return

        if not invoices:
            await callback.message.answer("⚠️ Счет не найден. Создай новую заявку.")
            await callback.answer()
            return

        status = invoices[0].get("status")
        if status == "paid":
            await db.confirm_deposit(deposit_id)
            await callback.message.answer(
                f"💎 Пополнение {deposit['amount']:.2f} {config.currency} подтверждено. Баланс обновлен."
            )
            await callback.answer()
            return

        if status == "expired":
            await db.set_deposit_status(deposit_id, "expired")
            await callback.message.answer(texts.cryptopay_expired())
            await callback.answer()
            return

        await callback.message.answer(texts.cryptopay_not_paid())
        await callback.answer()
        return

    await callback.message.answer(texts.deposit_waiting())

    user = await db.get_user(deposit["user_id"])
    username = user.get("username") if user else None
    first_name = user.get("first_name") if user else None

    for admin_id in config.admin_ids:
        try:
            await callback.bot.send_message(
                admin_id,
                "💎 Пополнение ожидает подтверждения\n"
                f"{texts.pending_deposit_line(deposit_id, username, first_name, deposit['amount'], config.currency)}",
                reply_markup=admin_deposit_action(deposit_id),
            )
        except Exception:
            continue

    await callback.answer()


@router.callback_query(F.data.startswith("admin_deposit_confirm:"))
async def admin_deposit_confirm(callback: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа", show_alert=True)
        return

    deposit_id = int(callback.data.split(":", 1)[1])
    deposit = await db.confirm_deposit(deposit_id)
    if not deposit:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.message.answer(f"✅ Подтверждено пополнение #{deposit_id}")
    try:
        await callback.bot.send_message(
            deposit["user_id"],
            f"💎 Пополнение {deposit['amount']:.2f} {config.currency} подтверждено. Баланс обновлен.",
        )
    except Exception:
        pass

    await callback.answer()
