"""Config flow for Energy Payback.

The config entry stands for the whole household. Each category (PV plant,
heat pump, electric car) is a config subentry with its own device, so
categories can be added, changed, and removed on their own.

Heat pump and electric car are set up in two steps: first the meters, then
the averages for the time since their data begins. That date follows from the
meters, so it can only be shown in the second step.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
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
from homeassistant.helpers.selector import (
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

from .calculation import HOUR
from .const import (
    CATEGORIES,
    CATEGORY_HEAT_PUMP,
    CATEGORY_PV,
    CATEGORY_WALLBOX,
    CONF_BEFORE,
    CONF_CURRENT,
    CONF_HEAT_METERS,
    CONF_HEATING,
    CONF_INVESTMENT,
    CONF_METERS,
    CONF_RECOMPUTE,
    CONF_SETUP_AT,
    DOMAIN,
    HEATING_GAS,
    HEATING_OIL,
    VALUE_COMBUSTION_CONSUMPTION,
    VALUE_EV_CONSUMPTION,
    VALUE_PRICE,
    VALUE_PRICE_ENTITY,
    VALUE_SCOP,
    VALUE_TARIFF,
)
from .coordinator import next_full_hour
from .sources import (
    EnergyInterfaceError,
    EnergySetup,
    async_first_hour,
    async_get_energy_setup,
)

CONF_CATEGORIES = "categories"
# The price fields are named after the former heating, so their label and unit
# fit. They are stored as VALUE_PRICE and VALUE_PRICE_ENTITY.
PRICE_FIELDS = {
    CATEGORY_HEAT_PUMP: {
        HEATING_GAS: ("gas_price", "gas_price_entity"),
        HEATING_OIL: ("oil_price", "oil_price_entity"),
    },
    CATEGORY_WALLBOX: {HEATING_GAS: ("fuel_price", "fuel_price_entity")},
}
PRICE_ENTITY_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["sensor", "input_number", "number"])
)


def _number(
    unit: str | None = None,
    *,
    maximum: float | None = None,
    step: float | Literal["any"] = "any",
) -> NumberSelector:
    config = NumberSelectorConfig(min=0, step=step, mode=NumberSelectorMode.BOX)
    if maximum is not None:
        config["max"] = maximum
    if unit is not None:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def _date(timestamp: float) -> str:
    return dt_util.as_local(dt_util.utc_from_timestamp(timestamp)).strftime("%d.%m.%Y")


def available_categories(setup: EnergySetup) -> list[str]:
    """Return the categories the energy dashboard has the data for."""
    available = []
    if setup.solar:
        available.append(CATEGORY_PV)
    if setup.devices:
        available.extend((CATEGORY_HEAT_PUMP, CATEGORY_WALLBOX))
    return available


async def async_category_title(hass: HomeAssistant, category: str) -> str:
    """Return the category's name in the system language."""
    translations = await async_get_translations(
        hass, hass.config.language, "config_subentries", [DOMAIN]
    )
    return translations.get(
        f"component.{DOMAIN}.config_subentries.{category}.entry_type", category
    )


def overview_placeholders(setup: EnergySetup) -> dict[str, str]:
    """Describe what the energy dashboard provides, one line each."""
    grid = setup.grid()
    exporting = any(source.export_stat for source in setup.grids)
    compensated = any(
        source.export_stat
        and (
            source.export_price is not None
            or source.export_price_entity is not None
            or source.compensation_stat is not None
        )
        for source in setup.grids
    )
    return {
        "grid": "✓" if grid is not None else "–",
        "export": "✓" if exporting else "–",
        "compensation": "✓" if compensated else "–",
        "solar": str(len(setup.solar)),
        "battery": "✓" if setup.batteries else "–",
        "devices": str(len(setup.devices)),
    }


def meter_selector(setup: EnergySetup, taken: Iterable[str]) -> SelectSelector:
    """Offer the individual devices that no other category uses."""
    used = set(taken)
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=device.stat, label=device.name or device.stat)
                for device in setup.devices
                if device.stat not in used
            ],
            multiple=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def investment_schema(hass: HomeAssistant) -> probatio.Schema:
    """Return the form of the PV plant."""
    return probatio.Schema(
        {probatio.Optional(CONF_INVESTMENT): _number(hass.config.currency, step=1)}
    )


