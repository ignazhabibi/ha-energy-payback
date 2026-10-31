"""Tests for the config flow and the category subentry flows."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_payback.const import DOMAIN
from custom_components.energy_payback.sources import EnergyInterfaceError

from .conftest import (
    HEAT_PUMP_DATA,
    PREFS,
    WALLBOX_DATA,
    import_hourly,
    make_entry,
    set_energy_prefs,
    setup_entry,
)

HEAT_PUMP_METERS: dict[str, Any] = {
    "meters": ["sensor.heat_pump"],
    "heating": "gas",
    "investment": 9000,
}
HEAT_PUMP_VALUES: dict[str, Any] = {
    "gas_price": 0.11,
    "scop": 3.8,
    "gas_price_entity": "input_number.gas_price",
}
WALLBOX_METERS: dict[str, Any] = {"meters": ["sensor.wallbox"]}
WALLBOX_VALUES: dict[str, Any] = {
    "ev_consumption": 20,
    "combustion_consumption": 7,
    "fuel_price": 1.75,
}


@pytest.fixture(autouse=True)
async def energy_prefs(hass: HomeAssistant) -> None:
    """Set up an energy dashboard without statistics."""
    hass.config.currency = "EUR"
    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)


def _options(result: Any, field: str) -> list[Any]:
    selector = next(
        value for key, value in result["data_schema"].schema.items() if key == field
    )
    return list(selector.config["options"])


def _fields(result: Any) -> list[str]:
    return [str(key) for key in result["data_schema"].schema]


def _suggested(result: Any) -> dict[str, Any]:
    return {
        str(key): key.description.get("suggested_value")
        for key in result["data_schema"].schema
        if key.description
    }


async def _start(hass: HomeAssistant, categories: list[str]) -> Any:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": categories}
    )


async def test_full_setup(hass: HomeAssistant) -> None:
    """The overview leads through the steps of each chosen category."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["description_placeholders"] == {
        "grid": "✓",
        "export": "✓",
        "compensation": "✓",
        "solar": "1",
        "battery": "–",
        "devices": "3",
    }
    # Nothing is preselected.
    assert _suggested(result) == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": ["pv", "heat_pump", "wallbox"]}
    )
    assert result["step_id"] == "pv"
    assert "since" in result["description_placeholders"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"investment": 14500}
    )
    assert result["step_id"] == "heat_pump"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], HEAT_PUMP_METERS
    )
    # Without heat meters the seasonal COP is needed.
    assert result["step_id"] == "heat_pump_values_gas_scop"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], HEAT_PUMP_VALUES
    )
    assert result["step_id"] == "wallbox"
    # A meter chosen for the heat pump is not offered again.
    assert [option["value"] for option in _options(result, "meters")] == [
        "sensor.wallbox",
        "sensor.washer",
    ]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], WALLBOX_METERS
    )
    assert result["step_id"] == "wallbox_values"
    with patch("custom_components.energy_payback.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], WALLBOX_VALUES
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.minor_version == 2
    subentries = {s.subentry_type: s for s in entry.subentries.values()}
    assert subentries["pv"].data["investment"] == 14500
    assert subentries["pv"].title == "PV plant"
    heat_pump = dict(subentries["heat_pump"].data)
    assert heat_pump.pop("setup_at") > 0
    assert heat_pump == {
        "meters": ["sensor.heat_pump"],
        "heat_meters": [],
        "heating": "gas",
        "investment": 9000,
        "before": {"price": 0.11, "scop": 3.8},
        "current": {
            "price": 0.11,
            "scop": 3.8,
            "price_entity": "input_number.gas_price",
        },
    }
    assert subentries["wallbox"].data["before"] == {
        "ev_consumption": 20,
        "combustion_consumption": 7,
        "price": 1.75,
    }
    assert subentries["wallbox"].title == "Electric car"


async def test_setup_validation(hass: HomeAssistant) -> None:
    """Missing choices and values of 0 are rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"categories": "categories_required"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": ["heat_pump"]}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {
        "meters": "meters_required",
        "heating": "heating_required",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**HEAT_PUMP_METERS, "heating": "oil"}
    )
    assert result["step_id"] == "heat_pump_values_oil_scop"
    assert "oil_price" in _fields(result)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"oil_price": 0, "scop": 0.5, "tariff": 0}
    )
    assert result["errors"] == {
        "oil_price": "value_required",
        "scop": "scop_range",
        "tariff": "value_required",
    }
    with patch("custom_components.energy_payback.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"oil_price": 1.1, "scop": 3.5}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    heat_pump = next(iter(result["result"].subentries.values())).data
    assert heat_pump["before"] == {"price": 1.1, "scop": 3.5}


async def test_scop_only_where_heat_data_is_missing(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """With heat data from the start no COP is asked; with later data, until when."""
    import_hourly(hass, "sensor.heat_pump", data_start, [0.0, 1.0, 1.0, 1.0])
    import_hourly(hass, "sensor.heat", data_start, [0.0, 4.0, 4.0, 4.0])
    import_hourly(hass, "sensor.heat_late", data_start + timedelta(hours=2), [0.0, 4.0])
    await async_wait_recording_done(hass)

    result = await _start(hass, ["heat_pump"])
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**HEAT_PUMP_METERS, "heat_meters": ["sensor.heat"]}
    )
    assert result["step_id"] == "heat_pump_values_gas"
    assert "scop" not in _fields(result)

    result = await _start(hass, ["heat_pump"])
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**HEAT_PUMP_METERS, "heat_meters": ["sensor.heat_late"]}
    )
    assert result["step_id"] == "heat_pump_values_gas_scop_until"
    assert result["description_placeholders"]["heat_until"]


@pytest.mark.parametrize(
    ("prefs", "reason"),
    [
        (
            {"energy_sources": [], "device_consumption": []},
            "no_energy_dashboard",
        ),
        (
            {"energy_sources": PREFS["energy_sources"][:1], "device_consumption": []},
            "nothing_to_evaluate",
        ),
    ],
)
async def test_setup_aborts(
    hass: HomeAssistant, prefs: dict[str, Any], reason: str
) -> None:
    """Setup ends with an explanation when the energy dashboard lacks data."""
    await set_energy_prefs(hass, prefs)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


@pytest.mark.parametrize(
    ("prefs", "step_id", "options"),
    [
        ({"device_consumption": []}, "user_no_devices", ["pv"]),
        (
            {"energy_sources": PREFS["energy_sources"][:1]},
            "user_no_solar",
            ["heat_pump", "wallbox"],
        ),
    ],
)
async def test_only_possible_categories_offered(
    hass: HomeAssistant, prefs: dict[str, Any], step_id: str, options: list[str]
) -> None:
    """Only possible categories are offered, and the overview says what is missing."""
    await set_energy_prefs(hass, prefs)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == step_id
    assert _options(result, "categories") == options


async def test_pv_without_feed_in(hass: HomeAssistant) -> None:
    """The PV step warns when the energy dashboard has no feed-in."""
    grid = {**PREFS["energy_sources"][0], "stat_energy_to": None}
    await set_energy_prefs(hass, {"energy_sources": [grid, PREFS["energy_sources"][1]]})
    result = await _start(hass, ["pv"])
    assert result["step_id"] == "pv_no_export"
    with patch("custom_components.energy_payback.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_setup_aborts_on_interface_error(hass: HomeAssistant) -> None:
    """A changed energy interface ends setup."""
    with patch(
        "custom_components.energy_payback.config_flow.async_get_energy_setup",
        side_effect=EnergyInterfaceError("moved"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "energy_interface"


async def test_single_instance(hass: HomeAssistant) -> None:
    """The household can be set up only once."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_add_category(hass: HomeAssistant) -> None:
    """A category can be added later, with the same steps as in the setup."""
    entry = make_entry(("heat_pump", HEAT_PUMP_DATA))
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "wallbox"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert [option["value"] for option in _options(result, "meters")] == [
        "sensor.wallbox",
        "sensor.washer",
    ]
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["errors"] == {"meters": "meters_required"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], WALLBOX_METERS
    )
    assert result["step_id"] == "wallbox_values"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**WALLBOX_VALUES, "fuel_price": 0}
    )
    assert result["errors"] == {"fuel_price": "value_required"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], WALLBOX_VALUES
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {s.subentry_type for s in entry.subentries.values()} == {
        "heat_pump",
        "wallbox",
    }
    assert hass.states.get("sensor.electric_car_saving") is not None


