"""Автонапоминание тем, кто начал заявку и бросил на полпути.

Фоновый цикл раз в полчаса просматривает FSM-хранилище: если гость завис в
диалоге заявки (NewLead*) сутки назад и до сих пор не вернулся — шлём одно
мягкое напоминание с кнопкой «Закончить заявку». Ровно одно: факт отправки
помечается в данных FSM, а окно ограничено тремя сутками, чтобы не будить
совсем остывших.

Пишем в fsm.db отдельным соединением — SQLite корректно разруливает доступ
с соединением SQLiteStorage в том же процессе.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

import journey
from config import Config
from keyboards import broadcast_kb
from middlewares.fsm_timeout import LAST_ACTIVE_KEY
from services import storage, users

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30 * 60      # период проверки, сек
MIN_AGE = 24 * 3600           # раньше суток не тревожим — может, ещё вернётся сам
MAX_AGE = 72 * 3600           # старше трёх суток — не спамим вдогонку
NUDGED_KEY = "_nudged"        # отметка «напоминание уже отправлено» в данных FSM

_TEXT = journey.with_step(
    journey.STAGE_ROAD,
    "Похоже, заявка на «Остров» осталась незаконченной 🙈\n"
    "Закончить можно за минуту — а места на open air разбирают 👇",
)
_KB = broadcast_kb(("▶️ Закончить заявку", "bcast:apply:nudge"))


async def run_loop(bot: Bot, config: Config) -> None:
    """Бесконечный цикл напоминаний; запускается фоновой задачей из bot.py."""
    await asyncio.sleep(60)  # даём боту подняться, прежде чем лезть в БД
    while True:
        try:
            sent = await _pass(bot, config)
            if sent:
                logger.info("Напоминания о брошенной заявке: отправлено %s", sent)
        except Exception:  # noqa: BLE001 — цикл должен пережить любой сбой
            logger.exception("Сбой прохода напоминаний")
        await asyncio.sleep(CHECK_INTERVAL)


# Разбор ключа FSM живёт в services.users — единая точка для формата ключа.
_parse_private_user_id = users.parse_fsm_private_user_id


async def _pass(bot: Bot, config: Config) -> int:
    """Один проход: находим зависшие заявки и шлём по одному напоминанию."""
    try:
        conn = sqlite3.connect(config.fsm_db_path)
    except sqlite3.OperationalError:
        return 0
    sent = 0
    try:
        try:
            rows = conn.execute(
                "SELECT key, data FROM fsm WHERE state LIKE 'NewLead%'"
            ).fetchall()
        except sqlite3.OperationalError:
            return 0  # таблицы ещё нет — бот только что развёрнут

        now = time.time()
        for key, raw in rows:
            user_id = _parse_private_user_id(key)
            if user_id is None:
                continue
            try:
                data = json.loads(raw or "{}")
            except ValueError:
                continue
            last = data.get(LAST_ACTIVE_KEY)
            if not last or data.get(NUDGED_KEY):
                continue
            if not MIN_AGE <= now - last <= MAX_AGE:
                continue
            if not users.is_reachable(user_id):
                continue
            if storage.latest_by_user(user_id) is not None:
                continue  # заявка уже есть (например, отправил через Mini App)

            try:
                await bot.send_message(user_id, _TEXT, reply_markup=_KB)
                sent += 1
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 1)
                continue  # не помечаем — доотправим в следующий проход
            except TelegramForbiddenError:
                users.mark_blocked(user_id)
            except Exception:  # noqa: BLE001
                logger.exception("Напоминание: не удалось отправить user_id=%s", user_id)
                continue

            # Помечаем и при блокировке: повторять такому юзеру всё равно нельзя.
            data[NUDGED_KEY] = 1
            conn.execute(
                "UPDATE fsm SET data = ? WHERE key = ?",
                (json.dumps(data, ensure_ascii=False), key),
            )
            conn.commit()
            await asyncio.sleep(0.1)
    finally:
        conn.close()
    return sent
