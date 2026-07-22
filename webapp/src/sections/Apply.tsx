import { useState } from "react";
import type { RefObject } from "react";
import { useTelegram } from "../hooks/useTelegram";
import {
  CHILD_ISLAND_ENTRY_PRICE,
  CHILD_TICKET_PRICE,
  ISLAND_ENTRY_PRICE,
  MAX_TICKETS,
  TICKET_OPTIONS,
  fmt,
  ticketPriceFor,
} from "../data/pricing";

const PHONE_RE = /^\+?\d[\d\s\-()]{7,}$/;
const USERNAME_RE = /^@?[a-zA-Z0-9_]{4,}$/;

// Приём заявок ботом (services/webapi.py), относительный путь: апп лежит на
// /afisha/, nginx проксирует /afisha/api/ внутрь бота. sendData тут не годится —
// из кнопки «Меню» у поля ввода он ничего не отправляет.
const API_URL = "api/application";

// Способы связи — как в диалоге бота (models.CONTACT_METHODS).
const CONTACT_METHODS = [
  { key: "telegram", label: "Telegram", emoji: "💬", placeholder: "@username" },
  { key: "phone", label: "Телефон", emoji: "📞", placeholder: "+7 999 123-45-67" },
  { key: "whatsapp", label: "WhatsApp", emoji: "🟢", placeholder: "+7XXXXXXXXXX" },
] as const;

type MethodKey = (typeof CONTACT_METHODS)[number]["key"];
type TariffKey = (typeof TICKET_OPTIONS)[number]["key"] | "custom";

type Errors = { name?: string; contact?: string };

function Stepper({
  value,
  min,
  onChange,
  suffix,
}: {
  value: number;
  min: number;
  onChange: (v: number) => void;
  suffix: string;
}) {
  const { haptic } = useTelegram();
  const step = (d: number) => {
    haptic("light");
    onChange(Math.max(min, Math.min(value + d, MAX_TICKETS)));
  };
  const btn =
    "h-12 w-12 rounded-full border border-foam/30 font-display text-xl font-bold text-foam transition active:bg-foam/10 disabled:opacity-30";
  return (
    <div className="flex items-center gap-3">
      <button type="button" onClick={() => step(-1)} disabled={value <= min} className={btn}>
        −
      </button>
      <span className="min-w-[7ch] text-center font-display text-lg font-bold">
        {value} {suffix}
      </span>
      <button type="button" onClick={() => step(1)} disabled={value >= MAX_TICKETS} className={btn}>
        +
      </button>
    </div>
  );
}

