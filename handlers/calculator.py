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
    "<i>Собери свой Остров: жми по услугам — каждый тап добавляет 1 в чек. "
    "Палатки можно подобрать под компанию одной кнопкой.</i>\n"
    "<i>💡 Билет считается по групповым тарифам («на двоих», «на четверых») — "
    "компанией выгоднее.</i>\n"
    "<i>🎪 Большой компанией удобно взять кухню-шатёр — общий навес, где собраться "
    "и готовить.</i>"
)


# Плитка и газ входят в комплект кухни-шатра (как на Ostrov2) — подсказываем,
# чтобы их не докупали отдельной строкой.
_CANOPY_INCLUDES = (
    "🎪 <i>В кухню-шатёр уже входят плитка и газ — отдельно брать не нужно.</i>"
)


def _has_canopy(data: dict) -> bool:
    return any(int(data.get(k, 0)) for k in CANOPY_TYPES_BY_KEY)


def _totals_block(quote: Quote) -> str:
    """Итог с разбивкой по моменту оплаты: аванс переводом сейчас и остальное на острове.

    Так человек сразу видит, что переводом бронирует только билет, а бо́льшая
    часть (вход на остров + аренда) платится на месте при выезде.
    """
    lines: list[str] = []
    if quote.advance:
        lines.append(f"💳 <b>Сейчас переводом</b> (бронь): {quote.advance} ₽")
    if quote.on_site:
        lines.append(f"🏝 <b>На острове</b> при выезде: {quote.on_site} ₽")
    lines.append(f"💰 <b>Всего за поездку: {quote.total} ₽</b>")
    return "\n".join(lines)


def _render_cart(data: dict) -> tuple[str, object]:
    """Текст экрана-чека (живая разбивка + итог) и клавиатура услуг."""
    quote = _quote(data)
    lines = "\n".join(f"• {label} — {amount} ₽" for label, amount in quote.breakdown)
    check = f"🧾 <b>В чеке:</b>\n{lines}\n\n" if lines else ""
    text = f"{_CART_INTRO}\n\n{check}{_totals_block(quote)}"
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
        f"{quote.summary_text()}\n"
        "─────────────\n"
        f"{_totals_block(quote)}\n\n"
        "ℹ️ Переводом бронируешь только билет на open air — вход на остров и "
        "аренда оплачиваются на месте при выезде. Финальную стоимость подтвердит "
        "менеджер."
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
