"""US equity market hours (Eastern Time)."""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def now_et() -> datetime:
    return datetime.now(ET)


def market_status(dt: datetime | None = None) -> str:
    """Return open | closed | pre | post."""
    dt = dt or now_et()
    if dt.weekday() >= 5:
        return "closed"
    t = dt.time()
    if time(9, 30) <= t < time(16, 0):
        return "open"
    if time(4, 0) <= t < time(9, 30):
        return "pre"
    if time(16, 0) <= t < time(20, 0):
        return "post"
    return "closed"


def is_regular_session_open(dt: datetime | None = None) -> bool:
    return market_status(dt) == "open"


def refresh_interval_seconds(dt: datetime | None = None) -> int:
    return 900 if is_regular_session_open(dt) else 3600
