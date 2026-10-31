"""The Energy Payback integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

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

from .const import (
    CARD_FILENAME,
    CATEGORY_HEAT_PUMP,
    CATEGORY_WALLBOX,
    CONF_BEFORE,
    CONF_CURRENT,
    CONF_HEAT_METERS,
    CONF_HEATING,
    CONF_INVESTMENT,
    CONF_METERS,
    CONF_SETUP_AT,
    DOMAIN,
    FRONTEND_URL,
    HEATING_GAS,
    SIGNAL_ENERGY_PREFS_UPDATED,
    VALUE_COMBUSTION_CONSUMPTION,
    VALUE_EV_CONSUMPTION,
    VALUE_PRICE,
    VALUE_PRICE_ENTITY,
    VALUE_SCOP,
)
from .coordinator import (
    EnergyPaybackConfigEntry,
    EnergyPaybackCoordinator,
    next_full_hour,
)
from .sources import (
    EnergyInterfaceError,
    async_get_energy_setup,
    async_last_value,
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


OLD_ENTITY_KEYS = ("investment_entity", "gas_price_entity", "fuel_price_entity")


def _migrated_data(
    category: str, old: dict[str, Any], known: dict[str, float], setup_at: float
) -> dict[str, Any]:
    """Convert a category of version 1.1 to the phases of version 1.2.

    The old values become both the averages before the setup and the current
    values. A missing amount or price is taken from the entity it was kept in;
    known holds those entities' values.
    """

    def number(key: str, entity_key: str | None = None) -> float | None:
        value = old.get(key)
        if isinstance(value, int | float) and value > 0:
            return float(value)
        return known.get(old.get(entity_key or "") or "")

    data: dict[str, Any] = {CONF_SETUP_AT: setup_at}
    if (investment := number(CONF_INVESTMENT, "investment_entity")) is not None:
        data[CONF_INVESTMENT] = investment
    values: dict[str, float] = {}
    if category == CATEGORY_HEAT_PUMP:
        data[CONF_METERS] = old.get(CONF_METERS, [])
        data[CONF_HEAT_METERS] = old.get(CONF_HEAT_METERS, [])
        data[CONF_HEATING] = HEATING_GAS
        values = {
            VALUE_PRICE: number("gas_price", "gas_price_entity") or 0.0,
            VALUE_SCOP: number(VALUE_SCOP) or 3.8,
        }
        entity = old.get("gas_price_entity")
    elif category == CATEGORY_WALLBOX:
        data[CONF_METERS] = old.get(CONF_METERS, [])
        values = {
            VALUE_EV_CONSUMPTION: number(VALUE_EV_CONSUMPTION) or 20.0,
            VALUE_COMBUSTION_CONSUMPTION: number(VALUE_COMBUSTION_CONSUMPTION) or 7.0,
            VALUE_PRICE: number("fuel_price", "fuel_price_entity") or 0.0,
        }
        entity = old.get("fuel_price_entity")
    else:
        return data
    data[CONF_BEFORE] = values
    data[CONF_CURRENT] = {**values, **({VALUE_PRICE_ENTITY: entity} if entity else {})}
    return data


async def async_migrate_entry(
    hass: HomeAssistant, entry: EnergyPaybackConfigEntry
) -> bool:
    """Migrate an entry from an older version."""
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        setup_at = next_full_hour()
        for subentry in list(entry.subentries.values()):
            old = dict(subentry.data)
            known = {
                entity_id: value
                for key in OLD_ENTITY_KEYS
                if (entity_id := old.get(key))
                and (value := await async_last_value(hass, entity_id)) is not None
            }
            hass.config_entries.async_update_subentry(
                entry,
                subentry,
                data=_migrated_data(subentry.subentry_type, old, known, setup_at),
            )
        hass.config_entries.async_update_entry(entry, minor_version=2)
        _LOGGER.debug("Migrated to version 1.2")
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EnergyPaybackConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
