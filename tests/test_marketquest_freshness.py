"""Freshness and scoring eligibility."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.freshness import (  # noqa: E402
    age_minutes,
    classify_freshness,
    is_scoring_eligible,
)


def test_stale_during_market_hours():
    old = (datetime.now(timezone.utc) - timedelta(minutes=21)).isoformat()
    age = age_minutes(old)
    assert classify_freshness(age, market_session_open=True, provider_ok=True) == "STALE"
    assert is_scoring_eligible("STALE", market_session_open=True) is False


def test_live_when_fresh():
    recent = datetime.now(timezone.utc).isoformat()
    age = age_minutes(recent)
    assert classify_freshness(age, market_session_open=True, provider_ok=True) == "LIVE"
    assert is_scoring_eligible("LIVE", market_session_open=True) is True
