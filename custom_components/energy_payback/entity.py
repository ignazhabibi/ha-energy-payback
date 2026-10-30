"""Base entity for Energy Payback."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergyPaybackCoordinator


class EnergyPaybackEntity(CoordinatorEntity[EnergyPaybackCoordinator]):
    """An entity on the overall device or on a category's device.

    Each category is a device of its own, named after the category, so it can
    be put in an area and removed together with its category.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyPaybackCoordinator,
        description: EntityDescription,
        device_id: str,
        device_translation_key: str,
    ) -> None:
        """Initialize the entity for the device device_id."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            entry_type=DeviceEntryType.SERVICE,
            translation_key=device_translation_key,
        )
