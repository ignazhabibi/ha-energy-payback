# Energiebilanz: product concept

A Home Assistant integration with its own dashboard card. It shows what a PV
plant, a heat pump, and an electric car have saved, and whether and when they
pay off.

"Energiebilanz" is a working title. This is a product concept: it describes
what the product does and how it feels to use. It deliberately leaves the
technical design open. `clean-install-mockup.html` sketches the user journey
from installation to the card. Its texts and figures are suggestions.

## 1. The problem

Many households electrified step by step: a PV plant, then a heat pump
instead of a gas boiler, then an electric car instead of a combustion car.
Home Assistant's energy dashboard shows what was consumed, produced, and paid.
It does not answer the questions these households actually ask:

- What has each investment saved so far, compared with the alternative it replaced?
- Has it paid for itself yet? If not, roughly when?
- Is the whole electrification in the plus already?

Answering this today takes spreadsheets, or hand-written template sensors and
cards. Both are fragile and need knowledge most users do not have.

## 2. Who it is for

Home Assistant users with a configured energy dashboard who own at least one
of: a PV plant, a heat pump, an electric car charged at home. They are not
expected to write YAML, create helpers, or understand statistics. The product
should also be pleasant for experienced users who already have price sensors
and want to use them.

## 3. What the product does

### 3.1 Savings per category

There are three categories. Each compares reality with the alternative it
replaced:

| Category | Saving | Compared with |
|---|---|---|
| PV plant | Solar energy used in the house, valued at what grid electricity cost at that time, plus the feed-in compensation received. | No PV plant: all electricity from the grid, no feed-in. |
| Heat pump | What a gas boiler would have cost for the same heat, minus what the heat pump's electricity cost. | A gas boiler. The heat comes from a heat meter if there is one, otherwise from the electricity and the heat pump's seasonal efficiency (SCOP). The gas needed follows from the heat and the boiler's efficiency. |
| Electric car | What fuel would have cost for the same distance, minus what the charging electricity cost. | A combustion car. The distance follows from the charged energy and the electric car's consumption; the fuel from the distance and the combustion car's consumption. |

- **No double counting.** The three savings add up to the household's total saving. The benefit of solar power belongs to the PV plant alone. The heat pump and the car pay for all their electricity at the grid price of the moment, even when the sun delivered it.
- **Electricity prices come from the energy dashboard**, fixed or changing over time. The price at the time of use counts, so dynamic tariffs are handled correctly.
- **Savings can be negative** for a while, for example when electricity is expensive and gas is cheap. The product shows that honestly.

### 3.2 Payback

For each category the user may enter what it cost:

- the PV plant's price;
- the heat pump's extra cost over a gas boiler;
- the car's extra cost over a comparable combustion car.

From that, the product shows:

- how much of the investment the savings have covered;
- the average saving per year;
- roughly how many years remain until it has paid off;
- once paid off, the annual return;
- across all categories: the overall balance (savings minus investments) and roughly from when the household is in the plus.

### 3.3 Results in Home Assistant

- Each category's saving is an ordinary Home Assistant sensor in the user's currency.
- It has history, works in statistics, and can be used in automations, for example a notification when the heat pump has paid off.
- Next to the sensor the user can see since when it counts and which assumptions it uses.

### 3.4 The card

- A dashboard card shows the balance of all categories at a glance. It needs no options: it finds the categories by itself.
- It has two views, switched in the card's header:
  - **Total:** savings so far against the investments, with the progress of each.
  - **Per year:** the yearly averages, the years still to go, and when the household will be in the plus.
- It shows the assumed gas and fuel prices. A tap leads to where they are changed.
- It appears immediately, without loading delay.

### 3.5 One install

- The integration and the card come together in one installation via HACS.
- There is no separate dashboard resource to add, and nothing to bump after an update.

## 4. Principles

- **Use what Home Assistant knows.** Grid, prices, feed-in, solar, and device meters come from the energy dashboard. The user is asked only for what HA cannot know: investments, dates, gas and fuel prices, and assumptions about the replaced alternatives.
- **Follow the energy dashboard.** When the user changes something there, the product uses the new setup from then on, without being set up again.
- **Honest numbers.**
  - No verdict without data: no payback percentage when the data does not reach back to the start of operation.
  - No yearly average from a few months, because seasons distort it.
  - Assumptions are visible, and estimates are called estimates.
- **Robust.** Savings have no gaps when Home Assistant was restarted or switched off for a while. Nothing is lost when a price sensor is briefly unavailable.
- **Works without helpers.** Every value can be typed into the setup dialog. Price sensors are an option, not a requirement.
- **Feels like Home Assistant.**
  - Set up and changed entirely in the UI, in HA's usual dialogs.
  - The card looks like HA's own energy cards: light and dark themes, phones and desktops.
  - Everything is reachable by keyboard and screen reader, with sufficient contrast.

## 5. User journey

The mockup shows each step. Example household: energy dashboard set up since
March 2023 with grid, fixed electricity price, feed-in price, a PV plant, and
the individual devices "Wärmepumpe", "Wallbox", and "Spülmaschine". No
helpers.

### 5.1 Install and set up

