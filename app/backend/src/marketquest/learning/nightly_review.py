"""Generate nightly learning reports from snapshots and agent picks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.config import today_iso
from marketquest.data_sources.base import utc_now_iso
from marketquest.learning.performance_tracker import load_scores, save_scores
from marketquest.paths import agent_picks_dir, reports_dir, snapshots_dir


def run_nightly_review(repo: Path) -> Path:
    reports_dir(repo).mkdir(parents=True, exist_ok=True)
    day = today_iso()
    report_path = reports_dir(repo) / f"{day}_nightly_review.md"

    scores = load_scores(repo)
    picks_files = sorted(agent_picks_dir(repo).glob("*.json"), reverse=True)[:3]
    snap_count = sum(1 for _ in snapshots_dir(repo).rglob("*.json")) if snapshots_dir(repo).is_dir() else 0

    agents = scores.get("agents") or {}
    lines = [
        f"# MarketQuest Nightly Review — {day}",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "## Summary",
        "",
        f"- Snapshots on disk: {snap_count}",
        f"- Recent pick files: {len(picks_files)}",
        "",
        "## Agent reliability (rolling)",
        "",
    ]
    if agents:
        for aid, rec in sorted(agents.items()):
            lines.append(f"- **{aid}**: hit rate {rec.get('hit_rate', 0):.1%} ({rec.get('wins', 0)}/{rec.get('total', 0)})")
    else:
        lines.append("_Insufficient history — scores populate as outcomes are labeled._")

    lines.extend(["", "## Event types", ""])
    et = scores.get("event_types") or {}
    if et:
        for name, rec in et.items():
            hr = rec.get("wins", 0) / max(rec.get("total", 1), 1)
            lines.append(f"- {name}: {hr:.1%} useful signal rate")
    else:
        lines.append("_No event-type outcomes yet._")

    lines.extend(
        [
            "",
            "## What worked / failed today",
            "",
            "_V0 uses snapshot-diff labeling when history exists. Run again after multiple trading days._",
            "",
            "## False positives",
            "",
            "- Skeptic agent flags stale data and weak ticker links — review skeptic picks in UI.",
            "",
            "## Beginner explanation",
            "",
            "MarketQuest scores **paper predictions** against what actually happened. "
            "Agents that beat the random baseline over time get higher ensemble weight. "
            "This is educational — not investment advice.",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Bootstrap scores if empty
    if not scores.get("agents"):
        scores["agents"] = {
            "random_baseline": {"wins": 0, "total": 0, "hit_rate": 0.0},
            "ensemble": {"wins": 0, "total": 0, "hit_rate": 0.0},
        }
        scores["updated_at"] = utc_now_iso()
        save_scores(repo, scores)

    return report_path


def load_latest_report(repo: Path) -> dict[str, Any]:
    root = reports_dir(repo)
    if not root.is_dir():
        return {"markdown": "", "summary": "No nightly report yet. Run marketquest_nightly_review.py"}
    files = sorted(root.glob("*_nightly_review.md"), reverse=True)
    if not files:
        return {"markdown": "", "summary": "No nightly report yet. Run marketquest_nightly_review.py"}
    text = files[0].read_text(encoding="utf-8")
    scores = load_scores(repo)
    return {
        "report_date": files[0].stem.replace("_nightly_review", ""),
        "markdown": text,
        "agent_scores": scores.get("agents", {}),
        "event_types": scores.get("event_types", {}),
        "summary": "Latest learning report loaded",
    }
