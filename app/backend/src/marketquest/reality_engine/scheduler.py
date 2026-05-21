"""Reality Engine scheduler loop."""

from __future__ import annotations

import time
from pathlib import Path

from marketquest.data_sources.market_hours import refresh_interval_seconds
from marketquest.reality_engine.collector import collect_snapshot


def run_loop(repo: Path, *, once: bool = False) -> None:
    while True:
        snap = collect_snapshot(repo, offline_training=False)
        print(
            f"[reality] snapshot {snap.get('timestamp_utc')} "
            f"market={snap.get('market_status')} "
            f"prices={len(snap.get('prices', []))} "
            f"scoring_ok={snap.get('scoring_data_eligible')}"
        )
        if once:
            return
        interval = refresh_interval_seconds()
        time.sleep(interval)
