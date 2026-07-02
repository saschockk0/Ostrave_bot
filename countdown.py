"""Обратный отсчёт до Острова — ощущение «с каждым днём ближе».

Дата события живёт в pricing.EVENT_START_DATE; здесь только человеко-понятная
строка с правильным склонением «день/дня/дней» и аккуратной обработкой самих
дней фестиваля (31 июля – 2 августа) и времени после него.
"""
from __future__ import annotations

from datetime import date

from pricing import EVENT_START_DATE

# Остров длится три дня (Пт–Вс): старт, старт+1, старт+2.
_EVENT_DAYS = 3


def days_left(today: date | None = None) -> int:
    """Сколько дней осталось до старта (отрицательное — событие уже началось)."""
    today = today or date.today()
    return (EVENT_START_DATE - today).days


def _plural_days(n: int) -> str:
    n = abs(n)
    if 11 <= n % 100 <= 14:
        return "дней"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"


def line(today: date | None = None) -> str | None:
    """Короткая строка отсчёта или None, если Остров уже позади.

    Возвращает None после окончания фестиваля — чтобы не показывать протухший
    счётчик до следующего сезона.
    """
    d = days_left(today)
    if d > 0:
        return f"🏝 До Острова — <b>{d}</b> {_plural_days(d)}"
    if d >= -(_EVENT_DAYS - 1):  # идёт прямо сейчас (старт .. старт+2)
        return "🔥 Остров идёт прямо сейчас — мы на берегу!"
    return None
