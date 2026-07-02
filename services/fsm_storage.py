"""Персистентное FSM-хранилище на SQLite — диалоги переживают перезапуск бота.

aiogram из коробки даёт только MemoryStorage (теряется при рестарте) и
Redis/Mongo (лишняя инфраструктура). Проект уже на SQLite, поэтому делаем лёгкое
хранилище в отдельном файле: недозаполненные заявки и шаги калькулятора не
теряются при перезапуске.

Одна строка на ключ FSM: состояние (строка) + данные (JSON). Доступ из event-loop
сериализуется asyncio-локом; пустые записи удаляются, чтобы таблица не росла.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from typing import Any, Dict, Mapping, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder, StateType, StorageKey

logger = logging.getLogger(__name__)


class SQLiteStorage(BaseStorage):
    """FSM-хранилище на SQLite (персистентное, без внешних зависимостей)."""

    def __init__(self, db_path: str = "fsm.db") -> None:
        self._db_path = db_path
        # with_bot_id/destiny — чтобы ключ был уникален и совпадал со стратегией aiogram.
        self._keys = DefaultKeyBuilder(with_bot_id=True, with_destiny=True)
        self._lock = asyncio.Lock()
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS fsm ("
            " key   TEXT PRIMARY KEY,"
            " state TEXT,"
            " data  TEXT NOT NULL DEFAULT '{}'"
            ")"
        )
        self._conn.commit()

    def _key(self, key: StorageKey) -> str:
        return self._keys.build(key)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        k = self._key(key)
        async with self._lock:
            if value is None:
                # Сброс состояния: если данных тоже нет — удаляем строку целиком.
                row = self._conn.execute("SELECT data FROM fsm WHERE key=?", (k,)).fetchone()
                if row is None or row[0] in (None, "", "{}"):
                    self._conn.execute("DELETE FROM fsm WHERE key=?", (k,))
                else:
                    self._conn.execute("UPDATE fsm SET state=NULL WHERE key=?", (k,))
            else:
                self._conn.execute(
                    "INSERT INTO fsm(key, state, data) VALUES(?, ?, '{}') "
                    "ON CONFLICT(key) DO UPDATE SET state=excluded.state",
                    (k, value),
                )
            self._conn.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        k = self._key(key)
        async with self._lock:
            row = self._conn.execute("SELECT state FROM fsm WHERE key=?", (k,)).fetchone()
        return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        k = self._key(key)
        async with self._lock:
            if not data:
                # Пустые данные: если и состояния нет — удаляем строку.
                row = self._conn.execute("SELECT state FROM fsm WHERE key=?", (k,)).fetchone()
                if row is None or row[0] is None:
                    self._conn.execute("DELETE FROM fsm WHERE key=?", (k,))
                else:
                    self._conn.execute("UPDATE fsm SET data='{}' WHERE key=?", (k,))
            else:
                payload = json.dumps(dict(data), ensure_ascii=False)
                self._conn.execute(
                    "INSERT INTO fsm(key, state, data) VALUES(?, NULL, ?) "
                    "ON CONFLICT(key) DO UPDATE SET data=excluded.data",
                    (k, payload),
                )
            self._conn.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        k = self._key(key)
        async with self._lock:
            row = self._conn.execute("SELECT data FROM fsm WHERE key=?", (k,)).fetchone()
        if not row or not row[0]:
            return {}
        try:
            return json.loads(row[0])
        except (ValueError, TypeError):
            logger.warning("Повреждённые FSM-данные для %s — игнорирую", k)
            return {}

    async def close(self) -> None:
        async with self._lock:
            self._conn.close()
