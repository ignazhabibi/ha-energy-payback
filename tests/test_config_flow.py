"""Tests for the config flow and the category subentry flows."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_payback.const import DOMAIN
from custom_components.energy_payback.sources import EnergyInterfaceError

from .conftest import PREFS, make_entry, set_energy_prefs, setup_entry

PV_INPUT: dict[str, Any] = {
    "investment": 14500,
    "advanced": {},
}
HEAT_PUMP_INPUT: dict[str, Any] = {
    "meters": ["sensor.heat_pump"],
    "scop": 3.8,
    "gas_price": 0.11,
    "commissioned": "2024-09-01",
    "assumptions": {"boiler_efficiency": 92},
    "advanced": {"gas_price_entity": "input_number.gas_price"},
}
WALLBOX_INPUT: dict[str, Any] = {
    "meters": ["sensor.wallbox"],
    "fuel_price": 1.75,
    "assumptions": {"combustion_consumption": 7, "ev_consumption": 20},
    "advanced": {},
}


@pytest.fixture(autouse=True)
async def energy_prefs(hass: HomeAssistant) -> None:
    """Set up an energy dashboard without statistics."""
    hass.config.currency = "EUR"
    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)


async def test_full_setup(hass: HomeAssistant) -> None:
    """The overview leads through one step per chosen category."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["description_placeholders"] == {
        "price": "0.3 EUR/kWh",
        "feed_in": "0.08 EUR/kWh",
        "solar": "sensor.solar",
        "devices": "Heat pump, Wallbox, Washer",
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": ["pv", "heat_pump", "wallbox"]}
    )
    assert result["step_id"] == "pv"
    assert result["description_placeholders"] == {"data_since": "–"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], PV_INPUT)
    assert result["step_id"] == "heat_pump"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], HEAT_PUMP_INPUT
    )
    assert result["step_id"] == "wallbox"
    with patch("custom_components.energy_payback.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], WALLBOX_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    subentries = {s.subentry_type: s for s in entry.subentries.values()}
    assert subentries["pv"].data == {"investment": 14500}
    assert subentries["pv"].title == "PV plant"
    assert subentries["heat_pump"].data == {
        "meters": ["sensor.heat_pump"],
        "scop": 3.8,
        "gas_price": 0.11,
        "commissioned": "2024-09-01",
        "boiler_efficiency": 92,
        "gas_price_entity": "input_number.gas_price",
    }
    assert subentries["wallbox"].data["fuel_price"] == 1.75


async def test_setup_validation(hass: HomeAssistant) -> None:
    """Missing categories, meters, and future dates are rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": []}
    )
    assert result["errors"] == {"categories": "categories_required"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": ["heat_pump"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**HEAT_PUMP_INPUT, "meters": [], "commissioned": "2999-01-01"},
    )
    assert result["errors"] == {
        "meters": "meters_required",
        "commissioned": "commissioned_in_future",
    }
    with patch("custom_components.energy_payback.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], HEAT_PUMP_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


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


async def test_only_possible_categories_offered(hass: HomeAssistant) -> None:
    """Without individual devices only the PV plant is offered."""
    await set_energy_prefs(hass, {"device_consumption": []})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    schema = result["data_schema"].schema
    selector = next(iter(schema.values()))
    assert selector.config["options"] == ["pv"]


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
    """A category can be added later from the integration page."""
    entry = make_entry(("pv", {}))
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "wallbox"), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**WALLBOX_INPUT, "meters": []}
    )
    assert result["errors"] == {"meters": "meters_required"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], WALLBOX_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {s.subentry_type for s in entry.subentries.values()} == {"pv", "wallbox"}
    assert hass.states.get("sensor.wallbox_saving") is not None


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


async def test_reconfigure_category(hass: HomeAssistant) -> None:
    """Reconfigure opens the category's form pre-filled and saves changes."""
    entry = make_entry(
        (
            "heat_pump",
            {
                "meters": ["sensor.heat_pump"],
                "scop": 3.8,
                "gas_price": 0.11,
                "boiler_efficiency": 90,
            },
        )
    )
    await setup_entry(hass, entry)
    subentry = next(iter(entry.subentries.values()))
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "heat_pump"),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry.subentry_id},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    suggested = {
        str(key): key.description.get("suggested_value")
        for key in result["data_schema"].schema
        if key.description
    }
    assert suggested["gas_price"] == 0.11

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**HEAT_PUMP_INPUT, "commissioned": "2999-01-01"}
    )
    assert result["errors"] == {"commissioned": "commissioned_in_future"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**HEAT_PUMP_INPUT, "gas_price": 0.13}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[subentry.subentry_id].data["gas_price"] == 0.13


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


async def test_grid_choice_with_several_grids(hass: HomeAssistant) -> None:
    """With several priced grid connections the device's tariff can be chosen."""
    second = {
        **PREFS["energy_sources"][0],
        "stat_energy_from": "sensor.heat_pump_tariff",
        "stat_energy_to": None,
        "number_energy_price": 0.24,
        "number_energy_price_export": None,
        "name": "Heat pump tariff",
    }
    await set_energy_prefs(hass, {"energy_sources": [*PREFS["energy_sources"], second]})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"categories": ["heat_pump"]}
    )
    advanced = next(
        value
        for key, value in result["data_schema"].schema.items()
        if key == "advanced"
    )
    assert "grid" in advanced.schema.schema
