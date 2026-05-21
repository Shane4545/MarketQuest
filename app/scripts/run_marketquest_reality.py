"""MarketQuest Reality Engine — collect real-market snapshots."""

from __future__ import annotations

import argparse
import sys

from _bootstrap import ensure_phase1_path

repo_root = ensure_phase1_path()

from marketquest.reality_engine.scheduler import run_loop  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="MarketQuest Reality Engine")
    ap.add_argument("--once", action="store_true", help="Run one collection cycle and exit")
    ap.add_argument("--daemon", action="store_true", help="Run scheduled loop")
    args = ap.parse_args()
    once = args.once or not args.daemon
    try:
        run_loop(repo_root, once=once)
    except KeyboardInterrupt:
        print("Reality Engine stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
