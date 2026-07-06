"""Интерактивные «сборы рюкзака» на Остров — последний шаг перед дорогой.

Чек-лист с галочками: тап по пункту отмечает/снимает его. Состояние без FSM —
закодировано битовой маской в callback_data (`pack:<mask>:<idx>`), поэтому
переживает рестарт бота и не конфликтует с другими диалогами. Открывается
из ответа FAQ «Что взять с собой?» (callback `pack:open`).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards import packing_kb
from models import PACK_ITEMS

router = Router()

_TOTAL = len(PACK_ITEMS)


def render(mask: int) -> str:
    """Заголовок чек-листа + прогресс сборов (сами пункты — на кнопках)."""
    done = bin(mask & ((1 << _TOTAL) - 1)).count("1")
    text = (
        "🎒 <b>Сборы на Остров</b>\n\n"
        "Последний шаг перед дорогой — отметь, что уже в рюкзаке 👇\n\n"
        f"<b>Собрано: {done} из {_TOTAL}</b>"
    )
    if done == _TOTAL:
        text += "\n\n🏝 Рюкзак готов — Волга ждёт. Скоро увидимся 😍"
    return text


@router.callback_query(F.data == "pack:open")
async def open_pack(call: CallbackQuery) -> None:
    # Новым сообщением (а не edit) — чтобы открываться откуда угодно, не затирая
    # исходное (ответ FAQ или подтверждение принятой заявки «Готово #N»).
    await call.answer()
    await call.message.answer(render(0), reply_markup=packing_kb(0))


@router.callback_query(F.data.startswith("pack:"))
async def toggle_pack(call: CallbackQuery) -> None:
    try:
        _, mask_s, idx_s = call.data.split(":")
        mask, idx = int(mask_s), int(idx_s)
    except ValueError:
        await call.answer()
        return
    if 0 <= idx < _TOTAL:
        mask ^= (1 << idx)  # переключаем галочку
    await call.answer()
    try:
        await call.message.edit_text(render(mask), reply_markup=packing_kb(mask))
    except Exception:  # noqa: BLE001 — текст/кнопки могли не измениться
        pass
