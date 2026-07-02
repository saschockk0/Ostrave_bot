import { Reveal } from "../components/Reveal";
import { event } from "../data/event";

const rotations = ["-2deg", "1.4deg", "-1deg", "1.8deg", "-1.6deg", "1deg"];

export function Program() {
  return (
    <section className="px-4 py-14">
      <div className="flex flex-wrap items-end gap-3">
        <h2 className="font-display text-4xl font-black uppercase leading-none">Что будет</h2>
        <span className="rotate-[-3deg] font-marker text-2xl text-orange-deep">программа</span>
      </div>

      <div className="mt-9 grid gap-5 sm:grid-cols-2">
        {event.program.map((p, i) => (
          <Reveal key={p.title} delay={(i % 2) * 0.06}>
            <article
              className="h-full border-[3px] border-ink bg-paper p-5 shadow-[6px_6px_0_#0e0e0e]"
              style={{ transform: `rotate(${rotations[i % rotations.length]})` }}
            >
              <span className="inline-block border-[2px] border-ink px-2 py-0.5 font-mono text-[11px] uppercase tracking-widest">
                {p.tag}
              </span>
              <h3 className="mt-3 font-display text-2xl font-extrabold leading-tight">
                {p.title}
              </h3>
              <p className="mt-2 max-w-[34ch] font-body text-ink/70">{p.text}</p>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
