"""Tests for setup, the computed savings, and the sensors."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_payback.const import DOMAIN
from custom_components.energy_payback.sources import EnergyInterfaceError

from .conftest import (
    HEAT_PUMP_PER_HOUR,
    HOURS,
    PREFS,
    PV_PER_HOUR,
    WALLBOX_PER_HOUR,
    import_hourly,
    import_hourly_mean,
    make_entry,
    set_energy_prefs,
    setup_entry,
)

COUNTED = HOURS - 1


def _state(hass: HomeAssistant, entity_id: str) -> Any:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state


@pytest.mark.usefixtures("energy")
async def test_savings(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Each category's saving follows from the energy dashboard's statistics."""
    await setup_entry(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    pv = _state(hass, "sensor.pv_plant_saving")
    assert float(pv.state) == pytest.approx(COUNTED * PV_PER_HOUR)
    assert pv.attributes["unit_of_measurement"] == "EUR"
    assert pv.attributes["category"] == "pv"
    assert pv.attributes["calculating"] is False
    assert pv.attributes["data_complete"] is True
    assert pv.attributes["investment"] == 10000
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(
        COUNTED * HEAT_PUMP_PER_HOUR
    )
    assert float(_state(hass, "sensor.wallbox_saving").state) == pytest.approx(
        COUNTED * WALLBOX_PER_HOUR
    )
    assert float(_state(hass, "sensor.pv_plant_paid_back").state) == pytest.approx(
        COUNTED * PV_PER_HOUR / 10000 * 100
    )
    # No investment, no payback; and no yearly figure after two days.
    assert _state(hass, "sensor.wallbox_paid_back").state == "unknown"
    assert _state(hass, "sensor.pv_plant_saving_per_year").state == "unknown"

    total = COUNTED * (PV_PER_HOUR + HEAT_PUMP_PER_HOUR + WALLBOX_PER_HOUR)
    assert float(_state(hass, "sensor.energy_payback_balance").state) == pytest.approx(
        total - 19000
    )


@pytest.mark.usefixtures("energy")
async def test_devices(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Each category is a device of its subentry."""
    await setup_entry(hass, config_entry)
    devices = dr.async_entries_for_config_entry(
        dr.async_get(hass), config_entry.entry_id
    )
    assert len(devices) == 4
    entity = er.async_get(hass).async_get("sensor.heat_pump_saving")
    assert entity is not None
    assert entity.config_subentry_id in config_entry.subentries


@pytest.mark.usefixtures("energy")
async def test_history_is_written(
    hass: HomeAssistant, config_entry: MockConfigEntry, data_start: datetime
) -> None:
    """The computed past becomes the saving sensor's long-term statistics."""
    await setup_entry(hass, config_entry)
    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        data_start,
        None,
        {"sensor.pv_plant_saving"},
        "hour",
        None,
        {"sum"},
    )
    sums = [row["sum"] for row in rows["sensor.pv_plant_saving"]]
    assert sums[-1] == pytest.approx(COUNTED * PV_PER_HOUR)
    assert sums[1] == pytest.approx(PV_PER_HOUR)


@pytest.mark.usefixtures("energy")
async def test_progress_survives_restart(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A reload continues from the stored progress instead of computing again."""
    await setup_entry(hass, config_entry)
    with patch(
        "custom_components.energy_payback.coordinator.async_hourly_changes"
    ) as changes:
        await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    changes.assert_not_called()
    assert float(_state(hass, "sensor.pv_plant_saving").state) == pytest.approx(
        COUNTED * PV_PER_HOUR
    )


@pytest.mark.usefixtures("energy")
async def test_reconfigure_assumption_recomputes(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A changed assumption computes the past again."""
    await setup_entry(hass, config_entry)
    subentry = next(
        s for s in config_entry.subentries.values() if s.subentry_type == "heat_pump"
    )
    hass.config_entries.async_update_subentry(
        config_entry, subentry, data={**subentry.data, "scop": 3.0}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    expected = COUNTED * (0.5 * 3.0 / 0.92 * 0.10 - 0.5 * 0.30)
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(
        expected
    )


@pytest.mark.usefixtures("energy")
async def test_new_price_applies_from_now_on(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A changed fixed price keeps what was computed."""
    await setup_entry(hass, config_entry)
    before = float(_state(hass, "sensor.heat_pump_saving").state)
    subentry = next(
        s for s in config_entry.subentries.values() if s.subentry_type == "heat_pump"
    )
    hass.config_entries.async_update_subentry(
        config_entry, subentry, data={**subentry.data, "gas_price": 0.20}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(before)
    state = config_entry.runtime_data.states[subentry.subentry_id]
    assert [value for _, value in state.prices.points] == [0.10, 0.20]


@pytest.mark.usefixtures("energy")
async def test_missing_meter_raises_issue(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A meter removed from the energy dashboard raises a repair issue."""
    await setup_entry(hass, config_entry)
    before = float(_state(hass, "sensor.wallbox_saving").state)
    await set_energy_prefs(
        hass,
        {
            "device_consumption": [
                device
                for device in PREFS["device_consumption"]
                if device["stat_consumption"] != "sensor.wallbox"
            ]
        },
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    subentry_id = next(
        s.subentry_id
        for s in config_entry.subentries.values()
        if s.subentry_type == "wallbox"
    )
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"missing_meter_{subentry_id}")
    assert issue is not None
    assert issue.translation_placeholders == {
        "category": "wallbox",
        "meters": "sensor.wallbox",
    }
    # The category keeps its last figures.
    assert float(_state(hass, "sensor.wallbox_saving").state) == before

    await set_energy_prefs(hass, PREFS)
    # Refreshes are debounced; do not wait for the cooldown.
    await config_entry.runtime_data.async_refresh()
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, f"missing_meter_{subentry_id}")
        is None
    )


@pytest.mark.usefixtures("energy")
async def test_no_grid_price_raises_issue(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Without an electricity price the figures stay and an issue is raised."""
    await setup_entry(hass, config_entry)
    grid = {**PREFS["energy_sources"][0], "number_energy_price": None}
    await set_energy_prefs(hass, {"energy_sources": [grid, PREFS["energy_sources"][1]]})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "no_grid_price") is not None
    assert _state(hass, "sensor.pv_plant_saving").state != "unavailable"


@pytest.mark.usefixtures("energy")
async def test_energy_interface_broken(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A changed energy interface fails loudly instead of computing wrong numbers."""
    await setup_entry(hass, config_entry)
    with patch(
        "custom_components.energy_payback.coordinator.async_get_energy_setup",
        side_effect=EnergyInterfaceError("moved"),
    ):
        await config_entry.runtime_data.async_refresh()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "energy_interface") is not None
    assert _state(hass, "sensor.pv_plant_saving").state == "unavailable"


@pytest.mark.usefixtures("energy")
async def test_setup_fails_when_energy_interface_broken(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Setup fails with a clear error when the energy dashboard cannot be read."""

    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.energy_payback.async_get_energy_setup",
        side_effect=EnergyInterfaceError("moved"),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.usefixtures("energy")
async def test_commissioned_before_data(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """A plant older than the data gets no payback and no overall balance."""

    commissioned = (data_start - timedelta(days=400)).date().isoformat()
    entry = make_entry(("pv", {"investment": 10000, "commissioned": commissioned}))
    await setup_entry(hass, entry)
    pv = _state(hass, "sensor.pv_plant_saving")
    assert pv.attributes["data_complete"] is False
    assert float(pv.state) == pytest.approx(COUNTED * PV_PER_HOUR)
    assert _state(hass, "sensor.pv_plant_paid_back").state == "unknown"
    assert _state(hass, "sensor.energy_payback_balance").state == "unknown"


@pytest.mark.usefixtures("energy")
async def test_commissioned_after_data_start(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """Counting starts at the commissioning date when it is later."""

    commissioned = dt_util.as_local(data_start + timedelta(days=1)).date()
    entry = make_entry(("pv", {"commissioned": commissioned.isoformat()}))
    await setup_entry(hass, entry)
    pv = _state(hass, "sensor.pv_plant_saving")
    start = dt_util.start_of_local_day(commissioned)
    end = data_start + timedelta(hours=HOURS)
    assert float(pv.state) == pytest.approx(
        (end - start).total_seconds() / 3600 * PV_PER_HOUR
    )


@pytest.mark.usefixtures("energy")
async def test_unload(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """The entry unloads cleanly."""
    await setup_entry(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.usefixtures("energy")
async def test_card_is_served(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The card is registered as an extra frontend module with its version."""
    await setup_entry(hass, config_entry)
    modules = hass.data["frontend_extra_module_url"]
    assert any(
        url.startswith("/energy_payback_static/energy-payback-card.js?v=")
        for url in modules.urls
    )


async def test_calculating_without_data(hass: HomeAssistant) -> None:
    """A category whose meters have no data yet shows no saving."""

    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)
    await async_wait_recording_done(hass)
    entry = make_entry(("pv", {}))
    await setup_entry(hass, entry)
    pv = _state(hass, "sensor.pv_plant_saving")
    assert pv.state == "unknown"
    assert pv.attributes["calculating"] is False


async def test_prices_from_entities_battery_and_heat_meter(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """Price entities, compensation statistics, a battery, and measured heat."""

    hass.config.currency = "EUR"
    assert await async_setup_component(hass, "energy", {})
    grid = {
        **PREFS["energy_sources"][0],
        "number_energy_price": None,
        "entity_energy_price": "sensor.price",
        "number_energy_price_export": None,
        "stat_compensation": "sensor.feed_in_compensation",
    }
    battery = {
        "type": "battery",
        "stat_energy_from": "sensor.discharge",
        "stat_energy_to": "sensor.charge",
    }
    await set_energy_prefs(
        hass,
        {
            **PREFS,
            "energy_sources": [grid, PREFS["energy_sources"][1], battery],
        },
    )
    flows = {
        "sensor.grid_import": 1.0,
        "sensor.grid_export": 0.5,
        "sensor.solar": 2.0,
        "sensor.discharge": 0.3,
        "sensor.charge": 0.4,
        "sensor.heat_pump": 0.5,
        "sensor.heat": 2.2,
    }
    for statistic_id, per_hour in flows.items():
        import_hourly(hass, statistic_id, data_start, [0.0] + [per_hour] * (HOURS - 1))
    import_hourly(
        hass,
        "sensor.feed_in_compensation",
        data_start,
        [0.0] + [0.05] * (HOURS - 1),
        unit="EUR",
    )
    import_hourly_mean(hass, "sensor.price", data_start, [0.25] * HOURS)
    import_hourly_mean(hass, "sensor.gas_price", data_start, [0.12] * HOURS)
    hass.states.async_set("input_number.heat_pump_cost", "13000")
    await async_wait_recording_done(hass)

    entry = make_entry(
        ("pv", {}),
        (
            "heat_pump",
            {
                "meters": ["sensor.heat_pump"],
                "heat_meters": ["sensor.heat"],
                "gas_price": 0.10,
                "gas_price_entity": "sensor.gas_price",
                "investment": 9000,
                "investment_entity": "input_number.heat_pump_cost",
            },
        ),
    )
    await setup_entry(hass, entry)

    pv_per_hour = (2.0 - 0.5 + 0.3 - 0.4) * 0.25 + 0.05
    assert float(_state(hass, "sensor.pv_plant_saving").state) == pytest.approx(
        COUNTED * pv_per_hour
    )
    hp_per_hour = 2.2 / 0.92 * 0.12 - 0.5 * 0.25
    heat_pump = _state(hass, "sensor.heat_pump_saving")
    assert float(heat_pump.state) == pytest.approx(COUNTED * hp_per_hour)
    assert heat_pump.attributes["investment"] == 13000
    assert heat_pump.attributes["assumed_price"] == 0.10

    # An unavailable investment helper falls back to the fixed amount.
    hass.states.async_set("input_number.heat_pump_cost", "unavailable")
    await entry.runtime_data.async_refresh()
    assert _state(hass, "sensor.heat_pump_saving").attributes["investment"] == 9000


@pytest.mark.usefixtures("energy")
async def test_solar_removed_raises_issue(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A PV plant without solar production in the energy dashboard raises an issue."""
    await setup_entry(hass, config_entry)
    await set_energy_prefs(hass, {"energy_sources": PREFS["energy_sources"][:1]})
    await hass.async_block_till_done(wait_background_tasks=True)
    subentry_id = next(
        s.subentry_id
        for s in config_entry.subentries.values()
        if s.subentry_type == "pv"
    )
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"missing_meter_{subentry_id}")
    assert issue is not None
    assert issue.translation_placeholders == {"category": "pv", "meters": "solar"}


async def test_meter_without_data(hass: HomeAssistant, data_start: datetime) -> None:
    """A category whose meters have no data yet is not shown as calculating."""

    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)
    import_hourly(hass, "sensor.grid_import", data_start, [0.0, 1.0, 1.0])
    await async_wait_recording_done(hass)
    await setup_entry(hass, make_entry(("wallbox", WALLBOX_DATA_FOR_TEST)))
    wallbox = _state(hass, "sensor.wallbox_saving")
    assert wallbox.state == "unknown"
    assert wallbox.attributes["calculating"] is False


WALLBOX_DATA_FOR_TEST = {"meters": ["sensor.wallbox"], "fuel_price": 1.8}
