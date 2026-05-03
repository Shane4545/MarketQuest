/**
 * Portfolio Allocation Optimizer — two-day snapshot; dollar allocations from imported ranked_results only.
 * Multiples = exit_close / entry_close. No invented prices. No brokers.
 */

const TASK_ID = "DASHBOARD_001";

/** Comparison + banner + failure analysis all use the same six allocation presets. */
const NUM_ALLOCATION_MODES = 6;

let snapshotData = null;
/** @type {Record<string, number>} manual dollar allocation per ticker */
let manualDollarsByTicker = {};

const diagnostics = {
  fileLoaded: false,
  requiredFieldsPresent: false,
  bestResultPresent: false,
  rankedResultCount: 0,
  calculation: "idle",
  missingFields: [],
  lastError: null,
  sourcePath: null,
  mismatchWarnings: [],
  parseError: null,
  recomputedTopTicker: null,
  importBestTicker: null,
  recomputedTopMatchesImport: null,
  maxDollarsRemainder: 0,
  minStocksNote: null,
  /** `?demo=1` fetch to /reports/live_market_snapshot.json */
  demoLoadPending: false,
  demoLoadFailed: false,
  demoLoadError: null,
};

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtMoney(x) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return Number(x).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtNum(x, digits = 6) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return Number(x).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function computeMultipleFromCloses(entryClose, exitClose) {
  const ec = Number(entryClose);
  const xc = Number(exitClose);
  if (!(ec > 0) || !Number.isFinite(xc)) return NaN;
  return xc / ec;
}

function computePercentFromCloses(entryClose, exitClose) {
  const ec = Number(entryClose);
  const xc = Number(exitClose);
  if (!(ec > 0) || !Number.isFinite(xc)) return NaN;
  return ((xc - ec) / ec) * 100;
}

function nearlyMaterialDiff(a, b, relTol = 1e-4) {
  if (!Number.isFinite(a) || !Number.isFinite(b)) return true;
  return Math.abs(a - b) > Math.max(1e-9, relTol * Math.max(Math.abs(a), Math.abs(b)));
}

function validateSnapshot(data) {
  const missing = [];
  if (!data || typeof data !== "object") missing.push("root object");
  if (!data.best_result) missing.push("best_result");
  if (!Array.isArray(data.ranked_results)) missing.push("ranked_results[]");
  const br = data.best_result;
  if (br) {
    ["ticker", "entry_close", "exit_close"].forEach((k) => {
      if (br[k] == null) missing.push("best_result." + k);
    });
  }
  return { ok: missing.length === 0, missing };
}

function enrichRanked(data) {
  return (data.ranked_results || []).map((r) => ({
    ...r,
    mult: computeMultipleFromCloses(r.entry_close, r.exit_close),
  }));
}

function sortByRankAsc(rows) {
  return [...rows].sort((a, b) => (a.rank || 0) - (b.rank || 0));
}

function sortByMultDesc(rows) {
  return [...rows].sort((a, b) => {
    const d = (b.mult || 0) - (a.mult || 0);
    if (d !== 0) return d;
    return String(a.ticker).localeCompare(String(b.ticker));
  });
}

function findBestMultipleRow(rows) {
  let best = null;
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    if (!Number.isFinite(r.mult)) continue;
    if (
      !best ||
      r.mult > best.mult ||
      (Math.abs(r.mult - best.mult) < 1e-15 && String(r.ticker) < String(best.ticker))
    ) {
      best = r;
    }
  }
  return best;
}

function buildMultMap(rows) {
  const m = {};
  rows.forEach((r) => {
    m[r.ticker] = r.mult;
  });
  return m;
}

function rowMapByTicker(rows) {
  const o = {};
  rows.forEach((r) => {
    o[r.ticker] = r;
  });
  return o;
}

/** Portfolio ending = sum_i allocated_cash_i * return_multiple_i */
function portfolioEndingFromAlloc(allocMap, multMap) {
  let end = 0;
  Object.keys(allocMap).forEach((t) => {
    const a = allocMap[t];
    const m = multMap[t];
    if (a > 1e-15 && Number.isFinite(m)) end += a * m;
  });
  return end;
}

function sumAllocMap(allocMap) {
  let s = 0;
  Object.keys(allocMap).forEach((t) => {
    s += Math.max(0, allocMap[t] || 0);
  });
  return s;
}

function countPositiveAlloc(allocMap) {
  let n = 0;
  Object.keys(allocMap).forEach((t) => {
    if (allocMap[t] > 1e-10) n++;
  });
  return n;
}

function largestAllocationDollars(allocMap) {
  let m = 0;
  Object.keys(allocMap).forEach((t) => {
    if (allocMap[t] > m) m = allocMap[t];
  });
  return m;
}

function dollarsToWeights(allocMap, startCash) {
  const w = {};
  if (startCash <= 1e-15) return w;
  Object.keys(allocMap).forEach((t) => {
    const a = allocMap[t];
    if (a > 1e-15) w[t] = a / startCash;
  });
  return w;
}

/** Unconstrained max return: all starting cash on highest multiple (simplex vertex proof in UI). */
function allocUnconstrainedMax(rows, startCash) {
  const best = findBestMultipleRow(rows);
  if (!best || !Number.isFinite(startCash) || startCash <= 0) return {};
  return { [best.ticker]: startCash };
}

/** Greedy by import rank (ascending): fill up to max $ per stock until cash exhausted. */
function allocMaxDollarsPerStock(rowsSortedRank, startCash, maxDollarsPerStock) {
  const cap = Math.max(0, Number(maxDollarsPerStock) || 0);
  const alloc = {};
  let rem = startCash;
  for (let i = 0; i < rowsSortedRank.length; i++) {
    if (rem <= 1e-12) break;
    const r = rowsSortedRank[i];
    if (!Number.isFinite(r.mult)) continue;
    const take = Math.min(rem, cap > 0 ? cap : rem);
    if (take <= 1e-15) break;
    alloc[r.ticker] = (alloc[r.ticker] || 0) + take;
    rem -= take;
  }
  return { alloc, remainder: rem };
}

function greedyMaxCapWeights(sortedMultDesc, maxPctDecimal) {
  const cap = Math.min(1, Math.max(0, maxPctDecimal));
  const weights = {};
  let rem = 1;
  for (let i = 0; i < sortedMultDesc.length; i++) {
    if (rem <= 1e-12) break;
    const r = sortedMultDesc[i];
    if (!Number.isFinite(r.mult)) continue;
    const take = Math.min(cap, rem);
    if (take <= 1e-15) continue;
    weights[r.ticker] = take;
    rem -= take;
  }
  return { weights, remainder: rem };
}

function allocMaxPctPerStock(rowsSortedMult, startCash, maxPct) {
  const r = greedyMaxCapWeights(rowsSortedMult, maxPct / 100);
  const dollars = {};
  const S = startCash;
  Object.keys(r.weights).forEach((t) => {
    if (r.weights[t] > 1e-15) dollars[t] = r.weights[t] * S;
  });
  return { alloc: dollars, weightRemainder: r.remainder };
}

function allocEqualTopN(rowsByRank, startCash, n) {
  const ranked = rowsByRank.filter((r) => Number.isFinite(r.mult));
  const N = Math.max(1, Math.min(Math.floor(n), ranked.length));
  const slice = ranked.slice(0, N);
  if (!slice.length || startCash <= 0) return {};
  const each = startCash / slice.length;
  const alloc = {};
  slice.forEach((r) => {
    alloc[r.ticker] = each;
  });
  return alloc;
}

/**
 * At least K stocks with positive dollars: top K by multiple get floor ε, remainder on best-of-K.
 */
