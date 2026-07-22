"""Калькулятор стоимости поездки — единый экран-чек.

Все услуги (человек, палатки, сап, снаряжение) показаны кнопками на одном
экране. Тап по услуге добавляет 1 единицу в чек, сверху — живой чек и итог.
«🧹 Обнулить чек» сбрасывает всё к старту, «✅ Посчитать» показывает итог с
разбивкой и кнопкой «Оставить заявку». Состав хранится в FSMContext и
прокидывается в диалог заявки для менеджера.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import Config
from handlers.application import begin_application
from keyboards import BTN_CALC, calc_cart_kb, calc_result_kb, main_kb
from models import MAX_TICKETS, ticket_price_for
from pricing import (
    CANOPY_TYPES_BY_KEY,
    EXTRA_EQUIPMENT_BY_KEY,
    TENT_TYPES_BY_KEY,
    Quote,
    build_quote,
    suggest_canopy_key,
)

router = Router()

# Все ключи-счётчики калькулятора.
_COUNTER_KEYS = [
    "people", "sup", *TENT_TYPES_BY_KEY, *CANOPY_TYPES_BY_KEY, *EXTRA_EQUIPMENT_BY_KEY,
]
# Границы значений (минимум, максимум). По умолчанию 0..20.
# Кухня-шатёр берут один-два на компанию — ограничим, чтобы случайный тап не
# накрутил абсурд (Эверест ×20 = 200 000 ₽). Для большой группы хватит пары.
_LIMITS = {
    "people": (1, MAX_TICKETS),
    "sup": (0, 12),
    **{k: (0, 3) for k in CANOPY_TYPES_BY_KEY},
}
_DEFAULT_LIMIT = (0, 20)


class Calc(StatesGroup):
    build = State()    # экран-чек: набираем услуги кнопками
    result = State()   # экран итога


# --- вспомогательные ------------------------------------------------------
def _limit(key: str) -> tuple[int, int]:
    return _LIMITS.get(key, _DEFAULT_LIMIT)


def _fresh_data() -> dict:
    data = {key: 0 for key in _COUNTER_KEYS}
    data["people"] = 1  # минимум один человек
    return data


def _quote(data: dict) -> Quote:
    people = int(data.get("people", 0))
    return build_quote(
        people=people,
        tents={k: data.get(k, 0) for k in TENT_TYPES_BY_KEY},
        canopies={k: data.get(k, 0) for k in CANOPY_TYPES_BY_KEY},
        sup_hours=data.get("sup", 0),
        equipment={k: data.get(k, 0) for k in EXTRA_EQUIPMENT_BY_KEY},
        # Билет на open air — по тем же групповым тарифам («на двоих» / «на
        # четверых»), что и в прямой заявке, чтобы суммы не расходились.
        open_air_total=ticket_price_for(people) if people > 0 else 0,
    )


_CART_INTRO = (
    "🧮 <b>Калькулятор поездки</b>\n\n"
    "<i>Жми по услугам — каждый тап добавляет 1 в чек.</i>\n\n"
    "❗️ <b>Платишь в два приёма, это две РАЗНЫЕ оплаты:</b>\n"
    "1️⃣ билет — <b>сейчас переводом</b> (бронь)\n"
    "2️⃣ остров и аренда — <b>потом, на месте при выезде</b>\n\n"
    "⛺ Палатки и снаряжение — по желанию: своё привезёшь — за аренду не платишь."
)


# Плитка и газ входят в комплект кухни-шатра (как на Ostrov2) — подсказываем,
# чтобы их не докупали отдельной строкой.
_CANOPY_INCLUDES = (
    "🎪 <i>В кухню-шатёр уже входят плитка и газ — отдельно брать не нужно.</i>"
)

# Что покрывает вход на остров — показываем прямо под строкой в чеке, чтобы
# самая большая цифра сразу объясняла свою ценность. Сап-борды сюда НЕ входят —
# они платная почасовая аренда, отдельная кнопка в калькуляторе.
_ISLAND_INCLUDES = (
    "   <i>входит: 🛥 трансфер туда-обратно, ⛵ парусные катамараны, "
    "🏐 волейбол, 🧖 баня и другие активности на острове</i>"
)

# Что даёт билет на open air — чтобы и первая строка чека объясняла себя сама.
_TICKET_INCLUDES = "сама тусовка: музыка, ночные сеты и атмосфера летней ночи"


def _per_person(amount: int, people: int) -> str:
    """«по N ₽ с человека» — при неделимой сумме с пометкой «примерно»."""
    if amount % people == 0:
        return f"по {amount // people} ₽ с человека"
    return f"примерно по {round(amount / people)} ₽ с человека"


def _has_canopy(data: dict) -> bool:
    return any(int(data.get(k, 0)) for k in CANOPY_TYPES_BY_KEY)


def _cheque_body(quote: Quote) -> str:
    """Чек, разбитый на ДВЕ отдельные оплаты, чтобы их нельзя было перепутать.

    Блок 1 — что платится сейчас переводом (бронь билета), блок 2 — что
    платится на острове при выезде (вход + аренда). Под каждым блоком свой
    подытог, внизу — общая сумма поездки.
    """
    parts: list[str] = []
    if quote.advance_items:
        lines: list[str] = []
        for label, amount in quote.advance_items:
            lines.append(f"• {label} — {amount} ₽")
            # Под билетом — что это за деньги и почём выходит на человека
            # (групповой тариф: вчетвером дешевле, чем поодиночке).
            if label.startswith("🎟 Билет"):
                note = _TICKET_INCLUDES
                if quote.people > 1 and amount:
                    note += f" · {_per_person(amount, quote.people)}"
                lines.append(f"   <i>{note}</i>")
        rows = "\n".join(lines)
        parts.append(
            "1️⃣ <b>Платишь СЕЙЧАС переводом</b> (бронь):\n"
            f"{rows}\n"
            f"💳 <b>Перевести сейчас: {quote.advance} ₽</b>"
        )
    if quote.on_site_items:
        lines: list[str] = []
        for label, amount in quote.on_site_items:
            lines.append(f"• {label} — {amount} ₽")
            # Под входом на остров — расшифровка, что уже оплачено этой строкой.
            if label.startswith("🏝 Вход на остров"):
                lines.append(_ISLAND_INCLUDES)
        rows = "\n".join(lines)
        parts.append(
            "2️⃣ <b>Платишь ПОТОМ на острове</b> (при выезде):\n"
            f"{rows}\n"
            f"🏝 <b>Оплатить на месте: {quote.on_site} ₽</b>"
        )
    body = "\n\n".join(parts)
    total_line = f"💰 <b>Всего за поездку: {quote.total} ₽</b>"
    if quote.people > 1 and quote.total:
        total_line += f"\n<i>Это {_per_person(quote.total, quote.people)} за все три дня</i>"
    return f"{body}\n\n{total_line}"


def _render_cart(data: dict) -> tuple[str, object]:
    """Текст экрана-чека (живой чек из двух оплат) и клавиатура услуг."""
    quote = _quote(data)
    text = f"{_CART_INTRO}\n\n{_cheque_body(quote)}"
    if _has_canopy(data):
        text += f"\n\n{_CANOPY_INCLUDES}"
    return text, calc_cart_kb(data)


async def _rerender(call: CallbackQuery, data: dict) -> None:
    text, kb = _render_cart(data)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:  # noqa: BLE001 — содержимое могло не измениться
        pass


# --- вход -----------------------------------------------------------------
@router.message(F.text == BTN_CALC)
@router.message(Command("calc"))
async def open_calculator(message: Message, state: FSMContext) -> None:
    await state.clear()
    data = _fresh_data()
    await state.set_state(Calc.build)
    await state.update_data(**data)
    text, kb = _render_cart(data)
    await message.answer(text, reply_markup=kb)


# --- набор чека -----------------------------------------------------------
@router.callback_query(Calc.build, F.data.startswith("calc:add:"))
async def calc_add(call: CallbackQuery, state: FSMContext) -> None:
    """Тап по услуге — добавляем 1 ед. в чек (до верхней границы)."""
    key = call.data.split(":", 2)[2]
    if key not in _COUNTER_KEYS:
        await call.answer()
        return
    data = await state.get_data()
    current = int(data.get(key, 0))
    _, hi = _limit(key)
    if current >= hi:
        await call.answer("Уже максимум")
        return
    value = current + 1
    await state.update_data(**{key: value})
    data[key] = value
    await call.answer()
    await _rerender(call, data)


@router.callback_query(Calc.build, F.data == "calc:suggest")
async def calc_suggest(call: CallbackQuery, state: FSMContext) -> None:
    """Авто-подбор палаток под число людей: пары в 2-местные, остаток — 1-местная."""
    data = await state.get_data()
    people = int(data.get("people", 1))
    data["tent2"] = people // 2
    data["tent1"] = people % 2
    data["tent3"] = 0
    await state.update_data(tent1=data["tent1"], tent2=data["tent2"], tent3=0)
    await call.answer(f"Подобрано под {people} чел.")
    await _rerender(call, data)


@router.callback_query(Calc.build, F.data == "calc:canopy")
async def calc_canopy(call: CallbackQuery, state: FSMContext) -> None:
    """Авто-подбор кухни-шатра под размер компании: ставим один подходящий, прочие в 0."""
    data = await state.get_data()
    people = int(data.get("people", 1))
    chosen = suggest_canopy_key(people)
    updates = {k: (1 if k == chosen else 0) for k in CANOPY_TYPES_BY_KEY}
    await state.update_data(**updates)
    data.update(updates)
    await call.answer(f"Шатёр под {people} чел.: {CANOPY_TYPES_BY_KEY[chosen].label}")
    await _rerender(call, data)


@router.callback_query(Calc.build, F.data == "calc:reset")
async def calc_reset(call: CallbackQuery, state: FSMContext) -> None:
    """«Обнулить чек» — сбрасываем все услуги к старту (1 человек, остальное 0)."""
    data = _fresh_data()
    await state.update_data(**data)
    await call.answer("Чек обнулён")
    await _rerender(call, data)


# --- итог -----------------------------------------------------------------
@router.callback_query(Calc.build, F.data == "calc:done")
async def calc_done(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await call.answer()
    quote = _quote(data)
    await state.set_state(Calc.result)
    canopy_note = f"\n\n{_CANOPY_INCLUDES}" if _has_canopy(data) else ""
    text = (
        "🏝 <b>Твой Остров собран</b>\n\n"
        "Вот из чего сложатся три дня на берегу:\n\n"
        f"{_cheque_body(quote)}\n\n"
        "ℹ️ Билет и остров — это две <b>отдельные</b> оплаты: билет бронируешь "
        "сейчас переводом, а за остров и аренду платишь потом, на месте при "
        "выезде. Скрытых доплат нет — платишь только за то, что в чеке. "
        "Финальную стоимость подтвердит менеджер."
        f"{canopy_note}\n\n"
        "🌅 Останется только собрать своих и приехать на Волгу."
    )
    try:
        await call.message.edit_text(text, reply_markup=calc_result_kb())
    except Exception:  # noqa: BLE001 — сообщение могло быть уже изменено
        await call.message.answer(text, reply_markup=calc_result_kb())


# --- экран итога ----------------------------------------------------------
@router.callback_query(Calc.result, F.data == "calc:edit")
async def calc_edit(call: CallbackQuery, state: FSMContext) -> None:
    """«Пересчитать» — вернуться к экрану-чеку, сохранив набранное."""
    data = await state.get_data()
    await state.set_state(Calc.build)
    await call.answer()
    await _rerender(call, data)


@router.callback_query(Calc.result, F.data == "calc:apply")
async def calc_apply(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    quote = _quote(data)
    await call.answer()
    # Снимаем кнопки итога, чтобы не нажали повторно.
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass
    await begin_application(
        call.message, state, call.from_user,
        tickets=quote.people, amount=quote.total, extras_note=quote.summary_text(),
    )


# --- выход (с любого экрана) ----------------------------------------------
@router.callback_query(StateFilter(Calc), F.data.in_({"calc:cancel", "calc:menu"}))
async def calc_exit(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    await call.answer()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 — сообщение могло быть уже изменено
        pass
    await call.message.answer("Главное меню 👇", reply_markup=main_kb(config.webapp_url))
