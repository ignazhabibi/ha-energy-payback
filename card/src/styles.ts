// Styles both cards share: category colors and the header.

import { css } from "lit";

export const cardStyles = css`
  :host {
    --energy-payback-pv-color: var(--energy-solar-color, #ff9800);
    --energy-payback-heat-pump-color: var(--energy-gas-color, #8e021b);
    --energy-payback-wallbox-color: var(--energy-non-fossil-color, #0f9d58);
  }
  ha-card {
    height: 100%;
    overflow: hidden;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 8px 0 16px;
  }
  .title {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: var(--ha-card-header-font-size, 24px);
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: 32px;
    letter-spacing: -0.012em;
    color: var(--ha-card-header-color, var(--primary-text-color));
  }
  .chip {
    font-size: 14px;
    font-weight: 500;
    line-height: 20px;
    padding: 4px 8px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    white-space: nowrap;
    color: var(--primary-text-color);
  }
  .summary {
    margin: 0;
    padding: 12px 16px 8px;
    color: var(--secondary-text-color);
  }
  .summary:empty {
    display: none;
  }
`;
