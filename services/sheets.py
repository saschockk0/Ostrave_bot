"""Зеркалирование заявок в Google Sheets через сервис-аккаунт.

Запись изолирована: любые ошибки логируются, но не пробрасываются наверх,
чтобы сбой таблицы не мешал работе бота. Источник правды — services/storage.py,
таблица лишь дублирует данные для тех, кому удобнее смотреть их там.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import gspread

from config import Config
from models import SHEET_HEADERS, Application

logger = logging.getLogger(__name__)

_ID_COL = 1  # колонка ID (1-based) — по ней ищем строку для обновления статуса
# «Статус» больше не последняя колонка (после неё «Источник»), ищем по имени.
_STATUS_COL = SHEET_HEADERS.index("Статус") + 1


@lru_cache(maxsize=1)
def _open_worksheet(gsheet_id: str, creds_path: str, worksheet: str):
    """Открывает лист таблицы. Кэшируется, чтобы не авторизоваться каждый раз."""
    client = gspread.service_account(filename=creds_path)
    spreadsheet = client.open_by_key(gsheet_id)
    ws = spreadsheet.worksheet(worksheet) if worksheet else spreadsheet.sheet1

    # Проставляем заголовки, если лист пустой.
    if not ws.row_values(1):
        ws.append_row(SHEET_HEADERS)
    return ws


def is_enabled(config: Config) -> bool:
    return bool(config.gsheet_id and os.path.exists(config.google_creds_path))


def append_application(config: Config, application: Application) -> bool:
    """Добавляет заявку строкой в таблицу. Возвращает True при успехе."""
    if not is_enabled(config):
        logger.info("Google Sheets отключён (нет GSHEET_ID или creds) — пропускаю запись.")
        return False
    try:
        ws = _open_worksheet(config.gsheet_id, config.google_creds_path, config.gsheet_worksheet)
        ws.append_row(application.to_sheet_row(), value_input_option="USER_ENTERED")
        return True
    except Exception:  # noqa: BLE001 — запись в таблицу не должна ронять бота
        logger.exception("Не удалось записать заявку в Google Sheets")
        return False


def update_status(config: Config, lead_id: int, status: str) -> bool:
    """Находит строку по ID и обновляет в ней колонку «Статус»."""
    if not is_enabled(config):
        return False
    try:
        ws = _open_worksheet(config.gsheet_id, config.google_creds_path, config.gsheet_worksheet)
        cell = ws.find(str(lead_id), in_column=_ID_COL)
        if cell is None:
            logger.warning("Заявка #%s не найдена в таблице — статус не обновлён", lead_id)
            return False
        ws.update_cell(cell.row, _STATUS_COL, status)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось обновить статус заявки #%s в Google Sheets", lead_id)
        return False