function allocMinNumStocks(rowsSortedMult, startCash, minK) {
  const valid = rowsSortedMult.filter((r) => Number.isFinite(r.mult));
  const Kwant = Math.max(1, Math.floor(minK));
  const K = Math.min(Kwant, valid.length);
  diagnostics.minStocksNote = null;
  if (!K || startCash <= 0) return {};
  if (valid.length < Kwant) {
    diagnostics.minStocksNote =
      "Universe has fewer valid rows than requested minimum; using all " + valid.length + " with positive multiples.";
  }
  const top = valid.slice(0, K);
  const eps = Math.min(0.01, startCash / (2 * K));
  if (K * eps > startCash + 1e-6) {
    const eq = startCash / K;
    const alloc = {};
    top.forEach((r) => {
      alloc[r.ticker] = eq;
    });
    return alloc;
  }
  const rem = startCash - K * eps;
  const alloc = {};
  top.forEach((r, i) => {
    alloc[r.ticker] = i === 0 ? eps + rem : eps;
  });
  return alloc;
}

function sumManualDollars(rows) {
  let s = 0;
  rows.forEach((r) => {
    s += Math.max(0, Number(manualDollarsByTicker[r.ticker]) || 0);
  });
  return s;
}

function allocManualDollarsMap(rows) {
  const alloc = {};
  rows.forEach((r) => {
    const v = Math.max(0, Number(manualDollarsByTicker[r.ticker]) || 0);
    if (v > 1e-12) alloc[r.ticker] = v;
  });
  return alloc;
}

function manualAllocNormalizedToStart(rows, startCash) {
  const sum = sumManualDollars(rows);
  if (sum <= 1e-12) return {};
  const out = {};
  rows.forEach((r) => {
    const v = Math.max(0, Number(manualDollarsByTicker[r.ticker]) || 0);
    if (v > 0) out[r.ticker] = (v / sum) * startCash;
  });
  return out;
}

const MANUAL_SUM_TOL = 0.02;

function manualAllocValid(rows, startCash) {
  return Math.abs(sumManualDollars(rows) - startCash) <= MANUAL_SUM_TOL;
}

function computeTargetBlock(startCash, endingCash, targetCash) {
  const reqMult = targetCash / startCash;
  const achMult = endingCash / startCash;
  const achieved = endingCash >= targetCash - 1e-9 * Math.max(1, targetCash);
  const distanceFromTarget = targetCash - endingCash;
  const percentOfTarget = targetCash > 0 ? (endingCash / targetCash) * 100 : 0;
  return { reqMult, achMult, achieved, distanceFromTarget, percentOfTarget };
}

function outcomeRowFromAlloc(methodLabel, allocMap, startCash, targetCash, multMap) {
  const ending = portfolioEndingFromAlloc(allocMap, multMap);
  const portMult = startCash > 0 ? ending / startCash : NaN;
  const portPct = startCash > 0 ? ((ending - startCash) / startCash) * 100 : NaN;
  const tm = computeTargetBlock(startCash, ending, targetCash);
  return {
    method: methodLabel,
    nStocks: countPositiveAlloc(allocMap),
    largestAlloc: largestAllocationDollars(allocMap),
    endingCash: ending,
    portMult,
    portPct,
    targetAchieved: tm.achieved,
    distance: tm.distanceFromTarget,
  };
}

function parseSnapshot(text, sourceLabel) {
  diagnostics.parseError = null;
  diagnostics.mismatchWarnings = [];
  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    diagnostics.parseError = String(e.message || e);
    throw new Error("Invalid JSON: " + e.message);
  }
  const v = validateSnapshot(data);
  diagnostics.missingFields = v.missing;
  diagnostics.requiredFieldsPresent = v.ok;
  if (!v.ok) {
    diagnostics.calculation = "blocked";
    throw new Error("Snapshot incomplete: " + v.missing.join(", "));
  }
  snapshotData = data;
  diagnostics.fileLoaded = true;
  diagnostics.bestResultPresent = true;
  diagnostics.sourcePath = sourceLabel || "memory";
  diagnostics.rankedResultCount = (data.ranked_results || []).length;
  diagnostics.calculation = "ready";

  const enriched = enrichRanked(data);
  const sortedRank = sortByRankAsc(enriched);
  manualDollarsByTicker = {};
  sortedRank.forEach((r) => {
    manualDollarsByTicker[r.ticker] = 0;
  });
}

function getInputs() {
  const startCash = Math.max(Number($("startCash").value) || 0, 1e-12);
  const targetCash = Math.max(Number($("targetCash").value) || 0, 1e-12);
  const allocMode = ($("allocMode") && $("allocMode").value) || "unconstrained_max";
  const topN = Math.max(1, Math.floor(Number($("allocTopN") && $("allocTopN").value) || 5));
  const maxPct = Math.min(100, Math.max(0.01, Number($("allocMaxPct") && $("allocMaxPct").value) || 25));
  const maxDollarsPerStock = Math.max(0.01, Number($("allocMaxDollars") && $("allocMaxDollars").value) || 20);
  const minStocks = Math.max(1, Math.floor(Number($("allocMinStocks") && $("allocMinStocks").value) || 5));
  return { startCash, targetCash, allocMode, topN, maxPct, maxDollarsPerStock, minStocks };
}

function auditMismatchForBest(br) {
  const warnings = [];
  const ec = Number(br.entry_close);
  const xc = Number(br.exit_close);
  const mCalc = computeMultipleFromCloses(ec, xc);
  const mImp = br.return_multiple != null ? Number(br.return_multiple) : NaN;
  const pCalc = computePercentFromCloses(ec, xc);
  const pImp = br.percent_return != null ? Number(br.percent_return) : NaN;

  if (Number.isFinite(mCalc) && Number.isFinite(mImp) && nearlyMaterialDiff(mImp, mCalc)) {
    warnings.push(
      "Stored return_multiple vs recomputed from closes (" + fmtNum(mImp, 8) + " vs " + fmtNum(mCalc, 8) + ")"
    );
  }
  if (Number.isFinite(pCalc) && Number.isFinite(pImp) && nearlyMaterialDiff(pImp, pCalc, 1e-3)) {
    warnings.push(
      "Stored percent_return vs closes-based % (" + fmtNum(pImp, 6) + " vs " + fmtNum(pCalc, 6) + ")"
    );
  }
  return warnings;
}

function verifyTopStock(rows, br) {
  const win = findBestMultipleRow(rows);
  diagnostics.importBestTicker = br.ticker;
  diagnostics.recomputedTopTicker = win ? win.ticker : null;
  diagnostics.recomputedTopMatchesImport = !!(win && br && win.ticker === br.ticker);
  const w = [];
  if (win && br && win.ticker !== br.ticker) {
    w.push(
      "Imported best_result.ticker (" +
        br.ticker +
        ") differs from recomputed top-return ticker (" +
        win.ticker +
        ") — verify ranks/closes in the JSON."
    );
  }
  return w;
}

function getActiveAllocMap(rowsSortedRank, rowsSortedMult) {
  const { startCash, allocMode, topN, maxPct, maxDollarsPerStock, minStocks } = getInputs();
  diagnostics.maxDollarsRemainder = 0;
  if (allocMode === "unconstrained_max") {
    return allocUnconstrainedMax(rowsSortedRank, startCash);
  }
  if (allocMode === "max_dollars") {
    const r = allocMaxDollarsPerStock(rowsSortedRank, startCash, maxDollarsPerStock);
    diagnostics.maxDollarsRemainder = r.remainder;
    return r.alloc;
  }
  if (allocMode === "max_pct") {
    const r = allocMaxPctPerStock(rowsSortedMult, startCash, maxPct);
    return r.alloc;
  }
  if (allocMode === "min_stocks") {
    return allocMinNumStocks(rowsSortedMult, startCash, minStocks);
  }
  if (allocMode === "equal") {
    return allocEqualTopN(rowsSortedRank, startCash, topN);
  }
  if (allocMode === "manual") {
    if (!manualAllocValid(rowsSortedRank, startCash)) return null;
    return allocManualDollarsMap(rowsSortedRank);
  }
  return allocUnconstrainedMax(rowsSortedRank, startCash);
}

