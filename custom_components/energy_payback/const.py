"""Constants for the Energy Payback integration."""

from typing import Final

DOMAIN: Final = "energy_payback"

# Categories. Each one is a config subentry type and appears at most once.
CATEGORY_PV: Final = "pv"
CATEGORY_HEAT_PUMP: Final = "heat_pump"
CATEGORY_WALLBOX: Final = "wallbox"
CATEGORIES: Final = (CATEGORY_PV, CATEGORY_HEAT_PUMP, CATEGORY_WALLBOX)

# Subentry data keys
CONF_COMMISSIONED: Final = "commissioned"
CONF_INVESTMENT: Final = "investment"
CONF_INVESTMENT_ENTITY: Final = "investment_entity"
CONF_METERS: Final = "meters"
CONF_HEAT_METERS: Final = "heat_meters"
CONF_SCOP: Final = "scop"
CONF_BOILER_EFFICIENCY: Final = "boiler_efficiency"
CONF_GAS_PRICE: Final = "gas_price"
CONF_GAS_PRICE_ENTITY: Final = "gas_price_entity"
CONF_FUEL_PRICE: Final = "fuel_price"
CONF_FUEL_PRICE_ENTITY: Final = "fuel_price_entity"
CONF_COMBUSTION_CONSUMPTION: Final = "combustion_consumption"
CONF_EV_CONSUMPTION: Final = "ev_consumption"
CONF_GRID: Final = "grid"

# Form sections
SECTION_ASSUMPTIONS: Final = "assumptions"
SECTION_ADVANCED: Final = "advanced"

DEFAULT_SCOP: Final = 3.8
DEFAULT_BOILER_EFFICIENCY: Final = 92.0
DEFAULT_COMBUSTION_CONSUMPTION: Final = 7.0
DEFAULT_EV_CONSUMPTION: Final = 20.0

# The card is served by the integration itself, so one install brings both.
FRONTEND_URL: Final = "/energy_payback_static"
CARD_FILENAME: Final = "energy-payback-card.js"

SIGNAL_ENERGY_PREFS_UPDATED: Final = f"{DOMAIN}_energy_prefs_updated"

# Issue ids
ISSUE_ENERGY_INTERFACE: Final = "energy_interface"
ISSUE_NO_GRID_PRICE: Final = "no_grid_price"
ISSUE_MISSING_METER: Final = "missing_meter"
