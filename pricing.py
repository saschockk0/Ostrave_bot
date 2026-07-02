"""Калькулятор стоимости поездки: позиции, цены и расчёт.

Идея и набор позиций взяты из веб-проекта Ostrov2 (src/pricing.js), но здесь всё
плоско: одна ставка на позицию (событие 31.07–02.08 — это Пт–Вс, поэтому берём
выходные цены) плюс динамическая цена билета, растущая по мере приближения к дате.

Чтобы поменять цены — правьте константы в этом файле, больше нигде не нужно.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PriceItem:
    key: str       # хранится в callback_data и в state
    label: str     # человекочитаемое название (с эмодзи)
    price: int     # ₽ за единицу


# --- позиции аренды (выходные ставки из Ostrov2) --------------------------
TENT_TYPES = [
    PriceItem("tent1", "⛺ Палатка 1-местная", 500),
    PriceItem("tent2", "⛺ Палатка 2-местная", 700),
    PriceItem("tent3", "⛺ Палатка 3-местная", 900),
]
TENT_TYPES_BY_KEY = {i.key: i for i in TENT_TYPES}

# --- кухня-шатёр (общий навес на компанию, как на сайте Ostrov2) -----------
# Не личная палатка, а большой шатёр-кухня: навес от дождя и солнца + место,
# где компании удобно собраться и готовить. Плитка и газовый баллон уже входят
# в комплект. Размеры и цены — как на Ostrov2 (data/prices.json, выходные
# ставки: событие 31.07–02.08 это Пт–Вс).
CANOPY_TYPES = [
    PriceItem("canopySmall",   "🎪 Кухня-шатёр малый (до 8 чел)",      1500),
    PriceItem("canopyMedium",  "🎪 Кухня-шатёр средний (10–15 чел)",   4500),
    PriceItem("canopyLarge",   "🎪 Кухня-шатёр большой (20–25 чел)",   7800),
    PriceItem("canopyEverest", "🎪 Кухня-шатёр «Эверест» (30–40 чел)", 10000),
]
CANOPY_TYPES_BY_KEY = {i.key: i for i in CANOPY_TYPES}


def suggest_canopy_key(people: int) -> str:
    """Минимальный кухня-шатёр, в который влезает компания (по вместимости).

    Пороги — из подписей CANOPY_TYPES (Ostrov2): до 8 / 10–15 / 20–25 / 30–40.
    Девятка округляется вверх к среднему — лучше с запасом, чем впритык.
    """
    people = max(1, int(people))
    if people <= 8:
        return "canopySmall"
    if people <= 15:
        return "canopyMedium"
    if people <= 25:
        return "canopyLarge"
    return "canopyEverest"


SUP_PRICE_PER_HOUR = 600  # ₽ за час на сап-борде

# Вход на остров — обязательный для каждого гостя, оплата на месте при выезде.
# Покрывает трансфер на остров и обратно, катамараны и баню (см. FAQ «price»).
# Это второй слой цены поверх билета на open air, поэтому считаем его на всех
# человек, чтобы итог калькулятора показывал честную сумму поездки.
ISLAND_ENTRY_PRICE = 4700  # ₽ с человека

EXTRA_EQUIPMENT = [
    PriceItem("sleepingSet", "🛌 Спальный комплект", 600),
    PriceItem("tableSet",    "🪑 Стол с табуретками", 700),
    PriceItem("stove",       "🔥 Походная плитка",    600),
    PriceItem("gasCanister", "⛽ Газовый баллончик",  250),
    PriceItem("kayak",       "🛶 Байдарка (час)",     600),
]
EXTRA_EQUIPMENT_BY_KEY = {i.key: i for i in EXTRA_EQUIPMENT}


# --- динамическая цена билета (растёт по мере приближения к дате) ----------
EVENT_START_DATE = date(2026, 7, 31)

# (порог «за сколько дней до старта», цена ₽ за человека). Идём от дальнего
# к близкому. Значения примерные — правятся здесь.
TICKET_PRICE_SCHEDULE = [
    (30, 2100),  # больше чем за 30 дней
    (14, 2500),  # за 14–29 дней
    (7,  2900),  # за 7–13 дней
    (0,  3300),  # менее 7 дней / в дни события
]


def current_ticket_price(today: date | None = None) -> int:
    """Цена билета за одного человека на текущую дату (растёт ближе к событию)."""
    today = today or date.today()
    days_left = (EVENT_START_DATE - today).days
    for threshold, price in TICKET_PRICE_SCHEDULE:
        if days_left >= threshold:
            return price
    # у самой даты или после неё — максимальная ставка
    return TICKET_PRICE_SCHEDULE[-1][1]


@dataclass
class Quote:
    people: int
    ticket_price: int                 # цена билета за человека на момент расчёта
    total: int                        # итог в рублях
    breakdown: list[tuple[str, int]]  # (подпись позиции, сумма ₽)

    def summary_text(self) -> str:
        """Состав расчёта построчно — для заявки и сообщения менеджеру."""
        return "\n".join(f"• {label} — {amount} ₽" for label, amount in self.breakdown)


def build_quote(
    people: int,
    tents: dict[str, int] | None = None,
    canopies: dict[str, int] | None = None,
    sup_hours: int = 0,
    equipment: dict[str, int] | None = None,
    today: date | None = None,
    open_air_total: int | None = None,
) -> Quote:
    """Считает предварительную стоимость поездки и разбивку по позициям.

    Итог = билет × кол-во человек + аренда палаток + кухня-шатёр + сап +
    доп. снаряжение. Упрощённый аналог calculateQuote из Ostrov2/src/pricing.js.

    `open_air_total` — готовая сумма билета на open air по групповому тарифу
    «на четверых» (та же, что в прямой заявке: models.ticket_price_for). Если не
    передан, падаем на per-person динамику. Считает вызывающая сторона, чтобы не
    тянуть models в pricing (иначе цикл импорта).
    """
    tents = tents or {}
    canopies = canopies or {}
    equipment = equipment or {}
    people = max(0, int(people))
    sup_hours = max(0, int(sup_hours))

    breakdown: list[tuple[str, int]] = []
    total = 0

    # Слой 1 — билет на open air (сама тусовка), оплата заранее переводом.
    if people > 0:
        if open_air_total is None:
            tp = current_ticket_price(today)
            amount = people * tp
            label = f"🎟 Билет на open air ×{people} (по {tp} ₽)"
        else:
            amount = max(0, int(open_air_total))
            label = f"🎟 Билет на open air ×{people} (тариф «на четверых»)"
        breakdown.append((label, amount))
        total += amount

    # Слой 2 — вход на остров (трансфер, катамараны, баня), оплата при выезде.
    if people > 0:
        amount = people * ISLAND_ENTRY_PRICE
        breakdown.append(
            (f"🏝 Вход на остров ×{people} (по {ISLAND_ENTRY_PRICE} ₽, при выезде)", amount)
        )
        total += amount

    # Палатки 1/2/3-местные.
    for item in TENT_TYPES:
        qty = max(0, int(tents.get(item.key, 0)))
        if qty:
            amount = qty * item.price
            breakdown.append((f"{item.label} ×{qty}", amount))
            total += amount

    # Кухня-шатёр — общий навес-кухня на всю компанию (как на Ostrov2).
    for item in CANOPY_TYPES:
        qty = max(0, int(canopies.get(item.key, 0)))
        if qty:
            amount = qty * item.price
            breakdown.append((f"{item.label} ×{qty}", amount))
            total += amount

    # Сап-борд по часам.
    if sup_hours:
        amount = sup_hours * SUP_PRICE_PER_HOUR
        breakdown.append((f"🏄 Сап-борд ×{sup_hours} ч", amount))
        total += amount

    # Доп. снаряжение.
    for item in EXTRA_EQUIPMENT:
        qty = max(0, int(equipment.get(item.key, 0)))
        if qty:
            amount = qty * item.price
            breakdown.append((f"{item.label} ×{qty}", amount))
            total += amount

    return Quote(
        people=people,
        ticket_price=current_ticket_price(today),  # базовая ставка (для справки)
        total=total,
        breakdown=breakdown,
    )
