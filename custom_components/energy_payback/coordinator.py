"""Coordinator that computes the savings hour by hour from the recorder."""

from __future__ import annotations

from datetime import timedelta
import logging
import math
from time import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .calculation import (
    HOUR,
    average_price,
    effective_meters,
    electricity_prices,
    heat_pump_saving,
    pv_saving,
    summarize,
    wallbox_saving,
)
from .const import (
    CATEGORY_HEAT_PUMP,
    CATEGORY_PV,
    DOMAIN,
    ISSUE_ENERGY_INTERFACE,
    ISSUE_MISSING_METER,
    ISSUE_MISSING_PRICE_ENTITY,
    ISSUE_NO_GRID_PRICE,
    VALUE_COMBUSTION_CONSUMPTION,
    VALUE_EV_CONSUMPTION,
    VALUE_PRICE,
    VALUE_PRICE_ENTITY,
    VALUE_SCOP,
    VALUE_TARIFF,
)
from .models import CategoryConfig, CategoryResult, CategoryState, PaybackData
from .sources import (
    EnergyInterfaceError,
    EnergySetup,
    GridSource,
    async_end_of_data,
    async_first_hour,
    async_get_energy_setup,
    async_hourly_changes,
    async_hourly_values,
    async_replace_history,
    cost_stat,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=15)
# The past is computed in chunks to keep each recorder query small.
CHUNK = 30 * 24 * HOUR
STORAGE_VERSION = 1

type EnergyPaybackConfigEntry = ConfigEntry[EnergyPaybackCoordinator]


