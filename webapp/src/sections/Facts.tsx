import { event } from "../data/event";

const facts = [
  { q: "Когда?", a: event.dateRange, sub: event.year },
  { q: "Где?", a: "Парусный клуб", sub: "«Остров»" },
  { q: "Зачем?", a: "Единение", sub: "с природой" },
];

export function Facts() {
  return (
    <section className="border-b-[3px] border-ink bg-orange text-ink">
      <div className="grid grid-cols-1 divide-y-[3px] divide-ink sm:grid-cols-3 sm:divide-x-[3px] sm:divide-y-0">
        {facts.map((f) => (
          <div key={f.q} className="px-5 py-9">
            <p className="font-mono text-xs uppercase tracking-[0.2em]">{f.q}</p>
            <p className="mt-3 font-display text-3xl font-black leading-none">{f.a}</p>
            <p className="font-display text-xl font-bold">{f.sub}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
