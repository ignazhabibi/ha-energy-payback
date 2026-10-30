"""Tests for the calculation rules."""

from __future__ import annotations

import pytest

from custom_components.energy_payback.calculation import (
    DAY,
    HOUR,
    YEAR,
    PriceTimeline,
    effective_meters,
    electricity_prices,
    heat_pump_saving,
    is_covered,
    pv_saving,
    summarize,
    wallbox_saving,
)


def test_price_timeline() -> None:
    """The first price also covers the past; later prices apply from their start."""
    timeline = PriceTimeline()
    assert timeline.value_at(100) is None
    assert timeline.set(0.11, valid_from=5000)
    assert timeline.value_at(-1) == 0.11
    assert not timeline.set(0.11, valid_from=6000)
    assert timeline.set(0.13, valid_from=7200)
    assert timeline.value_at(7199) == 0.11
    assert timeline.value_at(7200) == 0.13
    # A second change before the first took effect replaces it.
    assert timeline.set(0.14, valid_from=7200)
    assert timeline.points == [(0.0, 0.11), (7200, 0.14)]
    assert PriceTimeline.from_list(timeline.as_list()) == timeline


def test_electricity_prices_order() -> None:
    """Entity price, then costs per kWh, then fixed price, then the last price."""
    hours = [0.0, HOUR, 2 * HOUR, 3 * HOUR]
    prices = electricity_prices(
        hours,
        entity_prices={0.0: 0.40},
        costs={0.0: 9.0, HOUR: 0.6, 2 * HOUR: 0.0},
        energy={0.0: 1.0, HOUR: 2.0, 2 * HOUR: 0.0},
        fixed=None,
        last_known=0.2,
    )
    assert prices == [0.40, 0.3, 0.3, 0.3]

    assert electricity_prices(
        hours[:2], entity_prices={}, costs={}, energy={}, fixed=0.32, last_known=None
    ) == [0.32, 0.32]
    # Hours before the first known price take the first known price.
    assert electricity_prices(
        hours[:2],
        entity_prices={HOUR: 0.25},
        costs={},
        energy={},
        fixed=None,
        last_known=None,
    ) == [0.25, 0.25]
    assert electricity_prices(
        hours[:1], entity_prices={}, costs={}, energy={}, fixed=None, last_known=None
    ) == [None]


def test_pv_saving() -> None:
    """Self-used solar power at the grid price plus feed-in revenue."""
    assert pv_saving(
        solar=5, export=2, battery_out=1, battery_in=1.5, price=0.3, export_revenue=0.16
    ) == pytest.approx(2.5 * 0.3 + 0.16)


def test_heat_pump_saving() -> None:
    """Gas for the same heat minus the heat pump's electricity."""
    assert heat_pump_saving(
        electricity=1,
        heat=None,
        scop=4,
        boiler_efficiency=0.9,
        gas_price=0.09,
        electricity_price=0.3,
    ) == pytest.approx(4 / 0.9 * 0.09 - 0.3)
    measured = heat_pump_saving(
        electricity=1,
        heat=3,
        scop=4,
        boiler_efficiency=1,
        gas_price=0.1,
        electricity_price=0.3,
    )
    assert measured == pytest.approx(0.0)


def test_wallbox_saving() -> None:
    """Fuel for the same distance minus the charging electricity."""
    assert wallbox_saving(
        electricity=20,
        ev_consumption=20,
        combustion_consumption=7,
        fuel_price=1.8,
        electricity_price=0.3,
    ) == pytest.approx(7 * 1.8 - 6)


def test_effective_meters() -> None:
    """A meter contained in another selected meter is not counted twice."""
    parents = {"heating": "total", "water": "total", "total": None, "rod": "heating"}
    assert effective_meters(["heating", "water"], parents) == ["heating", "water"]
    assert effective_meters(["total", "heating", "rod"], parents) == ["total"]
    assert effective_meters(["heating", "rod", "heating"], parents) == ["heating"]
    cycle = {"a": "b", "b": "a"}
    assert effective_meters(["a"], cycle) == ["a"]


def test_is_covered() -> None:
    """Data must reach back to the start of operation, with some tolerance."""
    assert is_covered(None, 1000 * DAY)
    assert is_covered(999 * DAY, 1000 * DAY)
    assert not is_covered(990 * DAY, 1000 * DAY)


def test_summarize() -> None:
    """No yearly average before twelve months, no payback without full data."""
    early = summarize(
        saving=100, counting_since=0, until=100 * DAY, investment=1000, covered=True
    )
    assert early.per_year is None
    assert early.payback == pytest.approx(10)
    assert early.yearly_from == YEAR

    later = summarize(
        saving=3000, counting_since=0, until=2 * YEAR, investment=None, covered=True
    )
    assert later.per_year == pytest.approx(1500)
    assert later.payback is None

    uncovered = summarize(
        saving=3000, counting_since=0, until=2 * YEAR, investment=1000, covered=False
    )
    assert uncovered.payback is None
