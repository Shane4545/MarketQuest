"""Open-source project registry."""

from marketquest.research_scout.ai_tool_registry import _load_json
from phase1.paths import repo_root


def load_projects(repo=None):
    from pathlib import Path
    return _load_json(repo or repo_root(), "open_source_projects.json")
