import { Reveal } from "../components/Reveal";
import {
  CHILD_ISLAND_ENTRY_PRICE,
  CHILD_TICKET_PRICE,
  ISLAND_ENTRY_PRICE,
  TICKET_OPTIONS,
  fmt,
} from "../data/pricing";

// Цена из двух частей — как в FAQ бота «Сколько стоит?»: билет на open air
// (оплата заранее) и вход на остров (на месте, при выезде).
export function Prices() {
  return (
    <section className="border-y border-foam/10 bg-pine px-5 py-14">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="font-display text-3xl font-bold leading-tight">Сколько стоит</h2>
        <span className="font-script text-2xl text-leaf">две части</span>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <Reveal>
          <article className="h-full rounded-2xl border border-foam/15 bg-foam/[0.04] p-5">
            <span className="inline-block rounded-full border border-foam/25 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-foam/80">
              1 · заранее
            </span>
            <h3 className="mt-3 font-display text-xl font-bold leading-tight">
              🎟 Билет на open air
            </h3>
            <ul className="mt-4 grid gap-2 font-body">
              {TICKET_OPTIONS.map((o) => (
                <li key={o.key} className="flex items-baseline justify-between gap-3">
                  <span className="text-foam/85">{o.label}</span>
                  <span className="font-display font-bold text-leaf">
                    {fmt(o.price)}
                    {o.tickets > 1 && (
                      <span className="ml-1 font-mono text-xs font-normal text-foam/60">
                        по {fmt(o.price / o.tickets)}
                      </span>
                    )}
                  </span>
                </li>
              ))}
              <li className="flex items-baseline justify-between gap-3">
                <span className="text-foam/85">Детский 🧒</span>
                <span className="font-display font-bold text-leaf">{fmt(CHILD_TICKET_PRICE)}</span>
              </li>
            </ul>
            <p className="mt-4 font-body text-sm text-foam/60">
              Сама тусовка: приятная музыка, ночные сеты и уютная атмосфера летней ночи 🌙
            </p>
          </article>
        </Reveal>

        <Reveal delay={0.06}>
          <article className="h-full rounded-2xl border border-foam/15 bg-foam/[0.04] p-5">
            <span className="inline-block rounded-full border border-foam/25 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-foam/80">
              2 · при выезде
            </span>
            <h3 className="mt-3 font-display text-xl font-bold leading-tight">
              🏝 Вход на остров
            </h3>
            <ul className="mt-4 grid gap-2 font-body">
              <li className="flex items-baseline justify-between gap-3">
                <span className="text-foam/85">Взрослый</span>
                <span className="font-display font-bold text-leaf">{fmt(ISLAND_ENTRY_PRICE)}</span>
              </li>
              <li className="flex items-baseline justify-between gap-3">
                <span className="text-foam/85">Детский 🧒</span>
                <span className="font-display font-bold text-leaf">
                  {fmt(CHILD_ISLAND_ENTRY_PRICE)}
                </span>
              </li>
            </ul>
            <p className="mt-4 font-body text-sm text-foam/60">
              Сюда входит: 🛥 трансфер на остров и обратно, ⛵ покатушки на парусных катамаранах,
              🏐 волейбол, 🧖 баня — детокс и полный расслабон, и другие активности на острове.
              Оплата на месте, при выезде — скрытых доплат нет.
            </p>
          </article>
        </Reveal>
      </div>

      <p className="mt-6 max-w-[52ch] font-body text-sm text-foam/70">
        Проживание (палатки и кухни-шатры) и аренда снаряжения — отдельно. Своё привезёшь —
        сэкономишь, или арендуешь на острове. Прикинуть всё под свою компанию можно в
        «🧮 Калькуляторе» у бота.
      </p>
    </section>
  );
}
