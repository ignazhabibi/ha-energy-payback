# Energy Payback: product concept

A Home Assistant integration with its own dashboard card. It shows what a PV
plant, a heat pump, and an electric car have saved, and whether and when they
pay off.

This is a product concept: it describes what the product does and how it feels
to use, not the technical design. Revised on 2026-10-31 after the first test
in a real household, scoped as an MVP: useful, and as simple as possible.
`onboarding-flow.html` shows every setup dialog with its texts.

## 1. The problem

Many households electrified step by step: a PV plant, then a heat pump
instead of a gas or oil heating, then an electric car instead of a combustion
car. Home Assistant's energy dashboard shows what was consumed, produced, and
paid. It does not answer the questions these households actually ask:

- What has each investment saved so far, compared with the alternative it replaced?
- Has it paid for itself yet? If not, roughly when?
- Is the whole electrification in the plus already?

Answering this today takes spreadsheets, or hand-written template sensors and
cards. Both are fragile and need knowledge most users do not have.

## 2. Who it is for

Home Assistant users with a configured energy dashboard who own at least one
of: a PV plant, a heat pump, an electric car charged at home. They are not
expected to write YAML, create helpers, or understand statistics. Users with
a gas, oil, or fuel price sensor can use it.

## 3. What the product does

### 3.1 Three categories

Each category compares reality with the alternative it replaced. The card and
the setup name the categories by what saves the money; the setup asks for the
meters that measure it.

| Category | Measured by | Saving | Compared with |
|---|---|---|---|
| PV plant | The energy dashboard's solar, grid, and battery meters | Solar power used in the house, valued at the electricity price of that hour, plus the feed-in compensation received | No PV plant: all electricity from the grid, no feed-in |
| Heat pump | Its electricity meters, and heat meters if there are any | What the former gas or oil heating would have cost for the same heat, minus what the heat pump's electricity cost | A gas or oil heating |
| Electric car | The meters of the wallbox (or charging points) | What fuel would have cost for the same distance, minus what the charging electricity cost | A combustion car |

Each category exists once. A household with two cars has one category
"Electric car"; its consumption is the average of the cars.

### 3.2 Payback

For payback, the user may enter per category:

- the PV plant: its purchase cost;
- the heat pump: the extra purchase cost over a gas or oil heating;
- the electric car: the extra purchase cost over a combustion car.

From that, the product shows:

- how much of the investment the savings have covered;
- the average saving per year;
- roughly how many years remain until it has paid off;
- once paid off, the annual return;
- across all categories: the overall balance (savings minus investments) and roughly from when the household is in the plus.

### 3.3 Results in Home Assistant

- Each category is a device with sensors in the user's currency: saving, paid back (%), saving per year.
- A device "Balance" has the overall balance.
- The sensors have history, work in statistics, and can be used in automations, for example a notification when the heat pump has paid off.
- The saving sensor shows since when the category counts and which values it currently uses.

### 3.4 The card

- The card shows the balance of all categories at a glance. It needs no options: it finds the categories by itself.
- It has two views, switched in the card's header:
  - **Total:** savings so far against the investments, with the progress of each.
  - **Per year:** the yearly averages, the years still to go, and when the household will be in the plus.
- Each row says since when it counts, for example "since 27 Jul 2023".
- It shows the gas, oil, and fuel prices in use. A tap leads to where they are changed.
- It appears immediately, without loading delay.

### 3.5 One install

- The integration and the card come together in one installation via HACS.
- There is no separate dashboard resource to add, and nothing to bump after an update.

## 4. Principles

- **Three phases, one rule each** (section 5). Before Home Assistant nothing counts; until the setup, averages count; from the setup, current values count.
- **Measurements are facts.** The product computes with the data as Home Assistant recorded it. It never corrects or filters readings. Bad readings are fixed in Home Assistant's statistics tools, which also fixes the energy dashboard; then the category is recomputed.
- **Use what Home Assistant knows.** Grid, electricity prices, feed-in, solar, battery, and device meters come from the energy dashboard. The user is asked only for what Home Assistant cannot know.
- **Follow the energy dashboard.** When the user changes something there, the product uses the new setup without being set up again.
- **No double counting.** The three savings add up to the household's total saving. The benefit of solar power belongs to the PV plant alone. The heat pump and the car pay for all their electricity at the price of that hour, even when the sun delivered it.
- **Ask little, and say what is fixed.**
  - A field appears only when it is needed for this household.
  - Nothing is preselected that the user did not choose. Nothing is folded away.
  - Values almost nobody knows are fixed and described in the documentation: the former heating's efficiency is 92 %, and heating oil has 10 kWh per litre.
- **Short and clear.** Each dialog explains itself in one or two sentences, each field in at most one line. Terms are the ones users know from their bills and devices.
- **Works without helpers.** Every value can be typed in. A price sensor is an option, never a requirement.
- **Honest numbers.** Savings can be negative for a while, and the product shows that. There is no yearly average from a few months, because seasons distort it. Estimated heat is called an estimate.
- **Robust.** Savings have no gaps when Home Assistant was restarted or switched off for a while.
- **Feels like Home Assistant.**
  - Set up and changed entirely in the UI, in Home Assistant's usual dialogs.
  - The card looks like Home Assistant's own energy cards, in light and dark themes, on phones and desktops.
  - Everything is reachable by keyboard and screen reader, with sufficient contrast.

