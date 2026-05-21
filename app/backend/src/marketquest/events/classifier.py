"""Tag real-world event categories from headlines and filings."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketquest.entity_graph.resolver import resolve_entities
from marketquest.events.event_deduper import dedupe_events
from marketquest.events.event_importance import score_importance
from marketquest.events.event_schema import raw_to_event_dict

EARNINGS = re.compile(r"\b(earnings|eps|revenue|guidance)\b", re.I)
MERGER = re.compile(r"\b(merger|acquisition|buyout|takeover)\b", re.I)
FDA = re.compile(r"\b(FDA|approval|clinical trial|phase [123])\b", re.I)
LAWSUIT = re.compile(r"\b(lawsuit|SEC investigation|regulatory|fine)\b", re.I)
PRODUCT = re.compile(r"\b(launch|product|partnership)\b", re.I)
ANALYST = re.compile(r"\b(upgrade|downgrade|price target|analyst)\b", re.I)
MACRO_RATE = re.compile(r"\b(Fed|rate decision|FOMC|interest rate|yield)\b", re.I)
MACRO_INFLATION = re.compile(r"\b(inflation|CPI|PPI|consumer prices)\b", re.I)
MACRO_JOBS = re.compile(r"\b(jobs report|unemployment|nonfarm|payrolls)\b", re.I)
VOLUME = re.compile(r"\b(unusual volume|volume surge)\b", re.I)
GAP = re.compile(r"\b(gap up|gap down|gapped)\b", re.I)
TARIFF = re.compile(r"\b(tariff|tariffs|trade war|sanctions|import duty)\b", re.I)
GOVERNMENT = re.compile(r"\b(Cabinet|Parliament|White House|policy|legislation|infrastructure plan)\b", re.I)
INFRA = re.compile(r"\b(infrastructure|pipeline|port|PPP|public-private)\b", re.I)
ENERGY = re.compile(r"\b(oil|OPEC|crude|energy shock|gas prices)\b", re.I)
DEFENSE = re.compile(r"\b(defense spending|military|NATO|weapons)\b", re.I)
AI_DC = re.compile(r"\b(AI|data center|GPU|artificial intelligence)\b", re.I)
PUBLIC_FIGURE = re.compile(
    r"\b(Trump|Carney|Powell|Musk|Cook|Huang|President|Prime Minister|CEO)\b", re.I
)
MANAGEMENT = re.compile(r"\b(CEO resign|CFO resign|management change|steps down)\b", re.I)


def classify_news(headline: str, *, form_hint: str = "") -> str:
    text = f"{headline} {form_hint}"
    if PUBLIC_FIGURE.search(text) and not EARNINGS.search(text):
        return "public_figure_statement"
    if TARIFF.search(text):
        return "tariff_trade"
    if GOVERNMENT.search(text) or INFRA.search(text):
        if INFRA.search(text):
            return "infrastructure_project"
        return "government_policy"
    if ENERGY.search(text):
        return "energy_oil_shock"
    if DEFENSE.search(text):
        return "defense_spending"
    if AI_DC.search(text):
        return "ai_data_center"
    if EARNINGS.search(text):
        return "earnings"
    if MERGER.search(text):
        return "merger_acquisition"
    if FDA.search(text):
        return "fda_healthcare"
    if LAWSUIT.search(text):
        return "lawsuit_regulation"
    if MANAGEMENT.search(text):
        return "management_change"
    if PRODUCT.search(text):
        return "product_launch"
    if ANALYST.search(text):
        return "analyst_rating"
    if MACRO_INFLATION.search(text):
        return "macro_inflation"
    if MACRO_JOBS.search(text):
        return "macro_jobs"
    if MACRO_RATE.search(text):
        return "macro_rates"
    if VOLUME.search(text):
        return "unusual_volume"
    if GAP.search(text):
        return "price_breakout"
    return "headline"


def classify_filing(form_type: str) -> str:
    ft = form_type.upper()
    if ft.startswith("8-K"):
        return "sec_8k"
    if ft in ("10-K", "10-Q"):
        return "sec_10q_10k"
    if "4" in ft:
        return "insider_transaction"
    return "sec_filing"


def enrich_news_event(event: dict[str, Any]) -> dict[str, Any]:
    event = dict(event)
    event["category"] = classify_news(
        str(event.get("headline", "")),
        form_hint=str(event.get("form_type", "")),
    )
    return event


def classify_and_enrich(
    raw: dict[str, Any],
    repo: Path,
    *,
    watchlist: list[str] | None = None,
) -> dict[str, Any]:
    """Full pipeline: normalize → classify → entity resolve → importance."""
    ev = raw_to_event_dict(raw)
    headline = ev["title"]
    form = str(raw.get("form_type") or "")
    if form:
        ev["event_type"] = classify_filing(form)
    else:
        ev["event_type"] = classify_news(headline, form_hint=form)

    text = f"{headline} {ev.get('summary', '')}"
    resolved = resolve_entities(
        text,
        ev["event_type"],
        repo,
        watchlist=watchlist,
        existing_symbols=ev.get("symbols"),
    )
    ev.update(resolved)
    if ev.get("source_url") and ev["source_url"] not in ev.get("source_links", []):
        ev.setdefault("source_links", []).append(ev["source_url"])
    ev["importance_score"] = score_importance(ev, watchlist)
    return ev


def process_event_batch(
    raw_events: list[dict[str, Any]],
    repo: Path,
    *,
    watchlist: list[str] | None = None,
) -> list[dict[str, Any]]:
    deduped = dedupe_events(raw_events)
    classified = [classify_and_enrich(r, repo, watchlist=watchlist) for r in deduped]
    classified.sort(key=lambda e: float(e.get("importance_score") or 0), reverse=True)
    return classified
