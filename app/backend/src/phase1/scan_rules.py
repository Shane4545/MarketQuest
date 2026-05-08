"""Apply configurable scanning rules to feature rows."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def apply_momentum_volume_pressure(
    feat_row: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[str, str]:
    """
    Returns (status, reason) where status is 'selected' or 'rejected'.
    """
    sym = feat_row.get("symbol", "?")

    if feat_row.get("missing_required_ohlcv"):
        return "rejected", "missing required OHLCV fields"

    if feat_row.get("insufficient_evidence"):
        return "rejected", "insufficient evidence (history or data)"

    if feat_row.get("blowoff_flag"):
        return "rejected", "blowoff_flag true"

    if feat_row.get("close_weak_flag"):
        return "rejected", "close_weak_flag true"

    require_mc = bool(cfg.get("require_market_cap", True))
    if require_mc and feat_row.get("market_cap_missing_flag"):
        return "rejected", "market_cap_missing_flag true and market cap required"

    min_ret = float(cfg["min_prior_5d_return_pct"])
    min_vs = float(cfg["min_volume_surge"])
    min_clv = float(cfg["min_close_location_value"])

    pr = feat_row.get("prior_5d_return_pct")
    vs = feat_row.get("volume_surge")
    clv = feat_row.get("close_location_value")

    if pr is None or (isinstance(pr, float) and np.isnan(pr)):
        return "rejected", "insufficient evidence for prior_5d_return_pct"
    if vs is None or (isinstance(vs, float) and np.isnan(vs)):
        return "rejected", "insufficient evidence for volume_surge"
    if clv is None or (isinstance(clv, float) and np.isnan(clv)):
        return "rejected", "insufficient evidence for close_location_value"

    if float(pr) < min_ret:
        return "rejected", f"prior_5d_return_pct {float(pr):.4f} below threshold {min_ret}"

    if float(vs) < min_vs:
        return "rejected", f"volume_surge {float(vs):.4f} below threshold {min_vs}"

    if float(clv) < min_clv:
        return "rejected", f"close_location_value {float(clv):.4f} below threshold {min_clv}"

    return "selected", "passed momentum_volume_pressure thresholds"


def scan_frame(
    features: pd.DataFrame,
    rule_name: str,
    rules_yaml: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if rule_name not in rules_yaml:
        raise KeyError(f"Rule {rule_name!r} not defined in pattern_rules.yaml")

    cfg = dict(rules_yaml[rule_name])
    max_c = int(cfg.get("max_candidates", 10))

    passed: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    work = features.copy()
    if not work.empty:
        work["_score"] = work.apply(_score_key, axis=1)
        work = work.sort_values(["_score", "symbol"], ascending=[False, True])

    for _, row in work.iterrows():
        d = row.to_dict()
        status, reason = apply_momentum_volume_pressure(d, cfg)
        d["rule"] = rule_name
        d["scan_reason"] = reason
        if status == "selected":
            passed.append(d)
        else:
            d["status"] = "rejected"
            rejected_rows.append(d)

    # Rank passes and enforce max_candidates
    passed_sorted = sorted(passed, key=lambda x: (-_score_key(pd.Series(x)), x.get("symbol", "")))
    selected_rows: list[dict[str, Any]] = []
    for i, d in enumerate(passed_sorted):
        if i < max_c:
            d["status"] = "selected"
            selected_rows.append(d)
        else:
            d["status"] = "rejected"
            d["scan_reason"] = (
                f"passed rule but exceeded max_candidates ({max_c}); ranked below cutoff"
            )
            rejected_rows.append(d)

    sel = pd.DataFrame(selected_rows)
    rej = pd.DataFrame(rejected_rows)
    return sel, rej


def _score_key(row: pd.Series) -> float:
    """Higher is better for ranking prior to max_candidates trim."""
    try:
        pr = float(row.get("prior_5d_return_pct", np.nan))
        vs = float(row.get("volume_surge", np.nan))
        clv = float(row.get("close_location_value", np.nan))
        if np.isnan(pr):
            pr = 0.0
        if np.isnan(vs):
            vs = 0.0
        if np.isnan(clv):
            clv = 0.0
        return pr * 1.0 + vs * 10.0 + clv * 100.0
    except (TypeError, ValueError):
        return 0.0
