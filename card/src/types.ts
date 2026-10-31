// The parts of Home Assistant's frontend objects the card uses.

export interface HassEntityState {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface HassEntityRegistryEntry {
  entity_id: string;
  device_id?: string | null;
  platform: string;
  translation_key?: string | null;
}

export interface HomeAssistant {
  states: Record<string, HassEntityState>;
  entities: Record<string, HassEntityRegistryEntry>;
  locale: { language: string };
  language?: string;
  config: { currency: string };
  /** The websocket connection; the energy date selection keeps its period here. */
  connection?: object;
  callWS<T>(message: Record<string, unknown>): Promise<T>;
}

/** Rows of `recorder/statistics_during_period`, by statistic id. */
export type StatisticsResult = Record<
  string,
  Array<{ start: number | string; change?: number | null }> | undefined
>;

export type Category = "pv" | "heat_pump" | "wallbox";

export interface CategoryFigures {
  category: Category;
  savingEntity: string;
  calculating: boolean;
  saving: number | null;
  investment: number | null;
  payback: number | null;
  perYear: number | null;
  countingSince: Date | null;
  yearlyFrom: Date | null;
  /** The gas, oil, or fuel price in effect now. */
  price: number | null;
  heating: "gas" | "oil" | null;
  heatEstimated: boolean;
}
