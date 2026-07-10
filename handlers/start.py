"""Хендлер /start — приветствие и главное меню.

Кнопка «О вечеринке» ведёт в «Тур по Острову» — см. handlers/tour.py.
"""
from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import countdown
from config import Config
from keyboards import main_kb, success_kb
from models import (
    INVITE_TEXT,
    STATUS_IN_PROGRESS,
    STATUS_NEW,
    STATUS_PAID,
    STATUS_REJECTED,
    status_label,
)
from services import attribution, storage, users

router = Router()

# Следующий шаг к Острову — под статус заявки вернувшегося гостя.
_NEXT_STEP_BY_STATUS = {
    STATUS_NEW: "Менеджер скоро свяжется. А пока собери рюкзак и зови своих 👇",
    STATUS_IN_PROGRESS: "Менеджер уже занимается заявкой. Готовься: собери рюкзак и зови своих 👇",
    STATUS_PAID: "Место забронировано — ты в деле! 🎉 Осталось собрать рюкзак и позвать своих 👇",
}
_DEFAULT_NEXT_STEP = "Собери рюкзак и зови своих на берег 👇"

WELCOME = (
    "🏝 <b>Привет! Я Островной техно-бот</b> 🎧\n\n"
    "Помогу забронировать тебе место на open air «Остров» и подскажу по любым "
    "вопросам — пиши в любой момент, я всегда на связи 🤙\n"
    "🗓 <b>31 июля – 2 августа</b> — три дня музыки и закатов над водой 🌅\n\n"
    "<b>Чем могу помочь:</b>\n"
    "📝 <b>«Оставить заявку»</b> — бронь за минуту, менеджер сам тебе напишет.\n"
    "🧮 <b>«Калькулятор»</b> — прикинем стоимость поездки до рубля.\n"
    "❓ <b>«Есть вопрос»</b> — быстрые ответы на частые вопросы.\n"
    "ℹ️ <b>«О вечеринке»</b> — мини-тур по Острову и план на все три дня.\n\n"
    "<blockquote>⚠️ <b>Важно!</b> Цена из двух частей: билет на <b>open air</b> "
    "(оплата заранее) и <b>вход на остров — 4700 ₽</b> при выезде (трансфер, "
    "катамараны, баня). Проживание и аренда снаряжения — отдельно.\n"
    "💸 Подробно — в «❓ Есть вопрос» → «Сколько стоит?», а 🧮 «Калькулятор» "
    "посчитает всё под твою компанию.</blockquote>\n\n"
    "До встречи на берегу 🎶"
)

async def _returning_banner(message: Message) -> None:
    """Если гость уже оставлял заявку — баннер «что дальше» перед/после меню.

    Тянем к Острову и после брони: статус, отсчёт и быстрые шаги (собрать рюкзак,
    позвать своих). Для отклонённых заявок баннер не показываем.
    """
    user = message.from_user
    if not user:
        return
    app = storage.latest_by_user(user.id)
    if app is None or app.status == STATUS_REJECTED:
        return
    next_step = _NEXT_STEP_BY_STATUS.get(app.status, _DEFAULT_NEXT_STEP)
    text = (
        f"📋 Твоя заявка <b>#{app.id}</b> — {status_label(app.status)}.\n"
        f"{next_step}"
    )
    link = None
    try:
        me = await message.bot.me()
        if me.username:
            link = f"https://t.me/{me.username}?start=ref{user.id}"
    except Exception:  # noqa: BLE001 — без ссылки покажем только сборы
        link = None
    await message.answer(text, reply_markup=success_kb(link, INVITE_TEXT))


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext,
                    config: Config) -> None:
    # /start всегда даёт чистый лист — сбрасываем недозаполненный диалог, если был.
    await state.clear()
    # Источник перехода из deep-link: https://t.me/<bot>?start=<payload>.
    # Привяжется к заявке при отправке (services.leads.submit_application).
    # В реестре пользователей источник сохраняется персистентно (first-touch).
    if command.args and message.from_user:
        attribution.remember(message.from_user.id, command.args)
        users.set_source(message.from_user.id, command.args)
    # Живой крючок: отсчёт до старта (если ещё впереди) — затем меню.
    cd = countdown.line()
    text = f"{cd}\n\n{WELCOME}" if cd else WELCOME
    await message.answer(text, reply_markup=main_kb(config.webapp_url))
    # Уже бронировал? Покажем «что дальше» отдельным баннером.
    await _returning_banner(message)
