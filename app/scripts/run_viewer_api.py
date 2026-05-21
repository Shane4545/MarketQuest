"""Read-only local API server for acquisition/pipeline run artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _bootstrap import ensure_phase1_path

repo_root = ensure_phase1_path()

from acquisition.run_viewer import list_run_ids, load_run_summary  # noqa: E402
from acquisition.run_launcher import (  # noqa: E402
    build_launcher_options,
    execute_launch,
    load_launcher_status,
)
from pencil.api import (  # noqa: E402
    get_journal,
    get_latest_predictions_from_journal,
    get_ledger,
    get_universe_status,
    list_journal_dates,
)
from marketquest.api import (  # noqa: E402
    execute_paper_order,
    execute_paper_trade,
    get_agents_debate,
    get_careers_panel,
    get_challenges_active,
    get_cross_asset,
    get_currencies,
    get_dashboard,
    get_education_panel,
    get_entity_graph,
    get_events,
    get_glossary_panel,
    get_leaderboard,
    get_learning_report,
    get_lessons_panel,
    get_picks,
    get_portfolio,
    get_regime,
    get_research_registry,
    get_research_report_panel,
    get_snapshot_latest,
    get_status,
    get_watchlist,
    refresh_reality,
    submit_challenge_answer,
)


class RunViewerHandler(SimpleHTTPRequestHandler):
    repo: Path
    web_dir: Path

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        relative = unquote(parsed.path or "").lstrip("/")
        return str((self.web_dir / relative).resolve())

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/runs":
            self._send_json({"runs": list_run_ids(self.repo)})
            return
        if parsed.path.startswith("/api/runs/"):
            run_id = parsed.path.removeprefix("/api/runs/").strip("/")
            if not run_id:
                self._send_json({"error": "run_id is required"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                summary = load_run_summary(self.repo, run_id)
            except FileNotFoundError:
                self._send_json({"error": f"run_id not found: {run_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(summary)
            return
        if parsed.path == "/api/run":
            run_id = parse_qs(parsed.query).get("id", [""])[0]
            if not run_id:
                self._send_json({"error": "query param id is required"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                summary = load_run_summary(self.repo, run_id)
            except FileNotFoundError:
                self._send_json({"error": f"run_id not found: {run_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(summary)
            return

        if parsed.path == "/api/run-launcher/options":
            self._send_json(build_launcher_options(self.repo))
            return

        if parsed.path == "/api/run-launcher/status":
            run_id = parse_qs(parsed.query).get("run_id", [""])[0]
            if not run_id:
                self._send_json({"error": "query param run_id is required"}, HTTPStatus.BAD_REQUEST)
                return
            st = load_launcher_status(self.repo, run_id)
            if st is None:
                self._send_json({"error": f"launcher_status not found for run_id={run_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(st)
            return

        if parsed.path == "/api/pencil/ledger":
            self._send_json(get_ledger(self.repo))
            return

        if parsed.path == "/api/pencil/journal":
            signal_date = parse_qs(parsed.query).get("date", [""])[0]
            if not signal_date:
                self._send_json({"dates": list_journal_dates()})
                return
            entry = get_journal(signal_date)
            if entry is None:
                self._send_json({"error": f"no journal for {signal_date}"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(entry)
            return

        if parsed.path == "/api/pencil/predictions/latest":
            latest = get_latest_predictions_from_journal()
            if latest is None:
                self._send_json({"error": "no pencil journals yet"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(latest)
            return

        if parsed.path == "/api/pencil/universe":
            signal_date = parse_qs(parsed.query).get("date", [""])[0] or None
            self._send_json(get_universe_status(signal_date or None))
            return

        mq_qs = parse_qs(parsed.query)
        mq_training = mq_qs.get("training", [""])[0] in ("1", "true", "yes") or mq_qs.get(
            "mock", [""]
        )[0] in ("1", "true", "yes")
        mq_refresh = mq_qs.get("refresh", [""])[0] in ("1", "true", "yes")

        if parsed.path == "/api/marketquest/dashboard":
            self._send_json(
                get_dashboard(
                    self.repo,
                    mock=mq_training,
                    refresh=mq_refresh,
                    user_id=mq_qs.get("user_id", ["default"])[0],
                )
            )
            return

        if parsed.path == "/api/marketquest/watchlist":
            self._send_json(get_watchlist(self.repo, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/picks":
            as_of = mq_qs.get("date", [""])[0] or None
            self._send_json(get_picks(self.repo, as_of=as_of, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/leaderboard":
            week = mq_qs.get("week", [""])[0] or None
            self._send_json(get_leaderboard(self.repo, week=week, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/portfolio":
            user_id = mq_qs.get("user_id", ["default"])[0]
            self._send_json(get_portfolio(self.repo, user_id, mock=mq_training))
            return

        if parsed.path == "/api/marketquest/education":
            self._send_json(get_education_panel(self.repo, mock=mq_training))
            return

        if parsed.path == "/api/marketquest/status":
            self._send_json(get_status(self.repo, mock=mq_training))
            return

        if parsed.path == "/api/marketquest/snapshot/latest":
            self._send_json(get_snapshot_latest(self.repo, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/events":
            self._send_json(get_events(self.repo, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/agents":
            sym = mq_qs.get("symbol", [""])[0] or None
            self._send_json(get_agents_debate(self.repo, symbol=sym, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/entity-graph":
            self._send_json(get_entity_graph(self.repo))
            return

        if parsed.path == "/api/marketquest/currencies":
            self._send_json(get_currencies(self.repo, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/cross-asset":
            self._send_json(get_cross_asset(self.repo, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/regime":
            self._send_json(get_regime(self.repo, mock=mq_training, refresh=mq_refresh))
            return

        if parsed.path == "/api/marketquest/learning-report":
            self._send_json(get_learning_report(self.repo))
            return

        if parsed.path == "/api/marketquest/education/glossary":
            self._send_json(get_glossary_panel(self.repo))
            return

        if parsed.path == "/api/marketquest/education/lessons":
            ctx = mq_qs.get("context", [""])[0] or None
            self._send_json(get_lessons_panel(self.repo, context=ctx))
            return

        if parsed.path == "/api/marketquest/challenges/active":
            self._send_json(get_challenges_active(self.repo, mock=mq_training))
            return

        if parsed.path == "/api/marketquest/careers":
            self._send_json(get_careers_panel(self.repo))
            return

        if parsed.path == "/api/marketquest/research/registry":
            cat = mq_qs.get("category", [""])[0] or None
            self._send_json(get_research_registry(self.repo, category=cat))
            return

        if parsed.path == "/api/marketquest/research/report":
            self._send_json(get_research_report_panel(self.repo))
            return

        # Avoid trailing-slash pages breaking relative assets (./foo → …/run-viewer/foo).
        if parsed.path == "/run-viewer/":
            self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
            loc = "/run-viewer"
            if parsed.query:
                loc = f"{loc}?{parsed.query}"
            self.send_header("Location", loc)
            self.end_headers()
            return
        if parsed.path == "/run-launcher/":
            self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
            loc = "/run-launcher"
            if parsed.query:
                loc = f"{loc}?{parsed.query}"
            self.send_header("Location", loc)
            self.end_headers()
            return

        if parsed.path == "/pencil-test/":
            self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
            loc = "/pencil-test"
            if parsed.query:
                loc = f"{loc}?{parsed.query}"
            self.send_header("Location", loc)
            self.end_headers()
            return

        if parsed.path == "/marketquest/":
            self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
            loc = "/marketquest"
            if parsed.query:
                loc = f"{loc}?{parsed.query}"
            self.send_header("Location", loc)
            self.end_headers()
            return

        if parsed.path in {"/", "/run-viewer"}:
            self.path = "/run_viewer.html"
        elif parsed.path in {"/run-launcher"}:
            self.path = "/run_launcher.html"
        elif parsed.path in {"/pencil-test"}:
            self.path = "/pencil_test.html"
        elif parsed.path in {"/marketquest"}:
            self.path = "/marketquest.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        try:
            body = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/marketquest/reality/refresh":
            mq_qs = parse_qs(parsed.query)
            mq_training = mq_qs.get("training", [""])[0] in ("1", "true", "yes") or mq_qs.get(
                "mock", [""]
            )[0] in ("1", "true", "yes")
            result = refresh_reality(self.repo, training=mq_training)
            self._send_json(result)
            return

        if parsed.path == "/api/marketquest/refresh":
            mq_qs = parse_qs(parsed.query)
            mq_training = mq_qs.get("training", [""])[0] in ("1", "true", "yes") or mq_qs.get(
                "mock", [""]
            )[0] in ("1", "true", "yes")
            result = refresh_reality(self.repo, training=mq_training)
            self._send_json(result)
            return

        if parsed.path == "/api/marketquest/portfolio/paper-trade":
            mq_qs = parse_qs(parsed.query)
            mq_training = mq_qs.get("training", [""])[0] in ("1", "true", "yes") or mq_qs.get(
                "mock", [""]
            )[0] in ("1", "true", "yes")
            result = execute_paper_trade(self.repo, body, mock=mq_training)
            self._send_json(result)
            return

        if parsed.path == "/api/marketquest/paper-order":
            mq_qs = parse_qs(parsed.query)
            mq_training = mq_qs.get("training", [""])[0] in ("1", "true", "yes") or mq_qs.get(
                "mock", [""]
            )[0] in ("1", "true", "yes")
            result = execute_paper_order(self.repo, body, mock=mq_training)
            self._send_json(result)
            return

        if parsed.path == "/api/marketquest/challenges/submit":
            mq_qs = parse_qs(parsed.query)
            mq_training = mq_qs.get("training", [""])[0] in ("1", "true", "yes") or mq_qs.get(
                "mock", [""]
            )[0] in ("1", "true", "yes")
            result = submit_challenge_answer(self.repo, body)
            self._send_json(result)
            return

        if parsed.path != "/api/run-launcher/launch":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        result = execute_launch(self.repo, body)
        # Always 200 so the browser can read validation vs operational failures from JSON.
        self._send_json(result)


def build_handler(repo: Path, web_dir: Path):
    class _Handler(RunViewerHandler):
        pass

    _Handler.repo = repo
    _Handler.web_dir = web_dir
    return _Handler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8010")))
    args = ap.parse_args()

    host = args.host
    if os.environ.get("PORT") and host in {"127.0.0.1", "localhost"}:
        host = "0.0.0.0"

    web_dir = repo_root / "web"
    handler = build_handler(repo_root, web_dir)
    server = ThreadingHTTPServer((host, args.port), handler)
    print(f"Run Viewer API listening on http://{host}:{args.port}/run-viewer")
    print(f"MarketQuest: http://{host}:{args.port}/marketquest")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
