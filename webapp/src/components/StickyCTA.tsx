import { useEffect, useState } from "react";
import type { RefObject } from "react";

type StickyCTAProps = {
  targetRef: RefObject<HTMLElement>;
  onClick: () => void;
};

export function StickyCTA({ targetRef, onClick }: StickyCTAProps) {
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const el = targetRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => setHidden(entry.isIntersecting),
      { threshold: 0.12 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [targetRef]);

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-50 mx-auto max-w-[560px] px-3 pt-3 transition-transform duration-300 ${
        hidden ? "translate-y-[140%]" : "translate-y-0"
      }`}
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <button
        onClick={onClick}
        className="w-full border-[3px] border-ink bg-orange px-6 py-3.5 font-display text-base font-extrabold uppercase tracking-tight text-ink shadow-[5px_5px_0_#0e0e0e] transition active:translate-y-[2px] active:shadow-[2px_2px_0_#0e0e0e]"
      >
        Оставить заявку
      </button>
    </div>
  );
}
