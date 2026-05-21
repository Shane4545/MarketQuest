"""Snapshot path and round-trip."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.paths import snapshot_path_for  # noqa: E402
from marketquest.reality_engine.snapshot import load_latest_snapshot, write_snapshot  # noqa: E402


def test_snapshot_path_hhmm():
    p = snapshot_path_for(ROOT, "2026-05-20T14:30:00+00:00")
    assert "2026-05-20" in str(p)
    assert p.name.endswith(".json")


def test_write_and_load_snapshot(tmp_path):
    repo = tmp_path
    (repo / "app" / "scripts").mkdir(parents=True)
    (repo / "app" / "data" / "marketquest" / "snapshots").mkdir(parents=True)
    payload = {
        "timestamp_utc": "2026-05-20T15:00:00+00:00",
        "market_status": "open",
        "prices": [{"symbol": "SPY", "last": 500}],
        "scoring_data_eligible": True,
        "offline_training_mode": False,
    }
    write_snapshot(repo, payload)
    loaded = load_latest_snapshot(repo)
    assert loaded is not None
    assert loaded["prices"][0]["symbol"] == "SPY"
