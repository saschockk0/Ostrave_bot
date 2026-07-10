"""Диалог «оставить заявку» прямо в чате — без Mini App.

Сценарий (FSM): имя → способ связи (Telegram/телефон/WhatsApp) →
контакт → вариант билета → подтверждение → отправка через services.leads.
"""
from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, User

import countdown
import journey
from config import Config
from keyboards import (
    BTN_CANCEL,
    BTN_NEW_APPLICATION,
    CANCEL_CB,
    cancel_kb,
    children_ask_kb,
    children_count_kb,
    confirm_kb,
    contact_method_kb,
    custom_tickets_kb,
    main_kb,
    phone_request_kb,
    success_kb,
    tickets_kb,
)
from models import (
    CHILD_TICKET_PRICE,
    CONTACT_METHODS_BY_KEY,
    INVITE_TEXT,
    MAX_TICKETS,
    TICKET_OPTIONS_BY_KEY,
    Application,
    ticket_price_for,
)
from pricing import CHILD_ISLAND_ENTRY_PRICE, ISLAND_ENTRY_PRICE
from services import leads

router = Router()
logger = logging.getLogger(__name__)

# Один и тот же экран выбора билета показывается из двух мест (первый вход и
# возврат от степпера) — держим текст в одном месте, чтобы «нить пути» совпадала.
_TICKETS_PROMPT = "🎟 <b>Почти на месте!</b>\n\nКакой билет берём?"


class NewLead(StatesGroup):
    name = State()
    method = State()   # выбор способа связи
    contact = State()  # ввод значения контакта
    tickets = State()
    children = State()  # вопрос про детские билеты (полцены)
    confirm = State()


# --- запуск диалога -------------------------------------------------------
async def begin_application(message: Message, state: FSMContext,
                            from_user: User | None, *,
                            tickets: int | None = None, amount: int | None = None,
                            extras_note: str | None = None) -> None:
    """Начинает FSM-диалог заявки. Вызывается из меню, из FAQ и из калькулятора.

    `message` — чат, куда писать; `from_user` — клиент (в callback это не
    `message.from_user`, поэтому имя передаём явно).

    Если заявка пришла из калькулятора, билет/сумма/состав уже известны —
    передаём их сюда, чтобы пропустить шаг выбора билета.
    """
    await state.clear()
    if tickets is not None:
        await state.update_data(tickets=tickets, amount=amount, extras_note=extras_note)
    await state.set_state(NewLead.name)
    # Подставляем имя из профиля как подсказку — клиент может прислать своё.
    suggested = from_user.first_name if from_user else ""
    hint = f"\n\nНапример: <b>{escape(suggested)}</b>" if suggested else ""
    await message.answer(
        journey.with_step(
            journey.STAGE_PACK,
            "Давайте знакомиться! 😊\n"
            "Как вас зовут? Напишите имя, на которое оформить заявку." + hint,
        ),
        reply_markup=cancel_kb(),
    )


@router.message(F.text == BTN_NEW_APPLICATION)
@router.message(F.text == "/apply")
async def start_application(message: Message, state: FSMContext) -> None:
    await begin_application(message, state, message.from_user)


