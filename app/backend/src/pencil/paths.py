"""Pencil journal filesystem paths."""

from __future__ import annotations

from pathlib import Path

from aggressive.config import load_config, resolve_repo_path
from phase1.paths import repo_root


def journal_dir(cfg: dict | None = None) -> Path:
    c = cfg or load_config()
    rel = (c.get("paths") or {}).get("journal_dir", "app/data/pencil_journal")
    p = resolve_repo_path(str(rel))
    p.mkdir(parents=True, exist_ok=True)
    return p


def universe_dir(cfg: dict | None = None) -> Path:
    c = cfg or load_config()
    rel = (c.get("paths") or {}).get("universe_dir", "app/data/universe")
    p = resolve_repo_path(str(rel))
    p.mkdir(parents=True, exist_ok=True)
    return p


def ledger_path(cfg: dict | None = None) -> Path:
    c = cfg or load_config()
    rel = (c.get("paths") or {}).get("ledger_file", "app/data/pencil_journal/ledger_summary.json")
    p = resolve_repo_path(str(rel))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def journal_path_for_date(signal_date: str, cfg: dict | None = None) -> Path:
    return journal_dir(cfg) / f"{signal_date}.json"


def model_dir(cfg: dict | None = None) -> Path:
    c = cfg or load_config()
    rel = (c.get("model") or {}).get("artifact_dir", "app/data/models")
    p = resolve_repo_path(str(rel))
    p.mkdir(parents=True, exist_ok=True)
    return p
