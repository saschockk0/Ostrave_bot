"""Оркестрация новой заявки: единая точка для всех способов её оставить.

И диалог в чате, и Mini App в итоге вызывают submit_application(), чтобы
логика «сохранить → уведомить менеджеров → зеркалировать в таблицу» жила
в одном месте.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from config import Config
from keyboards import manager_lead_kb
from models import Application
from services import attribution, sheets, storage

logger = logging.getLogger(__name__)

# Обёртка над конкретным способом доставки карточки (send_message / edit_text /
# answer): принимает текст и клавиатуру, возвращает корутину Telegram-вызова.
SendCard = Callable[[str, InlineKeyboardMarkup], Awaitable[Message]]


async def emit_lead_card(send: SendCard, application: Application) -> Message:
    """Отправляет/обновляет карточку заявки, переживая приватность клиента.

    Если deeplink-кнопка «Написать клиенту» отклонена настройками приватности
    клиента (BUTTON_USER_PRIVACY_RESTRICTED), Telegram отвергает всё сообщение.
    В этом случае повторяем без этой кнопки — менеджеры в любом случае получают
    карточку и кнопки статуса.
    """
    text = application.to_manager_message()
    try:
        return await send(text, manager_lead_kb(application.id, application.user_id))
    except TelegramBadRequest as exc:
        if not application.user_id or "BUTTON_USER_PRIVACY_RESTRICTED" not in str(exc):
            raise
        logger.warning(
            "Заявка #%s: приватность клиента отклонила deeplink, "
            "отправляю без кнопки «Написать клиенту»",
            application.id,
        )
        return await send(
            text,
            manager_lead_kb(application.id, application.user_id, include_contact=False),
        )


async def submit_application(bot: Bot, config: Config, application: Application) -> Application:
    """Сохраняет заявку, уведомляет менеджеров и пишет в таблицу.

    Возвращает заявку с присвоенным id. Сбой уведомления/таблицы не мешает
    сохранению — клиент в любом случае не теряется.
    """
    # Единая точка привязки источника: работает и для чата, и для Mini App.
    if application.source is None and application.user_id:
        application.source = attribution.get(application.user_id)

    storage.add(application)  # присваивает application.id

    try:
        await emit_lead_card(
            lambda text, kb: bot.send_message(
                config.managers_chat_id,
                text,
                reply_markup=kb,
                message_thread_id=config.managers_topic_id or None,
            ),
            application,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось отправить заявку #%s в чат менеджеров", application.id)

    sheets.append_application(config, application)
    return application