function renderAllocControlVisibility() {
  const mode = ($("allocMode") && $("allocMode").value) || "unconstrained_max";
  const shows = {
    wrapAllocTopN: mode === "equal",
    wrapAllocMaxPct: mode === "max_pct",
    wrapAllocMaxDollars: mode === "max_dollars",
    wrapAllocMinStocks: mode === "min_stocks",
  };
  Object.keys(shows).forEach((id) => {
    const el = $(id);
    if (el) el.style.display = shows[id] ? "" : "none";
  });
}

function renderComparisonTable(rowsSortedRank, rowsSortedMult, multMap) {
  const { startCash, targetCash, topN, maxPct, maxDollarsPerStock, minStocks } = getInputs();
  const tbody = $("comparisonBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  const rows = [];
  rows.push(
    outcomeRowFromAlloc(
      "Unconstrained maximum return",
      allocUnconstrainedMax(rowsSortedRank, startCash),
      startCash,
      targetCash,
      multMap
    )
  );

  rows.push(
    outcomeRowFromAlloc(
      "Maximum dollars per stock (max $" + fmtMoney(maxDollarsPerStock) + " / name)",
      allocMaxDollarsPerStock(rowsSortedRank, startCash, maxDollarsPerStock).alloc,
      startCash,
      targetCash,
      multMap
    )
  );

  rows.push(
    outcomeRowFromAlloc(
      "Maximum percent per stock (max " + fmtNum(maxPct, 4) + "% / name)",
      allocMaxPctPerStock(rowsSortedMult, startCash, maxPct).alloc,
      startCash,
      targetCash,
      multMap
    )
  );

  rows.push(
    outcomeRowFromAlloc(
      "Minimum number of stocks (≥ " + minStocks + " names)",
      allocMinNumStocks(rowsSortedMult, startCash, minStocks),
      startCash,
      targetCash,
      multMap
    )
  );

  rows.push(
    outcomeRowFromAlloc("Equal weight top " + topN, allocEqualTopN(rowsSortedRank, startCash, topN), startCash, targetCash, multMap)
  );

  const sumM = sumManualDollars(rowsSortedRank);
  if (sumM > 1e-12) {
    const mw = manualAllocNormalizedToStart(rowsSortedRank, startCash);
    rows.push(outcomeRowFromAlloc("Manual allocation (normalized to starting cash)", mw, startCash, targetCash, multMap));
  } else {
    rows.push({
      method: "Manual allocation (normalized to starting cash)",
      nStocks: "—",
      largestAlloc: NaN,
      endingCash: NaN,
      portMult: NaN,
      portPct: NaN,
      targetAchieved: false,
      distance: NaN,
      skip: true,
    });
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    if (row.skip) {
      tr.innerHTML =
        "<td colspan=\"8\" class=\"cell-muted\">" +
        escapeHtml(row.method) +
        " — enter dollar amounts in the ranked table, then Normalize to starting cash.</td>";
    } else {
      const tm = computeTargetBlock(startCash, row.endingCash, targetCash);
      tr.innerHTML =
        "<td>" +
        escapeHtml(row.method) +
        "</td><td>" +
        row.nStocks +
        "</td><td>$" +
        fmtMoney(row.largestAlloc) +
        "</td><td>$" +
        fmtMoney(row.endingCash) +
        "</td><td>" +
        fmtNum(row.portMult, 10) +
        "</td><td>" +
        fmtNum(row.portPct) +
        "</td><td>" +
        (row.targetAchieved ? "Yes" : "No") +
        "</td><td>$" +
        fmtMoney(tm.distanceFromTarget) +
        "</td>";
    }
    tbody.appendChild(tr);
  });
}

function getStandardModeAllocations(rowsSortedRank, rowsSortedMult) {
  const { startCash, topN, maxPct, maxDollarsPerStock, minStocks } = getInputs();
  return [
    { label: "Unconstrained maximum return", alloc: allocUnconstrainedMax(rowsSortedRank, startCash) },
    { label: "Maximum dollars per stock", alloc: allocMaxDollarsPerStock(rowsSortedRank, startCash, maxDollarsPerStock).alloc },
    { label: "Maximum percent per stock", alloc: allocMaxPctPerStock(rowsSortedMult, startCash, maxPct).alloc },
    { label: "Minimum number of stocks", alloc: allocMinNumStocks(rowsSortedMult, startCash, minStocks) },
    { label: "Equal weight top N", alloc: allocEqualTopN(rowsSortedRank, startCash, topN) },
    {
      label: "Manual allocation",
      alloc:
        sumManualDollars(rowsSortedRank) > 1e-12
          ? manualAllocNormalizedToStart(rowsSortedRank, startCash)
          : {},
    },
  ];
}

function renderTargetAnyModeBanner(rowsSortedRank, rowsSortedMult, multMap) {
  const el = $("targetAnyModeBanner");
  if (!el) return;
  const { startCash, targetCash } = getInputs();

  const modes = getStandardModeAllocations(rowsSortedRank, rowsSortedMult);

  const hits = [];
  modes.forEach((m) => {
    const end = portfolioEndingFromAlloc(m.alloc, multMap);
    if (Number.isFinite(end) && end >= targetCash - 1e-9 * Math.max(1, targetCash)) {
      hits.push({ label: m.label, alloc: m.alloc, ending: end });
    }
  });

  if (!hits.length) {
    el.innerHTML =
      "<p><strong>Target check (all modes vs current starting &amp; target cash):</strong> " +
      "<span class=\"target-nohit\">Target not reached in the loaded data.</span> " +
      "No tested allocation mode meets the target using only imported entry/exit closes in this scan universe.</p>";
    return;
  }

  const bits = hits.map((h) => {
    const lines = Object.keys(h.alloc)
      .filter((t) => h.alloc[t] > 1e-8)
      .sort()
      .map((t) => escapeHtml(t) + ": $" + fmtMoney(h.alloc[t]))
      .join("; ");
    return (
      "<p class=\"target-hit-mode\"><strong>" +
      escapeHtml(h.label) +
      "</strong> — ending <strong>$" +
      fmtMoney(h.ending) +
      "</strong> ≥ target. Allocation: " +
      (lines || "—") +
      "</p>"
    );
  });

  el.innerHTML =
    "<div class=\"target-any-wrap\"><strong>Target reached by at least one tested mode:</strong>" +
    bits.join("") +
    "</div>";
}