async def test_add_pv(hass: HomeAssistant) -> None:
    """The PV plant is added in one step."""
    entry = make_entry(("wallbox", WALLBOX_DATA))
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "pv"), context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "pv"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"investment": 12000}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    pv = next(s for s in entry.subentries.values() if s.subentry_type == "pv")
    assert pv.data["investment"] == 12000


async def test_add_category_twice(hass: HomeAssistant) -> None:
    """Each category exists once."""
    entry = make_entry(("pv", {}))
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "pv"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_add_unavailable_category(hass: HomeAssistant) -> None:
    """A category the energy dashboard has no data for cannot be added."""
    entry = make_entry(("pv", {}))
    await setup_entry(hass, entry)
    await set_energy_prefs(hass, {"device_consumption": []})
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "heat_pump"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_available"


async def test_add_category_interface_error(hass: HomeAssistant) -> None:
    """A changed energy interface ends adding a category."""
    entry = make_entry(("pv", {}))
    await setup_entry(hass, entry)
    with patch(
        "custom_components.energy_payback.config_flow.async_get_energy_setup",
        side_effect=EnergyInterfaceError("moved"),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "heat_pump"), context={"source": SOURCE_USER}
        )
    assert result["reason"] == "energy_interface"


async def _reconfigure(
    hass: HomeAssistant, entry: MockConfigEntry, category: str, option: str
) -> Any:
    subentry = next(s for s in entry.subentries.values() if s.subentry_type == category)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, category),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry.subentry_id},
    )
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": option}
    )


