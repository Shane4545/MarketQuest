"""Build static MarketQuest site for GitHub Pages (docs/)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

_APP_SCRIPTS = Path(__file__).resolve().parent.parent / "app" / "scripts"
if str(_APP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_APP_SCRIPTS))

from _bootstrap import ensure_phase1_path

repo = ensure_phase1_path()

from marketquest.api import get_dashboard, get_learning_report  # noqa: E402

DOCS = repo / "pages"
DATA = DOCS / "data"
WEB = repo / "web"

STATIC_ASSETS = (
    "styles.css",
    "marketquest.css",
    "marketquest.js",
    "marketquest.html",
)


def main() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    DATA.mkdir(parents=True)

    dashboard = get_dashboard(repo, mock=True)
    dashboard["static_pages_mode"] = True
    dashboard["offline_training_mode"] = True

    (DATA / "dashboard.json").write_text(
        json.dumps(dashboard, indent=2, default=str),
        encoding="utf-8",
    )
    (DATA / "learning-report.json").write_text(
        json.dumps(get_learning_report(repo), indent=2, default=str),
        encoding="utf-8",
    )

    for name in STATIC_ASSETS:
        shutil.copy2(WEB / name, DOCS / name)

    (DOCS / "index.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="refresh" content="0; url=marketquest.html" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MarketQuest</title>
  <link rel="canonical" href="marketquest.html" />
</head>
<body>
  <p><a href="marketquest.html">Open MarketQuest</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    print(f"GitHub Pages build OK: {DOCS}")
    print(f"  dashboard.json: {len(json.dumps(dashboard))} bytes")


if __name__ == "__main__":
    main()
