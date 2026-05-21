"""Weekly research report markdown generator."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from marketquest.research_scout.ai_tool_registry import load_ai_tools, query_registry
from marketquest.paths import reports_dir
from phase1.paths import repo_root


def generate_report(repo: Path | None = None) -> dict[str, Any]:
    root = repo or repo_root()
    reg = query_registry(root)
    integrated = [e for e in reg["entries"] if e.get("integration_status") == "integrated"]
    evaluated = [e for e in reg["entries"] if e.get("integration_status") == "evaluated"]
    not_started = [e for e in reg["entries"] if e.get("integration_status") == "not_started"]
    today = date.today().isoformat()
    lines = [
        f"# MarketQuest Research Scout — {today}",
        "",
        f"Total registry entries: {reg['count']}",
        f"- Integrated: {len(integrated)}",
        f"- Evaluated: {len(evaluated)}",
        f"- Not started: {len(not_started)}",
        "",
        "## Integrated",
    ]
    for e in integrated:
        lines.append(f"- **{e['name']}** ({e.get('category', '')}) — {e.get('description', '')[:80]}")
    lines.extend(["", "## Ideas to explore next"])
    for e in not_started[:5]:
        lines.append(f"- {e['name']}: {', '.join(e.get('ideas_to_borrow', [])[:2])}")
    md = "\n".join(lines)
    reports_dir(root).mkdir(parents=True, exist_ok=True)
    path = reports_dir(root) / f"{today}_research_scout.md"
    path.write_text(md, encoding="utf-8")
    return {"report": md, "path": str(path), "generated_at": today}


def load_latest_report(repo: Path | None = None) -> dict[str, Any]:
    root = repo or repo_root()
    rdir = reports_dir(root)
    if not rdir.is_dir():
        return generate_report(root)
    files = sorted(rdir.glob("*_research_scout.md"), reverse=True)
    if not files:
        return generate_report(root)
    return {"report": files[0].read_text(encoding="utf-8"), "path": str(files[0])}
