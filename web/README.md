# Web Dashboard

Local dashboard for Stock Reality Scanner results.

Must make **Hindsight Optimizer** versus **Walk-forward strategy** visually distinct.

Expected controls and displays (see `stock_reality_scanner/README.md`):

- Starting cash input (default **$100**), target cash input (default **$100,000,000**).
- Selected lookback period (default **latest two completed trading days**).
- Ticker universe scanned; **warning** when the universe is limited.
- Best real hindsight pick; ending value from starting cash; **required** target multiple (**1,000,000×** for default targets); **achieved** multiple; **target achieved** yes/no; gap/distance to target when not achieved; source and fetch timestamp.
