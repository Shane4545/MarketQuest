"""Emit JSON manifest for latest Phase 1 run (paths hashes counts only — no performance claims)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import baskets_dir, curated_dir, evidence_dir, features_dir, staged_dir  # noqa: E402


def sha_file(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="latest")
    ap.add_argument("--as-of", default="2026-01-08")
    args = ap.parse_args()

    rid = args.run_id
    as_of = args.as_of

    staged = staged_dir() / "prices.parquet"
    feats = features_dir() / f"features_{as_of}.parquet"
    cand = curated_dir() / f"candidates_{as_of}.parquet"
    rej = curated_dir() / f"rejected_candidates_{as_of}.parquet"

    baskets = sorted(baskets_dir().glob("demo_auto_selected*.json"))

    manifest = {
        "run_id": rid,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of,
        "artifacts": {
            "staged_prices": {"path": str(staged), "sha256": sha_file(staged)},
            "features": {"path": str(feats), "sha256": sha_file(feats)},
            "candidates_selected": {"path": str(cand), "sha256": sha_file(cand)},
            "candidates_rejected": {"path": str(rej), "sha256": sha_file(rej)},
            "basket_files": [{"path": str(b), "sha256": sha_file(b)} for b in baskets],
        },
        "purpose": "Synthetic Phase 1 fixture validation — schema formulas gates — not market proof.",
    }

    evidence_dir().mkdir(parents=True, exist_ok=True)
    out = evidence_dir() / f"manifest_{rid}_{as_of}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
