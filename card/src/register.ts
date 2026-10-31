// Registers the cards and their card picker entries.

const REREGISTER_EVERY_MS = 100;
const REREGISTER_FOR_MS = 60_000;
const DOCUMENTATION_URL = "https://github.com/ignazhabibi/ha-energy-payback";

export interface CardEntry {
  tag: string;
  card: CustomElementConstructor;
  name: string;
  description: string;
}

const define = (tag: string, card: CustomElementConstructor): void => {
  if (customElements.get(tag)) return;
  try {
    customElements.define(tag, card);
  } catch {
    // The browser's own registry already holds this class.
    customElements.define(tag, class extends card {});
  }
};

export function registerCards(cards: CardEntry[]): void {
  const defineAll = () => cards.forEach(({ tag, card }) => define(tag, card));
  defineAll();

  // Home Assistant's app replaces the custom element registry with a scoped
  // one when it starts. A card loaded before that is unknown to the new
  // registry, and the dashboard shows a configuration error. Define the cards
  // again once the registry has been replaced; Home Assistant then rebuilds
  // them.
  const initialRegistry = window.customElements;
  const startedAt = Date.now();
  const watcher = window.setInterval(() => {
    const replaced = window.customElements !== initialRegistry;
    if (replaced) defineAll();
    if (replaced || Date.now() - startedAt > REREGISTER_FOR_MS) {
      window.clearInterval(watcher);
    }
  }, REREGISTER_EVERY_MS);

  const registry = window as unknown as {
    customCards?: Array<Record<string, unknown>>;
  };
  registry.customCards = registry.customCards ?? [];
  for (const { tag, name, description } of cards) {
    if (registry.customCards.some((card) => card.type === tag)) continue;
    registry.customCards.push({
      type: tag,
      name,
      description,
      preview: true,
      documentationURL: DOCUMENTATION_URL,
    });
  }
}