def meters_schema(
    hass: HomeAssistant, category: str, setup: EnergySetup, taken: Iterable[str]
) -> probatio.Schema:
    """Return the first step of heat pump and electric car: what is measured."""
    # Fields are optional for the form and checked in validate_meters, so that
    # Home Assistant does not preselect the first option.
    fields: dict[Any, Any] = {
        probatio.Optional(CONF_METERS): meter_selector(setup, taken)
    }
    if category == CATEGORY_HEAT_PUMP:
        fields[probatio.Optional(CONF_HEAT_METERS)] = EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="energy", multiple=True)
        )
        fields[probatio.Optional(CONF_HEATING)] = SelectSelector(
            SelectSelectorConfig(
                options=[HEATING_GAS, HEATING_OIL],
                mode=SelectSelectorMode.LIST,
                translation_key=CONF_HEATING,
            )
        )
    fields[probatio.Optional(CONF_INVESTMENT)] = _number(hass.config.currency, step=1)
    return probatio.Schema(fields)


def validate_meters(category: str, user_input: Mapping[str, Any]) -> dict[str, str]:
    """Return the errors of the first step."""
    errors: dict[str, str] = {}
    if not user_input.get(CONF_METERS):
        errors[CONF_METERS] = "meters_required"
    if category == CATEGORY_HEAT_PUMP and not user_input.get(CONF_HEATING):
        errors[CONF_HEATING] = "heating_required"
    return errors


