from __future__ import annotations

from app.utils import format_money


TITLE = "🧿 <b>KRIS CASINO</b> — Неоновый Сейф"


def game_title(game: str) -> str:
    names = {
        "dice": "Кости",
        "coinflip": "Монета",
        "roulette": "Рулетка",
        "crash": "Краш",
        "slots": "Слоты",
        "mines": "Сапёр 6x6",
    }
    return names.get(game, game.title())


def display_user(username: str | None, first_name: str | None) -> str:
    if username:
        return f"@{username}"
    if first_name:
        return first_name
    return "Без имени"


def welcome(balance: float, currency: str) -> str:
    return (
        f"{TITLE}\n"
        f"💎 Баланс: <b>{format_money(balance)} {currency}</b>\n"
        "🌌 Вход открыт. Выбери игру или пополни счет."
    )


def profile(balance: float, currency: str, bets_total: float, profit: float) -> str:
    profit_sign = "+" if profit >= 0 else ""
    return (
        "👤 <b>Профиль игрока</b>\n"
        f"💎 Баланс: <b>{format_money(balance)} {currency}</b>\n"
        f"🎲 Всего ставок: <b>{format_money(bets_total)} {currency}</b>\n"
        f"✨ Профит: <b>{profit_sign}{format_money(profit)} {currency}</b>"
    )


def history(items: list[str]) -> str:
    if not items:
        return "📊 История пуста. Сделай первый ход — и мы всё запомним."
    joined = "\n".join(items)
    return f"📊 <b>Последние игры</b>\n{joined}"


def support(contact: str) -> str:
    return (
        "🆘 <b>Поддержка</b>\n"
        "Если что-то не так — напиши сюда:\n"
        f"{contact}"
    )


def deposit_created(amount: float, currency: str, comment: str, send_username: str) -> str:
    return (
        "💎 <b>Пополнение создано</b>\n"
        f"Сумма: <b>{format_money(amount)} {currency}</b>\n"
        f"Комментарий для перевода: <b>{comment}</b>\n\n"
        f"Отправь перевод через {send_username} и обязательно укажи комментарий."
    )


def deposit_pay_url(pay_url: str) -> str:
    return (
        "⚡️ <b>Счет готов</b>\n"
        "Нажми кнопку ниже, чтобы оплатить."
    )


def cryptopay_invoice(amount: float, currency: str) -> str:
    return (
        "💎 <b>Счет Crypto Pay создан</b>\n"
        f"Сумма: <b>{format_money(amount)} {currency}</b>\n"
        "Нажми кнопку ниже для оплаты."
    )


def deposit_waiting() -> str:
    return "🧾 Заявка отмечена как оплаченная. Ждем подтверждение."


def cryptopay_checking() -> str:
    return "🧾 Проверяю оплату через Crypto Pay..."


def cryptopay_not_paid() -> str:
    return "⏳ Оплата еще не поступила. Попробуй чуть позже."


def cryptopay_expired() -> str:
    return "⌛️ Счет истек. Создай новое пополнение."


def withdraw_soon() -> str:
    return (
        "🏦 <b>Вывод</b>\n"
        "Вывод доступен по заявке. Выбери сумму и отправь запрос."
    )


def game_header(name: str, bet: float, currency: str) -> str:
    return (
        f"🧿 <b>KRIS CASINO</b> | {name}\n"
        f"💎 Ставка: <b>{format_money(bet)} {currency}</b>\n"
        "🕯️ Раунд запущен..."
    )


def game_result(win: bool, payout: float, currency: str) -> str:
    if win:
        return f"🔥 Победа! Выигрыш: <b>+{format_money(payout)} {currency}</b>"
    return "❌ Проигрыш. Возьми реванш — игра только началась."


def dice_result(roll: int) -> str:
    return f"🎲 Выпало: <b>{roll}</b>"


def coinflip_result(result: str) -> str:
    return f"🪙 Монета: <b>{result}</b>"


def roulette_result(number: int, color: str) -> str:
    return f"🎯 Выпало: <b>{number}</b> ({color})"


