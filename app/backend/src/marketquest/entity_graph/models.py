"""Entity graph data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENTITY_TYPES = ("person", "organization", "ticker", "sector", "theme", "policy", "event", "country")


@dataclass
class Entity:
    id: str
    name: str
    entity_type: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "entity_type": self.entity_type, **self.metadata}


@dataclass
class Relationship:
    source: str
    target: str
    rel_type: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {"from": self.source, "to": self.target, "type": self.rel_type}
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class ImpactHypothesis:
    description: str
    candidate_tickers: list[str] = field(default_factory=list)
    possible_positive: list[str] = field(default_factory=list)
    possible_negative: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "candidate_tickers": self.candidate_tickers,
            "possible_positive_impacts": self.possible_positive,
            "possible_negative_impacts": self.possible_negative,
            "uncertainties": self.uncertainties,
        }
