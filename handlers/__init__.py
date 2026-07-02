from aiogram import Router

from handlers import (
    application,
    calculator,
    fallback,
    faq,
    manager,
    packing,
    start,
    tour,
    webapp,
)


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(manager.router)      # команды и кнопки менеджеров
    router.include_router(faq.router)          # ветка «Есть вопрос» (FAQ)
    router.include_router(tour.router)         # «Тур по Острову» (кнопка «О вечеринке»)
    router.include_router(packing.router)      # интерактивный чек-лист сборов
    router.include_router(calculator.router)   # калькулятор стоимости
    router.include_router(application.router)  # диалог «оставить заявку»
    router.include_router(webapp.router)       # приём из Mini App (опционально)
    router.include_router(fallback.router)     # must be last — catch-all
    return router
