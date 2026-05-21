"""Mini-challenge engine — 5 challenge types."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from marketquest.education.explanation_scoring import score_explanation
from marketquest.game.competition import score_learning_attempt
from marketquest.paths import education_data_dir, learning_dir
from phase1.paths import repo_root

CHALLENGE_TYPES = [
    "event_interpretation",
    "currency_connection",
    "filing_detective",
    "ai_vs_human",
    "skeptic_challenge",
]


def _day_key() -> str:
    return date.today().isoformat()


def _challenge_index(snapshot: dict[str, Any]) -> int:
    ts = snapshot.get("timestamp_utc") or _day_key()
    h = int(hashlib.md5(ts[:10].encode()).hexdigest(), 16)
    return h % len(CHALLENGE_TYPES)


def build_active_challenge(snapshot: dict[str, Any]) -> dict[str, Any]:
    ctype = CHALLENGE_TYPES[_challenge_index(snapshot)]
    events = snapshot.get("news_events") or []
    cross = snapshot.get("cross_asset") or {}
    headline = ""
    if events:
        headline = str(events[0].get("title") or events[0].get("headline") or "")

    if ctype == "event_interpretation":
        return {
            "challenge_id": f"{_day_key()}_event",
            "type": ctype,
            "title": "Event Interpretation Challenge",
            "prompt": f"Which sectors might be affected by: \"{headline[:120]}\"?",
            "hint": "Name sectors and explain why — uncertainty is OK.",
            "headline": headline,
        }
    if ctype == "currency_connection":
        forex = (cross.get("forex") or [{}])[0] if cross.get("forex") else {}
        oil = cross.get("oil") or {}
        return {
            "challenge_id": f"{_day_key()}_currency",
            "type": ctype,
            "title": "Currency Connection Challenge",
            "prompt": "Explain possible relationships between USD/CAD, oil, and a Canadian energy stock.",
            "usd_cad": forex.get("last"),
            "oil_wti": oil.get("value") if isinstance(oil, dict) else None,
            "hint": "Think trade, commodities, and cross-border revenue.",
        }
    if ctype == "filing_detective":
        filings = snapshot.get("sec_filings") or []
        f = filings[0] if filings else {}
        return {
            "challenge_id": f"{_day_key()}_filing",
            "type": ctype,
            "title": "Filing Detective Challenge",
            "prompt": f"Does this SEC filing look important or routine? {f.get('form_type', '8-K')} for {f.get('symbol', '???')}",
            "filing": f,
            "hint": "8-K material events vs routine N-CEN/NPORT filings.",
        }
    if ctype == "ai_vs_human":
        picks = snapshot.get("ai_agent_picks") or []
        ens = next((p for p in picks if p.get("agent_id") == "ensemble"), picks[0] if picks else {})
        return {
            "challenge_id": f"{_day_key()}_ai_human",
            "type": ctype,
            "title": "AI vs Human Challenge",
            "prompt": f"Make a paper prediction for {ens.get('symbol', 'SPY')}. Scored at 15m, 1h, 1d, 1w.",
            "ensemble_pick": ens.get("symbol"),
            "hint": "Paper only — compare your pick to agents after horizons elapse.",
        }
    # skeptic_challenge
    hype = headline or "Stock soars on AI breakthrough — analysts say massive upside"
    return {
        "challenge_id": f"{_day_key()}_skeptic",
        "type": ctype,
        "title": "Skeptic Challenge",
        "prompt": f"Find reasons this trade might fail: \"{hype[:120]}\"",
        "headline": hype,
        "hint": "Priced in? Stale data? Weak catalyst? Overhyped?",
    }


def get_active_challenge(repo: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    return build_active_challenge(snapshot)


def submit_challenge(
    repo: Path,
    *,
    challenge_id: str,
    answer: str,
    player_id: str = "default",
    expected_sectors: list[str] | None = None,
) -> dict[str, Any]:
    expl = score_explanation(answer, expected_sectors=expected_sectors)
    learning = score_learning_attempt(
        explanation_quality=expl["score"] / 2,
        uncertainty_identified=expl["uncertainty_bonus"],
        concept_mastery=min(5, expl["score"] / 2),
    )
    scores_path = learning_dir(repo) / "player_scores.json"
    learning_dir(repo).mkdir(parents=True, exist_ok=True)
    scores: dict[str, Any] = {}
    if scores_path.is_file():
        scores = json.loads(scores_path.read_text(encoding="utf-8"))
    player = scores.setdefault(player_id, {"learning_points": 0, "attempts": []})
    player["learning_points"] = round(
        float(player.get("learning_points", 0)) + learning["learning_points"], 2
    )
    player["attempts"].append(
        {"challenge_id": challenge_id, "points": learning["learning_points"], "answer_preview": answer[:80]}
    )
    scores_path.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "challenge_id": challenge_id,
        "explanation_score": expl,
        "learning": learning,
        "total_learning_points": player["learning_points"],
    }
