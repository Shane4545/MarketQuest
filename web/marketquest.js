function byId(id) {
  return document.getElementById(id);
}

function esc(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtUsd(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return "$" + Number(n).toFixed(2);
}

function fmtPct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return sign + v.toFixed(2) + "%";
}

let countdownTimer = null;
let lastDashboard = null;

function querySuffix() {
  const params = new URLSearchParams(window.location.search);
  const parts = [];
  if (params.get("training") === "1" || params.get("mock") === "1") parts.push("training=1");
  return parts.length ? "?" + parts.join("&") : "";
}

async function fetchJson(url, options) {
  const res = await fetch(url, { cache: "no-store", ...options });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload.error || res.statusText || "HTTP " + res.status);
  return payload;
}

function agentLabel(id) {
  const map = {
    momentum: "Momentum Agent",
    news: "News Agent",
    news_only: "News-Only Agent",
    news_sentiment: "News Agent",
    filing_event: "Filing Agent",
    macro: "Macro Agent",
    macro_event: "Macro Agent",
    ensemble: "Ensemble Agent",
    human_baseline: "Human Baseline",
    random_baseline: "Random Baseline",
    spy_baseline: "SPY Baseline",
    qqq_baseline: "QQQ Baseline",
    equal_weight_baseline: "Equal-Weight Watchlist",
    momentum_baseline: "Simple Momentum Baseline",
    public_figure: "Public Figure Agent",
    entity_graph: "Entity Graph Agent",
    skeptic: "Skeptic Agent",
    fx_agent: "FX Agent",
    cross_asset_agent: "Cross-Asset Agent",
    regime_agent: "Regime Agent",
    divergence_agent: "Divergence Agent",
    correlation_skeptic: "Correlation Skeptic",
    default: "You (Human Player)",
  };
  return map[id] || id;
}

function renderProvenance(elId, data) {
  const el = byId(elId);
  if (!el) return;
  const ps = data.provider_status || {};
  const keys = Object.keys(ps);
  if (!keys.length && !data.timestamp_utc) {
    el.innerHTML = "";
    return;
  }
  let html = `<small>Snapshot: ${esc(data.timestamp_utc)} · age ${esc(data.snapshot_age_minutes)} min · session ${esc(data.market_session || data.market_status)}</small><br>`;
  keys.forEach((k) => {
    const p = ps[k];
    html += `<span class="badge ${esc((p.status || "OFFLINE").toLowerCase())}">${esc(k)}: ${esc(p.status)}</span> `;
  });
  const fresh = data.freshness || {};
  if (fresh.label) html += `<br><small>Freshness: ${esc(fresh.label)}</small>`;
  if (data.scoring_data_eligible === false) {
    html += `<p class="mq-warn">${esc(data.stale_warning || "Data stale — not used for current competition scoring.")}</p>`;
  }
  el.innerHTML = html;
}

function startCountdown(seconds) {
  if (countdownTimer) clearInterval(countdownTimer);
  const el = byId("refresh-countdown");
  if (!el) return;
  let left = Number(seconds) || 0;
  function tick() {
    if (left <= 0) {
      el.textContent = "Next refresh due";
      return;
    }
    const m = Math.floor(left / 60);
    const s = left % 60;
    el.textContent = `Next refresh in ${m}:${String(s).padStart(2, "0")}`;
    left -= 1;
  }
  tick();
  countdownTimer = setInterval(tick, 1000);
}

function renderBanner(data) {
  const el = byId("status-banner");
  const offline = data.offline_training_mode;
  const fresh = data.scoring_data_eligible ? "live" : "stale";
  el.className = "mq-banner " + (offline ? "mock" : fresh);
  if (byId("tagline")) byId("tagline").textContent = data.tagline || byId("tagline").textContent;

  let html = "";
  if (offline) {
    html += `<span class="badge mock">OFFLINE TRAINING MODE</span> `;
  } else {
    html += `<span class="badge ${esc(fresh)}">${esc((data.market_session || data.market_status || "unknown").toUpperCase())}</span> `;
  }
  html +=
    `Snapshot ${esc(data.timestamp_utc)} · age ${esc(data.snapshot_age_minutes)} min · ` +
    `MarketQuest Reality Radar v${esc(data.version || "2.0")}`;
  if (data.stale_warning) html += `<br><span class="mq-warn">${esc(data.stale_warning)}</span>`;
  if (data.ai_disclosure) html += `<br><span class="mq-warn">${esc(data.ai_disclosure)}</span>`;
  (data.benchmark_disclosures || []).slice(0, 3).forEach((d) => {
    html += `<br><small class="mq-disclosure">${esc(d)}</small>`;
  });
  el.innerHTML = html;
  renderProvenance("provenance-status", data);
  startCountdown(data.next_refresh_seconds);
}

