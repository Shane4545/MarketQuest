"""Monthly P&L rollups vs $90 target."""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime
from typing import Any

from pencil.journal import load_journal
from pencil.paths import journal_dir, ledger_path


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def daily_pace_for_month(
    cfg: dict,
    *,
    as_of: date,
    current_balance: float,
    month_start_balance: float,
) -> float:
    """Required daily % return to hit monthly profit target from month-start balance."""
    target_profit = float(cfg.get("monthly_profit_target_usd", 90))
    month_goal = month_start_balance + target_profit
    if current_balance <= 0:
        return float(cfg.get("daily_pace_pct", 3.23))
    days_in_month = monthrange(as_of.year, as_of.month)[1]
    # approximate trading days elapsed/remaining
    trading_days = int(cfg.get("trading_days_per_month", 20))
    day_of_month = as_of.day
    remaining = max(1, trading_days - min(day_of_month, trading_days) + 1)
    if current_balance >= month_goal:
        return 0.0
    # compound daily rate needed: (goal/current)^(1/remaining) - 1
    ratio = month_goal / current_balance
    daily = (ratio ** (1.0 / remaining) - 1.0) * 100.0
    return max(float(cfg.get("daily_pace_pct", 3.23)), round(daily, 4))


def load_all_journals(cfg: dict | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sorted(journal_dir(cfg).glob("*.json")):
        if p.name == "ledger_summary.json" or p.name.endswith(".superseded.json"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("signal_date"):
            out.append(data)
    return out


def build_monthly_rollup(cfg: dict, journals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    journals = journals if journals is not None else load_all_journals(cfg)
    starting = float(cfg.get("starting_balance_usd", 100))
    target_profit = float(cfg.get("monthly_profit_target_usd", 90))

    by_month: dict[str, dict[str, Any]] = {}
    running = starting

    for j in sorted(journals, key=lambda x: x.get("signal_date", "")):
        sd = j.get("signal_date", "")
        try:
            d = date.fromisoformat(sd)
        except ValueError:
            continue
        mk = _month_key(d)
        if mk not in by_month:
            by_month[mk] = {
                "month": mk,
                "starting_balance_usd": running,
                "ending_balance_usd": running,
                "net_profit_usd": 0.0,
                "monthly_profit_target_usd": target_profit,
                "target_met": False,
                "gap_to_target_usd": target_profit,
                "pick_days": 0,
                "skip_days": 0,
                "wins": 0,
                "losses": 0,
            }
        month = by_month[mk]
        if j.get("action") == "skip":
            month["skip_days"] += 1
        elif j.get("action") == "pick":
            month["pick_days"] += 1
        if j.get("status") == "scored":
            if "balance_after_usd" in j:
                running = float(j["balance_after_usd"])
            for p in j.get("picks", []):
                oc = p.get("outcome")
                if oc == "win":
                    month["wins"] += 1
                elif oc == "loss":
                    month["losses"] += 1
        month["ending_balance_usd"] = round(running, 2)
        month_start = float(month["starting_balance_usd"])
        month["net_profit_usd"] = round(running - month_start, 2)
        month["target_met"] = month["net_profit_usd"] >= target_profit
        month["gap_to_target_usd"] = round(max(0.0, target_profit - month["net_profit_usd"]), 2)

    today = date.today()
    current_mk = _month_key(today)
    current = by_month.get(current_mk)
    if current:
        current["daily_pace_pct_required"] = daily_pace_for_month(
            cfg,
            as_of=today,
            current_balance=float(current["ending_balance_usd"]),
            month_start_balance=float(current["starting_balance_usd"]),
        )

    return {
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "starting_balance_usd": starting,
        "monthly_profit_target_usd": target_profit,
        "current_balance_usd": round(running, 2),
        "months": list(by_month.values()),
        "strategy_state": _strategy_state(cfg, by_month),
    }


def _strategy_state(cfg: dict, by_month: dict[str, dict[str, Any]]) -> str:
    gate = cfg.get("backtest_gate") or {}
    min_profit = float(gate.get("min_profitable_month_profit_usd", 90))
    any_hit = any(m.get("net_profit_usd", 0) >= min_profit for m in by_month.values())
    today_mk = _month_key(date.today())
    cur = by_month.get(today_mk, {})
    if cur.get("target_met"):
        return "TARGET_MET"
    if any_hit:
        return "PENCIL_ACTIVE"
    return "RESEARCH"


def write_ledger_summary(cfg: dict) -> dict[str, Any]:
    summary = build_monthly_rollup(cfg)
    path = ledger_path(cfg)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def load_ledger_summary(cfg: dict | None = None) -> dict[str, Any]:
    from aggressive.config import load_config

    c = cfg or load_config()
    path = ledger_path(c)
    if not path.is_file():
        return write_ledger_summary(c)
    return json.loads(path.read_text(encoding="utf-8"))
