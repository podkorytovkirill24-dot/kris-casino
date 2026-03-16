from aiogram.fsm.state import State, StatesGroup


class GameState(StatesGroup):
    waiting_bet = State()
    waiting_choice = State()
    waiting_mines = State()
    waiting_mines_steps = State()
    mines_active = State()


class DepositState(StatesGroup):
    waiting_amount = State()


class WithdrawState(StatesGroup):
    waiting_amount = State()


class AdminGrantState(StatesGroup):
    waiting_username = State()
    waiting_amount = State()


class AdminFreezeState(StatesGroup):
    waiting_id = State()
