from __future__ import annotations

import random


RED_NUMBERS = {
    1, 3, 5, 7, 9,
    12, 14, 16, 18,
    19, 21, 23, 25, 27,
    30, 32, 34, 36,
}
ALL_NUMBERS = set(range(37))
BLACK_NUMBERS = set(range(1, 37)) - RED_NUMBERS
EVEN_NUMBERS = set(range(2, 37, 2))
ODD_NUMBERS = set(range(1, 36, 2))
ROULETTE_WIN_PROB = 18 / 37

SLOT_SYMBOLS = [
    ("🍒", 40, 2.0),
    ("🍋", 30, 2.5),
    ("⭐", 15, 5.0),
    ("7️⃣", 10, 10.0),
    ("💎", 5, 20.0),
]

def _target_win_rate(win_rate: float | None, natural: float) -> float:
    if win_rate is None:
        return natural
    if win_rate < 0:
        win_rate = 0.0
    if win_rate > 1:
        win_rate = 1.0
    return min(win_rate, natural)


def dice_roll(choice: int, win_rate: float | None = None) -> dict:
    target = _target_win_rate(win_rate, 1 / 6)
    win = random.random() < target
    if win:
        roll = choice
    else:
        roll = random.choice([i for i in range(1, 7) if i != choice])
    return {"roll": roll, "win": win}


def coinflip(choice: str, win_rate: float | None = None) -> dict:
    target = _target_win_rate(win_rate, 0.5)
    win = random.random() < target
    if win:
        result = choice
    else:
        result = "Решка" if choice == "Орел" else "Орел"
    return {"result": result, "win": win}


def _roulette_pick_number(choice: str, win: bool) -> int:
    if choice == "Красный":
        pool = RED_NUMBERS if win else (ALL_NUMBERS - RED_NUMBERS)
    elif choice == "Черный":
        pool = BLACK_NUMBERS if win else (ALL_NUMBERS - BLACK_NUMBERS)
    elif choice == "Чет":
        pool = EVEN_NUMBERS if win else (ALL_NUMBERS - EVEN_NUMBERS)
    elif choice == "Нечет":
        pool = ODD_NUMBERS if win else (ALL_NUMBERS - ODD_NUMBERS)
    else:
        pool = ALL_NUMBERS
    return random.choice(list(pool))


def roulette(choice: str, win_rate: float | None = None) -> dict:
    target = _target_win_rate(win_rate, ROULETTE_WIN_PROB)
    win = random.random() < target
    number = _roulette_pick_number(choice, win)
    if number == 0:
        color = "Зеленый"
    elif number in RED_NUMBERS:
        color = "Красный"
    else:
        color = "Черный"

    is_even = number != 0 and number % 2 == 0
    is_odd = number % 2 == 1

    win = False
    if choice == "Красный" and color == "Красный":
        win = True
    elif choice == "Черный" and color == "Черный":
        win = True
    elif choice == "Чет" and is_even:
        win = True
    elif choice == "Нечет" and is_odd:
        win = True

    return {"number": number, "color": color, "win": win}


def crash_point(edge: float = 0.03, cap: float = 25.0) -> float:
    r = random.random()
    point = (1 - edge) / (1 - r)
    if point < 1.0:
        point = 1.0
    if point > cap:
        point = cap
    return round(point, 2)


def crash(target: float, win_rate: float | None = None, edge: float = 0.03, cap: float = 25.0) -> dict:
    natural = min(1.0, (1 - edge) / target)
    target_rate = _target_win_rate(win_rate, natural)
    should_win = random.random() < target_rate
    max_attempts = 50
    point = crash_point(edge=edge, cap=cap)
    if should_win:
        for _ in range(max_attempts):
            point = crash_point(edge=edge, cap=cap)
            if point >= target:
                break
        else:
            point = round(max(target, 1.0), 2)
    else:
        for _ in range(max_attempts):
            point = crash_point(edge=edge, cap=cap)
            if point < target:
                break
        else:
            point = round(max(1.0, target - 0.01), 2)
    win = point >= target
    return {"point": point, "win": win}


def _slots_spin_once() -> dict:
    pool = []
    for symbol, weight, payout in SLOT_SYMBOLS:
        pool.extend([symbol] * weight)
    reels = [random.choice(pool) for _ in range(3)]

    unique = set(reels)
    if len(unique) == 1:
        symbol = reels[0]
        payout = next(p for s, _, p in SLOT_SYMBOLS if s == symbol)
        win = True
        multiplier = payout
    elif len(unique) == 2:
        win = True
        multiplier = 1.4
    else:
        win = False
        multiplier = 0.0

    return {"reels": reels, "win": win, "multiplier": multiplier}


def slots_spin(win_rate: float | None = None) -> dict:
    if win_rate is None:
        return _slots_spin_once()
    total_weight = sum(weight for _, weight, _ in SLOT_SYMBOLS)
    probs = [weight / total_weight for _, weight, _ in SLOT_SYMBOLS]
    natural = sum(p ** 3 for p in probs) + 3 * sum(p ** 2 * (1 - p) for p in probs)
    target = _target_win_rate(win_rate, natural)
    desired_win = random.random() < target
    result = _slots_spin_once()
    for _ in range(50):
        if result["win"] == desired_win:
            return result
        result = _slots_spin_once()
    return result


def mines_round(mines: int, steps: int, edge: float = 0.04) -> dict:
    total = 25
    prob = 1.0
    for i in range(steps):
        prob *= (total - mines - i) / (total - i)
    coef = (1 - edge) / prob
    coef = round(coef, 2)
    win = random.random() < prob
    return {"win": win, "coef": coef, "prob": prob}


def mines_coef(mines: int, opened: int, total: int = 36, edge: float = 0.04) -> float:
    prob = 1.0
    for i in range(opened):
        prob *= (total - mines - i) / (total - i)
    coef = (1 - edge) / prob
    return round(coef, 2)


def mines_board(total: int, mines: int) -> list[int]:
    positions = set(random.sample(range(total), mines))
    return [1 if i in positions else 0 for i in range(total)]
