// Bundle entry: registers the cards of the Energy Payback integration.

import { EnergyPaybackCard } from "./energy-payback-card";
import { EnergyPaybackHistoryCard } from "./energy-payback-history-card";
import { registerCards } from "./register";

registerCards([
  {
    tag: "energy-payback-card",
    card: EnergyPaybackCard,
    name: "Energy Payback",
    description:
      "What your PV plant, heat pump, and electric car have saved, and when they pay off.",
  },
  {
    tag: "energy-payback-history-card",
    card: EnergyPaybackHistoryCard,
    name: "Energy Payback history",
    description:
      "The savings of your PV plant, heat pump, and electric car per period. Follows the energy date selection.",
  },
]);
