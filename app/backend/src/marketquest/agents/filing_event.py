"""Filing/Event agent — SEC-weighted picks from snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso
from marketquest.events.classifier import classify_filing


def run_filing_event_from_snapshot(
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or snapshot.get("timestamp_utc", today_iso())[:10]
    filings = snapshot.get("sec_filings", [])
    if not filings:
        sym = (snapshot.get("symbols_checked") or ["SPY"])[0]
        return make_pick(
            symbol=sym,
            agent_id="filing_event",
            as_of=as_of,
            score=0,
            predicted_bias="neutral",
            headline="No recent SEC filings in snapshot",
            bullets=["EDGAR fetch may be rate-limited"],
            features={},
            data_mode="live",
        )
    best = max(
        filings,
        key=lambda f: (1 if classify_filing(f.get("form_type", "")) == "sec_8k" else 0, f.get("filed_at", "")),
    )
    sym = best.get("symbol", "SPY")
    return make_pick(
        symbol=sym,
        agent_id="filing_event",
        as_of=as_of,
        score=0.6,
        predicted_bias="neutral",
        headline=f"Filing pick: {sym} ({best.get('form_type')})",
        bullets=[f"Filed {best.get('filed_at')}", f"Category: {classify_filing(best.get('form_type', ''))}"],
        features={"form_type": best.get("form_type")},
        data_mode="live",
    )
