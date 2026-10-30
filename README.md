# Energy Payback

A Home Assistant integration with its own dashboard card. It shows what your
PV plant, heat pump, and electric car have saved compared with what they
replaced, and whether and when they pay off.

Home Assistant's energy dashboard shows what you consumed, produced, and paid.
Energy Payback answers the questions that come next:

- What has each investment saved so far?
- Has it paid for itself yet? If not, roughly when?
- Is the whole electrification in the plus already?

It needs no YAML, no helpers, and no template sensors. Everything it can, it
takes from the energy dashboard; it asks only for what Home Assistant cannot
know, such as what the heat pump cost or what gas would cost today.

![The card](docs/card.png)

## Use cases

- See at a glance whether the PV plant, heat pump, and electric car together
  have already saved more than they cost.
- Get a notification when the heat pump has paid for itself.
- Compare the yearly saving of each investment, for example before deciding on
  a battery or a second wallbox.
- Keep an honest record: savings can be negative for a while, for example when
  electricity is expensive and gas is cheap, and the integration shows that.

## What it calculates

There are three categories. Each compares reality with the alternative it
replaced.

| Category | Saving | Compared with |
|---|---|---|
| PV plant | Solar power used in the house, valued at the grid price at that time, plus the feed-in compensation received. A home battery counts as part of the PV plant. | No PV plant: all electricity from the grid, no feed-in. |
| Heat pump | What a gas boiler would have cost for the same heat, minus what the heat pump's electricity cost. | A gas boiler. Heat comes from heat meters where there are any, otherwise from electricity × SCOP. |
| Wallbox | What fuel would have cost for the same distance, minus what the charging electricity cost. | A combustion car. The distance follows from the charged energy and the electric car's consumption. |

- **No double counting.** The three savings add up to the household's total
  saving. The benefit of solar power belongs to the PV plant alone; heat pump
  and wallbox pay for all their electricity at the grid price of that hour,
  even when the sun delivered it.
- **Prices at the time of use.** The electricity price comes from the energy
  dashboard, fixed or changing, so dynamic tariffs are handled hour by hour.
- **Honest numbers.** There is no payback percentage when the data does not
  reach back to the start of operation, and no yearly average before twelve
  months of data, because seasons would distort it.

## Supported setups

Energy Payback works with any energy dashboard that has:

- a grid import with an electricity price (a fixed price, a price entity, or a
  cost statistic), and
- for the **PV plant**: at least one solar production source. Several solar
  sources and home batteries are counted together as one PV plant.
- for the **heat pump** and the **wallbox**: their electricity meters under
  *Individual devices*. Several meters per device are fine, for example
  separate meters for heating and hot water, or two wallboxes. Meters the
  energy dashboard marks as included in another selected meter are not
  counted twice.

Not supported: other heating systems than gas as the alternative, gas prices
per cubic metre, solar thermal, and fetching gas or fuel prices from online
services. Price sensors you already have can be used, though.

Home Assistant 2026.10 or newer is required.

## Installation

