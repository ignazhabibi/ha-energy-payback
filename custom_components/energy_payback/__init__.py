"""The Energy Payback integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import CARD_FILENAME, DOMAIN, FRONTEND_URL, SIGNAL_ENERGY_PREFS_UPDATED
from .coordinator import EnergyPaybackConfigEntry, EnergyPaybackCoordinator
from .sources import (
    EnergyInterfaceError,
    async_get_energy_setup,
    async_listen_energy_updates,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the card and follow changes of the energy dashboard."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(Path(__file__).parent / "frontend"))]
    )
    # The version in the URL makes browsers fetch the card again after an update.
    frontend.add_extra_js_url(
        hass, f"{FRONTEND_URL}/{CARD_FILENAME}?v={integration.version}"
    )

    async def _energy_prefs_updated() -> None:
        async_dispatcher_send(hass, SIGNAL_ENERGY_PREFS_UPDATED)

    try:
        await async_listen_energy_updates(hass, _energy_prefs_updated)
    except EnergyInterfaceError:
        # The coordinator raises a repair issue for this on its first update.
        _LOGGER.debug("Cannot follow energy dashboard changes", exc_info=True)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: EnergyPaybackConfigEntry
) -> bool:
    """Set up Energy Payback from a config entry."""
    try:
        await async_get_energy_setup(hass)
    except EnergyInterfaceError as err:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="energy_interface",
            translation_placeholders={"error": str(err)},
        ) from err

    coordinator = EnergyPaybackCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_ENERGY_PREFS_UPDATED, coordinator.async_request_refresh
        )
    )
    # Computing the past can take a moment, so setup does not wait for it.
    # Until then the sensors say that they are calculating.
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), f"{DOMAIN} initial calculation"
    )
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: EnergyPaybackConfigEntry
) -> None:
    """Reload when a category was added, changed, or removed."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: EnergyPaybackConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
