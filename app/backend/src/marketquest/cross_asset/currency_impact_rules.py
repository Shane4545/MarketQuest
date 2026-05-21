"""Currency impact hypotheses — two-sided, not buy signals."""

from __future__ import annotations

from typing import Any


def apply_currency_rules(pair: str, change_pct: float | None = None) -> dict[str, Any]:
    """Return educational hypotheses for a currency pair move."""
    chg = float(change_pct or 0)
    direction = "up" if chg > 0.05 else ("down" if chg < -0.05 else "flat")
    rules: dict[str, dict[str, Any]] = {
        "USD/CAD": {
            "positive_hypothesis": "CAD weakness may support USD-revenue Canadian exporters; oil linkage possible.",
            "negative_hypothesis": "CAD weakness may pressure Canadian domestic demand and importers.",
            "uncertainty": "Oil and Bank of Canada policy may override pure FX signal.",
            "confirmation_data": ["USO", "XLE", "BAM", "BN", "CAD-sensitive watchlist"],
            "sensitive_groups": ["Canadian infrastructure", "energy", "materials"],
        },
        "USD/JPY": {
            "positive_hypothesis": "Higher USD/JPY may signal risk-on carry or yield differential.",
            "negative_hypothesis": "Sudden JPY strength often signals risk-off flight.",
            "uncertainty": "Must check yields and global equity tone together.",
            "confirmation_data": ["TLT", "SPY", "QQQ", "GLD"],
            "sensitive_groups": ["global risk assets", "exporters", "carry trades"],
        },
        "USD/CNH": {
            "positive_hypothesis": "Weaker yuan may connect to China stress or tariff headlines.",
            "negative_hypothesis": "Yuan stability may reduce supply-chain volatility fears.",
            "uncertainty": "Official policy and trade headlines dominate.",
            "confirmation_data": ["FXI", "tariff-sensitive names", "industrials"],
            "sensitive_groups": ["China supply chain", "multinationals", "materials"],
        },
        "EUR/USD": {
            "positive_hypothesis": "Euro strength may reflect EU growth optimism.",
            "negative_hypothesis": "Euro weakness may help US multinationals' translated earnings.",
            "uncertainty": "ECB vs Fed rate path matters.",
            "confirmation_data": ["SPY", "XLF", "multinationals"],
            "sensitive_groups": ["multinationals", "luxury exporters"],
        },
    }
    base = rules.get(pair.upper(), {
        "positive_hypothesis": f"{pair} move may affect cross-border revenue and commodity pricing.",
        "negative_hypothesis": f"{pair} move may create offsetting sector effects.",
        "uncertainty": "Correlation is not causation — confirm with sector and macro context.",
        "confirmation_data": ["SPY", "sector ETFs"],
        "sensitive_groups": ["multinationals", "commodity producers"],
    })
    return {
        "pair": pair.upper(),
        "move_direction": direction,
        "change_pct_1d": chg,
        **base,
    }


def usd_strength_rules(usd_up: bool) -> dict[str, Any]:
    if usd_up:
        return {
            "regime_hint": "USD_strength",
            "positive_hypothesis": "May pressure commodities priced in USD; may help some importers.",
            "negative_hypothesis": "May hurt multinationals with foreign revenue translation.",
            "uncertainty": "Context depends on rates, growth, and risk appetite.",
            "confirmation_data": ["GLD", "USO", "QQQ", "XLE"],
        }
    return {
        "regime_hint": "USD_weakness",
        "positive_hypothesis": "May support commodities and EM-sensitive risk assets.",
        "negative_hypothesis": "May signal growth concerns if driven by rate-cut fear.",
        "uncertainty": "Check whether weakness is growth-positive or recession-fear.",
        "confirmation_data": ["GLD", "USO", "IWM", "HYG"],
    }
