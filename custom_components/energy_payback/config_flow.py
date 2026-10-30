"""Config flow for Energy Payback.

The config entry stands for the whole household. Each category (PV plant,
heat pump, wallbox) is a config subentry with its own device, so categories can
be added, reconfigured, and removed on their own from the integration page.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any, Literal, override

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    DateSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util
import probatio

from .const import (
    CATEGORIES,
    CATEGORY_HEAT_PUMP,
    CATEGORY_PV,
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
    DOMAIN,
    SECTION_ADVANCED,
    SECTION_ASSUMPTIONS,
)
from .sources import (
    EnergyInterfaceError,
    EnergySetup,
    async_first_hour,
    async_get_energy_setup,
)

CONF_CATEGORIES = "categories"
SECTIONS = {
    SECTION_ASSUMPTIONS: (
        CONF_BOILER_EFFICIENCY,
        CONF_COMBUSTION_CONSUMPTION,
        CONF_EV_CONSUMPTION,
    ),
    SECTION_ADVANCED: (
        CONF_GAS_PRICE_ENTITY,
        CONF_FUEL_PRICE_ENTITY,
        CONF_INVESTMENT_ENTITY,
        CONF_GRID,
    ),
}
NOT_FOUND = "–"

VALUE_ENTITY_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["sensor", "input_number", "number"])
)


def _number(
    unit: str | None = None,
    *,
    minimum: float = 0,
    maximum: float | None = None,
    step: float | Literal["any"] = "any",
) -> NumberSelector:
    config = NumberSelectorConfig(min=minimum, step=step, mode=NumberSelectorMode.BOX)
    if maximum is not None:
        config["max"] = maximum
    if unit is not None:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def available_categories(setup: EnergySetup) -> list[str]:
    """Return the categories the energy dashboard has the data for."""
    available = []
    if setup.solar:
        available.append(CATEGORY_PV)
    if setup.devices:
        available.extend((CATEGORY_HEAT_PUMP, CATEGORY_WALLBOX))
    return available


def category_schema(
    hass: HomeAssistant, category: str, setup: EnergySetup
) -> probatio.Schema:
    """Return the form of a category.

    Only what Home Assistant cannot know is asked. Assumptions with sensible
    defaults and taking values from entities are folded away.
    """
    currency = hass.config.currency
    fields: dict[Any, Any] = {}
    assumptions: dict[Any, Any] = {}
    advanced: dict[Any, Any] = {}

    if category != CATEGORY_PV:
        fields[probatio.Required(CONF_METERS)] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(
                        value=device.stat, label=device.name or device.stat
                    )
                    for device in setup.devices
                ],
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    if category == CATEGORY_HEAT_PUMP:
        fields[probatio.Optional(CONF_HEAT_METERS)] = EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="energy", multiple=True)
        )
        fields[probatio.Optional(CONF_SCOP, default=DEFAULT_SCOP)] = _number(
            minimum=1, maximum=10, step=0.1
        )
        fields[probatio.Required(CONF_GAS_PRICE)] = _number(f"{currency}/kWh")
        assumptions[
            probatio.Optional(CONF_BOILER_EFFICIENCY, default=DEFAULT_BOILER_EFFICIENCY)
        ] = _number("%", minimum=50, maximum=110, step=1)
        advanced[probatio.Optional(CONF_GAS_PRICE_ENTITY)] = VALUE_ENTITY_SELECTOR
    if category == CATEGORY_WALLBOX:
        fields[probatio.Required(CONF_FUEL_PRICE)] = _number(f"{currency}/l")
        assumptions[
            probatio.Optional(
                CONF_COMBUSTION_CONSUMPTION, default=DEFAULT_COMBUSTION_CONSUMPTION
            )
        ] = _number("l/100 km", minimum=1, maximum=50, step=0.1)
        assumptions[
            probatio.Optional(CONF_EV_CONSUMPTION, default=DEFAULT_EV_CONSUMPTION)
        ] = _number("kWh/100 km", minimum=5, maximum=100, step=0.1)
        advanced[probatio.Optional(CONF_FUEL_PRICE_ENTITY)] = VALUE_ENTITY_SELECTOR

    fields[probatio.Optional(CONF_INVESTMENT)] = _number(currency, step=1)
    fields[probatio.Optional(CONF_COMMISSIONED)] = DateSelector()
    advanced[probatio.Optional(CONF_INVESTMENT_ENTITY)] = VALUE_ENTITY_SELECTOR
    if category != CATEGORY_PV and len(setup.priced_grids) > 1:
        advanced[probatio.Optional(CONF_GRID)] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(
                        value=grid.import_stat or "",
                        label=grid.name or grid.import_stat or "",
                    )
                    for grid in setup.priced_grids
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

    if assumptions:
        fields[probatio.Required(SECTION_ASSUMPTIONS)] = section(
            probatio.Schema(assumptions), {"collapsed": True}
        )
    fields[probatio.Required(SECTION_ADVANCED)] = section(
        probatio.Schema(advanced), {"collapsed": True}
    )
    return probatio.Schema(fields)


def flatten(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Merge the form's sections into one dict and drop empty values."""
    data = {key: value for key, value in user_input.items() if key not in SECTIONS}
    for name in SECTIONS:
        data.update(user_input.get(name, {}))
    return {key: value for key, value in data.items() if value not in (None, "", [])}


