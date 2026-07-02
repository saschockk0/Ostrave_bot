"""Outer-middleware: регистрирует в реестре каждого, кто пишет боту в личку.

Реестр (services.users) — база для рассылок: без него бот помнит только тех,
кто дошёл до заявки. Пишем best-effort: сбой БД не должен ронять обработку
апдейта. Запись троттлится в памяти, чтобы не дёргать SQLite на каждый тап
по inline-кнопкам.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from services import users

logger = logging.getLogger(__name__)

_WRITE_INTERVAL = 60  # сек между записями last_seen одного юзера


class TrackUsersMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._last_write: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            self._track(event)
        except Exception:  # noqa: BLE001 — учёт не должен мешать обработке
            logger.exception("Не удалось записать пользователя в реестр")
        return await handler(event, data)

    def _track(self, event: TelegramObject) -> None:
        # Учитываем только личные чаты: группа менеджеров — не аудитория рассылок.
        if isinstance(event, Message):
            chat, user = event.chat, event.from_user
        elif isinstance(event, CallbackQuery):
            chat, user = (event.message.chat if event.message else None), event.from_user
        else:
            return
        if not user or user.is_bot or not chat or chat.type != "private":
            return
        now = time.time()
        if now - self._last_write.get(user.id, 0) < _WRITE_INTERVAL:
            return
        self._last_write[user.id] = now
        users.upsert(user.id, user.username, user.first_name)
