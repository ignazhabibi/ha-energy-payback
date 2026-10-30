"""How savings and payback are calculated.

Pure functions without Home Assistant, so the rules can be read and tested on
their own. Energy is in kWh, money in the user's currency.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

HOUR = 3600.0
DAY = 24 * HOUR
YEAR = 365.25 * DAY
# A commissioning date this much before the data begins still counts as covered.
COVERAGE_TOLERANCE = 2 * DAY
# Below this an hour's import is too small to derive a price from its costs.
MIN_PRICED_ENERGY = 0.01


@dataclass(slots=True)
class PriceTimeline:
    """A price the user typed in, each value valid from a point in time.

    A new price applies from the next full hour; what was computed with the
    old one stays, just as the energy dashboard treats a new electricity price.
    """

    points: list[tuple[float, float]] = field(default_factory=list)

    def value_at(self, timestamp: float) -> float | None:
        """Return the price in effect at timestamp."""
        if not self.points:
            return None
        index = bisect_right([start for start, _ in self.points], timestamp)
        # Before the first change the first price counts: the past is computed
        # with the price entered at setup.
        return self.points[max(index - 1, 0)][1]

    def set(self, value: float, valid_from: float) -> bool:
        """Record a new price. Return whether it changed."""
        if self.points and self.points[-1][1] == value:
            return False
        if not self.points:
            valid_from = 0.0
        self.points = [point for point in self.points if point[0] < valid_from]
        self.points.append((valid_from, value))
        return True

    def as_list(self) -> list[list[float]]:
        """Return the timeline for storage."""
        return [[start, value] for start, value in self.points]

    @classmethod
    def from_list(cls, points: Iterable[Sequence[float]]) -> PriceTimeline:
        """Restore a timeline from storage."""
        return cls([(float(start), float(value)) for start, value in points])


def electricity_prices(
    hours: Sequence[float],
    *,
    entity_prices: Mapping[float, float],
    costs: Mapping[float, float],
    energy: Mapping[float, float],
    fixed: float | None,
    last_known: float | None,
) -> list[float | None]:
    """Return the price of grid electricity for each hour.

    In order of preference: the dashboard's price entity, the dashboard's
    costs divided by the imported energy, its fixed price, the last price seen.
    Hours before the first known price take the first known price.
    """
    prices: list[float | None] = []
    previous = last_known
    for hour in hours:
        price = entity_prices.get(hour)
        if (
            price is None
            and hour in costs
            and (kwh := energy.get(hour, 0.0)) >= MIN_PRICED_ENERGY
        ):
            price = costs[hour] / kwh
        if price is None:
            price = fixed if fixed is not None else previous
        prices.append(price)
        if price is not None:
            previous = price
    first = next((price for price in prices if price is not None), None)
    return [first if price is None else price for price in prices]


def pv_saving(
    *,
    solar: float,
    export: float,
    battery_out: float,
    battery_in: float,
    price: float,
    export_revenue: float,
) -> float:
    """Return what the PV plant saved in one hour.

    Without PV and battery all electricity used in the house would come from
    the grid and nothing would be fed in. The battery belongs to the PV plant:
    what it gives back is valued when it is used.
    """
    self_used = solar - export + battery_out - battery_in
    return self_used * price + export_revenue


def heat_pump_saving(
    *,
    electricity: float,
    heat: float | None,
    scop: float,
    boiler_efficiency: float,
    gas_price: float,
    electricity_price: float,
) -> float:
    """Return what the heat pump saved in one hour, compared with a gas boiler.

    Measured heat is used when there is any; otherwise heat is estimated from
    electricity and SCOP. boiler_efficiency is a fraction, not a percentage.
    """
    if heat is None:
        heat = electricity * scop
    gas = heat / boiler_efficiency
    return gas * gas_price - electricity * electricity_price


def wallbox_saving(
    *,
    electricity: float,
    ev_consumption: float,
    combustion_consumption: float,
    fuel_price: float,
    electricity_price: float,
) -> float:
    """Return what charging at home saved in one hour, compared with a combustion car.

    Consumptions are per 100 km: kWh for the electric car, measured at the
    wallbox, and litres for the combustion car.
    """
    distance = electricity / ev_consumption * 100
    fuel = distance * combustion_consumption / 100
    return fuel * fuel_price - electricity * electricity_price


def effective_meters(
    selected: Iterable[str], parents: Mapping[str, str | None]
) -> list[str]:
    """Drop meters already contained in another selected meter.

    The energy dashboard records with included_in_stat that a device's
    consumption is part of another device's. Counting both would count twice.
    """
    chosen = list(dict.fromkeys(selected))
    result = []
    for meter in chosen:
        parent = parents.get(meter)
        seen = {meter}
        # Walk up until a selected ancestor, the top, or a loop.
        while parent is not None and parent not in chosen and parent not in seen:
            seen.add(parent)
            parent = parents.get(parent)
        if parent is None or parent in seen:
            result.append(meter)
    return result


def is_covered(commissioned: float | None, data_start: float) -> bool:
    """Return whether the data reaches back to the start of operation."""
    return commissioned is None or commissioned >= data_start - COVERAGE_TOLERANCE


@dataclass(frozen=True, slots=True)
class Summary:
    """Payback figures derived from the saving so far."""

    payback: float | None
    """Share of the investment the savings have covered, in percent."""
    per_year: float | None
    """Average saving per year, once there are twelve months of data."""
    yearly_from: float
    """When the yearly average becomes available."""


def summarize(
    *,
    saving: float,
    counting_since: float,
    until: float,
    investment: float | None,
    covered: bool,
) -> Summary:
    """Return payback figures, leaving out what the data cannot support."""
    yearly_from = counting_since + YEAR
    per_year = None
    if until >= yearly_from:
        per_year = saving / ((until - counting_since) / YEAR)
    payback = None
    if covered and investment is not None and investment > 0:
        payback = saving / investment * 100
    return Summary(payback=payback, per_year=per_year, yearly_from=yearly_from)