1. Set up the [energy dashboard](https://my.home-assistant.io/redirect/config_energy/)
   with grid import and electricity price, your solar production, and the
   meters of heat pump and wallbox under *Individual devices*.
2. Install Energy Payback from the Marketplace (Settings › Marketplace) or HACS
   as a custom repository: `https://github.com/ignazhabibi/ha-energy-payback`,
   type *Integration*.
3. Restart Home Assistant.
4. Go to **Settings › Devices & services › Add integration** and choose
   **Energy Payback**.
5. The first dialog lists what was found in the energy dashboard and asks which
   categories to evaluate. Only categories the dashboard has data for are
   offered.
6. Fill in one short step per category (see below), then assign areas to the
   new devices if you like.
7. Add the card **Energy Payback** to a dashboard from the card picker. It has
   no options. There is no dashboard resource to add: the integration serves
   the card itself and updates it with the integration.

The past is computed in the background right after setup. This usually takes
less than a minute; until then the card says that it is calculating.

## Configuration

Categories are config subentries. On the integration page each category has a
menu with **Reconfigure** and **Delete**, and there are buttons to add the
categories not set up yet.

### PV plant

| Field | Description |
|---|---|
| Investment (optional) | What the plant cost, including a battery. Without it there is no payback figure. |
| In operation since (optional) | Empty: counting starts with the first solar data. If the plant is older than the data, enter the real date: the saving still counts from the data, but no payback percentage is shown. |
| Advanced › Investment from an entity | A number entity with the investment, for example a helper with the running sum of your expenses. When it is unavailable, the fixed amount counts. |

### Heat pump instead of a gas boiler

| Field | Description |
|---|---|
| Electricity meters | The heat pump's meters from the energy dashboard's individual devices. Choose all that belong to it. |
| Heat meters (optional) | Energy sensors measuring the heat produced. Measured heat is used for every hour that has a measurement. |
| SCOP | Seasonal efficiency, used for hours without measured heat. Default 3.8. |
| Gas price | What a kWh of gas would cost today. Also used for the computed past. |
| Extra cost over a gas boiler (optional) | The investment the heat pump has to pay back. |
| In operation since (optional) | Empty: counting starts with the first data of the meters. |
| Assumptions › Gas boiler efficiency | Default 92 %. |
| Advanced › Gas price from an entity | Takes precedence over the fixed price while it has a value; its recorded history is used for the past. |
| Advanced › Investment from an entity | As for the PV plant. |
| Advanced › Electricity tariff | Only with several priced grid connections, for example a separate heat pump tariff: the one whose price the heat pump pays. |

### Electric car instead of a combustion car (wallbox)

| Field | Description |
|---|---|
| Electricity meters | The wallbox meters from the energy dashboard's individual devices. |
| Fuel price | What a litre would cost today. Also used for the computed past. |
| Extra cost over a combustion car (optional) | The investment to pay back, wallbox included if you like. |
| First electric car since (optional) | Empty: counting starts with the first charge in the data. |
| Assumptions › Consumption of the combustion car | Default 7 l/100 km. With several cars, an average. |
| Assumptions › Consumption of the electric car | Default 20 kWh/100 km, measured at the wallbox including charging losses. With several cars, an average. |
| Advanced › Fuel price from an entity | For example a fuel price sensor. Takes precedence while it has a value. |
| Advanced › Investment from an entity, Electricity tariff | As above. |

### What happens when you change something

- **Prices and investments** apply from the next full hour. What was already
  computed stays, just as the energy dashboard treats a new electricity price.
- **Meters, assumptions, price entities, and "In operation since"** compute the
  category again from the start, because the old values were simply wrong.
- **The energy dashboard**: changes there are followed automatically from then
  on, without setting anything up again.

## Entities

Each category is a device with three sensors; one more device holds the
overall balance.

| Entity | Description |
|---|---|
| Saving | Total saving since counting began, in your currency. It has long-term statistics, including the computed past. Its attributes show since when it counts, the start of operation, the investment, whether the data covers the time since the start of operation, from when yearly figures exist, and the assumed gas or fuel price. |
| Paid back | Share of the investment the saving has covered, in percent. Unknown without an investment or when the data does not reach back to the start of operation. |
| Saving per year | Average saving per year. Unknown before twelve months of data. |
| Balance | All savings minus all investments. Unknown while any category is calculating or lacks data back to its start of operation. |

## The card

The card finds the categories by itself. The button in its header switches
between two views:

- **Total**: savings so far against the investments, with the progress of each.
- **Per year**: yearly averages, the years still to go, and roughly when the
  household will be in the plus.

The assumed gas and fuel prices are shown at the bottom; selecting them opens
the integration page, where they are changed. The card follows light and dark
themes, works on phones and desktops, and can be used with keyboard and screen
reader.

## How the data updates

Energy Payback reads the recorder's hourly long-term statistics of the meters
in the energy dashboard. It checks for newly compiled hours every 15 minutes,
and at once when the energy dashboard changes. Each hour is valued with the
prices of that hour. When Home Assistant was off, the recorder reports the
missed energy with the next hour, so no energy is lost; prices of the missing
hours are not known and the next hour's price is used.

## Example automation

Notify when the heat pump has paid for itself:

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.heat_pump_paid_back
    above: 100
actions:
  - action: notify.notify
    data:
      message: "The heat pump has paid for itself."
```

## Known limitations

- The past before setup is computed with the prices entered at setup, because
  Home Assistant does not know earlier gas or fuel prices. A price entity's
  history is used as far as the recorder kept it.
- Only data Home Assistant has counts. Savings from before Home Assistant
  recorded the energy dashboard cannot be imported yet.
- Several cars sharing a wallbox use one average consumption.
- The yearly average is a plain average since counting began; the first and
  last partial seasons can make it a little high or low.
- The energy dashboard and the recorder statistics have no public Python
  interface. Energy Payback keeps all access to them in one module and raises a
  repair issue instead of showing wrong numbers if a Home Assistant update
  changes them.

## Troubleshooting

- **Setup ends right away**: the energy dashboard has no grid import with an
  electricity price, or neither solar production nor individual devices. The
  message names what is missing and links to the energy dashboard.
- **Heat pump or wallbox are not offered**: their meters must be listed under
  *Individual devices* in the energy dashboard.
- **A repair issue says a meter is missing**: the meter was removed from the
  energy dashboard. The category keeps its last figures. Add the meter back, or
  choose other meters with *Reconfigure*.
- **No payback percentage**: enter an investment, and check that "In operation
  since" is not earlier than the data in Home Assistant.
- **The card says it is calculating for long**: download the diagnostics from
  the integration page and open an issue with them.

## Removal

1. Remove the card from your dashboards.
2. Go to **Settings › Devices & services › Energy Payback**, open the menu
   (⋮) and choose **Delete**. To remove one category only, use **Delete** in
   that category's menu.
3. Uninstall Energy Payback in the Marketplace or HACS and restart Home
   Assistant.

The long-term statistics of the saving sensors stay in the recorder until you
remove them under **Developer tools › Statistics**.

## Development

- Python: `uv sync --group dev`, then `uv run pytest`, `uv run mypy`, and
  `uv run ruff check`.
- Translations are generated: edit `scripts/translations.py` and run it.
- Card: in `card/`, `npm ci` and `npm run build`. The built file is committed,
  because the Marketplace installs exactly what is published.
  `card/demo/index.html` shows the card's states with a mocked Home Assistant.

## License

MIT
