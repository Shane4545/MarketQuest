"""Coverage summary for rule firing counts on synthetic fixture (no performance semantics)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import curated_dir, evidence_dir  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="latest")
    ap.add_argument("--as-of", default="2026-01-08")
    args = ap.parse_args()

    as_of = args.as_of
    cand_path = curated_dir() / f"candidates_{as_of}.parquet"
    rej_path = curated_dir() / f"rejected_candidates_{as_of}.parquet"

    cov = {
        "run_id": args.run_id,
        "as_of": as_of,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbols_selected_count": int(pd.read_parquet(cand_path).shape[0]) if cand_path.is_file() else 0,
        "symbols_rejected_count": int(pd.read_parquet(rej_path).shape[0]) if rej_path.is_file() else 0,
        "notes": "Synthetic fixture only — verifies routing thresholds and artifact wiring.",
    }

    if rej_path.is_file():
        rj = pd.read_parquet(rej_path)
        if "scan_reason" in rj.columns:
            cov["rejection_reason_histogram"] = (
                rj["scan_reason"].astype(str).value_counts().head(25).to_dict()
            )

    evidence_dir().mkdir(parents=True, exist_ok=True)
    outp = evidence_dir() / f"coverage_{args.run_id}_{as_of}.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(cov, f, indent=2)
    print(f"Wrote {outp}")


if __name__ == "__main__":
    main()
