"""Клавиатуры бота: клиентская заявка и менеджерское управление."""
from __future__ import annotations

from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from models import (
    CONTACT_METHODS,
    FAQ_ITEMS,
    MANAGER_STATUSES,
    PACK_ITEMS,
    TICKET_OPTIONS,
    status_label,
    ticket_price_for,
)
from pricing import (
    CANOPY_TYPES,
    EXTRA_EQUIPMENT,
    ISLAND_ENTRY_PRICE,
    SUP_PRICE_PER_HOUR,
    TENT_TYPES,
)

BTN_NEW_APPLICATION = "📝 Оставить заявку"
BTN_FAQ = "❓ Есть вопрос"
BTN_CALC = "🧮 Калькулятор"
BTN_ABOUT = "ℹ️ О вечеринке"
BTN_CANCEL = "✖️ Отмена"
BTN_WEBAPP = "🎟 Открыть афишу"

# Inline-кнопка отмены под шагами с кнопками (способ связи, билет).
CANCEL_CB = "newlead:cancel"
_cancel_inline_row = [InlineKeyboardButton(text=BTN_CANCEL, callback_data=CANCEL_CB)]


def cancel_kb() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с одной кнопкой «Отмена» для шагов с вводом текста."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
        input_field_placeholder="Введите ответ или нажмите «Отмена»",
    )


def main_kb(webapp_url: str = "") -> ReplyKeyboardMarkup:
    """Главное меню клиента.

    Два основных пути: оставить заявку прямо в чате либо задать вопрос (FAQ).
    Если задан WEBAPP_URL, первым рядом во всю ширину идёт Mini App-афиша —
    главная точка входа (она же висит на кнопке «Меню» у поля ввода).
    """
    rows: list[list[KeyboardButton]] = []
    if webapp_url:
        rows.append([KeyboardButton(text=BTN_WEBAPP, web_app=WebAppInfo(url=webapp_url))])
    rows.append([KeyboardButton(text=BTN_NEW_APPLICATION), KeyboardButton(text=BTN_FAQ)])
    rows.append([KeyboardButton(text=BTN_CALC)])
    rows.append([KeyboardButton(text=BTN_ABOUT)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Оставьте заявку или задайте вопрос",
    )


def faq_menu_kb() -> InlineKeyboardMarkup:
    """Список вопросов + кнопка «оставить заявку», если ответа не нашлось."""
    rows = [
        [InlineKeyboardButton(text=item.question, callback_data=f"faq:q:{item.key}")]
        for item in FAQ_ITEMS
    ]
    rows.append(
        [InlineKeyboardButton(text=BTN_NEW_APPLICATION, callback_data="faq:apply")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def faq_answer_kb(extra: tuple[str, str] | None = None) -> InlineKeyboardMarkup:
    """Под ответом: опц. доп. кнопка (текст, callback), затем к вопросам и заявка."""
    rows: list[list[InlineKeyboardButton]] = []
    if extra:
        rows.append([InlineKeyboardButton(text=extra[0], callback_data=extra[1])])
    rows.append([InlineKeyboardButton(text="⬅️ К другим вопросам", callback_data="faq:menu")])
    rows.append([InlineKeyboardButton(text=BTN_NEW_APPLICATION, callback_data="faq:apply")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def packing_kb(mask: int) -> InlineKeyboardMarkup:
    """Чек-лист сборов: каждый пункт — кнопка-галочка; маска отмеченного в callback.

    Тап шлёт `pack:<новая_маска>:<идекс>` — обработчик просто перерисовывает список.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for i, item in enumerate(PACK_ITEMS):
        box = "✅" if mask & (1 << i) else "⬜"
        rows.append([InlineKeyboardButton(text=f"{box} {item}", callback_data=f"pack:{mask}:{i}")])
    rows.append([InlineKeyboardButton(text="⬅️ К вопросам", callback_data="faq:menu")])
    rows.append([InlineKeyboardButton(text=BTN_NEW_APPLICATION, callback_data="faq:apply")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tour_kb(idx: int, total: int) -> InlineKeyboardMarkup:
    """Навигация по «Туру по Острову» + CTA оставить заявку.

    Стрелки появляются только там, где есть куда идти; на последней карточке
    кнопка заявки становится главным акцентом. Заявка переиспользует callback
    `faq:apply` (обрабатывается в handlers.application → begin_application).
    """
    nav: list[InlineKeyboardButton] = []
    if idx > 0:
        nav.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"tour:{idx - 1}"))
    if idx < total - 1:
        nav.append(InlineKeyboardButton(text="Дальше ▶", callback_data=f"tour:{idx + 1}"))
    rows: list[list[InlineKeyboardButton]] = []
    if nav:
        rows.append(nav)
    cta = "🏝 Хочу на Остров" if idx == total - 1 else BTN_NEW_APPLICATION
    rows.append([InlineKeyboardButton(text=cta, callback_data="faq:apply")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def contact_method_kb() -> InlineKeyboardMarkup:
    """Выбор удобного способа связи (по одному в строке)."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"{m.emoji} {m.label}",
                callback_data=f"contact:{m.key}",
            )
        ]
        for m in CONTACT_METHODS
    ]
    rows.append(_cancel_inline_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_request_kb() -> ReplyKeyboardMarkup:
    """Кнопка, отправляющая контакт клиента в один тап (плюс «Отмена»)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Отправить мой номер", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Или введите номер вручную",
    )


def tickets_kb() -> InlineKeyboardMarkup:
    """Выбор варианта билета (каждый — отдельной строкой) + произвольное число."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"🎟 {o.label} — {o.price} ₽",
                callback_data=f"tickets:{o.key}",
            )
        ]
        for o in TICKET_OPTIONS
    ]
    rows.append([InlineKeyboardButton(text="✏️ Другое количество", callback_data="tickets:custom")])
    rows.append(_cancel_inline_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def custom_tickets_kb(count: int) -> InlineKeyboardMarkup:
    """Степпер выбора произвольного числа человек (сумма считается автоматически)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="−", callback_data="tickets:cdec"),
                InlineKeyboardButton(text=f"{count} чел.", callback_data="tickets:noop"),
                InlineKeyboardButton(text="+", callback_data="tickets:cinc"),
            ],
            [InlineKeyboardButton(text="✅ Выбрать", callback_data="tickets:cdone")],
            [InlineKeyboardButton(text="◀ Назад к вариантам", callback_data="tickets:cback")],
            _cancel_inline_row,
        ]
    )


def children_ask_kb() -> InlineKeyboardMarkup:
    """Вопрос «едут ли дети?» после выбора взрослого билета."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧒 Да, добавить детский билет", callback_data="children:yes")],
            [InlineKeyboardButton(text="Нет, только взрослые", callback_data="children:no")],
            _cancel_inline_row,
        ]
    )