export function Apply({ sectionRef }: { sectionRef: RefObject<HTMLElement> }) {
  const { tg, haptic, user, initData } = useTelegram();

  const [name, setName] = useState(user?.first_name ?? "");
  const [method, setMethod] = useState<MethodKey>("telegram");
  const [contact, setContact] = useState("");
  const [tariff, setTariff] = useState<TariffKey>("single");
  const [customCount, setCustomCount] = useState(5);
  const [children, setChildren] = useState(0);
  const [errors, setErrors] = useState<Errors>({});
  const [done, setDone] = useState(false);
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);

  // Telegram с @username в профиле — контакт подставляется сам, как в боте.
  const autoUsername = method === "telegram" && user?.username ? `@${user.username}` : null;

  const tickets = tariff === "custom" ? customCount : TICKET_OPTIONS.find((o) => o.key === tariff)!.tickets;
  const ticketCost = ticketPriceFor(tickets) + children * CHILD_TICKET_PRICE;
  const islandCost = tickets * ISLAND_ENTRY_PRICE + children * CHILD_ISLAND_ENTRY_PRICE;

  const submit = async () => {
    if (sending) return;
    const next: Errors = {};
    const contactValue = (autoUsername ?? contact).trim();
    if (name.trim().length < 2) next.name = "Как вас зовут?";
    if (!contactValue) {
      next.contact = "Куда вам написать?";
    } else if (method === "telegram" && !USERNAME_RE.test(contactValue)) {
      next.contact = "Ник в Telegram — например, @username";
    } else if (method !== "telegram" && !PHONE_RE.test(contactValue)) {
      next.contact = "Похоже, номер неполный";
    }
    setErrors(next);
    if (Object.keys(next).length > 0) {
      haptic("heavy");
      return;
    }

    const payload = {
      type: "party_application",
      name: name.trim(),
      contact_method: method,
      contact:
        method === "telegram" && !contactValue.startsWith("@")
          ? `@${contactValue}`
          : contactValue,
      tickets,
      children,
      username: user?.username ?? null,
      tg_id: user?.id ?? null,
    };

    haptic("medium");
    setFailed(false);

    // Основной путь: POST боту с подписью initData — работает независимо от
    // того, откуда открыли афишу (кнопка «Меню», reply-кнопка, ссылка).
    if (initData) {
      setSending(true);
      try {
        const res = await fetch(API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: initData, application: payload }),
        });
        const data = await res.json();
        if (res.ok && data?.ok) {
          haptic("rigid");
          setDone(true);
          return;
        }
        throw new Error(String(data?.error ?? res.status));
      } catch (err) {
        console.warn("Заявку не приняли по HTTP:", err);
      } finally {
        setSending(false);
      }
    }

    if (tg?.sendData) {
      // Запасной путь: доставка боту сообщением. Работает, только если апп
      // открыт reply-кнопкой web_app; заодно закрывает Mini App.
      try {
        tg.sendData(JSON.stringify(payload));
        return;
      } catch (err) {
        console.warn("sendData недоступен:", err);
      }
    }
    if (initData) {
      // В Telegram, но отправить не вышло — честно говорим об этом.
      haptic("heavy");
      setFailed(true);
      return;
    }
    // Локальная разработка / запуск вне Telegram.
    console.log("Заявка:", payload);
    setDone(true);
  };

  const label = "font-mono text-[11px] uppercase tracking-[0.2em] text-foam/60";
  const input =
    "rounded-xl border border-foam/25 bg-deep/60 px-4 py-3 font-body text-foam outline-none placeholder:text-foam/40 focus:border-leaf";
  const chip = (active: boolean) =>
    `rounded-full border px-4 py-3 font-display font-bold transition ${
      active ? "border-leaf bg-leaf text-deep" : "border-foam/30 text-foam active:bg-foam/10"
    }`;
  const card = (active: boolean) =>
    `rounded-xl border p-4 text-left transition ${
      active ? "border-leaf bg-leaf text-deep" : "border-foam/25 text-foam active:bg-foam/10"
    }`;

  return (
    <section ref={sectionRef} id="apply" className="border-t border-foam/10 bg-pine px-5 py-14">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="font-display text-3xl font-bold leading-tight">Заявка</h2>
        <span className="font-script text-2xl text-leaf">я в деле!</span>
      </div>
      <p className="mt-4 max-w-[42ch] font-body text-foam/70">
        Заявка ни к чему не обязывает: менеджер свяжется, ответит на вопросы и
        подтвердит бронь. Мест немного.
      </p>

      {done ? (
        <div className="mt-8 rounded-2xl bg-leaf p-6 text-deep">
          <p className="font-display text-xl font-bold">Готово!</p>
          <p className="mt-2 font-body">Заявка принята. Скоро напишем вам в Telegram.</p>
        </div>
      ) : (
        <div className="mt-8 grid gap-7">
          <div className="grid gap-2">
            <label htmlFor="name" className={label}>
              Имя
            </label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Алекс"
              className={input}
            />
            {errors.name && <p className="font-mono text-xs text-leaf">{errors.name}</p>}
          </div>

          <div className="grid gap-2">
            <span className={label}>Как с вами связаться</span>
            <div className="flex flex-wrap gap-2">
              {CONTACT_METHODS.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => {
                    haptic("light");
                    setMethod(m.key);
                    setContact("");
                    setErrors((e) => ({ ...e, contact: undefined }));
                  }}
                  className={chip(method === m.key)}
                >
                  {m.emoji} {m.label}
                </button>
              ))}
            </div>
            {autoUsername ? (
              <p className="font-body text-sm text-foam/70">
                Напишем вам в Telegram: <span className="font-mono text-leaf">{autoUsername}</span>
              </p>
            ) : (
              <>
                <input
                  aria-label="Контакт"
                  type={method === "telegram" ? "text" : "tel"}
                  inputMode={method === "telegram" ? "text" : "tel"}
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  placeholder={CONTACT_METHODS.find((m) => m.key === method)!.placeholder}
                  className={input}
                />
                {errors.contact && (
                  <p className="font-mono text-xs text-leaf">{errors.contact}</p>
                )}
              </>
            )}
          </div>

          <div className="grid gap-2">
            <span className={label}>Билет</span>
            <div className="grid gap-2 sm:grid-cols-2">
              {TICKET_OPTIONS.map((o) => (
                <button
                  key={o.key}
                  type="button"
                  onClick={() => {
                    haptic("light");
                    setTariff(o.key);
                  }}
                  className={card(tariff === o.key)}
                >
                  <span className="block font-display text-base font-bold leading-tight">
                    {o.label}
                  </span>
                  <span className="block font-mono text-xs opacity-75">
                    {fmt(o.price)}
                    {o.tickets > 1 && ` · по ${fmt(o.price / o.tickets)} с человека`}
                  </span>
                </button>
              ))}
              <button
                type="button"
                onClick={() => {
                  haptic("light");
                  setTariff("custom");
                }}
                className={card(tariff === "custom")}
              >
                <span className="block font-display text-base font-bold leading-tight">
                  Своя компания
                </span>
                <span className="block font-mono text-xs opacity-75">
                  тариф подберём автоматически
                </span>
              </button>
            </div>
            {tariff === "custom" && (
              <div className="mt-2 flex items-center justify-between gap-4">
                <Stepper value={customCount} min={1} onChange={setCustomCount} suffix="чел" />
                <span className="font-mono text-sm text-leaf">{fmt(ticketPriceFor(customCount))}</span>
              </div>
            )}
          </div>

          <div className="grid gap-2">
            <span className={label}>Дети едут?</span>
            <div className="flex items-center justify-between gap-4">
              <Stepper value={children} min={0} onChange={setChildren} suffix={children === 1 ? "ребёнок" : "детей"} />
              <span className="font-mono text-xs text-foam/60">
                билет {fmt(CHILD_TICKET_PRICE)} — в 2 раза дешевле взрослого
              </span>
            </div>
          </div>

          {/* Сводка — как в подтверждении заявки у бота: билет заранее, вход на
              остров (трансфер, катамараны, волейбол, баня) — при выезде. */}
          <div className="rounded-2xl border border-foam/20 bg-deep/50 p-5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-body text-sm text-foam/70">Билет — оплата заранее</span>
              <span className="font-display text-xl font-bold text-leaf">{fmt(ticketCost)}</span>
            </div>
            <div className="mt-2 flex items-baseline justify-between gap-3">
              <span className="font-body text-sm text-foam/70">Вход на остров — при выезде</span>
              <span className="font-display text-lg font-bold">~{fmt(islandCost)}</span>
            </div>
            <p className="mt-3 font-mono text-xs leading-relaxed text-foam/60">
              Вход на остров: трансфер, парусные катамараны, волейбол, баня и другие активности
              ({fmt(ISLAND_ENTRY_PRICE)} × {tickets}
              {children > 0 && ` + ${fmt(CHILD_ISLAND_ENTRY_PRICE)} × ${children} 🧒`}).
              Проживание и аренда снаряжения — отдельно.
            </p>
          </div>

          {failed && (
            <p className="font-body text-sm text-leaf">
              Заявка не ушла — связь пропала. Попробуйте ещё раз или напишите
              боту в чат: он примет заявку без афиши.
            </p>
          )}

          <button
            type="button"
            onClick={submit}
            disabled={sending}
            className="mt-1 w-full rounded-full bg-foam px-8 py-4 font-display text-base font-bold text-deep transition active:scale-[0.98] disabled:opacity-60"
          >
            {sending ? "Отправляем…" : "Отправить заявку →"}
          </button>
        </div>
      )}
    </section>
  );
}
