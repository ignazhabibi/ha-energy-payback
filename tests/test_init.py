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
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_payback import coordinator as coordinator_module
from custom_components.energy_payback.calculation import HOUR
from custom_components.energy_payback.const import DOMAIN
from custom_components.energy_payback.coordinator import EnergyPaybackCoordinator
from custom_components.energy_payback.models import CategoryConfig, CategoryState
from custom_components.energy_payback.sources import EnergyInterfaceError

from .conftest import (
    GRID_PRICE,
    HEAT_PUMP_DATA,
    HEAT_PUMP_PER_HOUR,
    HOURS,
    PREFS,
    PV_PER_HOUR,
    WALLBOX_DATA,
    WALLBOX_PER_HOUR,
    import_hourly,
    import_hourly_mean,
    make_entry,
    set_energy_prefs,
    setup_entry,
)

COUNTED = HOURS - 1
# The heat pump uses 0.5 kWh per hour in the test data.
HP_KWH = 0.5


def _heat_pump(**changes: Any) -> tuple[str, dict[str, Any]]:
    return ("heat_pump", {**HEAT_PUMP_DATA, **changes})


def _hp_hour(
    heat: float, gas_price: float, electricity_price: float = GRID_PRICE
) -> float:
    return heat / 0.92 * gas_price - HP_KWH * electricity_price


def _subentry(entry: MockConfigEntry, category: str) -> Any:
    return next(s for s in entry.subentries.values() if s.subentry_type == category)


