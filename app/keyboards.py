from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Игры", callback_data="menu:games")
    builder.button(text="💎 Пополнить", callback_data="menu:deposit")
    builder.button(text="🏦 Вывод", callback_data="menu:withdraw")
    builder.button(text="📊 История", callback_data="menu:history")
    builder.button(text="👤 Профиль", callback_data="menu:profile")
    builder.button(text="🆘 Поддержка", callback_data="menu:support")
    if is_admin:
        builder.button(text="🛠 Админка", callback_data="menu:admin")
    builder.adjust(2)
    return builder.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]]
    )


def back_to_games() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:games")]]
    )


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:admin")]]
    )


def back_to_deposit() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:deposit")]]
    )


def back_to_withdraw() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]]
    )


def games_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Кости", callback_data="game:dice")
    builder.button(text="🪙 Монета", callback_data="game:coinflip")
    builder.button(text="🎯 Рулетка", callback_data="game:roulette")
    builder.button(text="📈 Краш", callback_data="game:crash")
    builder.button(text="🎰 Слоты", callback_data="game:slots")
    builder.button(text="💣 Сапёр 6x6", callback_data="game:mines")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def dice_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.button(text=str(i), callback_data=f"choice:dice:{i}")
    builder.button(text="⬅️ Назад", callback_data="menu:games")
    builder.adjust(6, 1)
    return builder.as_markup()


def coinflip_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🦅 Орёл", callback_data="choice:coinflip:Орел")
    builder.button(text="🪙 Решка", callback_data="choice:coinflip:Решка")
    builder.button(text="⬅️ Назад", callback_data="menu:games")
    builder.adjust(2, 1)
    return builder.as_markup()


def roulette_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔴 Красный", callback_data="choice:roulette:Красный")
    builder.button(text="⚫ Черный", callback_data="choice:roulette:Черный")
    builder.button(text="➕ Чет", callback_data="choice:roulette:Чет")
    builder.button(text="➖ Нечет", callback_data="choice:roulette:Нечет")
    builder.button(text="⬅️ Назад", callback_data="menu:games")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def crash_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in [1.2, 1.5, 2.0, 3.0, 5.0]:
        builder.button(text=f"x{value}", callback_data=f"choice:crash:{value}")
    builder.button(text="⬅️ Назад", callback_data="menu:games")
    builder.adjust(3, 2, 1)
    return builder.as_markup()


def mines_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in [2, 4, 6, 8, 10]:
        builder.button(text=f"💣 {value}", callback_data=f"mines:{value}")
    builder.button(text="⬅️ Назад", callback_data="menu:games")
    builder.adjust(5, 1)
    return builder.as_markup()


def mines_steps_choices() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in [1, 2, 3, 4, 5]:
        builder.button(text=str(value), callback_data=f"mines_steps:{value}")
    builder.button(text="⬅️ Назад", callback_data="menu:games")
    builder.adjust(5, 1)
    return builder.as_markup()


def mines_grid(board: list[int], opened: set[int], reveal: bool, coef: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    total = len(board)
    for idx in range(total):
        if idx in opened:
            text = "🟩"
            cb = "noop"
        elif reveal and board[idx] == 1:
            text = "💣"
            cb = "noop"
        elif reveal:
            text = "⬜"
            cb = "noop"
        else:
            text = "🟦"
            cb = f"mines:open:{idx}"
        builder.button(text=text, callback_data=cb)

    rows = [6, 6, 6, 6, 6, 6]
    if not reveal:
        builder.button(text=f"💸 Забрать x{coef:.2f}", callback_data="mines:cashout")
        builder.button(text="❌ Сдаться", callback_data="mines:forfeit")
        rows.append(2)
    else:
        builder.button(text="⬅️ Назад", callback_data="menu:games")
        rows.append(1)
    builder.adjust(*rows)
    return builder.as_markup()


def deposit_amounts() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in [1, 5, 10, 25, 50, 100, 200]:
        builder.button(text=f"{value} USDT", callback_data=f"deposit:{value}")
    builder.button(text="✍️ Своя сумма", callback_data="deposit:custom")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


def deposit_pay_button(pay_url: str, deposit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"deposit_paid:{deposit_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def deposit_wait_button(deposit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"deposit_paid:{deposit_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")],
        ]
    )


def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="💎 Пополнения", callback_data="admin:deposits")
    builder.button(text="🧾 Логи игр", callback_data="admin:logs")
    builder.button(text="👥 Пользователи", callback_data="admin:users")
    builder.button(text="🏦 Выводы", callback_data="admin:withdrawals")
    builder.button(text="🧊 Заморозки", callback_data="admin:freezes")
    builder.button(text="💸 Выдать баланс", callback_data="admin:grant")
    builder.button(text="⛔ Стоп", callback_data="admin:maintenance")
    builder.button(text="💾 База данных", callback_data="admin:db")
    builder.button(text="🔗 Подписка", callback_data="admin:subscribe")
    builder.button(text="⚙️ Настройки", callback_data="admin:settings")
    builder.button(text="🚫 Блокировки", callback_data="admin:bans")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(2, 2, 2, 2, 2, 2, 1)
    return builder.as_markup()


def admin_deposit_action(deposit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_deposit_confirm:{deposit_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:admin")],
        ]
    )


def admin_withdraw_action(withdraw_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"withdraw:paid:{withdraw_id}")],
            [InlineKeyboardButton(text="⚠️ Ошибка", callback_data=f"withdraw:error:{withdraw_id}")],
        ]
    )


def admin_freeze_action(withdraw_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Разморозить", callback_data=f"freeze:unfreeze:{withdraw_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"freeze:delete:{withdraw_id}")],
        ]
    )


def subscribe_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📣 Подписаться", url=url)],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="subscribe:check")],
        ]
    )
