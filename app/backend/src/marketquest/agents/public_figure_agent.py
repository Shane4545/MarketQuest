"""Public figure agent — policy statements and entity-linked hypotheses."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_public_figure_from_snapshot(snapshot: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    events = snapshot.get("public_figure_events") or []
    if not events:
        events = [
            e
            for e in snapshot.get("news_events", [])
            if e.get("event_type") == "public_figure_statement"
        ]
    if not events:
        sym = (snapshot.get("symbols_checked") or ["SPY"])[0]
        return make_pick(
            symbol=str(sym).upper(),
            agent_id="public_figure",
            as_of=as_of,
            score=0.1,
            predicted_bias="neutral",
            headline="No public figure statements in current snapshot",
            bullets=["Monitor government and executive communications"],
            features={},
            prediction_type="watch",
            horizon="1h",
            confidence=0.1,
            reasons=["No fresh public figure events"],
            risks=["Policy statements can move markets quickly when they appear"],
        )

    best = max(events, key=lambda e: float(e.get("importance_score") or 0))
    tickers = best.get("candidate_tickers") or best.get("symbols") or snapshot.get("symbols_checked") or ["SPY"]
    sym = str(tickers[0]).upper()
    entities = best.get("entities") or []
    return make_pick(
        symbol=sym,
        agent_id="public_figure",
        as_of=as_of,
        score=float(best.get("importance_score") or 50) / 100,
        predicted_bias="neutral",
        headline=str(best.get("title", ""))[:120],
        bullets=[
            f"Entities: {', '.join(entities[:3]) or 'unknown'}",
            str(best.get("why_this_may_matter", ""))[:120],
        ],
        features={"event_type": best.get("event_type"), "entities": entities},
        prediction_type="watch",
        horizon="1h",
        confidence=min(float(best.get("importance_score") or 40) / 100, 0.85),
        expected_direction="unclear",
        reasons=[
            f"Public figure / policy signal: {best.get('event_type')}",
            f"Linked entities: {', '.join(entities[:2])}" if entities else "Entity link weak",
        ],
        risks=list(best.get("uncertainties") or [])[:3],
        source_event_ids=[str(best.get("event_id", ""))],
        news=[{"title": best.get("title"), "source": best.get("source")}],
        data_mode="live",
    )
