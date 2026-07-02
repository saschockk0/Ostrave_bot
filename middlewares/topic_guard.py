"""Outer-middleware: в группе бот активен только в одном топике.

Личные чаты с клиентами не трогаем — там идёт оформление заявок. В группе же
бот реагирует (и отвечает) только на апдейты из настроенного топика
(config.managers_topic_id): сообщения в других топиках и в «General»
игнорируются. Если топик не задан (managers_topic_id == 0) — ограничения нет.

Команда /chatinfo разрешена в любом топике: она нужна, чтобы (пере)настроить,
куда слать заявки.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Chat, Message, TelegramObject

from config import Config

logger = logging.getLogger(__name__)

_SETUP_COMMAND = "/chatinfo"


class TopicGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        config: Config | None = data.get("config")
        if config is None or not config.managers_topic_id:
            return await handler(event, data)  # ограничение не настроено

        chat, thread, text = self._extract(event)
        # Нет чата или личка — пропускаем (клиентов не ограничиваем).
        if chat is None or chat.type not in ("group", "supergroup"):
            return await handler(event, data)

        # /chatinfo нужен для настройки — разрешаем в любом топике.
        if text and text.lstrip().startswith(_SETUP_COMMAND):
            return await handler(event, data)

        in_topic = chat.id == config.managers_chat_id and thread == config.managers_topic_id
        if in_topic:
            return await handler(event, data)

        # Не наш топик — тихо игнорируем; у кнопок гасим «часики».
        if isinstance(event, CallbackQuery):
            try:
                await event.answer()
            except Exception:  # noqa: BLE001 — колбэк мог устареть
                pass
        logger.debug("Игнор апдейта вне топика: chat=%s thread=%s", chat.id, thread)
        return None

    @staticmethod
    def _extract(event: TelegramObject) -> tuple[Chat | None, int | None, str | None]:
        if isinstance(event, Message):
            return event.chat, event.message_thread_id, event.text
        if isinstance(event, CallbackQuery):
            msg = event.message
            if msg is not None:
                return msg.chat, getattr(msg, "message_thread_id", None), None
        return None, None, None
