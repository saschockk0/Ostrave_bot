# Перенос бота на Linux-сервер

Код кроссплатформенный (чистый Python, относительные пути, SQLite из stdlib) —
на Linux он работает без изменений. Меняется только способ запуска:
`restart_bot.ps1` — это Windows-лаунчер, на сервере его заменяет systemd
(`deploy/ostrave-bot.service`).

Требуется Python **3.11+** (сейчас прод работает на 3.13 — подойдёт любой из них).

## Что переносить

| Что | Зачем | Обязательно |
|-----|-------|-------------|
| код проекта (`*.py`, `handlers/`, `middlewares/`, `services/`, `content/`, `requirements.txt`) | сам бот | ✅ |
| `.env` | токен и настройки прода | ✅ |
| `leads.db` | **все заявки — источник правды** | ✅ |
| `fsm.db` | недозаполненные диалоги гостей | желательно |
| `creds.json` | ключ Google Sheets | только если включён `GSHEET_ID` (сейчас выключен) |

**Не** переносить: `.venv/`, `__pycache__/`, `bot*.log`, `webapp/node_modules/`.
`webapp/` целиком можно пропустить — `WEBAPP_URL` в проде пуст, Mini App не используется.

Архив для переноса (собирается на Windows-машине):

```powershell
tar -czf ostrave_bot.tar.gz --exclude=.venv --exclude=__pycache__ `
    --exclude='bot*.log*' --exclude=webapp -C C:\ -- Ostrave_bot
```

## Установка на сервере

```bash
# 1. Пользователь и каталог
sudo useradd --system --home /opt/ostrave_bot --shell /usr/sbin/nologin ostrave
sudo mkdir -p /opt/ostrave_bot
sudo tar -xzf ostrave_bot.tar.gz -C /opt --strip-components=1  # Ostrave_bot → /opt/ostrave_bot
sudo chown -R ostrave:ostrave /opt/ostrave_bot

# 2. Окружение
cd /opt/ostrave_bot
sudo -u ostrave python3 -m venv .venv
sudo -u ostrave .venv/bin/pip install -r requirements.txt

# 3. Префлайт (тот же, что делал restart_bot.ps1)
sudo -u ostrave .venv/bin/python -c "import handlers, keyboards, models; handlers.setup_routers()"

# 4. systemd
sudo cp deploy/ostrave-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ostrave-bot
```

## Переключение (важен порядок!)

Telegram допускает **только один** polling-экземпляр на токен. Два бота сразу →
`TelegramConflictError`, заявки будут теряться. Поэтому:

1. **Остановить бота на Windows** (от имени администратора):
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
       Where-Object { $_.CommandLine -match 'bot\.py' } |
       ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
2. **Забрать свежие `leads.db` и `fsm.db`** уже после остановки (чтобы не потерять
   заявки последних минут) и положить их в `/opt/ostrave_bot/`.
3. **Запустить на сервере:** `sudo systemctl start ostrave-bot`
4. **Проверить:**
   ```bash
   systemctl status ostrave-bot                 # active (running)
   journalctl -u ostrave-bot -n 30              # нет Traceback / TelegramConflictError
   ```
   И в Telegram: `/start` боту → меню отвечает; тестовая заявка падает в чат
   менеджеров; в чате менеджеров работает `/leads`.
5. На Windows-машине убрать автозапуск `restart_bot.ps1`, если он был
   (планировщик задач), чтобы старая копия не поднялась после перезагрузки.

## Эксплуатация

| Действие | Команда |
|----------|---------|
| Статус / логи | `systemctl status ostrave-bot` · `journalctl -u ostrave-bot -f` |
| Перезапуск после обновления кода | префлайт (шаг 3 выше) → `sudo systemctl restart ostrave-bot` |
| Логи бота (ротируемые) | `/opt/ostrave_bot/bot.log` |
| Бэкап заявок | достаточно копировать `leads.db` (например, в cron) |
