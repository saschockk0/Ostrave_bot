"""Хендлер FAQ — ветка «Есть вопрос» из главного меню.

Показываем список частых вопросов; на каждый ответ предлагаем вернуться
к списку или, если ответа не нашлось, оставить заявку (callback faq:apply
обрабатывается в handlers.application).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from keyboards import BTN_FAQ, faq_answer_kb, faq_menu_kb
from models import FAQ_ITEMS_BY_KEY

router = Router()

FAQ_INTRO = (
    "❓ <b>Частые вопросы</b>\n\n"
    "Выберите, что интересует 👇\n"
    "А если ответа не нашлось — жмите <b>«📝 Оставить заявку»</b>, "
    "и менеджер всё подробно расскажет."
)


@router.message(F.text == BTN_FAQ)
async def show_faq(message: Message) -> None:
    await message.answer(FAQ_INTRO, reply_markup=faq_menu_kb())


@router.callback_query(F.data == "faq:menu")
async def back_to_menu(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.edit_text(FAQ_INTRO, reply_markup=faq_menu_kb())


@router.callback_query(F.data.startswith("faq:q:"))
async def show_answer(call: CallbackQuery) -> None:
    item = FAQ_ITEMS_BY_KEY.get(call.data.split(":", 2)[2])
    if item is None:
        await call.answer("Вопрос не найден", show_alert=True)
        return
    await call.answer()
    # «Что взять с собой» открывает интерактивный чек-лист сборов.
    extra = ("🎒 Собрать рюкзак", "pack:open") if item.key == "camping" else None
    await call.message.edit_text(
        f"<b>{item.question}</b>\n\n{item.answer}",
        reply_markup=faq_answer_kb(extra),
        # Ответы вроде «Как добраться?» содержат ссылки на карты — без превью
        # они выглядят как в макете, аккуратным текстом, а не громоздкой карточкой.
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