@router.callback_query(F.data == "faq:apply")
async def start_application_from_faq(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin_application(call.message, state, call.from_user)


# --- отмена на любом шаге -------------------------------------------------
# Регистрируем ДО шаговых обработчиков, чтобы «Отмена» перехватывалась раньше,
# чем got_name / got_contact_text и т.п.
async def _cancel_to_menu(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    await message.answer(
        "Оформление отменено. Возвращайтесь, когда будете готовы 🙂",
        reply_markup=main_kb(config.webapp_url),
    )


@router.message(StateFilter(NewLead), F.text == BTN_CANCEL)
@router.message(StateFilter(NewLead), Command("cancel"))
async def cancel_text(message: Message, state: FSMContext, config: Config) -> None:
    await _cancel_to_menu(message, state, config)


@router.callback_query(StateFilter(NewLead), F.data == CANCEL_CB)
async def cancel_inline(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    await call.answer("Отменено")
    await state.clear()
    # Снимаем inline-кнопки у текущего сообщения, чтобы их нельзя было нажать снова.
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 — сообщение могло быть уже изменено
        pass
    await call.message.answer(
        "Оформление отменено. Возвращайтесь, когда будете готовы 🙂",
        reply_markup=main_kb(config.webapp_url),
    )


# --- шаг 1: имя -----------------------------------------------------------
@router.message(NewLead.name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Хм, слишком коротко 🙂 Напишите имя, пожалуйста, ещё раз.")
        return
    await state.update_data(name=name)
    await state.set_state(NewLead.method)
    await message.answer(
        journey.with_step(
            journey.STAGE_ROAD,
            f"Приятно, <b>{escape(name)}</b>! 🙌\n"
            "Как вам удобнее, чтобы мы с вами связались?",
        ),
        reply_markup=contact_method_kb(),
    )


# --- шаг 2: способ связи --------------------------------------------------
@router.callback_query(NewLead.method, F.data.startswith("contact:"))
async def choose_method(call: CallbackQuery, state: FSMContext) -> None:
    method = CONTACT_METHODS_BY_KEY.get(call.data.split(":", 1)[1])
    if method is None:
        await call.answer("Этот способ недоступен", show_alert=True)
        return
    await call.answer()

    user = call.from_user
    # Telegram с готовым @username — не спрашиваем контакт, берём из профиля.
    if method.key == "telegram" and user and user.username:
        await state.update_data(contact_method=method.label, contact=f"@{user.username}")
        await call.message.edit_text(f"Свяжемся с вами в Telegram: @{user.username}")
        await _after_contact(call.message, state)
        return

    await state.update_data(method_key=method.key, contact_method=method.label)
    await state.set_state(NewLead.contact)
    if method.request_phone:
        await call.message.edit_text(f"{method.emoji} {method.label}")
        await call.message.answer(
            journey.with_step(journey.STAGE_ROAD, method.prompt),
            reply_markup=phone_request_kb(),
        )
    else:
        await call.message.edit_text(journey.with_step(journey.STAGE_ROAD, method.prompt))


# --- шаг 3: значение контакта ---------------------------------------------
@router.message(NewLead.contact, F.contact)
async def got_shared_contact(message: Message, state: FSMContext) -> None:
    await _save_contact(message, state, message.contact.phone_number)


@router.message(NewLead.contact, F.text)
async def got_contact_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = data.get("method_key")
    value = message.text.strip()

    if key in ("phone", "whatsapp"):
        digits = value.lstrip("+").replace(" ", "").replace("-", "")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            await message.answer(
                "Хм, не похоже на номер 🤔 Введите в формате <b>+7XXXXXXXXXX</b>."
            )
            return
    elif key == "telegram":
        # Принимаем @user, user или ссылку t.me/user — нормализуем к @user.
        handle = value.lstrip("@").strip()
        if handle.startswith("http"):
            handle = handle.rstrip("/").split("/")[-1]
        if not handle or " " in handle:
            await message.answer("Введите ник в формате <b>@username</b> 💬")
            return
        value = f"@{handle}"

    await _save_contact(message, state, value)


async def _save_contact(message: Message, state: FSMContext, value: str) -> None:
    await state.update_data(contact=value)
    await _after_contact(message, state)


async def _after_contact(message: Message, state: FSMContext) -> None:
    """После контакта: из калькулятора билет уже известен — сразу подтверждение,
    иначе спрашиваем вариант билета как обычно."""
    data = await state.get_data()
    if data.get("tickets") is not None and data.get("amount") is not None:
        # Из калькулятора состав уже собран — вопрос про детей не задаём.
        await _to_confirm(message, state, children=0, edit=False)
    else:
        await _ask_tickets(message, state)


async def _ask_tickets(message: Message, state: FSMContext) -> None:
    await state.set_state(NewLead.tickets)
    # Хотим один пузырь: вопрос и варианты вместе. Но Telegram допускает только
    # один reply_markup на сообщение, поэтому reply-клавиатуру прошлого шага
    # (Отмена/телефон) снимаем отдельным служебным сообщением и сразу удаляем —
    # снятие сохраняется даже после удаления.
    nudge = await message.answer("⁣", reply_markup=ReplyKeyboardRemove())
    try:
        await nudge.delete()
    except Exception:  # noqa: BLE001 — служебное сообщение могло не удалиться
        pass
    await message.answer(
        journey.with_step(journey.STAGE_VOLGA, _TICKETS_PROMPT),
        reply_markup=tickets_kb(),
    )


# --- шаг 4а: произвольное количество с авто-суммой ------------------------
# Регистрируем ДО got_tickets_button (broad `tickets:`), чтобы спец-кнопки
# степпера не попадали в общий обработчик вариантов.
def _custom_tickets_text(count: int) -> str:
    price = ticket_price_for(count)
    island = count * ISLAND_ENTRY_PRICE
    return (
        "✏️ <b>Сколько человек?</b>\n\n"
        f"👥 <b>{count}</b> — билет <b>{price} ₽</b> (оплата заранее)\n"
        f"🏝 Вход на остров при выезде: <b>~{island} ₽</b>\n"
        "<i>Каждые 4 билета — по цене «на четверых», пара — «на двоих», так выгоднее.</i>"
    )


@router.callback_query(NewLead.tickets, F.data == "tickets:custom")
async def tickets_custom_open(call: CallbackQuery, state: FSMContext) -> None:
    count = int((await state.get_data()).get("custom_count", 2))
    await state.update_data(custom_count=count)
    await call.answer()
    await call.message.edit_text(_custom_tickets_text(count), reply_markup=custom_tickets_kb(count))


@router.callback_query(NewLead.tickets, F.data == "tickets:cback")
async def tickets_custom_back(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await call.message.edit_text(
        journey.with_step(journey.STAGE_VOLGA, _TICKETS_PROMPT),
        reply_markup=tickets_kb(),
    )


@router.callback_query(NewLead.tickets, F.data == "tickets:noop")
async def tickets_noop(call: CallbackQuery) -> None:
    await call.answer()


@router.callback_query(NewLead.tickets, F.data.in_({"tickets:cinc", "tickets:cdec"}))
async def tickets_custom_step(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    current = int(data.get("custom_count", 2))
    count = max(1, min(current + (1 if call.data.endswith("cinc") else -1), MAX_TICKETS))
    await call.answer()
    if count == current:
        return  # уже на границе
    await state.update_data(custom_count=count)
    try:
        await call.message.edit_text(_custom_tickets_text(count), reply_markup=custom_tickets_kb(count))
    except Exception:  # noqa: BLE001 — текст мог не измениться
        pass


@router.callback_query(NewLead.tickets, F.data == "tickets:cdone")
async def tickets_custom_done(call: CallbackQuery, state: FSMContext) -> None:
    count = int((await state.get_data()).get("custom_count", 2))
    await call.answer()
    await _ask_children(call.message, state, count, ticket_price_for(count))


# --- шаг 4: вариант билета ------------------------------------------------
@router.callback_query(NewLead.tickets, F.data.startswith("tickets:"))
async def got_tickets_button(call: CallbackQuery, state: FSMContext) -> None:
    option = TICKET_OPTIONS_BY_KEY.get(call.data.split(":", 1)[1])
    if option is None:
        await call.answer("Этот вариант недоступен", show_alert=True)
        return
    await call.answer()
    await _ask_children(call.message, state, option.tickets, option.price)


@router.message(NewLead.tickets, F.text)
async def got_tickets_text(message: Message, state: FSMContext) -> None:
    # На этом шаге ждём именно нажатие кнопки — иначе непонятна цена.
    await message.answer(
        "Пожалуйста, выберите билет кнопкой выше 👆",
        reply_markup=tickets_kb(),
    )


# --- шаг 4б: детские билеты (полцены от взрослого одиночного) ---------------
_CHILDREN_PROMPT = (
    "🧒 <b>Едут ли с вами дети?</b>\n\n"
    f"Детский билет — <b>{CHILD_TICKET_PRICE} ₽</b>, вход на остров для ребёнка — "
    f"<b>{CHILD_ISLAND_ENTRY_PRICE} ₽</b> (при выезде).\n"
    "<i>Всё в 2 раза дешевле взрослого.</i>"
)


def _children_text(count: int) -> str:
    return (
        "🧒 <b>Сколько детей?</b>\n\n"
        f"👶 <b>{count}</b> — детские билеты <b>{count * CHILD_TICKET_PRICE} ₽</b> "
        f"(по {CHILD_TICKET_PRICE} ₽, оплата заранее)\n"
        f"🏝 Вход на остров при выезде: <b>~{count * CHILD_ISLAND_ENTRY_PRICE} ₽</b> "
        f"(по {CHILD_ISLAND_ENTRY_PRICE} ₽)"
    )


async def _ask_children(message: Message, state: FSMContext, tickets: int, amount: int) -> None:
    """После выбора взрослого билета спрашиваем про детей, затем подтверждение."""
    await state.update_data(tickets=tickets, amount=amount)
    await state.set_state(NewLead.children)
    await message.edit_text(
        journey.with_step(journey.STAGE_VOLGA, _CHILDREN_PROMPT),
        reply_markup=children_ask_kb(),
    )


@router.callback_query(NewLead.children, F.data == "children:no")
async def children_none(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await _to_confirm(call.message, state, children=0, edit=True)


@router.callback_query(NewLead.children, F.data == "children:yes")
async def children_open(call: CallbackQuery, state: FSMContext) -> None:
    count = int((await state.get_data()).get("children_count", 1))
    await state.update_data(children_count=count)
    await call.answer()
    await call.message.edit_text(_children_text(count), reply_markup=children_count_kb(count))


@router.callback_query(NewLead.children, F.data == "children:back")
async def children_back(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await call.message.edit_text(
        journey.with_step(journey.STAGE_VOLGA, _CHILDREN_PROMPT),
        reply_markup=children_ask_kb(),
    )


@router.callback_query(NewLead.children, F.data == "children:noop")
async def children_noop(call: CallbackQuery) -> None:
    await call.answer()


@router.callback_query(NewLead.children, F.data.in_({"children:inc", "children:dec"}))
async def children_step(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    current = int(data.get("children_count", 1))
    count = max(1, min(current + (1 if call.data.endswith("inc") else -1), MAX_TICKETS))
    await call.answer()
    if count == current:
        return  # уже на границе
    await state.update_data(children_count=count)
    try:
        await call.message.edit_text(_children_text(count), reply_markup=children_count_kb(count))
    except Exception:  # noqa: BLE001 — текст мог не измениться
        pass


@router.callback_query(NewLead.children, F.data == "children:done")
async def children_done(call: CallbackQuery, state: FSMContext) -> None:
    count = int((await state.get_data()).get("children_count", 1))
    await call.answer()
    await _to_confirm(call.message, state, children=count, edit=True)


@router.message(NewLead.children, F.text)
async def children_text_fallback(message: Message) -> None:
    # На этом шаге ждём именно нажатие кнопки.
    await message.answer(
        "Пожалуйста, ответьте кнопкой выше 👆",
        reply_markup=children_ask_kb(),
    )


async def _to_confirm(message: Message, state: FSMContext, *, children: int,
                      edit: bool) -> None:
    data = await state.get_data()
    tickets = data["tickets"]
    # Детские билеты добавляются поверх взрослой суммы (полцены за каждого).
    amount = data["amount"] + children * CHILD_TICKET_PRICE
    await state.update_data(amount=amount, children=children)
    await state.set_state(NewLead.confirm)
    preview = journey.with_step(
        journey.STAGE_FOREST,
        Application(
            name=data["name"],
            contact_method=data["contact_method"],
            contact=data["contact"],
            username="",
            tickets=tickets,
            children=children,
            amount=amount,
            extras_note=data.get("extras_note"),
        ).to_user_summary(),
    )
    if edit:
        await message.edit_text(preview, reply_markup=confirm_kb())
    else:
        await message.answer(preview, reply_markup=confirm_kb())


# --- шаг 5: подтверждение -------------------------------------------------
@router.callback_query(NewLead.confirm, F.data == "confirm:no")
async def cancel(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    await call.answer("Заявка отменена")
    await call.message.edit_text("Заявка отменена. Возвращайтесь в любой момент — будем рады! 🙂")
    await call.message.answer("Главное меню 👇", reply_markup=main_kb(config.webapp_url))


@router.callback_query(NewLead.confirm, F.data == "confirm:yes")
async def confirm(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    data = await state.get_data()
    user = call.from_user
    username = f"@{user.username}" if user and user.username else "не задан"
    application = Application(
        name=data["name"],
        contact_method=data["contact_method"],
        contact=data["contact"],
        username=username,
        tickets=data["tickets"],
        children=data.get("children", 0),
        amount=data.get("amount"),
        user_id=user.id if user else None,
        extras_note=data.get("extras_note"),
    )

    await call.answer("Отправляю…")
    # Сохранение пишет в SQLite (источник правды). Если оно упало — заявка НЕ
    # сохранена (уведомление менеджеру и таблица изолированы и не бросают), значит
    # повтор безопасен и дубликата не создаст. Состояние НЕ чистим, чтобы клиент
    # мог повторить отправку, не вводя всё заново.
    try:
        application = await leads.submit_application(call.bot, config, application)
    except Exception:  # noqa: BLE001 — сбой БД/сети не должен терять заявку клиента
        logger.exception(
            "Не удалось сохранить заявку от user_id=%s", user.id if user else None
        )
        try:
            await call.message.edit_text(
                "😔 Не получилось отправить заявку — кажется, временный сбой.\n"
                "Попробуйте ещё раз через минуту 🙏",
                reply_markup=confirm_kb(),
            )
        except Exception:  # noqa: BLE001 — текст мог не измениться при повторном сбое
            await call.answer("Не получилось, попробуйте ещё раз чуть позже", show_alert=True)
        return

    await state.clear()
    body = (
        f"🎉 <b>Готово!</b> Заявка <b>#{application.id}</b> принята.\n\n"
        "Менеджер совсем скоро свяжется с вами. До встречи на Острове! 🌅"
    )
    cd = countdown.line()
    if cd:
        body += f"\n\n{cd}"
    # «Позови своих»: deep-link с реферальным payload (друг придёт как ref<id>,
    # менеджер увидит источник). Username бота берём из кэша aiogram (bot.me()).
    link = None
    try:
        me = await call.bot.me()
        if user and me.username:
            link = f"https://t.me/{me.username}?start=ref{user.id}"
    except Exception:  # noqa: BLE001 — без приглашения заявка всё равно принята
        link = None
    body += (
        "\n\nЗови своих — на берегу веселее, а пока собери рюкзак 👇" if link
        else "\n\nА пока — собери рюкзак в дорогу 👇"
    )
    await call.message.edit_text(
        journey.with_step(journey.STAGE_ISLAND, body),
        reply_markup=success_kb(link, INVITE_TEXT),
    )
    await call.message.answer("Главное меню 👇", reply_markup=main_kb(config.webapp_url))
