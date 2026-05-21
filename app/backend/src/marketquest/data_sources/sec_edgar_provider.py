"""SEC EDGAR submissions — metadata only, no full filing text."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen

from marketquest.data_sources.base import FilingEvent, ProviderResult, utc_now_iso

USER_AGENT = "MarketQuest/1.0 (educational; contact@example.com)"


def fetch_recent_filings(symbols: list[str], *, limit: int = 5) -> ProviderResult:
    fetched = utc_now_iso()
    filings: list[FilingEvent] = []
    for sym in symbols[:6]:
        try:
            rows = _filings_for_symbol(sym, limit=limit)
            filings.extend(rows)
        except Exception:
            continue
    return ProviderResult(
        provider="sec_edgar",
        ok=bool(filings),
        fetched_at=fetched,
        freshness="DELAYED" if filings else "OFFLINE",
        filings=filings,
    )


def _filings_for_symbol(symbol: str, *, limit: int) -> list[FilingEvent]:
    cik = _lookup_cik(symbol)
    if not cik:
        return []
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession = recent.get("accessionNumber", [])
    out: list[FilingEvent] = []
    for i in range(min(limit, len(forms))):
        form = str(forms[i])
        filed = str(dates[i])
        acc = str(accession[i]).replace("-", "")
        url_f = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
        cat = "sec_8k" if form.startswith("8-K") else "sec_filing"
        out.append(
            FilingEvent(
                symbol=symbol.upper(),
                form_type=form,
                filed_at=filed,
                url=url_f,
                category=cat,
            )
        )
    return out


def _lookup_cik(symbol: str) -> str | None:
    url = "https://www.sec.gov/files/company_tickers.json"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    sym = symbol.upper()
    for entry in data.values():
        if str(entry.get("ticker", "")).upper() == sym:
            return str(entry.get("cik_str", "")).zfill(10)
    return None
