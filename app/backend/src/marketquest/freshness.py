"""Freshness classification and scoring eligibility."""

from __future__ import annotations

from datetime import datetime, timezone

STALE_THRESHOLD_MIN = 20


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def age_minutes(fetched_at: str, *, now: datetime | None = None) -> float:
    dt = parse_iso(fetched_at)
    if not dt:
        return 9999.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 60.0)


def classify_freshness(
    age_min: float,
    *,
    market_session_open: bool,
    provider_ok: bool,
    is_fallback: bool = False,
    stale_threshold: float = STALE_THRESHOLD_MIN,
) -> str:
    if not provider_ok:
        return "OFFLINE"
    if is_fallback:
        return "DELAYED"
    if market_session_open and age_min > stale_threshold:
        return "STALE"
    if age_min > 60:
        return "DELAYED"
    if age_min <= 5:
        return "LIVE"
    return "DELAYED"


def is_scoring_eligible(
    freshness: str,
    *,
    market_session_open: bool,
) -> bool:
    if freshness in ("OFFLINE", "STALE"):
        return False
    if market_session_open and freshness == "STALE":
        return False
    return freshness in ("LIVE", "DELAYED")


def attach_provenance(
    *,
    provider: str,
    fetched_at: str,
    market_timestamp: str | None,
    market_session_open: bool,
    provider_ok: bool,
    is_fallback: bool = False,
    error: str | None = None,
) -> dict:
    age = age_minutes(fetched_at)
    fresh = classify_freshness(
        age,
        market_session_open=market_session_open,
        provider_ok=provider_ok,
        is_fallback=is_fallback,
    )
    return {
        "provider": provider,
        "fetched_at": fetched_at,
        "market_timestamp": market_timestamp,
        "age_minutes": round(age, 2),
        "freshness": fresh,
        "fallback": is_fallback,
        "error": error,
        "scoring_eligible": is_scoring_eligible(fresh, market_session_open=market_session_open),
    }