def children_count_kb(count: int) -> InlineKeyboardMarkup:
    """Степпер количества детских билетов (полцены от взрослого одиночного)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="−", callback_data="children:dec"),
                InlineKeyboardButton(text=f"{count} дет.", callback_data="children:noop"),
                InlineKeyboardButton(text="+", callback_data="children:inc"),
            ],
            [InlineKeyboardButton(text="✅ Готово", callback_data="children:done")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="children:back")],
            _cancel_inline_row,
        ]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение/отмена заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="confirm:yes"),
                InlineKeyboardButton(text="✖️ Отменить", callback_data="confirm:no"),
            ]
        ]
    )


def success_kb(invite_link: str | None, invite_text: str) -> InlineKeyboardMarkup:
    """Кнопки под принятой заявкой: «Позвать своих» (нативный шеринг Telegram с
    deep-link бота) и «Собрать рюкзак» (открывает чек-лист сборов).

    invite_link=None (не удалось узнать username бота) — показываем только сборы.
    """
    rows: list[list[InlineKeyboardButton]] = []
    if invite_link:
        share = (
            "https://t.me/share/url?url=" + quote(invite_link, safe="")
            + "&text=" + quote(invite_text, safe="")
        )
        rows.append([InlineKeyboardButton(text="🤝 Позвать своих на Остров", url=share)])
    rows.append([InlineKeyboardButton(text="🎒 Собрать рюкзак", callback_data="pack:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcast_kb(cta: tuple[str, str] | None) -> InlineKeyboardMarkup:
    """Кнопки под рассылкой/напоминанием: CTA (текст, callback) + отписка.

    Кнопка «Больше не присылать» обязательна в каждой рассылке — это и есть
    разница между полезным напоминанием и спамом.
    """
    rows: list[list[InlineKeyboardButton]] = []
    if cta:
        rows.append([InlineKeyboardButton(text=cta[0], callback_data=cta[1])])
    rows.append(
        [InlineKeyboardButton(text="🔕 Больше не присылать", callback_data="bcast:mute")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- калькулятор ----------------------------------------------------------
_calc_cancel_row = [InlineKeyboardButton(text="✖️ Отмена", callback_data="calc:cancel")]


def _cart_btn(label: str, price: int, qty: int, key: str) -> InlineKeyboardButton:
    """Кнопка услуги в чеке: тап добавляет 1 ед.; справа — сколько уже набрано."""
    badge = f"  ✅ ×{qty}" if qty else ""
    return InlineKeyboardButton(text=f"{label} — {price} ₽{badge}", callback_data=f"calc:add:{key}")


def calc_cart_kb(data: dict) -> InlineKeyboardMarkup:
    """Единый экран-чек: каждая услуга — кнопка (тап = +1 в чек), плюс авто-подбор
    палаток, обнуление чека и подсчёт. Цена билета динамическая, прочие — из pricing.
    """
    # Билет на open air идёт по групповому тарифу «на четверых» (нелинейно: 4 чел
    # дешевле 3), поэтому фикс. цена за человека ввела бы в заблуждение. Показываем
    # реальный подытог секции «люди» (билет группой + вход на остров) для текущего
    # числа; тап по «＋» добавляет ещё одного.
    people = int(data.get("people", 1))
    people_subtotal = ticket_price_for(people) + people * ISLAND_ENTRY_PRICE
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(
            text=f"👥 Человек ×{people} — {people_subtotal} ₽   ＋",
            callback_data="calc:add:people",
        )],
    ]
    rows += [[_cart_btn(t.label, t.price, data.get(t.key, 0), t.key)] for t in TENT_TYPES]
    # Кухня-шатёр — не личная палатка, а общий навес на компанию (как на Ostrov2).
    rows += [[_cart_btn(c.label, c.price, data.get(c.key, 0), c.key)] for c in CANOPY_TYPES]
    rows.append([_cart_btn("🏄 Сап-борд, час", SUP_PRICE_PER_HOUR, data.get("sup", 0), "sup")])
    rows += [[_cart_btn(e.label, e.price, data.get(e.key, 0), e.key)] for e in EXTRA_EQUIPMENT]
    rows.append([
        InlineKeyboardButton(text="✨ Палатки под компанию", callback_data="calc:suggest"),
        InlineKeyboardButton(text="🎪 Шатёр под компанию", callback_data="calc:canopy"),
    ])
    rows.append([
        InlineKeyboardButton(text="🧹 Обнулить чек", callback_data="calc:reset"),
        InlineKeyboardButton(text="✅ Посчитать", callback_data="calc:done"),
    ])
    rows.append(_calc_cancel_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def calc_result_kb() -> InlineKeyboardMarkup:
    """Под итогом: оставить заявку, вернуться к настройке или в меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_NEW_APPLICATION, callback_data="calc:apply")],
            [InlineKeyboardButton(text="🔄 Пересчитать", callback_data="calc:edit")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="calc:menu")],
        ]
    )


def manager_lead_kb(
    lead_id: int, user_id: int | None = None, include_contact: bool = True
) -> InlineKeyboardMarkup:
    """Кнопки управления заявкой в чате менеджеров.

    Верхний ряд — смена статуса, ниже — быстрый переход в чат с клиентом
    (работает, если клиент писал боту: tg://user?id=...).

    include_contact=False убирает кнопку «Написать клиенту»: нужно как
    запасной вариант, когда приватность клиента отклоняет deeplink
    (BUTTON_USER_PRIVACY_RESTRICTED) — иначе Telegram отвергает всё сообщение.
    """
    status_buttons = [
        InlineKeyboardButton(text=status_label(s), callback_data=f"status:{lead_id}:{s}")
        for s in MANAGER_STATUSES
    ]
    # По две кнопки в ряд, чтобы не растягивать сообщение.
    rows = [status_buttons[i:i + 2] for i in range(0, len(status_buttons), 2)]
    if user_id and include_contact:
        rows.append(
            [InlineKeyboardButton(text="✉️ Написать клиенту", url=f"tg://user?id={user_id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
