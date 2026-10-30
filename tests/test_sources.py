"""Tests for reading the energy dashboard and the recorder."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_payback.sources import (
    EnergyInterfaceError,
    EnergySetup,
    GridSource,
    async_end_of_data,
    async_first_hour,
    async_get_energy_setup,
    async_hourly_changes,
    async_hourly_values,
    async_listen_energy_updates,
    cost_stat,
    parse_preferences,
)

from .conftest import PREFS, import_hourly, import_hourly_mean


def test_parse_unified_grid() -> None:
    """The current grid format gives import, export, and prices."""
    setup = parse_preferences(PREFS)
    grid = setup.grid()
    assert grid is not None
    assert grid.import_stat == "sensor.grid_import"
    assert grid.export_stat == "sensor.grid_export"
    assert grid.price == 0.30
    assert grid.export_price == 0.08
    assert setup.solar == ("sensor.solar",)
    assert setup.device("sensor.wallbox") is not None
    assert setup.device("sensor.unknown") is None
    assert setup.is_usable


def test_parse_legacy_grid_and_battery() -> None:
    """The grid format before 2025.12 and batteries are understood."""
    setup = parse_preferences(
        {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {
                            "stat_energy_from": "sensor.import",
                            "stat_cost": "sensor.import_cost",
                            "entity_energy_price": None,
                            "number_energy_price": None,
                        }
                    ],
                    "flow_to": [
                        {
                            "stat_energy_to": "sensor.export",
                            "stat_compensation": None,
                            "entity_energy_price": "sensor.feed_in",
                            "number_energy_price": None,
                        }
                    ],
                    "cost_adjustment_day": 0,
                },
                {
                    "type": "battery",
                    "stat_energy_from": "sensor.discharge",
                    "stat_energy_to": "sensor.charge",
                },
                {"type": "gas", "stat_energy_from": "sensor.gas"},
            ],
            "device_consumption": [
                {"stat_consumption": "sensor.heating", "included_in_stat": "sensor.hp"}
            ],
        }
    )
    assert setup.grids[0].import_stat == "sensor.import"
    assert setup.grids[0].cost_stat == "sensor.import_cost"
    assert setup.grids[1].export_stat == "sensor.export"
    assert setup.grids[1].export_price_entity == "sensor.feed_in"
    assert setup.batteries[0].charge_stat == "sensor.charge"
    assert setup.devices[0].included_in == "sensor.hp"


def test_parse_errors() -> None:
    """An unexpected format raises instead of guessing."""
    assert parse_preferences(None) == EnergySetup()
    with pytest.raises(EnergyInterfaceError):
        parse_preferences({"energy_sources": [{"type": "solar"}]})


def test_grid_selection() -> None:
    """The chosen grid is used, or the first one with a price."""
    unpriced = GridSource("sensor.a", None, None, None, None, None, None, None)
    priced = GridSource("sensor.b", None, None, None, None, 0.3, None, None)
    setup = EnergySetup(grids=(unpriced, priced))
    assert setup.grid() is priced
    assert setup.grid("sensor.b") is priced
    assert setup.grid("sensor.a") is priced
    assert EnergySetup().grid() is None


async def test_energy_manager_moved(hass: HomeAssistant) -> None:
    """A moved energy module surfaces as EnergyInterfaceError."""
    with (
        patch.dict("sys.modules", {"homeassistant.components.energy.data": None}),
        pytest.raises(EnergyInterfaceError),
    ):
        await async_get_energy_setup(hass)


async def test_energy_manager_changed(hass: HomeAssistant) -> None:
    """A manager without the expected attributes surfaces as EnergyInterfaceError."""
    with (
        patch(
            "homeassistant.components.energy.data.async_get_manager",
            return_value=object(),
        ),
        pytest.raises(EnergyInterfaceError),
    ):
        await async_get_energy_setup(hass)
    with (
        patch(
            "homeassistant.components.energy.data.async_get_manager",
            return_value=object(),
        ),
        pytest.raises(EnergyInterfaceError),
    ):
        await async_listen_energy_updates(hass, lambda: None)  # type: ignore[arg-type,return-value]


async def test_cost_stat(hass: HomeAssistant) -> None:
    """The energy dashboard's own cost sensor is found, or its default name."""
    assert cost_stat(hass, "sensor.grid", compensation=False) == "sensor.grid_cost"
    assert cost_stat(hass, "external:grid", compensation=True) is None
    assert await async_setup_component(hass, "energy", {})
    hass.data["energy"]["cost_sensors"]["sensor.grid"] = "sensor.renamed_cost"
    assert cost_stat(hass, "sensor.grid", compensation=False) == "sensor.renamed_cost"


async def test_statistics(hass: HomeAssistant, data_start: datetime) -> None:
    """Changes, means, history values, first hour, and end of data."""
    import_hourly(hass, "sensor.meter", data_start + timedelta(hours=2), [0, 1, 2])
    import_hourly_mean(hass, "sensor.price", data_start, [0.3, 0.4])
    await async_wait_recording_done(hass)
    hass.states.async_set("input_number.price", "0.11")
    hass.states.async_set("input_number.broken", "unknown")
    await async_wait_recording_done(hass)

    start = data_start.timestamp()
    end = start + 10 * 3600
    assert await async_hourly_changes(hass, [], start, end) == {}
    changes = await async_hourly_changes(hass, ["sensor.meter"], start, end)
    assert list(changes["sensor.meter"].values())[1:] == [1.0, 2.0]

    assert await async_hourly_values(hass, [], start, end) == {}
    values = await async_hourly_values(
        hass, ["sensor.price", "input_number.price", "input_number.broken"], start, end
    )
    assert values["sensor.price"] == {start: 0.3, start + 3600: 0.4}
    assert values["input_number.broken"] == {}
    # The helper's state only exists from now on, so none of these hours has it.
    assert values["input_number.price"] == {}

    assert await async_first_hour(hass, []) is None
    assert await async_first_hour(hass, ["sensor.none"]) is None
    assert await async_first_hour(hass, ["sensor.meter"]) == start + 2 * 3600
    assert await async_end_of_data(hass, "sensor.none") is None
    assert await async_end_of_data(hass, "sensor.meter") == start + 5 * 3600


async def test_history_values_step(hass: HomeAssistant) -> None:
    """A helper's value is the state in effect at the start of each hour."""
    hass.states.async_set("input_number.price", "0.11")
    hass.states.async_set("input_number.broken", "0.2")
    await async_wait_recording_done(hass)
    hass.states.async_set("input_number.broken", "unknown")
    await async_wait_recording_done(hass)
    start = dt_util.utcnow().timestamp() + 1
    values = await async_hourly_values(
        hass, ["input_number.price", "input_number.broken"], start, start + 2 * 3600
    )
    assert values["input_number.price"] == {start: 0.11, start + 3600: 0.11}
    assert values["input_number.broken"] == {}
