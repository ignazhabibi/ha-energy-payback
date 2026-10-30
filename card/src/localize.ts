// The card's own texts. Home Assistant does not load custom cards' translations.

const en = {
  title: "Balance",
  "category.pv": "PV plant",
  "category.heat_pump": "Heat pump",
  "category.wallbox": "Electric cars",
  show_yearly: "Show yearly figures",
  show_total: "Show totals",
  not_set_up:
    "Set up the Energy Payback integration to see what your PV plant, heat pump, and electric car have saved.",
  calculating_all: "The past is being computed …",
  calculating: "Being computed …",
  saved_invested: "{saved} saved, {invested} invested",
  saved_only: "{saved} saved",
  no_balance:
    "Saved since {since}. No balance, because the {names} is older than the data.",
  no_balance_many:
    "Saved since {since}. No balance, because some systems are older than the data.",
  of_investment: "{percent} of {investment}",
  paid_off: "paid off",
  counted_since:
    "counted since {since}, in operation since {commissioned}",
  instead_heat_pump: "instead of gas, without extra cost",
  instead_wallbox: "instead of fuel, without extra cost",
  instead_pv: "without investment",
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
  instead_of_fuel: "instead of fuel",
  per_year: "{amount}/year",
  gas: "Gas {price}/kWh",
  fuel: "Fuel {price}/l",
  prices_link: "Change the assumed prices",
  progress: "{name}: {percent} of the investment saved",
};

type Key = keyof typeof en;

const de: Record<Key, string> = {
  title: "Bilanz",
  "category.pv": "PV-Anlage",
  "category.heat_pump": "Wärmepumpe",
  "category.wallbox": "E-Autos",
  show_yearly: "Jahreswerte zeigen",
  show_total: "Gesamtwerte zeigen",
  not_set_up:
    "Richte die Integration Energy Payback ein, um zu sehen, was PV-Anlage, Wärmepumpe und E-Auto gespart haben.",
  calculating_all: "Die Vergangenheit wird nachgerechnet …",
  calculating: "Wird berechnet …",
  saved_invested: "{saved} gespart, {invested} investiert",
  saved_only: "{saved} gespart",
  no_balance:
    "Gespart seit {since}. Keine Bilanz, weil die {names} älter ist als die Daten.",
  no_balance_many:
    "Gespart seit {since}. Keine Bilanz, weil manche Anlagen älter sind als die Daten.",
  of_investment: "{percent} von {investment}",
  paid_off: "amortisiert",
  counted_since: "gezählt seit {since}, in Betrieb seit {commissioned}",
  instead_heat_pump: "statt Gas, ohne Mehrpreis",
  instead_wallbox: "statt Sprit, ohne Mehrpreis",
  instead_pv: "ohne Investition",
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
  instead_of_fuel: "statt Sprit",
  per_year: "{amount}/Jahr",
  gas: "Gas {price}/kWh",
  fuel: "Sprit {price}/l",
  prices_link: "Angenommene Preise ändern",
  progress: "{name}: {percent} der Investition gespart",
};

const languages: Record<string, Record<Key, string>> = { en, de };

export type Localize = (key: Key, values?: Record<string, string>) => string;

export function localizer(language: string): Localize {
  const texts = languages[language.split("-")[0]] ?? en;
  return (key, values = {}) =>
    texts[key].replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? "");
}
