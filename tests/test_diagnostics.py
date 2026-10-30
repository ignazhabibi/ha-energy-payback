"""Tests for diagnostics."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_payback.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.energy_payback.sources import EnergyInterfaceError

from .conftest import setup_entry


@pytest.mark.usefixtures("energy")
async def test_diagnostics(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Diagnostics show settings, the energy dashboard, and progress."""
    await setup_entry(hass, config_entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["currency"] == "EUR"
    assert diagnostics["energy_dashboard"]["solar"] == ("sensor.solar",)
    categories = {c["type"]: c for c in diagnostics["categories"].values()}
    assert categories["pv"]["data"] == {"investment": 10000}
    assert categories["pv"]["state"]["saving"] > 0
    assert categories["pv"]["result"]["calculating"] is False
    assert diagnostics["balance"] is not None

    with patch(
        "custom_components.energy_payback.diagnostics.async_get_energy_setup",
        side_effect=EnergyInterfaceError("moved"),
    ):
        diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["energy_dashboard"] == "unavailable: moved"
