"""News/Sentiment Agent — VADER-weighted news features."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from marketquest.agents._pick import make_pick, ensure_pick_schema
from marketquest.config import load_config, today_iso


def _news_articles_for_symbol(sym: str, cfg: dict) -> list[dict[str, Any]]:
    try:
        from news.fetch_news import fetch_news_batch

        end = date.today()
        start = end - timedelta(days=3)
        batch = fetch_news_batch([sym], start, end)
        return batch.get(sym.upper(), batch.get(sym, []))
    except Exception:
        return []


def run_news_sentiment_agent(
    repo: Path,
    *,
    as_of: str | None = None,
    mock: bool = False,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    cfg = load_config(repo)
    syms = symbols or cfg["symbols"]

    if mock:
        from marketquest.scoring.orchestrator import load_fixture_picks

        for p in load_fixture_picks(repo):
            if p.get("agent_id") == "news_sentiment":
                p = ensure_pick_schema(p)
                p["agent_id"] = "news"
                return p
        return make_pick(
            symbol="TSLA",
            agent_id="news_sentiment",
            as_of=as_of,
            score=0.65,
            predicted_bias="bullish",
            headline="Positive news sentiment cluster (mock)",
            bullets=["sentiment_mean elevated", "multiple articles in 48h"],
            features={"sentiment_mean": 0.42, "news_count_48h": 5},
            news=[
                {"title": "Mock headline: product update", "sentiment": 0.5, "source": "fixture"}
            ],
            data_mode="mock",
        )

    try:
        from news.fetch_news import fetch_news_batch
        from news.sentiment_scorer import build_news_feature_map

        end = date.today()
        start = end - timedelta(days=3)
        batch = fetch_news_batch(syms, start, end)
        nf_map = build_news_feature_map(batch, cfg)
    except Exception:
        nf_map = {}

    best_sym = syms[0]
    best_score = -999.0
    best_nf: dict[str, Any] = {}
    best_arts: list[dict] = []

    for sym in syms:
        nf = nf_map.get(sym.upper(), nf_map.get(sym, {}))
        sent = float(nf.get("sentiment_mean") or 0)
        cnt = int(nf.get("news_count_48h") or 0)
        combined = sent + 0.05 * min(cnt, 10)
        if combined > best_score:
            best_score = combined
            best_sym = sym.upper()
            best_nf = nf
            try:
                best_arts = batch.get(sym.upper(), batch.get(sym, []))[:5]
            except Exception:
                best_arts = []

    news_ui = []
    for art in best_arts[:5]:
        title = str(art.get("title") or "News item")
        try:
            from news.sentiment_scorer import score_text_vader

            sent = score_text_vader(title)
        except Exception:
            sent = 0.0
        news_ui.append(
            {
                "title": title,
                "sentiment": round(sent, 3),
                "source": str(art.get("publisher") or art.get("source") or "news"),
            }
        )

    sent_mean = float(best_nf.get("sentiment_mean") or 0)
    bias = "bullish" if sent_mean > 0.1 else "bearish" if sent_mean < -0.1 else "neutral"

    return make_pick(
        symbol=best_sym,
        agent_id="news_sentiment",
        as_of=as_of,
        score=best_score,
        predicted_bias=bias,
        headline=f"News sentiment leader: {best_sym}",
        bullets=[
            f"Mean sentiment (48h): {sent_mean:.3f}",
            f"Article count: {best_nf.get('news_count_48h', 0)}",
            "VADER compound + recency weighting",
        ],
        features=best_nf,
        news=news_ui,
        data_mode="live" if nf_map else "mock",
        runners_up=[s for s in syms if s.upper() != best_sym][:3],
    )
