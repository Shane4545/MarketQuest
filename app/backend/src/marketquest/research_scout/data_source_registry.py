"""Data source registry."""

from marketquest.research_scout.ai_tool_registry import _load_json
from phase1.paths import repo_root


def load_data_sources(repo=None):
    return _load_json(repo or repo_root(), "data_sources.json")
