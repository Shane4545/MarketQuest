"""Concentrated allocation for aggressive pencil picks."""

from __future__ import annotations

from typing import Any


def allocate_top1(balance_usd: float, pick: dict[str, Any]) -> dict[str, Any]:
    """Assign 100% notional to a single pick."""
    out = dict(pick)
    out["notional_usd"] = round(float(balance_usd), 2)
    out["allocation_mode"] = "concentrated_top1"
    return out


def allocate_picks(
    balance_usd: float,
    ranked: list[dict[str, Any]],
    mode: str = "concentrated_top1",
) -> list[dict[str, Any]]:
    if not ranked:
        return []
    if mode == "concentrated_top1":
        return [allocate_top1(balance_usd, ranked[0])]
    # equal split top-N fallback
    n = len(ranked)
    share = round(float(balance_usd) / n, 2)
    out = []
    for i, p in enumerate(ranked):
        row = dict(p)
        row["notional_usd"] = share
        row["allocation_mode"] = mode
        row["rank"] = i + 1
        out.append(row)
    return out