def nest(data: Mapping[str, Any]) -> dict[str, Any]:
    """Split stored data into the form's sections, for pre-filling."""
    nested: dict[str, Any] = {name: {} for name in SECTIONS}
    for key, value in data.items():
        name = next((name for name, keys in SECTIONS.items() if key in keys), None)
        if name is None:
            nested[key] = value
        else:
            nested[name][key] = value
    return nested


def validate(category: str, data: Mapping[str, Any]) -> dict[str, str]:
    """Return form errors."""
    errors: dict[str, str] = {}
    if category != CATEGORY_PV and not data.get(CONF_METERS):
        errors[CONF_METERS] = "meters_required"
    if (commissioned := data.get(CONF_COMMISSIONED)) and date.fromisoformat(
        commissioned
    ) > dt_util.now().date():
        errors[CONF_COMMISSIONED] = "commissioned_in_future"
    return errors


async def async_category_title(hass: HomeAssistant, category: str) -> str:
    """Return the category's name in the system language."""
    translations = await async_get_translations(
        hass, hass.config.language, "config_subentries", [DOMAIN]
    )
    return translations.get(
        f"component.{DOMAIN}.config_subentries.{category}.entry_type", category
    )


def _label(hass: HomeAssistant, entity_id: str | None) -> str:
    if entity_id is None:
        return NOT_FOUND
    if (state := hass.states.get(entity_id)) is not None:
        return state.name
    return entity_id


def _price(
    hass: HomeAssistant, entity: str | None, number: float | None, cost: str | None
) -> str:
    if entity is not None:
        return _label(hass, entity)
    if number is not None:
        return f"{number:g} {hass.config.currency}/kWh"
    return _label(hass, cost)


def found_placeholders(hass: HomeAssistant, setup: EnergySetup) -> dict[str, str]:
    """Describe what was found in the energy dashboard."""
    grid = setup.grid()
    assert grid is not None
    return {
        "price": _price(hass, grid.price_entity, grid.price, grid.cost_stat),
        "feed_in": (
            _price(
                hass,
                grid.export_price_entity,
                grid.export_price,
                grid.compensation_stat,
            )
            if grid.export_stat
            else NOT_FOUND
        ),
        "solar": ", ".join(_label(hass, stat) for stat in setup.solar) or NOT_FOUND,
        "devices": ", ".join(
            device.name or _label(hass, device.stat) for device in setup.devices
        )
        or NOT_FOUND,
    }


async def _async_category_placeholders(
    hass: HomeAssistant, category: str, setup: EnergySetup
) -> dict[str, str]:
    if category != CATEGORY_PV:
        return {}
    first = await async_first_hour(hass, setup.solar)
    since = (
        dt_util.as_local(dt_util.utc_from_timestamp(first)).date().isoformat()
        if first is not None
        else NOT_FOUND
    )
    return {"data_since": since}


class EnergyPaybackConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the household: an overview, then one short step per category."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._setup = EnergySetup()
        self._pending: list[str] = []
        self._subentries: list[ConfigSubentryData] = []

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the categories that can be added later."""
        return dict.fromkeys(CATEGORIES, CategorySubentryFlow)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show what the energy dashboard provides and ask which categories to evaluate."""
        try:
            self._setup = await async_get_energy_setup(self.hass)
        except EnergyInterfaceError:
            return self.async_abort(reason="energy_interface")
        if not self._setup.is_usable:
            return self.async_abort(reason="no_energy_dashboard")
        available = available_categories(self._setup)
        if not available:
            return self.async_abort(reason="nothing_to_evaluate")

        errors: dict[str, str] = {}
        if user_input is not None:
            chosen = user_input.get(CONF_CATEGORIES, [])
            self._pending = [category for category in CATEGORIES if category in chosen]
            if self._pending:
                return await self._async_next_category()
            errors[CONF_CATEGORIES] = "categories_required"

        schema = probatio.Schema(
            {
                probatio.Required(CONF_CATEGORIES, default=available): SelectSelector(
                    SelectSelectorConfig(
                        options=available,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        translation_key=CONF_CATEGORIES,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=found_placeholders(self.hass, self._setup),
        )

    async def _async_next_category(self) -> ConfigFlowResult:
        if not self._pending:
            return self.async_create_entry(
                title="Energy Payback", data={}, subentries=self._subentries
            )
        return await self._async_category(self._pending[0], None)

    async def async_step_pv(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the PV plant's details."""
        return await self._async_category(CATEGORY_PV, user_input)

    async def async_step_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the heat pump's details."""
        return await self._async_category(CATEGORY_HEAT_PUMP, user_input)

    async def async_step_wallbox(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the wallbox's details."""
        return await self._async_category(CATEGORY_WALLBOX, user_input)

    async def _async_category(
        self, category: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = flatten(user_input)
            if not (errors := validate(category, data)):
                self._subentries.append(
                    ConfigSubentryData(
                        subentry_type=category,
                        title=await async_category_title(self.hass, category),
                        data=data,
                        unique_id=category,
                    )
                )
                self._pending.pop(0)
                return await self._async_next_category()
        schema = category_schema(self.hass, category, self._setup)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id=category,
            data_schema=schema,
            errors=errors,
            description_placeholders=await _async_category_placeholders(
                self.hass, category, self._setup
            ),
            last_step=len(self._pending) == 1,
        )


class CategorySubentryFlow(ConfigSubentryFlow):
    """Add a category later, or change one."""

    async def _async_setup(self) -> EnergySetup | SubentryFlowResult:
        try:
            setup = await async_get_energy_setup(self.hass)
        except EnergyInterfaceError:
            return self.async_abort(reason="energy_interface")
        if self._subentry_type not in available_categories(setup):
            return self.async_abort(reason="not_available")
        return setup

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a category."""
        category = self._subentry_type
        if any(
            subentry.subentry_type == category
            for subentry in self._get_entry().subentries.values()
        ):
            return self.async_abort(reason="already_configured")
        setup = await self._async_setup()
        if not isinstance(setup, EnergySetup):
            return setup

        errors: dict[str, str] = {}
        if user_input is not None:
            data = flatten(user_input)
            if not (errors := validate(category, data)):
                return self.async_create_entry(
                    title=await async_category_title(self.hass, category),
                    data=data,
                    unique_id=category,
                )
        schema = category_schema(self.hass, category, setup)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=await _async_category_placeholders(
                self.hass, category, setup
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change a category, pre-filled with its current settings."""
        subentry = self._get_reconfigure_subentry()
        category = subentry.subentry_type
        setup = await self._async_setup()
        if not isinstance(setup, EnergySetup):
            return setup

        errors: dict[str, str] = {}
        if user_input is not None:
            data = flatten(user_input)
            if not (errors := validate(category, data)):
                # The entry's update listener reloads it.
                return self.async_update_and_abort(
                    self._get_entry(), subentry, data=data
                )
        schema = self.add_suggested_values_to_schema(
            category_schema(self.hass, category, setup),
            user_input if user_input is not None else nest(subentry.data),
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
            description_placeholders=await _async_category_placeholders(
                self.hass, category, setup
            ),
        )
