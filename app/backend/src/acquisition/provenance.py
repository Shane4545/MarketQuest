"""Provenance helpers for OpenBB acquisition runs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """Return UTC timestamp as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """Return sha256 for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON payload with deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)

