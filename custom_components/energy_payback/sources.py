"""Access to Home Assistant's energy preferences and recorder statistics.

Neither the energy preferences nor the recorder statistics have a public Python
interface. Everything that depends on their internals lives in this module, so
a change in Home Assistant breaks one place, and it breaks loudly with
EnergyInterfaceError instead of producing wrong numbers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import state_changes_during_period
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
    get_metadata,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

ENERGY_DOMAIN = "energy"
HOUR = 3600.0
# Statistics before this date are not looked for.
_EARLIEST = datetime(2000, 1, 1, tzinfo=dt_util.UTC)


class EnergyInterfaceError(Exception):
    """Home Assistant's energy or recorder internals are not as expected."""


@dataclass(frozen=True, slots=True)
class GridSource:
    """One grid connection of the energy dashboard."""

    import_stat: str | None
    export_stat: str | None
    cost_stat: str | None
    compensation_stat: str | None
    price_entity: str | None
    price: float | None
    export_price_entity: str | None
    export_price: float | None
    name: str | None = None

    @property
    def has_import_price(self) -> bool:
        """Return whether the energy dashboard knows what an import costs."""
        return self.import_stat is not None and (
            self.cost_stat is not None
            or self.price_entity is not None
            or self.price is not None
        )


@dataclass(frozen=True, slots=True)
class Battery:
    """One home battery of the energy dashboard."""

    discharge_stat: str
    charge_stat: str


@dataclass(frozen=True, slots=True)
class DeviceMeter:
    """One individual device of the energy dashboard."""

    stat: str
    name: str | None
    included_in: str | None


@dataclass(frozen=True, slots=True)
class EnergySetup:
    """What the energy dashboard knows, reduced to what this integration needs."""

    grids: tuple[GridSource, ...] = ()
    solar: tuple[str, ...] = ()
    batteries: tuple[Battery, ...] = ()
    devices: tuple[DeviceMeter, ...] = ()

    @property
    def priced_grids(self) -> tuple[GridSource, ...]:
        """Return the grid connections with an import meter and a price."""
        return tuple(grid for grid in self.grids if grid.has_import_price)

    @property
    def is_usable(self) -> bool:
        """Return whether there is a grid import with a price."""
        return bool(self.priced_grids)

    def grid(self, import_stat: str | None = None) -> GridSource | None:
        """Return the priced grid with this import meter, or the first one."""
        grids = self.priced_grids
        for grid in grids:
            if grid.import_stat == import_stat:
                return grid
        return grids[0] if grids else None

    def device(self, stat: str) -> DeviceMeter | None:
        """Return the individual device with this meter."""
        return next((device for device in self.devices if device.stat == stat), None)


def _grid_from_unified(source: Mapping[str, Any]) -> GridSource:
    return GridSource(
        import_stat=source.get("stat_energy_from"),
        export_stat=source.get("stat_energy_to"),
        cost_stat=source.get("stat_cost"),
        compensation_stat=source.get("stat_compensation"),
        price_entity=source.get("entity_energy_price"),
        price=source.get("number_energy_price"),
        export_price_entity=source.get("entity_energy_price_export"),
        export_price=source.get("number_energy_price_export"),
        name=source.get("name"),
    )


def _grids_from_legacy(source: Mapping[str, Any]) -> list[GridSource]:
    """Read the grid format used before Home Assistant 2025.12."""
    grids = [
        GridSource(
            import_stat=flow["stat_energy_from"],
            export_stat=None,
            cost_stat=flow.get("stat_cost"),
            compensation_stat=None,
            price_entity=flow.get("entity_energy_price"),
            price=flow.get("number_energy_price"),
            export_price_entity=None,
            export_price=None,
        )
        for flow in source["flow_from"]
    ]
    grids.extend(
        GridSource(
            import_stat=None,
            export_stat=flow["stat_energy_to"],
            cost_stat=None,
            compensation_stat=flow.get("stat_compensation"),
            price_entity=None,
            price=None,
            export_price_entity=flow.get("entity_energy_price"),
            export_price=flow.get("number_energy_price"),
        )
        for flow in source.get("flow_to", [])
    )
    return grids


