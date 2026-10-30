"""Data classes shared by the coordinator, the sensors, and diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
from typing import Any

from homeassistant.util import dt as dt_util

from .calculation import PriceTimeline
from .const import (
    CATEGORY_HEAT_PUMP,
    CATEGORY_WALLBOX,
    CONF_BOILER_EFFICIENCY,
    CONF_COMBUSTION_CONSUMPTION,
    CONF_COMMISSIONED,
    CONF_EV_CONSUMPTION,
    CONF_FUEL_PRICE,
    CONF_FUEL_PRICE_ENTITY,
    CONF_GAS_PRICE,
    CONF_GAS_PRICE_ENTITY,
    CONF_GRID,
    CONF_HEAT_METERS,
    CONF_INVESTMENT,
    CONF_INVESTMENT_ENTITY,
    CONF_METERS,
    CONF_SCOP,
    DEFAULT_BOILER_EFFICIENCY,
    DEFAULT_COMBUSTION_CONSUMPTION,
    DEFAULT_EV_CONSUMPTION,
    DEFAULT_SCOP,
)


@dataclass(frozen=True, slots=True)
class CategoryConfig:
    """What the user entered for one category."""

    category: str
    commissioned: date | None = None
    investment: float | None = None
    investment_entity: str | None = None
    meters: tuple[str, ...] = ()
    heat_meters: tuple[str, ...] = ()
    scop: float = DEFAULT_SCOP
    boiler_efficiency: float = DEFAULT_BOILER_EFFICIENCY
    combustion_consumption: float = DEFAULT_COMBUSTION_CONSUMPTION
    ev_consumption: float = DEFAULT_EV_CONSUMPTION
    price: float | None = None
    """Gas price per kWh for the heat pump, fuel price per litre for the wallbox."""
    price_entity: str | None = None
    grid: str | None = None
    """Import meter of the grid whose price the device pays."""

    @classmethod
    def from_data(cls, category: str, data: Mapping[str, Any]) -> CategoryConfig:
        """Create from subentry data."""
        commissioned = data.get(CONF_COMMISSIONED)
        price_key, price_entity_key = {
            CATEGORY_HEAT_PUMP: (CONF_GAS_PRICE, CONF_GAS_PRICE_ENTITY),
            CATEGORY_WALLBOX: (CONF_FUEL_PRICE, CONF_FUEL_PRICE_ENTITY),
        }.get(category, ("", ""))
        investment = data.get(CONF_INVESTMENT)
        price = data.get(price_key)
        return cls(
            category=category,
            commissioned=date.fromisoformat(commissioned) if commissioned else None,
            investment=float(investment) if investment is not None else None,
            investment_entity=data.get(CONF_INVESTMENT_ENTITY) or None,
            meters=tuple(data.get(CONF_METERS, ())),
            heat_meters=tuple(data.get(CONF_HEAT_METERS, ())),
            scop=float(data.get(CONF_SCOP, DEFAULT_SCOP)),
            boiler_efficiency=float(
                data.get(CONF_BOILER_EFFICIENCY, DEFAULT_BOILER_EFFICIENCY)
            ),
            combustion_consumption=float(
                data.get(CONF_COMBUSTION_CONSUMPTION, DEFAULT_COMBUSTION_CONSUMPTION)
            ),
            ev_consumption=float(data.get(CONF_EV_CONSUMPTION, DEFAULT_EV_CONSUMPTION)),
            price=float(price) if price is not None else None,
            price_entity=data.get(price_entity_key) or None,
            grid=data.get(CONF_GRID) or None,
        )

    @property
    def commissioned_ts(self) -> float | None:
        """Return the start of the commissioning day as a timestamp."""
        if self.commissioned is None:
            return None
        return dt_util.start_of_local_day(self.commissioned).timestamp()

    @property
    def fingerprint(self) -> str:
        """Identify the settings that change the computed past.

        Fixed prices and investments are left out: they apply from now on.
        Everything else was simply wrong before, so the past is recomputed.
        """
        relevant = {
            "commissioned": self.commissioned.isoformat()
            if self.commissioned
            else None,
            "meters": sorted(self.meters),
            "heat_meters": sorted(self.heat_meters),
            "scop": self.scop,
            "boiler_efficiency": self.boiler_efficiency,
            "combustion_consumption": self.combustion_consumption,
            "ev_consumption": self.ev_consumption,
            "price_entity": self.price_entity,
            "grid": self.grid,
        }
        encoded = json.dumps(relevant, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]


@dataclass(slots=True)
class CategoryState:
    """The persisted progress of one category."""

    fingerprint: str = ""
    data_start: float | None = None
    next_hour: float | None = None
    """Start of the next hour to compute; None before the past is computed."""
    saving: float = 0.0
    last_price: float | None = None
    prices: PriceTimeline = field(default_factory=PriceTimeline)

    def reset(self, fingerprint: str) -> None:
        """Forget the computed past, keeping the price history."""
        self.fingerprint = fingerprint
        self.data_start = None
        self.next_hour = None
        self.saving = 0.0
        self.last_price = None

    def as_dict(self) -> dict[str, Any]:
        """Return the state for storage."""
        return {
            "fingerprint": self.fingerprint,
            "data_start": self.data_start,
            "next_hour": self.next_hour,
            "saving": self.saving,
            "last_price": self.last_price,
            "prices": self.prices.as_list(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CategoryState:
        """Restore the state from storage."""
        return cls(
            fingerprint=data.get("fingerprint", ""),
            data_start=data.get("data_start"),
            next_hour=data.get("next_hour"),
            saving=float(data.get("saving", 0.0)),
            last_price=data.get("last_price"),
            prices=PriceTimeline.from_list(data.get("prices", [])),
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
    commissioned: date | None = None
    covered: bool = True
    yearly_from: datetime | None = None
    price: float | None = None
    """The assumed gas or fuel price in effect now."""

    @property
    def balance_ready(self) -> bool:
        """Return whether this category can take part in the overall balance."""
        return not self.calculating and self.saving is not None and self.covered


@dataclass(frozen=True, slots=True)
class PaybackData:
    """Coordinator data: one result per category, keyed by subentry id."""

    categories: dict[str, CategoryResult] = field(default_factory=dict)

    @property
    def balance(self) -> float | None:
        """Return all savings minus all investments.

        Unknown while any category is still calculating or its data does not
        reach back to its start of operation.
        """
        results = list(self.categories.values())
        if not results or not all(result.balance_ready for result in results):
            return None
        return sum(
            (result.saving or 0.0) - (result.investment or 0.0) for result in results
        )