def _data(entry: MockConfigEntry, category: str) -> dict[str, Any]:
    return dict(
        next(s for s in entry.subentries.values() if s.subentry_type == category).data
    )


async def test_reconfigure_values_from_now_on(hass: HomeAssistant) -> None:
    """Values from now on are pre-filled and replace the current values."""
    entry = make_entry(("heat_pump", HEAT_PUMP_DATA))
    await setup_entry(hass, entry)
    result = await _reconfigure(hass, entry, "heat_pump", "now")
    assert result["step_id"] == "now_gas"
    assert _suggested(result)["gas_price"] == 0.10
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"gas_price": 0, "scop": 4.0}
    )
    assert result["errors"] == {"gas_price": "value_required"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"gas_price": 0.13, "scop": 4.0, "gas_price_entity": "sensor.gas"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "values_from"
    assert result["description_placeholders"]["time"]
    data = _data(entry, "heat_pump")
    assert data["current"] == {"price": 0.13, "scop": 4.0, "price_entity": "sensor.gas"}
    assert data["before"] == HEAT_PUMP_DATA["before"]


async def test_reconfigure_now_keeps_cop_with_heat_meters(hass: HomeAssistant) -> None:
    """With heat meters the COP is not asked from now on, and kept."""
    entry = make_entry(
        ("heat_pump", {**HEAT_PUMP_DATA, "heat_meters": ["sensor.heat"]})
    )
    await setup_entry(hass, entry)
    result = await _reconfigure(hass, entry, "heat_pump", "now")
    assert "scop" not in _fields(result)
    await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"gas_price": 0.12}
    )
    assert _data(entry, "heat_pump")["current"] == {"price": 0.12, "scop": 4.0}