function renderRegime(regime) {
  const el = byId("regime-card");
  if (!el) return;
  regime = regime || {};
  if (!regime.regime) {
    el.innerHTML = "<p>Regime data loading…</p>";
    return;
  }
  const evidence = (regime.evidence || [])
    .map((e) => `<li>${esc(e)}</li>`)
    .join("");
  const groups = (regime.likely_sensitive_groups || [])
    .map((g) => `<span class="badge delayed">${esc(g)}</span>`)
    .join(" ");
  el.innerHTML =
    `<div class="mq-regime-card">` +
    `<strong class="mq-regime-label">${esc(String(regime.regime).replace(/_/g, " "))}</strong> ` +
    `<span class="badge live">confidence ${esc((Number(regime.confidence) * 100).toFixed(0))}%</span>` +
    `<ul>${evidence || "<li>Mixed signals</li>"}</ul>` +
    `<p><small>Sensitive groups: ${groups || "—"}</small></p></div>`;
}

function renderCurrencyRadar(currencies, cross) {
  const el = byId("currency-radar");
  if (!el) return;
  const forex = currencies || (cross || {}).forex || [];
  if (!forex.length) {
    el.innerHTML = "<p>FX offline — check Finnhub key or yfinance fallback.</p>";
    return;
  }
  el.innerHTML =
    `<table class="mq-table"><thead><tr><th>Pair</th><th>Last</th><th>1d %</th><th>Provider</th><th>Status</th></tr></thead><tbody>` +
    forex
      .map((f) => {
        const chg = f.change_pct_1d != null ? f.change_pct_1d : f.change_pct;
        const err = (f.errors || []).length ? `<br><small class="mq-warn">${esc(f.errors[0])}</small>` : "";
        return (
          `<tr><td>${esc(f.pair)}</td><td>${esc(f.last != null ? f.last : "—")}</td>` +
          `<td>${fmtPct(chg)}</td><td>${esc(f.provider || "—")}</td>` +
          `<td><span class="badge ${esc((f.status || f.freshness || "OFFLINE").toLowerCase())}">${esc(f.status || f.freshness || "OFFLINE")}</span>${err}</td></tr>`
        );
      })
      .join("") +
    `</tbody></table>`;
}

function renderCrossAssetMatrix(cross) {
  const el = byId("cross-asset-matrix");
  if (!el) return;
  const matrix = (cross || {}).matrix || [];
  if (!matrix.length) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML =
    `<h3>Cross-Asset Matrix</h3>` +
    `<table class="mq-table"><thead><tr><th>Symbol</th><th>1d %</th><th>FX Link</th><th>Regime</th><th>Note</th></tr></thead><tbody>` +
    matrix
      .slice(0, 10)
      .map((r) => {
        const fx = r.strongest_currency_correlation || {};
        return (
          `<tr><td>${esc(r.symbol)}</td><td>${fmtPct(r.change_pct_1d)}</td>` +
          `<td>${esc(fx.related_asset || "—")} (${esc(fx.direction || "n/a")})</td>` +
          `<td>${esc(r.regime_alignment || "—")}</td>` +
          `<td><small>${esc(r.skeptic_warning || "")}</small></td></tr>`
        );
      })
      .join("") +
    `</tbody></table>`;
}

