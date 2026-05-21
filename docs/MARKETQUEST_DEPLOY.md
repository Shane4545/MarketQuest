# MarketQuest — Deploy Guide

## GitHub Pages (phone + browser)

1. Push to `main` on https://github.com/Shane4545/MarketQuest
2. **Settings → Pages → Build and deployment → Source:** GitHub Actions
3. Wait for **Deploy GitHub Pages** workflow

**URL:** https://shane4545.github.io/MarketQuest/marketquest.html

Static demo with offline fixtures. Paper trades persist in your browser session only.

## Local live server

```powershell
cd app/scripts
python run_viewer_api.py --port 8010
```

Open http://127.0.0.1:8010/marketquest
