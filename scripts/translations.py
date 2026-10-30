"""Write custom_components/energy_payback/translations/*.json.

Custom integrations ship finished translation files; Home Assistant's
strings.json references are not resolved for them. The category forms appear
three times (setup, adding, reconfiguring), so they are written once here.

Run: python scripts/translations.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT = Path(__file__).parent.parent / "custom_components/energy_payback/translations"

TEXTS: dict[str, dict[str, Any]] = {
    "en": {
        "categories": {
            "pv": "PV plant",
            "heat_pump": "Heat pump",
            "wallbox": "Wallbox",
        },
        "category_options": {
            "pv": "PV plant",
            "heat_pump": "Heat pump instead of a gas boiler",
            "wallbox": "Electric car instead of a combustion car",
        },
        "add": {
            "pv": "Add PV plant",
            "heat_pump": "Add heat pump",
            "wallbox": "Add wallbox",
        },
        "titles": {
            "pv": "PV plant",
            "heat_pump": "Heat pump instead of a gas boiler",
            "wallbox": "Electric car instead of a combustion car",
        },
        "descriptions": {
            "pv": "From the energy dashboard: solar production, feed-in with compensation, grid import with electricity price. Only what Home Assistant does not know is asked here.",
            "heat_pump": "From the energy dashboard: grid import with electricity price. Saving: gas for the same heat, minus the heat pump's electricity.",
            "wallbox": "From the energy dashboard: grid import with electricity price. Saving: fuel for the same distance, minus the charging electricity.",
        },
        "reconfigure_note": 'New prices and investments apply from the next full hour; what was already computed stays. Other changes, such as the meters, an assumption, or "In operation since", compute the category again.',
        "fields": {
            "meters": "Electricity meters",
            "heat_meters": "Heat meters (optional)",
            "scop": "SCOP",
            "gas_price": "Gas price",
            "fuel_price": "Fuel price",
            "investment": "Investment (optional)",
            "commissioned": "In operation since (optional)",
            "boiler_efficiency": "Gas boiler efficiency",
            "combustion_consumption": "Consumption of the combustion car",
            "ev_consumption": "Consumption of the electric car",
            "gas_price_entity": "Gas price from an entity (optional)",
            "fuel_price_entity": "Fuel price from an entity (optional)",
            "investment_entity": "Investment from an entity (optional)",
            "grid": "Electricity tariff",
        },
        "field_overrides": {
            "heat_pump": {"investment": "Extra cost over a gas boiler (optional)"},
            "wallbox": {
                "investment": "Extra cost over a combustion car (optional)",
                "commissioned": "First electric car since (optional)",
            },
        },
        "hints": {
            "meters": "From the individual devices of the energy dashboard. Choose all that belong to it, for example heating and hot water.",
            "heat_meters": "Without one: heat = electricity × SCOP.",
            "scop": "Only used without a heat meter, or before it was installed. Usually 3 to 4.5.",
            "gas_price": "What a kilowatt-hour of gas would cost today. Also used for the computed past.",
            "fuel_price": "What a litre would cost today. Also used for the computed past.",
            "investment": "What it cost. The card then shows how far it has paid for itself.",
            "boiler_efficiency": "The share of the gas's energy that becomes heat.",
            "combustion_consumption": "The car the electric car replaces. With several cars, an average.",
            "ev_consumption": "Measured at the wallbox, with charging losses. With several cars, an average.",
            "gas_price_entity": "For example a number helper or your supplier's price sensor. It takes precedence; when it is unavailable, the fixed price counts.",
            "fuel_price_entity": "For example a number helper or a fuel price sensor. It takes precedence; when it is unavailable, the fixed price counts.",
            "investment_entity": "For example a number helper with the running sum of your expenses. When it is unavailable, the fixed amount counts.",
            "grid": "The grid connection whose price the device pays, for example a separate heat pump tariff.",
        },
        "commissioned_hints": {
            "pv": "Empty: from the beginning of the solar data ({data_since}). If the plant is older, enter the real date.",
            "heat_pump": "Empty: from the first data of the electricity meters.",
            "wallbox": "Empty: from the first charge in the data.",
        },
        "sections": {"assumptions": "Assumptions", "advanced": "Advanced"},
        "user": {
            "title": "Set up Energy Payback",
            "description": "Found in the energy dashboard:\n- Electricity price: {price}\n- Feed-in compensation: {feed_in}\n- Solar: {solar}\n- Individual devices: {devices}\n\nThe integration keeps reading these from the energy dashboard. When you change something there, it uses the new setup from then on. Heat pump and wallbox need their meters under individual devices in the [energy dashboard](/config/energy).",
            "categories": "What should be evaluated?",
            "categories_hint": "You can add more categories later on the integration page.",
        },
        "errors": {
            "meters_required": "Choose at least one meter.",
            "commissioned_in_future": "The date lies in the future.",
            "categories_required": "Choose at least one category.",
        },
        "aborts": {
            "no_energy_dashboard": "The energy dashboard has no grid import with an electricity price. Energy Payback calculates with them; please set them up in the [energy dashboard](/config/energy) first.",
            "nothing_to_evaluate": "The energy dashboard has neither solar production nor individual devices. Add your PV plant, or the meters of your heat pump or wallbox, in the [energy dashboard](/config/energy) first.",
            "energy_interface": "Energy Payback cannot read the energy dashboard of this Home Assistant version. Please look for an update of Energy Payback.",
            "already_configured": "This category is already set up. To change it, use Reconfigure on it.",
            "single_instance_allowed": "Energy Payback is already set up. Add more categories on its integration page.",
            "single_instance_allowed": "Energy Payback is already set up. Add more categories on its integration page.",
            "not_available": "The energy dashboard does not provide the data for this category. It needs solar production for the PV plant, and individual devices for heat pump and wallbox.",
        },
        "create_entry": 'The past is now being computed in the background; this usually takes less than a minute. Add the card "Energy Payback" from the card picker of any dashboard.',
        "devices": {"total": "Energy Payback"},
        "entities": {
            "saving": "Saving",
            "payback": "Paid back",
            "saving_per_year": "Saving per year",
            "balance": "Balance",
        },
        "attributes": {
            "category": "Category",
            "calculating": "Calculating",
            "counting_since": "Counted since",
            "commissioned": "In operation since",
            "investment": "Investment",
            "data_complete": "Data since start of operation",
            "yearly_from": "Yearly figures from",
            "assumed_price": "Assumed price",
        },
        "exceptions": {
            "energy_interface": "Cannot read the energy dashboard: {error}",
        },
        "issues": {
            "energy_interface": (
                "Energy Payback cannot read the energy dashboard",
                "This version of Home Assistant stores the energy dashboard or its statistics in a way Energy Payback does not understand. The savings are unavailable until Energy Payback is updated.",
            ),
            "no_grid_price": (
                "Energy Payback is missing the electricity price",
                "The energy dashboard has no grid import with an electricity price anymore. The savings keep their last values until it is set up again in the [energy dashboard](/config/energy).",
            ),
            "missing_meter": (
                "{category}: meter missing in the energy dashboard",
                "The energy dashboard no longer has: {meters}. {category} keeps its last figures until this is fixed. Add the meter back in the [energy dashboard](/config/energy), or choose other meters with Reconfigure on the integration page of Energy Payback.",
            ),
        },
    },
    "de": {
        "categories": {
            "pv": "PV-Anlage",
            "heat_pump": "Wärmepumpe",
            "wallbox": "Wallbox",
        },
        "category_options": {
            "pv": "PV-Anlage",
            "heat_pump": "Wärmepumpe statt Gastherme",
            "wallbox": "E-Auto statt Verbrenner",
        },
        "add": {
            "pv": "PV-Anlage hinzufügen",
            "heat_pump": "Wärmepumpe hinzufügen",
            "wallbox": "Wallbox hinzufügen",
        },
        "titles": {
            "pv": "PV-Anlage",
            "heat_pump": "Wärmepumpe statt Gastherme",
            "wallbox": "E-Auto statt Verbrenner",
        },
        "descriptions": {
            "pv": "Aus dem Energie-Dashboard: Solarertrag, Einspeisung mit Vergütung, Netzbezug mit Strompreis. Hier steht nur, was Home Assistant nicht weiß.",
            "heat_pump": "Aus dem Energie-Dashboard: Netzbezug mit Strompreis. Gerechnet wird: Gas für dieselbe Wärme minus Strom der Wärmepumpe.",
            "wallbox": "Aus dem Energie-Dashboard: Netzbezug mit Strompreis. Gerechnet wird: Sprit für dieselben Kilometer minus Ladestrom.",
        },
        "reconfigure_note": "Neue Preise und Investitionen gelten ab der nächsten vollen Stunde; bisher Gerechnetes bleibt. Andere Änderungen, etwa an den Zählern, an einer Annahme oder an »In Betrieb seit«, rechnen die Kategorie neu.",
        "fields": {
            "meters": "Stromzähler",
            "heat_meters": "Wärmemengenzähler (optional)",
            "scop": "SCOP",
            "gas_price": "Gaspreis",
            "fuel_price": "Spritpreis",
            "investment": "Investition (optional)",
            "commissioned": "In Betrieb seit (optional)",
            "boiler_efficiency": "Wirkungsgrad der Gastherme",
            "combustion_consumption": "Verbrauch Verbrenner",
            "ev_consumption": "Verbrauch E-Auto",
            "gas_price_entity": "Gaspreis aus einer Entität (optional)",
            "fuel_price_entity": "Spritpreis aus einer Entität (optional)",
            "investment_entity": "Investition aus einer Entität (optional)",
            "grid": "Stromtarif",
        },
        "field_overrides": {
            "heat_pump": {"investment": "Mehrpreis gegenüber Gastherme (optional)"},
            "wallbox": {
                "investment": "Mehrpreis gegenüber Verbrenner (optional)",
                "commissioned": "Erstes E-Auto seit (optional)",
            },
        },
        "hints": {
            "meters": "Aus den einzelnen Geräten des Energie-Dashboards. Wähle alle, die dazugehören, etwa Heizung und Warmwasser.",
            "heat_meters": "Ohne Zähler gilt: Wärme = Strom × SCOP.",
            "scop": "Nur ohne Wärmemengenzähler nötig, oder für die Zeit vor seinem Einbau. Üblich sind 3 bis 4,5.",
            "gas_price": "Was eine Kilowattstunde Gas heute kosten würde. Gilt auch für die nachgerechnete Vergangenheit.",
            "fuel_price": "Was ein Liter heute kosten würde. Gilt auch für die nachgerechnete Vergangenheit.",
            "investment": "Was es gekostet hat. Daraus rechnet die Karte, wie weit es sich bezahlt gemacht hat.",
            "boiler_efficiency": "Der Anteil der Energie im Gas, der zu Wärme wird.",
            "combustion_consumption": "Das Auto, das das E-Auto ersetzt. Bei mehreren Autos ein Mittelwert.",
            "ev_consumption": "Ab Wallbox gemessen, mit Ladeverlusten. Bei mehreren Autos ein Mittelwert.",
            "gas_price_entity": "Zum Beispiel ein Zahlen-Helfer oder der Preis-Sensor deines Gasversorgers. Er hat Vorrang; ist er nicht verfügbar, gilt der feste Preis.",
            "fuel_price_entity": "Zum Beispiel ein Zahlen-Helfer oder ein Spritpreis-Sensor. Er hat Vorrang; ist er nicht verfügbar, gilt der feste Preis.",
            "investment_entity": "Zum Beispiel ein Zahlen-Helfer mit der laufenden Summe deiner Ausgaben. Ist er nicht verfügbar, gilt der feste Betrag.",
            "grid": "Der Netzanschluss, dessen Preis das Gerät zahlt, etwa ein eigener Wärmepumpentarif.",
        },
        "commissioned_hints": {
            "pv": "Leer: ab Beginn der Solardaten ({data_since}). Ist die Anlage älter, trag das echte Datum ein.",
            "heat_pump": "Leer: ab den ersten Daten der Stromzähler.",
            "wallbox": "Leer: ab dem ersten Ladevorgang in den Daten.",
        },
        "sections": {"assumptions": "Annahmen", "advanced": "Erweitert"},
        "user": {
            "title": "Energy Payback einrichten",
            "description": "Gefunden im Energie-Dashboard:\n- Strompreis: {price}\n- Einspeisevergütung: {feed_in}\n- Solar: {solar}\n- Einzelne Geräte: {devices}\n\nDie Integration liest diese Angaben laufend aus dem Energie-Dashboard. Änderst du dort etwas, rechnet sie ab dann damit. Für Wärmepumpe und Wallbox braucht es deren Zähler unter »Einzelne Geräte« im [Energie-Dashboard](/config/energy).",
            "categories": "Was soll ausgewertet werden?",
            "categories_hint": "Weitere Kategorien fügst du später auf der Integrationsseite hinzu.",
        },
        "errors": {
            "meters_required": "Wähle mindestens einen Zähler.",
            "commissioned_in_future": "Das Datum liegt in der Zukunft.",
            "categories_required": "Wähle mindestens eine Kategorie.",
        },
        "aborts": {
            "no_energy_dashboard": "Im Energie-Dashboard fehlen Netzbezug oder Strompreis. Energy Payback rechnet mit diesen Angaben; bitte richte sie zuerst im [Energie-Dashboard](/config/energy) ein.",
            "nothing_to_evaluate": "Das Energie-Dashboard hat weder Solarertrag noch einzelne Geräte. Trag zuerst die PV-Anlage oder die Zähler von Wärmepumpe oder Wallbox im [Energie-Dashboard](/config/energy) ein.",
            "energy_interface": "Energy Payback kann das Energie-Dashboard dieser Home-Assistant-Version nicht lesen. Bitte sieh nach, ob es ein Update von Energy Payback gibt.",
            "already_configured": "Diese Kategorie ist schon eingerichtet. Ändern kannst du sie mit »Neu konfigurieren«.",
            "single_instance_allowed": "Energy Payback ist schon eingerichtet. Weitere Kategorien fügst du auf seiner Integrationsseite hinzu.",
            "single_instance_allowed": "Energy Payback ist schon eingerichtet. Weitere Kategorien fügst du auf seiner Integrationsseite hinzu.",
            "not_available": "Das Energie-Dashboard liefert die Daten für diese Kategorie nicht. Die PV-Anlage braucht einen Solarertrag, Wärmepumpe und Wallbox brauchen einzelne Geräte.",
        },
        "create_entry": "Die Vergangenheit wird jetzt im Hintergrund nachgerechnet; das dauert meist unter einer Minute. Die Karte »Energy Payback« findest du im Dashboard unter »Karte hinzufügen«.",
        "devices": {"total": "Energy Payback"},
        "entities": {
            "saving": "Ersparnis",
            "payback": "Amortisiert",
            "saving_per_year": "Ersparnis pro Jahr",
            "balance": "Bilanz",
        },
        "attributes": {
            "category": "Kategorie",
            "calculating": "Wird berechnet",
            "counting_since": "Gezählt seit",
            "commissioned": "In Betrieb seit",
            "investment": "Investition",
            "data_complete": "Daten seit Inbetriebnahme",
            "yearly_from": "Jahreswerte ab",
            "assumed_price": "Angenommener Preis",
        },
        "exceptions": {
            "energy_interface": "Das Energie-Dashboard kann nicht gelesen werden: {error}",
        },
        "issues": {
            "energy_interface": (
                "Energy Payback kann das Energie-Dashboard nicht lesen",
                "Diese Home-Assistant-Version speichert das Energie-Dashboard oder seine Statistiken so, wie Energy Payback es nicht versteht. Die Ersparnisse sind nicht verfügbar, bis Energy Payback aktualisiert ist.",
            ),
            "no_grid_price": (
                "Energy Payback fehlt der Strompreis",
                "Im Energie-Dashboard gibt es keinen Netzbezug mit Strompreis mehr. Die Ersparnisse behalten ihre letzten Werte, bis er im [Energie-Dashboard](/config/energy) wieder eingerichtet ist.",
            ),
            "missing_meter": (
                "{category}: Zähler fehlt im Energie-Dashboard",
                "Im Energie-Dashboard fehlt: {meters}. {category} behält die letzten Werte, bis das behoben ist. Trag den Zähler im [Energie-Dashboard](/config/energy) wieder ein, oder wähle mit »Neu konfigurieren« auf der Integrationsseite von Energy Payback andere Zähler.",
            ),
        },
    },
}

CATEGORY_FIELDS = {
    "pv": {
        "main": ["investment", "commissioned"],
        "assumptions": [],
        "advanced": ["investment_entity"],
    },
    "heat_pump": {
        "main": [
            "meters",
            "heat_meters",
            "scop",
            "gas_price",
            "investment",
            "commissioned",
        ],
        "assumptions": ["boiler_efficiency"],
        "advanced": ["gas_price_entity", "investment_entity", "grid"],
    },
    "wallbox": {
        "main": ["meters", "fuel_price", "investment", "commissioned"],
        "assumptions": ["combustion_consumption", "ev_consumption"],
        "advanced": ["fuel_price_entity", "investment_entity", "grid"],
    },
}


def category_step(
    t: dict[str, Any], category: str, reconfigure: bool
) -> dict[str, Any]:
    """Return the translations of one category form."""
    fields = CATEGORY_FIELDS[category]
    names = t["fields"] | t["field_overrides"].get(category, {})
    hints = t["hints"] | {"commissioned": t["commissioned_hints"][category]}

    def block(keys: list[str]) -> dict[str, Any]:
        return {
            "data": {key: names[key] for key in keys},
            "data_description": {key: hints[key] for key in keys},
        }

    description = t["descriptions"][category]
    if reconfigure:
        description = f"{t['reconfigure_note']}\n\n{description}"
    step: dict[str, Any] = {
        "title": t["titles"][category],
        "description": description,
        **block(fields["main"]),
    }
    sections = {
        name: {"name": t["sections"][name], **block(fields[name])}
        for name in ("assumptions", "advanced")
        if fields[name]
    }
    if sections:
        step["sections"] = sections
    return step


def build(t: dict[str, Any]) -> dict[str, Any]:
    """Return a complete translation file."""
    categories = list(CATEGORY_FIELDS)
    errors = t["errors"]
    aborts = t["aborts"]
    return {
        "config": {
            "step": {
                "user": {
                    "title": t["user"]["title"],
                    "description": t["user"]["description"],
                    "data": {"categories": t["user"]["categories"]},
                    "data_description": {"categories": t["user"]["categories_hint"]},
                },
                **{
                    category: category_step(t, category, False)
                    for category in categories
                },
            },
            "error": errors,
            "abort": {
                key: aborts[key]
                for key in (
                    "no_energy_dashboard",
                    "nothing_to_evaluate",
                    "energy_interface",
                    "single_instance_allowed",
                )
            },
            "create_entry": {"default": t["create_entry"]},
        },
        "config_subentries": {
            category: {
                "entry_type": t["categories"][category],
                "initiate_flow": {"user": t["add"][category]},
                "step": {
                    "user": category_step(t, category, False),
                    "reconfigure": category_step(t, category, True),
                },
                "error": errors,
                "abort": {
                    key: aborts[key]
                    for key in (
                        "energy_interface",
                        "already_configured",
                        "not_available",
                    )
                },
            }
            for category in categories
        },
        "device": {
            "total": {"name": t["devices"]["total"]},
            **{
                category: {"name": t["categories"][category]} for category in categories
            },
        },
        "entity": {
            "sensor": {
                "saving": {
                    "name": t["entities"]["saving"],
                    "state_attributes": {
                        key: {"name": name} for key, name in t["attributes"].items()
                    },
                },
                **{
                    key: {"name": t["entities"][key]}
                    for key in ("payback", "saving_per_year", "balance")
                },
            }
        },
        "exceptions": {
            key: {"message": message} for key, message in t["exceptions"].items()
        },
        "issues": {
            key: {"title": title, "description": description}
            for key, (title, description) in t["issues"].items()
        },
        "selector": {"categories": {"options": t["category_options"]}},
    }


def main() -> None:
    """Write all translation files."""
    OUT.mkdir(parents=True, exist_ok=True)
    for language, texts in TEXTS.items():
        path = OUT / f"{language}.json"
        path.write_text(
            json.dumps(build(texts), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
