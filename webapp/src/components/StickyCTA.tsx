import { useEffect, useState } from "react";
import type { RefObject } from "react";

type StickyCTAProps = {
  targetRef: RefObject<HTMLElement>; // секция заявки — рядом с ней кнопка не нужна
  heroRef: RefObject<HTMLElement>; // герой с собственным CTA — не дублируем
  onClick: () => void;
};

export function StickyCTA({ targetRef, heroRef, onClick }: StickyCTAProps) {
  const [applyVisible, setApplyVisible] = useState(false);
  const [heroVisible, setHeroVisible] = useState(true);

  useEffect(() => {
    const observers = [
      [targetRef, setApplyVisible] as const,
      [heroRef, setHeroVisible] as const,
    ].map(([ref, set]) => {
      const el = ref.current;
      if (!el) return null;
      const io = new IntersectionObserver(([entry]) => set(entry.isIntersecting), {
        threshold: 0.12,
      });
      io.observe(el);
      return io;
    });
    return () => observers.forEach((io) => io?.disconnect());
  }, [targetRef, heroRef]);

  const hidden = applyVisible || heroVisible;
  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-50 mx-auto max-w-[560px] px-3 pt-3 transition-transform duration-300 ${
        hidden ? "translate-y-[140%]" : "translate-y-0"
      }`}
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <button
        onClick={onClick}
        className="w-full rounded-full bg-foam px-6 py-3.5 font-display text-base font-bold text-deep shadow-[0_8px_24px_rgba(0,0,0,0.45)] transition active:scale-[0.98]"
      >
        Оставить заявку
      </button>
    </div>
  );
}
