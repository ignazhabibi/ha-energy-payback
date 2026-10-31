// Dashboard card of the Energy Payback integration. It needs no options: it
// finds the integration's sensors by itself and renders from the states the
// frontend already has, so it appears without loading delay.

import { mdiCalendarMonthOutline, mdiSigma } from "@mdi/js";
import { LitElement, css, html, nothing, type TemplateResult } from "lit";

import { localizer, type Localize } from "./localize";
import {
  DOMAIN,
  annualReturn,
  readCategories,
  totals,
  yearsToPayback,
} from "./model";
import type { CategoryFigures, HomeAssistant } from "./types";

type View = "total" | "yearly";
const VIEW_STORAGE_KEY = "energy-payback-card-view";

const readView = (): View => {
  try {
    return localStorage.getItem(VIEW_STORAGE_KEY) === "yearly"
      ? "yearly"
      : "total";
  } catch {
    return "total";
  }
};

class EnergyPaybackCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _view: { state: true },
  };

  hass?: HomeAssistant;
  private _view: View = readView();

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
    return 4;
  }

  getGridOptions(): { columns: number; min_columns: number } {
    return { columns: 12, min_columns: 6 };
  }

  private get _localize(): Localize {
    return localizer(this.hass?.locale?.language ?? this.hass?.language ?? "en");
  }

  private get _language(): string {
    return this.hass?.locale?.language ?? "en";
  }

  private _money(value: number, signed = false): string {
    return new Intl.NumberFormat(this._language, {
      style: "currency",
      currency: this.hass?.config.currency ?? "EUR",
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
      signDisplay: signed ? "exceptZero" : "auto",
    }).format(value);
  }

  private _price(value: number): string {
    return new Intl.NumberFormat(this._language, {
      style: "currency",
      currency: this.hass?.config.currency ?? "EUR",
      maximumFractionDigits: 4,
      minimumFractionDigits: 2,
    }).format(value);
  }

  private _percent(value: number): string {
    return new Intl.NumberFormat(this._language, {
      style: "percent",
      maximumFractionDigits: 0,
    }).format(value / 100);
  }

  private _month(value: Date): string {
    return new Intl.DateTimeFormat(this._language, {
      month: "long",
      year: "numeric",
    }).format(value);
  }

  private _years(years: number): string {
    const t = this._localize;
    if (years < 1) return t("under_one_year");
    const count = Math.round(years);
    return count === 1
      ? t("years_one")
      : t("years_other", { count: String(count) });
  }

  private _toggleView(): void {
    this._view = this._view === "total" ? "yearly" : "total";
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, this._view);
    } catch {
      // Remembering the view is a convenience only.
    }
  }

  private _openIntegration(): void {
    history.pushState(null, "", `/config/integrations/integration/${DOMAIN}`);
    window.dispatchEvent(new CustomEvent("location-changed"));
  }

  protected render(): TemplateResult {
    const t = this._localize;
    if (!this.hass) return html``;
    const categories = readCategories(this.hass);
    if (!categories.length) {
      return html`<ha-card>
        <div class="header"><h2 class="title">${t("title")}</h2></div>
        <p class="summary">${t("not_set_up")}</p>
      </ha-card>`;
    }
    const sums = totals(categories);
    const yearly = this._view === "yearly";
    return html`<ha-card>
      <div class="header">
        <h2 class="title">${t("title")}</h2>
        ${this._chip(sums, yearly)}
        <button
          class="toggle"
          type="button"
          aria-label=${yearly ? t("show_total") : t("show_yearly")}
          title=${yearly ? t("show_total") : t("show_yearly")}
          @click=${this._toggleView}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d=${yearly ? mdiSigma : mdiCalendarMonthOutline}></path>
          </svg>
        </button>
      </div>
      <p class="summary">${this._summary(sums, categories, yearly)}</p>
      <ul class="rows">
        ${categories.map((category) => this._row(category, yearly))}
      </ul>
      ${this._footer(categories)}
    </ha-card>`;
  }

  private _chip(sums: ReturnType<typeof totals>, yearly: boolean) {
    const t = this._localize;
    let text: string | null = null;
    if (yearly) {
      if (sums.perYear !== null)
        text = t("per_year", { amount: this._money(sums.perYear, true) });
    } else if (sums.balance !== null) {
      text = this._money(sums.balance, true);
    } else if (!sums.calculating) {
      text = this._money(sums.saved);
    }
    return text === null ? nothing : html`<span class="chip">${text}</span>`;
  }

  private _summary(
    sums: ReturnType<typeof totals>,
    categories: CategoryFigures[],
    yearly: boolean
  ): string {
    const t = this._localize;
    if (sums.calculating) return t("calculating_all");
    if (yearly) {
      if (sums.inThePlusFrom === null) {
        return categories.some((c) => c.perYear === null)
          ? t("yearly_after_twelve")
          : "";
      }
      return sums.balance !== null && sums.balance >= 0
        ? t("in_the_plus")
        : t("in_the_plus_from", { date: this._month(sums.inThePlusFrom) });
    }
    return sums.invested > 0
      ? t("saved_invested", {
          saved: this._money(sums.saved),
          invested: this._money(sums.invested),
        })
      : t("saved_only", { saved: this._money(sums.saved) });
  }

  private _row(category: CategoryFigures, yearly: boolean): TemplateResult {
    const t = this._localize;
    const name = t(`category.${category.category}`);
    let amount = "–";
    if (!category.calculating) {
      if (yearly && category.perYear !== null)
        amount = t("per_year", { amount: this._money(category.perYear) });
      else if (!yearly && category.saving !== null)
        amount = this._money(category.saving);
    }
    return html`<li class="row ${category.category}">
      <span class="swatch" aria-hidden="true"></span>
      <div class="row-body">
        <div class="line">
          <span>${name}</span>
          <span class="amount ${amount === "–" ? "waiting" : ""}">${amount}</span>
        </div>
        <div class="sub">
          ${category.calculating
            ? t("calculating")
            : yearly
              ? this._yearlyDetail(category)
              : this._totalDetail(category, name)}
        </div>
        ${category.calculating ? nothing : this._since(category)}
      </div>
    </li>`;
  }

  /** Since when a row counts, and whether heat was partly estimated. */
  private _since(category: CategoryFigures) {
    const t = this._localize;
    const parts: string[] = [];
    if (category.countingSince)
      parts.push(t("since", { date: this._month(category.countingSince) }));
    if (category.heatEstimated) parts.push(t("heat_estimated"));
    return parts.length
      ? html`<div class="sub since">${parts.join(" · ")}</div>`
      : nothing;
  }

  private _totalDetail(
    category: CategoryFigures,
    name: string
  ): TemplateResult | string {
    const t = this._localize;
    if (category.investment && category.payback !== null) {
      const percent = Math.max(0, category.payback);
      const shown = this._percent(category.payback);
      return html`<div class="meter">
        <div
          class="bar"
          role="progressbar"
          aria-label=${t("progress", { name, percent: shown })}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-valuenow=${Math.min(100, Math.round(percent))}
        >
          <i style="width:${Math.min(100, percent)}%"></i>
        </div>
        <span
          >${percent >= 100
            ? t("paid_off")
            : t("of_investment", {
                percent: shown,
                investment: this._money(category.investment),
              })}</span
        >
      </div>`;
    }
    return t(`instead_${category.category}`);
  }

  private _yearlyDetail(category: CategoryFigures): string {
    const t = this._localize;
    if (category.perYear === null) {
      return category.yearlyFrom
        ? t("yearly_from", { date: this._month(category.yearlyFrom) })
        : "";
    }
    const returnRate = annualReturn(category);
    if (returnRate !== null)
      return t("return_per_year", { percent: this._percent(returnRate) });
    const years = yearsToPayback(category);
    if (years !== null) return t("pays_off_in", { years: this._years(years) });
    if (category.category === "heat_pump")
      return t(category.heating === "oil" ? "instead_of_oil" : "instead_of_gas");
    if (category.category === "wallbox") return t("instead_of_fuel");
    return "";
  }

  private _footer(categories: CategoryFigures[]) {
    const t = this._localize;
    const prices: string[] = [];
    for (const category of categories) {
      if (category.price === null) continue;
      const price = this._price(category.price);
      if (category.category === "heat_pump")
        prices.push(t(category.heating === "oil" ? "oil" : "gas", { price }));
      if (category.category === "wallbox") prices.push(t("fuel", { price }));
    }
    if (!prices.length) return nothing;
    return html`<div class="footer">
      <button
        class="prices"
        type="button"
        title=${t("prices_link")}
        aria-label=${`${t("prices_link")}: ${prices.join(", ")}`}
        @click=${this._openIntegration}
      >
        ${prices.join(" · ")}
      </button>
    </div>`;
  }

  static styles = css`
    :host {
      --energy-payback-pv-color: var(--energy-solar-color, #ff9800);
      --energy-payback-heat-pump-color: var(--energy-gas-color, #8e021b);
      --energy-payback-wallbox-color: var(--energy-non-fossil-color, #0f9d58);
    }
    ha-card {
      height: 100%;
      overflow: hidden;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 8px 0 16px;
    }
    .title {
      flex: 1;
      min-width: 0;
      margin: 0;
      font-size: var(--ha-card-header-font-size, 24px);
      font-weight: var(--ha-font-weight-normal, 400);
      line-height: 32px;
      letter-spacing: -0.012em;
      color: var(--ha-card-header-color, var(--primary-text-color));
    }
    .chip {
      font-size: 14px;
      font-weight: 500;
      line-height: 20px;
      padding: 4px 8px;
      border-radius: 8px;
      border: 1px solid var(--divider-color);
      white-space: nowrap;
      color: var(--primary-text-color);
    }
    .toggle {
      flex: none;
      width: 40px;
      height: 40px;
      border: none;
      border-radius: 50%;
      background: none;
      color: var(--secondary-text-color);
      display: grid;
      place-items: center;
      cursor: pointer;
      padding: 0;
    }
    .toggle:hover {
      background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
    }
    .toggle:focus-visible,
    .prices:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
    .toggle svg {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .summary {
      margin: 0;
      padding: 12px 16px 8px;
      color: var(--secondary-text-color);
    }
    .summary:empty {
      display: none;
    }
    .rows {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .row {
      display: flex;
      gap: 16px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .row:last-child {
      border-bottom: none;
    }
    .pv {
      --color: var(--energy-payback-pv-color);
    }
    .heat_pump {
      --color: var(--energy-payback-heat-pump-color);
    }
    .wallbox {
      --color: var(--energy-payback-wallbox-color);
    }
    .swatch {
      flex: none;
      width: 32px;
      height: 16px;
      margin-top: 2px;
      border-radius: 4px;
      border: 1px solid var(--color);
      background: color-mix(in srgb, var(--color) 50%, transparent);
    }
    .row-body {
      flex: 1;
      min-width: 0;
    }
    .line {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--primary-text-color);
    }
    .amount {
      flex: none;
      font-variant-numeric: tabular-nums;
    }
    .amount.waiting {
      color: var(--secondary-text-color);
    }
    .sub {
      margin-top: 6px;
      font-size: 12px;
      line-height: 16px;
      color: var(--secondary-text-color);
    }
    .sub:empty {
      display: none;
    }
    .sub.since {
      margin-top: 2px;
    }
    .meter {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .bar {
      flex: 1;
      height: 6px;
      border-radius: 4px;
      background: var(--divider-color);
      overflow: hidden;
    }
    .bar i {
      display: block;
      height: 100%;
      background: var(--color);
    }
    .meter span {
      flex: none;
      white-space: nowrap;
    }
    .footer {
      padding: 4px 8px 8px;
      border-top: 1px solid var(--divider-color);
    }
    .prices {
      font: inherit;
      font-size: 12px;
      line-height: 16px;
      color: var(--secondary-text-color);
      background: none;
      border: none;
      padding: 8px;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: underline dotted;
      text-underline-offset: 3px;
      text-align: start;
    }
    .prices:hover {
      color: var(--primary-text-color);
    }
  `;
}

if (!customElements.get("energy-payback-card")) {
  customElements.define("energy-payback-card", EnergyPaybackCard);
}

const registry = window as unknown as {
  customCards?: Array<Record<string, unknown>>;
};
registry.customCards = registry.customCards ?? [];
if (!registry.customCards.some((card) => card.type === "energy-payback-card")) {
  registry.customCards.push({
    type: "energy-payback-card",
    name: "Energy Payback",
    description:
      "What your PV plant, heat pump, and electric car have saved, and when they pay off.",
    preview: true,
    documentationURL: "https://github.com/ignazhabibi/ha-energy-payback",
  });
}
