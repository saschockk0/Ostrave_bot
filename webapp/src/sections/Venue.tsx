import { Marquee } from "../components/Marquee";
import { event } from "../data/event";
import { useTelegram } from "../hooks/useTelegram";

export function Venue() {
  const { tg, haptic } = useTelegram();

  const openMap = () => {
    haptic("light");
    if (tg?.openLink) tg.openLink(event.mapUrl);
    else window.open(event.mapUrl, "_blank", "noopener");
  };

  return (
    <section className="border-t-[3px] border-ink bg-ink text-paper">
      <Marquee
        reverse
        items={["как добраться", "парусный клуб «остров»", "берег, лес и причал"]}
        className="border-b-[3px] border-paper/25 py-2 font-marker text-2xl text-orange"
      />

      <div className="grid gap-8 px-4 py-14 md:grid-cols-2">
        <div>
          <h2 className="font-display text-4xl font-black uppercase leading-[0.9]">
            Где
            <br />
            встречаемся
          </h2>
          <p className="mt-4 max-w-[42ch] font-body text-paper/70">
            Парусный клуб «Остров» на берегу: лес, вода и причал. Точное время сбора и
            дорогу пришлём в личку после заявки.
          </p>
        </div>

        <div className="border-[3px] border-orange p-6">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-orange">Локация</p>
          <p className="mt-2 font-display text-2xl font-extrabold">{event.venue}</p>
          <button
            onClick={openMap}
            className="mt-6 w-full border-[3px] border-orange bg-orange px-5 py-3 font-display font-extrabold uppercase tracking-tight text-ink shadow-[5px_5px_0_#fbf7ee] transition active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
          >
            Построить маршрут →
          </button>
        </div>
      </div>
    </section>
  );
}
