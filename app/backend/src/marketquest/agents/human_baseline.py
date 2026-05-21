"""Human baseline — holds SPY or last recorded human pick."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso
from marketquest.paths import portfolios_dir


def run_human_baseline(
    repo: Path,
    *,
    symbols: list[str],
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    sym = "SPY"
    path = portfolios_dir(repo) / "default.json"
    if path.is_file():
        pf = json.loads(path.read_text(encoding="utf-8"))
        positions = pf.get("positions") or []
        if positions:
            sym = str(positions[0].get("symbol", sym)).upper()
    elif symbols:
        sym = symbols[0].upper()

    return make_pick(
        symbol=sym,
        agent_id="human_baseline",
        as_of=as_of,
        score=0.0,
        predicted_bias="neutral",
        headline=f"Human baseline tracks portfolio or SPY: {sym}",
        bullets=["Educational comparator for human players", "Not optimized — reflects your book"],
        features={"baseline": "human"},
        data_mode="live",
    )
