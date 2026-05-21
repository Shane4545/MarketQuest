"""HTTP-facing pencil test data loaders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aggressive.config import load_config
from pencil.journal import load_journal
from pencil.monthly_pnl import load_all_journals, load_ledger_summary, write_ledger_summary
from pencil.paths import journal_dir, universe_dir


def get_ledger(repo: Path | None = None) -> dict[str, Any]:
    cfg = load_config()
    return load_ledger_summary(cfg)


def get_journal(signal_date: str) -> dict[str, Any] | None:
    return load_journal(signal_date, load_config())


def list_journal_dates() -> list[str]:
    cfg = load_config()
    dates = []
    skip_names = {"ledger_summary.json", "backtest_report.json"}
    for p in sorted(journal_dir(cfg).glob("*.json")):
        if p.name in skip_names or p.name.endswith(".superseded.json"):
            continue
        stem = p.stem
        if len(stem) == 10 and stem[4] == "-" and stem[7] == "-":
            dates.append(stem)
    return dates


def get_latest_predictions_from_journal() -> dict[str, Any] | None:
    journals = load_all_journals(load_config())
    if not journals:
        return None
    latest = sorted(journals, key=lambda x: x.get("signal_date", ""))[-1]
    return latest


def get_universe_status(signal_date: str | None = None) -> dict[str, Any]:
    """Load cached universe snapshot for a date (default: latest file)."""
    cfg = load_config()
    udir = universe_dir(cfg)
    if signal_date:
        path = udir / f"{signal_date}.json"
        if not path.is_file():
            return {"error": f"no universe snapshot for {signal_date}", "signal_date": signal_date}
        snap = json.loads(path.read_text(encoding="utf-8"))
        snap["signal_date"] = signal_date
        return snap

    files = sorted(udir.glob("*.json"), key=lambda p: p.stem, reverse=True)
    if not files:
        return {"error": "no universe snapshots yet"}
    path = files[0]
    snap = json.loads(path.read_text(encoding="utf-8"))
    snap["signal_date"] = path.stem
    return snap
