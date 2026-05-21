"""Random baseline agent — mandatory honesty benchmark."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_random_baseline(
    repo: Path,
    *,
    symbols: list[str],
    as_of: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    if not symbols:
        symbols = ["SPY"]
    rng = random.Random(seed or as_of)
    sym = rng.choice(symbols).upper()
    return make_pick(
        symbol=sym,
        agent_id="random_baseline",
        as_of=as_of,
        score=0.0,
        predicted_bias="neutral",
        headline=f"Random baseline pick: {sym}",
        bullets=[
            "Uniform random symbol from watchlist",
            "If AI cannot beat this over time, the UI must show that honestly",
        ],
        features={"random": True},
        data_mode="live",
    )
