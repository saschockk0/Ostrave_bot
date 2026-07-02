"""Рассылки менеджеров по сегментам пользователей.

Доступно только в чате менеджеров:
  • /broadcast — выбрать сегмент (с живыми счётчиками), прислать текст,
    посмотреть превью глазами получателя и подтвердить отправку.

Отправка идёт фоном с паузой между сообщениями (лимиты Telegram), юзеры,
заблокировавшие бота, помечаются в реестре и выпадают из будущих рассылок.
Под каждым сообщением — CTA «Оставить заявку» с меткой источника (видно в
карточке заявки, какая рассылка её принесла) и кнопка «Больше не присылать».
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Config
from handlers.application import begin_application
from keyboards import BTN_NEW_APPLICATION, broadcast_kb
from services import attribution, users

logger = logging.getLogger(__name__)
router = Router()

_SEND_PAUSE = 0.05  # ~20 сообщений/сек — с запасом до лимита Telegram (30/сек)


class BroadcastForm(StatesGroup):
    text = State()  # ждём от менеджера текст рассылки


def _is_managers_chat(chat_id: int, config: Config) -> bool:
    return chat_id == config.managers_chat_id


def _user_kb(segment: str) -> InlineKeyboardMarkup:
    """Кнопки, которые увидит получатель рассылки — CTA зависит от сегмента."""
    if segment == "paid":
        # Оплатившим заявку не предлагаем — им пора собирать рюкзак.
        return broadcast_kb(("🎒 Собрать рюкзак", "pack:open"))
    # Метка источника: в карточке заявки будет видно, какая рассылка её принесла.
    tag = f"bc_{segment}_{datetime.now():%d%m}"
    return broadcast_kb((BTN_NEW_APPLICATION, f"bcast:apply:{tag}"))


# --- /broadcast: выбор сегмента --------------------------------------------
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        await message.answer("Эта команда доступна только в чате менеджеров.")
        return
    await state.clear()
    counts = users.segment_counts(config.fsm_db_path)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{label} — {counts[key]}",
                callback_data=f"bcast:seg:{key}",
            )]
            for key, label in users.SEGMENTS.items()
        ]
    )
    await message.answer(
        "📣 <b>Рассылка</b>\n\nКому отправляем? Юзеры, заблокировавшие бота или "
        "нажавшие «Больше не присылать», уже исключены из счётчиков.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("bcast:seg:"))
async def choose_segment(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_managers_chat(call.message.chat.id, config):
        await call.answer("Доступно только менеджерам", show_alert=True)
        return
    segment = call.data.split(":", 2)[2]
    if segment not in users.SEGMENTS:
        await call.answer("Неизвестный сегмент", show_alert=True)
        return
    await call.answer()
    await state.set_state(BroadcastForm.text)
    await state.update_data(segment=segment)
    await call.message.edit_text(
        f"Сегмент: <b>{users.SEGMENTS[segment]}</b>\n\n"
        "Пришлите текст рассылки одним сообщением — форматирование (жирный, "
        "курсив, ссылки) сохранится. Кнопки «Оставить заявку» и «Больше не "
        "присылать» добавятся автоматически.\n\nОтмена: /cancel"
    )


# --- текст рассылки → превью ------------------------------------------------
@router.message(StateFilter(BroadcastForm), Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        return
    await state.clear()
    await message.answer("Рассылка отменена.")


@router.message(BroadcastForm.text, F.text)
async def got_text(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_managers_chat(message.chat.id, config):
        return
    if message.text.startswith("/"):
        await message.answer("Жду текст рассылки. Отменить: /cancel")
        return
    data = await state.get_data()
    segment = data["segment"]
    await state.update_data(text=message.html_text)
    recipients = users.segment_user_ids(segment, config.fsm_db_path)
    await message.answer("👀 Так это увидит получатель:")
    await message.answer(message.html_text, reply_markup=_user_kb(segment))
    await message.answer(
        f"Сегмент: <b>{users.SEGMENTS[segment]}</b>\n"
        f"Получателей: <b>{len(recipients)}</b>\n\nОтправляем?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🚀 Отправить", callback_data="bcast:go"),
                InlineKeyboardButton(text="✖️ Отмена", callback_data="bcast:cancel"),
            ]]
        ),
    )


@router.callback_query(F.data == "bcast:cancel")
async def confirm_cancel(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_managers_chat(call.message.chat.id, config):
        await call.answer("Доступно только менеджерам", show_alert=True)
        return
    await state.clear()
    await call.answer("Отменено")
    await call.message.edit_text("Рассылка отменена.")


@router.callback_query(F.data == "bcast:go")
async def confirm_send(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not _is_managers_chat(call.message.chat.id, config):
        await call.answer("Доступно только менеджерам", show_alert=True)
        return
    data = await state.get_data()
    segment, text = data.get("segment"), data.get("text")
    if not segment or not text:
        # Кнопка от старой, уже сброшенной рассылки.
        await call.answer("Эта рассылка уже неактуальна — начните заново: /broadcast",
                          show_alert=True)
        return
    recipients = users.segment_user_ids(segment, config.fsm_db_path)
    if not recipients:
        await call.answer("Сегмент пуст — отправлять некому", show_alert=True)
        return
    await state.clear()
    await call.answer("Поехали!")
    await call.message.edit_text(
        f"🚀 Рассылка запущена: {users.SEGMENTS[segment]}, "
        f"{len(recipients)} получателей. Отчёт придёт сюда."
    )
    asyncio.create_task(
        _run_broadcast(call.bot, config, recipients, text, _user_kb(segment), segment)
    )


async def _run_broadcast(bot: Bot, config: Config, user_ids: list[int],
                         text: str, kb: InlineKeyboardMarkup, segment: str) -> None:
    """Фоновая отправка с паузами и учётом заблокировавших; в конце — отчёт."""
    sent = blocked = failed = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, reply_markup=kb)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 1)
            try:
                await bot.send_message(user_id, text, reply_markup=kb)
                sent += 1
            except Exception:  # noqa: BLE001 — не роняем рассылку из-за одного юзера
                failed += 1
        except TelegramForbiddenError:
            users.mark_blocked(user_id)
            blocked += 1
        except Exception:  # noqa: BLE001
            failed += 1
            logger.exception("Рассылка: не удалось отправить user_id=%s", user_id)
        await asyncio.sleep(_SEND_PAUSE)

    report = (
        f"📣 <b>Рассылка завершена</b> — {users.SEGMENTS.get(segment, segment)}\n"
        f"✅ Доставлено: <b>{sent}</b>\n"
        f"🚫 Заблокировали бота: <b>{blocked}</b>\n"
        f"⚠️ Ошибок: <b>{failed}</b>"
    )
    try:
        await bot.send_message(
            config.managers_chat_id, report,
            message_thread_id=config.managers_topic_id or None,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось отправить отчёт о рассылке")


# --- кнопки под рассылкой (жмут клиенты в личке) -----------------------------
@router.callback_query(F.data.startswith("bcast:apply:"))
async def apply_from_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    """CTA «Оставить заявку» из рассылки: метим источник и запускаем диалог."""
    tag = call.data.split(":", 2)[2]
    if call.from_user:
        attribution.remember(call.from_user.id, tag)
        users.set_source(call.from_user.id, tag)
    await call.answer()
    await begin_application(call.message, state, call.from_user)


@router.callback_query(F.data == "bcast:mute")
async def mute(call: CallbackQuery) -> None:
    if call.from_user:
        users.set_muted(call.from_user.id, True)
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 — сообщение могло быть уже изменено
        pass
    await call.answer("Хорошо, больше не побеспокоим 🙏", show_alert=True)
