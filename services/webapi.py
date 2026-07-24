"""HTTP-приём заявок из Mini App (кнопка «Меню» у поля ввода).

`Telegram.WebApp.sendData` доставляет данные боту только тогда, когда апп
открыт reply-кнопкой; из кнопки «Меню» и из инлайн-кнопок он молча ничего не
шлёт. Поэтому форма афиши отправляет заявку обычным POST сюда, а подлинность
подтверждает подписью `initData` — её Telegram считает на токене бота, так что
подделать заявку от чужого имени нельзя.

Слушаем только localhost: наружу порт отдаёт nginx на пути `/afisha/api/`
(см. deploy/nginx-afisha.conf). Заявка уходит в тот же
`services.leads.submit_application`, что и диалог в чате.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from aiogram import Bot
from aiohttp import web

from config import Config
from models import Application
from services import leads

logger = logging.getLogger(__name__)

# Подпись initData живёт сутки: просроченную не принимаем, чтобы перехваченный
# запрос нельзя было переиграть спустя неделю.
INIT_DATA_MAX_AGE = 24 * 60 * 60


def check_init_data(init_data: str, bot_token: str) -> dict[str, str] | None:
    """Проверяет подпись initData по алгоритму Telegram.

    Возвращает разобранные поля (user, auth_date, …) либо None, если подпись
    не сходится, протухла или строка вообще не разбирается.
    """
    if not init_data:
        return None
    try:
        fields = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = fields.pop("hash", "")
    if not received_hash:
        return None

    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return None

    try:
        auth_age = time.time() - int(fields.get("auth_date", "0"))
    except ValueError:
        return None
    if auth_age > INIT_DATA_MAX_AGE:
        return None

    return fields


def _user_from_fields(fields: dict[str, str]) -> dict:
    try:
        user = json.loads(fields.get("user", "{}"))
    except ValueError:
        return {}
    return user if isinstance(user, dict) else {}


async def _handle_application(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    config: Config = request.app["config"]

    try:
        body = await request.json()
    except (ValueError, TypeError):
        return web.json_response({"ok": False, "error": "bad_json"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"ok": False, "error": "bad_json"}, status=400)

    fields = check_init_data(str(body.get("init_data") or ""), config.bot_token)
    if fields is None:
        logger.warning("Заявка из Mini App с невалидной подписью initData отклонена")
        return web.json_response({"ok": False, "error": "bad_signature"}, status=403)

    user = _user_from_fields(fields)
    payload = body.get("application")
    if not isinstance(payload, dict):
        return web.json_response({"ok": False, "error": "no_application"}, status=400)

    try:
        application = Application.from_webapp(
            payload,
            fallback_username=user.get("username"),
            user_id=user.get("id"),
        )
    except ValueError:
        return web.json_response({"ok": False, "error": "not_enough_data"}, status=400)

    application = await leads.submit_application(bot, config, application)

    # Дублируем подтверждение в чат — как при заявке из диалога, чтобы у гостя
    # осталась история под рукой.
    if application.user_id:
        try:
            await bot.send_message(
                application.user_id,
                "🎉 <b>Готово!</b> Заявка принята.\n\n"
                "Менеджер совсем скоро свяжется с вами. До встречи на берегу! 🌅",
            )
        except Exception:  # noqa: BLE001 — гость мог закрыть личку боту
            logger.warning("Не удалось подтвердить заявку #%s в личке", application.id)

    return web.json_response({"ok": True, "id": application.id})


async def _handle_health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def start(bot: Bot, config: Config) -> web.AppRunner | None:
    """Поднимает локальный HTTP-сервер приёма заявок.

    Возвращает runner (его нужно `cleanup()` при остановке) либо None, если
    приём выключен или порт занят — бот в любом случае должен подняться.
    """
    if not config.webapp_api_port:
        return None

    app = web.Application()
    app["bot"] = bot
    app["config"] = config
    app.add_routes([web.post("/application", _handle_application), web.get("/health", _handle_health)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.webapp_api_host, config.webapp_api_port)
    try:
        await site.start()
    except OSError:
        logger.exception(
            "Не удалось занять %s:%s — приём заявок из Mini App по HTTP выключен",
            config.webapp_api_host,
            config.webapp_api_port,
        )
        await runner.cleanup()
        return None

    logger.info(
        "Приём заявок из Mini App слушает http://%s:%s", config.webapp_api_host, config.webapp_api_port
    )
    return runner
