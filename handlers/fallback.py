"""Глобальный fallback — ловит всё, что не обработали другие роутеры.

Должен подключаться последним в setup_routers(), чтобы у специфических
хендлеров был приоритет.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message

from config import Config
from keyboards import cancel_kb, main_kb

logger = logging.getLogger(__name__)
router = Router()

# Fallback — только для личных чатов с клиентами. В группе менеджеров бот не
# должен встревать в переписку («не понял…») — он отвечает там лишь на команды
# и кнопки карточек.


@router.message(StateFilter(default_state), F.chat.type == "private")
async def fallback_no_state(message: Message, config: Config) -> None:
    """Пользователь не в FSM — показываем главное меню."""
    logger.debug("fallback (no state): user=%s text=%r", message.from_user and message.from_user.id, message.text)
    await message.answer(
        "Не совсем понял 🤔 Давайте через кнопки меню — так будет быстрее 👇",
        reply_markup=main_kb(config.webapp_url),
    )


@router.message(F.chat.type == "private")
async def fallback_in_state(message: Message) -> None:
    """Пользователь внутри FSM прислал нечто непредвиденное (фото, стикер, голос…).

    Не сбрасываем состояние — просто напоминаем воспользоваться кнопками или отменить.
    """
    logger.debug("fallback (in state): user=%s text=%r", message.from_user and message.from_user.id, message.text)
    await message.answer(
        "Не понял этот ответ 🙈 Воспользуйтесь кнопками выше или нажмите «Отмена».",
        reply_markup=cancel_kb(),
    )
