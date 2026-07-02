import { motion, useReducedMotion } from "motion/react";
import { Marquee } from "../components/Marquee";
import { event } from "../data/event";

export function Hero({ onApply }: { onApply: () => void }) {
  const reduce = useReducedMotion();
  const enter = (delay: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 22 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] as const },
        };

  return (
    <header className="relative flex min-h-[100dvh] flex-col">
      <div className="flex items-center justify-between border-b-[3px] border-ink px-4 py-3 font-mono text-[11px] uppercase tracking-[0.2em]">
        <span>The Ostrov</span>
        <span>Open air</span>
      </div>

      <div className="relative flex flex-1 flex-col justify-center px-4 py-8">
        <div
          className="halftone pointer-events-none absolute right-2 top-6 h-32 w-32 text-orange/30"
          aria-hidden="true"
        />

        <motion.p {...enter(0)} className="rotate-[-3deg] font-marker text-2xl text-ink/80">
          the
        </motion.p>

        <motion.h1
          {...enter(0.08)}
          className="font-display font-black uppercase leading-[0.84] tracking-tight text-orange"
          style={{ fontSize: "clamp(3.4rem, 21vw, 8.5rem)" }}
        >
          Ostrov
        </motion.h1>

        <motion.p {...enter(0.18)} className="mt-1 rotate-[-2deg] font-marker text-3xl">
          open air
        </motion.p>

        <motion.div {...enter(0.28)} className="mt-7 flex flex-wrap gap-3">
          <span className="border-[3px] border-ink bg-ink px-3 py-1 font-mono text-sm uppercase text-paper">
            {event.dateRange}
          </span>
          <span className="border-[3px] border-ink px-3 py-1 font-mono text-sm uppercase">
            {event.venue}
          </span>
        </motion.div>

        <motion.button
          {...enter(0.38)}
          onClick={onApply}
          className="mt-8 w-fit border-[3px] border-ink bg-orange px-6 py-3 font-display text-lg font-extrabold uppercase tracking-tight shadow-[6px_6px_0_#0e0e0e] transition active:translate-x-[3px] active:translate-y-[3px] active:shadow-none"
        >
          Оставить заявку →
        </motion.button>
      </div>

      <Marquee
        items={event.marquee}
        className="border-y-[3px] border-ink bg-orange py-2 font-display text-xl font-extrabold uppercase text-ink"
      />
    </header>
  );
}
