# 🏝 THE OSTROV - open air (Telegram Mini App)

Лендинг open-air вечеринки «Остров», упакованный в Telegram Mini App.
Пользователь листает афишу (план по дням, цены, дорога, FAQ) и оставляет
заявку прямо внутри Telegram — с теми же полями, что в диалоге бота: способ
связи (Telegram / телефон / WhatsApp), тариф билета и детские билеты.
Заявка уходит боту через `Telegram.WebApp.sendData`.

## Стек
Vite + React + TypeScript + Tailwind v4 + Motion. Шрифты самохостятся через
Fontsource (Comfortaa / Manrope / JetBrains Mono / Caveat, латиница + кириллица).

## Дизайн
Оформление повторяет официальную афишу (`src/assets/afisha.jpg`): аэрофото
соснового леса и Волги, тёмная «вода» как базовый фон, белая типографика,
округлый дисплейный шрифт (Comfortaa — ближайший к леттерингу афиши),
рукописные акценты (Caveat, как «что в программе?» на афише), mono-подписи
вразрядку и один цветовой акцент — подсвеченная солнцем листва. Верхние 3/4
афиши — арт героя (леттеринг уже в изображении), низ пересобран живой
типографикой. Тема тёмная. Контент центрируется колонкой `max-w-[560px]` —
на десктопе выглядит как мобильное приложение.

## Запуск

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # прод-сборка в dist/
npm run preview    # предпросмотр сборки
npm run typecheck  # проверка типов
```

## Структура

| Путь | Назначение |
|------|------------|
| `src/App.tsx` | сборка секций + фикс. CTA |
| `src/hooks/useTelegram.ts` | инициализация WebApp (expand, цвета, haptic, user) |
| `src/sections/Hero.tsx` | афишный герой с кинетикой и бегущей строкой |
| `src/sections/Facts.tsx` | блок Когда / Где / Зачем |
| `src/sections/Program.tsx` | план на три дня (как «Тур по Острову» у бота) |
| `src/sections/Prices.tsx` | цены: билеты + вход на остров (как FAQ бота) |
| `src/sections/Venue.tsx` | точка сбора, дорога, парковка, такси, маршрут |
| `src/sections/Faq.tsx` | частые вопросы (сокращённый FAQ бота) |
| `src/sections/Apply.tsx` | форма заявки: способ связи, тариф, дети, сводка цены |
| `src/components/*` | Marquee, Reveal, StickyCTA |
| `src/data/event.ts` | контент: даты, программа по дням, FAQ, локация |
| `src/data/pricing.ts` | цены и авто-тариф — зеркало `models.py`/`pricing.py` бота |

Контент меняется в `src/data/event.ts`, цены — в `src/data/pricing.ts`
(они должны совпадать с `models.py` / `pricing.py` бота — бот пересчитывает
сумму сам и не доверяет клиенту).

## Подключение к Telegram

1. **Хостинг.** Залейте `dist/` на любой HTTPS-хостинг (Vercel / Netlify / GitHub
   Pages / свой сервер). Telegram Mini App требует HTTPS. Прод живёт на
   `https://pkostrov.ru/afisha/` — статика в `/var/www/afisha`, конфиг nginx
   лежит в репозитории: `../deploy/nginx-afisha.conf`.
2. **Кнопки.** Достаточно задать боту `WEBAPP_URL` — он сам ставит афишу
   и первым рядом reply-меню (`keyboards.main_kb`), и на кнопку «Меню» у поля
   ввода (`set_chat_menu_button` в `bot.py`). В BotFather ничего делать не нужно.
3. **Приём заявки.** Форма шлёт `POST api/application` (относительно адреса
   аппа → `/afisha/api/application`) с телом `{init_data, application}`;
   nginx проксирует его в бота на `127.0.0.1:8081`, а `services/webapi.py`
   проверяет подпись `initData` на токене бота. Запасной путь — старый
   `tg.sendData(...)`: он доставляет данные как `message.web_app_data`, но
   **только если Mini App открыт reply-кнопкой `web_app`** (из кнопки «Меню»
   молча ничего не отправляет — ради этого и появился HTTP-приём). Payload
   `application`:

   ```json
   {
     "type": "party_application",
     "name": "Алекс",
     "contact_method": "telegram",
     "contact": "@alex",
     "tickets": 2,
     "children": 1,
     "username": "alex",
     "tg_id": 12345678
   }
   ```

   `contact_method` — ключ из `models.CONTACT_METHODS` (`telegram` / `phone` /
   `whatsapp`). Старый формат `{name, phone, tickets}` бот тоже принимает.

## Связка с ботом (в каталоге `../`)

Бот принимает заявки из Mini App двумя путями: `services/webapi.py` (HTTP,
основной) и `handlers/webapp.py` (`F.web_app_data`, запасной). Оба строят
`models.Application.from_webapp` (сумма считается на стороне бота: тариф +
детские билеты) и отдают в тот же `services/leads.submit_application`, что и
диалог в чате — заявка падает в чат менеджеров и в Google-таблицу.

## Что заменить перед продакшеном
- `src/data/event.ts` → реальная ссылка на карту (`mapUrl`), год, программа.
- При желании добавить фирменные иллюстрации с афиши (палатка, дерево, лодка) -
  как `<img>` в Hero / Program, дизайн рассчитан на их добавление.