function renderCrossAsset(cross) {
  const el = byId("cross-asset-strip");
  if (!el) return;
  cross = cross || {};
  const forex = cross.forex || [];
  const macro = cross.macro || [];
  const oil = cross.oil || {};
  const items = [];
  forex.forEach((f) => {
    items.push(
      `<div class="mq-cross-item" title="${esc(f.why_it_matters || "")}">` +
        `<strong>${esc(f.pair)}</strong> ${esc(f.last)} ` +
        `<span class="badge ${esc((f.freshness || "OFFLINE").toLowerCase())}">${esc(f.freshness || "OFFLINE")}</span>` +
      `</div>`
    );
  });
  const oilVal = oil.value != null ? oil.value : (oil.last != null ? oil.last : null);
  if (oilVal != null) {
    items.push(`<div class="mq-cross-item"><strong>WTI Oil</strong> $${esc(oilVal)} <span class="badge delayed">DELAYED</span></div>`);
  }
  macro.filter((m) => ["FEDFUNDS", "DGS10"].includes(m.series_id)).forEach((m) => {
    items.push(`<div class="mq-cross-item"><strong>${esc(m.name)}</strong> ${esc(m.value)}%</div>`);
  });
  el.innerHTML = items.length ? items.join("") : "<p>Cross-asset data offline — check FRED/Finnhub keys.</p>";
  renderCrossAssetMatrix(cross);
}

function renderBenchmarkScoreboard(lb, disclosures) {
  const el = byId("benchmark-scoreboard");
  if (!el) return;
  const comparisons = lb.benchmark_comparisons || {};
  const keys = Object.keys(comparisons);
  if (!keys.length) {
    el.innerHTML = "<p>Benchmark comparisons appear after agents run on live data.</p>";
    return;
  }
  let html = "<ul class=" + '"mq-benchmark-list"' + ">";
  keys.forEach((k) => {
    const c = comparisons[k];
    html += `<li><strong>${esc(c.winner)}</strong> won vs ${esc(c.a_id === c.winner ? c.b_id : c.a_id)} ` +
      `(Δ ${esc(c.delta_pct)}%, ${esc(c.period)})</li>`;
  });
  html += "</ul>";
  (disclosures || []).forEach((d) => {
    html += `<p class="mq-disclosure">${esc(d)}</p>`;
  });
  el.innerHTML = html;
}

function renderChallenge(ch) {
  const el = byId("challenge-content");
  if (!el || !ch) return;
  el.innerHTML =
    `<div class="mq-challenge-card">` +
    `<h3>${esc(ch.title || "Today's Challenge")}</h3>` +
    `<p>${esc(ch.prompt || "")}</p>` +
    `<p><small>${esc(ch.hint || "")}</small></p>` +
    `<textarea id="challenge-answer" rows="3" placeholder="Your reasoning…"></textarea>` +
    `<button type="button" id="btn-challenge-submit">Submit Answer</button>` +
    `<p id="challenge-msg" class="mq-msg"></p></div>`;
  byId("btn-challenge-submit").addEventListener("click", submitChallenge);
}

async function submitChallenge() {
  const msg = byId("challenge-msg");
  if (!lastDashboard || !lastDashboard.active_challenge) return;
  const ch = lastDashboard.active_challenge;
  try {
    const result = await fetchJson("/api/marketquest/challenges/submit" + querySuffix(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        challenge_id: ch.challenge_id,
        answer: byId("challenge-answer").value,
        player_id: "default",
      }),
    });
    msg.textContent = `+${result.learning?.learning_points || 0} learning points (total: ${result.total_learning_points || 0})`;
    msg.className = "mq-msg ok";
  } catch (e) {
    msg.textContent = e.message;
    msg.className = "mq-msg err";
  }
}

function renderCareers(careersData) {
  const el = byId("career-content");
  if (!el) return;
  const careers = (careersData || {}).careers || [];
  el.innerHTML = careers
    .map(
      (c) =>
        `<details class="mq-career-card"><summary><strong>${esc(c.title)}</strong></summary>` +
        `<p>${esc(c.description)}</p>` +
        `<p><strong>Skills:</strong> ${esc((c.skills || []).join(", "))}</p>` +
        `<p><strong>MarketQuest teaches:</strong> ${esc(c.marketquest_teaches)}</p>` +
        `<p><strong>Beginner project:</strong> ${esc(c.beginner_project)}</p>` +
        `<p><strong>School subjects:</strong> ${esc((c.school_subjects || []).join(", "))}</p></details>`
    )
    .join("");
  if (careersData.footer_note) {
    el.innerHTML += `<p class="mq-hint">${esc(careersData.footer_note)}</p>`;
  }
}

