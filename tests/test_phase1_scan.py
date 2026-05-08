"""Phase 1 scanner tests — synthetic symbols only (no listed equities)."""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "backend" / "src"))

from phase1.scan_rules import apply_momentum_volume_pressure  # noqa: E402


def test_rule_accepts_clean_row():
    cfg = yaml.safe_load(
        """
momentum_volume_pressure:
  min_prior_5d_return_pct: 20
  min_volume_surge: 2.0
  min_close_location_value: 0.60
  require_market_cap: true
  weak_close_clv_max: 0.35
  blowoff_min_volume_surge: 4.5
  blowoff_min_prior_5d_return_pct: 45
"""
    )["momentum_volume_pressure"]
    row = {
        "symbol": "TEST_X",
        "prior_5d_return_pct": 25.0,
        "volume_surge": 3.0,
        "close_location_value": 0.7,
        "close_weak_flag": False,
        "blowoff_flag": False,
        "market_cap_missing_flag": False,
        "insufficient_evidence": False,
        "missing_required_ohlcv": False,
    }
    st, reason = apply_momentum_volume_pressure(row, cfg)
    assert st == "selected"
    assert "passed" in reason


def test_rule_rejects_weak_close():
    cfg = yaml.safe_load(
        """
momentum_volume_pressure:
  min_prior_5d_return_pct: 20
  min_volume_surge: 2.0
  min_close_location_value: 0.60
  require_market_cap: true
  weak_close_clv_max: 0.35
  blowoff_min_volume_surge: 4.5
  blowoff_min_prior_5d_return_pct: 45
"""
    )["momentum_volume_pressure"]
    row = {
        "symbol": "TEST_Y",
        "prior_5d_return_pct": 50.0,
        "volume_surge": 5.0,
        "close_location_value": 0.1,
        "close_weak_flag": True,
        "blowoff_flag": False,
        "market_cap_missing_flag": False,
        "insufficient_evidence": False,
        "missing_required_ohlcv": False,
    }
    st, reason = apply_momentum_volume_pressure(row, cfg)
    assert st == "rejected"
    assert "weak" in reason.lower()