def crash_result(point: float) -> str:
    return f"📈 Краш на: <b>x{point}</b>"


def slots_result(reels: list[str]) -> str:
    return f"🎰 Результат: <b>{' '.join(reels)}</b>"


def mines_result(mines: int, steps: int, coef: float) -> str:
    return (
        f"💣 Мины: <b>{mines}</b> | Шаги: <b>{steps}</b>\n"
        f"Коэффициент: <b>x{coef}</b>"
    )


def insufficient_balance() -> str:
    return "💥 Недостаточно средств. Пополни баланс и возвращайся в игру."


def invalid_amount(min_bet: float, max_bet: float, currency: str) -> str:
    return (
        "⚠️ Неверная сумма."
        f" Введи ставку от <b>{format_money(min_bet)} {currency}</b>"
        f" до <b>{format_money(max_bet)} {currency}</b>."
    )


def deposit_amount_prompt(min_deposit: float, currency: str) -> str:
    return (
        f"💎 Выбери сумму пополнения (минимум {format_money(min_deposit)} {currency}).\n"
        "Или нажми «Своя сумма»."
    )


def deposit_custom_prompt(min_deposit: float, currency: str) -> str:
    return (
        "✍️ Введи свою сумму пополнения.\n"
        f"Минимум: {format_money(min_deposit)} {currency}"
    )


def invalid_deposit_amount(min_deposit: float, currency: str) -> str:
    return (
        "⚠️ Неверная сумма пополнения.\n"
        f"Минимум: {format_money(min_deposit)} {currency}"
    )


def bet_prompt(min_bet: float, max_bet: float, currency: str) -> str:
    return (
        "🧪 Введи сумму ставки.\n"
        f"Диапазон: {format_money(min_bet)}–{format_money(max_bet)} {currency}"
    )


def withdraw_prompt(min_withdraw: float, currency: str) -> str:
    return (
        "🏦 <b>Заявка на вывод</b>\n"
        f"Введи сумму (минимум {format_money(min_withdraw)} {currency})."
    )


def invalid_withdraw_amount(min_withdraw: float, currency: str) -> str:
    return (
        "⚠️ Неверная сумма вывода.\n"
        f"Минимум: {format_money(min_withdraw)} {currency}"
    )


def withdraw_created(amount: float, currency: str, withdraw_id: int) -> str:
    return (
        "✅ <b>Заявка принята</b>\n"
        f"Сумма: <b>{format_money(amount)} {currency}</b>\n"
        f"Номер: <b>#{withdraw_id}</b>\n"
        "Мы отправили запрос в очередь на выплату."
    )


def withdraw_paid(amount: float, currency: str) -> str:
    return f"💸 Ваша заявка на вывод оплачена: <b>{format_money(amount)} {currency}</b>"


def withdraw_frozen() -> str:
    return "⛔ Ваши деньги заморожены до выяснения обстоятельств."


def withdraw_request_admin_line(
    withdraw_id: int,
    username: str | None,
    first_name: str | None,
    amount: float,
    currency: str,
) -> str:
    return (
        f"🏦 Заявка #{withdraw_id} | 👤 "
        f"{display_user(username, first_name)} | {format_money(amount)} {currency}"
    )


def withdraw_request_admin_text(
    withdraw_id: int,
    username: str | None,
    first_name: str | None,
    amount: float,
    currency: str,
    status_line: str | None = None,
) -> str:
    lines = [
        "🏦 <b>Новая заявка на вывод</b>",
        withdraw_request_admin_line(withdraw_id, username, first_name, amount, currency),
        f"👤 {display_user(username, first_name)}",
    ]
    if status_line:
        lines.append(status_line)
    return "\n".join(lines)


def withdraw_status_paid() -> str:
    return "✅ Заявка обработана. Выплата получена."


def withdraw_status_frozen() -> str:
    return "⛔ Деньги заморожены."


def withdraw_refunded(amount: float, currency: str) -> str:
    return f"✅ Средства возвращены на баланс: <b>{format_money(amount)} {currency}</b>. Приносим извинения."