function renderScout(research) {
  const el = byId("scout-content");
  if (!el) return;
  const entries = (research || {}).entries || [];
  if (!entries.length) {
    el.innerHTML = "<p>Research registry loading…</p>";
    return;
  }
  el.innerHTML =
    `<table class="mq-table"><thead><tr><th>Name</th><th>Category</th><th>Free</th><th>Status</th><th>Ideas to borrow</th></tr></thead><tbody>` +
    entries
      .slice(0, 15)
      .map(
        (e) =>
          `<tr><td><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.name)}</a></td>` +
          `<td>${esc(e.category)}</td><td>${e.free ? "Yes" : "No"}</td>` +
          `<td>${esc(e.integration_status)}</td>` +
          `<td><small>${esc((e.ideas_to_borrow || []).slice(0, 2).join("; "))}</small></td></tr>`
      )
      .join("") +
    `</tbody></table>`;
}

function renderEventRadar(events) {
  const el = byId("event-radar");
  if (!el) return;
  const list = events || [];
  if (!list.length) {
    el.innerHTML = "<p>No events in snapshot — try Refresh or check provider status.</p>";
    return;
  }
  el.innerHTML = list
    .slice(0, 12)
    .map((ev) => {
      const tickers = (ev.candidate_tickers || ev.symbols || []).join(", ") || "—";
      const ents = (ev.entities || []).join(", ") || "—";
      return (
        `<article class="mq-event-card">` +
        `<div class="mq-event-meta"><span class="badge">${esc(ev.event_type || ev.category)}</span> ` +
        `<span class="importance">Importance ${esc(ev.importance_score)}</span></div>` +
        `<h3>${esc(ev.title || ev.headline)}</h3>` +
        `<p><small>${esc(ev.source)} · ${esc(ev.freshness_minutes)} min ago</small></p>` +
        `<p><strong>Entities:</strong> ${esc(ents)} · <strong>Tickers:</strong> ${esc(tickers)}</p>` +
        `<p class="mq-why">${esc(ev.why_this_may_matter || ev.summary || "")}</p>` +
        `</article>`
      );
    })
    .join("");
}

function renderWatchlist(wl, data) {
  renderProvenance("provenance-watchlist", data);
  const el = byId("watchlist-content");
  const quotes = wl.quotes || [];
  if (!quotes.length) {
    el.textContent = "No watchlist data.";
    return;
  }
  const rows = quotes
    .map((q) => {
      const prov = q.provenance || {};
      return (
        `<tr><td><strong>${esc(q.symbol)}</strong></td><td>${fmtUsd(q.last)}</td>` +
        `<td class="${Number(q.change_pct) >= 0 ? "bullish" : "bearish"}">${fmtPct(q.change_pct)}</td>` +
        `<td>${esc(q.volume != null ? Number(q.volume).toLocaleString() : "—")}</td>` +
        `<td><small>${esc(prov.provider)} ${esc(prov.freshness)}</small></td>` +
        `<td>${q.reality_score != null ? esc(q.reality_score) : "—"}</td></tr>`
      );
    })
    .join("");
  el.innerHTML =
    `<table class="mq-table"><thead><tr><th>Symbol</th><th>Last</th><th>Chg%</th><th>Volume</th><th>Data</th><th>Reality</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderRealityScores(scores) {
  const el = byId("reality-scores");
  if (!el) return;
  el.innerHTML = (scores || [])
    .slice(0, 8)
    .map((r) => {
      const reasons = (r.reasons || [])
        .map((x) => `<li>${x.delta > 0 ? "+" : ""}${esc(x.delta)}: ${esc(x.label)}</li>`)
        .join("");
      return (
        `<div class="mq-explain-card"><strong>${esc(r.symbol)}</strong> — Reality Score ${esc(r.reality_score)}` +
        `<ul>${reasons}</ul></div>`
      );
    })
    .join("");
}

function renderPicksTable(picksPayload) {
  const el = byId("picks-table-wrap");
  const picks = picksPayload.picks || [];
  if (!picks.length) {
    el.innerHTML = "<p>No AI picks — data may be stale.</p>";
    return;
  }
  const sorted = picks.slice().sort((a, b) => (b.confidence || b.score || 0) - (a.confidence || a.score || 0));
  el.innerHTML =
    `<table class="mq-table mq-picks-table"><thead><tr>` +
    `<th>#</th><th>Ticker</th><th>Agent</th><th>Horizon</th><th>Conf</th><th>Dir</th><th>Action</th><th>Reasons</th><th>Risks</th></tr></thead><tbody>` +
    sorted
      .map((p, i) => {
        const reasons = (p.reasons || (p.explanation || {}).bullets || []).slice(0, 2).join("; ");
        const risks = (p.risks || []).slice(0, 2).join("; ");
        return (
          `<tr><td>${i + 1}</td><td><strong>${esc(p.symbol)}</strong></td>` +
          `<td>${esc(agentLabel(p.agent_id))}</td>` +
          `<td>${esc(p.horizon || "1d")}</td>` +
          `<td>${esc(p.confidence != null ? p.confidence : p.score)}</td>` +
          `<td>${esc(p.expected_direction || p.predicted_bias)}</td>` +
          `<td>${esc(p.prediction_type || "paper_long")}</td>` +
          `<td><small>${esc(reasons)}</small></td>` +
          `<td><small>${esc(risks)}</small></td></tr>`
        );
      })
      .join("") +
    `</tbody></table>`;
}

