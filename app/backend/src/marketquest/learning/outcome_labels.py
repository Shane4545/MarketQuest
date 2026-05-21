"""Label prediction outcomes from snapshot price history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.freshness import age_minutes
from marketquest.paths import predictions_dir, snapshots_dir

HORIZONS_MINUTES = {
    "15m": 15,
    "1h": 60,
    "1d": 1440,
    "1w": 10080,
}


def label_outcome(
    *,
    symbol: str,
    price_at_prediction: float,
    price_after: float | None,
    spy_return: float = 0.0,
) -> dict[str, Any]:
    if price_after is None or price_at_prediction <= 0:
        return {"labeled": False, "reason": "insufficient price history"}
    ret = (price_after - price_at_prediction) / price_at_prediction
    adj = ret - spy_return
    direction_right = ret > 0
    return {
        "labeled": True,
        "return_pct": round(ret * 100, 4),
        "spy_adjusted_return_pct": round(adj * 100, 4),
        "direction_right": direction_right,
        "thesis_right": direction_right,
        "timing_right": abs(ret) > 0.001,
    }


def store_prediction(repo: Path, pick: dict[str, Any], snapshot_ts: str) -> None:
    predictions_dir(repo).mkdir(parents=True, exist_ok=True)
    day = snapshot_ts[:10]
    path = predictions_dir(repo) / f"{day}.jsonl"
    record = {
        "snapshot_ts": snapshot_ts,
        "agent_id": pick.get("agent_id"),
        "symbol": pick.get("symbol"),
        "horizon": pick.get("horizon", "1d"),
        "price_at_prediction": pick.get("features", {}).get("last"),
        "prediction_type": pick.get("prediction_type"),
        "confidence": pick.get("confidence"),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _load_snapshots_for_day(repo: Path, day: str) -> list[dict[str, Any]]:
    day_dir = snapshots_dir(repo) / day
    if not day_dir.is_dir():
        return []
    snaps = []
    for p in sorted(day_dir.glob("*.json")):
        try:
            snaps.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return snaps


def label_horizon_outcomes(repo: Path, current_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Label prior predictions against current prices when horizon elapsed."""
    ts = current_snapshot.get("timestamp_utc", "")
    if not ts:
        return []
    prices = {p["symbol"]: float(p.get("last") or 0) for p in current_snapshot.get("prices", [])}
    day = ts[:10]
    pred_path = predictions_dir(repo) / f"{day}.jsonl"
    if not pred_path.is_file():
        return []

    labeled: list[dict[str, Any]] = []
    for line in pred_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        pred_ts = rec.get("snapshot_ts", "")
        horizon = rec.get("horizon", "1d")
        mins_needed = HORIZONS_MINUTES.get(horizon, 1440)
        elapsed = age_minutes(pred_ts) if pred_ts else 99999
        if elapsed < mins_needed:
            continue
        sym = rec.get("symbol", "")
        price_now = prices.get(sym)
        price_then = rec.get("price_at_prediction")
        if price_then is None:
            for snap in _load_snapshots_for_day(repo, day):
                if snap.get("timestamp_utc", "").startswith(pred_ts[:16]):
                    for p in snap.get("prices", []):
                        if p.get("symbol") == sym:
                            price_then = float(p.get("last") or 0)
                            break
        if price_then is None or price_now is None:
            continue
        outcome = label_outcome(
            symbol=sym,
            price_at_prediction=float(price_then),
            price_after=price_now,
        )
        labeled.append({**rec, "outcome": outcome, "horizon": horizon})
    return labeled