def meters_data(category: str, user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return the subentry data of the first step."""
    data: dict[str, Any] = {CONF_METERS: list(user_input[CONF_METERS])}
    if category == CATEGORY_HEAT_PUMP:
        data[CONF_HEAT_METERS] = list(user_input.get(CONF_HEAT_METERS, []))
        data[CONF_HEATING] = user_input[CONF_HEATING]
    if (investment := user_input.get(CONF_INVESTMENT)) is not None:
        data[CONF_INVESTMENT] = investment
    return data


def values_schema(
    hass: HomeAssistant,
    category: str,
    heating: str,
    *,
    scop: bool,
    price_entity: bool,
) -> probatio.Schema:
    """Return the form of the values: averages before, or values from now on.

    scop says whether the seasonal COP is needed, price_entity whether a price
    sensor may be chosen (only for the time from the setup on).
    """
    currency = hass.config.currency
    price_key, entity_key = PRICE_FIELDS[category][heating]
    unit = "kWh" if category == CATEGORY_HEAT_PUMP and heating == HEATING_GAS else "l"
    fields: dict[Any, Any] = {}
    if category == CATEGORY_WALLBOX:
        fields[probatio.Required(VALUE_EV_CONSUMPTION)] = _number(
            "kWh/100 km", maximum=100, step=0.1
        )
        fields[probatio.Required(VALUE_COMBUSTION_CONSUMPTION)] = _number(
            "l/100 km", maximum=50, step=0.1
        )
    fields[probatio.Required(price_key)] = _number(f"{currency}/{unit}")
    if scop:
        fields[probatio.Required(VALUE_SCOP)] = _number(maximum=10, step=0.1)
    fields[probatio.Optional(VALUE_TARIFF)] = _number(f"{currency}/kWh")
    if price_entity:
        fields[probatio.Optional(entity_key)] = PRICE_ENTITY_SELECTOR
    return probatio.Schema(fields)


def validate_values(
    category: str, heating: str, user_input: Mapping[str, Any]
) -> dict[str, str]:
    """Return the errors of a values form: everything entered must be above 0."""
    price_key, _ = PRICE_FIELDS[category][heating]
    keys = (
        price_key,
        VALUE_SCOP,
        VALUE_TARIFF,
        VALUE_EV_CONSUMPTION,
        VALUE_COMBUSTION_CONSUMPTION,
    )
    errors = {
        key: "value_required"
        for key in keys
        if key in user_input and not user_input[key] > 0
    }
    if (
        VALUE_SCOP in user_input
        and VALUE_SCOP not in errors
        and user_input[VALUE_SCOP] < 1
    ):
        errors[VALUE_SCOP] = "scop_range"
    return errors


def values_data(
    category: str, heating: str, user_input: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the stored values of a values form."""
    price_key, entity_key = PRICE_FIELDS[category][heating]
    data: dict[str, Any] = {
        key: value
        for key, value in user_input.items()
        if key not in (price_key, entity_key) and value is not None
    }
    data[VALUE_PRICE] = user_input[price_key]
    if entity := user_input.get(entity_key):
        data[VALUE_PRICE_ENTITY] = entity
    return data


def values_form_input(
    category: str, heating: str, values: Mapping[str, Any]
) -> dict[str, Any]:
    """Return stored values as form input, for pre-filling."""
    price_key, entity_key = PRICE_FIELDS[category][heating]
    form = {
        key: value
        for key, value in values.items()
        if key not in (VALUE_PRICE, VALUE_PRICE_ENTITY)
    }
    if VALUE_PRICE in values:
        form[price_key] = values[VALUE_PRICE]
    if VALUE_PRICE_ENTITY in values:
        form[entity_key] = values[VALUE_PRICE_ENTITY]
    return form


async def async_scop_needed(
    hass: HomeAssistant, meters: list[str], heat_meters: list[str]
) -> tuple[bool, float | None]:
    """Return whether heat must be estimated before heat data begins, and until when."""
    if not heat_meters:
        return True, None
    heat_start = await async_first_hour(hass, heat_meters)
    data_start = await async_first_hour(hass, meters)
    if heat_start is None:
        return True, None
    return data_start is not None and data_start + HOUR < heat_start, heat_start


async def async_data_since(hass: HomeAssistant, stats: list[str]) -> float:
    """Return when the data of these meters begins, or now if there is none."""
    first = await async_first_hour(hass, stats)
    return first if first is not None else next_full_hour()


class EnergyPaybackConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the household: an overview, then the chosen categories."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._setup = EnergySetup()
        self._pending: list[str] = []
        self._subentries: list[ConfigSubentryData] = []
        self._data: dict[str, Any] = {}
        self._since = 0.0
        self._scop = False
        self._heat_start: float | None = None

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
        """Show what the energy dashboard provides and ask what to evaluate."""
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
                probatio.Optional(CONF_CATEGORIES): SelectSelector(
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
            step_id=_overview_step(self._setup),
            data_schema=schema,
            errors=errors,
            description_placeholders=overview_placeholders(self._setup),
        )

    async_step_user_no_devices = async_step_user
    async_step_user_no_solar = async_step_user

    async def _async_next_category(self) -> ConfigFlowResult:
        if not self._pending:
            return self.async_create_entry(
                title="Energy Payback", data={}, subentries=self._subentries
            )
        category = self._pending[0]
        if category == CATEGORY_PV:
            return await self.async_step_pv()
        if category == CATEGORY_HEAT_PUMP:
            return await self.async_step_heat_pump()
        return await self.async_step_wallbox()

    async def _async_add(self, category: str, data: dict[str, Any]) -> ConfigFlowResult:
        self._subentries.append(
            ConfigSubentryData(
                subentry_type=category,
                title=await async_category_title(self.hass, category),
                data={CONF_SETUP_AT: next_full_hour(), **data},
                unique_id=category,
            )
        )
        self._pending.pop(0)
        return await self._async_next_category()

    async def async_step_pv(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the PV plant's purchase cost."""
        if user_input is not None:
            return await self._async_add(CATEGORY_PV, dict(user_input))
        return self.async_show_form(
            step_id=_pv_step(self._setup),
            data_schema=investment_schema(self.hass),
            description_placeholders={
                "since": _date(
                    await async_data_since(self.hass, list(self._setup.solar))
                )
            },
            last_step=len(self._pending) == 1,
        )

    async_step_pv_no_export = async_step_pv

    async def async_step_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the heat pump's meters, former heating, and extra cost."""
        return await self._async_meters(CATEGORY_HEAT_PUMP, user_input)

    async def async_step_wallbox(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the charging meters and the car's extra cost."""
        return await self._async_meters(CATEGORY_WALLBOX, user_input)

    def _taken(self) -> list[str]:
        return [
            meter
            for subentry in self._subentries
            for meter in subentry["data"].get(CONF_METERS, [])
        ]

    async def _async_meters(
        self, category: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_meters(category, user_input)
        ):
            self._data = meters_data(category, user_input)
            self._since = await async_data_since(self.hass, self._data[CONF_METERS])
            self._scop, self._heat_start = (
                await async_scop_needed(
                    self.hass, self._data[CONF_METERS], self._data[CONF_HEAT_METERS]
                )
                if category == CATEGORY_HEAT_PUMP
                else (False, None)
            )
            return await self._async_values(category, None)
        schema = meters_schema(self.hass, category, self._setup, self._taken())
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id=category, data_schema=schema, errors=errors)

    async def async_step_heat_pump_values_gas(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the heat pump's averages since its data begins."""
        return await self._async_values(CATEGORY_HEAT_PUMP, user_input)

    async_step_heat_pump_values_gas_scop = async_step_heat_pump_values_gas
    async_step_heat_pump_values_gas_scop_until = async_step_heat_pump_values_gas
    async_step_heat_pump_values_oil = async_step_heat_pump_values_gas
    async_step_heat_pump_values_oil_scop = async_step_heat_pump_values_gas
    async_step_heat_pump_values_oil_scop_until = async_step_heat_pump_values_gas

    async def async_step_wallbox_values(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the car's averages since its data begins."""
        return await self._async_values(CATEGORY_WALLBOX, user_input)

    async def _async_values(
        self, category: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        heating = self._data.get(CONF_HEATING, HEATING_GAS)
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_values(category, heating, user_input)
        ):
            values = values_data(category, heating, user_input)
            before = {
                key: value for key, value in values.items() if key != VALUE_PRICE_ENTITY
            }
            return await self._async_add(
                category, {**self._data, CONF_BEFORE: before, CONF_CURRENT: values}
            )
        schema = values_schema(
            self.hass, category, heating, scop=self._scop, price_entity=True
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id=_values_step(category, heating, self._scop, self._heat_start),
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "since": _date(self._since),
                "heat_until": _date(self._heat_start) if self._heat_start else "",
            },
            last_step=len(self._pending) == 1,
        )


def _overview_step(setup: EnergySetup) -> str:
    """Return the overview's step id, which names what is missing."""
    if not setup.devices:
        return "user_no_devices"
    if not setup.solar:
        return "user_no_solar"
    return "user"


def _pv_step(setup: EnergySetup) -> str:
    """Return the PV step id, which warns when the feed-in is not measured."""
    return "pv" if any(source.export_stat for source in setup.grids) else "pv_no_export"


def _values_step(
    category: str, heating: str, scop: bool, heat_start: float | None
) -> str:
    """Return the step id of the values form.

    Step ids select the translations, so the labels and hints fit the former
    heating and whether, and why, the seasonal COP is asked.
    """
    if category == CATEGORY_WALLBOX:
        return "wallbox_values"
    step = f"heat_pump_values_{heating}"
    if scop:
        step += "_scop_until" if heat_start else "_scop"
    return step


class CategorySubentryFlow(ConfigSubentryFlow):
    """Add a category later, or change one."""

    def __init__(self) -> None:
        """Initialize the flow."""
        self._setup = EnergySetup()
        self._data: dict[str, Any] = {}
        self._since = 0.0
        self._scop = False
        self._heat_start: float | None = None

    @property
    def _category(self) -> str:
        return self._subentry_type

    async def _async_load_setup(self) -> SubentryFlowResult | None:
        try:
            self._setup = await async_get_energy_setup(self.hass)
        except EnergyInterfaceError:
            return self.async_abort(reason="energy_interface")
        if self._category not in available_categories(self._setup):
            return self.async_abort(reason="not_available")
        return None

    def _taken(self, own: str | None = None) -> list[str]:
        return [
            meter
            for subentry_id, subentry in self._get_entry().subentries.items()
            if subentry_id != own
            for meter in subentry.data.get(CONF_METERS, [])
        ]

    # Adding a category

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a category: the same steps as in the first setup."""
        category = self._category
        if user_input is None:
            if any(
                subentry.subentry_type == category
                for subentry in self._get_entry().subentries.values()
            ):
                return self.async_abort(reason="already_configured")
            if (abort := await self._async_load_setup()) is not None:
                return abort

        if category == CATEGORY_PV:
            if user_input is not None:
                return await self._async_create(dict(user_input))
            return self.async_show_form(
                step_id=_pv_step(self._setup),
                data_schema=investment_schema(self.hass),
                description_placeholders={
                    "since": _date(
                        await async_data_since(self.hass, list(self._setup.solar))
                    )
                },
            )
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_meters(category, user_input)
        ):
            await self._async_take_meters(meters_data(category, user_input))
            return await self._async_values_form(None, reconfigure=False)
        schema = meters_schema(self.hass, category, self._setup, self._taken())
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_pv_no_export(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add the PV plant while the feed-in is not measured."""
        return await self.async_step_user(user_input)

    async def async_step_pv(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add the PV plant."""
        return await self.async_step_user(user_input)

    async def _async_create(self, data: dict[str, Any]) -> SubentryFlowResult:
        return self.async_create_entry(
            title=await async_category_title(self.hass, self._category),
            data={CONF_SETUP_AT: next_full_hour(), **data},
            unique_id=self._category,
        )

    async def _async_take_meters(self, data: dict[str, Any]) -> None:
        """Remember the first step and look up what the values form needs."""
        self._data = data
        self._since = await async_data_since(self.hass, data[CONF_METERS])
        if self._category == CATEGORY_HEAT_PUMP:
            self._scop, self._heat_start = await async_scop_needed(
                self.hass, data[CONF_METERS], data[CONF_HEAT_METERS]
            )

    async def _async_values_form(
        self, user_input: dict[str, Any] | None, *, reconfigure: bool
    ) -> SubentryFlowResult:
        """Ask for the averages since the data begins.

        When reconfiguring, this follows a change of the former heating or of
        meters that now need a seasonal COP; it replaces all values.
        """
        category = self._category
        heating = self._data.get(CONF_HEATING, HEATING_GAS)
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_values(category, heating, user_input)
        ):
            values = values_data(category, heating, user_input)
            before = {
                key: value for key, value in values.items() if key != VALUE_PRICE_ENTITY
            }
            data = {**self._data, CONF_BEFORE: before, CONF_CURRENT: values}
            if not reconfigure:
                return await self._async_create(data)
            subentry = self._get_reconfigure_subentry()
            return self._async_save({**subentry.data, **data}, "recomputing", {})
        schema = values_schema(
            self.hass, category, heating, scop=self._scop, price_entity=True
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id=_values_step(category, heating, self._scop, self._heat_start),
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "since": _date(self._since),
                "heat_until": _date(self._heat_start) if self._heat_start else "",
            },
        )

    async def async_step_wallbox_values(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Ask for the car's averages."""
        return await self._async_values_form(
            user_input, reconfigure=self.source == "reconfigure"
        )

    async def async_step_heat_pump_values_gas(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Ask for the heat pump's averages, compared with gas."""
        return await self.async_step_wallbox_values(user_input)

    async_step_heat_pump_values_gas_scop = async_step_heat_pump_values_gas
    async_step_heat_pump_values_gas_scop_until = async_step_heat_pump_values_gas
    async_step_heat_pump_values_oil = async_step_heat_pump_values_gas
    async_step_heat_pump_values_oil_scop = async_step_heat_pump_values_gas
    async_step_heat_pump_values_oil_scop_until = async_step_heat_pump_values_gas

    # Changing a category

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Ask what to change."""
        if (abort := await self._async_load_setup()) is not None:
            return abort
        options = (
            ["investment", "recompute"]
            if self._category == CATEGORY_PV
            else ["now", "before", "meters", "recompute"]
        )
        return self.async_show_menu(step_id="reconfigure", menu_options=options)

    def _async_save(
        self, data: dict[str, Any], reason: str, placeholders: dict[str, str]
    ) -> SubentryFlowResult:
        """Store the category and close with a message saying what happens.

        The entry's update listener reloads it, which applies the change.
        """
        entry = self._get_entry()
        self.hass.config_entries.async_update_subentry(
            entry, self._get_reconfigure_subentry(), data=data
        )
        return self.async_abort(reason=reason, description_placeholders=placeholders)

    async def async_step_investment(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the PV plant's purchase cost."""
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            data = {
                key: value
                for key, value in subentry.data.items()
                if key != CONF_INVESTMENT
            }
            return self._async_save({**data, **user_input}, "investment_saved", {})
        return self.async_show_form(
            step_id="investment",
            data_schema=self.add_suggested_values_to_schema(
                investment_schema(self.hass), subentry.data
            ),
        )

    async def async_step_recompute(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Compute the category again, for example after fixing readings."""
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            return self._async_save(
                {**subentry.data, CONF_RECOMPUTE: dt_util.utcnow().timestamp()},
                "recomputing",
                {},
            )
        return self.async_show_form(
            step_id="recompute", data_schema=probatio.Schema({})
        )

    def _uses_scop(self, data: Mapping[str, Any]) -> bool:
        return self._category == CATEGORY_HEAT_PUMP and VALUE_SCOP in data.get(
            CONF_BEFORE, {}
        )

    async def async_step_now(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the values that apply from the next full hour."""
        subentry = self._get_reconfigure_subentry()
        category = self._category
        heating = subentry.data.get(CONF_HEATING, HEATING_GAS)
        # From now on the seasonal COP is needed only without heat meters.
        scop = category == CATEGORY_HEAT_PUMP and not subentry.data.get(
            CONF_HEAT_METERS
        )
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_values(category, heating, user_input)
        ):
            current = values_data(category, heating, user_input)
            if not scop and VALUE_SCOP in subentry.data.get(CONF_CURRENT, {}):
                current[VALUE_SCOP] = subentry.data[CONF_CURRENT][VALUE_SCOP]
            valid_from = dt_util.as_local(dt_util.utc_from_timestamp(next_full_hour()))
            return self._async_save(
                {**subentry.data, CONF_CURRENT: current},
                "values_from",
                {"time": valid_from.strftime("%H:%M")},
            )
        schema = self.add_suggested_values_to_schema(
            values_schema(self.hass, category, heating, scop=scop, price_entity=True),
            user_input
            if user_input is not None
            else values_form_input(
                category, heating, subentry.data.get(CONF_CURRENT, {})
            ),
        )
        return self.async_show_form(
            step_id=f"now_{heating}" if category == CATEGORY_HEAT_PUMP else "now",
            data_schema=schema,
            errors=errors,
        )

    async_step_now_gas = async_step_now
    async_step_now_oil = async_step_now

    async def async_step_before(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the averages for the time before the setup."""
        subentry = self._get_reconfigure_subentry()
        category = self._category
        heating = subentry.data.get(CONF_HEATING, HEATING_GAS)
        scop = self._uses_scop(subentry.data)
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_values(category, heating, user_input)
        ):
            return self._async_save(
                {
                    **subentry.data,
                    CONF_BEFORE: values_data(category, heating, user_input),
                },
                "recomputing",
                {},
            )
        since = await async_data_since(
            self.hass, list(subentry.data.get(CONF_METERS, []))
        )
        schema = self.add_suggested_values_to_schema(
            values_schema(self.hass, category, heating, scop=scop, price_entity=False),
            user_input
            if user_input is not None
            else values_form_input(
                category, heating, subentry.data.get(CONF_BEFORE, {})
            ),
        )
        return self.async_show_form(
            step_id=f"before_{heating}" if category == CATEGORY_HEAT_PUMP else "before",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "since": _date(since),
                "until": _date(subentry.data.get(CONF_SETUP_AT, next_full_hour())),
            },
        )

    async_step_before_gas = async_step_before
    async_step_before_oil = async_step_before

    async def async_step_meters(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change meters, former heating, and extra cost."""
        subentry = self._get_reconfigure_subentry()
        category = self._category
        errors: dict[str, str] = {}
        if user_input is not None and not (
            errors := validate_meters(category, user_input)
        ):
            data = {
                key: value
                for key, value in subentry.data.items()
                if key != CONF_INVESTMENT
            }
            data.update(meters_data(category, user_input))
            await self._async_take_meters(data)
            heating_changed = data.get(CONF_HEATING) != subentry.data.get(CONF_HEATING)
            scop_missing = self._scop and not self._uses_scop(subentry.data)
            if heating_changed or scop_missing:
                return await self._async_values_form(None, reconfigure=True)
            return self._async_save(data, "recomputing", {})
        schema = self.add_suggested_values_to_schema(
            meters_schema(
                self.hass, category, self._setup, self._taken(subentry.subentry_id)
            ),
            user_input if user_input is not None else subentry.data,
        )
        return self.async_show_form(step_id="meters", data_schema=schema, errors=errors)