function populateDebateSymbols(picks) {
  const sel = byId("debate-symbol");
  if (!sel) return;
  const syms = [...new Set((picks || []).map((p) => p.symbol).filter(Boolean))];
  if (!syms.length) syms.push("SPY");
  sel.innerHTML = syms.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("");
}

function renderAgentDebate(picks, symbol) {
  const el = byId("agent-debate");
  const sym = symbol || (picks[0] && picks[0].symbol) || "";
  const debate = picks.filter((p) => p.symbol === sym);
  if (!debate.length) {
    el.innerHTML = "<p>Select a ticker to see agent debate.</p>";
    return;
  }
  el.innerHTML = debate
    .map((p) => {
      const reasons = (p.reasons || (p.explanation || {}).bullets || [])
        .map((r) => `<li>${esc(r)}</li>`)
        .join("");
      return (
        `<div class="mq-debate-card ${esc(p.agent_id)}">` +
        `<strong>${esc(agentLabel(p.agent_id))}</strong> — ${esc(p.prediction_type || "watch")} · ${esc(p.horizon || "1d")}` +
        `<p>${esc((p.explanation || {}).headline || "")}</p>` +
        (reasons ? `<ul>${reasons}</ul>` : "") +
        `</div>`
      );
    })
    .join("");
}

function renderEntityGraph(graph) {
  const el = byId("entity-graph-content");
  if (!el) return;
  const chains = graph.recent_chains || [];
  const rels = graph.relationships || [];
  let html = "<h3>Recent chains</h3>";
  if (chains.length) {
    html += chains
      .slice(0, 8)
      .map(
        (c) =>
          `<div class="mq-graph-row">` +
          `<strong>${esc((c.entities || []).join(" → "))}</strong> → ${esc((c.candidate_tickers || []).join(", "))}` +
          `<br><small>${esc(c.title)}</small></div>`
      )
      .join("");
  } else {
    html += "<p>Example: Mark Carney → Canada infrastructure → BAM, BN, ENB (hypothesis only)</p>";
  }
  html += "<h3>Seed relationships</h3><ul>";
  rels.slice(0, 15).forEach((r) => {
    const to = Array.isArray(r.to) ? r.to.join(", ") : r.to;
    html += `<li>${esc(r.from)} → ${esc(to)} <small>(${esc(r.type)})</small></li>`;
  });
  html += "</ul>";
  el.innerHTML = html;
}

