"""Run MarketQuest nightly learning review."""

from __future__ import annotations

import argparse
import sys

from _bootstrap import ensure_phase1_path

repo_root = ensure_phase1_path()

from marketquest.learning.nightly_review import run_nightly_review  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="MarketQuest nightly review")
    args = ap.parse_args()
    path = run_nightly_review(repo_root)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
