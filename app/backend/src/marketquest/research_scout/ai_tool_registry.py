"""Load and query research registries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import research_data_dir
from phase1.paths import repo_root


def _load_json(repo: Path, filename: str) -> list[dict[str, Any]]:
    path = research_data_dir(repo) / filename
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    key = filename.replace(".json", "")
    if key == "ai_tools":
        return list(data.get("tools", []))
    if key == "open_source_projects":
        return list(data.get("projects", []))
    if key == "models":
        return list(data.get("models", []))
    if key == "data_sources":
        return list(data.get("sources", []))
    return list(data.values()) if isinstance(data, dict) else []


def load_ai_tools(repo: Path | None = None) -> list[dict[str, Any]]:
    return _load_json(repo or repo_root(), "ai_tools.json")


def query_registry(
    repo: Path | None = None,
    *,
    category: str | None = None,
    registry: str | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    all_entries: list[dict[str, Any]] = []
    sources = {
        "ai_tools": load_ai_tools(root),
        "open_source_projects": _load_json(root, "open_source_projects.json"),
        "models": _load_json(root, "models.json"),
        "data_sources": _load_json(root, "data_sources.json"),
    }
    if registry and registry in sources:
        all_entries = sources[registry]
    else:
        for items in sources.values():
            all_entries.extend(items)
    if category:
        all_entries = [e for e in all_entries if e.get("category") == category]
    return {"entries": all_entries, "count": len(all_entries), "category": category}
