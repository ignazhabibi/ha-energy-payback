// Periods and their slots for the history card, and the statistics rows
// summed per slot.

import type { StatisticsResult } from "./types";

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const MAX_SLOTS = 400;

/** A period from its first to its last millisecond. */
export interface Range {
  start: number;
  end: number;
}

export type Period = "hour" | "day" | "month" | "year";

/** The slot length for a period: hours for up to two days, days for up to
 * about three months, months up to three years, years beyond. */
export function periodOf({ start, end }: Range): Period {
  const span = end - start;
  if (span <= 2 * DAY + HOUR) return "hour";
  if (span <= 95 * DAY) return "day";
  if (span <= 3 * 366 * DAY) return "month";
  return "year";
}

/** The statistics period to request for a slot length. The recorder has no
 * years, so years are summed from months. */
export const statisticsPeriod = (period: Period): string =>
  period === "year" ? "month" : period;

const slotStart = (time: number, period: Period): number => {
  const date = new Date(time);
  if (period === "hour") return date.setMinutes(0, 0, 0);
  date.setHours(0, 0, 0, 0);
  if (period === "day") return date.getTime();
  date.setDate(1);
  if (period === "month") return date.getTime();
  return date.setMonth(0);
};

const nextSlot = (time: number, period: Period): number => {
  const date = new Date(time);
  if (period === "hour") date.setHours(date.getHours() + 1);
  else if (period === "day") date.setDate(date.getDate() + 1);
  else if (period === "month") date.setMonth(date.getMonth() + 1);
  else date.setFullYear(date.getFullYear() + 1);
  return date.getTime();
};

/** The starts of the slots that make up a period. */
export function slotsOf({ start, end }: Range, period: Period): number[] {
  const slots: number[] = [];
  for (
    let time = slotStart(start, period);
    time <= end && slots.length < MAX_SLOTS;
    time = nextSlot(time, period)
  ) {
    slots.push(time);
  }
  return slots;
}

/** Whole years from the first year that counts to the current one. */
export function yearsOf(firstDates: Array<Date | null>, now = new Date()): Range {
  const years = firstDates
    .filter((date): date is Date => date !== null)
    .map((date) => date.getFullYear());
  const first = Math.min(now.getFullYear(), ...years);
  return {
    start: new Date(first, 0, 1).getTime(),
    end: new Date(now.getFullYear() + 1, 0, 1).getTime() - 1,
  };
}

/** The change of one statistic summed per slot; null where it has no rows. */
export function valuesPerSlot(
  rows: StatisticsResult[string],
  slots: number[],
  period: Period
): Array<number | null> {
  const values: Array<number | null> = slots.map(() => null);
  // Days and longer begin at midnight of the server's time zone, which may
  // be a few hours off the browser's.
  const tolerance = period === "hour" ? 0 : 12 * HOUR;
  for (const row of rows ?? []) {
    if (row.change === null || row.change === undefined) continue;
    const at =
      (typeof row.start === "number" ? row.start : Date.parse(row.start)) +
      tolerance;
    let index = -1;
    for (let i = 0; i < slots.length && slots[i] <= at; i += 1) index = i;
    if (index < 0) continue;
    values[index] = (values[index] ?? 0) + row.change;
  }
  return values;
}
