# Time Traveller Stock Optimizer (Stock Reality Scanner)

This project is a **Time Traveller Stock Optimizer**: you **pretend** you already know **future historical** market outcomes (because they are **past** completed prices), go back to chosen dates with a chosen dollar amount, and ask:

**“Knowing what actually happened in the market, what stock or sequence of stocks should I have bought to make the most money?”**

This is **perfect hindsight optimization** using **real historical market data**.

It is **not** future prediction.  
It is **not** financial advice.  
It is **not** real trading or broker automation.

---

## Data reality (Cursor and imports)

Cursor may **not** have reliable live internet. The application must therefore **import externally generated** market packages (for example from ChatGPT with live web access or another approved collector).

Supported inputs include:

- `reports/live_market_snapshot.json`
- `reports/historical_market_data.json`
- `reports/historical_market_data.csv`

Imports must include enough fields to compute factual results (ticker, exchange/market, name, dates, OHLC where available, adjusted close where available, volume where available, source name, source link, fetch timestamp, caveats).

The application **must never invent prices**. It **must never claim** a factual result unless the imported data contains the **required prices**. It **must** surface limited-universe warnings.

Use **small synthetic fixtures only in automated tests**, never as the production source of truth.

---

## Mode 1 — Latest One-Day Time Traveller Scan

Answers exactly:

**“If I went back to yesterday’s market close with $100 and already knew today’s market result, what stock or instrument should I have bought yesterday to have the most money today?”**

Behavior:

- Uses the **two most recent completed trading days** present in the imported data as **start** (previous session) and **end** (latest session).
- **Holding period:** one completed trading day.
- **Perfect hindsight:** ranks **actual** one-day movers in the scanned universe; shows **best pick**, entry/exit dates, closes, **percent return**, **return multiple**, ending value from chosen starting cash, **target cash** comparison, **sources**, **timestamps**, **caveats**, **skipped tickers**.
- Results must be labeled **known historical outcome**, not a prediction.

**Dashboard:** include a **Latest One-Day Time Traveller Scan** preset control that selects those two dates, runs the one-day scan, ranks movers, and shows ending cash vs target.

---

## Mode 2 — Historical Time Traveller Path Optimizer

User selects starting cash, target cash, start date, end date, and universe (from imported data).

Answers:

**“If I had this starting cash on the historical start date and already knew all prices after that, what exact stock or sequence would maximize ending value by the end date?”**

### A. Single Best Trade

- Buy **one** instrument on **start date**, sell on **end date**.  
- Pick the instrument with the **best actual** return in the scanned universe over that span.

### B. Perfect Daily Switching

- Each session: pick the instrument with the **best actual next-day** return, invest **full** cash (fractional shares by default), sell next completed session, repeat through **end date**.  
- Output the **full trade path** (trade #, ticker, name, entry/exit dates, closes, returns, multiples, cash before/after, sources, links, caveats).

### Summary outputs

Starting cash, target cash, ending cash, target reached, required vs achieved multiple, distance from target, best single-trade path vs daily-switching path, ranked opportunities where applicable, skipped tickers / missing data, sources and timestamps, **warning** that results apply **only** to the scanned universe.

---

## Walk-forward strategy (separate, optional)

**Walk-forward** uses **only** information available **before** each simulated decision—**no** peeking at future prices. It is **not** Time Traveller mode and must stay visually and logically separate.

---

## User interface (expectations)

- **Title:** Time Traveller Stock Optimizer  
- **Mode selector:** Latest One-Day Time Traveller Scan · Single Best Trade · Perfect Daily Switching · Walk-forward (optional/later)  
- Starting cash (default **100**), target cash (default **1,000,000**), date pickers, file loader for imported data, universe summary, run control, best pick, ending cash, target reached, multiples, distance, trade-path table, ranked table, sources/timestamps, caveats/missing data.  
- **Banner:** *Perfect hindsight mode uses already-known historical outcomes. It is not a future prediction.*

---

## Constraints

Do **not** connect to broker accounts, place trades, or execute real-money orders. Do **not** bypass site terms, paywalls, or rate limits when gathering data outside this app.

Purpose: show **what the imported historical data implies** under explicit hindsight rules—including when the universe is incomplete or the target is unreachable.
