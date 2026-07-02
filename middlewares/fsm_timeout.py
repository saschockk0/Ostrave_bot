"""Outer-middleware: авто-сброс заброшенного диалога (FSM) по таймауту.

У aiogram нет встроенного таймаута состояний — это типовой приём из надёжных
ботов: храним время последней активности в данных FSM и, если гость вернулся
посреди диалога после долгой паузы, тихо сбрасываем состояние, чтобы он начал
с чистого листа, а не застрял в недозаполненной заявке.

Регистрируется как outer-middleware на message/callback_query (см. bot.py). В
aiogram FSM-контекст ставится outer-middleware уровня update, поэтому `state`
уже доступен здесь, и сброс происходит ДО выбора хендлера: «протухший» апдейт
проваливается в обработчики состояния по умолчанию (меню/нчало диалога).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 30 * 60  # полчаса без активности — считаем диалог брошенным
# Ключ с подчёркиванием, чтобы не путать с «бизнес»-полями заявки в данных FSM.
LAST_ACTIVE_KEY = "_last_active"


class FSMTimeoutMiddleware(BaseMiddleware):
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.ttl = ttl_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext | None = data.get("state")
        if state is not None and await state.get_state() is not None:
            sdata = await state.get_data()
            last = sdata.get(LAST_ACTIVE_KEY)
            now = time.time()
            if last is not None and now - last > self.ttl:
                await state.clear()
                logger.info("FSM сброшен по таймауту (%.0f c простоя)", now - last)
                if isinstance(event, CallbackQuery):
                    # Старая inline-кнопка после паузы — гасим «часики» и подсказываем.
                    try:
                        await event.answer("Сессия истекла — начните заново 🙂", show_alert=True)
                    except Exception:  # noqa: BLE001 — колбэк мог устареть
                        pass
            else:
                # Освежаем отметку активности (заодно инициализируем при первом шаге).
                await state.update_data(**{LAST_ACTIVE_KEY: now})
        return await handler(event, data)
