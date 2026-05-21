"""Paper portfolio — JSON persistence, no broker."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.config import load_config, today_iso
from marketquest.data_sources.watchlist import load_watchlist
from marketquest.paths import fixtures_dir, portfolios_dir


def _default_portfolio(repo: Path, user_id: str) -> dict[str, Any]:
    fixture = fixtures_dir(repo) / "portfolio_default.json"
    if fixture.is_file():
        data = json.loads(fixture.read_text(encoding="utf-8"))
        data["user_id"] = user_id
        return data
    cfg = load_config(repo)
    return {
        "user_id": user_id,
        "cash_usd": cfg["starting_cash_usd"],
        "positions": [],
        "day_pnl_usd": 0.0,
        "total_value_usd": cfg["starting_cash_usd"],
        "as_of": today_iso(),
    }


def load_portfolio(repo: Path, user_id: str = "default", *, mock: bool | None = None) -> dict[str, Any]:
    path = portfolios_dir(repo) / f"{user_id}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    pf = _default_portfolio(repo, user_id)
    portfolios_dir(repo).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pf, indent=2), encoding="utf-8")
    return pf


def _mark_prices(repo: Path, positions: list[dict], mock: bool | None) -> dict[str, float]:
    wl = load_watchlist(repo, mock=mock)
    prices = {q["symbol"]: float(q.get("last") or 0) for q in wl.get("quotes", [])}
    return prices


def _revalue(portfolio: dict[str, Any], prices: dict[str, float]) -> dict[str, Any]:
    cash = float(portfolio.get("cash_usd") or 0)
    positions = list(portfolio.get("positions") or [])
    mv = 0.0
    cost = 0.0
    for pos in positions:
        sym = str(pos.get("symbol", "")).upper()
        qty = float(pos.get("qty") or 0)
        entry = float(pos.get("entry_price") or 0)
        last = prices.get(sym, entry)
        pos["last_price"] = last
        pos["market_value_usd"] = round(qty * last, 2)
        pos["unrealized_pnl_usd"] = round(qty * (last - entry), 2)
        mv += pos["market_value_usd"]
        cost += qty * entry
    total = cash + mv
    portfolio["total_value_usd"] = round(total, 2)
    portfolio["positions_market_value_usd"] = round(mv, 2)
    portfolio["day_pnl_usd"] = round(total - float(portfolio.get("starting_value_usd") or total), 2)
    if "starting_value_usd" not in portfolio:
        portfolio["starting_value_usd"] = total
    return portfolio


def load_portfolio_valued(
    repo: Path,
    user_id: str = "default",
    *,
    mock: bool | None = None,
) -> dict[str, Any]:
    pf = load_portfolio(repo, user_id, mock=mock)
    prices = _mark_prices(repo, pf.get("positions", []), mock)
    return _revalue(pf, prices)


def paper_trade(
    repo: Path,
    body: dict[str, Any],
    *,
    mock: bool | None = None,
) -> dict[str, Any]:
    user_id = str(body.get("player_id") or body.get("user_id") or "default")
    symbol = str(body.get("symbol", "")).upper()
    side = str(body.get("side", "buy")).lower().replace("paper_", "")
    notional = float(body.get("notional") or 0)
    qty = float(body.get("qty") or 0)
    if notional > 0 and qty <= 0:
        pass  # resolved by caller with price
    if not symbol:
        return {"error": "symbol required"}
    if qty <= 0 and notional <= 0:
        return {"error": "positive qty or notional required"}

    snap_stale_block = False
    try:
        from marketquest.reality_engine.snapshot import load_latest_snapshot

        snap = load_latest_snapshot(repo)
        if snap and not snap.get("scoring_data_eligible") and not mock:
            snap_stale_block = True
    except Exception:
        pass
    if snap_stale_block and side == "buy":
        return {"error": "data stale — paper order rejected during stale market data"}

    pf = load_portfolio_valued(repo, user_id, mock=mock)
    prices = _mark_prices(repo, pf.get("positions", []), mock)
    price = prices.get(symbol, 0.0)
    if price <= 0 and not mock:
        return {"error": f"no price for {symbol}"}
    if price <= 0:
        price = 100.0

    if notional > 0 and qty <= 0:
        qty = max(1, int(notional / price))

    if qty <= 0:
        return {"error": "positive qty required"}

    cash = float(pf.get("cash_usd") or 0)
    positions = {str(p["symbol"]).upper(): dict(p) for p in pf.get("positions", [])}

    cfg = load_config(repo)
    max_positions = 10
    max_concentration = 0.25

    if side == "sell" and cfg.get("long_only") and symbol not in positions:
        return {"error": "long-only: no position to sell"}

    if side == "buy":
        cost = qty * price
        if cost > cash:
            return {"error": "insufficient paper cash"}
        total_value = float(pf.get("total_value_usd") or cash)
        if symbol not in positions and len(positions) >= max_positions:
            return {"error": f"max {max_positions} positions allowed"}
        new_total = total_value
        pos_value = qty * price
        if new_total > 0 and pos_value / new_total > max_concentration + 0.01:
            return {"error": f"max {int(max_concentration * 100)}% concentration per position"}
        cash -= cost
        pos = positions.get(symbol, {"symbol": symbol, "qty": 0, "entry_price": price})
        old_qty = float(pos.get("qty") or 0)
        old_entry = float(pos.get("entry_price") or price)
        new_qty = old_qty + qty
        pos["entry_price"] = (old_entry * old_qty + price * qty) / new_qty if new_qty else price
        pos["qty"] = new_qty
        positions[symbol] = pos
    elif side == "sell":
        pos = positions.get(symbol)
        if not pos or float(pos.get("qty") or 0) < qty:
            return {"error": "insufficient shares"}
        cash += qty * price
        pos["qty"] = float(pos["qty"]) - qty
        if pos["qty"] <= 0:
            del positions[symbol]
        else:
            positions[symbol] = pos
    else:
        return {"error": "side must be buy or sell"}

    pf["cash_usd"] = round(cash, 2)
    pf["positions"] = list(positions.values())
    pf["as_of"] = today_iso()
    path = portfolios_dir(repo) / f"{user_id}.json"
    portfolios_dir(repo).mkdir(parents=True, exist_ok=True)
    priced = _revalue(pf, prices)
    path.write_text(json.dumps(priced, indent=2), encoding="utf-8")
    return {"ok": True, "portfolio": priced}
