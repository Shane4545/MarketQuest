# MarketQuest Product Spec

## One-line definition

**MarketQuest is a Wall Street intelligence learning game — real-world data, paper scoring, honest competition.**

See [MARKETQUEST_MISSION.md](MARKETQUEST_MISSION.md) for mission, honesty rules, and forbidden wording.

Event radar first — picks are an **output** of the radar, not the product core.

## What is real vs simulated

| Real (required) | Simulated only |
|-----------------|----------------|
| Tickers, prices, movement | Cash, orders, fills |
| Headlines, SEC filings, macro, gov RSS | Broker execution |
| Entity-linked event hypotheses | Margin, short, options, crypto (V0) |

## Run

```bash
python app/scripts/run_viewer_api.py
python app/scripts/run_marketquest_reality.py --once   # collect snapshot
python app/scripts/run_marketquest_reality.py --daemon # 15m / 60m loop
python app/scripts/marketquest_nightly_review.py       # learning report
```

- **App:** http://127.0.0.1:8010/marketquest
- **Offline training:** http://127.0.0.1:8010/marketquest?training=1
- **Refresh:** UI button or `POST /api/marketquest/refresh`

## Reality Engine

Snapshots: `app/data/marketquest/snapshots/YYYY-MM-DD/HHMM.json`

Includes: prices, classified events, public figure events, entity graph updates, agent picks, freshness, `scoring_data_eligible`.

See [MARKETQUEST_DATA_SOURCES.md](MARKETQUEST_DATA_SOURCES.md) for providers and API keys.

## UI sections

1. World Connects — USD/CAD, oil, yields with freshness badges
2. Live Reality Status Bar — session, freshness, provider badges
3. Event Radar — classified events with entities, tickers, importance
4. Live Watchlist — quotes with provenance
5. AI Picks Today — paper hypotheses table
6. Benchmark Scoreboard — AI vs random, SPY, QQQ, momentum comparisons
7. Agent Debate — per-ticker agent statements + skeptic
8. Entity Graph — person → org → ticker chains (hypothesis only)
9. Paper Portfolio + Leaderboard — humans, agents, benchmarks (split)
10. Learning Lab — nightly review snippets + scout link
11. Education & Challenges — glossary, lesson cards, daily mini-challenge
12. Future Builder — career cards
13. AI Tool Scout — research registry (FinRL, FRED, Finnhub, etc.)

## API

- `GET /api/marketquest/dashboard`
- `GET /api/marketquest/status`
- `POST /api/marketquest/refresh`
- `GET /api/marketquest/snapshot/latest`
- `GET /api/marketquest/events`
- `GET /api/marketquest/picks`
- `GET /api/marketquest/agents?symbol=NVDA`
- `GET /api/marketquest/entity-graph`
- `GET /api/marketquest/portfolio`
- `POST /api/marketquest/paper-order`
- `GET /api/marketquest/leaderboard`
- `GET /api/marketquest/learning-report`
- `GET /api/marketquest/education/glossary`
- `GET /api/marketquest/education/lessons?context=filing`
- `GET /api/marketquest/challenges/active`
- `POST /api/marketquest/challenges/submit`
- `GET /api/marketquest/careers`
- `GET /api/marketquest/research/registry?category=macro_data`
- `GET /api/marketquest/research/report`

## Tests

```bash
python -m pytest tests/test_marketquest_*.py -q
```

## Agent rules

See [MARKETQUEST_AGENT_RULES.md](MARKETQUEST_AGENT_RULES.md).

## Non-goals

- Real-money orders
- Paywall bypass / scraped X without API
- Investment advice wording
- Extending `stock_reality_scanner/`, Time Traveller, or governance evidence unless requested
