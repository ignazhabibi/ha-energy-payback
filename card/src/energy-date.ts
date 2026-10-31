// Follows the period of Home Assistant's energy date selection card, as HA's
// own energy cards do: that card keeps an energy data collection on the
// websocket connection, and its subscribers get the selected start and end.

import type { Range } from "./history";

interface EnergyData {
  start: Date;
  end?: Date;
}

interface Collection {
  subscribe(callback: (data: EnergyData) => void): () => void;
}

const WAIT_MS = 500;
const WAIT_TRIES = 20;
/** Tries before the card assumes there is no date selection. It keeps
 * looking afterwards, since the date card may build its collection later. */
const ASSUME_NONE_AFTER = 2;

const isCollection = (value: unknown): value is Collection =>
  !!value && typeof (value as Collection).subscribe === "function";

/** The date selection's collection: the one of this dashboard (HA keys it by
 * the dashboard path), else the plain one. */
function findCollection(connection: object): Collection | undefined {
  const path = location.pathname.split("/")[1] ?? "";
  const keys = connection as Record<string, unknown>;
  for (const key of [`_energy_${path}`, "_energy"]) {
    if (isCollection(keys[key])) return keys[key];
  }
  return undefined;
}

/** The end of today, for a selection that is still open. */
const endOfToday = (): number => new Date().setHours(24, 0, 0, 0) - 1;

/** Calls back with the selected period, or with null while the dashboard has
 * no date selection. Returns a function that stops following. */
export function followEnergyDate(
  connection: object,
  callback: (range: Range | null) => void
): () => void {
  let unsubscribe: (() => void) | undefined;
  let timer: number | undefined;
  let tries = 0;
  const attach = () => {
    const collection = findCollection(connection);
    if (collection) {
      unsubscribe = collection.subscribe((data) =>
        callback({
          start: new Date(data.start).getTime(),
          end: data.end ? new Date(data.end).getTime() : endOfToday(),
        })
      );
      return;
    }
    tries += 1;
    if (tries === ASSUME_NONE_AFTER) callback(null);
    if (tries < WAIT_TRIES) timer = window.setTimeout(attach, WAIT_MS);
  };
  attach();
  return () => {
    window.clearTimeout(timer);
    unsubscribe?.();
  };
}
