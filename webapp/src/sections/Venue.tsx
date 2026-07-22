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
    <section className="px-5 py-14">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="font-display text-3xl font-bold leading-tight">Где встречаемся</h2>
        <span className="font-script text-2xl text-leaf">как добраться</span>
      </div>

      <p className="mt-4 max-w-[42ch] font-body text-foam/70">
        Точка сбора — причал «Новомелково», местные таксисты знают его как
        «причал МИФИ». {event.transfer} — и ты в маленьком раю 🏝
      </p>

      <div className="mt-6 grid gap-4">
        <div className="border-l-2 border-leaf pl-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-leaf">
            🚗 На машине
          </p>
          <p className="mt-1 font-body text-sm text-foam/70">
            Кидаешь координаты в навигатор — и маршрут до причала готов. {event.parking}.
          </p>
        </div>
        <div className="border-l-2 border-leaf pl-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-leaf">
            🚆 Без машины
          </p>
          <p className="mt-1 font-body text-sm text-foam/70">
            С Ленинградского вокзала — до станции Редкино, дальше такси до причала.{" "}
            {event.taxi.name}: <span className="font-mono">{event.taxi.phone}</span>. В пик
            ждать можно до часа — заказывай заранее!
          </p>
        </div>
      </div>

      <div className="mt-8 rounded-2xl border border-foam/15 bg-foam/[0.04] p-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-foam/60">
          📍 Точка сбора
        </p>
        <p className="mt-2 font-display text-xl font-bold">{event.pier}</p>
        <p className="mt-1 font-mono text-sm text-foam/60">{event.coords}</p>
        <button
          onClick={openMap}
          className="mt-6 w-full rounded-full bg-foam px-6 py-3.5 font-display font-bold text-deep transition active:scale-[0.98]"
        >
          Построить маршрут →
        </button>
      </div>
    </section>
  );
}