## 5. Three phases

### 5.1 The phases

| Phase | Period | What counts |
|---|---|---|
| 1. Before Home Assistant | Before the first data of a category | Nothing. There is no data and no starting value. The card says "since 27 Jul 2023". |
| 2. Before the setup | From the first data to the setup of the category | One average per value, entered in the setup |
| 3. From the setup | From the setup on | The averages as starting values. Changes and a price sensor apply from the next full hour. |

Each category has its own phases. Its phase 2 begins with the first data of
its meters: solar for the PV plant, the electricity meters for the heat pump,
the charging meters for the car.

### 5.2 What applies when

| Value | Phase 2 | Phase 3 |
|---|---|---|
| Measurements | Recorded data | Recorded data |
| Electricity price and feed-in compensation | What the energy dashboard used for each hour | The same |
| Gas, oil, or fuel price | The average | The current value, or the sensor if one is chosen |
| Consumption of both cars, seasonal COP, own electricity tariff | The average | The current value |
| Investments | The current value always counts. They are totals, not rates. | The same |

- **Electricity price of an hour:** with several tariffs, such as day and night, it is the average of that hour. Before the energy dashboard has costs, its first known price applies.
- **A price sensor** counts only in phase 3. Its history from before the setup is not used, so phase 2 follows one rule without exceptions. While the sensor is unavailable, its last value applies.
- **Changes in phase 3** apply from the next full hour. Hours already computed keep their values.

### 5.3 Corrections

| What changes | What is computed again |
|---|---|
| Averages before the setup | Phase 2 only |
| Meters, or gas instead of oil | The whole category; averages and current values stay |
| The energy dashboard, for example a second solar source | The whole category |
| "Neu berechnen" after fixing readings in Home Assistant | The whole category with the current data; all values stay |
| Investments | Nothing; the new value counts at once |

## 6. The categories in detail

The prerequisite for every category is an energy dashboard with grid import and
an electricity price. Without it, setup ends with a short explanation.

### 6.1 PV plant

| Input | Required | Source |
|---|---|---|
| Solar production (all solar sources together) | yes | Energy dashboard |
| Grid import with electricity price | yes | Energy dashboard |
| Grid export | yes, if the plant feeds in | Energy dashboard |
| Feed-in compensation | no | Energy dashboard |
| Home battery | no, counted automatically if present | Energy dashboard |
| Purchase cost | no; for the payback | Setup |

- Solar power used in the house is production minus export, plus battery discharge minus battery charge.
- Without a grid export meter the product counts all solar power as used in the house. The setup says so as a warning.

### 6.2 Heat pump

| Input | Required | Source |
|---|---|---|
| Electricity meters (1 or more) | yes | Energy dashboard, individual devices |
| Heat meters (0 or more) | no | Any energy sensor |
| Former heating: gas or oil | yes | Setup |
| Extra purchase cost | no; for the payback | Setup |
| Gas or oil price | yes | Setup: average, optionally a sensor from now on |
| Seasonal COP | only when heat data is missing | Setup: average |
| Own electricity tariff | no; without it the energy dashboard's price counts | Setup: average |

- **Totals, or parts that add up to them.** The user chooses the meter for the whole heat pump if there is one, otherwise the separate meters for heating and hot water; they are added. Heat meters cover the same parts as the electricity meters.
- **One seasonal COP** for heating and hot water together.
- **Measured heat first.**
  - An hour counts as measured when every chosen heat meter has data for it.
  - Otherwise its heat is estimated from the electricity and the seasonal COP.
- **When the setup asks for the COP:**
  - Without heat meters: always, in phase 2 and phase 3.
  - When the electricity data begins before the heat data: in phase 2, with the period named, for example "Schätzt die Wärme bis 02.02.2026".
  - Otherwise never. Should heat data be missing later, those hours use the COP measured until then.
- **Fuel for the same heat:** heat divided by 92 %. Gas is priced per kWh, oil per litre at 10 kWh.

### 6.3 Electric car

| Input | Required | Source |
|---|---|---|
| Charging meters (1 or more) | yes | Energy dashboard, individual devices |
| Extra purchase cost | no; for the payback | Setup |
| Electric car consumption, kWh/100 km | yes | Setup: average |
| Combustion car consumption, l/100 km | yes | Setup: average |
| Fuel price per litre | yes | Setup: average, optionally a sensor from now on |
| Own electricity tariff | no; without it the energy dashboard's price counts | Setup: average |

- The distance follows from the charged energy and the electric car's consumption. The fuel follows from the distance and the combustion car's consumption.
- The electric car's consumption is the one measured at the wallbox, including charging losses. That is usually 10–15 % more than the car shows. The field says so.

### 6.4 Device choice

