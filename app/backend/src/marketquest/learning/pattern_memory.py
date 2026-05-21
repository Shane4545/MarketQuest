"""Pattern memory stub — versioned JSON only, no code self-modification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import learning_dir


def memory_path(repo: Path) -> Path:
    return learning_dir(repo) / "pattern_memory.json"


def load_memory(repo: Path) -> dict[str, Any]:
    path = memory_path(repo)
    if not path.is_file():
        return {"patterns": [], "version": 1}
    return json.loads(path.read_text(encoding="utf-8"))
