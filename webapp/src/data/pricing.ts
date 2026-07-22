// Цены — зеркало бота (models.py и pricing.py в корне репо).
// Источник правды — бот: сумму заявки он считает сам, здесь только превью
// в форме. Поменяли цены в боте — поменяйте и тут.

export type TicketOption = {
  key: "single" | "duo" | "quad";
  label: string;
  tickets: number; // сколько человек проходит по билету
  price: number; // ₽ за билет
};

export const TICKET_OPTIONS: TicketOption[] = [
  { key: "single", label: "Одиночный", tickets: 1, price: 2100 },
  { key: "duo", label: "На двоих", tickets: 2, price: 3600 },
  { key: "quad", label: "На четверых", tickets: 4, price: 6000 },
];

// Детский билет — половина взрослого одиночного (models.CHILD_TICKET_PRICE).
export const CHILD_TICKET_PRICE = TICKET_OPTIONS[0].price / 2;

// Вход на остров — оплата на месте при выезде (pricing.ISLAND_ENTRY_PRICE).
// Покрывает трансфер на остров и обратно, парусные катамараны, волейбол и баню.
export const ISLAND_ENTRY_PRICE = 4700;
export const CHILD_ISLAND_ENTRY_PRICE = ISLAND_ENTRY_PRICE / 2;

export const MAX_TICKETS = 50;

const byKey = Object.fromEntries(TICKET_OPTIONS.map((o) => [o.key, o]));

/** Авто-расчёт билета за `count` человек — как models.ticket_price_for.
 *
 * Жадно от крупного к мелкому: четвёрки → пары → одиночные. Оптимально,
 * т.к. цена за человека убывает с размером тарифа (1500 < 1800 < 2100).
 */
export function ticketPriceFor(count: number): number {
  const n = Math.max(1, Math.min(Math.trunc(count) || 1, MAX_TICKETS));
  const quads = Math.floor(n / byKey.quad.tickets);
  const rest = n % byKey.quad.tickets;
  const duos = Math.floor(rest / byKey.duo.tickets);
  const singles = rest % byKey.duo.tickets;
  return quads * byKey.quad.price + duos * byKey.duo.price + singles * byKey.single.price;
}

export const fmt = (n: number) => `${n.toLocaleString("ru-RU")} ₽`;
