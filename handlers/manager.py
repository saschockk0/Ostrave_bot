"""Работа менеджеров с заявками внутри Telegram.

Доступно только в чате менеджеров (config.managers_chat_id):
  • inline-кнопки статуса под каждой заявкой;
  • /leads — последние заявки и сводка по статусам;
  • /lead <id> — карточка конкретной заявки с кнопками управления;
  • /stats — сводка за день/неделю/всё время + разбивка по статусам.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from config import Config
from models import STATUS_EMOJI, STATUS_PAID, status_label
from services import sheets, storage
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