function renderTargetFailureAnalysis(rowsSortedRank, rowsSortedMult, multMap) {
  const sec = $("targetFailureSection");
  const inner = $("targetFailureInner");
  const harder = $("searchHarderSection");
  if (!sec || !inner) return;
  if (!snapshotData) {
    sec.classList.add("panel-hidden");
    if (harder) harder.classList.add("panel-hidden");
    return;
  }
  sec.classList.remove("panel-hidden");
  if (harder) harder.classList.remove("panel-hidden");

  const { startCash, targetCash } = getInputs();
  const modes = getStandardModeAllocations(rowsSortedRank, rowsSortedMult);
  let hitCount = 0;
  modes.forEach((m) => {
    const end = portfolioEndingFromAlloc(m.alloc, multMap);
    if (Number.isFinite(end) && end >= targetCash - 1e-9 * Math.max(1, targetCash)) hitCount++;
  });

  const winner = findBestMultipleRow(rowsSortedRank);
  const bestMult = winner && Number.isFinite(winner.mult) ? winner.mult : NaN;
  const bestEnding = Number.isFinite(bestMult) ? startCash * bestMult : NaN;
  const reqMult = startCash > 0 ? targetCash / startCash : NaN;
  const shortfall = Number.isFinite(bestEnding) ? Math.max(0, targetCash - bestEnding) : NaN;
  const nRanked = (snapshotData.ranked_results || []).length;

  if (hitCount > 0) {
    inner.innerHTML =
      '<p class="target-success-note"><strong>Target reached under at least one tested mode</strong> with your current starting and target cash. ' +
      "The detailed gap analysis is omitted because the loaded outcomes already allow meeting the target.</p>";
    return;
  }

  const reqMultDisplay =
    Number.isFinite(reqMult) && reqMult >= 1000 && Math.abs(reqMult - Math.round(reqMult)) < 1e-6
      ? Math.round(reqMult).toLocaleString() + "×"
      : fmtNum(reqMult, 8) + "×";

  inner.innerHTML =
    '<p class="target-failure-callout">Target not reached in the loaded data.</p>' +
    '<p class="target-failure-intro">Using only this imported two-day long-only scan (current starting and target cash):</p>' +
    '<div class="target-failure-metrics">' +
    "<dl><dt>1. Starting cash</dt><dd>$" +
    fmtMoney(startCash) +
    "</dd></dl>" +
    "<dl><dt>2. Target cash</dt><dd>$" +
    fmtMoney(targetCash) +
    "</dd></dl>" +
    "<dl><dt>3. Required multiple</dt><dd>" +
    reqMultDisplay +
    " <span class=\"metric-hint\">(target ÷ start)</span></dd></dl>" +
    "<dl><dt>4. Best multiple found in imported data</dt><dd>≈ " +
    fmtNum(bestMult, 4) +
    "×</dd></dl>" +
    "<dl><dt>5. Best ending cash</dt><dd>≈ $" +
    fmtMoney(bestEnding) +
    " <span class=\"metric-hint\">(all cash in best multiple)</span></dd></dl>" +
    "<dl><dt>6. Dollar shortfall</dt><dd>≈ $" +
    fmtMoney(shortfall) +
    " <span class=\"metric-hint\">(target − best ending)</span></dd></dl>" +
    "<dl><dt>7. Number of ranked stocks inspected</dt><dd>" +
    nRanked +
    "</dd></dl>" +
    "<dl><dt>8. Number of allocation modes tested</dt><dd>" +
    NUM_ALLOCATION_MODES +
    "</dd></dl>" +
    "<dl><dt>9. Number of target-reaching allocations found</dt><dd>" +
    hitCount +
    "</dd></dl>" +
    "</div>" +
    '<p class="target-failure-explain">' +
    "<strong>Weighted average limit (single two-day long-only scan):</strong> " +
    "Splitting money across multiple stocks creates a weighted average of returns. " +
    "A weighted average cannot exceed the highest individual return unless extra mechanisms are introduced, " +
    "such as leverage, options, short selling, intraday high/low timing, or a different/broader universe.</p>";
}

function renderAllocationDetailPanel(allocMap, rowByTicker, startCash, multMap, targetCash, endingPortfolio) {
  const sec = $("allocationDetailSection");
  const tb = $("allocationDetailBody");
  const sumEl = $("allocationPortfolioSummary");
  if (!sec || !tb || !sumEl) return;
  if (!Number.isFinite(endingPortfolio) || Object.keys(allocMap).length === 0) {
    sec.classList.add("panel-hidden");
    tb.innerHTML = "";
    sumEl.innerHTML = "";
    return;
  }
  sec.classList.remove("panel-hidden");
  tb.innerHTML = "";
  const tickers = Object.keys(allocMap).filter((t) => allocMap[t] > 1e-12 && Number.isFinite(multMap[t]));
  tickers.sort((a, b) => allocMap[b] - allocMap[a]);
  tickers.forEach((t) => {
    const a = allocMap[t];
    const m = multMap[t];
    const pctOfStart = startCash > 0 ? (a / startCash) * 100 : 0;
    const endPos = a * m;
    const profit = endPos - a;
    const r = rowByTicker[t];
    const tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" +
      escapeHtml(t) +
      "</td><td>" +
      escapeHtml((r && r.name) || "—") +
      "</td><td>" +
      escapeHtml(String((r && r.rank) != null ? r.rank : "—")) +
      "</td><td>$" +
      fmtMoney(a) +
      "</td><td>" +
      fmtNum(pctOfStart, 4) +
      "%</td><td>" +
      fmtNum(r ? r.entry_close : NaN) +
      "</td><td>" +
      fmtNum(r ? r.exit_close : NaN) +
      "</td><td>" +
      fmtNum(m, 10) +
      "</td><td>$" +
      fmtMoney(endPos) +
      "</td><td>$" +
      fmtMoney(profit) +
      "</td><td>" +
      caveatsHtml((r && r.caveats) || []) +
      "</td>";
    tb.appendChild(tr);
  });
  const tm = computeTargetBlock(startCash, endingPortfolio, targetCash);
  sumEl.innerHTML =
    "<p><strong>Portfolio ending cash:</strong> $" +
    fmtMoney(endingPortfolio) +
    " · <strong>Portfolio return multiple:</strong> " +
    fmtNum(endingPortfolio / startCash, 10) +
    " · <strong>Portfolio % return:</strong> " +
    fmtNum(((endingPortfolio - startCash) / startCash) * 100) +
    " · <strong>Target reached:</strong> " +
    (tm.achieved ? "Yes" : "No") +
    " · <strong>Distance from target:</strong> $" +
    fmtMoney(tm.distanceFromTarget) +
    "</p>";
}

