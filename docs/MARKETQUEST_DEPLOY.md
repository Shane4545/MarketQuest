# MarketQuest — Deploy Guide

## GitHub Pages (phone + browser)

1. Push to `main` — workflow builds and updates the `gh-pages` branch.
2. **Settings → Pages → Build and deployment**
3. **Source:** Deploy from a branch → **gh-pages** / **/ (root)**
4. Save, wait ~1 minute

**URL:** https://shane4545.github.io/MarketQuest/marketquest.html

Static demo with offline fixtures. Paper trades persist in your browser session only.

## Local live server

```powershell
cd app/scripts
python run_viewer_api.py --port 8010
```

Open http://127.0.0.1:8010/marketquest
