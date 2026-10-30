"""Sensors for Energy Payback."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EnergyPaybackConfigEntry, EnergyPaybackCoordinator
from .entity import EnergyPaybackEntity
from .models import CategoryResult

# Sensors only read the coordinator's data.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class CategorySensorDescription(SensorEntityDescription):
    """Describes a sensor of one category."""

    value_fn: Callable[[CategoryResult], float | None]
    unit_fn: Callable[[str], str]


CATEGORY_SENSORS: tuple[CategorySensorDescription, ...] = (
    CategorySensorDescription(
        key="saving",
        translation_key="saving",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda result: result.saving,
        unit_fn=lambda currency: currency,
    ),
    CategorySensorDescription(
        key="payback",
        translation_key="payback",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda result: result.payback,
        unit_fn=lambda _: PERCENTAGE,
    ),
    CategorySensorDescription(
        key="saving_per_year",
        translation_key="saving_per_year",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda result: result.per_year,
        unit_fn=lambda currency: f"{currency}/a",
    ),
)

BALANCE_SENSOR = SensorEntityDescription(
    key="balance",
    translation_key="balance",
    device_class=SensorDeviceClass.MONETARY,
    state_class=SensorStateClass.TOTAL,
    suggested_display_precision=0,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnergyPaybackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the overall balance and the sensors of each category."""
    coordinator = entry.runtime_data
    async_add_entities([BalanceSensor(coordinator, entry.entry_id)])
    for subentry_id, subentry in entry.subentries.items():
        async_add_entities(
            [
                CategorySensor(
                    coordinator, description, subentry_id, subentry.subentry_type
                )
                for description in CATEGORY_SENSORS
            ],
            config_subentry_id=subentry_id,
        )


class BalanceSensor(EnergyPaybackEntity, SensorEntity):
    """All savings minus all investments."""

    def __init__(self, coordinator: EnergyPaybackCoordinator, entry_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, BALANCE_SENSOR, entry_id, "total")
        self._attr_native_unit_of_measurement = coordinator.hass.config.currency

    @property
    def native_value(self) -> float | None:
        """Return the balance, unknown while it would be misleading."""
        return self.coordinator.data.balance


class CategorySensor(EnergyPaybackEntity, SensorEntity):
    """A figure of one category."""

    entity_description: CategorySensorDescription
    # The card and the more-info dialog read these. They change rarely, and
    # their history is not interesting, so the recorder skips them.
    _unrecorded_attributes = frozenset(
        {
            "category",
            "calculating",
            "counting_since",
            "commissioned",
            "investment",
            "data_complete",
            "yearly_from",
            "assumed_price",
        }
    )

    def __init__(
        self,
        coordinator: EnergyPaybackCoordinator,
        description: CategorySensorDescription,
        subentry_id: str,
        category: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description, subentry_id, category)
        self._subentry_id = subentry_id
        self._category = category
        self._attr_native_unit_of_measurement = description.unit_fn(
            coordinator.hass.config.currency
        )

    @property
    def _result(self) -> CategoryResult | None:
        return self.coordinator.data.categories.get(self._subentry_id)

    @property
    def native_value(self) -> float | None:
        """Return the figure."""
        if (result := self._result) is None:
            return None
        return self.entity_description.value_fn(result)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return since when the saving counts and which assumptions it uses."""
        if self.entity_description.key != "saving" or (result := self._result) is None:
            return None
        return {
            "category": self._category,
            "calculating": result.calculating,
            "counting_since": (
                result.counting_since.isoformat() if result.counting_since else None
            ),
            "commissioned": (
                result.commissioned.isoformat() if result.commissioned else None
            ),
            "investment": result.investment,
            "data_complete": result.covered,
            "yearly_from": result.yearly_from.isoformat()
            if result.yearly_from
            else None,
            "assumed_price": result.price,
        }
