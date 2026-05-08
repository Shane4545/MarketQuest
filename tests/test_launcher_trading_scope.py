from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acquisition.launcher_trading_scope import (  # noqa: E402
    merge_launcher_request_payload,
    merge_launcher_status_payload,
)


def test_merge_forces_safe_flags_even_if_user_requests_live() -> None:
    merged = merge_launcher_request_payload(
        {
            "run_purpose": "paper_research",
            "trading_enabled": True,
            "broker_execution_enabled": True,
            "live_orders_enabled": True,
            "approval_required_for_orders": False,
            "paper_only": False,
        }
    )
    assert merged["trading_enabled"] is False
    assert merged["broker_execution_enabled"] is False
    assert merged["live_orders_enabled"] is False
    assert merged["approval_required_for_orders"] is True
    assert merged["paper_only"] is True
    assert merged["run_purpose"] == "paper_research"


def test_invalid_run_purpose_reverts_to_research() -> None:
    merged = merge_launcher_request_payload({"run_purpose": "live_trade"})
    assert merged["run_purpose"] == "research"


def test_status_merge_matches_request_semantics() -> None:
    s = merge_launcher_status_payload({"run_purpose": "paper_research"})
    assert s["live_orders_enabled"] is False
    assert s["paper_only"] is True