- Heat pump and electric car offer the individual devices of the energy dashboard.
- Nothing is preselected.
- A device chosen in one category is not offered in the other.
- If a device and one of its sub-devices (as nested in the energy dashboard) are both chosen, only the outer one counts, so nothing is counted twice.

## 7. Setup and changes

`onboarding-flow.html` has every dialog with its texts, hints, and errors.
The texts are German; the English translation follows the same wording.

### 7.1 First setup

1. **Overview:** what comes from the energy dashboard (✓ or –), and which categories to evaluate. Nothing is ticked; only possible categories are offered.
2. **PV plant:** since when it counts, and the purchase cost.
3. **Heat pump:** electricity meters, heat meters, former heating, extra purchase cost.
4. **Heat pump, "Durchschnitt seit 01.10.2024":** the averages for phase 2, which also start phase 3; an optional price sensor for phase 3.
5. **Electric car:** charging meters, extra purchase cost.
6. **Electric car, "Durchschnitt seit …":** as step 4.
7. **Done:** the past is being computed; where to find the card.

Only the chosen categories appear. Steps 4 and 6 are separate because their
date follows from the meters chosen just before.

### 7.2 Later

- **Integration page:** each category is listed with "Reconfigure". There are buttons to add the missing categories; they lead through the same steps as the first setup.
- **Reconfigure** opens a menu:
  - **Werte ab jetzt:** current values and price sensor (phase 3).
  - **Durchschnittswerte vor der Einrichtung:** the averages (phase 2).
  - **Zähler und Mehrkosten:** meters, former heating, extra purchase cost.
  - **Neu berechnen:** after fixing readings in Home Assistant.
  - The PV plant has only "Anschaffungskosten" and "Neu berechnen".
- Each dialog says in one sentence what the change does (section 5.3), and confirms it afterwards, for example "Die neuen Werte gelten ab 15:00 Uhr."
- **Removing a category** removes its device, its sensors, its row in the card, and its values. Adding it again starts with a new phase 2.

## 8. The card's states

- **a. Just set up:** the past is being computed. This takes seconds, not hours.
- **b. Total view:** savings, investments, progress per category, overall balance.
- **c. Per-year view:** yearly averages, years to payback, the expected date for the plus.
- **d. Only a few months of data:** no yearly figures yet. The card says from when there will be some.
- **e. Partly estimated:** a heat pump with estimated heat says so in its row: "Wärme teilweise geschätzt".

## 9. When something is wrong

- **A meter disappears** from the energy dashboard: a repair notice. The category keeps its last figures until it is fixed.
- **The energy dashboard loses its electricity price:** a repair notice. All categories keep their last figures.
- **A price sensor is removed** from Home Assistant: a repair notice that leads to "Werte ab jetzt". Until then its last value applies.
- **Bad readings:** no notice in the MVP. The figures use the data as it is; the documentation explains how to fix readings and recompute.

## 10. Not part of the MVP

- **Investments from a helper** (only typed-in values).
- **Sensors for consumptions and the seasonal COP.**
- **A price sensor's history** from before the setup.
- **A notice about implausible readings**, such as a meter going backwards.
- **Importing history** from before the Home Assistant data, for example savings kept in a spreadsheet.
- **Fetching prices** from online services. Existing integrations do that; their sensors can be used.
- **Other categories:** solar thermal, a battery of its own.
- **Other alternatives** than a gas or oil heating and a combustion car.
- **More dashboard cards** beyond the balance card.

## 11. Decisions

| Question | Decision |
|---|---|
| Name | Energy Payback |
| Start of counting | The first hour with data, per category. No date to enter, no starting value. |
| The past | One average per value for the time before the setup |
| Changing values | From the next full hour. The averages before the setup are corrected separately. |
| Bad readings | Fixed in Home Assistant's statistics, then "Neu berechnen". Never filtered. |
| Several of a kind | One category each. Heat pump and electric car add up several meters. Several cars share an average consumption. |
| Heating and hot water | One seasonal COP for both |
| Former heating | Gas or oil; efficiency fixed at 92 % |
| Own tariffs | Optional own electricity price for the heat pump and the car |
| Investments | Purchase cost for PV, extra purchase cost for heat pump and car; optional, for the payback |
| More sensors | Paid back (%), saving per year, overall balance |
| Battery storage | Part of the PV plant |
| Units and currency | Per kWh, per litre, and totals, in Home Assistant's currency |
| Detail views | Home Assistant's history of the sensors |
| Distribution | One repository, one HACS entry |

## 12. Open

- `clean-install-mockup.html` shows the earlier journey and card states, including "in operation since". `onboarding-flow.html` replaces its setup part; its card part has to follow section 8.

## 13. Quality expectations

- **Home Assistant guidelines:** follow the developer guidelines at contributors.home-assistant.io and come as close to Platinum on the integration quality scale as a custom integration can.
- **Languages:** English and German.
- **Interfaces:** prefer public Home Assistant interfaces. Where none exists, isolate the dependency, document it, and fail with a clear repair notice instead of wrong numbers.
- **Verification of the card:** check it in light and dark themes, at phone and desktop widths, with keyboard and screen reader.
- **Performance:** computing the past must not slow Home Assistant down noticeably, even with several years of data.