async def test_reconfigure_averages_before(hass: HomeAssistant) -> None:
    """The averages before the setup can be corrected on their own."""
    entry = make_entry(("wallbox", WALLBOX_DATA))
    await setup_entry(hass, entry)
    result = await _reconfigure(hass, entry, "wallbox", "before")
    assert result["step_id"] == "before"
    assert "fuel_price_entity" not in _fields(result)
    assert set(result["description_placeholders"]) == {"since", "until"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**WALLBOX_VALUES, "fuel_price": 1.69}
    )
    assert result["reason"] == "recomputing"
    data = _data(entry, "wallbox")
    assert data["before"]["price"] == 1.69
    assert data["current"] == WALLBOX_DATA["current"]


async def test_reconfigure_meters(hass: HomeAssistant) -> None:
    """Other meters are saved; a new former heating asks for the values again."""
    entry = make_entry(("heat_pump", HEAT_PUMP_DATA))
    await setup_entry(hass, entry)
    result = await _reconfigure(hass, entry, "heat_pump", "meters")
    assert result["step_id"] == "meters"
    assert _suggested(result)["meters"] == ["sensor.heat_pump"]
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"meters": ["sensor.heat_pump", "sensor.washer"], "heating": "gas"},
    )
    assert result["reason"] == "recomputing"
    data = _data(entry, "heat_pump")
    assert data["meters"] == ["sensor.heat_pump", "sensor.washer"]
    assert "investment" not in data

    result = await _reconfigure(hass, entry, "heat_pump", "meters")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"meters": ["sensor.heat_pump"], "heating": "oil"}
    )
    assert result["step_id"] == "heat_pump_values_oil_scop"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"oil_price": 1.05, "scop": 3.6}
    )
    assert result["reason"] == "recomputing"
    data = _data(entry, "heat_pump")
    assert data["heating"] == "oil"
    assert data["before"] == {"price": 1.05, "scop": 3.6}


async def test_reconfigure_meters_needing_cop(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """Meters that now need a COP the category does not have ask for it."""
    import_hourly(hass, "sensor.heat_pump", data_start, [0.0, 1.0, 1.0, 1.0])
    import_hourly(hass, "sensor.heat", data_start, [0.0, 4.0, 4.0, 4.0])
    await async_wait_recording_done(hass)
    values = {"price": 0.1}
    entry = make_entry(
        (
            "heat_pump",
            {
                **HEAT_PUMP_DATA,
                "heat_meters": ["sensor.heat"],
                "before": values,
                "current": values,
            },
        )
    )
    await setup_entry(hass, entry)
    result = await _reconfigure(hass, entry, "heat_pump", "meters")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"meters": ["sensor.heat_pump"], "heating": "gas"}
    )
    assert result["step_id"] == "heat_pump_values_gas_scop"


async def test_reconfigure_pv_and_recompute(hass: HomeAssistant) -> None:
    """The PV plant changes its purchase cost; every category can be recomputed."""
    entry = make_entry(("pv", {"investment": 10000, "setup_at": 0}))
    await setup_entry(hass, entry)
    result = await _reconfigure(hass, entry, "pv", "investment")
    assert _suggested(result)["investment"] == 10000
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["reason"] == "investment_saved"
    assert "investment" not in _data(entry, "pv")

    result = await _reconfigure(hass, entry, "pv", "recompute")
    assert result["step_id"] == "recompute"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["reason"] == "recomputing"
    assert _data(entry, "pv")["recompute"] > 0


async def test_reconfigure_interface_error(hass: HomeAssistant) -> None:
    """A changed energy interface ends reconfiguring."""
    entry = make_entry(("pv", {}))
    await setup_entry(hass, entry)
    subentry = next(iter(entry.subentries.values()))
    with patch(
        "custom_components.energy_payback.config_flow.async_get_energy_setup",
        side_effect=EnergyInterfaceError("moved"),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "pv"),
            context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry.subentry_id},
        )
    assert result["reason"] == "energy_interface"
