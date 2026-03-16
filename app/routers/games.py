from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.db import Database
from app import games, texts
from app.keyboards import (
    dice_choices,
    coinflip_choices,
    roulette_choices,
    crash_choices,
    mines_choices,
    mines_grid,
    back_to_games,
    back_to_main,
)
from app.states import GameState
from app.utils import parse_amount

router = Router()


async def _finalize_game(
    message: Message,
    db: Database,
    config: Config,
    game: str,
    bet: float,
    win: bool,
    payout: float,
    meta: dict,
    extra_lines: list[str],
) -> None:
    await db.change_balance(message.from_user.id, -bet, "bet", {"game": game, "bet": bet})
    if win and payout > 0:
        await db.change_balance(message.from_user.id, payout, "win", {"game": game, "payout": payout})
    await db.add_bet(message.from_user.id, game, bet, payout if win else 0.0, win, meta)

    header = texts.game_header(texts.game_title(game), bet, config.currency)
    result_line = texts.game_result(win, payout if win else 0.0, config.currency)
    message_text = "\n".join([header, *extra_lines, result_line])
    await message.answer(message_text, reply_markup=back_to_games())


async def _finalize_mines(
    message: Message,
    db: Database,
    config: Config,
    bet: float,
    win: bool,
    payout: float,
    meta: dict,
    extra_lines: list[str],
) -> None:
    if win and payout > 0:
        await db.change_balance(message.from_user.id, payout, "win", {"game": "mines", "payout": payout})
    await db.add_bet(message.from_user.id, "mines", bet, payout if win else 0.0, win, meta)

    header = texts.game_header(texts.game_title("mines"), bet, config.currency)
    result_line = texts.game_result(win, payout if win else 0.0, config.currency)
    message_text = "\n".join([header, *extra_lines, result_line])
    await message.answer(message_text, reply_markup=back_to_games())


