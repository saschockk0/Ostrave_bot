"""Точка входа: создаёт бота, диспетчер и запускает long polling."""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import load_config
from handlers import setup_routers
from logging_setup import setup_logging
from middlewares.fsm_timeout import FSMTimeoutMiddleware
from middlewares.topic_guard import TopicGuardMiddleware
from services import storage
from services.fsm_storage import SQLiteStorage

logger = logging.getLogger(__name__)


def _build_fsm_storage() -> BaseStorage:
    """Персистентное FSM-хранилище; при сбое — деградация на MemoryStorage."""
    path = os.getenv("FSM_DB_PATH", "fsm.db")
    try:
        return SQLiteStorage(path)
    except Exception:  # noqa: BLE001 — нет прав/диска: бот должен подняться
        logger.exception("Не удалось открыть FSM-хранилище %s, использую MemoryStorage", path)
        return MemoryStorage()


async def _set_commands(bot: Bot) -> None:
    """Команды, видимые в меню бота (кнопка «/» в чате)."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать / открыть меню"),
            BotCommand(command="apply", description="Оставить заявку"),
            BotCommand(command="calc", description="Калькулятор стоимости"),
        ]
    )


async def main() -> None:
    setup_logging()  # консоль + ротируемый bot.log (см. logging_setup.py)
    config = load_config()
    storage.init(config.db_path)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=_build_fsm_storage())
    # В группе бот активен только в одном топике (личные чаты не ограничиваем).
    # Ставим первым, чтобы лишние групповые апдейты отсеивались сразу.
    dp.message.outer_middleware(TopicGuardMiddleware())
    dp.callback_query.outer_middleware(TopicGuardMiddleware())
    # Авто-сброс брошенных диалогов: если гость вернулся после долгой паузы
    # посреди FSM — состояние тихо обнуляется, чтобы он начал заново.
    dp.message.outer_middleware(FSMTimeoutMiddleware())
    dp.callback_query.outer_middleware(FSMTimeoutMiddleware())
    dp.include_router(setup_routers())

    await _set_commands(bot)
    # config доступен во всех хендлерах как параметр `config: Config`.
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, config=config)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
