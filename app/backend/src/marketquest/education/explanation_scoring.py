"""Score free-text player reasoning."""

from __future__ import annotations

import re
from typing import Any

UNCERTAINTY_PHRASES = [
    "might", "may", "could", "uncertain", "unclear", "risk", "if", "depends",
    "not sure", "possibly", "perhaps", "hard to tell",
]

SECTOR_KEYWORDS = {
    "tech": ["technology", "xlk", "software", "semiconductor", "nvda", "ai"],
    "energy": ["energy", "oil", "xle", "crude", "opec"],
    "financials": ["bank", "xlf", "rate", "fed", "yield"],
    "healthcare": ["health", "xlv", "fda", "biotech"],
    "consumer": ["retail", "consumer", "xlp", "xly"],
    "utilities": ["utility", "xlu", "power"],
    "real_estate": ["real estate", "reit", "housing", "mortgage"],
    "airlines": ["airline", "travel", "jet fuel"],
}


def score_explanation(text: str, *, expected_sectors: list[str] | None = None) -> dict[str, Any]:
    text_lower = text.lower().strip()
    if not text_lower:
        return {"score": 0, "uncertainty_bonus": False, "sectors_mentioned": []}

    uncertainty = any(p in text_lower for p in UNCERTAINTY_PHRASES)
    sectors_found: list[str] = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            sectors_found.append(sector)

    base = min(5.0, len(text_lower.split()) / 10)
    if uncertainty:
        base += 1.0
    if expected_sectors:
        overlap = set(sectors_found) & set(expected_sectors)
        base += len(overlap) * 1.5

    return {
        "score": round(min(10, base), 2),
        "uncertainty_bonus": uncertainty,
        "sectors_mentioned": sectors_found,
    }