function renderBestActive(rowsSortedRank, rowsSortedMult, multMap, rowByTicker) {
  const { startCash, targetCash, allocMode } = getInputs();
  const inner = $("bestCommandInner");
  if (allocMode === "manual") {
    const sum = sumManualDollars(rowsSortedRank);
    if (!manualAllocValid(rowsSortedRank, startCash)) {
      if (inner) {
        inner.innerHTML =
          '<p class="calc-warnings">' +
          "Manual mode requires dollar allocations to sum to <strong>starting cash</strong> ($" +
          fmtMoney(startCash) +
          ", within $" +
          fmtMoney(MANUAL_SUM_TOL) +
          "). Current total: <strong>$" +
          fmtMoney(sum) +
          "</strong>. Adjust inputs or click <strong>Normalize to starting cash</strong>.</p>";
      }
      return;
    }
  }

  const allocMap = getActiveAllocMap(rowsSortedRank, rowsSortedMult);
  if (allocMap === null) return;

  const ending = portfolioEndingFromAlloc(allocMap, multMap);
  const portMult = ending / startCash;
  const portPct = ((ending - startCash) / startCash) * 100;
  const tm = computeTargetBlock(startCash, ending, targetCash);
  const winner = findBestMultipleRow(rowsSortedRank);
  const unconstrainedAlloc = allocUnconstrainedMax(rowsSortedRank, startCash);
  const endingUnconstrained = portfolioEndingFromAlloc(unconstrainedAlloc, multMap);

  let bestSingleHtml = "";
  if (winner && Number.isFinite(winner.mult)) {
    const a = startCash;
    const endS = a * winner.mult;
    bestSingleHtml =
      '<div class="best-single-block">' +
      "<h3 class=\"subhead optimizer-subhead\">Best single-stock result (full starting cash in one name)</h3>" +
      '<dl class="metric-row">' +
      "<dt>Ticker</dt><dd>" +
      escapeHtml(winner.ticker) +
      "</dd>" +
      "<dt>Allocation ($)</dt><dd>$" +
      fmtMoney(a) +
      "</dd>" +
      "<dt>Return multiple</dt><dd>" +
      fmtNum(winner.mult, 10) +
      "</dd>" +
      "<dt>Ending cash</dt><dd>$" +
      fmtMoney(endS) +
      "</dd>" +
      "</dl></div>";
  }

  let proofHtml = "";
  if (allocMode === "unconstrained_max" && winner && Number.isFinite(winner.mult)) {
    const endProof = startCash * winner.mult;
    proofHtml =
      '<aside class="proof-box" role="note">' +
      "<p><strong>Unconstrained maximum return (derived):</strong> Maximize <em>Σᵢ aᵢ·mᵢ</em> subject to <em>Σᵢ aᵢ = S</em>, aᵢ ≥ 0. " +
      "This is linear; an optimum lies at a vertex (all cash in one ticker with maximal <em>mᵢ</em> from imported closes). " +
      "Here <strong>" +
      escapeHtml(winner.ticker) +
      "</strong> has <em>m</em> = " +
      fmtNum(winner.mult, 10) +
      ", so ending = $" +
      fmtMoney(startCash) +
      " × " +
      fmtNum(winner.mult, 10) +
      " = <strong>$" +
      fmtMoney(endProof) +
      "</strong>.</p>" +
      "<p>Tie-break: lexicographically smallest ticker among ties.</p>" +
      "</aside>";
  }

  let modeDesc = "";
  if (allocMode === "unconstrained_max") {
    modeDesc =
      "<p class=\"active-mode-desc\"><strong>Active mode — Unconstrained maximum return:</strong> computed optimum (see proof).</p>";
  } else if (allocMode === "max_dollars") {
    modeDesc =
      "<p class=\"active-mode-desc\"><strong>Active mode — Maximum dollars per stock:</strong> greedy fill in rank order up to your cap per name.</p>";
  } else if (allocMode === "max_pct") {
    modeDesc =
      "<p class=\"active-mode-desc\"><strong>Active mode — Maximum percent per stock:</strong> greedy fill by return multiple with a weight cap.</p>";
  } else if (allocMode === "min_stocks") {
    modeDesc =
      "<p class=\"active-mode-desc\"><strong>Active mode — Minimum number of stocks:</strong> at least K names with positive dollars (floor + remainder on best multiple among top K).</p>";
  } else if (allocMode === "equal") {
    modeDesc =
      "<p class=\"active-mode-desc\"><strong>Active mode — Equal weight top N:</strong> equal dollars to top N by import rank.</p>";
  } else {
    modeDesc =
      "<p class=\"active-mode-desc\"><strong>Active mode — Manual allocation:</strong> dollars from the ranked table; must sum to starting cash.</p>";
  }

  const allocLines = Object.keys(allocMap)
    .filter((t) => allocMap[t] > 1e-8)
    .sort()
    .map((t) => escapeHtml(t) + ": $" + fmtMoney(allocMap[t]))
    .join("; ");

  const splitNote =
    allocMode !== "unconstrained_max" &&
    Object.keys(unconstrainedAlloc).length &&
    ending < endingUnconstrained - 1e-9 * Math.max(1, Math.abs(endingUnconstrained))
      ? '<p class="split-note">This mode’s ending is below the unconstrained maximum ($' +
        fmtMoney(endingUnconstrained) +
        ") — expected under caps, minimum holdings, equal split, or manual rules.</p>"
      : "";

  const maxDollarWarn =
    allocMode === "max_dollars" && diagnostics.maxDollarsRemainder > 0.01
      ? '<p class="calc-warnings">Could not deploy all starting cash with current max $/stock and rank order; remainder ≈ $' +
        fmtMoney(diagnostics.maxDollarsRemainder) +
        " (see ranked universe / caps).</p>"
      : "";

  const minStockWarn = allocMode === "min_stocks" && diagnostics.minStocksNote ? '<p class="calc-warnings">' + escapeHtml(diagnostics.minStocksNote) + "</p>" : "";

  if (!inner) return;

  inner.innerHTML =
    bestSingleHtml +
    "<h3 class=\"subhead optimizer-subhead\">Best split portfolio under selected mode</h3>" +
    modeDesc +
    proofHtml +
    maxDollarWarn +
    minStockWarn +
    "<p class=\"weight-breakdown\"><strong>Allocation ( dollars ):</strong> " +
    (allocLines || "—") +
    "</p>" +
    '<div class="command-center-grid">' +
    '<dl class="metric-card metric-hero"><dt>Portfolio ending cash</dt><dd>$' +
    fmtMoney(ending) +
    "</dd></dl>" +
    '<dl class="metric-card"><dt># Stocks used</dt><dd>' +
    countPositiveAlloc(allocMap) +
    "</dd></dl>" +
    '<dl class="metric-card"><dt>Portfolio return multiple</dt><dd>' +
    fmtNum(portMult, 10) +
    "</dd></dl>" +
    '<dl class="metric-card"><dt>Portfolio % return</dt><dd>' +
    fmtNum(portPct) +
    "</dd></dl>" +
    '<dl class="metric-card"><dt>Target achieved</dt><dd>' +
    (tm.achieved ? "Yes" : "No") +
    "</dd></dl>" +
    '<dl class="metric-card"><dt>Distance from target</dt><dd>$' +
    fmtMoney(tm.distanceFromTarget) +
    "</dd></dl>" +
    "</div>" +
    splitNote;
}

function renderTargetActive(startCash, endingCash, targetCash) {
  if (!Number.isFinite(endingCash)) return;
  const tm = computeTargetBlock(startCash, endingCash, targetCash);
  const trInner = $("targetRealityInner");
  if (trInner) {
    trInner.innerHTML =
      '<dl class="metric-card"><dt>Required multiple (target ÷ start)</dt><dd>' +
      fmtNum(tm.reqMult, 8) +
      "</dd></dl>" +
      '<dl class="metric-card"><dt>Achieved multiple (ending ÷ start)</dt><dd>' +
      fmtNum(tm.achMult, 8) +
      "</dd></dl>" +
      '<dl class="metric-card"><dt>Distance from target</dt><dd>$' +
      fmtMoney(tm.distanceFromTarget) +
      "</dd></dl>" +
      '<dl class="metric-card"><dt>Percent of target achieved</dt><dd>' +
      fmtNum(tm.percentOfTarget) +
      "%</dd></dl>";
  }
  const tsl = $("targetStatusLine");
  if (tsl) {
    tsl.innerHTML =
      "<strong class=\"" +
      (tm.achieved ? "status-ok" : "status-no") +
      "\">" +
      (tm.achieved ? "Target reached (active mode)" : "Target not reached (active mode)") +
      "</strong> — ending $" +
      fmtMoney(endingCash) +
      " vs target $" +
      fmtMoney(targetCash) +
      ".";
  }
}

function renderManualTotal(rowsSortedRank) {
  const { startCash } = getInputs();
  const sum = sumManualDollars(rowsSortedRank);
  const el = $("allocTotalDisplay");
  const warn = $("allocWarn");
  if (el) el.textContent = "Manual allocation total: $" + fmtMoney(sum) + " (starting cash: $" + fmtMoney(startCash) + ")";
  if (warn) {
    if (!manualAllocValid(rowsSortedRank, startCash) && sum > 0) {
      warn.hidden = false;
      warn.textContent = "Total must equal starting cash (within $" + fmtMoney(MANUAL_SUM_TOL) + ") for manual mode.";
    } else {
      warn.hidden = true;
      warn.textContent = "";
    }
  }
}

