from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

from app.db import Database
from app.keyboards import subscribe_keyboard
from app import texts


async def get_subscribe_target(db: Database) -> tuple[str | None, str | None]:
    chat_id = (await db.get_setting("subscribe_chat", "") or "").strip()
    url = (await db.get_setting("subscribe_url", "") or "").strip()
    if not chat_id:
        return None, None
    if not url and chat_id.startswith("@"):
        url = f"https://t.me/{chat_id.lstrip('@')}"
    return chat_id, url or None


async def is_subscribed(bot: Bot, chat_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    status = getattr(member, "status", None)
    if status in {"left", "kicked"}:
        return False
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return True


async def ensure_subscribed(message_or_callback: Message | CallbackQuery, db: Database) -> bool:
    chat_id, url = await get_subscribe_target(db)
    if not chat_id:
        return True
    bot = message_or_callback.bot
    user_id = message_or_callback.from_user.id
    if await is_subscribed(bot, chat_id, user_id):
        return True

    text = texts.subscribe_required()
    markup = subscribe_keyboard(url) if url else None
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=markup)
    else:
        await message_or_callback.message.answer(text, reply_markup=markup)
        await message_or_callback.answer()
    return False
