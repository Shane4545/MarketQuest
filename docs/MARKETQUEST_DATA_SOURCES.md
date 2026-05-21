# MarketQuest Data Sources

MarketQuest uses **real public data only**. Paper portfolios and scoring are simulated.

## Provider priority (quotes)

1. **Finnhub** — `FINNHUB_API_KEY`
2. **Alpaca market data** — `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`
3. **yfinance** — fallback, labeled `DELAYED`

Optional: Alpaca stream when `MARKETQUEST_STREAM=1`.

## News and events

| Provider | Env / config | Notes |
|----------|--------------|-------|
| RSS | built-in | Yahoo, MarketWatch headlines |
| SEC EDGAR | none | Watchlist filings |
| FRED | `FRED_API_KEY` | Macro series: Fed Funds, CPI, VIX, WTI oil (`DCOILWTICO`), 10Y yield (`DGS10`), USD/CAD (`DEXCAUS`) |
| Forex (Finnhub) | `FINNHUB_API_KEY` | USD/CAD, EUR/USD; FRED fallback for USD/CAD |
| Government RSS | built-in | Bank of Canada, Federal Reserve press |
| Company press | `watchlists/default.json` → `press_rss` | IR RSS URLs |
| Finnhub news | `FINNHUB_API_KEY` | Company news when keyed |
| X API | `X_BEARER_TOKEN` | Official API only; OFFLINE if unset |

## Setup

Copy `config/marketquest.example.env` to `.env` (never commit secrets).

```bash
python app/scripts/run_viewer_api.py
python app/scripts/run_marketquest_reality.py --once
```

## Freshness

Every quote/event shows: provider, fetched time, age in minutes, label:

- `LIVE` / `DELAYED` / `STALE` / `OFFLINE`

During **market hours**, quote data older than **20 minutes** is `STALE` and excluded from AI competition scoring.

## OFFLINE TRAINING MODE

Use `?training=1` or `MARKETQUEST_OFFLINE_TRAINING=1` for fixtures only. The UI labels this clearly.

## Watchlist

Edit `app/data/marketquest/watchlists/default.json` — symbols, groups, and company press RSS URLs.

## Entity seed

Edit `app/data/marketquest/entity_seed.json` for people, organizations, themes, and relationship rules.

## Not investment advice

All outputs are paper predictions and educational signals.
