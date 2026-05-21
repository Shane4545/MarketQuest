# MarketQuest — Deploy Guide

MarketQuest is a Python web app: static UI in `web/` plus API routes in `app/scripts/run_viewer_api.py`.

## Quick local run

```powershell
cd app/scripts
python run_viewer_api.py --port 8010
```

Open: http://127.0.0.1:8010/marketquest

Instant offline demo (no live providers): http://127.0.0.1:8010/marketquest?training=1

## Mobile

The UI is responsive (`web/marketquest.css`). Use your phone browser or devtools device mode. Tables scroll horizontally on small screens.

## Docker

```bash
docker build -t marketquest .
docker run -p 8010:8010 marketquest
```

## Render (recommended)

1. Push this repo to GitHub.
2. In [Render](https://render.com), **New → Blueprint** and connect the repo (uses `render.yaml`).
3. Optional: add API keys in Render env vars (`FINNHUB_API_KEY`, `FRED_API_KEY`, etc.). Without keys, yfinance + SEC EDGAR still work with honest DELAYED labels.
4. Deploy. Your app URL will be `https://<service>.onrender.com/marketquest`.

## Railway / Fly.io

Use the same Docker image. Set `PORT` from the platform; the server binds `0.0.0.0` automatically when `PORT` is set.

## Environment variables

Copy `config/marketquest.example.env` — never commit `.env`.

| Variable | Purpose |
|----------|---------|
| `FINNHUB_API_KEY` | Live quotes/news (optional) |
| `FRED_API_KEY` | Macro series (optional) |
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | Broker paper data (optional) |
| `MARKETQUEST_OFFLINE_TRAINING=1` | Fixture-only mode |

## GitHub setup

```powershell
gh auth login
gh repo create marketquest-v0 --public --source=. --remote=origin --push
```

Or create the repo on github.com, then:

```powershell
git remote add origin https://github.com/YOUR_USER/marketquest-v0.git
git push -u origin marketquest-reset
```
