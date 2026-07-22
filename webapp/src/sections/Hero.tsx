import { motion, useReducedMotion } from "motion/react";
import type { RefObject } from "react";
import { event } from "../data/event";
import afisha from "../assets/afisha.jpg";

export function Hero({
  sectionRef,
  onApply,
}: {
  sectionRef: RefObject<HTMLElement>;
  onApply: () => void;
}) {
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
    <header ref={sectionRef} className="relative">
      {/* Верхние ~75% афиши как арт: фирменный леттеринг THE OSTROV и слова
          «природа · друзья · кэмпинг · музыка» уже в изображении. Нижняя часть
          (программа, дата) обрезается и дублируется ниже живой типографикой —
          читаемой и доступной. Квадратная рамка = верхние 3/4 постера 3:4. */}
      <div className="relative aspect-square overflow-hidden">
        <img
          src={afisha}
          alt="Афиша THE OSTROV open air: сосновый лес и Волга с высоты птичьего полёта"
          className="h-full w-full object-cover object-top"
        />
        {/* Плавный переход воды в фоновый цвет */}
        <div
          className="absolute inset-x-0 bottom-0 h-2/5 bg-gradient-to-b from-deep/0 to-deep"
          aria-hidden="true"
        />
        <div className="absolute inset-x-0 top-0 flex items-center justify-between px-5 py-3 font-mono text-[11px] uppercase tracking-[0.2em] text-foam/80">
          <span>The Ostrov</span>
          <span>Open air</span>
        </div>
      </div>

      {/* Живой низ афиши */}
      <div className="relative -mt-8 px-5 pb-10">
        <motion.p
          {...enter(0.1)}
          className="text-center font-script text-3xl text-foam"
        >
          что в программе?
        </motion.p>

        <motion.div {...enter(0.18)} className="mt-4 flex justify-center gap-4">
          <div className="max-w-[20ch] text-right font-mono text-xs uppercase leading-relaxed tracking-wider text-foam">
            <p className="text-foam/60">день:</p>
            {event.programDay.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
          <div className="w-px bg-foam/40" aria-hidden="true" />
          <div className="max-w-[22ch] font-mono text-xs uppercase leading-relaxed tracking-wider text-foam">
            <p className="text-foam/60">ночь:</p>
            {event.programNight.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
        </motion.div>

        <motion.p
          {...enter(0.26)}
          className="mt-9 text-center font-display text-5xl font-bold tracking-tight text-foam"
        >
          {event.dateShort}
        </motion.p>
        <motion.p
          {...enter(0.3)}
          className="mt-2 text-center font-mono text-[11px] uppercase tracking-[0.2em] text-foam/70"
        >
          📍 ПК «Остров» / {event.area}
        </motion.p>

        <motion.button
          {...enter(0.38)}
          onClick={onApply}
          className="mt-8 w-full rounded-full bg-foam px-8 py-4 font-display text-base font-bold text-deep transition active:scale-[0.98]"
        >
          Оставить заявку →
        </motion.button>
      </div>
    </header>
  );
}
