import { useState } from "react";
import type { RefObject } from "react";
import { useTelegram } from "../hooks/useTelegram";

const PHONE_RE = /^\+?\d[\d\s\-()]{7,}$/;
const TICKET_CHIPS = [1, 2, 3, 4, 5];

export function Apply({ sectionRef }: { sectionRef: RefObject<HTMLElement> }) {
  const { tg, haptic, user } = useTelegram();

  const [name, setName] = useState(user?.first_name ?? "");
  const [phone, setPhone] = useState("");
  const [tickets, setTickets] = useState(1);
  const [errors, setErrors] = useState<{ name?: string; phone?: string }>({});
  const [done, setDone] = useState(false);

  const submit = () => {
    const next: { name?: string; phone?: string } = {};
    if (name.trim().length < 2) next.name = "Как вас зовут?";
    if (!PHONE_RE.test(phone.trim())) next.phone = "Похоже, номер неполный";
    setErrors(next);
    if (Object.keys(next).length > 0) {
      haptic("heavy");
      return;
    }

    const payload = {
      type: "party_application",
      name: name.trim(),
      phone: phone.trim(),
      tickets,
      username: user?.username ?? null,
      tg_id: user?.id ?? null,
    };

    haptic("medium");
    if (tg?.sendData) {
      // Отправляет данные боту и закрывает Mini App
      // (работает, когда приложение открыто кнопкой web_app в боте).
      tg.sendData(JSON.stringify(payload));
    } else {
      // Локальная разработка / запуск вне Telegram.
      console.log("Заявка:", payload);
      setDone(true);
    }
  };

  return (
    <section ref={sectionRef} id="apply" className="bg-ink px-4 py-16 text-paper">
      <div className="flex flex-wrap items-end gap-3">
        <h2 className="font-display text-4xl font-black uppercase leading-none">Заявка</h2>
        <span className="rotate-[-3deg] font-marker text-2xl text-orange">я в деле</span>
      </div>
      <p className="mt-4 max-w-[42ch] font-body text-paper/70">
        Оставьте контакты и число билетов. Заявка ни к чему не обязывает, мы свяжемся и
        расскажем детали. Мест немного.
      </p>

      {done ? (
        <div className="mt-8 border-[3px] border-orange bg-orange p-6 text-ink">
          <p className="font-display text-2xl font-extrabold uppercase">Готово!</p>
          <p className="mt-2 font-body">Заявка принята. Скоро напишем вам в Telegram.</p>
        </div>
      ) : (
        <div className="mt-8 grid gap-6">
          <div className="grid gap-2">
            <label htmlFor="name" className="font-mono text-xs uppercase tracking-[0.2em] text-paper/70">
              Имя
            </label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Алекс"
              className="border-[3px] border-ink bg-paper px-4 py-3 font-body text-ink outline-none placeholder:text-ink/35 focus:border-orange"
            />
            {errors.name && <p className="font-mono text-xs text-orange">{errors.name}</p>}
          </div>

          <div className="grid gap-2">
            <label htmlFor="phone" className="font-mono text-xs uppercase tracking-[0.2em] text-paper/70">
              Телефон
            </label>
            <input
              id="phone"
              type="tel"
              inputMode="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+7 999 123-45-67"
              className="border-[3px] border-ink bg-paper px-4 py-3 font-body text-ink outline-none placeholder:text-ink/35 focus:border-orange"
            />
            {errors.phone && <p className="font-mono text-xs text-orange">{errors.phone}</p>}
          </div>

          <div className="grid gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-paper/70">
              Сколько билетов
            </span>
            <div className="flex flex-wrap gap-2">
              {TICKET_CHIPS.map((n) => {
                const active = tickets === n;
                return (
                  <button
                    key={n}
                    type="button"
                    onClick={() => {
                      haptic("light");
                      setTickets(n);
                    }}
                    className={`h-12 w-12 border-[3px] font-display text-lg font-extrabold transition ${
                      active
                        ? "border-ink bg-orange text-ink"
                        : "border-paper/40 text-paper active:bg-paper/10"
                    }`}
                  >
                    {n}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => {
                  haptic("light");
                  setTickets((t) => (t >= 6 ? t + 1 : 6));
                }}
                className={`h-12 px-4 border-[3px] font-display text-lg font-extrabold transition ${
                  tickets >= 6
                    ? "border-ink bg-orange text-ink"
                    : "border-paper/40 text-paper active:bg-paper/10"
                }`}
              >
                {tickets >= 6 ? tickets : "6+"}
              </button>
            </div>
          </div>

          <button
            type="button"
            onClick={submit}
            className="mt-2 border-[3px] border-orange bg-orange px-6 py-4 font-display text-lg font-extrabold uppercase tracking-tight text-ink shadow-[6px_6px_0_#fbf7ee] transition active:translate-x-[3px] active:translate-y-[3px] active:shadow-none"
          >
            Отправить заявку →
          </button>
        </div>
      )}
    </section>
  );
}
