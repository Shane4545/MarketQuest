function byId(id) {
  return document.getElementById(id);
}

function showOptsError(message) {
  const node = byId("optsError");
  node.style.display = "";
  node.textContent = message;
}

function clearOptsError() {
  const node = byId("optsError");
  node.style.display = "none";
  node.textContent = "";
}

async function fetchJson(url, options) {
  const response = await fetch(url, Object.assign({ cache: "no-store" }, options || {}));
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function postLaunch(body) {
  const response = await fetch("/api/run-launcher/launch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function fillSelect(selectId, values, selected) {
  const sel = byId(selectId);
  sel.innerHTML = "";
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  });
  if (selected && values.includes(selected)) sel.value = selected;
}

async function loadOptions() {
  clearOptsError();
  const payload = await fetchJson("/api/run-launcher/options");
  fillSelect("mode", payload.available_modes || []);
  fillSelect("provider", payload.available_providers || []);
  fillSelect("rule", payload.available_rules || []);
  fillSelect("run_purpose", payload.allowed_run_purpose || []);

  const defs = payload.default_dates_fixture || {};
  byId("start_date").value = defs.start_date || "";
  byId("end_date").value = defs.end_date || "";

  const today = defs.end_date || "2026-01-08";
  byId("as_of_date").value = today;
  byId("review_date").value = today;

  const fx = payload.default_fixture_relative_paths || {};
  byId("fixture_path").placeholder = fx.fixture || "";
  byId("market_cap_fixture").placeholder = fx.market_cap_fixture || "";

  byId("mode").value = "fixture";
  byId("provider").value = "fixture";
  byId("amount").value = "10000";
  byId("basket_name").value = "launcher_demo";
}

function collectPayload() {
  const symbolsRaw = byId("symbols").value.trim();
  const payload = {
    mode: byId("mode").value,
    provider: byId("provider").value,
    start_date: byId("start_date").value.trim(),
    end_date: byId("end_date").value.trim(),
    as_of_date: byId("as_of_date").value.trim(),
    review_date: byId("review_date").value.trim(),
    rule: byId("rule").value,
    basket_name: byId("basket_name").value.trim(),
    amount: Number(byId("amount").value),
    run_purpose: byId("run_purpose").value,
  };
  if (symbolsRaw) payload.symbols = symbolsRaw;

  const fp = byId("fixture_path").value.trim();
  const mcf = byId("market_cap_fixture").value.trim();
  if (fp) payload.fixture_path = fp;
  if (mcf) payload.market_cap_fixture = mcf;

  const rid = byId("run_id").value.trim();
  if (rid) payload.run_id = rid;

  return payload;
}

byId("launchForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  clearOptsError();
  const btn = byId("submitBtn");
  btn.disabled = true;
  const panel = byId("resultPanel");
  const pre = byId("resultPre");
  const linkP = byId("viewerLinkP");
  linkP.style.display = "none";
  panel.style.display = "";
  pre.textContent = "Running…";
  try {
    const body = collectPayload();
    const payload = await postLaunch(body);
    pre.textContent = JSON.stringify(payload, null, 2);
    if (payload.viewer_url) {
      linkP.style.display = "";
      const a = byId("viewerLink");
      a.href = payload.viewer_url;
      a.textContent = payload.viewer_url;
    }
  } catch (err) {
    pre.textContent = String(err.message || err);
  } finally {
    btn.disabled = false;
  }
});

loadOptions().catch((err) => showOptsError(err.message || String(err)));