1. **Install** via HACS and restart Home Assistant.
2. **Add the integration** under Settings › Devices & services.
3. **Overview.** The first dialog lists what was found in the energy dashboard: grid, electricity price, feed-in price, solar with the date its data begins, individual devices. It asks which categories to evaluate. Only possible categories are offered.
4. **One short step per chosen category:**
   - It names what comes from the energy dashboard.
   - It asks only for the rest:
     - the meter, chosen from the energy dashboard's devices;
     - prices;
     - optional investment;
     - optional "in operation since".
   - Assumptions with sensible defaults are folded away, such as boiler efficiency or the consumption of both cars. So is the option to take a price from a sensor.
5. **Done.**
   - A short message says that the past is being computed and where the card is.
   - HA's usual area choice for the new devices follows.

### 5.2 Afterwards

- **Integration page:** the integration lists its categories. Each has a menu to reconfigure or remove it, and there are buttons to add more.
- **Devices and sensors:** each category appears as a device with a sensor "Ersparnis".
- **Card:** the user adds the card from the card picker without options.
  - While the past is still being computed, it says so; this takes moments, not hours.
  - Then it shows the figures.

### 5.3 The card's states

The mockup shows them as a to e.

- **a. Just set up:** the past is being computed.
- **b. Total view:** savings, investments, progress per category, overall balance.
- **c. Per-year view:** yearly averages, years to payback, the expected date for the plus.
- **d. A system older than the data:** for example a PV plant from 2019, with HA data only from 2023. That row shows what was saved since the data begins, but no payback progress. The card shows no overall balance and says why.
- **e. Only a few months of data:** no yearly figures yet. The card says from when there will be some.

### 5.4 Changing things later

- **Same dialog:** "Reconfigure" on a category opens its dialog, pre-filled.
- **Prices, investments, and assumptions:** changes apply from now on. What was already computed stays, just as the energy dashboard treats a new electricity price.
- **"In operation since":** a different date computes the category again from that date.
- **Removing a category** removes its device, its sensor, and its row in the card.

### 5.5 When something is missing

- **No energy dashboard,** or one without grid import or price: setup ends with a short explanation and a link to the energy dashboard.
- **No individual devices:** heat pump and car are not offered. A note says what to add in the energy dashboard. The categories can be added later.
- **Problems later on:** if a chosen meter later disappears from the energy dashboard, Home Assistant shows a repair notice. The category keeps its last figures until it is fixed.

## 6. How the numbers behave

- **Start of counting:** each category counts from the beginning of its data in Home Assistant. If the user gave a later "in operation since", it counts from there. A new user therefore sees real figures right after setup.
- **The past:** computed with the prices and assumptions entered at setup, because Home Assistant does not know earlier gas or fuel prices. The dialog says so. If a price sensor with a history is used, its history counts.
- **From then on:** each moment is valued with the prices of that moment.
- **Heat:**
  - Measured heat is preferred.
  - Estimating from electricity and SCOP is used only where no heat measurement exists, for example before a heat meter was installed.
  - The same heat is never counted twice.
- **Payback progress** is shown only when the data covers the time since the system went into operation.
- **Yearly averages** appear only after twelve months of data.

## 7. Not part of the product for now

- **Importing history from before the Home Assistant data,** for example savings a long-time user kept in a spreadsheet. This may come later as its own feature.
- **Fetching gas or fuel prices from online services.**
- **Other categories:** a separate battery storage category, solar thermal, other heating systems than gas as the alternative.
- **Gas prices per cubic metre** (only per kWh).
- **More dashboard cards** beyond the balance card.

## 8. Open questions

1. **Name** of the integration and the card.
2. **Start of counting:** from the beginning of the data, as proposed, or should users be able to choose "from now"?
3. **The past:** today's prices as proposed, or a way to enter earlier prices?
4. **Corrections of assumptions,** such as a wrong fuel consumption: from now on like prices, or recomputed for the past because the old value was simply wrong?
5. **Several of a kind:** several wallboxes, several heat pumps, several cars with different consumption sharing one wallbox.
6. **Investments from a helper:** some users keep a running sum of their expenses in a helper. Should an investment be able to come from an entity, like prices?
7. **More sensors:** payback progress or the overall balance as sensors of their own, for automations?
8. **Battery storage:** is it fine to treat it as part of the PV plant?
9. **Units and currencies:** show prices per kWh in cents or euros? How to handle other currencies?
10. **Detail views:** does the card need a way to see a single category over time, or is HA's history of the sensor enough?
11. **Distribution:** integration and card in one repository and one HACS entry (as described), or two?

## 9. Quality expectations

- **Home Assistant guidelines:** follow the developer guidelines and aim for the basics of the integration quality scale (UI setup, translations, clean unloading, diagnostics, tests).
- **Languages:** at least English and German.
- **Interfaces:** prefer public Home Assistant interfaces. Where none exists, isolate the dependency, document it, and fail with a clear repair notice instead of wrong numbers.
- **Verification of the card:** check it in light and dark themes, at phone and desktop widths, with keyboard and screen reader.
- **Performance:** computing the past must not slow Home Assistant down noticeably, even with several years of data.
