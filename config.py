"""Конфигурация бота: читает переменные окружения из .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Не задана переменная окружения {name}. "
            f"Скопируйте .env.example в .env и заполните значения."
        )
    return value


def _parse_int_env(name: str, raw: str, *, hint: str = "") -> int:
    """int() с понятным сообщением вместо сырого ValueError-трейсбека."""
    try:
        return int(raw.strip())
    except ValueError:
        suffix = f" {hint}" if hint else ""
        raise RuntimeError(
            f"{name} должно быть целым числом, а получено «{raw}».{suffix}"
        ) from None


def _parse_managers_chat_id(raw: str) -> tuple[int, int]:
    """Разбирает MANAGERS_CHAT_ID, поддерживая комбинированный формат.

    Помимо обычного «-1001234567890» принимает «-1001234567890/127» —
    chat_id и id топика форум-супергруппы вместе (именно так id топика
    выглядит в ссылке t.me/c/<chat>/<thread>). Возвращает (chat_id,
    thread_id); thread_id = 0, если топик не указан.
    """
    text = raw.strip()
    thread_id = 0
    if "/" in text:
        chat_part, _, thread_part = text.partition("/")
        text = chat_part.strip()
        thread_part = thread_part.strip()
        if thread_part:
            thread_id = _parse_int_env(
                "MANAGERS_CHAT_ID",
                thread_part,
                hint="После «/» ожидается номер топика, напр. -1001234567890/127.",
            )
    chat_id = _parse_int_env(
        "MANAGERS_CHAT_ID",
        text,
        hint="Для групп это обычно отрицательное число вида -1001234567890. "
        "Топик можно добавить через слэш: -1001234567890/127.",
    )
    return chat_id, thread_id


@dataclass(frozen=True)
class Config:
    bot_token: str
    managers_chat_id: int
    webapp_url: str
    db_path: str
    gsheet_id: str
    google_creds_path: str
    gsheet_worksheet: str
    # message_thread_id топика в группе менеджеров, куда слать заявки.
    # 0 — без топика (обычный чат / тема «General»).
    managers_topic_id: int = 0
    # Файл FSM-хранилища: его же читают сегмент «бросили заявку» и напоминания.
    fsm_db_path: str = "fsm.db"


def load_config() -> Config:
    managers_chat_id, topic_from_chat = _parse_managers_chat_id(_require("MANAGERS_CHAT_ID"))
    # Явный MANAGERS_TOPIC_ID имеет приоритет; иначе берём топик из
    # комбинированного MANAGERS_CHAT_ID (формат «-100…/127»).
    topic_env = os.getenv("MANAGERS_TOPIC_ID", "").strip()
    managers_topic_id = _parse_int_env("MANAGERS_TOPIC_ID", topic_env) if topic_env else topic_from_chat
    return Config(
        bot_token=_require("BOT_TOKEN"),
        managers_chat_id=managers_chat_id,
        # WEBAPP_URL опционален: основной путь — заявка прямо в чате.
        # Если задан, бот дополнительно покажет кнопку с Mini App-афишей.
        webapp_url=os.getenv("WEBAPP_URL", ""),
        # Файл локальной БД заявок (источник правды для менеджеров).
        db_path=os.getenv("DB_PATH", "leads.db"),
        # GSHEET_ID и creds опциональны: без них запись в таблицу просто отключается.
        gsheet_id=os.getenv("GSHEET_ID", ""),
        google_creds_path=os.getenv("GOOGLE_CREDS_PATH", "creds.json"),
        gsheet_worksheet=os.getenv("GSHEET_WORKSHEET", ""),
        # (Необязательно) топик в группе менеджеров. Узнать id: /chatinfo в топике.
        managers_topic_id=managers_topic_id,
        fsm_db_path=os.getenv("FSM_DB_PATH", "fsm.db"),
    )
