"""Filesystem paths for MarketQuest data (isolated from pencil/acquisition)."""

from __future__ import annotations

from pathlib import Path

from phase1.paths import repo_root


def data_root(repo: Path | None = None) -> Path:
    root = repo or repo_root()
    return root / "app" / "data" / "marketquest"


def snapshots_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "snapshots"


def snapshot_path_for(repo: Path, timestamp_utc: str) -> Path:
    """Path: snapshots/YYYY-MM-DD/HHMM.json from ISO timestamp."""
    from datetime import datetime

    ts = timestamp_utc.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        dt = datetime.utcnow()
    day = dt.strftime("%Y-%m-%d")
    hhmm = dt.strftime("%H%M")
    return snapshots_dir(repo) / day / f"{hhmm}.json"


def agent_picks_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "agent_picks"


def portfolios_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "portfolios"


def leaderboards_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "leaderboards"


def competitions_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "competitions"


def fixtures_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "fixtures"


def learning_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "learning"


def reports_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "reports"


def watchlists_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "watchlists"


def predictions_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "predictions"


def education_data_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "education"


def career_data_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "career"


def research_data_dir(repo: Path | None = None) -> Path:
    return data_root(repo) / "research"


def ensure_dirs(repo: Path | None = None) -> None:
    for d in (
        snapshots_dir,
        agent_picks_dir,
        portfolios_dir,
        leaderboards_dir,
        competitions_dir,
        fixtures_dir,
        learning_dir,
        reports_dir,
        watchlists_dir,
        predictions_dir,
        education_data_dir,
        career_data_dir,
        research_data_dir,
    ):
        d(repo).mkdir(parents=True, exist_ok=True)
