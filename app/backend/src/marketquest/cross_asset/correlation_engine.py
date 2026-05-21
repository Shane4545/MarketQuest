"""Rolling correlation estimates from snapshot price moves."""

from __future__ import annotations

from typing import Any

WINDOWS = ["15m", "30m", "1h", "4h", "1d", "5d", "20d"]


def _change_map(snapshot: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in snapshot.get("prices", []):
        sym = p.get("symbol")
        if sym:
            out[str(sym).upper()] = float(p.get("change_pct") or 0)
    for f in (snapshot.get("cross_asset") or {}).get("forex") or snapshot.get("currencies") or []:
        pair = f.get("pair")
        if pair:
            out[str(pair).upper()] = float(f.get("change_pct_1d") or f.get("change_pct") or 0)
    return out


def _strength(corr: float, n: int) -> tuple[str, str]:
    if n < 5:
        return "weak", "unstable"
    ac = abs(corr)
    strength = "strong" if ac >= 0.6 else ("moderate" if ac >= 0.35 else "weak")
    direction = "positive" if corr >= 0.15 else ("negative" if corr <= -0.15 else "unstable")
    return strength, direction


def compute_correlations(snapshot: dict[str, Any], *, max_pairs: int = 20) -> list[dict[str, Any]]:
    """Estimate same-day directional alignment (V0 proxy when intraday history unavailable)."""
    changes = _change_map(snapshot)
    if len(changes) < 2:
        return []

    fx_pairs = [k for k in changes if "/" in k]
    stocks = [k for k in changes if "/" not in k and k not in ("SPY", "QQQ", "IWM", "DIA")]
    indexes = [k for k in ("SPY", "QQQ", "IWM", "DIA") if k in changes]
    sectors = [k for k in changes if k.startswith("XL")]

    results: list[dict[str, Any]] = []
    ts = snapshot.get("timestamp_utc", "")

    def add(symbol: str, related: str, window: str = "1d") -> None:
        if symbol not in changes or related not in changes:
            return
        a, b = changes[symbol], changes[related]
        # Directional alignment proxy: product sign with magnitude weight
        if a == 0 or b == 0:
            corr = 0.0
        else:
            corr = (1.0 if (a * b) > 0 else -1.0) * min(abs(a), abs(b)) / max(abs(a), abs(b), 0.01)
            corr = max(-1.0, min(1.0, corr))
        n = 1  # single snapshot sample in V0
        strength, direction = _strength(corr, n)
        results.append({
            "symbol": symbol,
            "related_asset": related,
            "window": window,
            "correlation": round(corr, 3),
            "sample_count": n,
            "relationship_strength": strength,
            "direction": direction,
            "last_updated_utc": ts,
            "explanation": (
                f"{symbol} shows {strength} {direction} same-day alignment with {related} "
                f"in current snapshot (V0 proxy — not full rolling history)."
            ),
        })

    for fx in fx_pairs[:4]:
        for sym in stocks[:6]:
            add(sym, fx)
    for idx in indexes:
        for sym in stocks[:8]:
            add(sym, idx)
    for sec in sectors[:4]:
        for sym in stocks[:6]:
            add(sym, sec)

    usd_cad = changes.get("USD/CAD")
    if usd_cad is not None:
        for sym in ("BAM", "BN", "ENB", "XLE", "USO"):
            if sym in changes:
                add(sym, "USD/CAD")

    return results[:max_pairs]
