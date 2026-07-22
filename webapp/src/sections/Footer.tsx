import { event } from "../data/event";

export function Footer({ onApply }: { onApply: () => void }) {
  return (
    <footer className="border-t border-foam/10 px-5 pb-28 pt-12">
      <p className="font-display text-4xl font-bold leading-none">The Ostrov</p>
      <p className="mt-1 font-script text-2xl text-leaf">open air</p>

      <div className="mt-6 grid gap-1 font-mono text-[11px] uppercase tracking-[0.18em] text-foam/60">
        <span>{event.dateRange}</span>
        <span>ПК «Остров» / {event.area}</span>
      </div>

      <button
        onClick={onApply}
        className="mt-7 w-full rounded-full bg-foam px-8 py-3.5 font-display font-bold text-deep transition active:scale-[0.98] sm:w-fit"
      >
        Оставить заявку →
      </button>
    </footer>
  );
}
