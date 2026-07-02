"""Настройка логирования: консоль + файл с ротацией по размеру.

Раньше логи шли только в stdout/stderr — их перехватывал лаунчер в bot.out/err.log
без ограничения размера, так что файл мог разрастаться между перезапусками.
Теперь приложение само пишет в ротируемый `bot.log` (+ N бэкапов): при достижении
лимита файл переименовывается в bot.log.1, bot.log.2 … а старые удаляются.

Параметры читаются из окружения напрямую (а не из Config), чтобы логирование
поднималось ДО загрузки конфига и ловило ошибки старта.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 МБ на файл
_DEFAULT_BACKUPS = 5


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def setup_logging() -> None:
    """Конфигурирует корневой логгер: всегда консоль, плюс файл с ротацией.

    Переменные окружения (все необязательны):
      LOG_LEVEL         — уровень (INFO по умолчанию)
      LOG_FILE          — путь к файлу лога (bot.log)
      LOG_MAX_BYTES     — размер файла до ротации (5 МБ)
      LOG_BACKUP_COUNT  — сколько бэкапов хранить (5)
    """
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    log_file = os.getenv("LOG_FILE", "bot.log")
    max_bytes = _int_env("LOG_MAX_BYTES", _DEFAULT_MAX_BYTES)
    backups = _int_env("LOG_BACKUP_COUNT", _DEFAULT_BACKUPS)

    formatter = logging.Formatter(_FORMAT)
    root = logging.getLogger()
    root.setLevel(level)
    # Повторный вызов безопасен: убираем ранее добавленные хендлеры.
    root.handlers.clear()

    console = logging.StreamHandler()  # как раньше — в stderr, попадает в bot.err.log
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Путь недоступен (нет прав/каталога) — не валим бота, остаёмся на консоли.
        root.warning("Не удалось открыть лог-файл %s, пишу только в консоль", log_file,
                     exc_info=True)
