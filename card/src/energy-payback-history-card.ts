// History card of the Energy Payback integration: what each category saved
// per hour, day, month, or year, from the long-term statistics of its saving
// sensor, which include the computed past. It follows the energy date
// selection card on the same dashboard, and without one shows a bar per
// year. Like the balance card it needs no options.

import {
  LitElement,
  css,
  html,
  nothing,
  unsafeCSS,
  type PropertyValues,
  type TemplateResult,
} from "lit";

import { chartReady, savingsChart } from "./chart";
import { followEnergyDate } from "./energy-date";
import {
  periodOf,
  slotsOf,
  statisticsPeriod,
  valuesPerSlot,
  yearsOf,
  type Period,
  type Range,
} from "./history";
import { localizer, type Localize } from "./localize";
import { readCategories } from "./model";
import { cardStyles } from "./styles";
import type {
  Category,
  CategoryFigures,
  HomeAssistant,
  StatisticsResult,
} from "./types";

/** The saving sensors update every 15 minutes. */
const REFRESH_MS = 5 * 60 * 1000;
const CHART_HEIGHT = "250px";

const COLOR_VARIABLES: Record<Category, [string, string]> = {
  pv: ["--energy-payback-pv-color", "#ff9800"],
  heat_pump: ["--energy-payback-heat-pump-color", "#8e021b"],
  wallbox: ["--energy-payback-wallbox-color", "#0f9d58"],
};

interface Request {
  key: string;
  range: Range;
  period: Period;
  categories: CategoryFigures[];
}

interface Loaded {
  key: string;
  at: number;
  period: Period;
  slots: number[];
  values: Array<{ category: Category; values: Array<number | null> }>;
  failed: boolean;
}

export class EnergyPaybackHistoryCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _selected: { state: true },
    _loaded: { state: true },
    _hasChart: { state: true },
  };

  hass?: HomeAssistant;
  /** The date selection's period; null without one, undefined until known. */
  private _selected?: Range | null;
  private _loaded?: Loaded;
  private _hasChart?: boolean;
  private _loading?: string;
  private _unfollow?: () => void;
  private _chart?: ReturnType<typeof savingsChart>;

  static getStubConfig(): Record<string, never> {
    return {};
  }

  static getConfigForm(): { schema: never[] } {
    return { schema: [] };
  }

  setConfig(_config: unknown): void {
    // The card has no options.
  }

  getCardSize(): number {
    return 5;
  }

  getGridOptions(): { columns: number; min_columns: number } {
    return { columns: 12, min_columns: 6 };
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._follow();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unfollow?.();
    this._unfollow = undefined;
  }

  private get _localize(): Localize {
    return localizer(this.hass?.locale?.language ?? this.hass?.language ?? "en");
  }

  private get _language(): string {
    return this.hass?.locale?.language ?? "en";
  }

  /** Whole amounts, with cents below 100 so that small days and hours show. */
  private _money(value: number, cents = Math.abs(value) < 100): string {
    return new Intl.NumberFormat(this._language, {
      style: "currency",
      currency: this.hass?.config.currency ?? "EUR",
      maximumFractionDigits: cents ? 2 : 0,
      minimumFractionDigits: cents ? 2 : 0,
    }).format(value);
  }

  private _currencySymbol(): string {
    return (
      new Intl.NumberFormat(this._language, {
        style: "currency",
        currency: this.hass?.config.currency ?? "EUR",
      })
        .formatToParts(0)
        .find((part) => part.type === "currency")?.value ?? ""
    );
  }

  private _follow(): void {
    if (this._unfollow || !this.isConnected || !this.hass?.connection) return;
    this._unfollow = followEnergyDate(this.hass.connection, (range) => {
      this._selected = range;
    });
  }

  private _request(categories: CategoryFigures[]): Request | undefined {
    if (this._selected === undefined || !categories.length) return undefined;
    if (categories.some((category) => category.calculating)) return undefined;
    const range =
      this._selected ?? yearsOf(categories.map((c) => c.countingSince));
    const period = this._selected ? periodOf(range) : "year";
    const ids = categories.map((category) => category.savingEntity);
    return {
      key: JSON.stringify([ids, range.start, range.end, period]),
      range,
      period,
      categories,
    };
  }

  private async _load(request: Request): Promise<void> {
    if (!this.hass) return;
    this._loading = request.key;
    const slots = slotsOf(request.range, request.period);
    let result: StatisticsResult = {};
    let failed = false;
    try {
      result = await this.hass.callWS<StatisticsResult>({
        type: "recorder/statistics_during_period",
        start_time: new Date(request.range.start).toISOString(),
        end_time: new Date(request.range.end + 1).toISOString(),
        statistic_ids: request.categories.map((c) => c.savingEntity),
        period: statisticsPeriod(request.period),
        types: ["change"],
      });
    } catch {
      failed = true;
    }
    if (this._loading !== request.key) return;
    this._loading = undefined;
    this._loaded = {
      key: request.key,
      at: Date.now(),
      period: request.period,
      slots,
      values: request.categories.map((category) => ({
        category: category.category,
        values: valuesPerSlot(result[category.savingEntity], slots, request.period),
      })),
      failed,
    };
  }

  protected willUpdate(changed: PropertyValues): void {
    if (!this.hass) return;
    if (changed.has("hass")) this._follow();
    if (this._hasChart === undefined) {
      this._hasChart = false;
      chartReady().then((ok) => {
        this._hasChart = ok;
      });
    }
    const request = this._request(readCategories(this.hass));
    const stale =
      !this._loaded || Date.now() - this._loaded.at > REFRESH_MS;
    if (
      request &&
      request.key !== this._loading &&
      (request.key !== this._loaded?.key || (stale && !this._loading))
    ) {
      void this._load(request);
    }
    if (changed.has("_loaded")) this._chart = this._buildChart();
  }

  private _color(category: Category): string {
    const [variable, fallback] = COLOR_VARIABLES[category];
    return getComputedStyle(this).getPropertyValue(variable).trim() || fallback;
  }

  private _buildChart(): ReturnType<typeof savingsChart> | undefined {
    const loaded = this._loaded;
    if (!loaded || loaded.failed) return undefined;
    const t = this._localize;
    return savingsChart({
      labels: this._labels(loaded.slots, loaded.period),
      series: loaded.values.map(({ category, values }) => ({
        id: category,
        name: t(`category.${category}`),
        color: this._color(category),
        values,
      })),
      unit: this._currencySymbol(),
      total: t("history_total"),
      money: (value) => this._money(value, true),
      tick: (value) =>
        new Intl.NumberFormat(this._language, {
          maximumFractionDigits: 2,
        }).format(value),
    });
  }

  private _labels(
    slots: number[],
    period: Period
  ): Array<{ axis: string; tooltip: string }> {
    const format = (options: Intl.DateTimeFormatOptions) =>
      new Intl.DateTimeFormat(this._language, options);
    const hour = format({ hour: "2-digit", minute: "2-digit" });
    const severalYears =
      new Date(slots[0]).getFullYear() !==
      new Date(slots[slots.length - 1]).getFullYear();
    const axis = {
      hour,
      day: format({ day: "numeric" }),
      month: format(
        severalYears ? { month: "short", year: "2-digit" } : { month: "short" }
      ),
      year: format({ year: "numeric" }),
    }[period];
    const tooltip = {
      hour,
      day: format({ weekday: "short", day: "numeric", month: "short" }),
      month: format({ month: "long", year: "numeric" }),
      year: format({ year: "numeric" }),
    }[period];
    return slots.map((slot) => ({
      axis: axis.format(slot),
      tooltip:
        period === "hour"
          ? `${hour.format(slot)} – ${hour.format(slot + 3_600_000)}`
          : tooltip.format(slot),
    }));
  }

  protected render(): TemplateResult {
    const t = this._localize;
    if (!this.hass) return html``;
    const categories = readCategories(this.hass);
    const title =
      this._selected === null ? t("history_title_years") : t("history_title");
    if (!categories.length) {
      return html`<ha-card>
        <div class="header"><h2 class="title">${title}</h2></div>
        <p class="summary">${t("not_set_up")}</p>
      </ha-card>`;
    }
    const calculating = categories.some((category) => category.calculating);
    const loaded = calculating ? undefined : this._loaded;
    const values = loaded?.values.flatMap((series) => series.values) ?? [];
    const sum = values.reduce<number>((total, value) => total + (value ?? 0), 0);
    const hasData = values.some((value) => value);
    return html`<ha-card>
      <div class="header">
        <h2 class="title">${title}</h2>
        ${loaded && !loaded.failed && hasData
          ? html`<span class="chip">${this._money(sum)}</span>`
          : nothing}
      </div>
      ${calculating
        ? html`<p class="summary">${t("calculating_all")}</p>`
        : this._body(loaded, hasData)}
    </ha-card>`;
  }

  private _body(loaded: Loaded | undefined, hasData: boolean) {
    const t = this._localize;
    if (!this._hasChart) {
      return html`<p class="summary">${t("history_no_chart")}</p>`;
    }
    if (loaded?.failed) {
      return html`<p class="summary">${t("history_failed")}</p>`;
    }
    return html`<div class="chart">
      ${this._chart
        ? html`<ha-chart-base
            .hass=${this.hass}
            .data=${this._chart.data}
            .options=${this._chart.options}
            .height=${CHART_HEIGHT}
          ></ha-chart-base>`
        : nothing}
      ${loaded && !hasData
        ? html`<div class="empty">${t("history_empty")}</div>`
        : nothing}
    </div>`;
  }

  static styles = [
    cardStyles,
    css`
      .chart {
        position: relative;
        min-height: ${unsafeCSS(CHART_HEIGHT)};
        padding: 8px 16px 16px;
      }
      .empty {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        padding: 16px;
        text-align: center;
        color: var(--secondary-text-color);
        background: color-mix(
          in srgb,
          var(--card-background-color, #fff) 70%,
          transparent
        );
      }
    `,
  ];
}