async def _update(
    hass: HomeAssistant, entry: MockConfigEntry, category: str, **data: Any
) -> None:
    subentry = _subentry(entry, category)
    hass.config_entries.async_update_subentry(
        entry, subentry, data={**subentry.data, **data}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    await hass.async_block_till_done(wait_background_tasks=True)


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
    assert pv.attributes["investment"] == 10000
    assert "price" not in pv.attributes
    heat_pump = _state(hass, "sensor.heat_pump_saving")
    assert float(heat_pump.state) == pytest.approx(COUNTED * HEAT_PUMP_PER_HOUR)
    assert heat_pump.attributes["price"] == 0.10
    assert heat_pump.attributes["heating"] == "gas"
    assert heat_pump.attributes["heat_estimated"] is True
    assert float(_state(hass, "sensor.electric_car_saving").state) == pytest.approx(
        COUNTED * WALLBOX_PER_HOUR
    )
    assert float(_state(hass, "sensor.pv_plant_paid_back").state) == pytest.approx(
        COUNTED * PV_PER_HOUR / 10000 * 100
    )
    # No investment, no payback; and no yearly figure after two days.
    assert _state(hass, "sensor.electric_car_paid_back").state == "unknown"
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
async def test_phases(hass: HomeAssistant, data_start: datetime) -> None:
    """Before the setup the averages count, after it the current values."""
    setup_at = (data_start + timedelta(hours=24)).timestamp()
    entry = make_entry(
        _heat_pump(
            setup_at=setup_at,
            before={"price": 0.10, "scop": 4.0},
            current={"price": 0.20, "scop": 4.0},
        )
    )
    await setup_entry(hass, entry)
    expected = 23 * _hp_hour(2.0, 0.10) + 24 * _hp_hour(2.0, 0.20)
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(
        expected
    )

    # Changed averages compute the time before the setup again.
    await _update(hass, entry, "heat_pump", before={"price": 0.30, "scop": 4.0})
    expected = 23 * _hp_hour(2.0, 0.30) + 24 * _hp_hour(2.0, 0.20)
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(
        expected
    )


@pytest.mark.usefixtures("energy")
async def test_new_value_applies_from_now_on(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A changed current value keeps what was computed."""
    await setup_entry(hass, config_entry)
    before = float(_state(hass, "sensor.heat_pump_saving").state)
    await _update(hass, config_entry, "heat_pump", current={"price": 0.20, "scop": 3.0})
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(before)
    subentry = _subentry(config_entry, "heat_pump")
    state = config_entry.runtime_data.states[subentry.subentry_id]
    assert [value for _, value in state.timeline("price").points] == [0.10, 0.20]
    assert [value for _, value in state.timeline("scop").points] == [4.0, 3.0]
    assert _state(hass, "sensor.heat_pump_saving").attributes["price"] == 0.10


@pytest.mark.usefixtures("energy")
async def test_recompute_keeps_values(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Recompute computes the category again with the recorded values."""
    await setup_entry(hass, config_entry)
    subentry = _subentry(config_entry, "heat_pump")
    before = float(_state(hass, "sensor.heat_pump_saving").state)
    fingerprint = config_entry.runtime_data.states[subentry.subentry_id].fingerprint
    with patch(
        "custom_components.energy_payback.coordinator.async_hourly_changes",
        wraps=coordinator_module.async_hourly_changes,
    ) as changes:
        await _update(hass, config_entry, "heat_pump", recompute=1.0)
    assert changes.called
    state = config_entry.runtime_data.states[subentry.subentry_id]
    assert state.fingerprint != fingerprint
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(before)


@pytest.mark.usefixtures("energy")
async def test_oil_and_own_tariff(hass: HomeAssistant) -> None:
    """Oil is priced per litre; an own tariff replaces the grid price."""
    values = {"price": 1.0, "scop": 4.0, "tariff": 0.20}
    entry = make_entry(_heat_pump(heating="oil", before=values, current=values))
    await setup_entry(hass, entry)
    per_hour = 2.0 / 0.92 / 10 * 1.0 - HP_KWH * 0.20
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(
        COUNTED * per_hour
    )
    assert _state(hass, "sensor.heat_pump_saving").attributes["heating"] == "oil"


@pytest.mark.usefixtures("energy")
async def test_heating_change_starts_values_over(hass: HomeAssistant) -> None:
    """Gas and oil prices are not comparable, so their timeline starts over."""
    entry = make_entry(_heat_pump())
    await setup_entry(hass, entry)
    values = {"price": 1.0, "scop": 4.0}
    await _update(
        hass, entry, "heat_pump", heating="oil", before=values, current=values
    )
    state = entry.runtime_data.states[_subentry(entry, "heat_pump").subentry_id]
    assert [value for _, value in state.timeline("price").points] == [1.0]


async def test_heat_measured_after_estimate(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """Before the heat meter's data the COP estimates, afterwards heat is measured."""
    hass.config.currency = "EUR"
    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)
    for statistic_id in ("sensor.grid_import", "sensor.heat_pump"):
        per_hour = 1.0 if statistic_id == "sensor.grid_import" else HP_KWH
        import_hourly(hass, statistic_id, data_start, [0.0] + [per_hour] * (HOURS - 1))
    import_hourly(
        hass, "sensor.heat", data_start + timedelta(hours=24), [0.0] + [2.2] * 23
    )
    await async_wait_recording_done(hass)
    values = {"price": 0.10, "scop": 3.0}
    entry = make_entry(
        _heat_pump(heat_meters=["sensor.heat"], before=values, current=values)
    )
    await setup_entry(hass, entry)
    expected = 23 * _hp_hour(1.5, 0.10) + _hp_hour(0.0, 0.10) + 23 * _hp_hour(2.2, 0.10)
    heat_pump = _state(hass, "sensor.heat_pump_saving")
    assert float(heat_pump.state) == pytest.approx(expected)
    assert heat_pump.attributes["heat_estimated"] is True


def test_heat_gap_uses_measured_cop() -> None:
    """A gap after the heat meter began uses the COP measured until then."""
    config = CategoryConfig.from_data(
        "heat_pump",
        {**HEAT_PUMP_DATA, "heat_meters": ["sensor.heat"], "before": {"price": 0.1}},
    )
    state = CategoryState()
    changes = {"sensor.heat": {0.0: 4.0}}
    heat = EnergyPaybackCoordinator._heat
    assert heat(config, state, changes, 1.0, 0.0) == 4.0
    assert state.heat_start == 0.0
    assert heat(config, state, changes, 2.0, HOUR) == pytest.approx(8.0)
    assert state.estimated


@pytest.mark.usefixtures("energy")
async def test_price_sensor_after_setup(
    hass: HomeAssistant, data_start: datetime
) -> None:
    """A price sensor counts after the setup; during its gaps its last value."""
    import_hourly_mean(hass, "sensor.gas_price", data_start, [0.12] * 36)
    await async_wait_recording_done(hass)
    setup_at = (data_start + timedelta(hours=12)).timestamp()
    entry = make_entry(
        _heat_pump(
            setup_at=setup_at,
            current={"price": 0.10, "scop": 4.0, "price_entity": "sensor.gas_price"},
        )
    )
    await setup_entry(hass, entry)
    expected = 11 * _hp_hour(2.0, 0.10) + 36 * _hp_hour(2.0, 0.12)
    assert float(_state(hass, "sensor.heat_pump_saving").state) == pytest.approx(
        expected
    )


@pytest.mark.usefixtures("energy")
async def test_missing_price_sensor_raises_issue(hass: HomeAssistant) -> None:
    """A price sensor that no longer exists raises a repair issue."""
    current = {**WALLBOX_DATA["current"], "price_entity": "sensor.gone"}
    entry = make_entry(("wallbox", {**WALLBOX_DATA, "current": current}))
    await setup_entry(hass, entry)
    subentry_id = _subentry(entry, "wallbox").subentry_id
    issue_id = f"missing_price_entity_{subentry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    hass.states.async_set("sensor.gone", "1.7")
    await entry.runtime_data.async_refresh()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert _state(hass, "sensor.electric_car_saving").attributes["price"] == 1.7


@pytest.mark.usefixtures("energy")
async def test_missing_meter_raises_issue(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A meter removed from the energy dashboard raises a repair issue."""
    await setup_entry(hass, config_entry)
    before = float(_state(hass, "sensor.electric_car_saving").state)
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
    assert float(_state(hass, "sensor.electric_car_saving").state) == before

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
    await async_wait_recording_done(hass)

    entry = make_entry(
        ("pv", {"setup_at": 0}),
        _heat_pump(
            heat_meters=["sensor.heat"],
            current={"price": 0.10, "price_entity": "sensor.gas_price"},
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
    assert heat_pump.attributes["investment"] == 9000
    assert heat_pump.attributes["heat_estimated"] is False
    # The sensor has no state, so the entered price is shown.
    assert heat_pump.attributes["price"] == 0.10


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
    await setup_entry(hass, make_entry(("wallbox", WALLBOX_DATA)))
    wallbox = _state(hass, "sensor.electric_car_saving")
    assert wallbox.state == "unknown"
    assert wallbox.attributes["calculating"] is False


async def test_migration(hass: HomeAssistant, data_start: datetime) -> None:
    """Categories of version 1.1 move to the phases of version 1.2."""
    assert await async_setup_component(hass, "energy", {})
    await set_energy_prefs(hass, PREFS)
    hass.states.async_set("input_number.pv_cost", "12174.5")
    # The fuel price sensor is not loaded yet; its statistics are.
    import_hourly_mean(hass, "sensor.diesel", data_start, [1.65])
    await async_wait_recording_done(hass)
    entry = make_entry(
        ("pv", {"investment_entity": "input_number.pv_cost"}),
        (
            "heat_pump",
            {
                "meters": ["sensor.heat_pump"],
                "scop": 3.8,
                "gas_price": 0.1,
                "gas_price_entity": "sensor.gas_price",
                "boiler_efficiency": 92,
                "investment": 13000,
                "commissioned": "2024-09-01",
            },
        ),
        (
            "wallbox",
            {
                "meters": ["sensor.wallbox"],
                "fuel_price": 0,
                "fuel_price_entity": "sensor.diesel",
            },
        ),
        minor_version=1,
    )
    await setup_entry(hass, entry)
    assert entry.minor_version == 2
    pv = _subentry(entry, "pv").data
    assert pv["investment"] == 12174.5
    heat_pump = _subentry(entry, "heat_pump").data
    assert heat_pump["heating"] == "gas"
    assert heat_pump["investment"] == 13000
    assert heat_pump["before"] == {"price": 0.1, "scop": 3.8}
    assert heat_pump["current"]["price_entity"] == "sensor.gas_price"
    assert "commissioned" not in heat_pump
    wallbox = _subentry(entry, "wallbox").data
    assert wallbox["before"]["price"] == 1.65
    assert wallbox["before"]["ev_consumption"] == 20.0


async def test_migration_from_future_version(hass: HomeAssistant) -> None:
    """An entry from a newer version is not touched."""
    entry = make_entry(("pv", {}), version=2)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
