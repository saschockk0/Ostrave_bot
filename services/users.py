"""Реестр пользователей бота: каждый, кто хоть раз писал боту.

Заявки (leads) знают только дошедших до конца воронки. Здесь запоминается
любой контакт с ботом — это база для рассылок «тем, кто ещё думает».
Живёт в той же SQLite-БД, что и заявки (см. services.storage).

Флаги доставки:
  • blocked — юзер заблокировал бота (узнаём при рассылке; больше не шлём);
  • muted   — юзер нажал «Больше не присылать» (не шлём рассылки и напоминания).

Колонка source — источник первого перехода (first-touch deep-link): в отличие
от services.attribution (память процесса, last-touch для заявки) переживает
рестарт бота.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime

from models import STATUS_IN_PROGRESS, STATUS_NEW, STATUS_PAID

logger = logging.getLogger(__name__)

_DB_PATH = "leads.db"
_MAX_SOURCE_LEN = 64  # как в services.attribution — лимит payload deep-link

# Сегменты рассылок: ключ (хранится в callback_data) → подпись для менеджера.
SEGMENTS = {
    "thinking": "🤔 Думают — без заявки",
    "abandoned": "🚪 Бросили заявку на полпути",
    "unpaid": "⏳ Заявка есть, оплаты нет",
    "paid": "💰 Оплатившие",
    "all": "👥 Все, кто писал боту",
}


def init(db_path: str) -> None:
    """Создаёт таблицу users при первом запуске. Вызывается из bot.py."""
    global _DB_PATH
    _DB_PATH = db_path
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT    NOT NULL DEFAULT '',
                first_name TEXT    NOT NULL DEFAULT '',
                first_seen TEXT    NOT NULL,
                last_seen  TEXT    NOT NULL,
                source     TEXT,
                blocked    INTEGER NOT NULL DEFAULT 0,
                muted      INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean_username(username: str | None) -> str:
    uname = (username or "").lstrip("@").strip()
    return "" if uname == "не задан" else uname


# --- регистрация активности -----------------------------------------------
def upsert(user_id: int, username: str | None = None,
           first_name: str | None = None) -> None:
    """Запоминает пользователя / освежает last_seen. Вызывается на каждый апдейт."""
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users(user_id, username, first_name, first_seen, last_seen) "
            "VALUES(?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "  username = excluded.username, "
            "  first_name = excluded.first_name, "
            "  last_seen = excluded.last_seen",
            (user_id, _clean_username(username), first_name or "", now, now),
        )


def set_source(user_id: int | None, source: str | None) -> None:
    """Источник первого перехода (first-touch): повторные заходы его не затирают."""
    if not user_id or not source:
        return
    cleaned = source.strip()[:_MAX_SOURCE_LEN]
    if not cleaned:
        return
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(user_id, first_seen, last_seen) VALUES(?, ?, ?)",
            (user_id, now, now),
        )
        conn.execute(
            "UPDATE users SET source = ? "
            "WHERE user_id = ? AND (source IS NULL OR source = '')",
            (cleaned, user_id),
        )


def get_source(user_id: int | None) -> str | None:
    if not user_id:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT source FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row[0] if row and row[0] else None


# --- флаги доставки ---------------------------------------------------------
def mark_blocked(user_id: int, blocked: bool = True) -> None:
    """Юзер заблокировал бота (TelegramForbiddenError при отправке)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET blocked = ? WHERE user_id = ?",
            (1 if blocked else 0, user_id),
        )


def set_muted(user_id: int, muted: bool) -> None:
    """Кнопка «Больше не присылать» под рассылкой."""
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET muted = ? WHERE user_id = ?",
            (1 if muted else 0, user_id),
        )