@router.callback_query(F.data.startswith("game:"))
async def game_selected(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    game = callback.data.split(":", 1)[1]
    if await db.is_maintenance():
        await callback.message.answer(texts.maintenance_notice(), reply_markup=back_to_main())
        await callback.answer()
        return
    await db.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    await state.set_state(GameState.waiting_bet)
    await state.update_data(game=game)
    intro = texts.game_intro(game, config.currency)
    prompt = texts.bet_prompt(config.min_bet, config.max_bet, config.currency)
    await callback.message.answer(f"{intro}\n\n{prompt}", reply_markup=back_to_games())
    await callback.answer()


@router.message(GameState.waiting_bet)
async def bet_entered(message: Message, state: FSMContext, db: Database, config: Config) -> None:
    data = await state.get_data()
    game = data.get("game")
    if not game:
        await state.clear()
        return

    if await db.is_maintenance():
        await state.clear()
        await message.answer(texts.maintenance_notice(), reply_markup=back_to_main())
        return

    amount = parse_amount(message.text or "")
    if amount is None or amount < config.min_bet or amount > config.max_bet:
        await message.answer(texts.invalid_amount(config.min_bet, config.max_bet, config.currency))
        return

    balance = await db.get_balance(message.from_user.id)
    if amount > balance:
        await message.answer(texts.insufficient_balance())
        return

    await state.update_data(bet=amount)

    if game == "slots":
        result = games.slots_spin(config.win_rate)
        payout = amount * result["multiplier"]
        extra = [texts.slots_result(result["reels"])]
        await _finalize_game(
            message,
            db,
            config,
            game,
            amount,
            result["win"],
            payout,
            {"reels": result["reels"]},
            extra,
        )
        await state.clear()
        return

    if game == "mines":
        await state.set_state(GameState.waiting_mines)
        await message.answer("💣 Сколько мин на поле? Чем больше — тем выше риск.", reply_markup=mines_choices())
        return

    if game == "dice":
        await state.set_state(GameState.waiting_choice)
        await message.answer("🎲 Выбери число 1–6.", reply_markup=dice_choices())
        return

    if game == "coinflip":
        await state.set_state(GameState.waiting_choice)
        await message.answer("🪙 Выбери сторону монеты.", reply_markup=coinflip_choices())
        return

    if game == "roulette":
        await state.set_state(GameState.waiting_choice)
        await message.answer("🎯 Выбери цвет или четность.", reply_markup=roulette_choices())
        return

    if game == "crash":
        await state.set_state(GameState.waiting_choice)
        await message.answer("📈 Выбери целевой коэффициент.", reply_markup=crash_choices())
        return


@router.callback_query(GameState.waiting_choice, F.data.startswith("choice:"))
async def game_choice(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    data = await state.get_data()
    game = data.get("game")
    bet = data.get("bet")
    if not game or bet is None:
        await state.clear()
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return

    choice = ":".join(parts[2:])

    if game == "dice":
        result = games.dice_roll(int(choice), config.win_rate)
        payout = bet * 5.5 if result["win"] else 0.0
        extra = [texts.dice_result(result["roll"])]
        await _finalize_game(callback.message, db, config, game, bet, result["win"], payout, result, extra)

    elif game == "coinflip":
        result = games.coinflip(choice, config.win_rate)
        payout = bet * 1.9 if result["win"] else 0.0
        extra = [texts.coinflip_result(result["result"])]
        await _finalize_game(callback.message, db, config, game, bet, result["win"], payout, result, extra)

    elif game == "roulette":
        result = games.roulette(choice, config.win_rate)
        payout = bet * 1.9 if result["win"] else 0.0
        extra = [texts.roulette_result(result["number"], result["color"])]
        await _finalize_game(callback.message, db, config, game, bet, result["win"], payout, result, extra)

    elif game == "crash":
        target = float(choice)
        result = games.crash(target, config.win_rate)
        payout = bet * target if result["win"] else 0.0
        extra = [texts.crash_result(result["point"])]
        meta = {"target": target, "point": result["point"]}
        await _finalize_game(callback.message, db, config, game, bet, result["win"], payout, meta, extra)

    await state.clear()
    await callback.answer()


@router.callback_query(GameState.waiting_mines, F.data.startswith("mines:"))
async def mines_count(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    data = await state.get_data()
    bet = data.get("bet")
    if bet is None:
        await state.clear()
        await callback.answer()
        return

    if data.get("bet_locked"):
        await callback.answer("Раунд уже создан")
        return

    count = int(callback.data.split(":", 1)[1])
    board = games.mines_board(36, count)

    await db.change_balance(callback.from_user.id, -bet, "bet", {"game": "mines", "bet": bet})
    await state.update_data(mines=count, board=board, opened=[], bet_locked=True)
    await state.set_state(GameState.mines_active)

    coef = games.mines_coef(count, 0, total=36)
    await callback.message.answer(
        f"💣 <b>САПЁР 6x6</b>\n"
        f"Открывай клетки, коэффициент растет. Сейчас: <b>x{coef:.2f}</b>\n"
        "Жми «💸 Забрать», когда захочешь зафиксировать выигрыш.",
        reply_markup=mines_grid(board, set(), False, coef),
    )
    await callback.answer()


@router.callback_query(GameState.mines_active, F.data.startswith("mines:open:"))
async def mines_open(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    data = await state.get_data()
    board = data.get("board") or []
    opened = set(data.get("opened") or [])
    mines = data.get("mines")
    bet = data.get("bet")
    if not board or mines is None or bet is None:
        await state.clear()
        await callback.answer()
        return

    idx = int(callback.data.split(":", 2)[2])
    if idx in opened:
        await callback.answer("Уже открыто")
        return

    if board[idx] == 1:
        opened.add(idx)
        coef = games.mines_coef(mines, len(opened), total=len(board))
        await state.clear()
        await callback.message.answer(
            "💥 Мина! Раунд завершен.",
            reply_markup=mines_grid(board, opened, True, coef),
        )
        await _finalize_mines(
            callback.message,
            db,
            config,
            bet,
            False,
            0.0,
            {"mines": mines, "opened": len(opened), "coef": coef},
            ["💥 Мина сработала."],
        )
        await callback.answer()
        return

    opened.add(idx)
    coef = games.mines_coef(mines, len(opened), total=len(board))
    await state.update_data(opened=list(opened))
    await callback.message.edit_text(
        f"✅ Чисто! Открыто: <b>{len(opened)}</b> | Коэфф: <b>x{coef:.2f}</b>",
        reply_markup=mines_grid(board, opened, False, coef),
    )
    await callback.answer()


@router.callback_query(GameState.mines_active, F.data == "mines:cashout")
async def mines_cashout(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    data = await state.get_data()
    board = data.get("board") or []
    opened = set(data.get("opened") or [])
    mines = data.get("mines")
    bet = data.get("bet")
    if not board or mines is None or bet is None:
        await state.clear()
        await callback.answer()
        return

    if not opened:
        await callback.answer("Сначала открой клетку")
        return

    coef = games.mines_coef(mines, len(opened), total=len(board))
    payout = bet * coef
    await state.clear()
    await _finalize_mines(
        callback.message,
        db,
        config,
        bet,
        True,
        payout,
        {"mines": mines, "opened": len(opened), "coef": coef},
        [f"💸 Забрано: x{coef:.2f}"],
    )
    await callback.answer()


@router.callback_query(GameState.mines_active, F.data == "mines:forfeit")
async def mines_forfeit(callback: CallbackQuery, state: FSMContext, db: Database, config: Config) -> None:
    data = await state.get_data()
    board = data.get("board") or []
    opened = set(data.get("opened") or [])
    mines = data.get("mines")
    bet = data.get("bet")
    if not board or mines is None or bet is None:
        await state.clear()
        await callback.answer()
        return

    coef = games.mines_coef(mines, len(opened), total=len(board))
    await state.clear()
    await callback.message.answer(
        "❌ Раунд завершен.",
        reply_markup=mines_grid(board, opened, True, coef),
    )
    await _finalize_mines(
        callback.message,
        db,
        config,
        bet,
        False,
        0.0,
        {"mines": mines, "opened": len(opened), "coef": coef},
        ["❌ Раунд завершен."],
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()
