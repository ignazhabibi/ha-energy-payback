// The savings chart on Home Assistant's own chart element `ha-chart-base`
// (ECharts), set up like HA's energy graphs: stacked bars with rounded caps,
// HA's legend, and the axis tooltip. `ha-chart-base` is internal to the
// frontend and loaded lazily; outside Home Assistant there is none.

const WAIT_MS = 10_000;

type CardHelpers = { createCardElement(config: Record<string, unknown>): unknown };

let ready: Promise<boolean> | undefined;

/** Resolves true once `ha-chart-base` is defined. HA loads it with its chart
 * cards, so creating a statistics graph card pulls it in. */
export function chartReady(): Promise<boolean> {
  if (customElements.get("ha-chart-base")) return Promise.resolve(true);
  const loadCardHelpers = (
    window as unknown as { loadCardHelpers?: () => Promise<CardHelpers> }
  ).loadCardHelpers;
  // Outside a dashboard the element will not come.
  if (!loadCardHelpers) return Promise.resolve(false);
  ready ??= (async () => {
    try {
      const helpers = await loadCardHelpers();
      helpers.createCardElement({ type: "statistics-graph", entities: [] });
    } catch {
      // Another card may still load it.
    }
    const timeout = new Promise<boolean>((resolve) =>
      setTimeout(() => resolve(false), WAIT_MS)
    );
    return Promise.race([
      customElements.whenDefined("ha-chart-base").then(() => true),
      timeout,
    ]);
  })();
  return ready;
}

export interface ChartSeries {
  id: string;
  name: string;
  /** A real color: ECharts cannot read CSS variables. */
  color: string;
  values: Array<number | null>;
}

export interface ChartInput {
  /** Axis label and tooltip heading of each slot. */
  labels: Array<{ axis: string; tooltip: string }>;
  series: ChartSeries[];
  /** The currency symbol, as the axis name. */
  unit: string;
  total: string;
  money: (value: number) => string;
  /** Axis ticks in the user's number format. */
  tick: (value: number) => string;
}

const hex2 = (alpha: number) =>
  Math.round(alpha * 255)
    .toString(16)
    .padStart(2, "0");

/** A color with alpha, for ECharts. */
export function withAlpha(color: string, alpha: number): string {
  const value = color.trim();
  if (/^#[0-9a-f]{6}$/i.test(value)) return value + hex2(alpha);
  if (/^#[0-9a-f]{3}$/i.test(value))
    return `#${[...value.slice(1)].map((c) => c + c).join("")}${hex2(alpha)}`;
  const rgb = value.match(/^rgba?\(([^)]+)\)/i);
  if (rgb) {
    const [r, g, b] = rgb[1].split(/[ ,/]+/).filter(Boolean);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return value;
}

const escape = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (c) => `&#${c.charCodeAt(0)};`
  );

const marker = (color: string) =>
  `<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:${color}"></span>`;

interface TooltipParam {
  dataIndex: number;
  seriesName?: string;
  color?: string;
  value?: number | null;
}

/** The data and options for `ha-chart-base`. Savings can be negative, for
 * example a heat pump in a month of cheap gas: those bars stack downwards. */
export function savingsChart(input: ChartInput) {
  const data = input.series.map((series, k) => ({
    id: series.id,
    type: "bar",
    name: series.name,
    stack: "savings",
    cursor: "default",
    barMaxWidth: 50,
    color: withAlpha(series.color, 0.5),
    itemStyle: { borderColor: series.color },
    data: series.values.map((value, i) => {
      // The outermost bar of each side gets the rounded cap.
      const outer = input.series
        .slice(k + 1)
        .every((other) => Math.sign(other.values[i] ?? 0) !== Math.sign(value ?? 0));
      return {
        value,
        itemStyle: !value
          ? { borderWidth: 0 }
          : outer
            ? { borderRadius: value > 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] }
            : undefined,
      };
    }),
  }));

  const tooltip = (params: unknown): Node => {
    const list = (Array.isArray(params) ? params : [params]) as TooltipParam[];
    const shown = list.filter((p) => p.value);
    const element = document.createElement("div");
    if (!list.length) return element;
    const rows = shown.map(
      (p) =>
        `${marker(String(p.color ?? ""))}${escape(p.seriesName ?? "")}: ${input.money(p.value ?? 0)}`
    );
    const sum = shown.reduce((total, p) => total + (p.value ?? 0), 0);
    element.innerHTML =
      `<b>${escape(input.labels[list[0].dataIndex]?.tooltip ?? "")}</b>` +
      (rows.length ? `<br>${rows.join("<br>")}` : "") +
      (shown.length > 1 ? `<br><b>${escape(input.total)}: ${input.money(sum)}</b>` : "");
    return element;
  };

  const options = {
    xAxis: {
      type: "category",
      data: input.labels.map((label) => label.axis),
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: input.unit,
      nameGap: 2,
      nameTextStyle: { align: "left" },
      axisLabel: { formatter: input.tick },
      splitLine: { show: true },
    },
    grid: { top: 15, bottom: 0, left: 1, right: 1, containLabel: true },
    legend: {
      show: true,
      type: "custom",
      data: input.series.map((series) => ({ id: series.id, name: series.name })),
    },
    // HA renders the tooltip with lit, which shows a string as text.
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: tooltip },
  };
  return { data, options };
}
