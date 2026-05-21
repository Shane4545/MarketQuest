"""Momentum Agent — gap/rvol/composite ranking."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick, ensure_pick_schema
from marketquest.config import load_config, today_iso
from marketquest.data_sources.prices import fetch_prices_yfinance, simple_features


def run_momentum_agent(
    repo: Path,
    *,
    as_of: str | None = None,
    mock: bool = False,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    cfg = load_config(repo)
    syms = symbols or cfg["symbols"]

    if mock:
        from marketquest.scoring.orchestrator import load_fixture_picks

        picks = load_fixture_picks(repo)
        for p in picks:
            if p.get("agent_id") == "momentum":
                return ensure_pick_schema(p)
        return make_pick(
            symbol="NVDA",
            agent_id="momentum",
            as_of=as_of,
            score=0.72,
            predicted_bias="bullish",
            headline="Strong gap and relative volume (mock)",
            bullets=["gap_pct elevated", "rvol above average", "composite score leads watchlist"],
            features={"gap_pct": 4.2, "rvol": 2.1, "ml_predicted_return_1d_pct": 3.5},
            data_mode="mock",
        )

    prices_df = fetch_prices_yfinance(syms)
    rows = simple_features(prices_df, date.fromisoformat(as_of))
    top: dict[str, Any] | None = None
    weights = cfg.get("composite_weights") or {}

    if rows:
        try:
            from signals.aggressive_ranker import composite_score, rank_candidates

            news_map = {r["symbol"]: {} for r in rows}
            ranked = rank_candidates(rows, news_map, cfg, as_of=date.fromisoformat(as_of))
            top = ranked[0] if ranked else max(rows, key=lambda r: composite_score(r, weights))
        except Exception:
            from signals.aggressive_ranker import composite_score

            top = max(rows, key=lambda r: composite_score(r, weights))

    if not rows and not top:
        return make_pick(
            symbol=syms[0],
            agent_id="momentum",
            as_of=as_of,
            score=0.0,
            predicted_bias="neutral",
            headline="Insufficient price data",
            bullets=["Using default symbol"],
            features={},
            data_mode="mock",
        )

    top = top or rows[0]
    sym = str(top["symbol"])
    gap = float(top.get("gap_pct") or 0)
    rvol = float(top.get("rvol") or 1)
    score = float(top.get("composite_score") or top.get("ml_predicted_return_1d_pct") or 0)
    bias = "bullish" if gap > 0 else "bearish" if gap < 0 else "neutral"
    runners = [str(r["symbol"]) for r in rows if str(r["symbol"]) != sym][:3]

    return make_pick(
        symbol=sym,
        agent_id="momentum",
        as_of=as_of,
        score=score,
        predicted_bias=bias,
        headline=f"Momentum leader: {sym} (gap {gap:.2f}%, RVOL {rvol:.2f})",
        bullets=[
            f"Gap vs prior close: {gap:.2f}%",
            f"Relative volume: {rvol:.2f}x",
            f"ML/rule return estimate: {top.get('ml_predicted_return_1d_pct', '—')}%",
        ],
        features={
            "gap_pct": gap,
            "rvol": rvol,
            "ml_predicted_return_1d_pct": top.get("ml_predicted_return_1d_pct"),
            "composite_score": top.get("composite_score"),
        },
        data_mode="live",
        runners_up=runners,
    )
