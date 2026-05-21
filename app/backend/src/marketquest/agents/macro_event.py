"""Macro/Event Agent — earnings/financing keyword catalysts."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick, ensure_pick_schema
from marketquest.config import load_config, today_iso


def _event_score(nf: dict[str, Any]) -> float:
    score = 0.0
    if nf.get("has_earnings_keyword"):
        score += 0.5
    if nf.get("has_financing_keyword"):
        score += 0.35
    if nf.get("dilution_flag"):
        score += 0.25
    score += 0.1 * int(nf.get("news_count_48h") or 0)
    return score


def run_macro_event_agent(
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

        for p in load_fixture_picks(repo):
            if p.get("agent_id") == "macro_event":
                return ensure_pick_schema(p)
        return make_pick(
            symbol="AMD",
            agent_id="macro_event",
            as_of=as_of,
            score=0.58,
            predicted_bias="neutral",
            headline="Earnings/macro event signal (mock)",
            bullets=["earnings keyword detected", "event-driven catalyst"],
            features={"has_earnings_keyword": True, "news_count_48h": 3},
            news=[{"title": "Mock: earnings preview", "sentiment": 0.1, "source": "fixture"}],
            data_mode="mock",
        )

    nf_map: dict[str, dict[str, Any]] = {}
    batch: dict[str, list] = {}
    try:
        from news.catalyst_gate import passes_catalyst_gate
        from news.fetch_news import fetch_news_batch
        from news.sentiment_scorer import build_news_feature_map

        end = date.today()
        start = end - timedelta(days=5)
        batch = fetch_news_batch(syms, start, end)
        nf_map = build_news_feature_map(batch, cfg)
    except Exception:
        pass

    best_sym = syms[0]
    best_score = -1.0
    best_nf: dict[str, Any] = {}
    best_reason = "no macro events detected"

    for sym in syms:
        nf = nf_map.get(sym.upper(), {})
        ev = _event_score(nf)
        row = {"symbol": sym.upper(), **nf}
        try:
            from news.catalyst_gate import passes_catalyst_gate

            ok, reason = passes_catalyst_gate(row, nf, cfg)
            if ok:
                ev += 0.2
        except Exception:
            reason = ""
        if ev > best_score:
            best_score = ev
            best_sym = sym.upper()
            best_nf = nf
            best_reason = reason or "keyword catalyst"

    news_ui = []
    for art in batch.get(best_sym, [])[:5]:
        news_ui.append(
            {
                "title": str(art.get("title") or "Event"),
                "sentiment": 0.0,
                "source": str(art.get("publisher") or "news"),
            }
        )

    flags = []
    if best_nf.get("has_earnings_keyword"):
        flags.append("earnings")
    if best_nf.get("has_financing_keyword"):
        flags.append("financing")
    if best_nf.get("dilution_flag"):
        flags.append("dilution")

    return make_pick(
        symbol=best_sym,
        agent_id="macro_event",
        as_of=as_of,
        score=best_score,
        predicted_bias="neutral" if best_nf.get("dilution_flag") else "bullish",
        headline=f"Macro/event pick: {best_sym} ({best_reason})",
        bullets=[
            f"Event flags: {', '.join(flags) or 'general news flow'}",
            f"Catalyst score: {best_score:.2f}",
            "Macro V0 uses news keyword tags (FRED/sector feeds in V1)",
        ],
        features=best_nf,
        news=news_ui,
        data_mode="live" if nf_map else "mock",
        runners_up=[s for s in syms if s.upper() != best_sym][:3],
    )
