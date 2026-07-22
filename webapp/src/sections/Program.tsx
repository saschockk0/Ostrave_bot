import { Reveal } from "../components/Reveal";
import { event } from "../data/event";

export function Program() {
  return (
    <section className="px-5 py-14">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="font-display text-3xl font-bold leading-tight">План на три дня</h2>
        <span className="font-script text-2xl text-leaf">от заезда до последнего трека</span>
      </div>

      <div className="mt-8 grid gap-4">
        {event.days.map((d, i) => (
          <Reveal key={d.date} delay={i * 0.06}>
            <article className="rounded-2xl border border-foam/15 bg-foam/[0.04] p-5">
              <span className="inline-block rounded-full bg-foam/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-foam/80">
                {d.date} · {d.weekday}
              </span>
              <h3 className="mt-3 font-display text-xl font-bold leading-tight">{d.title}</h3>
              <ul className="mt-3 grid gap-2">
                {d.items.map((item) => (
                  <li key={item} className="font-body text-foam/80">
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
