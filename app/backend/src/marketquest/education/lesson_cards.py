"""Contextual lesson cards tied to events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import education_data_dir
from phase1.paths import repo_root


def load_lesson_cards(repo: Path | None = None) -> list[dict[str, Any]]:
    root = repo or repo_root()
    path = education_data_dir(root) / "lesson_cards.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("cards", []))


def get_lessons(*, context: str | None = None, repo: Path | None = None) -> dict[str, Any]:
    cards = load_lesson_cards(repo)
    if context:
        cards = [c for c in cards if c.get("context") == context]
    return {"cards": cards, "count": len(cards)}


def lesson_for_event(event: dict[str, Any], repo: Path | None = None) -> dict[str, Any] | None:
    etype = event.get("event_type") or event.get("category") or ""
    mapping = {
        "sec_filing": "filing",
        "filing": "filing",
        "macro": "macro",
        "energy_oil_shock": "energy",
        "currency": "currency",
        "headline": "news",
    }
    ctx = mapping.get(str(etype), "news")
    cards = load_lesson_cards(repo)
    return next((c for c in cards if c.get("context") == ctx), cards[0] if cards else None)
