function byId(id) {
  return document.getElementById(id);
}

function html(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function item(label, value) {
  return `<div class="item"><div class="k">${html(label)}</div><div class="v">${value}</div></div>`;
}

function renderList(containerId, entries) {
  byId(containerId).innerHTML = entries.join("");
}

function showError(message) {
  const node = byId("errors");
  node.style.display = "";
  node.textContent = message;
}

function clearError() {
  const node = byId("errors");
  node.style.display = "none";
  node.textContent = "";
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    throw new Error(
      response.status === 404
        ? `API not found (${url}). Start the Run Viewer API: python app/scripts/run_viewer_api.py`
        : `Bad response from ${url} (HTTP ${response.status}); expected JSON from Run Viewer API`
    );
  }
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function loadRuns() {
  clearError();
  const payload = await fetchJson("/api/runs");
  const select = byId("runSelect");
  select.innerHTML = "";
  const runs = payload.runs || [];
  if (!runs.length) {
    select.innerHTML = `<option value="">(no runs found)</option>`;
    byId("status").textContent = "No runs discovered in app/data/acquisition_runs/";
    return;
  }
  runs.forEach((runId) => {
    const opt = document.createElement("option");
    opt.value = runId;
    opt.textContent = runId;
    select.appendChild(opt);
  });
  byId("status").textContent = `Loaded ${runs.length} run id(s).`;
}

function formatValue(value) {
  if (Array.isArray(value)) return html(value.length ? JSON.stringify(value) : "[]");
  if (value === null || value === undefined || value === "") return "--";
  if (typeof value === "boolean") return value ? "true" : "false";
  return html(String(value));
}

function pathValue(value) {
  if (!value) return "--";
  if (value === "not linked to run_id") {
    return `<span class="warn">${html(value)}</span>`;
  }
  return `<code>${html(value)}</code>`;
}

function renderRun(run) {
  const banner = byId("noCandidatesBanner");
  if (run.overall_pipeline_status === "COMPLETE_NO_CANDIDATES" && run.no_candidates_message) {
    banner.style.display = "";
    banner.textContent = run.no_candidates_message;
  } else {
    banner.style.display = "none";
    banner.textContent = "";
  }

  renderList("summaryGrid", [
    item("run_id", formatValue(run.run_id)),
    item("provider", formatValue(run.provider)),
    item("start_date", formatValue(run.start_date)),
    item("end_date", formatValue(run.end_date)),
    item("symbols_requested", formatValue(run.symbols_requested)),
    item("symbols_returned", formatValue(run.symbols_returned)),
    item("symbols_skipped", formatValue(run.symbols_skipped)),
    item("normalized_rows", formatValue(run.normalized_rows)),
    item("rejected_rows", formatValue(run.rejected_rows)),
    item("candidate_count", formatValue(run.candidate_count)),
    item("rejected_candidate_count", formatValue(run.rejected_candidate_count)),
    item("partial_coverage", formatValue(run.partial_coverage)),
    item("full_coverage_claimed", formatValue(run.full_coverage_claimed)),
    item("ready_for_pipeline", formatValue(run.ready_for_pipeline)),
    item("overall_pipeline_status", formatValue(run.overall_pipeline_status)),
  ]);

  renderList("sourceGrid", [
    item("provider_selected", formatValue(run.provider)),
    item("source_log_row_count", formatValue(run.source_log_rows_returned)),
    item("provider_source_reference", formatValue(run.provider_source_reference)),
    item("limitations", formatValue(run.limitations)),
    item("warnings", formatValue(run.warnings)),
  ]);

  const paths = run.paths || {};
  renderList(
    "pathsGrid",
    Object.keys(paths)
      .sort()
      .map((key) => item(key, pathValue(paths[key])))
  );

  byId("missingArtifacts").textContent = (run.missing_artifacts || []).length
    ? JSON.stringify(run.missing_artifacts, null, 2)
    : "[]";

  const gov = document.getElementById("governanceDetail");
  if (gov) {
    gov.textContent = JSON.stringify(run.governance || {}, null, 2);
  }
}

async function loadSelectedRun() {
  clearError();
  const runId = byId("runSelect").value;
  if (!runId) {
    showError("Select a run id first.");
    return;
  }
  const payload = await fetchJson(`/api/runs/${encodeURIComponent(runId)}`);
  renderRun(payload);
  byId("status").textContent = `Loaded run: ${runId}`;
}

byId("refreshRuns").addEventListener("click", () => {
  loadRuns().catch((err) => showError(err.message));
});
byId("loadRun").addEventListener("click", () => {
  loadSelectedRun().catch((err) => showError(err.message));
});

loadRuns()
  .then(() => {
    const params = new URLSearchParams(window.location.search);
    const preset = params.get("run_id");
    const sel = byId("runSelect");
    if (preset) {
      const match = Array.from(sel.options).find((o) => o.value === preset);
      if (match) sel.value = preset;
    }
    if (sel.value) return loadSelectedRun();
    return Promise.resolve();
  })
  .catch((err) => showError(err.message));
