"""Cross-asset module tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.api import get_cross_asset, get_currencies, get_dashboard, get_regime  # noqa: E402
from marketquest.cross_asset.correlation_engine import compute_correlations  # noqa: E402
from marketquest.cross_asset.cross_asset_features import enrich_snapshot_cross_asset  # noqa: E402
from marketquest.cross_asset.currency_watchlist import major_pairs  # noqa: E402
from marketquest.cross_asset.divergence_detector import detect_divergences  # noqa: E402
from marketquest.cross_asset.regime_detector import detect_regime  # noqa: E402
from marketquest.data_sources.fred_provider import DEFAULT_SERIES  # noqa: E402
from marketquest.reality_engine.snapshot import load_offline_training_snapshot  # noqa: E402


def test_currency_watchlist_has_seven_major_pairs():
    pairs = major_pairs(ROOT)
    assert len(pairs) >= 7


def test_fred_includes_oil_and_usdcad():
    ids = {s[0] for s in DEFAULT_SERIES}
    assert "DCOILWTICO" in ids
    assert "DEXCAUS" in ids
    assert "DGS10" in ids


def test_training_snapshot_has_cross_asset():
    snap = load_offline_training_snapshot(ROOT)
    assert snap is not None
    cross = snap.get("cross_asset", {})
    assert "forex" in cross
    assert "oil" in cross
    assert len(cross.get("forex") or []) >= 7


def test_enrich_snapshot_cross_asset_training():
    snap = load_offline_training_snapshot(ROOT)
    assert snap is not None
    cross = enrich_snapshot_cross_asset(ROOT, snap)
    assert cross.get("regime")
    assert "correlations" in cross
    assert "matrix" in cross


def test_regime_detector_returns_schema():
    snap = load_offline_training_snapshot(ROOT) or {}
    regime = detect_regime(snap)
    assert "regime" in regime
    assert "confidence" in regime
    assert "evidence" in regime


def test_correlation_engine_runs():
    snap = load_offline_training_snapshot(ROOT) or {}
    corrs = compute_correlations(snap)
    assert isinstance(corrs, list)


def test_divergence_detector_runs():
    snap = load_offline_training_snapshot(ROOT) or {}
    divs = detect_divergences(snap)
    assert isinstance(divs, list)


def test_dashboard_includes_regime_training():
    dash = get_dashboard(ROOT, mock=True, refresh=True)
    assert "cross_asset" in dash
    assert dash.get("regime")
    assert len(dash.get("currencies") or []) >= 7
    assert dash.get("careers", {}).get("count") == 12


def test_api_currencies_training():
    cur = get_currencies(ROOT, mock=True, refresh=True)
    assert cur.get("count", 0) >= 7


def test_api_cross_asset_training():
    ca = get_cross_asset(ROOT, mock=True, refresh=True)
    assert "cross_asset" in ca
    assert "matrix" in ca


def test_api_regime_training():
    reg = get_regime(ROOT, mock=True, refresh=True)
    assert reg.get("regime")


def test_watchlist_json_files_exist():
    cur_path = ROOT / "app" / "data" / "marketquest" / "watchlists" / "currencies.json"
    proxy_path = ROOT / "app" / "data" / "marketquest" / "watchlists" / "cross_asset_proxies.json"
    assert cur_path.is_file()
    assert proxy_path.is_file()
    cur = json.loads(cur_path.read_text(encoding="utf-8"))
    assert len(cur.get("major_pairs") or []) >= 7