function renderGoalRealityBanner() {
  const sec = $("goalRealityBanner");
  if (!sec) return;
  if (!snapshotData) {
    sec.classList.add("panel-hidden");
    sec.innerHTML = "";
    return;
  }
  sec.classList.remove("panel-hidden");
  const { startCash, targetCash } = getInputs();
  const enriched = enrichRanked(snapshotData);
  const rowsSortedRank = sortByRankAsc(enriched);
  const winner = findBestMultipleRow(rowsSortedRank);
  const bestMult = winner && Number.isFinite(winner.mult) ? winner.mult : NaN;
  const bestEnd = Number.isFinite(bestMult) ? startCash * bestMult : NaN;
  const needMult = startCash > 0 ? targetCash / startCash : NaN;
  let compoundPara = "";
  if (
    Number.isFinite(bestMult) &&
    bestMult > 1.001 &&
    Number.isFinite(needMult) &&
    needMult > bestMult + 1e-12
  ) {
    const nSteps = Math.log(needMult) / Math.log(bestMult);
    compoundPara =
      "<p><strong>Compound illustration (not a forecast):</strong> If you could repeat this file’s best multiple (" +
      fmtNum(bestMult, 4) +
      "×) every identical two-day period with no losses, reaching a <strong>" +
      fmtNum(needMult, 4) +
      "×</strong> goal would take on the order of <strong>" +
      fmtNum(nSteps, 1) +
      "</strong> such periods — not one trade, and not achievable as a guarantee in real markets.</p>";
  }
  sec.innerHTML =
    '<div class="goal-reality-inner">' +
    '<span class="goal-tag">Goal vs one-step maximum</span>' +
    "<p><strong>Best stock / allocation in this imported list:</strong> For this entry→exit window, the highest return multiple is <strong>" +
    escapeHtml(winner ? winner.ticker : "—") +
    "</strong> at about <strong>" +
    fmtNum(bestMult, 4) +
    "×</strong>, so the best long-only ending cash from <strong>$" +
    fmtMoney(startCash) +
    "</strong> is about <strong>$" +
    fmtMoney(bestEnd) +
    "</strong> (put 100% in that name — “Unconstrained maximum return”). No other symbol in <code>ranked_results</code> has a higher multiple here; mixing names only lowers the weighted return toward smaller multiples.</p>" +
    "<p><strong>About turning $100 into $1,000,000:</strong> That requires a <strong>10,000×</strong> portfolio gain. No realistic two-day <em>daily close</em> move among liquid equities is on that scale. This dashboard cannot “pick different stocks” inside the same JSON to invent a 10,000× — the file’s best is the cap. To pursue large wealth growth you need <strong>many periods</strong>, different instruments, or different risk (see scope banner: multi-day paths are not implemented here).</p>" +
    "<p><strong>Your current target</strong> ($" +
    fmtMoney(targetCash) +
    ") implies <strong>" +
    fmtNum(needMult, 4) +
    "×</strong> on starting cash. Compare to this file’s best <strong>" +
    fmtNum(bestMult, 4) +
    "×</strong>.</p>" +
    compoundPara +
    "</div>";
}

function renderHeaderAndMeta() {
  const chips = $("commandHeaderChips");
  const meta = $("commandHeaderMeta");
  if (!snapshotData) {
    if (chips) {
      chips.innerHTML =
        '<span class="chip chip-muted">Data: not loaded</span>' +
        '<span class="chip chip-muted">Entry: —</span>' +
        '<span class="chip chip-muted">Exit: —</span>' +
        '<span class="chip chip-muted">Fetch: —</span>';
    }
    if (meta) meta.innerHTML = "";
    return;
  }
  const d = snapshotData;
  const ft = d.fetch_timestamp || "—";
  if (chips) {
    chips.innerHTML =
      '<span class="chip chip-ok">Data: loaded</span>' +
      '<span class="chip">' +
      escapeHtml("Entry day: " + (d.entry_day || "—")) +
      "</span>" +
      '<span class="chip">' +
      escapeHtml("Exit day: " + (d.exit_day || "—")) +
      "</span>" +
      '<span class="chip">' +
      escapeHtml("Fetch: " + String(ft).slice(0, 19)) +
      "</span>";
  }
  if (meta) {
    meta.innerHTML =
      '<span class="header-meta-line">' +
      escapeHtml(d.scan_mode || "") +
      " · Two-Day Hindsight Scan</span>";
  }
  const u = $("universeSummary");
  if (u) u.textContent = d.universe_description || "—";
}

function renderImportExpectations() {
  const el = $("importExpectations");
  if (!el) return;
  const { startCash, targetCash } = getInputs();
  if (!snapshotData) {
    el.innerHTML =
      "<strong>Why results look “stuck” until you load data:</strong> " +
      "The optimizer only runs after <code>ranked_results</code> is loaded. " +
      "Choose the JSON file, or open with <code>?demo=1</code> on a local server. " +
      "<strong>About a $1,000,000 target from $100:</strong> that needs a <strong>10,000×</strong> portfolio return. " +
      "A typical two-day long-only file delivers a best multiple near <strong>1–2×</strong>, so you will <em>not</em> see ending cash at a million — that is a limitation of the data, not a bug.";
    return;
  }
  const enriched = enrichRanked(snapshotData);
  const rowsSortedRank = sortByRankAsc(enriched);
  const winner = findBestMultipleRow(rowsSortedRank);
  const bestMult = winner && Number.isFinite(winner.mult) ? winner.mult : NaN;
  const bestEnd = Number.isFinite(bestMult) ? startCash * bestMult : NaN;
  const needMult = startCash > 0 ? targetCash / startCash : NaN;
  el.innerHTML =
    "<strong>Loaded data — what’s possible in one two-day step:</strong> " +
    "Best return multiple in this file is <strong>≈ " +
    fmtNum(bestMult, 4) +
    "×</strong>, so the best long-only ending from <strong>$" +
    fmtMoney(startCash) +
    "</strong> is about <strong>$" +
    fmtMoney(bestEnd) +
    "</strong>. " +
    "Your target <strong>$" +
    fmtMoney(targetCash) +
    "</strong> would need <strong>" +
    fmtNum(needMult, 4) +
    "×</strong>. " +
    (Number.isFinite(needMult) && Number.isFinite(bestMult) && needMult > bestMult + 1e-9
      ? "This file cannot reach that target; see <strong>Target failure analysis</strong> below."
      : "Adjust targets to compare outcomes.");
}

function renderMissionObjective(startCash) {
  const el = $("missionObjectiveText");
  if (!el) return;
  if (!snapshotData) {
    el.innerHTML =
      "Load <code>ranked_results</code> from the snapshot, then answer: <em>If I had <strong>$" +
      fmtMoney(startCash) +
      "</strong> and already knew the outcome, how should I split that across all scanned stocks to make the most money or get closest to the target?</em> Use the Portfolio Allocation Optimizer.";
    return;
  }
  el.innerHTML =
    "<em>If I had <strong>$" +
    fmtMoney(startCash) +
    "</strong> and already knew the outcome, how should I split that across all scanned stocks to maximize ending cash or approach the target?</em> All math uses recomputed multiples from imported entry/exit closes only.";
}

function renderGovernance() {
  const el = $("governanceInner");
  if (!el) return;
  el.innerHTML =
    "<p><strong>Task identifier:</strong> " +
    escapeHtml(TASK_ID) +
    "</p>" +
    "<p><strong>Expected evidence artifacts:</strong></p>" +
    "<ul>" +
    "<li><code>agent_workspace/evidence/" +
    TASK_ID +
    "/test_results.txt</code></li>" +
    "<li><code>agent_workspace/evidence/" +
    TASK_ID +
    "/lint_results.txt</code></li>" +
    "<li><code>agent_workspace/evidence/" +
    TASK_ID +
    "/ui_proof.png</code></li>" +
    "</ul>" +
    "<p><strong>Visual proof status:</strong> A real screenshot is required before this dashboard task can pass the judge gate.</p>";
}

function renderIntegrity() {
  const pre = $("integrityBody");
  if (!pre) return;
  const out = {
    file_loaded: diagnostics.fileLoaded,
    required_fields_present: diagnostics.requiredFieldsPresent,
    best_result_present: diagnostics.bestResultPresent,
    ranked_result_count: diagnostics.rankedResultCount,
    recomputed_top_ticker: diagnostics.recomputedTopTicker,
    import_best_ticker: diagnostics.importBestTicker,
    recomputed_top_matches_import_best: diagnostics.recomputedTopMatchesImport,
    calculation_mismatch_warnings: diagnostics.mismatchWarnings,
    parse_errors: diagnostics.parseError,
    source_path: diagnostics.sourcePath,
    calculation_state: diagnostics.calculation,
    last_error: diagnostics.lastError,
  };
  pre.textContent = JSON.stringify(out, null, 2);
}

function caveatsHtml(arr) {
  if (!Array.isArray(arr) || !arr.length) return "—";
  return (
    "<ul class=\"caveats-list\">" +
    arr.map((x) => "<li>" + escapeHtml(String(x)) + "</li>").join("") +
    "</ul>"
  );
}

