"""
Trading-scope defaults for governed run launcher artifacts.

Current phase: research and paper-basket workflows only. Execution hooks are disabled.
This module centralizes safe defaults so a future run launcher can attach brokerage/intent
layers without rewriting artifact shape.

Human Supreme / compliance: booleans here are enforced for artifact writes in-repo;
callers must merge via merge_launcher_request_payload / merge_launcher_status_payload.
"""

from __future__ import annotations

from typing import Any

ALLOWED_RUN_PURPOSES = frozenset({"research", "paper_research", "aggressive_pencil"})


def default_trading_flags_for_request() -> dict[str, Any]:
    """Canonical defaults for launcher_request.json trading-related fields."""
    return {
        "run_purpose": "research",
        "trading_enabled": False,
        "broker_execution_enabled": False,
        "live_orders_enabled": False,
        "approval_required_for_orders": True,
        "max_loss_limit": None,
        "max_position_size": None,
        "paper_only": True,
    }


def default_trading_flags_for_status() -> dict[str, Any]:
    """Canonical defaults for launcher_status.json (mirrors request for audit trail)."""
    return {
        "run_purpose": "research",
        "trading_enabled": False,
        "broker_execution_enabled": False,
        "live_orders_enabled": False,
        "approval_required_for_orders": True,
        "max_loss_limit": None,
        "max_position_size": None,
        "paper_only": True,
    }


def _normalize_run_purpose(raw: object | None) -> str:
    v = (str(raw).strip() if raw is not None else "") or "research"
    if v not in ALLOWED_RUN_PURPOSES:
        return "research"
    return v


def _enforce_current_phase_safety(d: dict[str, Any]) -> dict[str, Any]:
    """Force safe values: no live broker, no live orders, no implied production trading."""
    out = dict(d)
    out["trading_enabled"] = False
    out["broker_execution_enabled"] = False
    out["live_orders_enabled"] = False
    out["approval_required_for_orders"] = True
    out["paper_only"] = True
    out["run_purpose"] = _normalize_run_purpose(out.get("run_purpose"))
    if "max_loss_limit" not in out:
        out["max_loss_limit"] = None
    if "max_position_size" not in out:
        out["max_position_size"] = None
    return out


def merge_launcher_request_payload(user: dict[str, Any] | None) -> dict[str, Any]:
    """
    Merge user launcher fields with defaults and current-phase safety enforcement.
    User cannot enable live trading or broker execution via this merge in the current phase.
    """
    base = default_trading_flags_for_request()
    allowed = set(base.keys())
    if user:
        base.update({k: v for k, v in user.items() if k in allowed})
    return _enforce_current_phase_safety(base)


def merge_launcher_status_payload(user: dict[str, Any] | None) -> dict[str, Any]:
    """Same safety rules for launcher_status.json."""
    base = default_trading_flags_for_status()
    allowed = set(base.keys())
    if user:
        base.update({k: v for k, v in user.items() if k in allowed})
    return _enforce_current_phase_safety(base)
