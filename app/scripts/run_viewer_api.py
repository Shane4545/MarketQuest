"""Read-only local API server for acquisition/pipeline run artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from _bootstrap import ensure_phase1_path

repo_root = ensure_phase1_path()

from acquisition.run_viewer import list_run_ids, load_run_summary  # noqa: E402
from acquisition.run_launcher import (  # noqa: E402
    build_launcher_options,
    execute_launch,
    load_launcher_status,
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

        if parsed.path in {"/", "/run-viewer"}:
            self.path = "/run_viewer.html"
        elif parsed.path in {"/run-launcher"}:
            self.path = "/run_launcher.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/run-launcher/launch":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        try:
            body = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON body"}, HTTPStatus.BAD_REQUEST)
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
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8010)
    args = ap.parse_args()

    web_dir = repo_root / "web"
    handler = build_handler(repo_root, web_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Run Viewer API listening on http://{args.host}:{args.port}/run-viewer")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