function orderRankedRowsForDisplay(allRows) {
  const sort = ($("rankedSort") && $("rankedSort").value) || "rank";
  const { startCash } = getInputs();
  const list = [...allRows];
  const m = (r) => r.mult;
  if (sort === "pct_desc") {
    list.sort((a, b) => (m(b) || 0) - (m(a) || 0));
  } else if (sort === "cash_desc") {
    list.sort((a, b) => startCash * (m(b) || 0) - startCash * (m(a) || 0));
  } else if (sort === "ticker") {
    list.sort((a, b) => String(a.ticker).localeCompare(String(b.ticker)));
  } else {
    list.sort((a, b) => (a.rank || 0) - (b.rank || 0));
  }
  return list;
}

function rowMatchesSearch(r, q) {
  if (!q) return true;
  const blob = (r.ticker || "") + " " + (r.name || "") + " " + (r.exchange || "");
  return blob.toLowerCase().indexOf(q) !== -1;
}

function renderRankedTable() {
  const tbody = $("rankedBody");
  if (!tbody || !snapshotData) return;
  tbody.innerHTML = "";
  const enriched = enrichRanked(snapshotData);
  const ordered = orderRankedRowsForDisplay(enriched);
  const q = (($("rankedSearch") && $("rankedSearch").value) || "").trim().toLowerCase();
  const { startCash } = getInputs();
  const mode = ($("allocMode") && $("allocMode").value) || "unconstrained_max";
  const brTicker = snapshotData.best_result.ticker;
  const topWin = findBestMultipleRow(enriched);

  ordered.forEach((r) => {
    const mult = r.mult;
    const pct = computePercentFromCloses(r.entry_close, r.exit_close);
    const endFull = Number.isFinite(mult) ? startCash * mult : NaN;
    const tr = document.createElement("tr");
    tr.dataset.ticker = r.ticker;
    if (!rowMatchesSearch(r, q)) tr.classList.add("row-filter-hide");
    if (r.ticker === brTicker) tr.classList.add("row-import-best");
    if (topWin && r.ticker === topWin.ticker) tr.classList.add("row-recomputed-top");
    const manualVal =
      manualDollarsByTicker[r.ticker] != null ? manualDollarsByTicker[r.ticker] : "";
    const mph = escapeHtml(r.ticker);
    const disabled = mode !== "manual" ? " disabled" : "";
    tr.innerHTML =
      "<td>" +
      escapeHtml(String(r.rank)) +
      "</td><td>" +
      escapeHtml(r.ticker) +
      "</td><td>" +
      escapeHtml(r.name || "—") +
      "</td><td>" +
      escapeHtml(r.exchange || "—") +
      "</td><td>" +
      fmtNum(r.entry_close) +
      "</td><td>" +
      fmtNum(r.exit_close) +
      "</td><td>" +
      fmtNum(pct) +
      "</td><td>" +
      fmtNum(mult, 8) +
      "</td><td>$" +
      (Number.isFinite(endFull) ? fmtMoney(endFull) : "—") +
      '</td><td><input type="number" class="manual-dollar-input" min="0" step="0.01" data-ticker="' +
      mph +
      "\" value=\"" +
      (manualVal === "" || manualVal === 0 ? "" : manualVal) +
      '"' +
      disabled +
      "/></td><td>" +
      escapeHtml(r.source_name || "—") +
      "</td><td>" +
      caveatsHtml(r.caveats) +
      "</td>";
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll(".manual-dollar-input").forEach((inp) => {
    inp.addEventListener("input", () => {
      const t = inp.getAttribute("data-ticker");
      manualDollarsByTicker[t] = Number(inp.value) || 0;
      renderManualTotal(sortByRankAsc(enrichRanked(snapshotData)));
    });
  });
}

function renderSourceAudit() {
  const el = $("sourceAuditInner");
  if (!el || !snapshotData) return;
  const br = snapshotData.best_result;
  const skipped =
    snapshotData.skipped_tickers || snapshotData.skipped || snapshotData.skipped_symbols;
  let skippedBlock = "";
  if (Array.isArray(skipped) && skipped.length) {
    skippedBlock =
      "<h3>Skipped tickers</h3><ul>" +
      skipped.map((x) => "<li>" + escapeHtml(String(x)) + "</li>").join("") +
      "</ul>";
  } else {
    skippedBlock = "<h3>Skipped tickers</h3><p>None listed in this file.</p>";
  }
  const lim = (snapshotData.limitations || []).map((x) => "<li>" + escapeHtml(x) + "</li>").join("");
  const sourcesSet = new Map();
  (snapshotData.ranked_results || []).forEach((r) => {
    if (r.source_name) sourcesSet.set(r.source_name, r.source_link || "");
  });
  let srcList = "";
  sourcesSet.forEach((link, name) => {
    srcList +=
      "<li>" +
      escapeHtml(name) +
      (link
        ? ' — <a href="' +
          escapeHtml(link) +
          '" target="_blank" rel="noopener">' +
          escapeHtml(link) +
          "</a>"
        : "") +
      "</li>";
  });
  el.innerHTML =
    "<div><h3>Best result source</h3><p>" +
    escapeHtml(br.source_name || "—") +
    '</p><p><a href="' +
    escapeHtml(br.source_link || "#") +
    '" target="_blank" rel="noopener">' +
    escapeHtml(br.source_link || "") +
    "</a></p>" +
    "<h3>Sources (ranked rows)</h3><ul>" +
    (srcList || "<li>—</li>") +
    "</ul></div>" +
    "<div><h3>Fetch timestamp</h3><p>" +
    escapeHtml(String(snapshotData.fetch_timestamp || "—")) +
    "</p>" +
    "<h3>Universe description</h3><p>" +
    escapeHtml(snapshotData.universe_description || "—") +
    "</p>" +
    "<h3>Limitations</h3><ul>" +
    (lim || "<li>—</li>") +
    "</ul>" +
    "<h3>Best-result caveats</h3><ul>" +
    (br.caveats || []).map((x) => "<li>" + escapeHtml(x) + "</li>").join("") +
    "</ul>" +
    skippedBlock +
    "</div>";
}

function renderPanels() {
  if (!snapshotData) {
    const gb = $("goalRealityBanner");
    if (gb) {
      gb.classList.add("panel-hidden");
      gb.innerHTML = "";
    }
    [
      "comparisonSection",
      "targetAnyModeSection",
      "targetFailureSection",
      "searchHarderSection",
      "bestCommandSection",
      "allocationDetailSection",
      "targetRealitySection",
      "rankedSection",
      "sourceAuditSection",
    ].forEach((id) => {
      const p = $(id);
      if (p) p.classList.add("panel-hidden");
    });
    diagnostics.calculation = "idle";
    return;
  }

  const enriched = enrichRanked(snapshotData);
  const rowsSortedRank = sortByRankAsc(enriched);
  const rowsSortedMult = sortByMultDesc(enriched);
  const multMap = buildMultMap(enriched);
  const rowByTicker = rowMapByTicker(enriched);
  const br = snapshotData.best_result;

  diagnostics.mismatchWarnings = auditMismatchForBest(br).concat(verifyTopStock(enriched, br));

  const warningsEl = $("calcWarnings");
  if (warningsEl) {
    if (diagnostics.mismatchWarnings.length) {
      warningsEl.hidden = false;
      warningsEl.innerHTML =
        "<strong>Validation / mismatch:</strong><ul>" +
        diagnostics.mismatchWarnings.map((w) => "<li>" + escapeHtml(w) + "</li>").join("") +
        "</ul>";
    } else {
      warningsEl.hidden = true;
      warningsEl.innerHTML = "";
    }
  }

  $("comparisonSection").classList.remove("panel-hidden");
  renderComparisonTable(rowsSortedRank, rowsSortedMult, multMap);

  $("targetAnyModeSection").classList.remove("panel-hidden");
  renderTargetAnyModeBanner(rowsSortedRank, rowsSortedMult, multMap);

  renderTargetFailureAnalysis(rowsSortedRank, rowsSortedMult, multMap);

  const { startCash, targetCash, allocMode } = getInputs();
  const allocMap = getActiveAllocMap(rowsSortedRank, rowsSortedMult);
  let endingActive = allocMap ? portfolioEndingFromAlloc(allocMap, multMap) : NaN;
  if (allocMode === "manual" && allocMap === null) {
    endingActive = NaN;
  }

  $("bestCommandSection").classList.remove("panel-hidden");
  renderBestActive(rowsSortedRank, rowsSortedMult, multMap, rowByTicker);

  renderAllocationDetailPanel(allocMap || {}, rowByTicker, startCash, multMap, targetCash, endingActive);

  $("targetRealitySection").classList.remove("panel-hidden");
  if (allocMode === "manual" && Number.isNaN(endingActive)) {
    $("targetRealityInner").innerHTML =
      "<p class=\"calc-warnings\">Target metrics unavailable until manual dollars sum to starting cash.</p>";
    $("targetStatusLine").textContent = "";
  } else {
    renderTargetActive(startCash, endingActive, targetCash);
  }

  $("rankedSection").classList.remove("panel-hidden");
  renderRankedTable();
  renderManualTotal(rowsSortedRank);

  $("sourceAuditSection").classList.remove("panel-hidden");
  renderSourceAudit();

  renderAllocControlVisibility();

  diagnostics.calculation = "ok_portfolio_optimizer";
}

function renderAll() {
  renderHeaderAndMeta();
  renderGoalRealityBanner();
  renderGovernance();

  const loadEl = $("loadStatus");
  if (loadEl) {
    if (diagnostics.fileLoaded) {
      loadEl.innerHTML =
        "<strong>File:</strong> loaded (" + escapeHtml(diagnostics.sourcePath || "") + ")";
    } else {
      let extra = "";
      try {
        const sp = new URLSearchParams(typeof location !== "undefined" ? location.search : "");
        if (sp.get("demo") === "1") {
          if (diagnostics.demoLoadPending) {
            extra =
              ' <span class="load-pending">Loading demo snapshot from <code>/reports/live_market_snapshot.json</code>…</span>';
          } else if (diagnostics.demoLoadFailed) {
            extra =
              '<p class="load-err">Demo could not load: ' +
              escapeHtml(diagnostics.demoLoadError || "unknown") +
              ". Serve the site from the <strong>project root</strong> (e.g. <code>python -m http.server 8000</code>) so that URL is reachable, or use the file picker.</p>";
          }
        }
      } catch (e) {
        extra = "";
      }
      if (!diagnostics.demoLoadPending && !diagnostics.demoLoadFailed) {
        extra +=
          ' <span class="load-hint">Use the file picker, or add <code>?demo=1</code> to the address bar when using a local server. Until a file loads, target and starting cash only update the text above — no allocation math runs.</span>';
      }
      loadEl.innerHTML = "<strong>File:</strong> not loaded." + extra;
    }
  }

  renderImportExpectations();

  const { startCash } = getInputs();
  renderMissionObjective(startCash);

  if (!snapshotData) {
    diagnostics.calculation = "idle";
    renderIntegrity();
    return;
  }

  renderPanels();
  renderIntegrity();
}

function normalizeManualAlloc() {
  if (!snapshotData) return;
  const enriched = enrichRanked(snapshotData);
  const rowsSortedRank = sortByRankAsc(enriched);
  const { startCash } = getInputs();
  let sum = sumManualDollars(rowsSortedRank);
  if (sum <= 1e-12) return;
  rowsSortedRank.forEach((r) => {
    const v = Math.max(0, Number(manualDollarsByTicker[r.ticker]) || 0);
    manualDollarsByTicker[r.ticker] = (v / sum) * startCash;
  });
  renderAll();
}

function resetDashboard() {
  snapshotData = null;
  manualDollarsByTicker = {};
  diagnostics.fileLoaded = false;
  diagnostics.requiredFieldsPresent = false;
  diagnostics.bestResultPresent = false;
  diagnostics.rankedResultCount = 0;
  diagnostics.calculation = "idle";
  diagnostics.missingFields = [];
  diagnostics.lastError = null;
  diagnostics.sourcePath = null;
  diagnostics.mismatchWarnings = [];
  diagnostics.parseError = null;
  diagnostics.recomputedTopTicker = null;
  diagnostics.importBestTicker = null;
  diagnostics.recomputedTopMatchesImport = null;
  diagnostics.maxDollarsRemainder = 0;
  diagnostics.minStocksNote = null;
  diagnostics.demoLoadPending = false;
  diagnostics.demoLoadFailed = false;
  diagnostics.demoLoadError = null;
  const fi = $("fileInput");
  if (fi) fi.value = "";
  const sc = $("startCash");
  const tc = $("targetCash");
  if (sc) sc.value = "100";
  if (tc) tc.value = "1000000";
  const rs = $("rankedSearch");
  if (rs) rs.value = "";
  const rk = $("rankedSort");
  if (rk) rk.value = "rank";
  if ($("allocMode")) $("allocMode").value = "unconstrained_max";
  if ($("allocTopN")) $("allocTopN").value = "5";
  if ($("allocMaxPct")) $("allocMaxPct").value = "25";
  if ($("allocMaxDollars")) $("allocMaxDollars").value = "20";
  if ($("allocMinStocks")) $("allocMinStocks").value = "5";
  renderAll();
}

function wireEvents() {
  function onCashOrAllocInput() {
    renderAll();
  }
  ["startCash", "targetCash", "allocTopN", "allocMaxPct", "allocMaxDollars", "allocMinStocks"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("input", onCashOrAllocInput);
    el.addEventListener("change", onCashOrAllocInput);
  });

  const allocModeEl = $("allocMode");
  if (allocModeEl) {
    allocModeEl.addEventListener("change", () => {
      renderAll();
    });
  }

  $("btnNormalize").addEventListener("click", () => normalizeManualAlloc());

  $("btnRun").addEventListener("click", () => renderAll());

  $("btnReset").addEventListener("click", () => resetDashboard());

  $("btnTarget1M").addEventListener("click", () => {
    $("targetCash").value = "1000000";
    renderAll();
  });

  $("btnTarget100M").addEventListener("click", () => {
    $("targetCash").value = "100000000";
    renderAll();
  });

  $("rankedSearch").addEventListener("input", () => {
    if (snapshotData) renderRankedTable();
  });
  $("rankedSort").addEventListener("change", () => {
    if (snapshotData) renderRankedTable();
  });

  $("fileInput").addEventListener("change", (ev) => {
    const f = ev.target.files && ev.target.files[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        parseSnapshot(String(r.result), f.name);
        renderAll();
      } catch (e) {
        alert(e.message);
        diagnostics.lastError = String(e);
        diagnostics.parseError = String(e.message || e);
        renderAll();
      }
    };
    r.readAsText(f);
  });
}

