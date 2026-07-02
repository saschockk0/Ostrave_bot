# 🏝 THE OSTROV - open air (Telegram Mini App)

Лендинг open-air вечеринки «Остров», упакованный в Telegram Mini App.
Пользователь листает афишу и оставляет заявку (имя, телефон, кол-во билетов)
прямо внутри Telegram. Заявка уходит боту через `Telegram.WebApp.sendData`.

## Стек
Vite + React + TypeScript + Tailwind v4 + Motion. Шрифты самохостятся через
Fontsource (Unbounded / Manrope / JetBrains Mono / Permanent Marker, латиница + кириллица).

## Дизайн
Зин/панк-эстетика афиши: тёплая бумага, оранжевый + чёрный, толстые контуры,
hard-shadow «стикеры», halftone-текстура, маркерные рукописные акценты, бегущие
строки. Тема намеренно залочена в светлую (бренд-решение). Контент центрируется
колонкой `max-w-[560px]` — на десктопе выглядит как мобильное приложение.

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
| `src/sections/Program.tsx` | стикер-карточки программы |
| `src/sections/Venue.tsx` | локация + «Построить маршрут» |
| `src/sections/Apply.tsx` | форма заявки (имя, телефон, билеты) |
| `src/components/*` | Marquee, Reveal, StickyCTA |
| `src/data/event.ts` | весь контент мероприятия (даты, программа, ссылка на карту) |

Контент мероприятия меняется в одном месте: `src/data/event.ts`.

## Подключение к Telegram

1. **Хостинг.** Залейте `dist/` на любой HTTPS-хостинг (Vercel / Netlify / GitHub
   Pages / свой сервер). Telegram Mini App требует HTTPS.
2. **BotFather.** У бота: `/newapp` (или `Bot Settings → Web App`), укажите
   URL вашего хостинга. Либо добавьте кнопку:
   - **меню-кнопка**: `Bot Settings → Menu Button → URL`;
   - **reply-кнопка**: `KeyboardButton(text="Открыть афишу", web_app=WebAppInfo(url=...))`.
3. **Приём заявки.** Форма вызывает `tg.sendData(JSON.stringify(payload))`.
   `sendData` доставляет данные боту как `message.web_app_data` **только если
   Mini App открыт reply-кнопкой `web_app`**. Payload:

   ```json
   {
     "type": "party_application",
     "name": "Алекс",
     "phone": "+7 999 123-45-67",
     "tickets": 2,
     "username": "alex",
     "tg_id": 12345678
   }
   ```

## Связка с ботом (в каталоге `../`)

Бот в корне репозитория уже умеет форматировать заявку и слать её менеджерам +
в Google Sheets. Чтобы принять данные из Mini App, добавьте хендлер, который
ловит `F.web_app_data`, парсит JSON и переиспользует существующие сервисы
`services/notify.py` и `services/sheets.py` (и модель `models.Application`).
Тогда заявки из веб-аппа лягут в тот же чат менеджеров и ту же таблицу.

## Что заменить перед продакшеном
- `src/data/event.ts` → реальная ссылка на карту (`mapUrl`), год, программа.
- При желании добавить фирменные иллюстрации с афиши (палатка, дерево, лодка) -
  как `<img>` в Hero / Program, дизайн рассчитан на их добавление.
