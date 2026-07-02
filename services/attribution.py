"""Источник перехода (deep-link payload) по user_id до отправки заявки.

Когда гость приходит по ссылке вида `https://t.me/<bot>?start=insta`, payload
`insta` запоминается здесь и привязывается к заявке в момент её отправки —
так менеджер видит, откуда пришёл клиент (UTM-атрибуция).

Хранение — в памяти процесса: атрибуция best-effort, при рестарте теряется
(источником правды остаётся уже сохранённая в БД заявка). Это типовой компромисс
для подобных ботов: deep-link и заявка обычно происходят в одной сессии.
"""
from __future__ import annotations

_MAX_LEN = 64  # Telegram ограничивает payload deep-link 64 символами
_sources: dict[int, str] = {}


def remember(user_id: int | None, payload: str | None) -> None:
    """Запоминает источник для пользователя (вызывается из /start <payload>)."""
    if not user_id or not payload:
        return
    cleaned = payload.strip()[:_MAX_LEN]
    if cleaned:
        _sources[user_id] = cleaned


def get(user_id: int | None) -> str | None:
    """Источник пользователя, если он переходил по deep-link в этой сессии."""
    if not user_id:
        return None
    return _sources.get(user_id)
