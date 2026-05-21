"""Track agent performance in JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import learning_dir


def scores_path(repo: Path) -> Path:
    return learning_dir(repo) / "agent_scores.json"


def load_scores(repo: Path) -> dict[str, Any]:
    path = scores_path(repo)
    if not path.is_file():
        return {"agents": {}, "event_types": {}, "updated_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_scores(repo: Path, data: dict[str, Any]) -> Path:
    learning_dir(repo).mkdir(parents=True, exist_ok=True)
    path = scores_path(repo)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def record_agent_result(
    repo: Path,
    agent_id: str,
    *,
    hit: bool,
    event_type: str = "unknown",
) -> dict[str, Any]:
    data = load_scores(repo)
    agents = data.setdefault("agents", {})
    rec = agents.setdefault(agent_id, {"wins": 0, "total": 0, "hit_rate": 0.0})
    rec["total"] = int(rec.get("total", 0)) + 1
    if hit:
        rec["wins"] = int(rec.get("wins", 0)) + 1
    rec["hit_rate"] = round(rec["wins"] / max(rec["total"], 1), 4)

    et = data.setdefault("event_types", {})
    er = et.setdefault(event_type, {"wins": 0, "total": 0})
    er["total"] += 1
    if hit:
        er["wins"] += 1

    from marketquest.data_sources.base import utc_now_iso

    data["updated_at"] = utc_now_iso()
    save_scores(repo, data)
    return data
