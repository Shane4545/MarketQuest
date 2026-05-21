"""Persist and merge entity graph updates from events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.entity_graph.models import Relationship
from marketquest.entity_graph.ticker_mapper import load_entity_seed
from marketquest.paths import data_root


class GraphStore:
    def __init__(self, repo: Path):
        self.repo = repo
        self.path = data_root(repo) / "entity_graph.json"

    def load(self) -> dict[str, Any]:
        if self.path.is_file():
            return json.loads(self.path.read_text(encoding="utf-8"))
        seed = load_entity_seed(self.repo)
        return {
            "people": seed.get("people", []),
            "organizations": seed.get("organizations", []),
            "themes": seed.get("themes", []),
            "relationships": seed.get("relationships", []),
            "recent_chains": [],
        }

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def merge_from_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge event entity links into graph; return update records for snapshot."""
        graph = self.load()
        updates: list[dict[str, Any]] = []

        for ev in events:
            entities = ev.get("entities") or []
            tickers = ev.get("candidate_tickers") or []
            if not entities:
                continue
            chain = {
                "event_id": ev.get("event_id"),
                "title": ev.get("title", "")[:120],
                "entities": entities,
                "candidate_tickers": tickers,
                "event_type": ev.get("event_type"),
            }
            graph.setdefault("recent_chains", [])
            graph["recent_chains"].insert(0, chain)
            updates.append(chain)

            for ent in entities:
                for sym in tickers:
                    rel = Relationship(source=ent, target=sym, rel_type="event_link").to_dict()
                    if rel not in graph.get("relationships", []):
                        graph.setdefault("relationships", []).append(rel)

        graph["recent_chains"] = graph.get("recent_chains", [])[:50]
        self.save(graph)
        return updates[:20]

    def export_for_api(self) -> dict[str, Any]:
        graph = self.load()
        return {
            "people": graph.get("people", []),
            "organizations": graph.get("organizations", []),
            "themes": graph.get("themes", []),
            "relationships": graph.get("relationships", [])[:100],
            "recent_chains": graph.get("recent_chains", [])[:20],
        }
