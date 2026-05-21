"""Immutable daily pencil journal read/write."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pencil.paths import journal_path_for_date


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_journal(signal_date: str, cfg: dict | None = None) -> dict[str, Any] | None:
    path = journal_path_for_date(signal_date, cfg)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_journal(entry: dict[str, Any], cfg: dict | None = None, *, allow_overwrite: bool = False) -> Path:
    signal_date = str(entry["signal_date"])
    path = journal_path_for_date(signal_date, cfg)
    if path.is_file() and not allow_overwrite:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("status") != "superseded":
            raise FileExistsError(f"Journal already exists for {signal_date}; use supersede to replace")
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return path


def record_skip(
    signal_date: str,
    reason: str,
    *,
    balance_usd: float,
    cfg: dict | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "signal_date": signal_date,
        "action": "skip",
        "status": "skipped",
        "reason": reason,
        "balance_before_usd": round(float(balance_usd), 2),
        "balance_after_usd": round(float(balance_usd), 2),
        "picks": [],
        "recorded_at": _utc_now(),
        "meta": meta or {},
    }
    c = cfg
    if c:
        entry["starting_balance_usd"] = c.get("starting_balance_usd", 100)
        entry["monthly_profit_target_usd"] = c.get("monthly_profit_target_usd", 90)
    write_journal(entry, cfg)
    return entry


def record_pick_entry(
    signal_date: str,
    picks: list[dict[str, Any]],
    *,
    balance_usd: float,
    cfg: dict | None = None,
    rationale: dict[str, Any] | None = None,
    mode: str = "after_close",
) -> dict[str, Any]:
    c = cfg or {}
    entry = {
        "signal_date": signal_date,
        "action": "pick",
        "status": "pending",
        "mode": mode,
        "balance_before_usd": round(float(balance_usd), 2),
        "starting_balance_usd": c.get("starting_balance_usd", 100),
        "monthly_profit_target_usd": c.get("monthly_profit_target_usd", 90),
        "allocation_mode": c.get("allocation_mode", "concentrated_top1"),
        "picks": picks,
        "rationale": rationale or {},
        "recorded_at": _utc_now(),
    }
    write_journal(entry, cfg)
    return entry


def supersede_journal(signal_date: str, new_entry: dict[str, Any], cfg: dict | None = None) -> dict[str, Any]:
    old = load_journal(signal_date, cfg)
    if old:
        old["status"] = "superseded"
        old["superseded_at"] = _utc_now()
        path = journal_path_for_date(signal_date, cfg)
        path.with_suffix(".superseded.json").write_text(json.dumps(old, indent=2), encoding="utf-8")
    new_entry["supersedes"] = signal_date
    write_journal(new_entry, cfg, allow_overwrite=True)
    return new_entry
