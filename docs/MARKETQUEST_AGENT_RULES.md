# MarketQuest Agent Rules

## Purpose

AI agents consume the **same reality snapshot** and output **paper hypotheses** — not buy/sell advice.

## Benchmark roster (10 required)

| # | Player | Role |
|---|--------|------|
| 1 | Random Baseline | **Mandatory** — honesty benchmark |
| 2 | SPY Baseline | S&P 500 proxy |
| 3 | QQQ Baseline | Nasdaq-100 proxy |
| 4 | Equal-Weight Watchlist | Diversified basket baseline |
| 5 | Simple Momentum Baseline | Transparent top-momentum rule |
| 6 | News-Only Agent | Headline freshness only |
| 7 | Macro Agent | Rates, inflation, macro indicators |
| 8 | Filing Agent | SEC filings as events |
| 9 | Entity Graph Agent | Person → org → ticker chains |
| 10 | Ensemble Agent | Weighted consensus; skeptic-adjusted |

Additional agents: Momentum, Public Figure, **Skeptic** (mandatory on AI picks), Human Baseline.

## Comparison disclosure

The UI must show honest benchmark comparisons:

- AI vs random, SPY, QQQ, momentum, prior week
- Auto-generated strings only: *"Ensemble beat SPY this week in paper scoring"*
- Never: *"beat Wall Street"* or *"better than Edward Jones"*

## Prediction schema

Each pick includes:

- `prediction_type`: `paper_long` | `avoid` | `watch`
- `horizon`: `15m` | `1h` | `1d` | `1w`
- `confidence`, `expected_direction`, `reasons`, `risks`
- `player_type`: `benchmark` | `agent` | `human`
- `source_event_ids` when tied to radar events

## Wording rules

**Use:** paper prediction, AI hypothesis, educational signal, not investment advice.

**Never use:** buy this, guaranteed winner, will go up, free money, beat brokers.

## Skeptic mandate

The Skeptic agent runs on AI picks every snapshot. Passive index baselines are not skeptic-scored.

## Random baseline honesty

If random baseline outperforms AI over time, the leaderboard and UI must disclose that.

## Learning

Nightly review updates `app/data/marketquest/learning/agent_scores.json`. Mini-challenges award learning points in `player_scores.json`.