def withdraw_deleted(amount: float, currency: str) -> str:
    return (
        f"⚠️ Ваши деньги {format_money(amount)} {currency} подозреваются как накрученные.\n"
        "Если это не так — обратитесь в поддержку."
    )


def maintenance_notice() -> str:
    return "⛔ Казино временно не работает. Попробуй позже."


def maintenance_state(enabled: bool) -> str:
    if enabled:
        return "⛔ Казино остановлено администратором."
    return "✅ Казино снова работает. Игры открыты."


def game_intro(game: str, currency: str) -> str:
    if game == "dice":
        return (
            "🎲 <b>КОСТИ</b>\n"
            "Как играть:\n"
            "1. Выбираешь число от 1 до 6.\n"
            "2. Кубик бросается автоматически.\n"
            "3. Совпало — победа.\n"
            "Коэффициент: <b>x5.5</b>\n"
            "🧿 Один бросок — одна судьба."
        )
    if game == "coinflip":
        return (
            "🪙 <b>МОНЕТА</b>\n"
            "Как играть:\n"
            "1. Выбираешь Орёл или Решку.\n"
            "2. Подбрасываем монету — 50/50.\n"
            "Коэффициент: <b>x1.9</b>\n"
            "✨ Чистая дуэль удачи."
        )
    if game == "roulette":
        return (
            "🎯 <b>РУЛЕТКА</b>\n"
            "Как играть:\n"
            "1. Выбираешь Красный/Черный или Чет/Нечет.\n"
            "2. 0 — зеленый и всегда против.\n"
            "Коэффициент: <b>x1.9</b>\n"
            "🕯️ Колесо решает."
        )
    if game == "crash":
        return (
            "📈 <b>КРАШ</b>\n"
            "Как играть:\n"
            "1. Выбираешь цель (коэффициент).\n"
            "2. Если краш случится после цели — победа.\n"
            "Выигрыш: ставка × выбранный коэффициент.\n"
            "⚗️ Чем выше цель — тем жарче риск."
        )
    if game == "slots":
        return (
            "🎰 <b>СЛОТЫ</b>\n"
            "Как играть:\n"
            "1. Крутим 3 барабана.\n"
            "2. 3 одинаковых — крупный выигрыш.\n"
            "3. 2 одинаковых — утешительный профит.\n"
            "💎 Лови серию."
        )
    if game == "mines":
        return (
            "💣 <b>САПЁР 6x6</b>\n"
            "Как играть:\n"
            "1. Выбираешь число мин.\n"
            "2. Открываешь клетки на поле 6x6.\n"
            "3. Каждая чистая клетка повышает коэффициент.\n"
            "4. В любой момент жми «💸 Забрать».\n"
            "💥 Мина = раунд окончен."
        )
    return f"🎮 <b>{game}</b>"


def admin_menu() -> str:
    return "🛠 <b>Админка</b>"


def admin_stats(users: float, deposits: float, bets: float, payouts: float, profit: float, currency: str) -> str:
    profit_sign = "+" if profit >= 0 else ""
    return (
        "📊 <b>Статистика</b>\n"
        f"👥 Пользователи: <b>{int(users)}</b>\n"
        f"💎 Пополнения: <b>{format_money(deposits)} {currency}</b>\n"
        f"🎲 Ставки: <b>{format_money(bets)} {currency}</b>\n"
        f"🏆 Выплаты: <b>{format_money(payouts)} {currency}</b>\n"
        f"✨ Профит: <b>{profit_sign}{format_money(profit)} {currency}</b>"
    )


def no_pending_deposits() -> str:
    return "✅ Нет ожидающих пополнений."


def pending_deposit_line(
    deposit_id: int,
    username: str | None,
    first_name: str | None,
    amount: float,
    currency: str,
) -> str:
    return (
        f"#{deposit_id} | 👤 "
        f"{display_user(username, first_name)} | {format_money(amount)} {currency}"
    )
