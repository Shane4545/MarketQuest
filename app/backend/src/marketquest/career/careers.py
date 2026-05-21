"""Future Builder career cards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import career_data_dir
from phase1.paths import repo_root


def load_careers(repo: Path | None = None) -> list[dict[str, Any]]:
    root = repo or repo_root()
    path = career_data_dir(root) / "careers.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("careers", []))


def get_careers(repo: Path | None = None) -> dict[str, Any]:
    careers = load_careers(repo)
    return {
        "title": "Future Builder",
        "subtitle": "Careers this game teaches — no real money required.",
        "careers": careers,
        "count": len(careers),
        "footer_note": "You can learn valuable skills and build useful tools without trading real money.",
    }