def parse_preferences(prefs: Mapping[str, Any] | None) -> EnergySetup:
    """Turn the energy dashboard's preferences into an EnergySetup."""
    if prefs is None:
        return EnergySetup()
    try:
        grids: list[GridSource] = []
        solar: list[str] = []
        batteries: list[Battery] = []
        for source in prefs["energy_sources"]:
            match source["type"]:
                case "grid" if "flow_from" in source:
                    grids.extend(_grids_from_legacy(source))
                case "grid":
                    grids.append(_grid_from_unified(source))
                case "solar":
                    solar.append(source["stat_energy_from"])
                case "battery":
                    batteries.append(
                        Battery(source["stat_energy_from"], source["stat_energy_to"])
                    )
        devices = tuple(
            DeviceMeter(
                stat=device["stat_consumption"],
                name=device.get("name"),
                included_in=device.get("included_in_stat"),
            )
            for device in prefs["device_consumption"]
        )
    except (KeyError, TypeError) as err:
        raise EnergyInterfaceError(
            f"Unexpected energy preferences format: {err!r}"
        ) from err
    return EnergySetup(tuple(grids), tuple(solar), tuple(batteries), devices)


async def _async_manager(hass: HomeAssistant) -> Any:
    try:
        # Imported here so that a moved module surfaces as EnergyInterfaceError.
        from homeassistant.components.energy.data import (  # noqa: PLC0415
            async_get_manager,
        )
    except ImportError as err:
        raise EnergyInterfaceError("Energy data manager not found") from err
    return await async_get_manager(hass)


async def async_get_energy_setup(hass: HomeAssistant) -> EnergySetup:
    """Return the current energy dashboard setup."""
    manager = await _async_manager(hass)
    try:
        prefs = manager.data
    except AttributeError as err:
        raise EnergyInterfaceError("Energy preferences not found") from err
    return parse_preferences(prefs)


async def async_listen_energy_updates(
    hass: HomeAssistant, listener: Callable[[], Awaitable[None]]
) -> None:
    """Call listener whenever the energy dashboard is changed.

    The energy manager has no way to stop listening, so register only once.
    """
    manager = await _async_manager(hass)
    try:
        manager.async_listen_updates(listener)
    except AttributeError as err:
        raise EnergyInterfaceError("Energy update listener not found") from err


def cost_stat(hass: HomeAssistant, energy_stat: str, compensation: bool) -> str | None:
    """Return the statistic the energy dashboard keeps the costs in.

    Used when the dashboard was given a price instead of a cost statistic: it
    then creates its own cost sensor.
    """
    cost_sensors: Mapping[str, str] = hass.data.get(ENERGY_DOMAIN, {}).get(
        "cost_sensors", {}
    )
    if (entity_id := cost_sensors.get(energy_stat)) is not None:
        return entity_id
    # Not created yet, for example right after a restart: use the default name.
    suffix = "compensation" if compensation else "cost"
    return f"{energy_stat}_{suffix}" if "." in energy_stat else None


def _rows_to_series(
    rows: Mapping[str, list[Any]], key: str
) -> dict[str, dict[float, float]]:
    series: dict[str, dict[float, float]] = {}
    for stat_id, stat_rows in rows.items():
        values = series.setdefault(stat_id, {})
        for row in stat_rows:
            if (value := row.get(key)) is not None:
                values[float(row["start"])] = float(value)
    return series


async def async_hourly_changes(
    hass: HomeAssistant, stat_ids: Iterable[str], start: float, end: float
) -> dict[str, dict[float, float]]:
    """Return the change per hour of sum statistics, energy in kWh.

    A statistic that missed hours, for example while Home Assistant was off,
    reports the whole difference in its next hour, so nothing is lost.
    """
    ids = set(stat_ids)
    if not ids:
        return {}
    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utc_from_timestamp(start),
        dt_util.utc_from_timestamp(end),
        ids,
        "hour",
        {"energy": "kWh"},
        {"change"},
    )
    return _rows_to_series(rows, "change")


