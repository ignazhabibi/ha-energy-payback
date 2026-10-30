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
    effective_meters,
    electricity_prices,
    heat_pump_saving,
    is_covered,
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
    ISSUE_NO_GRID_PRICE,
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


def _number(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Return the numeric state of an entity, or None."""
    if entity_id is None or (state := hass.states.get(entity_id)) is None:
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


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
        """Restore progress and apply changed settings."""
        stored = await self._store.async_load() or {}
        stored_categories: dict[str, Any] = stored.get("categories", {})
        next_full_hour = _ceil_hour(time() + 1)
        for subentry_id, subentry in self.config_entry.subentries.items():
            config = CategoryConfig.from_data(subentry.subentry_type, subentry.data)
            state = CategoryState.from_dict(stored_categories.get(subentry_id, {}))
            if state.fingerprint != config.fingerprint:
                state.reset(config.fingerprint)
            if config.price is not None:
                state.prices.set(config.price, next_full_hour)
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

        counting_since = _ceil_hour(max(state.data_start, config.commissioned_ts or 0))
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
        grid = setup.grid(None if config.category == CATEGORY_PV else config.grid)
        assert grid is not None and grid.import_stat is not None
        grids = setup.grids if config.category == CATEGORY_PV else (grid,)
        meters = self._key_stats(config, setup)

        sums: set[str] = set(meters) | set(config.heat_meters)
        values: set[str] = {
            entity for entity in (config.price_entity,) if entity is not None
        }
        for source in grids:
            sums |= _grid_sums(self.hass, source)
            values |= {
                entity
                for entity in (source.price_entity, source.export_price_entity)
                if entity is not None
            }
        if config.category == CATEGORY_PV:
            for battery in setup.batteries:
                sums |= {battery.discharge_stat, battery.charge_stat}
        changes = await async_hourly_changes(self.hass, sums, start, end)
        entity_values = await async_hourly_values(self.hass, values, start, end)

        prices = self._import_prices(grid, hours, changes, entity_values, state)

        def change(stat: str, hour: float) -> float:
            return changes.get(stat, {}).get(hour, 0.0)

        history: list[tuple[float, float]] = []
        if config.category == CATEGORY_PV:
            export_prices = {
                source: _export_prices(self.hass, source, hours, changes, entity_values)
                for source in grids
                if source.export_stat is not None
            }
            for index, hour in enumerate(hours):
                state.saving += pv_saving(
                    solar=sum(change(stat, hour) for stat in setup.solar),
                    export=sum(
                        change(source.export_stat, hour)
                        for source in export_prices
                        if source.export_stat
                    ),
                    battery_out=sum(
                        change(b.discharge_stat, hour) for b in setup.batteries
                    ),
                    battery_in=sum(
                        change(b.charge_stat, hour) for b in setup.batteries
                    ),
                    price=prices[index] or 0.0,
                    export_revenue=sum(
                        change(source.export_stat, hour) * (rates[index] or 0.0)
                        for source, rates in export_prices.items()
                        if source.export_stat
                    ),
                )
                history.append((hour, state.saving))
            return history

        alternative = entity_values.get(config.price_entity or "", {})
        for index, hour in enumerate(hours):
            electricity = sum(change(meter, hour) for meter in meters)
            price = alternative.get(hour, state.prices.value_at(hour) or 0.0)
            if config.category == CATEGORY_HEAT_PUMP:
                measured = [
                    changes[meter][hour]
                    for meter in config.heat_meters
                    if hour in changes.get(meter, {})
                ]
                state.saving += heat_pump_saving(
                    electricity=electricity,
                    heat=sum(measured) if measured else None,
                    scop=config.scop,
                    boiler_efficiency=config.boiler_efficiency / 100,
                    gas_price=price,
                    electricity_price=prices[index] or 0.0,
                )
            else:
                state.saving += wallbox_saving(
                    electricity=electricity,
                    ev_consumption=config.ev_consumption,
                    combustion_consumption=config.combustion_consumption,
                    fuel_price=price,
                    electricity_price=prices[index] or 0.0,
                )
            history.append((hour, state.saving))
        return history

    def _import_prices(
        self,
        grid: GridSource,
        hours: list[float],
        changes: dict[str, dict[float, float]],
        entity_values: dict[str, dict[float, float]],
        state: CategoryState,
    ) -> list[float | None]:
        assert grid.import_stat is not None
        costs = _cost_stat(self.hass, grid)
        prices = electricity_prices(
            hours,
            entity_prices=entity_values.get(grid.price_entity or "", {}),
            costs=changes.get(costs or "", {}),
            energy=changes.get(grid.import_stat, {}),
            fixed=grid.price,
            last_known=state.last_price,
        )
        if prices and prices[-1] is not None:
            state.last_price = prices[-1]
        return prices

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

    def investment(self, config: CategoryConfig) -> float | None:
        """Return the investment, from its entity if one is set and valid."""
        from_entity = _number(self.hass, config.investment_entity)
        return from_entity if from_entity is not None else config.investment

    def _results(self) -> PaybackData:
        now = time()
        results: dict[str, CategoryResult] = {}
        for subentry_id, config in self.configs.items():
            state = self.states[subentry_id]
            price = _number(self.hass, config.price_entity)
            if price is None:
                price = state.prices.value_at(now)
            if state.data_start is None or state.next_hour is None:
                results[subentry_id] = CategoryResult(
                    category=config.category,
                    calculating=subentry_id not in self._without_data,
                    investment=self.investment(config),
                    commissioned=config.commissioned,
                    price=price,
                )
                continue
            commissioned = config.commissioned_ts
            counting_since = _ceil_hour(max(state.data_start, commissioned or 0))
            covered = is_covered(commissioned, state.data_start)
            investment = self.investment(config)
            summary = summarize(
                saving=state.saving,
                counting_since=counting_since,
                until=state.next_hour,
                investment=investment,
                covered=covered,
            )
            results[subentry_id] = CategoryResult(
                category=config.category,
                calculating=False,
                saving=state.saving,
                investment=investment,
                payback=summary.payback,
                per_year=summary.per_year,
                counting_since=dt_util.utc_from_timestamp(counting_since),
                commissioned=config.commissioned,
                covered=covered,
                yearly_from=dt_util.utc_from_timestamp(summary.yearly_from),
                price=price,
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
