"""Модель заявки на вечеринку и её статусы."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape

# Вход на остров (оплата при выезде): взрослый и детский (половина взрослого).
from pricing import CHILD_ISLAND_ENTRY_PRICE, ISLAND_ENTRY_PRICE

# Колонка ID нужна, чтобы синхронизировать статус заявки между чатом и таблицей.
# «Источник» и «Детских билетов» добавлены в конец, чтобы не сдвигать колонку
# «Статус» в уже существующих таблицах (по ней ищется строка при смене статуса).
SHEET_HEADERS = [
    "ID", "Дата", "Имя", "Способ связи", "Контакт", "Username",
    "Кол-во билетов", "Сумма", "Статус", "Источник", "Детских билетов",
]
MAX_TICKETS = 50

# Текст, который улетает друзьям через шеринг (кнопка «Позвать своих»).
INVITE_TEXT = (
    "Я еду на «Остров» 🏝 31 июля – 2 августа — три дня музыки, закатов и сосен "
    "на берегу Волги. Залетай со мной!"
)


@dataclass(frozen=True)
class TicketOption:
    key: str          # хранится в callback_data
    label: str        # человекочитаемое название
    tickets: int      # сколько человек проходит по билету
    price: int        # стоимость в рублях


# Варианты билетов, которые видит клиент. Чтобы добавить новый — допишите сюда.
TICKET_OPTIONS = [
    TicketOption("single", "Одиночный", 1, 2100),
    TicketOption("duo", "На двоих", 2, 3600),
    TicketOption("quad", "На четверых", 4, 6000),
]
TICKET_OPTIONS_BY_KEY = {o.key: o for o in TICKET_OPTIONS}

# Детский билет — половина взрослого одиночного. Считаем от TICKET_OPTIONS,
# чтобы при изменении цен не разъезжалось.
CHILD_TICKET_PRICE = TICKET_OPTIONS_BY_KEY["single"].price // 2


def ticket_price_for(count: int) -> int:
    """Авто-расчёт суммы за `count` человек.

    Жадно от крупного к мелкому: каждые 4 человека — по цене «на четверых»,
    оставшуюся пару — «на двоих», остаток — одиночным. Жадный подбор оптимален,
    т.к. цена за человека убывает с размером тарифа (1500 < 1800 < 2100).
    Цены берём из TICKET_OPTIONS, чтобы не дублировать их.
    Пример: 7 → 6000 + 3600 + 2100 = 11700 ₽.
    """
    count = max(1, min(int(count), MAX_TICKETS))
    quad = TICKET_OPTIONS_BY_KEY["quad"]
    duo = TICKET_OPTIONS_BY_KEY["duo"]
    single = TICKET_OPTIONS_BY_KEY["single"]
    quads, rest = divmod(count, quad.tickets)
    duos, singles = divmod(rest, duo.tickets)
    return quads * quad.price + duos * duo.price + singles * single.price


@dataclass(frozen=True)
class ContactMethod:
    key: str          # хранится в callback_data
    label: str        # человекочитаемое название (пишется в заявку)
    emoji: str
    prompt: str       # что спросить у клиента после выбора способа
    request_phone: bool = False  # показать ли кнопку «отправить номер»


# Способы связи на выбор клиента. Telegram отдельно обрабатывается в хендлере:
# если у клиента есть @username, его подставляем автоматически без вопроса.
CONTACT_METHODS = [
    ContactMethod(
        "telegram", "Telegram", "💬",
        prompt="Напишите ваш ник в Telegram — например, <b>@username</b> 💬",
    ),
    ContactMethod(
        "phone", "Телефон", "📞",
        prompt="Оставьте номер телефона 📞\nМожно одной кнопкой ниже или ввести вручную.",
        request_phone=True,
    ),
    ContactMethod(
        "whatsapp", "WhatsApp", "🟢",
        prompt="Напишите номер WhatsApp в формате <b>+7XXXXXXXXXX</b> 🟢",
    ),
]
CONTACT_METHODS_BY_KEY = {m.key: m for m in CONTACT_METHODS}
CONTACT_METHODS_BY_LABEL = {m.label: m for m in CONTACT_METHODS}


@dataclass(frozen=True)
class FaqItem:
    key: str       # хранится в callback_data (faq:q:<key>)
    question: str  # текст кнопки
    answer: str    # ответ (HTML)


# Часто задаваемые вопросы. Чтобы добавить пункт — допишите сюда.
FAQ_ITEMS = [
    FaqItem(
        "how_to_get",
        "🚗 Как добраться?",
        "🧭 Дорога на Остров проще, чем кажется.\n\n"
        "🚩 <b>Точка сбора</b> — причал «Новомелково» (на картах так, но местные "
        "таксисты знают его как «причал МИФИ»).\n"
        "📍 <code>56.685085, 36.382499</code>\n"
        "🗺 <a href=\"https://yandex.ru/maps/?pt=36.382499,56.685085&z=16&l=map\">"
        "Открыть в Яндекс.Картах</a>\n\n"
        "🚗 <b>На машине</b>\n"
        "Кидаешь координаты в Яндекс.Карты — и маршрут до причала готов 😎\n"
        "🅿️ Парковка — 300 ₽/день.\n\n"
        "🚆 <b>Без машины</b>\n"
        "С Ленинградского вокзала → до станции <b>Редкино</b>.\n"
        "От станции — такси прямо у вокзала до причала Новомелково (МИФИ).\n"
        "📞 Такси «Тройка»: <b>+7 (906) 655-70-00</b>\n"
        "⚠️ В пик ждать можно до часа — заказывай заранее!\n\n"
        "🛥 От причала забираем тебя на остров — <b>10 минут по воде</b>, и ты "
        "в маленьком раю 🏝",
    ),
    FaqItem(
        "price",
        "💸 Сколько стоит?",
        "💸 Стоимость складывается из <b>двух частей</b>.\n\n"
        "🎟 <b>1. Билет на open air</b> — оплата заранее, переводом.\n"
        "• Одиночный — <b>2100 ₽</b>\n"
        "• На двоих — <b>3600 ₽</b> (по 1800 ₽ с человека)\n"
        "• Групповой на 4-х — <b>6000 ₽</b>\n"
        f"• Детский — <b>{CHILD_TICKET_PRICE} ₽</b> (половина взрослого)\n"
        "Это сама тусовка: приятная музыка, ночные сеты и уютная атмосфера "
        "летней ночи 🌙\n\n"
        f"🏝 <b>2. Вход на остров</b> — <b>{ISLAND_ENTRY_PRICE} ₽</b> "
        f"(детям — <b>{CHILD_ISLAND_ENTRY_PRICE} ₽</b>), оплата на месте, при выезде.\n"
        "Сюда входит:\n"
        "🛥 Трансфер на остров и обратно\n"
        "⛵ Покатушки на парусных катамаранах\n"
        "🏐 Волейбол\n"
        "🧖 Баня — детокс и полный расслабон\n"
        "…и другие активности на острове\n\n"
        "ℹ️ Проживание (палатки и кухни-шатры) и аренда снаряжения — отдельно. Своё "
        "привезёшь — сэкономишь, или арендуешь на острове.\n"
        "🔗 Все услуги и аренда клуба: <a href=\"https://ostrov-parusa.ru/\">"
        "ostrov-parusa.ru</a>\n\n"
        "🧮 Прикинуть всё под свою компанию можно в «Калькуляторе».",
    ),
    FaqItem(
        "island",
        "🏝 Это правда остров?",
        "🏝 <b>Да, это настоящий остров!</b>\n\n"
        "Тихий островок с сосновым лесом, со всех сторон — вода. Уединение, "
        "простор и свобода 💯\n\n"
        "⛵ Это парусный клуб «Остров» — ему уже 20 лет, и только сейчас мы решили "
        "устроить здесь ТУСОВКУ 🔥\n"
        "🛥 Попасть можно только по воде: трансфер забирает тебя с причала, и через "
        "10 минут ты на берегу.\n\n"
        "🌿 Взамен просим одно: уважай природу — не мусори, убери за собой после "
        "кэмпа и береги лес и его обитателей 💚",
    ),
    FaqItem(
        "music",
        "🎶 Какая музыка?",
        "🎶 Музыка — сердце Острова, и звучит она весь день по-разному:\n\n"
        "☀️ <b>Днём</b> — лёгкие мелодичные сеты у воды, чтобы валяться на песке и купаться.\n"
        "🌅 <b>На закате</b> — темп растёт, диджеи разгоняют к ночи.\n"
        "🌲 <b>Ночью</b> — глубокое техно и хаус на лесном танцполе среди сосен, "
        "до самого рассвета.\n\n"
        "🎧 Полный лайн-ап раскрываем ближе к датам — следите за анонсами.",
    ),
    FaqItem(
        "camping",
        "🏕 Что взять с собой?",
        "⛺ <b>Формат — палаточный, спортивно-туристический.</b> Своё снаряжение "
        "привезёшь — сэкономишь, или арендуешь на острове (уточняй наличие).\n\n"
        "Бери с собой:\n"
        "⛺ Палатку и спальник\n"
        "🧥 Тёплые вещи на ночь — у воды свежо\n"
        "👟 Удобную обувь и фонарик\n"
        "🍔 Еду и напитки — каждый сам себе, затарься заранее!\n\n"
        "🎪 <b>Едете компанией?</b> На острове можно арендовать не только палатку, "
        "но и кухню-шатёр — большой навес от дождя и солнца, где удобно собраться "
        "и готовить (плитка и газ уже внутри). Размеры — от малого до «Эвереста» "
        "на 30–40 человек; прикинь в «🧮 Калькуляторе».\n\n"
        "🛒 Если что-то кончится — есть магазин в Радченко.\n"
        "🌿 И главное: уважай природу — убери за собой и береги лес 💚",
    ),
]
FAQ_ITEMS_BY_KEY = {i.key: i for i in FAQ_ITEMS}

# Чек-лист «Сборы на Остров» — пункты как кнопки-галочки (см. handlers/packing.py).
# Состояние отмеченного кодируется битовой маской в callback_data, поэтому держим
# список стабильным по порядку (индекс = номер бита) и не длиннее ~25 пунктов,
# чтобы клавиатура оставалась обозримой.
PACK_ITEMS = [
    "⛺ Палатка",
    "🛌 Спальник",
    "🛏 Коврик под спальник",
    "💤 Подушка",
    "🪑 Удобный кемпинг-стул",
    "🩳 Одежда для пляжа",
    "🕶 Солнечные очки",
    "🧢 Головной убор",
    "🧴 Солнцезащитный крем",
    "🪩 Аутфит для танцев",
    "🩴 Кроксы / удобная обувь",
    "🧥 Тёплая одежда на вечер",
    "🦟 Репеллент от комаров",
    "🪥 Гигиенические принадлежности",
    "🔋 Заряженный пауэрбанк (розетки тоже будут)",
    "😴 Маска для сна ‼️",
    "🙉 Беруши ‼️",
    "🥤 Свой стакан для напитков",
    "🔦 Фонарик",
    "🌧 Дождевик",
    "👙 Девочкам — запасные купальники",
    "🧖 Простыня для бани",
    "💊 Аптечка",
]

# Статусы заявки. Ключ хранится в БД/таблице, значение показывается людям.
STATUS_NEW = "Новая"
STATUS_IN_PROGRESS = "В работе"
STATUS_PAID = "Оплачено"
STATUS_DONE = "Завершена"
STATUS_REJECTED = "Отказ"

# Эмодзи для наглядности в сообщениях и списках.
STATUS_EMOJI = {
    STATUS_NEW: "🆕",
    STATUS_IN_PROGRESS: "⏳",
    STATUS_PAID: "💰",
    STATUS_DONE: "🎉",
    STATUS_REJECTED: "❌",
}

# Кнопки смены статуса, которые видит менеджер (кроме текущего статуса).
MANAGER_STATUSES = [STATUS_IN_PROGRESS, STATUS_PAID, STATUS_DONE, STATUS_REJECTED]


def status_label(status: str) -> str:
    return f"{STATUS_EMOJI.get(status, '•')} {status}"


@dataclass
class Application:
    name: str
    contact_method: str  # как клиенту удобнее связаться: "Telegram"/"Телефон"/"WhatsApp"
    contact: str         # значение контакта: "@user" / "+7..." и т.п.
    username: str        # @username аккаунта (для кнопки менеджера), либо "не задан"
    tickets: int
    children: int = 0    # детских билетов (по CHILD_TICKET_PRICE, половина взрослого)
    amount: int | None = None  # сумма к оплате в рублях (если известна)
    user_id: int | None = None  # Telegram-id клиента: нужен, чтобы менеджер мог написать
    id: int | None = None  # присваивается хранилищем при сохранении
    created_at: datetime = field(default_factory=datetime.now)
    status: str = STATUS_NEW
    extras_note: str | None = None  # состав расчёта из калькулятора (если заявка пришла оттуда)
    source: str | None = None  # источник перехода из deep-link /start <payload> (UTM)

    # --- конструкторы -----------------------------------------------------
    @classmethod
    def from_webapp(cls, data: dict, fallback_username: str | None = None,
                    user_id: int | None = None) -> "Application":
        """Строит заявку из payload Mini App (Telegram.WebApp.sendData).

        Актуальный payload зеркалит диалог в чате: способ связи на выбор
        (telegram/phone/whatsapp), контакт, взрослые и детские билеты.
        Старый формат {name, phone, tickets} тоже принимается. Сумму считаем
        сами по ценам из models — присланному клиентом не доверяем.
        Бросает ValueError, если в данных нет имени или контакта.
        """
        name = str(data.get("name", "")).strip()
        method = CONTACT_METHODS_BY_KEY.get(
            str(data.get("contact_method", "")).strip(), CONTACT_METHODS_BY_KEY["phone"]
        )
        contact = str(data.get("contact") or data.get("phone") or "").strip()
        raw_username = data.get("username") or fallback_username
        # Telegram без введённого ника — подставляем @username аккаунта,
        # как это делает диалог заявки в чате.
        if not contact and method.key == "telegram" and raw_username:
            contact = f"@{raw_username}"
        if not name or not contact:
            raise ValueError("В заявке нет имени или контакта")

        tickets = cls._clamp_tickets(data.get("tickets", 1))
        children = cls._clamp_children(data.get("children", 0))
        return cls(
            name=name,
            contact_method=method.label,
            contact=contact,
            username=f"@{raw_username}" if raw_username else "не задан",
            tickets=tickets,
            children=children,
            amount=ticket_price_for(tickets) + children * CHILD_TICKET_PRICE,
            user_id=user_id,
        )

    @staticmethod
    def _clamp_tickets(value) -> int:
        try:
            tickets = int(value)
        except (TypeError, ValueError):
            tickets = 1
        return max(1, min(tickets, MAX_TICKETS))

    @staticmethod
    def _clamp_children(value) -> int:
        try:
            children = int(value)
        except (TypeError, ValueError):
            children = 0
        return max(0, min(children, MAX_TICKETS))

    @property
    def amount_label(self) -> str:
        """Сумма для показа людям: «6000 ₽» либо «—», если неизвестна."""
        return f"{self.amount} ₽" if self.amount else "—"

    @property
    def contact_label(self) -> str:
        """Способ связи + значение, напр. «💬 Telegram: @user»."""
        method = CONTACT_METHODS_BY_LABEL.get(self.contact_method)
        prefix = method.emoji if method else "🔗"
        return f"{prefix} {self.contact_method}: {self.contact}"

    # --- представления ----------------------------------------------------
    def to_sheet_row(self) -> list[str]:
        """Строка для добавления в Google-таблицу (порядок = SHEET_HEADERS)."""
        return [
            str(self.id or ""),
            self.created_at.strftime("%Y-%m-%d %H:%M"),
            self.name,
            self.contact_method,
            self.contact,
            self.username,
            str(self.tickets),
            str(self.amount) if self.amount else "",
            self.status,
            self.source or "",
            str(self.children) if self.children else "",
        ]

    def to_manager_message(self) -> str:
        """HTML-сообщение для чата менеджеров."""
        header = "🎟 <b>Новая заявка на вечеринку «Остров»</b>"
        # Состав из калькулятора (наш собственный текст, без спецсимволов HTML).
        extras = f"🏕 <b>Состав расчёта:</b>\n{self.extras_note}\n" if self.extras_note else ""
        src = f"📈 <b>Источник:</b> {escape(self.source)}\n" if self.source else ""
        # Аванс (перевод менеджеру) — только билет на open air по групповому тарифу.
        # Остальное в сумме (вход на остров + аренда) гость платит на острове при
        # выезде, не переводом. Разводим, чтобы менеджер не собрал лишнее. Для прямых
        # заявок сумма = аванс, on_club = 0 — строку не показываем.
        split = ""
        if self.amount:
            advance = ticket_price_for(self.tickets) + self.children * CHILD_TICKET_PRICE
            on_club = self.amount - advance
            if on_club > 0:
                split = (
                    f"   ├ 💳 аванс (перевод): {advance} ₽\n"
                    f"   └ 🏝 на острове при выезде: {on_club} ₽\n"
                )
        return (
            f"{header}\n\n"
            f"🆔 <b>Заявка #{self.id}</b>\n"
            f"👤 <b>Имя:</b> {escape(self.name)}\n"
            f"🔗 <b>Связь:</b> {escape(self.contact_label)}\n"
            f"💬 <b>Username:</b> {escape(self.username)}\n"
            f"🎫 <b>Человек:</b> {self.tickets}"
            + (f" + 🧒 детей: {self.children}" if self.children else "") + "\n"
            f"💰 <b>Сумма:</b> {self.amount_label}\n"
            f"{split}"
            f"{extras}"
            f"{src}"
            f"🕒 <b>Время:</b> {self.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📌 <b>Статус:</b> {status_label(self.status)}"
        )

    def to_list_line(self) -> str:
        """Короткая строка для списка заявок (/leads)."""
        return (
            f"<b>#{self.id}</b> {STATUS_EMOJI.get(self.status, '•')} "
            f"{escape(self.name)} · {escape(self.contact_label)} · 🎫{self.tickets}"
            f"{f'+🧒{self.children}' if self.children else ''} "
            f"· 💰{self.amount_label} · {self.created_at.strftime('%d.%m %H:%M')}"
        )

    def to_user_summary(self) -> str:
        """Сводка для подтверждения пользователем."""
        if self.extras_note:
            # Заявка из калькулятора — показываем состав и что всё уже в сумме.
            extras = f"🏕 Состав:\n{self.extras_note}\n\n"
            note = (
                "ℹ️ <i>В сумму входят билет на open air и вход на остров (трансфер, "
                "парусные катамараны, волейбол, баня и другие активности), аренда и "
                "снаряжение. Часть оплачивается заранее, вход на остров — при выезде. "
                "Скрытых доплат нет. Финальную стоимость подтвердит менеджер.</i>"
            )
            people_label = "👥 Человек"
            # Из калькулятора вход на остров уже сидит в общей сумме.
            cost_block = f"💰 К оплате: <b>{self.amount_label}</b>\n\n"
        else:
            extras = ""
            note = (
                "ℹ️ <i>Бронируем билет на open air (оплата заранее). Вход на остров — "
                "это трансфер, парусные катамараны, волейбол, баня и другие активности; "
                "проживание и аренда — отдельно.</i>"
            )
            people_label = "🎫 Билетов"
            # Прямой поток: показываем обе части честно — билет заранее и вход на
            # остров при выезде (доминирующая статья, чтобы не было сюрприза на причале).
            island_total = (self.tickets * ISLAND_ENTRY_PRICE
                            + self.children * CHILD_ISLAND_ENTRY_PRICE)
            island_detail = f"{ISLAND_ENTRY_PRICE} ₽ × {self.tickets}"
            if self.children:
                island_detail += f" + {CHILD_ISLAND_ENTRY_PRICE} ₽ × {self.children} 🧒"
            cost_block = (
                f"💰 Билет (оплата заранее): <b>{self.amount_label}</b>\n"
                f"🏝 Вход на остров при выезде: <b>~{island_total} ₽</b> "
                f"({island_detail})\n\n"
            )
        children_line = (
            f"🧒 Детских билетов: <b>{self.children}</b> (по {CHILD_TICKET_PRICE} ₽)\n"
            if self.children else ""
        )
        return (
            "Почти готово! Проверьте заявку 👇\n\n"
            f"👤 Имя: <b>{escape(self.name)}</b>\n"
            f"🔗 Связь: <b>{escape(self.contact_label)}</b>\n"
            f"{people_label}: <b>{self.tickets}</b>\n"
            f"{children_line}"
            f"{cost_block}"
            f"{extras}"
            f"{note}\n\n"
            "Всё верно? ✅"
        )
