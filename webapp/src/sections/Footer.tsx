import { event } from "../data/event";

export function Footer({ onApply }: { onApply: () => void }) {
  return (
    <footer className="border-t-[3px] border-paper/20 bg-ink px-4 pb-28 pt-12 text-paper">
      <p className="font-display text-5xl font-black uppercase leading-none text-orange">
        Ostrov
      </p>
      <p className="-mt-1 rotate-[-2deg] font-marker text-2xl">open air</p>

      <div className="mt-6 grid gap-1 font-mono text-xs uppercase tracking-[0.18em] text-paper/70">
        <span>{event.dateRange}</span>
        <span>{event.venue}</span>
      </div>

      <button
        onClick={onApply}
        className="mt-7 w-full border-[3px] border-orange bg-orange px-6 py-3.5 font-display font-extrabold uppercase tracking-tight text-ink transition active:translate-y-[2px] sm:w-fit"
      >
        Оставить заявку →
      </button>
    </footer>
  );
}
