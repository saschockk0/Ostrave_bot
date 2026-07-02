"""«Тур по Острову» — иммерсивная замена статичной «О вечеринке».

Не форма и не логистика: короткий путь из карточек, который шаг за шагом
погружает гостя в идею Острова — берег Волги, музыка в сосновом лесу, ночь
у костра — и в конце мягко зовёт оставить заявку. Та же дуга, что у «нити
пути» в заявке (journey.py), но для тех, кто пока только присматривается.

Навигация без FSM: номер карточки лежит в callback_data (`tour:<idx>`).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import countdown
import daypart
from keyboards import BTN_ABOUT, tour_kb

router = Router()

# Карточки тура: только атмосфера, без цен и правил (это берёт на себя FAQ).
_CARDS = (
    (
        "🌊 <b>Берег Волги</b>\n\n"
        "Телефон замолкает, лента новостей где-то далеко. Перед тобой — вода до "
        "горизонта, тёплый песок и запах реки. Здесь время идёт медленнее."
    ),
    (
        "🌲 <b>Сосновый лес</b> 🎶\n\n"
        "Между соснами протянут звук: днём — лёгкие сеты, ночью — глубокое техно "
        "до рассвета. Танцпол под открытым небом, хвоя под ногами, бас в груди."
    ),
    (
        "🔥 <b>Когда стемнеет</b>\n\n"
        "Костры у воды, баня с прыжком в Волгу, закаты, переходящие в рассветы. "
        "Кто-то у огня с гитарой, кто-то в палатке, кто-то всё ещё танцует.\n\n"
        "Соединяйся с космосом или отключайся, открывай чакры или закрывай — "
        "делай что в голову придёт. Главное — чтоб другим не мешало 🙏"
    ),
    (
        "🏝 <b>31 июля – 2 августа</b>\n\n"
        "Три дня без спешки, на берегу, со своими по духу. Места ограничены — "
        "лучше занять заранее.\n\nГотов на Остров? Жми кнопку ниже 👇"
    ),
)
_TOTAL = len(_CARDS)
_FOREST_IDX = 1   # карточка «Сосновый лес» — оживляем звуком по времени суток
_LAST_IDX = _TOTAL - 1  # финальная карточка (даты) — показываем отсчёт


def _progress(idx: int) -> str:
    """Мини-индикатор погружения: чем дальше карточка, тем больше открыт Остров."""
    dots = "".join("●" if i <= idx else "○" for i in range(_TOTAL))
    return f"<i>{dots}  ({idx + 1}/{_TOTAL})</i>"


def _card(idx: int) -> str:
    body = _CARDS[idx]
    # Лесная карточка про музыку — оживляем тем, что звучало бы прямо сейчас.
    if idx == _FOREST_IDX:
        body = f"{body}\n\n<i>{daypart.now_music_line()}</i>"
    # На финальной карточке (даты) показываем живой отсчёт до старта.
    elif idx == _LAST_IDX:
        cd = countdown.line()
        if cd:
            body = f"{body}\n\n{cd}"
    return f"{_progress(idx)}\n\n{body}"


@router.message(F.text == BTN_ABOUT)
async def open_tour(message: Message) -> None:
    await message.answer(_card(0), reply_markup=tour_kb(0, _TOTAL))


@router.callback_query(F.data.startswith("tour:"))
async def flip_tour(call: CallbackQuery) -> None:
    try:
        idx = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer()
        return
    idx = max(0, min(idx, _TOTAL - 1))
    await call.answer()
    try:
        await call.message.edit_text(_card(idx), reply_markup=tour_kb(idx, _TOTAL))
    except Exception:  # noqa: BLE001 — текст/кнопки могли не измениться
        pass