function boot() {
  try {
    wireEvents();
    tryDemoQueryLoad();
    renderAll();
  } catch (err) {
    diagnostics.lastError = String(err && err.stack ? err.stack : err);
    const pre = $("integrityBody");
    if (pre) pre.textContent = "BOOT ERROR\n" + diagnostics.lastError;
  }
}

function tryDemoQueryLoad() {
  try {
    var sp = new URLSearchParams(location.search);
    if (sp.get("demo") !== "1") return;
    diagnostics.demoLoadFailed = false;
    diagnostics.demoLoadError = null;
    diagnostics.demoLoadPending = true;
    fetch("/reports/live_market_snapshot.json", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.text();
      })
      .then(function (t) {
        diagnostics.demoLoadPending = false;
        parseSnapshot(t, "/reports/live_market_snapshot.json (?demo=1)");
        renderAll();
      })
      .catch(function (err) {
        diagnostics.demoLoadPending = false;
        diagnostics.demoLoadFailed = true;
        diagnostics.demoLoadError = String(err && err.message ? err.message : err);
        renderAll();
      });
  } catch (e) {
    diagnostics.lastError = String(e);
    diagnostics.demoLoadPending = false;
    diagnostics.demoLoadFailed = true;
    diagnostics.demoLoadError = String(e && e.message ? e.message : e);
    renderAll();
  }
}

boot();
