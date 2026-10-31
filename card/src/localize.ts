// The card's own texts. Home Assistant does not load custom cards' translations.

const en = {
  title: "Balance",
  "category.pv": "PV plant",
  "category.heat_pump": "Heat pump",
  "category.wallbox": "Electric car",
  show_yearly: "Show yearly figures",
  show_total: "Show totals",
  not_set_up:
    "Set up the Energy Payback integration to see what your PV plant, heat pump, and electric car have saved.",
  calculating_all: "The past is being computed …",
  calculating: "Being computed …",
  saved_invested: "{saved} saved, {invested} invested",
  saved_only: "{saved} saved",
  of_investment: "{percent} of {investment}",
  paid_off: "paid off",
  since: "since {date}",
  heat_estimated: "heat partly estimated",
  instead_heat_pump: "no extra cost entered",
  instead_wallbox: "no extra cost entered",
  instead_pv: "no purchase cost entered",
  in_the_plus_from: "In the plus from about {date}",
  in_the_plus: "In the plus",
  yearly_after_twelve: "Yearly figures after twelve months of data.",
  yearly_from: "Yearly figure from {date}",
  pays_off_in: "pays off in about {years}",
  years_one: "1 year",
  years_other: "{count} years",
  under_one_year: "less than a year",
  return_per_year: "paid off, {percent} return per year",
  instead_of_gas: "instead of gas",
  instead_of_oil: "instead of oil",
  instead_of_fuel: "instead of fuel",
  per_year: "{amount}/year",
  gas: "Gas {price}/kWh",
  oil: "Oil {price}/l",
  fuel: "Fuel {price}/l",
  prices_link: "Change the prices",
  progress: "{name}: {percent} of the investment saved",
  history_title: "Savings",
  history_title_years: "Savings per year",
  history_total: "Total",
  history_no_chart: "The chart is only shown in Home Assistant.",
  history_failed: "The statistics could not be loaded.",
  history_empty: "No savings in this period.",
};

type Key = keyof typeof en;

const de: Record<Key, string> = {
  title: "Bilanz",
  "category.pv": "PV-Anlage",
  "category.heat_pump": "Wärmepumpe",
  "category.wallbox": "E-Auto",
  show_yearly: "Jahreswerte zeigen",
  show_total: "Gesamtwerte zeigen",
  not_set_up:
    "Richte die Integration Energy Payback ein, um zu sehen, was PV-Anlage, Wärmepumpe und E-Auto gespart haben.",
  calculating_all: "Die Vergangenheit wird nachgerechnet …",
  calculating: "Wird berechnet …",
  saved_invested: "{saved} gespart, {invested} investiert",
  saved_only: "{saved} gespart",
  of_investment: "{percent} von {investment}",
  paid_off: "amortisiert",
  since: "seit {date}",
  heat_estimated: "Wärme teilweise geschätzt",
  instead_heat_pump: "ohne Mehrkosten",
  instead_wallbox: "ohne Mehrkosten",
  instead_pv: "ohne Anschaffungskosten",
  in_the_plus_from: "Im Plus ab etwa {date}",
  in_the_plus: "Im Plus",
  yearly_after_twelve: "Jahreswerte gibt es nach zwölf Monaten Daten.",
  yearly_from: "Jahreswert ab {date}",
  pays_off_in: "amortisiert in etwa {years}",
  years_one: "1 Jahr",
  years_other: "{count} Jahren",
  under_one_year: "weniger als einem Jahr",
  return_per_year: "amortisiert, {percent} Rendite pro Jahr",
  instead_of_gas: "statt Gas",
  instead_of_oil: "statt Öl",
  instead_of_fuel: "statt Sprit",
  per_year: "{amount}/Jahr",
  gas: "Gas {price}/kWh",
  oil: "Öl {price}/l",
  fuel: "Sprit {price}/l",
  prices_link: "Preise ändern",
  progress: "{name}: {percent} der Investition gespart",
  history_title: "Ersparnis",
  history_title_years: "Ersparnis pro Jahr",
  history_total: "Summe",
  history_no_chart: "Das Diagramm erscheint nur in Home Assistant.",
  history_failed: "Die Statistik konnte nicht geladen werden.",
  history_empty: "Keine Ersparnis in diesem Zeitraum.",
};

const languages: Record<string, Record<Key, string>> = { en, de };

export type Localize = (key: Key, values?: Record<string, string>) => string;

export function localizer(language: string): Localize {
  const texts = languages[language.split("-")[0]] ?? en;
  return (key, values = {}) =>
    texts[key].replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? "");
}
