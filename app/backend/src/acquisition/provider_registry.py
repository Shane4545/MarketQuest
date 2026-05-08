"""Provider selection registry for acquisition skill agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderSelection:
    """Provider selection decision."""

    provider_used: str
    fallback_used: bool
    fallback_candidates: list[str]


SUPPORTED_PROVIDERS = {"fixture", "yfinance", "tmx"}


def choose_provider(preferred_provider: str, fallback_providers: list[str]) -> ProviderSelection:
    """Choose provider from preferred + fallback list."""
    candidates = [preferred_provider] + [p for p in fallback_providers if p != preferred_provider]
    for idx, provider in enumerate(candidates):
        if provider in SUPPORTED_PROVIDERS:
            return ProviderSelection(
                provider_used=provider,
                fallback_used=(idx > 0),
                fallback_candidates=fallback_providers,
            )
    raise ValueError(
        f"No supported provider found in preferred/fallback list: {candidates}. Supported: {sorted(SUPPORTED_PROVIDERS)}"
    )

