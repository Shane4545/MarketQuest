"""Entity graph agent — second-order relationship chain hypotheses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso
from marketquest.entity_graph.graph_store import GraphStore


def run_entity_graph_from_snapshot(
    snapshot: dict[str, Any],
    repo: Path,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    chains = snapshot.get("entity_graph_updates") or GraphStore(repo).load().get("recent_chains", [])

    if not chains:
        events = snapshot.get("news_events") or []
        if events:
            ev = events[0]
            tickers = ev.get("candidate_tickers") or ev.get("symbols") or ["SPY"]
            sym = str(tickers[0]).upper()
            return make_pick(
                symbol=sym,
                agent_id="entity_graph",
                as_of=as_of,
                score=0.3,
                predicted_bias="neutral",
                headline=f"Entity link from event: {ev.get('title', '')[:80]}",
                bullets=[str(ev.get("why_this_may_matter", ""))[:100]],
                features={"chain_depth": 1},
                prediction_type="watch",
                horizon="1d",
                confidence=0.35,
                reasons=["Single-hop entity mapping from latest event"],
                risks=["Second-order effects uncertain"],
                source_event_ids=[str(ev.get("event_id", ""))],
            )
        sym = (snapshot.get("symbols_checked") or ["SPY"])[0]
        return make_pick(
            symbol=str(sym).upper(),
            agent_id="entity_graph",
            as_of=as_of,
            score=0,
            predicted_bias="neutral",
            headline="No entity graph chains in snapshot",
            bullets=["Graph updates when events link people, orgs, and tickers"],
            features={},
            prediction_type="watch",
            horizon="1d",
            confidence=0.1,
            reasons=["No graph activity"],
            risks=["Relationship hypotheses require fresh events"],
        )

    chain = chains[0]
    tickers = chain.get("candidate_tickers") or snapshot.get("symbols_checked") or ["SPY"]
    sym = str(tickers[0]).upper()
    entities = chain.get("entities") or []
    chain_desc = " → ".join(entities[:3]) if entities else "event chain"
    return make_pick(
        symbol=sym,
        agent_id="entity_graph",
        as_of=as_of,
        score=0.45,
        predicted_bias="neutral",
        headline=f"Graph chain: {chain_desc} → {sym}",
        bullets=[
            f"Event: {chain.get('title', '')[:80]}",
            f"Candidate tickers: {', '.join(tickers[:4])}",
        ],
        features={"entities": entities, "chain_tickers": tickers},
        prediction_type="watch",
        horizon="1d",
        confidence=0.5,
        expected_direction="unclear",
        reasons=[
            f"Entity graph linked {chain_desc} to watchlist tickers",
            "Educational second-order hypothesis — not investment advice",
        ],
        risks=["Correlation ≠ causation", "Market may have priced narrative already"],
        source_event_ids=[str(chain.get("event_id", ""))],
        data_mode="live",
    )