def _hours(start: float, end: float) -> list[float]:
    return [start + index * HOUR for index in range(int((end - start) // HOUR))]


def _ceil_hour(timestamp: float) -> float:
    return math.ceil(timestamp / HOUR) * HOUR


def next_full_hour() -> float:
    """Return the start of the next full hour, from when new values apply."""
    return _ceil_hour(time() + 1)


def _number(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return the numeric state of an entity, or None."""
    if entity_id is None or (state := hass.states.get(entity_id)) is None:
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def value_at(
    config: CategoryConfig, state: CategoryState, key: str, hour: float
) -> float | None:
    """Return a value in effect at hour.

    Before the setup the average entered for that time counts, after it the
    current value of that hour.
    """
    if hour < config.setup_at:
        return config.before.get(key)
    value = state.timeline(key).value_at(hour)
    return float(value) if isinstance(value, int | float) else None


def _price_entity_at(state: CategoryState, hour: float) -> str | None:
    entity = state.timeline(VALUE_PRICE_ENTITY).value_at(hour)
    return entity if isinstance(entity, str) else None


class EnergyPaybackCoordinator(DataUpdateCoordinator[PaybackData]):
    """Compute each category's saving from the energy dashboard's statistics.

    Every update continues where the last one stopped, so hours missed while
    Home Assistant was off are caught up. The first update computes the past.
    """

    config_entry: EnergyPaybackConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EnergyPaybackConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.configs: dict[str, CategoryConfig] = {}
        self.states: dict[str, CategoryState] = {}
        self._without_data: set[str] = set()

    async def async_load(self) -> None:
        """Restore progress and record changed current values."""
        stored = await self._store.async_load() or {}
        stored_categories: dict[str, Any] = stored.get("categories", {})
        valid_from = next_full_hour()
        for subentry_id, subentry in self.config_entry.subentries.items():
            config = CategoryConfig.from_data(subentry.subentry_type, subentry.data)
            state = CategoryState.from_dict(stored_categories.get(subentry_id, {}))
            if state.heating != config.heating:
                # Gas prices are per kWh, oil prices per litre: start over.
                state.timelines = {}
                state.heating = config.heating
            if state.fingerprint != config.fingerprint:
                state.reset(config.fingerprint)
            for key in config.values:
                state.timeline(key).set(config.current.get(key), valid_from)
            if config.category != CATEGORY_PV:
                state.timeline(VALUE_PRICE_ENTITY).set(config.price_entity, valid_from)
            self.configs[subentry_id] = config
            self.states[subentry_id] = state
        await self._async_save()
        self.data = self._results()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "categories": {
                    subentry_id: state.as_dict()
                    for subentry_id, state in self.states.items()
                }
            }
        )

    async def _async_update_data(self) -> PaybackData:
        """Compute all hours the recorder has compiled since the last update."""
        try:
            setup = await async_get_energy_setup(self.hass)
        except EnergyInterfaceError as err:
            self._issue(ISSUE_ENERGY_INTERFACE, ISSUE_ENERGY_INTERFACE)
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key=ISSUE_ENERGY_INTERFACE,
                translation_placeholders={"error": str(err)},
            ) from err
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_ENERGY_INTERFACE)

        grid = setup.grid()
        if grid is None or grid.import_stat is None:
            # Keep the last figures until the energy dashboard is fixed.
            self._issue(ISSUE_NO_GRID_PRICE, ISSUE_NO_GRID_PRICE)
            return self._results()
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_NO_GRID_PRICE)

        self._check_price_entities()
        if (end := await async_end_of_data(self.hass, grid.import_stat)) is None:
            # No grid data yet, so there is nothing to compute.
            self._without_data = set(self.configs)
            return self._results()
        for subentry_id, config in self.configs.items():
            await self._async_advance(subentry_id, config, setup, end)
        await self._async_save()
        return self._results()

    def _issue(
        self,
        issue_id: str,
        translation_key: str,
        placeholders: dict[str, str] | None = None,
    ) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=translation_key,
            translation_placeholders=placeholders,
        )

    def _check_price_entities(self) -> None:
        """Raise an issue for price sensors that no longer exist."""
        registry = er.async_get(self.hass)
        for subentry_id, config in self.configs.items():
            issue_id = f"{ISSUE_MISSING_PRICE_ENTITY}_{subentry_id}"
            entity = config.price_entity
            if (
                entity is not None
                and registry.async_get(entity) is None
                and self.hass.states.get(entity) is None
            ):
                # Until it is replaced, its last value counts.
                self._issue(
                    issue_id,
                    ISSUE_MISSING_PRICE_ENTITY,
                    {
                        "category": self.config_entry.subentries[subentry_id].title,
                        "entity": entity,
                    },
                )
            else:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    def _key_stats(self, config: CategoryConfig, setup: EnergySetup) -> list[str]:
        """Return the statistics whose data defines when a category begins."""
        if config.category == CATEGORY_PV:
            return list(setup.solar)
        parents = {device.stat: device.included_in for device in setup.devices}
        return effective_meters(config.meters, parents)

    async def _async_advance(
        self,
        subentry_id: str,
        config: CategoryConfig,
        setup: EnergySetup,
        end: float,
    ) -> None:
        """Compute one category up to end."""
        state = self.states[subentry_id]
        issue_id = f"{ISSUE_MISSING_METER}_{subentry_id}"
        missing = [meter for meter in config.meters if setup.device(meter) is None]
        if config.category == CATEGORY_PV and not setup.solar:
            missing = ["solar"]
        if missing:
            # Keep the last figures until the meter is back or replaced.
            self._issue(
                issue_id,
                ISSUE_MISSING_METER,
                {
                    "category": self.config_entry.subentries[subentry_id].title,
                    "meters": ", ".join(missing),
                },
            )
            return
        ir.async_delete_issue(self.hass, DOMAIN, issue_id)

        if state.data_start is None:
            state.data_start = await async_first_hour(
                self.hass, self._key_stats(config, setup)
            )
            if state.data_start is None:
                self._without_data.add(subentry_id)
                return
        self._without_data.discard(subentry_id)

        counting_since = _ceil_hour(state.data_start)
        computing_past = state.next_hour is None
        start = state.next_hour if state.next_hour is not None else counting_since
        history: list[tuple[float, float]] = []
        while start < end:
            chunk_end = min(start + CHUNK, end)
            history.extend(
                await self._async_compute(config, setup, state, start, chunk_end)
            )
            state.next_hour = start = chunk_end
        if computing_past:
            state.next_hour = max(start, counting_since)
            self._async_write_history(subentry_id, history)

    async def _async_compute(
        self,
        config: CategoryConfig,
        setup: EnergySetup,
        state: CategoryState,
        start: float,
        end: float,
    ) -> list[tuple[float, float]]:
        """Add the saving of the hours from start to end to state.

        Return the cumulative saving at the end of each hour.
        """
        hours = _hours(start, end)
        meters = self._key_stats(config, setup)
        is_pv = config.category == CATEGORY_PV

        sums: set[str] = set(meters) | set(config.heat_meters)
        values: set[str] = set()
        for source in setup.grids:
            sums |= _grid_sums(self.hass, source)
            values |= {
                entity
                for entity in (source.price_entity, source.export_price_entity)
                if entity is not None
            }
        if is_pv:
            for battery in setup.batteries:
                sums |= {battery.discharge_stat, battery.charge_stat}
        elif end > config.setup_at:
            # Price sensors count only after the setup.
            values |= {
                entity
                for _, entity in state.timeline(VALUE_PRICE_ENTITY).points
                if isinstance(entity, str)
            }
        changes = await async_hourly_changes(self.hass, sums, start, end)
        entity_values = await async_hourly_values(self.hass, values, start, end)
        prices = self._grid_prices(setup, hours, changes, entity_values, state)

        def change(stat: str, hour: float) -> float:
            return changes.get(stat, {}).get(hour, 0.0)

        history: list[tuple[float, float]] = []
        if is_pv:
            exporting = [source for source in setup.grids if source.export_stat]
            export_prices = {
                source.export_stat: _export_prices(
                    self.hass, source, hours, changes, entity_values
                )
                for source in exporting
                if source.export_stat is not None
            }
            for index, hour in enumerate(hours):
                state.saving += pv_saving(
                    solar=sum(change(stat, hour) for stat in setup.solar),
                    export=sum(change(stat, hour) for stat in export_prices),
                    battery_out=sum(
                        change(b.discharge_stat, hour) for b in setup.batteries
                    ),
                    battery_in=sum(
                        change(b.charge_stat, hour) for b in setup.batteries
                    ),
                    price=prices[index] or 0.0,
                    export_revenue=sum(
                        change(stat, hour) * (rates[index] or 0.0)
                        for stat, rates in export_prices.items()
                    ),
                )
                history.append((hour, state.saving))
            return history

        def value(key: str, hour: float) -> float | None:
            return value_at(config, state, key, hour)

        for index, hour in enumerate(hours):
            electricity = sum(change(meter, hour) for meter in meters)
            tariff = value(VALUE_TARIFF, hour)
            electricity_price = tariff if tariff is not None else prices[index] or 0.0
            fuel_price = self._fuel_price(config, state, entity_values, hour)
            if config.category == CATEGORY_HEAT_PUMP:
                state.saving += heat_pump_saving(
                    electricity=electricity,
                    heat=self._heat(config, state, changes, electricity, hour),
                    heating=config.heating,
                    fuel_price=fuel_price,
                    electricity_price=electricity_price,
                )
            elif (ev := value(VALUE_EV_CONSUMPTION, hour)) and (
                combustion := value(VALUE_COMBUSTION_CONSUMPTION, hour)
            ) is not None:
                state.saving += wallbox_saving(
                    electricity=electricity,
                    ev_consumption=ev,
                    combustion_consumption=combustion,
                    fuel_price=fuel_price,
                    electricity_price=electricity_price,
                )
            history.append((hour, state.saving))
        return history

    def _fuel_price(
        self,
        config: CategoryConfig,
        state: CategoryState,
        entity_values: dict[str, dict[float, float]],
        hour: float,
    ) -> float:
        """Return the gas, oil, or fuel price of an hour.

        After the setup a price sensor takes precedence. While it has no value,
        its last value counts.
        """
        if hour >= config.setup_at and (entity := _price_entity_at(state, hour)):
            price = entity_values.get(entity, {}).get(hour)
            if price is not None:
                state.last_prices[entity] = price
                return price
            if (last := state.last_prices.get(entity)) is not None:
                return last
        return value_at(config, state, VALUE_PRICE, hour) or 0.0

    @staticmethod
    def _heat(
        config: CategoryConfig,
        state: CategoryState,
        changes: dict[str, dict[float, float]],
        electricity: float,
        hour: float,
    ) -> float:
        """Return the heat of an hour, measured if possible, else estimated.

        An hour counts as measured when every heat meter has data for it.
        Before the first measured hour the seasonal COP entered for that time
        estimates the heat; later gaps use the COP measured until then.
        """
        heat_meters = config.heat_meters
        if heat_meters and all(hour in changes.get(meter, {}) for meter in heat_meters):
            heat = sum(changes[meter][hour] for meter in heat_meters)
            if state.heat_start is None:
                state.heat_start = hour
            state.measured_heat += heat
            state.measured_electricity += electricity
            return heat
        scop = None
        if state.heat_start is None:
            scop = value_at(config, state, VALUE_SCOP, hour)
        if scop is None and state.measured_electricity > 0:
            scop = state.measured_heat / state.measured_electricity
        if scop is None:
            scop = value_at(config, state, VALUE_SCOP, hour) or 0.0
        if electricity:
            state.estimated = True
        return electricity * scop

    def _grid_prices(
        self,
        setup: EnergySetup,
        hours: list[float],
        changes: dict[str, dict[float, float]],
        entity_values: dict[str, dict[float, float]],
        state: CategoryState,
    ) -> list[float | None]:
        """Return the electricity price of each hour over all grid connections."""
        per_grid: list[list[float | None]] = []
        energies: list[dict[float, float]] = []
        for grid in setup.priced_grids:
            assert grid.import_stat is not None
            costs = _cost_stat(self.hass, grid)
            energy = changes.get(grid.import_stat, {})
            prices = electricity_prices(
                hours,
                entity_prices=entity_values.get(grid.price_entity or "", {}),
                costs=changes.get(costs or "", {}),
                energy=energy,
                fixed=grid.price,
                last_known=state.last_prices.get(grid.import_stat),
            )
            if prices and prices[-1] is not None:
                state.last_prices[grid.import_stat] = prices[-1]
            per_grid.append(prices)
            energies.append(energy)
        return [
            average_price(
                [prices[index] for prices in per_grid],
                [energy.get(hour, 0.0) for energy in energies],
            )
            for index, hour in enumerate(hours)
        ]

    def _async_write_history(
        self, subentry_id: str, history: list[tuple[float, float]]
    ) -> None:
        """Give the saving sensor the computed past as long-term statistics."""
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, f"{subentry_id}_saving"
        )
        if entity_id is None:
            return
        async_replace_history(self.hass, entity_id, self.hass.config.currency, history)

    def current_price(
        self, config: CategoryConfig, state: CategoryState
    ) -> float | None:
        """Return the gas, oil, or fuel price in effect now."""
        now = time()
        price = _number(self.hass, _price_entity_at(state, now))
        if price is None:
            price = value_at(config, state, VALUE_PRICE, now)
        return price

    def _results(self) -> PaybackData:
        results: dict[str, CategoryResult] = {}
        for subentry_id, config in self.configs.items():
            state = self.states[subentry_id]
            is_heat_pump = config.category == CATEGORY_HEAT_PUMP
            base: dict[str, Any] = {
                "category": config.category,
                "investment": config.investment,
                "price": None
                if config.category == CATEGORY_PV
                else self.current_price(config, state),
                "heating": config.heating if is_heat_pump else None,
            }
            if state.data_start is None or state.next_hour is None:
                results[subentry_id] = CategoryResult(
                    calculating=subentry_id not in self._without_data, **base
                )
                continue
            counting_since = _ceil_hour(state.data_start)
            summary = summarize(
                saving=state.saving,
                counting_since=counting_since,
                until=state.next_hour,
                investment=config.investment,
            )
            results[subentry_id] = CategoryResult(
                calculating=False,
                saving=state.saving,
                payback=summary.payback,
                per_year=summary.per_year,
                counting_since=dt_util.utc_from_timestamp(counting_since),
                yearly_from=dt_util.utc_from_timestamp(summary.yearly_from),
                heat_estimated=state.estimated if is_heat_pump else None,
                **base,
            )
        return PaybackData(results)


def _cost_stat(hass: HomeAssistant, grid: GridSource) -> str | None:
    if grid.cost_stat is not None or grid.import_stat is None:
        return grid.cost_stat
    if grid.price is None and grid.price_entity is None:
        return None
    return cost_stat(hass, grid.import_stat, compensation=False)


def _compensation_stat(hass: HomeAssistant, grid: GridSource) -> str | None:
    if grid.compensation_stat is not None or grid.export_stat is None:
        return grid.compensation_stat
    if grid.export_price is None and grid.export_price_entity is None:
        return None
    return cost_stat(hass, grid.export_stat, compensation=True)


def _grid_sums(hass: HomeAssistant, grid: GridSource) -> set[str]:
    """Return the sum statistics a grid's prices and flows need."""
    stats = (
        grid.import_stat,
        grid.export_stat,
        _cost_stat(hass, grid),
        _compensation_stat(hass, grid),
    )
    return {stat for stat in stats if stat is not None}


def _export_prices(
    hass: HomeAssistant,
    grid: GridSource,
    hours: list[float],
    changes: dict[str, dict[float, float]],
    entity_values: dict[str, dict[float, float]],
) -> list[float | None]:
    """Return the feed-in compensation per kWh for each hour."""
    assert grid.export_stat is not None
    compensation = _compensation_stat(hass, grid)
    return electricity_prices(
        hours,
        entity_prices=entity_values.get(grid.export_price_entity or "", {}),
        costs=changes.get(compensation or "", {}),
        energy=changes.get(grid.export_stat, {}),
        fixed=grid.export_price,
        last_known=None,
    )
