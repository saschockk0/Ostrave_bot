import { event } from "../data/event";

const facts = [
  { q: "Когда?", a: event.dateRange, sub: event.year },
  { q: "Где?", a: "ПК «Остров»", sub: event.area },
  { q: "Зачем?", a: "Единение", sub: "с природой" },
];

export function Facts() {
  return (
    <section className="border-y border-foam/10 bg-pine">
      <div className="grid grid-cols-1 divide-y divide-foam/10 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {facts.map((f) => (
          <div key={f.q} className="px-5 py-8">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-foam/60">{f.q}</p>
            <p className="mt-3 font-display text-2xl font-bold leading-tight">{f.a}</p>
            <p className="font-display text-base text-foam/70">{f.sub}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
