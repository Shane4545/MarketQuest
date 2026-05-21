"""Map text mentions to candidate tickers via seed graph and watchlist."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from marketquest.paths import data_root


def _normalize_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def load_entity_seed(repo: Path) -> dict[str, Any]:
    path = data_root(repo) / "entity_seed.json"
    if not path.is_file():
        return {"people": [], "organizations": [], "themes": [], "relationships": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_watchlist_symbols(repo: Path) -> list[str]:
    wl_path = data_root(repo) / "watchlists" / "default.json"
    if wl_path.is_file():
        data = json.loads(wl_path.read_text(encoding="utf-8"))
        return [str(s).upper() for s in data.get("symbols", [])]
    return []


def build_ticker_map(repo: Path) -> dict[str, list[str]]:
    """theme/person/org name → tickers from seed relationships."""
    seed = load_entity_seed(repo)
    watchlist = set(load_watchlist_symbols(repo))
    mapping: dict[str, list[str]] = {}

    for rel in seed.get("relationships", []):
        src = str(rel.get("from", ""))
        tgt = rel.get("to")
        rel_type = rel.get("type", "")
        tickers: list[str] = []
        if rel_type in ("theme_tickers", "org_tickers") and isinstance(tgt, list):
            tickers = [t.upper() for t in tgt if t.upper() in watchlist or True]
        elif rel_type in ("theme_tickers", "org_tickers") and isinstance(tgt, str):
            if tgt.upper().isalpha() and len(tgt) <= 5:
                tickers = [tgt.upper()]
        if tickers and src:
            mapping.setdefault(_normalize_id(src), []).extend(tickers)

    # Direct symbol mentions in watchlist
    for sym in watchlist:
        mapping[_normalize_id(sym)] = [sym]

    return mapping


def extract_entities_from_text(text: str, repo: Path) -> list[str]:
    """Find people, orgs, themes mentioned in text."""
    seed = load_entity_seed(repo)
    found: list[str] = []
    lower = text.lower()
    for group in ("people", "organizations", "themes"):
        for name in seed.get(group, []):
            if name.lower() in lower:
                found.append(name)
    return found


def map_text_to_tickers(text: str, repo: Path, watchlist: list[str] | None = None) -> list[str]:
    """Return candidate tickers from entity/theme mentions and direct symbol hits."""
    symbols = watchlist or load_watchlist_symbols(repo)
    sym_set = {s.upper() for s in symbols}
    tickers: list[str] = []
    ticker_map = build_ticker_map(repo)

    for entity in extract_entities_from_text(text, repo):
        key = _normalize_id(entity)
        for t in ticker_map.get(key, []):
            if t not in tickers:
                tickers.append(t)

    for theme in load_entity_seed(repo).get("themes", []):
        if theme.lower() in text.lower():
            for t in ticker_map.get(_normalize_id(theme), []):
                if t not in tickers:
                    tickers.append(t)

    # Direct $TICKER or uppercase symbol in watchlist
    for sym in sym_set:
        if re.search(rf"\b{re.escape(sym)}\b", text.upper()):
            if sym not in tickers:
                tickers.append(sym)

    return [t for t in tickers if t in sym_set or True][:10]
