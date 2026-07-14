"""Работа менеджеров с заявками внутри Telegram.

Доступно только в чате менеджеров (config.managers_chat_id):
  • inline-кнопки статуса под каждой заявкой;
  • /leads — последние заявки и сводка по статусам;
  • /lead <id> — карточка конкретной заявки с кнопками управления;
  • /stats — сводка за день/неделю/всё время + разбивка по статусам;
  • /users — мониторинг реестра пользователей: сводка, сегменты, список.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Config
from models import STATUS_EMOJI, STATUS_PAID, status_label
from services import sheets, storage, users
from services.leads import emit_lead_card

logger = logging.getLogger(__name__)
router = Router()


def _is_managers_chat(chat_id: int, config: Config) -> bool:
    return chat_id == config.managers_chat_id


# --- /chatinfo — помощник настройки: показывает id чата и топика ----------
@router.message(Command("chatinfo"))
async def cmd_chatinfo(message: Message, config: Config) -> None:
    """Подсказывает, что прописать в .env. Вызовите в нужном топике группы."""
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(
            "Добавьте бота в группу менеджеров и вызовите /chatinfo "
            "в том топике, куда должны падать заявки."
        )
        return
    thread = message.message_thread_id
    topic_value = thread if thread is not None else ""
    topic_human = thread if thread is not None else "— (основной чат / «General»)"
    await message.answer(
        "🧭 <b>Куда слать заявки</b>\n"
        f"chat_id: <code>{message.chat.id}</code>\n"
        f"topic_id: <code>{topic_human}</code>\n\n"
        "Пропишите в <code>.env</code> и перезапустите бота:\n"
        f"<code>MANAGERS_CHAT_ID={message.chat.id}</code>\n"
        f"<code>MANAGERS_TOPIC_ID={topic_value}</code>"
    )


# --- смена статуса по кнопке ---------------------------------------------
@router.callback_query(F.data.startswith("status:"))
async def change_status(call: CallbackQuery, config: Config) -> None:
    if not _is_managers_chat(call.message.chat.id, config):
        await call.answer("Доступно только менеджерам", show_alert=True)
        return

    _, raw_id, status = call.data.split(":", 2)
    application = storage.update_status(int(raw_id), status)
    if application is None:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    sheets.update_status(config, application.id, status)
    await call.answer(f"Статус: {status}")
    await emit_lead_card(
        lambda text, kb: call.message.edit_text(text, reply_markup=kb),
        application,
    )


# --- /leads — список и сводка --------------------------------------------
@router.message(Command("leads"))
async def cmd_leads(message: Message, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        await message.answer("Эта команда доступна только в чате менеджеров.")
        return

    items = storage.recent(limit=15)
    if not items:
        await message.answer("Пока нет ни одной заявки.")
        return

    counts = storage.counts_by_status()
    summary = "  ".join(
        f"{STATUS_EMOJI.get(s, '•')} {n}" for s, n in counts.items()
    )
    lines = [a.to_list_line() for a in items]
    await message.answer(
        f"📋 <b>Последние заявки</b>\n{summary}\n\n"
        + "\n".join(lines)
        + "\n\nКарточка заявки: <code>/lead номер</code>"
    )


# --- /stats — сводка за день/неделю/всё время ----------------------------
@router.message(Command("stats"))
async def cmd_stats(message: Message, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        await message.answer("Эта команда доступна только в чате менеджеров.")
        return

    now = datetime.now()
    today = storage.stats(since=now.replace(hour=0, minute=0, second=0, microsecond=0))
    week = storage.stats(since=now - timedelta(days=7))
    total = storage.stats()

    def fmt(s: dict) -> str:
        return f"<b>{s['count']}</b> · {s['amount']} ₽ · 🎫 {s['tickets']}"

    lines = [
        "📊 <b>Статистика заявок</b>",
        "",
        f"📅 Сегодня: {fmt(today)}",
        f"🗓 7 дней: {fmt(week)}",
        f"∑ Всего: {fmt(total)}",
        "",
        "<b>По статусам (всего):</b>",
    ]
    by_status = total["by_status"]
    for status in STATUS_EMOJI:  # известные статусы — в фиксированном порядке
        lines.append(f"{status_label(status)}: <b>{by_status.get(status, 0)}</b>")
    for status, n in by_status.items():  # на случай нестандартных статусов
        if status not in STATUS_EMOJI:
            lines.append(f"• {status}: <b>{n}</b>")

    if total["count"]:
        paid = by_status.get(STATUS_PAID, 0)
        conv = round(paid * 100 / total["count"])
        lines += ["", f"💳 Конверсия в оплату: <b>{conv}%</b> ({paid}/{total['count']})"]

    await message.answer("\n".join(lines))


# --- /users — мониторинг реестра пользователей ----------------------------
_USERS_PAGE_SIZE = 10


def _fmt_seen(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m %H:%M")
    except ValueError:  # чужеродное значение в БД — покажем как есть
        return iso


def _user_line(row: dict) -> str:
    """Одна строка списка: метка · имя · @username · id · активность · источник."""
    if row["blocked"]:
        mark = "🚫"
    elif row["muted"]:
        mark = "🔕"
    elif row["lead_status"]:
        mark = STATUS_EMOJI.get(row["lead_status"], "•")
    else:
        mark = "🤔"  # писал боту, но заявки нет — как сегмент «Думают»
    name = escape(row["first_name"] or "Без имени")
    uname = f" @{escape(row['username'])}" if row["username"] else ""
    source = f" · 📈 {escape(row['source'])}" if row["source"] else ""
    return (
        f"{mark} <b>{name}</b>{uname} <code>{row['user_id']}</code>"
        f" — {_fmt_seen(row['last_seen'])}{source}"
    )


def _users_page(offset: int, config: Config) -> tuple[str, InlineKeyboardMarkup | None]:
    """Текст и клавиатура страницы /users; вынесено для команды и листания."""
    stats = users.overview()
    total = stats["total"]
    if not total:
        return "👥 <b>Пользователи бота</b>\n\nПока никто не писал боту.", None

    # Не даём улистать за край: реестр мог сжаться между нажатиями.
    offset = max(0, min(offset, (total - 1) // _USERS_PAGE_SIZE * _USERS_PAGE_SIZE))
    rows = users.recent_users(limit=_USERS_PAGE_SIZE, offset=offset)
    segments = users.segment_counts(config.fsm_db_path)

    lines = [
        "👥 <b>Пользователи бота</b>",
        "",
        f"∑ Всего: <b>{total}</b> · 🚫 заблокировали: <b>{stats['blocked']}</b>"
        f" · 🔕 отписались: <b>{stats['muted']}</b>",
        f"🆕 Новые: сегодня <b>{stats['new_today']}</b> · 7 дней <b>{stats['new_week']}</b>",
        f"⚡️ Активные: сегодня <b>{stats['active_today']}</b>"
        f" · 7 дней <b>{stats['active_week']}</b>",
        "",
        "<b>Сегменты рассылок:</b>",
    ]
    lines += [f"{label}: <b>{segments[key]}</b>" for key, label in users.SEGMENTS.items()]
    lines += [
        "",
        f"<b>Последние активные</b> ({offset + 1}–{offset + len(rows)} из {total}):",
    ]
    lines += [_user_line(row) for row in rows]
    lines += [
        "",
        "<i>Метка — статус последней заявки; 🤔 без заявки, "
        "🚫 заблокировал бота, 🔕 отписался от рассылок.</i>",
    ]

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Новее", callback_data=f"users:page:{offset - _USERS_PAGE_SIZE}",
        ))
    nav.append(InlineKeyboardButton(text="🔄 Обновить", callback_data=f"users:page:{offset}"))
    if offset + _USERS_PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(
            text="Раньше ➡️", callback_data=f"users:page:{offset + _USERS_PAGE_SIZE}",
        ))
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=[nav])


@router.message(Command("users"))
async def cmd_users(message: Message, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        await message.answer("Эта команда доступна только в чате менеджеров.")
        return
    text, kb = _users_page(0, config)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("users:page:"))
async def users_page(call: CallbackQuery, config: Config) -> None:
    if not _is_managers_chat(call.message.chat.id, config):
        await call.answer("Доступно только менеджерам", show_alert=True)
        return
    raw_offset = call.data.rsplit(":", 1)[1]
    if not raw_offset.isdigit():
        await call.answer("Некорректная страница", show_alert=True)
        return
    text, kb = _users_page(int(raw_offset), config)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as exc:
        # «Обновить» без изменений в реестре — Telegram отвергает то же сообщение.
        if "message is not modified" not in str(exc):
            raise
    await call.answer("Обновлено")


# --- /lead <id> — карточка с кнопками ------------------------------------
@router.message(Command("lead"))
async def cmd_lead(message: Message, command: CommandObject, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        await message.answer("Эта команда доступна только в чате менеджеров.")
        return

    if not command.args or not command.args.strip().isdigit():
        await message.answer("Укажите номер заявки: <code>/lead 12</code>")
        return

    application = storage.get(int(command.args.strip()))
    if application is None:
        await message.answer("Заявка с таким номером не найдена.")
        return

    await emit_lead_card(
        lambda text, kb: message.answer(text, reply_markup=kb),
        application,
    )
