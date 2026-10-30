"""Fixtures for Energy Payback tests."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.energy.data import async_get_manager
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_payback.const import (
    CATEGORY_HEAT_PUMP,
    CATEGORY_PV,
    CATEGORY_WALLBOX,
    DOMAIN,
)

HOURS = 48
GRID_PRICE = 0.30
FEED_IN_PRICE = 0.08

PREFS: dict[str, Any] = {
    "energy_sources": [
        {
            "type": "grid",
            "stat_energy_from": "sensor.grid_import",
            "stat_energy_to": "sensor.grid_export",
            "stat_cost": None,
            "stat_compensation": None,
            "entity_energy_price": None,
            "number_energy_price": GRID_PRICE,
            "entity_energy_price_export": None,
            "number_energy_price_export": FEED_IN_PRICE,
            "cost_adjustment_day": 0,
        },
        {
            "type": "solar",
            "stat_energy_from": "sensor.solar",
            "config_entry_solar_forecast": None,
        },
    ],
    "device_consumption": [
        {"stat_consumption": "sensor.heat_pump", "name": "Heat pump"},
        {"stat_consumption": "sensor.wallbox", "name": "Wallbox"},
        {"stat_consumption": "sensor.washer", "name": "Washer"},
    ],
    "device_consumption_water": [],
}

# kWh per hour from the second hour on; the first hour of a statistic has no change.
FLOWS = {
    "sensor.grid_import": 1.0,
    "sensor.grid_export": 0.5,
    "sensor.solar": 2.0,
    "sensor.heat_pump": 0.5,
    "sensor.wallbox": 1.0,
    "sensor.washer": 0.2,
}

PV_DATA: dict[str, Any] = {"investment": 10000}
HEAT_PUMP_DATA: dict[str, Any] = {
    "meters": ["sensor.heat_pump"],
    "scop": 4.0,
    "gas_price": 0.10,
    "boiler_efficiency": 92,
    "investment": 9000,
}
WALLBOX_DATA: dict[str, Any] = {
    "meters": ["sensor.wallbox"],
    "fuel_price": 1.80,
    "ev_consumption": 20,
    "combustion_consumption": 7,
}
# Saving per hour of each category with FLOWS and the data above.
PV_PER_HOUR = (2.0 - 0.5) * GRID_PRICE + 0.5 * FEED_IN_PRICE
HEAT_PUMP_PER_HOUR = 0.5 * 4.0 / 0.92 * 0.10 - 0.5 * GRID_PRICE
WALLBOX_PER_HOUR = 1.0 / 20 * 7 * 1.80 - 1.0 * GRID_PRICE


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    recorder_mock: Any, enable_custom_integrations: None
) -> None:
    """Enable custom integrations and the recorder in all tests.

    The integration depends on the recorder, which must start before hass.
    """


@pytest.fixture
def data_start() -> datetime:
    """Return the start of the first hour of test data."""
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    return now - timedelta(hours=HOURS + 2)


def import_hourly(
    hass: HomeAssistant,
    statistic_id: str,
    start: datetime,
    increments: Sequence[float],
    unit: str = "kWh",
) -> None:
    """Import a sum statistic with these hourly increments."""
    total = 0.0
    rows = []
    for index, increment in enumerate(increments):
        total += increment
        rows.append(
            StatisticData(start=start + timedelta(hours=index), state=total, sum=total)
        )
    async_import_statistics(
        hass,
        StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=None,
            source="recorder",
            statistic_id=statistic_id,
            unit_class="energy" if unit in ("kWh", "Wh", "MWh") else None,
            unit_of_measurement=unit,
        ),
        rows,
    )


def import_hourly_mean(
    hass: HomeAssistant, statistic_id: str, start: datetime, values: Sequence[float]
) -> None:
    """Import a mean statistic, such as a price sensor."""
    async_import_statistics(
        hass,
        StatisticMetaData(
            mean_type=StatisticMeanType.ARITHMETIC,
            has_sum=False,
            name=None,
            source="recorder",
            statistic_id=statistic_id,
            unit_class=None,
            unit_of_measurement="EUR/kWh",
        ),
        [
            StatisticData(
                start=start + timedelta(hours=index),
                mean=value,
                min=value,
                max=value,
            )
            for index, value in enumerate(values)
        ],
    )


async def set_energy_prefs(hass: HomeAssistant, prefs: dict[str, Any]) -> None:
    """Configure the energy dashboard."""
    manager = await async_get_manager(hass)
    await manager.async_update(prefs)  # type: ignore[arg-type]


@pytest.fixture
async def energy(hass: HomeAssistant, data_start: datetime) -> None:
    """Set up an energy dashboard with two days of statistics."""
    hass.config.currency = "EUR"
    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)
    for statistic_id, per_hour in FLOWS.items():
        import_hourly(hass, statistic_id, data_start, [0.0] + [per_hour] * (HOURS - 1))
    await async_wait_recording_done(hass)


def make_entry(*categories: tuple[str, dict[str, Any]]) -> MockConfigEntry:
    """Return a config entry with these categories."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Energy Payback",
        data={},
        subentries_data=[
            ConfigSubentryData(
                subentry_type=category, title=category, data=data, unique_id=category
            )
            for category, data in categories
        ],
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry with all three categories."""
    return make_entry(
        (CATEGORY_PV, PV_DATA),
        (CATEGORY_HEAT_PUMP, HEAT_PUMP_DATA),
        (CATEGORY_WALLBOX, WALLBOX_DATA),
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the entry and wait until the past is computed."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    await async_wait_recording_done(hass)
