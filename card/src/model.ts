// Reads the integration's sensors and derives what the card shows.

import type { Category, CategoryFigures, HomeAssistant } from "./types";

export const DOMAIN = "energy_payback";
const ORDER: Category[] = ["pv", "heat_pump", "wallbox"];
const MONTH_MS = (365.25 / 12) * 24 * 3600 * 1000;

const number = (value: unknown): number | null => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const date = (value: unknown): Date | null =>
  typeof value === "string" && value ? new Date(value) : null;

/** Returns the figures of every category, found without any card options. */
export function readCategories(hass: HomeAssistant): CategoryFigures[] {
  const entries = Object.values(hass.entities ?? {}).filter(
    (entry) => entry.platform === DOMAIN
  );
  const siblings = (deviceId: string | null | undefined, key: string) =>
    entries.find(
      (entry) => entry.device_id === deviceId && entry.translation_key === key
    );
  const value = (entityId: string | undefined) =>
    entityId ? number(hass.states[entityId]?.state) : null;

  const figures: CategoryFigures[] = [];
  for (const entry of entries) {
    if (entry.translation_key !== "saving") continue;
    const state = hass.states[entry.entity_id];
    if (!state || state.state === "unavailable") continue;
    const attributes = state.attributes;
    const category = attributes.category as Category;
    if (!ORDER.includes(category)) continue;
    figures.push({
      category,
      savingEntity: entry.entity_id,
      calculating: attributes.calculating === true,
      saving: number(state.state),
      investment: number(attributes.investment),
      payback: value(siblings(entry.device_id, "payback")?.entity_id),
      perYear: value(siblings(entry.device_id, "saving_per_year")?.entity_id),
      countingSince: date(attributes.counting_since),
      yearlyFrom: date(attributes.yearly_from),
      price: number(attributes.price),
      heating:
        attributes.heating === "gas" || attributes.heating === "oil"
          ? attributes.heating
          : null,
      heatEstimated: attributes.heat_estimated === true,
    });
  }
  return figures.sort(
    (a, b) => ORDER.indexOf(a.category) - ORDER.indexOf(b.category)
  );
}

export interface Totals {
  saved: number;
  invested: number;
  /** Savings minus investments; null while it is being computed. */
  balance: number | null;
  perYear: number | null;
  /** When the household is roughly in the plus; null if unknown. */
  inThePlusFrom: Date | null;
  calculating: boolean;
}

export function totals(categories: CategoryFigures[], now = new Date()): Totals {
  const calculating = categories.some((category) => category.calculating);
  const saved = categories.reduce((sum, c) => sum + (c.saving ?? 0), 0);
  const invested = categories.reduce((sum, c) => sum + (c.investment ?? 0), 0);
  const ready = !calculating && categories.length > 0;
  const balance = ready ? saved - invested : null;
  const yearly = categories.every((category) => category.perYear !== null);
  const perYear =
    ready && yearly
      ? categories.reduce((sum, c) => sum + (c.perYear ?? 0), 0)
      : null;
  let inThePlusFrom: Date | null = null;
  if (balance !== null && perYear !== null) {
    if (balance >= 0) inThePlusFrom = now;
    else if (perYear > 0)
      inThePlusFrom = new Date(
        now.getTime() + (-balance / perYear) * 12 * MONTH_MS
      );
  }
  return {
    saved,
    invested,
    balance,
    perYear,
    inThePlusFrom,
    calculating,
  };
}

/** Years until a category has paid for itself, or null if it cannot be said. */
export function yearsToPayback(category: CategoryFigures): number | null {
  const { investment, saving, perYear } = category;
  if (investment === null || investment <= 0) return null;
  if (saving === null || perYear === null || perYear <= 0) return null;
  return Math.max(0, (investment - saving) / perYear);
}

/** Yearly return on the investment once paid off, in percent. */
export function annualReturn(category: CategoryFigures): number | null {
  const { investment, saving, perYear } = category;
  if (investment === null || investment <= 0) return null;
  if (saving === null || perYear === null || saving < investment) return null;
  return (perYear / investment) * 100;
}
