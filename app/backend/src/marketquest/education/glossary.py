"""Education glossary — loads from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import education_data_dir
from phase1.paths import repo_root


def _load_glossary_json(repo: Path | None = None) -> list[dict[str, str]]:
    root = repo or repo_root()
    path = education_data_dir(root) / "glossary.json"
    if not path.is_file():
        return _FALLBACK_GLOSSARY
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("terms", data if isinstance(data, list) else []))


_FALLBACK_GLOSSARY = [
    {
        "term": "Paper P&L",
        "definition": "Simulated profit/loss using delayed quotes — no real orders.",
    },
]


def get_education(picks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    picks = picks or []
    glossary = _load_glossary_json()
    by_symbol: dict[str, dict] = {}
    for p in picks:
        sym = p.get("symbol")
        if not sym:
            continue
        by_symbol[sym] = {
            "symbol": sym,
            "agents": [p.get("agent_id")],
            "features_explained": [
                {"name": k, "value": v}
                for k, v in (p.get("features") or {}).items()
            ],
            "headline": (p.get("explanation") or {}).get("headline", ""),
        }
    for p in picks:
        sym = p.get("symbol")
        if sym in by_symbol and p.get("agent_id") not in by_symbol[sym]["agents"]:
            by_symbol[sym]["agents"].append(p.get("agent_id"))

    return {
        "glossary": glossary,
        "symbol_guides": list(by_symbol.values()),
        "models_overview": (
            "Ten benchmark players compete on the same watchlist: Random, SPY, QQQ, "
            "Equal-Weight, Momentum, News-Only, Macro, Filing, Entity Graph, and Ensemble. "
            "Humans paper-trade alongside them. Paper scoring only — not investment advice."
        ),
    }


def get_glossary(repo: Path | None = None) -> dict[str, Any]:
    return {"terms": _load_glossary_json(repo)}