async def async_hourly_values(
    hass: HomeAssistant, entity_ids: Iterable[str], start: float, end: float
) -> dict[str, dict[float, float]]:
    """Return the value per hour of price or amount entities.

    Entities with long-term statistics give their hourly mean. Others, such as
    input_number helpers, give the value at the start of each hour, as far back
    as the recorder keeps their history.
    """
    ids = set(entity_ids)
    if not ids:
        return {}
    instance = get_instance(hass)
    metadata = await instance.async_add_executor_job(
        lambda: get_metadata(hass, statistic_ids=ids)
    )
    with_mean = {
        stat_id
        for stat_id, (_, meta) in metadata.items()
        if meta["mean_type"] != StatisticMeanType.NONE
    }
    values: dict[str, dict[float, float]] = {}
    if with_mean:
        rows = await instance.async_add_executor_job(
            statistics_during_period,
            hass,
            dt_util.utc_from_timestamp(start),
            dt_util.utc_from_timestamp(end),
            with_mean,
            "hour",
            None,
            {"mean"},
        )
        values.update(_rows_to_series(rows, "mean"))
    for entity_id in ids - with_mean:
        states = await instance.async_add_executor_job(
            lambda entity_id=entity_id: state_changes_during_period(
                hass,
                dt_util.utc_from_timestamp(start),
                dt_util.utc_from_timestamp(end),
                entity_id,
                no_attributes=True,
            )
        )
        values[entity_id] = _hourly_steps(states.get(entity_id, []), start, end)
    return values


def _hourly_steps(
    states: Iterable[Any], start: float, end: float
) -> dict[float, float]:
    """Return the numeric state in effect at the start of each hour."""
    changes: list[tuple[float, float | None]] = []
    for state in states:
        try:
            value: float | None = float(state.state)
        except ValueError:
            value = None
        changes.append((state.last_changed.timestamp(), value))
    changes.sort()
    result: dict[float, float] = {}
    index = 0
    current: float | None = None
    hour = start
    while hour < end:
        while index < len(changes) and changes[index][0] <= hour:
            current = changes[index][1]
            index += 1
        if current is not None:
            result[hour] = current
        hour += HOUR
    return result


async def async_first_hour(
    hass: HomeAssistant, stat_ids: Iterable[str]
) -> float | None:
    """Return the start of the first hour any of the statistics has data for."""
    ids = set(stat_ids)
    if not ids:
        return None
    instance = get_instance(hass)
    months = await instance.async_add_executor_job(
        statistics_during_period,
        hass,
        _EARLIEST,
        None,
        ids,
        "month",
        None,
        {"change"},
    )
    starts = [rows[0]["start"] for rows in months.values() if rows]
    if not starts:
        return None
    month_start = dt_util.utc_from_timestamp(min(starts))
    hours = await instance.async_add_executor_job(
        statistics_during_period,
        hass,
        month_start,
        month_start + timedelta(days=32),
        ids,
        "hour",
        None,
        {"change"},
    )
    first = [rows[0]["start"] for rows in hours.values() if rows]
    return float(min(first)) if first else float(min(starts))


async def async_end_of_data(hass: HomeAssistant, stat_id: str) -> float | None:
    """Return the end of the last hour the recorder has compiled for a statistic."""
    rows = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, stat_id, False, {"sum"}
    )
    if not (stat_rows := rows.get(stat_id)):
        return None
    return float(stat_rows[0]["start"]) + HOUR


def async_replace_history(
    hass: HomeAssistant,
    entity_id: str,
    currency: str,
    rows: Iterable[tuple[float, float]],
) -> None:
    """Replace the long-term statistics of a saving sensor with computed values.

    rows holds (hour start, cumulative saving at the end of that hour). The
    recorder then continues from the last row with the sensor's own states.
    Both jobs run in the recorder's queue, in this order.
    """
    get_instance(hass).async_clear_statistics([entity_id])
    metadata = StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=None,
        source="recorder",
        statistic_id=entity_id,
        unit_class=None,
        unit_of_measurement=currency,
    )
    statistics = [
        StatisticData(start=dt_util.utc_from_timestamp(start), state=value, sum=value)
        for start, value in rows
    ]
    if statistics:
        async_import_statistics(hass, metadata, statistics)
