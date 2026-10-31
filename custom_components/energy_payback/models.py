"""Data classes shared by the coordinator, the sensors, and diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from typing import Any

from .calculation import Timeline
from .const import (
    CATEGORY_HEAT_PUMP,
    CATEGORY_WALLBOX,
    CONF_BEFORE,
    CONF_CURRENT,
    CONF_HEAT_METERS,
    CONF_HEATING,
    CONF_INVESTMENT,
    CONF_METERS,
    CONF_RECOMPUTE,
    CONF_SETUP_AT,
    HEATING_GAS,
    VALUE_COMBUSTION_CONSUMPTION,
    VALUE_EV_CONSUMPTION,
    VALUE_PRICE,
    VALUE_PRICE_ENTITY,
    VALUE_SCOP,
    VALUE_TARIFF,
)

# The values each category asks for. They have an average for the time before
# the setup, and a current value with its own timeline after it.
CATEGORY_VALUES: dict[str, tuple[str, ...]] = {
    CATEGORY_HEAT_PUMP: (VALUE_PRICE, VALUE_SCOP, VALUE_TARIFF),
    CATEGORY_WALLBOX: (
        VALUE_EV_CONSUMPTION,
        VALUE_COMBUSTION_CONSUMPTION,
        VALUE_PRICE,
        VALUE_TARIFF,
    ),
}


def _numbers(data: Any) -> dict[str, float]:
    if not isinstance(data, Mapping):
        return {}
    return {
        key: float(value)
        for key, value in data.items()
        if isinstance(value, int | float) and not isinstance(value, bool)
    }


@dataclass(frozen=True, slots=True)
class CategoryConfig:
    """What the user entered for one category."""

    category: str
    investment: float | None = None
    meters: tuple[str, ...] = ()
    heat_meters: tuple[str, ...] = ()
    heating: str = HEATING_GAS
    setup_at: float = 0.0
    before: Mapping[str, float] = field(default_factory=dict)
    current: Mapping[str, float] = field(default_factory=dict)
    price_entity: str | None = None
    recompute: float | None = None

    @classmethod
    def from_data(cls, category: str, data: Mapping[str, Any]) -> CategoryConfig:
        """Create from subentry data."""
        investment = data.get(CONF_INVESTMENT)
        current = data.get(CONF_CURRENT) or {}
        recompute = data.get(CONF_RECOMPUTE)
        return cls(
            category=category,
            investment=float(investment) if investment is not None else None,
            meters=tuple(data.get(CONF_METERS, ())),
            heat_meters=tuple(data.get(CONF_HEAT_METERS, ())),
            heating=data.get(CONF_HEATING, HEATING_GAS),
            setup_at=float(data.get(CONF_SETUP_AT, 0.0)),
            before=_numbers(data.get(CONF_BEFORE)),
            current=_numbers(current),
            price_entity=current.get(VALUE_PRICE_ENTITY) or None,
            recompute=float(recompute) if recompute is not None else None,
        )

    @property
    def values(self) -> tuple[str, ...]:
        """Return the keys of the values this category asks for."""
        return CATEGORY_VALUES.get(self.category, ())

    @property
    def fingerprint(self) -> str:
        """Identify the settings that change the computed past.

        Current values and investments are left out: they apply from now on.
        Meters, the former heating, and the averages before the setup change
        what was computed, so the category is computed again.
        """
        relevant = {
            "meters": sorted(self.meters),
            "heat_meters": sorted(self.heat_meters),
            "heating": self.heating,
            "setup_at": self.setup_at,
            "before": dict(sorted(self.before.items())),
            "recompute": self.recompute,
        }
        encoded = json.dumps(relevant, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]


@dataclass(slots=True)
class CategoryState:
    """The persisted progress of one category."""

    fingerprint: str = ""
    heating: str | None = None
    """The former heating the timelines were recorded for."""
    data_start: float | None = None
    heat_start: float | None = None
    """First hour of heat data; None without heat meters or data."""
    next_hour: float | None = None
    """Start of the next hour to compute; None before the past is computed."""
    saving: float = 0.0
    last_prices: dict[str, float] = field(default_factory=dict)
    """Last electricity price per grid import meter, to bridge gaps."""
    last_entity_price: float | None = None
    measured_heat: float = 0.0
    measured_electricity: float = 0.0
    estimated: bool = False
    """Whether some heat was estimated instead of measured."""
    timelines: dict[str, Timeline] = field(default_factory=dict)

    def reset(self, fingerprint: str) -> None:
        """Forget the computed past, keeping the timelines of current values."""
        self.fingerprint = fingerprint
        self.data_start = None
        self.heat_start = None
        self.next_hour = None
        self.saving = 0.0
        self.last_prices = {}
        self.last_entity_price = None
        self.measured_heat = 0.0
        self.measured_electricity = 0.0
        self.estimated = False

    def timeline(self, key: str) -> Timeline:
        """Return the timeline of a value, creating it if needed."""
        return self.timelines.setdefault(key, Timeline())

    def as_dict(self) -> dict[str, Any]:
        """Return the state for storage."""
        return {
            "fingerprint": self.fingerprint,
            "heating": self.heating,
            "data_start": self.data_start,
            "heat_start": self.heat_start,
            "next_hour": self.next_hour,
            "saving": self.saving,
            "last_prices": self.last_prices,
            "last_entity_price": self.last_entity_price,
            "measured_heat": self.measured_heat,
            "measured_electricity": self.measured_electricity,
            "estimated": self.estimated,
            "timelines": {
                key: timeline.as_list() for key, timeline in self.timelines.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CategoryState:
        """Restore the state from storage."""
        return cls(
            fingerprint=data.get("fingerprint", ""),
            heating=data.get("heating"),
            data_start=data.get("data_start"),
            heat_start=data.get("heat_start"),
            next_hour=data.get("next_hour"),
            saving=float(data.get("saving", 0.0)),
            last_prices=dict(data.get("last_prices", {})),
            last_entity_price=data.get("last_entity_price"),
            measured_heat=float(data.get("measured_heat", 0.0)),
            measured_electricity=float(data.get("measured_electricity", 0.0)),
            estimated=bool(data.get("estimated", False)),
            timelines={
                key: Timeline.from_list(points)
                for key, points in data.get("timelines", {}).items()
            },
        )


@dataclass(frozen=True, slots=True)
class CategoryResult:
    """What the sensors and the card show for one category."""

    category: str
    calculating: bool
    saving: float | None = None
    investment: float | None = None
    payback: float | None = None
    per_year: float | None = None
    counting_since: datetime | None = None
    yearly_from: datetime | None = None
    price: float | None = None
    """The gas, oil, or fuel price in effect now."""
    heating: str | None = None
    heat_estimated: bool | None = None

    @property
    def balance_ready(self) -> bool:
        """Return whether this category can take part in the overall balance."""
        return not self.calculating and self.saving is not None


@dataclass(frozen=True, slots=True)
class PaybackData:
    """Coordinator data: one result per category, keyed by subentry id."""

    categories: dict[str, CategoryResult] = field(default_factory=dict)

    @property
    def balance(self) -> float | None:
        """Return all savings minus all investments.

        Unknown while any category is still calculating or has no data yet.
        """
        results = list(self.categories.values())
        if not results or not all(result.balance_ready for result in results):
            return None
        return sum(
            (result.saving or 0.0) - (result.investment or 0.0) for result in results
        )
