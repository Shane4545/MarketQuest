"""Deduplicate events by normalized title within time window."""

from __future__ import annotations

import re
from typing import Any


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def dedupe_events(events: list[dict[str, Any]], *, max_keep: int = 100) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for ev in events:
        title = ev.get("title") or ev.get("headline") or ev.get("raw_title") or ""
        key = _normalize_title(str(title))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(ev)
        if len(out) >= max_keep:
            break
    return out
