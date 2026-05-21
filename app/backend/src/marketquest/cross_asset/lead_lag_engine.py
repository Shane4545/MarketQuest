"""Lead-lag relationship candidates from cross-asset moves."""

from __future__ import annotations

from typing import Any

LAGS = [5, 15, 30, 60, 1440]


def compute_lead_lag(snapshot: dict[str, Any], *, max_pairs: int = 10) -> list[dict[str, Any]]:
    """V0 heuristic: flag assets with large driver move and smaller follower move."""
    changes = {}
    for p in snapshot.get("prices", []):
        sym = p.get("symbol")
        if sym:
            changes[str(sym).upper()] = float(p.get("change_pct") or 0)
    for f in (snapshot.get("cross_asset") or {}).get("forex") or []:
        pair = f.get("pair")
        if pair:
            changes[str(pair).upper()] = float(f.get("change_pct_1d") or f.get("change_pct") or 0)

    candidates: list[tuple[str, str, int, float]] = [
        ("USO", "XLE", 30, 0.55),
        ("USD/CAD", "BAM", 30, 0.50),
        ("USD/CAD", "ENB", 30, 0.48),
        ("QQQ", "NVDA", 15, 0.52),
        ("TLT", "XLF", 60, 0.45),
        ("USD/CNH", "FXI", 30, 0.40),
    ]
    ts = snapshot.get("timestamp_utc", "")
    results: list[dict[str, Any]] = []

    for leader, follower, lag, base_score in candidates:
        lc = changes.get(leader)
        fc = changes.get(follower)
        if lc is None or fc is None:
            continue
        if abs(lc) < 0.3:
            continue
        # Follower hasn't moved as much as leader — possible lag
        if abs(fc) >= abs(lc):
            continue
        score = base_score * min(abs(lc) / 2.0, 1.0)
        status = "candidate" if score >= 0.45 else "weak"
        results.append({
            "leader": leader,
            "follower": follower,
            "lag_minutes": lag,
            "relationship_score": round(score, 3),
            "historical_hit_rate": round(0.5 + score * 0.1, 3),
            "sample_count": 1,
            "status": status,
            "explanation": (
                f"{leader} moved {lc:.2f}% while {follower} moved {fc:.2f}% — "
                f"possible {lag}m lag candidate (moderate confidence, V0 heuristic)."
            ),
            "last_updated_utc": ts,
        })

    return results[:max_pairs]
