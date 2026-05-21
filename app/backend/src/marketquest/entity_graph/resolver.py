"""Resolve entities and tickers from event text."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.entity_graph.relationship_rules import get_impact_for_event
from marketquest.entity_graph.ticker_mapper import extract_entities_from_text, map_text_to_tickers


def resolve_entities(
    text: str,
    event_type: str,
    repo: Path,
    *,
    watchlist: list[str] | None = None,
    existing_symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Return entities, candidate tickers, and impact hypotheses for an event."""
    entities = extract_entities_from_text(text, repo)
    candidate_tickers = map_text_to_tickers(text, repo, watchlist)
    for sym in existing_symbols or []:
        s = str(sym).upper()
        if s not in candidate_tickers:
            candidate_tickers.append(s)

    # Brookfield / Carney special chain hint
    lower = text.lower()
    if "brookfield" in lower or "carney" in lower:
        for t in ("BAM", "BN"):
            if t not in candidate_tickers:
                candidate_tickers.append(t)
        if "Mark Carney" not in entities and "carney" in lower:
            entities.append("Mark Carney")
        if "Brookfield" not in entities and "brookfield" in lower:
            entities.append("Brookfield")

    impact_type = event_type
    if "brookfield" in lower or ("carney" in lower and "brookfield" in " ".join(entities).lower()):
        impact_type = "brookfield_related"

    impact = get_impact_for_event(impact_type, entities)
    rule_tickers = impact.get("candidate_tickers") or []
    for t in rule_tickers:
        if t not in candidate_tickers:
            candidate_tickers.append(t)

    return {
        "entities": entities,
        "candidate_tickers": candidate_tickers[:10],
        "possible_positive_impacts": impact.get("possible_positive_impacts", []),
        "possible_negative_impacts": impact.get("possible_negative_impacts", []),
        "uncertainties": impact.get("uncertainties", []),
        "affected_sectors": impact.get("affected_sectors", []),
        "why_this_may_matter": _why_summary(event_type, entities, impact),
    }


def _why_summary(event_type: str, entities: list[str], impact: dict[str, Any]) -> str:
    ent = ", ".join(entities[:3]) if entities else "unknown entities"
    pos = impact.get("possible_positive_impacts", [])
    neg = impact.get("possible_negative_impacts", [])
    parts = [f"Educational signal: {event_type} involving {ent}."]
    if pos:
        parts.append(f"Possible positive themes: {'; '.join(pos[:2])}.")
    if neg:
        parts.append(f"Possible negative themes: {'; '.join(neg[:2])}.")
    parts.append("Not investment advice — paper hypothesis only.")
    return " ".join(parts)
