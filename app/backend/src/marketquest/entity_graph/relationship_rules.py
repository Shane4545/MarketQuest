"""Explainable entity → theme → ticker relationship rules."""

from __future__ import annotations

from typing import Any

# Event type + entity keyword → impact hypotheses (educational only)
IMPACT_RULES: dict[str, dict[str, Any]] = {
    "tariff_trade": {
        "entities": ["China", "tariffs", "Donald Trump"],
        "possible_positive": ["domestic producers", "steel/aluminum", "domestic manufacturing"],
        "possible_negative": ["import-heavy retailers", "tech hardware importers", "auto supply chain"],
        "uncertainties": ["inflation risk", "retaliatory tariffs", "supply chain disruption"],
        "sectors": ["industrials", "materials", "consumer discretionary", "tech hardware"],
        "tickers": ["XLI", "XLB", "XLY", "XLE"],
    },
    "government_policy": {
        "entities": ["Canada", "Mark Carney", "Bank of Canada"],
        "possible_positive": ["infrastructure operators", "engineering firms", "materials", "rail", "ports"],
        "possible_negative": ["debt-sensitive firms if rates rise"],
        "uncertainties": ["fiscal deficit", "rate environment", "PPP financing terms"],
        "sectors": ["infrastructure", "utilities", "materials", "real estate"],
        "tickers": ["BAM", "BN", "ENB", "TRP", "XLI"],
    },
    "infrastructure_project": {
        "entities": ["Canada", "Brookfield", "infrastructure"],
        "possible_positive": ["infrastructure operators", "construction", "materials", "energy transition"],
        "possible_negative": ["rate-sensitive growth if funding costs rise"],
        "uncertainties": ["project approval timeline", "government co-financing"],
        "sectors": ["industrials", "utilities", "real estate"],
        "tickers": ["BAM", "BN", "ENB", "TRP", "XLI"],
    },
    "energy_oil_shock": {
        "entities": ["OPEC", "oil", "crude"],
        "possible_positive": ["energy producers", "oil services"],
        "possible_negative": ["airlines", "transportation", "consumer discretionary"],
        "uncertainties": ["demand destruction", "strategic reserve release"],
        "sectors": ["energy", "airlines", "transportation"],
        "tickers": ["XLE", "XOM", "CVX", "COP"],
    },
    "macro_rates": {
        "entities": ["Federal Reserve", "Jerome Powell", "interest rates"],
        "possible_positive": ["banks if steepening curve"],
        "possible_negative": ["long-duration tech", "homebuilders", "utilities"],
        "uncertainties": ["inflation path", "labor market strength"],
        "sectors": ["financials", "technology", "utilities", "real estate"],
        "tickers": ["XLF", "XLK", "XLU", "SPY"],
    },
    "macro_inflation": {
        "entities": ["CPI", "inflation", "Federal Reserve"],
        "possible_positive": ["commodities", "TIPS proxies"],
        "possible_negative": ["consumer staples margin pressure", "rate-sensitive growth"],
        "uncertainties": ["Fed reaction function", "wage-price spiral"],
        "sectors": ["materials", "consumer staples", "financials"],
        "tickers": ["XLB", "XLP", "XLF", "SPY"],
    },
    "public_figure_statement": {
        "entities": ["Donald Trump", "Mark Carney", "Elon Musk"],
        "possible_positive": ["mentioned sectors/companies (hypothesis only)"],
        "possible_negative": ["sectors targeted by policy rhetoric"],
        "uncertainties": ["statement vs official policy", "market may have priced in"],
        "sectors": ["varies by statement"],
        "tickers": [],
    },
    "brookfield_related": {
        "entities": ["Brookfield", "Mark Carney"],
        "possible_positive": ["infrastructure/renewables exposure (hypothesis)"],
        "possible_negative": ["rate sensitivity on leveraged assets"],
        "uncertainties": ["no direct causal link from person to ticker", "check filings and volume"],
        "sectors": ["infrastructure", "renewables", "real estate", "private equity"],
        "tickers": ["BAM", "BN"],
    },
}


def get_impact_for_event(event_type: str, entities: list[str]) -> dict[str, Any]:
    """Return explainable impact hypotheses for event type and matched entities."""
    rule = IMPACT_RULES.get(event_type, {})
    if not rule:
        return {
            "possible_positive_impacts": [],
            "possible_negative_impacts": [],
            "uncertainties": ["Event type not in rule table — treat as low-confidence hypothesis"],
            "affected_sectors": [],
            "candidate_tickers": [],
        }

    entity_text = " ".join(entities).lower()
    matched = any(e.lower() in entity_text for e in rule.get("entities", []))
    if not matched and event_type not in ("tariff_trade", "macro_rates", "macro_inflation"):
        return {
            "possible_positive_impacts": rule.get("possible_positive", []),
            "possible_negative_impacts": rule.get("possible_negative", []),
            "uncertainties": rule.get("uncertainties", []) + ["Entity match weak"],
            "affected_sectors": rule.get("sectors", []),
            "candidate_tickers": rule.get("tickers", []),
        }

    return {
        "possible_positive_impacts": rule.get("possible_positive", []),
        "possible_negative_impacts": rule.get("possible_negative", []),
        "uncertainties": rule.get("uncertainties", []),
        "affected_sectors": rule.get("sectors", []),
        "candidate_tickers": rule.get("tickers", []),
    }