function renderLearningLab(report) {
  const el = byId("learning-lab");
  if (!el) return;
  const scores = report.agent_scores || {};
  let html = `<p>${esc(report.summary || "")}</p>`;
  html += `<p><a href="#panel-scout">Tools we're researching →</a></p>`;
  const keys = Object.keys(scores);
  if (keys.length) {
    html += "<ul>";
    keys.forEach((k) => {
      const s = scores[k];
      html += `<li><strong>${esc(k)}</strong>: hit rate ${esc((s.hit_rate * 100).toFixed(1))}%</li>`;
    });
    html += "</ul>";
  }
  if (report.markdown) {
    html += `<pre class="mq-report-snippet">${esc(report.markdown.slice(0, 1200))}</pre>`;
  }
  el.innerHTML = html || "<p>Run python app/scripts/marketquest_nightly_review.py for reports.</p>";
}

function renderPortfolio(pf) {
  const el = byId("portfolio-content");
  const positions = pf.positions || [];
  let posRows = positions
    .map(
      (p) =>
        `<tr><td>${esc(p.symbol)}</td><td>${esc(p.qty)}</td><td>${fmtUsd(p.entry_price)}</td>` +
        `<td>${fmtUsd(p.last_price)}</td><td>${fmtUsd(p.unrealized_pnl_usd)}</td></tr>`
    )
    .join("");
  if (!posRows) posRows = `<tr><td colspan="5"><em>No positions — long-only, $100k paper</em></td></tr>`;
  el.innerHTML =
    `<p><strong>Cash:</strong> ${fmtUsd(pf.cash_usd)} · <strong>Total:</strong> ${fmtUsd(pf.total_value_usd)} · ` +
    `<strong>Day P&amp;L:</strong> ${fmtUsd(pf.day_pnl_usd)}</p>` +
    `<table class="mq-table"><thead><tr><th>Symbol</th><th>Qty</th><th>Entry</th><th>Last</th><th>Unrealized</th></tr></thead>` +
    `<tbody>${posRows}</tbody></table>`;
}

function renderLeaderboard(lb) {
  const el = byId("leaderboard-content");
  const entries = lb.entries || [];
  let disc = "";
  if (lb.ai_disclosure) disc = `<p class="mq-warn">${esc(lb.ai_disclosure)}</p>`;
  (lb.benchmark_disclosures || []).slice(0, 2).forEach((d) => {
    disc += `<p class="mq-disclosure">${esc(d)}</p>`;
  });
  const benchmarks = lb.benchmarks || entries.filter((e) => e.type === "benchmark");
  const agents = lb.agents || entries.filter((e) => e.type === "agent");
  const players = lb.players || entries.filter((e) => e.type === "human");
  function tableRows(list) {
    return list
      .map(
        (e) =>
          `<tr><td>${esc(e.rank)}</td><td>${esc(e.display_name)}</td>` +
          `<td>${fmtPct(e.weekly_return_pct ?? e.score_pct)}</td>` +
          `<td>${fmtPct(e.max_drawdown_pct)}</td><td>${esc(e.hit_rate)}</td><td>${esc(e.best_pick)}</td></tr>`
      )
      .join("");
  }
  el.innerHTML =
    disc +
    `<p><small>Week ${esc(lb.week)}</small></p>` +
    (players.length ? `<h3>Human Players</h3><table class="mq-table"><thead><tr><th>#</th><th>Player</th><th>Return%</th><th>Drawdown</th><th>Hit%</th><th>Best</th></tr></thead><tbody>${tableRows(players)}</tbody></table>` : "") +
    (agents.length ? `<h3>AI Agents</h3><table class="mq-table"><thead><tr><th>#</th><th>Agent</th><th>Return%</th><th>Drawdown</th><th>Hit%</th><th>Best</th></tr></thead><tbody>${tableRows(agents)}</tbody></table>` : "") +
    (benchmarks.length ? `<h3>Benchmarks</h3><table class="mq-table"><thead><tr><th>#</th><th>Benchmark</th><th>Return%</th><th>Drawdown</th><th>Hit%</th><th>Best</th></tr></thead><tbody>${tableRows(benchmarks)}</tbody></table>` : tableRows(entries));
}

