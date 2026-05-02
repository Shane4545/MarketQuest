# Stock Reality Scanner

Real-market-data scanner and historical backtesting for the AI Nation governance system. The core goal is **market reverse-engineering** using **real** historical data—not fictional sample prices.

## External research workflow (no live internet inside Cursor)

Development agents in Cursor **must not** rely on live internet market research in this environment.

1. A human asks **ChatGPT** (with live web access) to research the **last two completed trading days** and return a structured package (JSON or CSV) with at least: ticker symbol, exchange/market, instrument name, entry date, exit date, entry close, exit close, percent return, return multiple, data source, source link, fetch timestamp, and notes (splits, gaps, uncertainty).
2. The human saves that output as **`reports/live_market_snapshot.json`** (project convention).
3. Stock Reality Scanner **imports** that file, validates it, and runs **real historical hindsight scan** calculations only from rows that contain the required prices.
4. The app **must not invent** market data, **must not** claim a result without source prices, and must show **source and timestamp** for every displayed result. Use **small fake fixtures only in automated tests**, never as the main production outcome.

The analytical mode label for this path is **real historical hindsight scan**.

## Core question (Hindsight Optimizer)

“If I had **$100** two **completed** trading days ago, and I could choose the **best real market instrument** after knowing what happened, what would I have had **by yesterday**?”

This is a **hindsight optimizer**: it scans real historical data and finds the **best actual move** over a **selected completed period** (default: latest two completed trading days). It does **not** force any outcome (for example, it does **not** force $100,000,000).

### Target and gap (transparent reporting)

- Optional aspirational **target cash** (default **$100,000,000** from **$100**).
- **Required multiple** to hit that target from the starting stake: **1,000,000×** (for the defaults).
- The app **calculates** whether the scanned universe could actually reach the target from real data.
- If **no** instrument in the scan reaches the target, the UI and exports must state that clearly and show the **gap** (distance to target), **best real result**, and **achieved multiple**.
- If the honest answer is “nothing in the scanned universe came close,” the application must say so.

### Report fields (best real hindsight pick)

For the winning instrument over the period, outputs should include where applicable:

- Symbol  
- Entry date, exit date  
- Entry price, exit price  
- Percent return, **return multiple**  
- **Ending value** from the configured starting cash (e.g. $100)  
- **Distance** from the configured target (e.g. $100,000,000)  
- Data **source** and **fetch timestamp**  
- Warning if the **scan universe is limited**

## Two modes (must be visually distinct)

### 1. Real historical hindsight scan (prioritized)

Uses **imported** research rows (from ChatGPT-produced snapshots) to find the **best actual** result over the **completed** period encoded in the file. Allowed to “know the answer” because it looks backward. Used to reverse-engineer what would have worked.

### 2. Walk-forward strategy mode

Uses **only** information available **before** each simulated trade, then checks what happened next. Tests whether a **rule** could have made money **without** future knowledge.

**Labels**

- Hindsight Optimizer = “best possible past choice **after** knowing what happened.”  
- Walk-forward = “rule-based historical test **without** future leakage.”

## Constraints

- **Real** market data at runtime for production paths; do not use fictional prices as the main source.  
- Do **not** connect to broker accounts, place trades, or execute real-money orders.  
- Do **not** bypass paywalls, authentication, rate limits, or site restrictions.  
- Cache only small local evidence snapshots for testing and repeatability.

## Dashboard expectations (summary)

- Starting cash input (default **$100**), target cash input (default **$100,000,000**).  
- Lookback: default **latest two completed trading days**.  
- Ticker universe scanned; **warning** if the universe is limited.  
- Best real hindsight pick; ending value; required target multiple; achieved multiple; **target achieved** yes/no; source and timestamp.  

Purpose: **prove what the real historical data says**—including when the answer is that nothing in the universe came close to the target.
