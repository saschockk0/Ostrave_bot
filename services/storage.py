"""Локальное хранилище заявок на SQLite.

Это «единый источник правды» по заявкам: сюда всё пишется в первую очередь,
поэтому менеджеры могут работать с клиентами (смотреть список, менять статус)
даже когда Google Sheets не настроен. Таблица — лишь зеркало для удобства.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime

from models import Application

logger = logging.getLogger(__name__)

_DB_PATH = "leads.db"


def init(db_path: str) -> None:
    """Создаёт файл БД и таблицу при первом запуске. Вызывается из bot.py."""
    global _DB_PATH
    _DB_PATH = db_path
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT    NOT NULL,
                name           TEXT    NOT NULL,
                contact_method TEXT    NOT NULL DEFAULT 'Телефон',
                contact        TEXT    NOT NULL DEFAULT '',
                username       TEXT    NOT NULL,
                user_id        INTEGER,
                tickets        INTEGER NOT NULL,
                amount         INTEGER,
                status         TEXT    NOT NULL,
                source         TEXT
            )
            """
        )
        # Миграции для БД, созданных в ранних версиях.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(leads)")}
        if "amount" not in columns:
            conn.execute("ALTER TABLE leads ADD COLUMN amount INTEGER")
        if "source" not in columns:
            conn.execute("ALTER TABLE leads ADD COLUMN source TEXT")
        if "contact" not in columns:
            conn.execute("ALTER TABLE leads ADD COLUMN contact TEXT NOT NULL DEFAULT ''")
        if "contact_method" not in columns:
            conn.execute(
                "ALTER TABLE leads ADD COLUMN contact_method TEXT NOT NULL DEFAULT 'Телефон'"
            )
        # Раньше контакт хранился в колонке phone (NOT NULL, без дефолта).
        # Переносим данные в contact и удаляем устаревшую колонку — иначе новые
        # вставки без phone падают с "NOT NULL constraint failed: leads.phone".
        if "phone" in columns:
            conn.execute(
                "UPDATE leads SET contact = phone "
                "WHERE contact IS NULL OR contact = ''"
            )
            conn.execute("ALTER TABLE leads DROP COLUMN phone")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_application(row: sqlite3.Row) -> Application:
    return Application(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        name=row["name"],
        contact_method=row["contact_method"],
        contact=row["contact"],
        username=row["username"],
        user_id=row["user_id"],
        tickets=row["tickets"],
        amount=row["amount"],
        status=row["status"],
        source=row["source"] if "source" in row.keys() else None,
    )


def add(application: Application) -> Application:
    """Сохраняет заявку и проставляет ей присвоенный id (мутирует объект)."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads
                (created_at, name, contact_method, contact, username,
                 user_id, tickets, amount, status, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application.created_at.isoformat(timespec="seconds"),
                application.name,
                application.contact_method,
                application.contact,
                application.username,
                application.user_id,
                application.tickets,
                application.amount,
                application.status,
                application.source,
            ),
        )
        application.id = cur.lastrowid
    return application


def get(lead_id: int) -> Application | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return _row_to_application(row) if row else None


def latest_by_user(user_id: int | None) -> Application | None:
    """Последняя заявка этого Telegram-пользователя (для экрана «что дальше»)."""
    if not user_id:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM leads WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return _row_to_application(row) if row else None


def update_status(lead_id: int, status: str) -> Application | None:
    """Меняет статус заявки и возвращает обновлённую заявку (или None)."""
    with _connect() as conn:
        conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    return get(lead_id)


def recent(limit: int = 20, status: str | None = None) -> list[Application]:
    """Последние заявки, новейшие сверху; опционально фильтр по статусу."""
    query = "SELECT * FROM leads"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_application(r) for r in rows]


def counts_by_status() -> dict[str, int]:
    """Сводка «статус → количество» для дашборда менеджера."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM leads GROUP BY status"
        ).fetchall()
    return {r["status"]: r["n"] for r in rows}


def stats(since: datetime | None = None) -> dict:
    """Агрегаты по заявкам для /stats: количество, сумма, билеты, разбивка по статусам.

    `since` фильтрует по дате создания. created_at хранится ISO-строкой, поэтому
    лексикографическое сравнение `>=` корректно работает как сравнение дат.
    """
    where, params = "", []
    if since is not None:
        where = " WHERE created_at >= ?"
        params.append(since.isoformat(timespec="seconds"))
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS amount, "
            "COALESCE(SUM(tickets), 0) AS tickets FROM leads" + where,
            params,
        ).fetchone()
        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM leads" + where + " GROUP BY status",
            params,
        ).fetchall()
    return {
        "count": row["n"],
        "amount": row["amount"],
        "tickets": row["tickets"],
        "by_status": {r["status"]: r["n"] for r in status_rows},
    }