def is_reachable(user_id: int) -> bool:
    """Можно ли слать этому юзеру рассылки/напоминания."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT blocked, muted FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return bool(row) and not row[0] and not row[1]


# --- разовый посев из уже накопленных данных --------------------------------
def seed_from_leads() -> None:
    """Заполняет users из уже существующих заявок (идемпотентно)."""
    now = _now()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT user_id, username, MIN(created_at) FROM leads "
            "WHERE user_id IS NOT NULL GROUP BY user_id"
        ).fetchall()
        for user_id, username, created in rows:
            conn.execute(
                "INSERT OR IGNORE INTO users(user_id, username, first_seen, last_seen) "
                "VALUES(?, ?, ?, ?)",
                (user_id, _clean_username(username), created or now, created or now),
            )


def seed_from_fsm(fsm_db_path: str) -> None:
    """Заполняет users из ключей FSM-хранилища — там лежат незакрытые диалоги."""
    now = _now()
    ids = _fsm_user_ids(fsm_db_path)
    if not ids:
        return
    with _connect() as conn:
        for user_id in ids:
            conn.execute(
                "INSERT OR IGNORE INTO users(user_id, first_seen, last_seen) "
                "VALUES(?, ?, ?)",
                (user_id, now, now),
            )


# --- сегменты для рассылок ---------------------------------------------------
def _fsm_rows(fsm_db_path: str) -> list[tuple[str, str | None]]:
    """(key, state) из fsm.db; пустой список, если файла/таблицы ещё нет."""
    try:
        conn = sqlite3.connect(f"file:{fsm_db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return []
    try:
        return conn.execute("SELECT key, state FROM fsm").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _fsm_user_ids(fsm_db_path: str, state_prefix: str | None = None) -> set[int]:
    """user_id из ключей FSM (только личные чаты: chat_id == user_id).

    Формат ключа задаёт DefaultKeyBuilder(with_bot_id=True, with_destiny=True):
    «bot_id:chat_id:user_id:destiny». `state_prefix` фильтрует по состоянию,
    напр. "NewLead" — только незаконченные заявки.
    """
    ids: set[int] = set()
    for key, state in _fsm_rows(fsm_db_path):
        if state_prefix is not None and not (state or "").startswith(state_prefix):
            continue
        parts = key.split(":")
        if len(parts) < 3:
            continue
        chat_id, user_id = parts[1], parts[2]
        if chat_id != user_id or not user_id.isdigit():
            continue
        ids.add(int(user_id))
    return ids


def segment_user_ids(segment: str, fsm_db_path: str = "fsm.db") -> list[int]:
    """user_id сегмента; blocked/muted исключены из всех сегментов."""
    base = "SELECT user_id FROM users WHERE blocked = 0 AND muted = 0"
    if segment == "all":
        with _connect() as conn:
            return [r[0] for r in conn.execute(base)]
    if segment == "thinking":
        with _connect() as conn:
            return [
                r[0] for r in conn.execute(
                    base + " AND user_id NOT IN "
                    "(SELECT user_id FROM leads WHERE user_id IS NOT NULL)"
                )
            ]
    if segment == "abandoned":
        # Незаконченный диалог заявки и ни одной отправленной — самые «горячие».
        in_dialog = _fsm_user_ids(fsm_db_path, state_prefix="NewLead")
        return sorted(set(segment_user_ids("thinking")) & in_dialog)
    if segment in ("unpaid", "paid"):
        statuses = (STATUS_NEW, STATUS_IN_PROGRESS) if segment == "unpaid" else (STATUS_PAID,)
        marks = ", ".join("?" for _ in statuses)
        # Смотрим последнюю заявку юзера — прежние отменённые/дубли не в счёт.
        query = (
            "SELECT u.user_id FROM users u JOIN leads l ON l.user_id = u.user_id "
            "WHERE u.blocked = 0 AND u.muted = 0 "
            "  AND l.id = (SELECT MAX(id) FROM leads WHERE user_id = u.user_id) "
            f"  AND l.status IN ({marks})"
        )
        with _connect() as conn:
            return [r[0] for r in conn.execute(query, statuses)]
    raise ValueError(f"Неизвестный сегмент: {segment}")


def segment_counts(fsm_db_path: str = "fsm.db") -> dict[str, int]:
    """Размер каждого сегмента — для экрана выбора в /broadcast."""
    return {seg: len(segment_user_ids(seg, fsm_db_path)) for seg in SEGMENTS}
