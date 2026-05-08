"""Add `app/backend/src` to sys.path for Phase 1 CLI scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_phase1_path() -> Path:
    """Return repository root path."""
    here = Path(__file__).resolve()
    # app/scripts/<caller>.py -> parents[2] == repo root
    repo = here.parents[2]
    src = repo / "app" / "backend" / "src"
    if src.is_dir():
        p = str(src.resolve())
        if p not in sys.path:
            sys.path.insert(0, p)
    return repo
