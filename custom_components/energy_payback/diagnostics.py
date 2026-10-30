"""Diagnostics for Energy Payback."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import EnergyPaybackConfigEntry
from .sources import EnergyInterfaceError, async_get_energy_setup


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EnergyPaybackConfigEntry
) -> dict[str, Any]:
    """Return what was configured, what the energy dashboard provides, and the progress.

    Nothing here is secret: statistic ids, prices, and amounts the user entered.
    """
    coordinator = entry.runtime_data
    try:
        energy: dict[str, Any] | str = asdict(await async_get_energy_setup(hass))
    except EnergyInterfaceError as err:
        energy = f"unavailable: {err}"
    return {
        "categories": {
            subentry_id: {
                "type": subentry.subentry_type,
                "data": dict(subentry.data),
                "state": coordinator.states[subentry_id].as_dict()
                if subentry_id in coordinator.states
                else None,
                "result": asdict(result)
                if (result := coordinator.data.categories.get(subentry_id))
                else None,
            }
            for subentry_id, subentry in entry.subentries.items()
        },
        "balance": coordinator.data.balance,
        "currency": hass.config.currency,
        "energy_dashboard": energy,
        "last_update_success": coordinator.last_update_success,
    }
