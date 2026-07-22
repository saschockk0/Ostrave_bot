import { Reveal } from "../components/Reveal";
import { event } from "../data/event";
import { useTelegram } from "../hooks/useTelegram";

// Частые вопросы — те же ответы, что в FAQ бота (models.FAQ_ITEMS),
// в сокращённом виде. Нативный <details> — без лишнего state.
export function Faq() {
  const { haptic } = useTelegram();
  return (
    <section className="border-t border-foam/10 bg-pine px-5 py-14">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="font-display text-3xl font-bold leading-tight">Вопросы</h2>
        <span className="font-script text-2xl text-leaf">и ответы</span>
      </div>

      <div className="mt-8 grid gap-3">
        {event.faq.map((item, i) => (
          <Reveal key={item.q} delay={i * 0.05}>
            <details
              className="group rounded-2xl border border-foam/15 bg-foam/[0.04]"
              onToggle={() => haptic("light")}
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 font-display text-base font-bold [&::-webkit-details-marker]:hidden">
                {item.q}
                <span className="font-mono text-xl text-foam/60 transition group-open:rotate-45">
                  +
                </span>
              </summary>
              <div className="grid gap-3 border-t border-foam/10 px-5 py-4">
                {item.a.map((p) => (
                  <p key={p} className="font-body text-foam/75">
                    {p}
                  </p>
                ))}
              </div>
            </details>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