function renderEducation(edu, lessons) {
  const el = byId("education-content");
  const glossary = (edu.glossary || [])
    .slice(0, 12)
    .map((g) => `<dt>${esc(g.term)}</dt><dd>${esc(g.definition)}</dd>`)
    .join("");
  let lessonHtml = "";
  ((lessons || {}).cards || []).slice(0, 3).forEach((c) => {
    lessonHtml += `<div class="mq-lesson-card"><strong>${esc(c.title)}</strong><p>${esc(c.why_it_matters)}</p></div>`;
  });
  el.innerHTML = `<p>${esc(edu.models_overview || "")}</p>${lessonHtml}<dl class="mq-glossary">${glossary}</dl>`;
}

function paintDashboard(data) {
  lastDashboard = data;
  renderBanner(data);
  byId("disclaimer").textContent = data.disclaimer || byId("disclaimer").textContent;
  renderRegime(data.regime || (data.cross_asset || {}).regime);
  renderCurrencyRadar(data.currencies, data.cross_asset);
  renderCrossAsset(data.cross_asset);
  renderEventRadar(data.news_events || []);
  renderWatchlist(data.watchlist || {}, data);
  renderRealityScores(data.reality_scores || []);
  renderPicksTable(data.picks || {});
  renderBenchmarkScoreboard(data.leaderboard || {}, data.benchmark_disclosures);
  populateDebateSymbols((data.picks || {}).picks || []);
  const sym = byId("debate-symbol") && byId("debate-symbol").value;
  renderAgentDebate((data.picks || {}).picks || [], sym);
  renderEntityGraph(data.entity_graph || {});
  renderPortfolio(data.portfolio || {});
  renderLeaderboard(data.leaderboard || {});
  renderEducation(data.education || {}, data.lessons);
  renderChallenge(data.active_challenge);
  renderCareers(data.careers);
  renderScout(data.research_registry);
}

async function loadLearningLab() {
  try {
    const report = await fetchJson("/api/marketquest/learning-report" + querySuffix());
    renderLearningLab(report);
  } catch (_) {
    renderLearningLab({});
  }
}

async function submitTrade() {
  const msg = byId("trade-msg");
  msg.textContent = "";
  msg.className = "mq-msg";
  const notional = Number(byId("trade-notional").value);
  const body = {
    symbol: byId("trade-symbol").value.trim().toUpperCase(),
    side: byId("trade-side").value,
    user_id: "default",
    player_id: "local_player",
  };
  if (notional > 0) body.notional = notional;
  else body.qty = Number(byId("trade-qty").value);

  try {
    const result = await fetchJson("/api/marketquest/paper-order" + querySuffix(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (result.error) {
      msg.textContent = result.error;
      msg.className = "mq-msg err";
      return;
    }
    msg.textContent = "Paper order recorded — not investment advice.";
    msg.className = "mq-msg ok";
    if (result.portfolio) renderPortfolio(result.portfolio);
  } catch (e) {
    msg.textContent = e.message;
    msg.className = "mq-msg err";
  }
}

async function refreshNow() {
  const st = byId("refresh-status");
  st.textContent = "Refreshing…";
  try {
    await fetchJson("/api/marketquest/refresh" + querySuffix(), { method: "POST" });
    const qs = querySuffix();
    const data = await fetchJson(
      "/api/marketquest/dashboard?refresh=1" + (qs ? "&" + qs.slice(1) : "")
    );
    paintDashboard(data);
    await loadLearningLab();
    st.textContent = "Updated.";
    st.className = "mq-msg ok";
  } catch (e) {
    st.textContent = e.message;
    st.className = "mq-msg err";
  }
}

async function init() {
  try {
    const data = await fetchJson("/api/marketquest/dashboard" + querySuffix());
    paintDashboard(data);
    await loadLearningLab();
  } catch (e) {
    byId("status-banner").textContent =
      "Error: " + e.message + " — Start run_viewer_api.py on 8010. Offline: /marketquest?training=1";
    byId("status-banner").className = "mq-banner mock";
  }
}

byId("trade-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  submitTrade();
});
byId("btn-refresh").addEventListener("click", refreshNow);
byId("debate-symbol").addEventListener("change", () => {
  if (lastDashboard) {
    renderAgentDebate((lastDashboard.picks || {}).picks || [], byId("debate-symbol").value);
  }
});

init();
