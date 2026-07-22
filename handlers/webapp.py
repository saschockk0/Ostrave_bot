"""Приём заявки из Mini App (опциональный путь).

Когда пользователь жмёт «Отправить» в веб-аппе, тот вызывает
Telegram.WebApp.sendData(...), и боту прилетает message.web_app_data с JSON.
Здесь мы его парсим и отдаём в тот же services.leads.submit_application,
что и обычный диалог в чате.
"""
from __future__ import annotations

import json
import logging

from aiogram import F, Router
from aiogram.types import Message

from config import Config
from models import Application
from services import leads

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.web_app_data)
async def on_webapp_data(message: Message, config: Config) -> None:
    raw = message.web_app_data.data
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("web_app_data не распарсился: %r", raw)
        await message.answer("Не удалось прочитать заявку 😕 Откройте форму и попробуйте ещё раз.")
        return

    user = message.from_user
    try:
        application = Application.from_webapp(
            data,
            fallback_username=user.username if user else None,
            user_id=user.id if user else None,
        )
    except ValueError:
        await message.answer("Кажется, не хватает данных 🙈 Откройте форму и заполните имя и контакт.")
        return

    application = await leads.submit_application(message.bot, config, application)
    await message.answer(
        f"🎉 <b>Готово!</b> Заявка <b>#{application.id}</b> принята.\n\n"
        "Менеджер совсем скоро свяжется с вами. До встречи на берегу! 🌅"
    )
