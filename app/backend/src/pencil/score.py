"""Score pencil picks against next-day closes."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from common.trading_calendar import close_on, nth_trading_day_after, trading_calendar_from_df
from pencil.journal import load_journal, write_journal


def outcome_from_return(return_pct: float, *, win_threshold: float = 0.0) -> str:
    if return_pct > win_threshold:
        return "win"
    if return_pct < win_threshold:
        return "loss"
    return "flat"


def score_journal_day(
    signal_date: str,
    prices_df: pd.DataFrame,
    *,
    cfg: dict | None = None,
) -> dict[str, Any] | None:
    entry = load_journal(signal_date, cfg)
    if entry is None:
        return None
    if entry.get("action") == "skip":
        entry["status"] = "scored"
        entry["scored_at"] = entry.get("scored_at")
        write_journal(entry, cfg, allow_overwrite=True)
        return entry

    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    cal = trading_calendar_from_df(df)
    as_of = date.fromisoformat(signal_date)
    exit_d = nth_trading_day_after(cal, as_of, 1)
    if exit_d is None:
        return entry

    balance = float(entry.get("balance_before_usd", 100))
    total_pnl = 0.0
    all_scored = True

    for pick in entry.get("picks", []):
        sym = str(pick["symbol"])
        entry_close = pick.get("entry_close")
        if entry_close is None:
            entry_close = close_on(df, sym, as_of)
            pick["entry_close"] = entry_close
        exit_close = close_on(df, sym, exit_d)
        pick["exit_date"] = str(exit_d)
        pick["exit_close"] = exit_close
        if entry_close is None or exit_close is None or entry_close == 0:
            pick["status"] = "unscorable"
            all_scored = False
            continue
        ret_pct = (exit_close / float(entry_close) - 1.0) * 100.0
        notional = float(pick.get("notional_usd", balance))
        pnl = notional * (ret_pct / 100.0)
        pick["actual_return_1d_pct"] = round(ret_pct, 4)
        pick["pnl_usd"] = round(pnl, 2)
        pick["outcome"] = outcome_from_return(ret_pct)
        pick["status"] = "scored"
        total_pnl += pnl

    if all_scored and entry.get("picks"):
        entry["status"] = "scored"
        entry["total_pnl_usd"] = round(total_pnl, 2)
        entry["balance_after_usd"] = round(balance + total_pnl, 2)
        from datetime import datetime, timezone

        entry["scored_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    write_journal(entry, cfg, allow_overwrite=True)
    return entry


def current_balance_from_journals(
    journals: list[dict[str, Any]],
    starting_balance: float,
) -> float:
    balance = float(starting_balance)
    for j in sorted(journals, key=lambda x: x.get("signal_date", "")):
        if j.get("status") == "scored" and "balance_after_usd" in j:
            balance = float(j["balance_after_usd"])
        elif j.get("action") == "skip":
            balance = float(j.get("balance_after_usd", balance))
    return balance
