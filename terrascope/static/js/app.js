"use strict";
// TerraScope front-end. Code generated with AI assistance (Claude, Anthropic).

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const GLYPH = { increase: "▲", decrease: "▼", none: "●", insufficient: "?" };
const LABEL = { increase: "SIGNIFICANT INCREASE", decrease: "SIGNIFICANT DECREASE", none: "NO SIG. TREND", insufficient: "NOT ANALYSED" };
const SCOL = ["#3df5ff", "#ff4fa3", "#ffd23f"];

let CAT = null, RES = null, MAP = null, LAYER, PREVIEW, SEL = [], BOXC = [], MARKERS = {};

const fmt = v => v == null ? "–" : Math.abs(v) < 0.1 ? v.toFixed(3) : Math.abs(v) < 10 ? v.toFixed(2) : v.toFixed(1);
const sg = v => v == null ? "–" : (v > 0 ? "+" : "") + fmt(v);
const pf = p => p == null ? "–" : p < 0.001 ? "<0.001" : p.toFixed(3);

/* ---------------- pixel art ---------------- */
function px(canvas, rows, pal, s) {
  canvas.width = rows[0].length * s; canvas.height = rows.length * s;
  const g = canvas.getContext("2d");
  rows.forEach((r, y) => [...r].forEach((ch, x) => { if (pal[ch]) { g.fillStyle = pal[ch]; g.fillRect(x * s, y * s, s, s); } }));
}
function drawRocket() {
  px($("#rocket"), [
    "......RR......", ".....RRRR.....", "....RWWWWR....", "....RWBBWR....", "....RWBBWR....", "....RWWWWR....",
    "....RWWWWR....", "...RRWWWWRR...", "..RRR.WW.RRR..", "..RR..WW..RR..", "......OO......", ".....OYYO.....", "......YY......"],
    { R: "#ff4f6d", W: "#f2f2ff", B: "#4de1ff", O: "#ff8a3d", Y: "#ffd23f" }, 6);
}
function drawEarth() {
  const c = $("#earth"), n = 20, s = 5; c.width = c.height = n * s;
  const g = c.getContext("2d");
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const d = Math.hypot(x - 9.5, y - 9.5); if (d > 9.6) continue;
    const land = Math.sin(x * 0.8 + 1.3) * Math.cos(y * 0.65 + 0.4) + Math.sin((x - y) * 0.45) > 0.55, dark = x + y > 20;
    g.fillStyle = d > 8.7 ? "#7fdcff" : land ? (dark ? "#2a8f45" : "#3fcf62") : (dark ? "#1b4fa8" : "#2f79e8");
    g.fillRect(x * s, y * s, s, s);
  }
}
function drawStars() {
  const c = $("#stars"), g = c.getContext("2d"), reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let W, H, S = [];
  const init = () => {
    W = c.width = innerWidth; H = c.height = innerHeight;
    S = Array.from({ length: Math.floor(W * H / 9000) }, () => ({
      x: Math.floor(Math.random() * W / 4) * 4, y: Math.floor(Math.random() * H / 4) * 4, s: Math.random() < .15 ? 4 : 2,
      p: Math.random() * 6.28, c: ["#ffffff", "#9fb4ff", "#ffd9a0", "#3df5ff"][Math.floor(Math.random() * 4)]
    }));
    draw(0);
  };
  const draw = t => {
    g.clearRect(0, 0, W, H);
    for (const o of S) { g.globalAlpha = reduce ? .7 : .35 + .65 * Math.abs(Math.sin(t / 1200 + o.p)); g.fillStyle = o.c; g.fillRect(o.x, o.y, o.s, o.s); }
    if (!reduce) setTimeout(() => requestAnimationFrame(draw), 100);
  };
  let started = false;
  addEventListener("resize", () => { if (started) { W = c.width = innerWidth; H = c.height = innerHeight; } });
  init(); started = true;
}

/* ---------------- boot ---------------- */
async function boot() {
  drawStars(); drawRocket(); drawEarth();
  CAT = await (await fetch("/api/catalog")).json();
  $("#synth").hidden = !CAT.synthetic;
  $("#variable").innerHTML = CAT.variables.filter(v => v.enabled).map(v => `<option value="${v.id}">${esc(v.name)} (${esc(v.out_unit)})</option>`).join("");
  $("#season").innerHTML = CAT.seasons.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join("");
  $("#start").value = CAT.first_year; $("#end").value = CAT.last_year;
  $("#start").min = CAT.first_year; $("#end").max = CAT.last_year;
  $("#mm-years").textContent = `${CAT.first_year} – ${CAT.last_year}`;
  initMap(); renderExplorer();

  $$(".tab").forEach(b => b.onclick = () => showTab(b.dataset.tab));
  $$("input[name=scope]").forEach(r => r.onchange = onScope);
  ["lat", "lon", "la0", "la1", "lo0", "lo1"].forEach(id => $("#" + id).oninput = drawPreview);
  $("#run").onclick = () => run(formParams());
  $("#mm-run").onclick = monsoonPreset;
  $("#q").oninput = renderExplorer;
  $("#showlin").onchange = drawChart;
  $("#dl-csv").onclick = exportCSV; $("#dl-md").onclick = exportMD; $("#dl-print").onclick = () => print();
}

function showTab(t) {
  $$(".tab").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
  ["mission", "explorer", "monsoon", "method"].forEach(n => $("#tab-" + n).hidden = n !== t);
  if (t === "mission" && MAP) setTimeout(() => MAP.invalidateSize(), 50);
  scrollTo({ top: 0 });
}

/* ---------------- map ---------------- */
const scope = () => $("input[name=scope]:checked").value;
function initMap() {
  MAP = L.map("map", { center: [21.5, 80], zoom: 5, minZoom: 2, worldCopyJump: true });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 12 }).addTo(MAP);
  LAYER = L.layerGroup().addTo(MAP); PREVIEW = L.layerGroup().addTo(MAP);
  MAP.on("click", onMapClick); drawPreview();
}
function onScope() {
  $("#sc-point").hidden = scope() !== "point"; $("#sc-box").hidden = scope() !== "box";
  BOXC = []; drawPreview();
}
function onMapClick(e) {
  const lat = +e.latlng.lat.toFixed(2), lon = +e.latlng.wrap().lng.toFixed(2), s = scope();
  if (s === "point") { $("#lat").value = lat; $("#lon").value = lon; }
  else if (s === "box") {
    if (BOXC.length >= 2) BOXC = [];
    BOXC.push([lat, lon]);
    if (BOXC.length === 2) {
      const [a, b] = BOXC;
      $("#la0").value = Math.min(a[0], b[0]); $("#la1").value = Math.max(a[0], b[0]);
      $("#lo0").value = Math.min(a[1], b[1]); $("#lo1").value = Math.max(a[1], b[1]);
    }
  } else return;
  drawPreview();
}
const sqIcon = (cls, html = "", size = 22) => L.divIcon({ className: "pxm-wrap", html: `<div class="${cls}">${html}</div>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
function drawPreview() {
  PREVIEW.clearLayers(); const s = scope();
  if (s === "india") CAT.zones.forEach(z => z.points.forEach(p =>
    L.marker([p.lat, p.lon], { icon: sqIcon("pxs", "", 8), interactive: true, keyboard: false }).bindTooltip(`${z.name}: ${p.label}`).addTo(PREVIEW)));
  else if (s === "point") { const la = +$("#lat").value, lo = +$("#lon").value; if (isFinite(la) && isFinite(lo)) L.marker([la, lo], { icon: sqIcon("pxm none", "+") }).addTo(PREVIEW); }
  else {
    const v = ["la0", "la1", "lo0", "lo1"].map(id => +$("#" + id).value);
    if (v.every(isFinite) && v[1] > v[0] && v[3] > v[2]) L.rectangle([[v[0], v[2]], [v[1], v[3]]], { color: "#ffd23f", weight: 3, dashArray: "6 6", fillOpacity: 0.08 }).addTo(PREVIEW);
    BOXC.forEach(c => L.marker(c, { icon: sqIcon("pxm none", "+") }).addTo(PREVIEW));
  }
}
function drawMarkers() {
  LAYER.clearLayers(); PREVIEW.clearLayers(); MARKERS = {};
  const pts = [];
  RES.points.forEach(p => {
    const st = p.stats, ok = st && st.status === "ok";
    const tip = `<b>${esc(p.zone)}</b> – ${esc(p.label)}<br>${GLYPH[p.cls]} ${ok ? sg(st.sen_slope) + " " + esc(unit()) + "/yr" : "no data"}${p.q != null ? "<br>q = " + pf(p.q) : ""}`;
    const m = L.marker([p.lat, p.lon], { icon: sqIcon("pxm " + p.cls, GLYPH[p.cls]), keyboard: false }).bindTooltip(tip).addTo(LAYER);
    m.on("click", () => { if (p.values) { SEL = ["p:" + p.id]; refreshSel(); } });
    MARKERS[p.id] = m; pts.push([p.lat, p.lon]);
  });
  if (pts.length > 1) MAP.fitBounds(pts, { padding: [40, 40], maxZoom: 7 }); else if (pts.length) MAP.setView(pts[0], 6);
}

/* ---------------- run ---------------- */
const unit = () => RES ? RES.meta.variable.out_unit : "";
function formParams() {
  const p = { variable: $("#variable").value, season: $("#season").value, start: +$("#start").value, end: +$("#end").value, scope: scope() };
  if (p.scope === "point") { p.lat = $("#lat").value; p.lon = $("#lon").value; }
  if (p.scope === "box") { p.lat_min = $("#la0").value; p.lat_max = $("#la1").value; p.lon_min = $("#lo0").value; p.lon_max = $("#lo1").value; }
  return p;
}
function monsoonPreset() {
  $("#variable").value = "PRECTOTCORR"; $("#season").value = "JJAS"; $("#start").value = CAT.first_year; $("#end").value = CAT.last_year;
  $("input[name=scope][value=india]").checked = true; onScope(); showTab("mission"); run(formParams());
}
function setBusy(on, msg) {
  $("#run").disabled = on; $("#busy").hidden = !on;
  if (on) { $("#bar").style.width = "3%"; $("#busy-msg").textContent = msg; $("#err").hidden = true; }
}
function showErr(m) { const e = $("#err"); e.textContent = "⚠ " + m; e.hidden = false; }

async function run(body) {
  setBusy(true, "CONTACTING NASA POWER...");
  try {
    const r = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Request rejected");
    for (;;) {
      const s = await (await fetch("/api/job/" + j.job)).json();
      if (s.status === "running") {
        const pct = s.total ? Math.max(3, Math.round(100 * s.done / s.total)) : 3;
        $("#bar").style.width = pct + "%";
        $("#busy-msg").textContent = s.total ? `FETCHING ${s.done} / ${s.total} LOCATIONS...` : "CONTACTING NASA POWER...";
        await sleep(500); continue;
      }
      if (s.status === "error") throw new Error(s.error);
      $("#bar").style.width = "100%"; render(s.result); break;
    }
  } catch (e) { showErr(e.message || String(e)); }
  setBusy(false);
}

/* ---------------- render results ---------------- */
function seriesOf(key) {
  const [t, i] = key.split(":"), o = t === "z" ? RES.zones[+i] : RES.points.find(p => p.id === +i);
  return { key, label: t === "z" ? o.name : `${o.zone} (${o.label})`, values: o.values, stats: o.stats, cls: o.cls, q: o.q, n_points: o.n_points };
}
function render(res) {
  RES = res; SEL = ["z:0"];
  $("#results").hidden = false;
  const m = res.meta, c = res.summary.counts;
  $("#warns").innerHTML = m.warnings.map(w => `<div class="warn">⚠ ${esc(w)}</div>`).join("");
  const nz = res.zones.length;
  $("#tiles").innerHTML = [
    ["REGIONS", nz], ["POINTS ANALYSED", `${m.n_points - m.n_failed}/${m.n_points}`], ["YEARS", `${m.start}–${m.end}`],
    ["▲ SIGNIFICANT UP", c.increase], ["▼ SIGNIFICANT DOWN", c.decrease], ["● NO SIG. TREND", c.none]
  ].map(([k, v]) => `<div class="tile"><b>${k}</b><span>${v}</span></div>`).join("");

  const tag = (n, cls) => `<span class="${cls}">${esc(n)} ${cls === "inc" ? GLYPH.increase : GLYPH.decrease}</span>`;
  const S = res.summary;
  $("#callout").innerHTML = nz < 2 ? "" : S.opposing
    ? `<div class="callout">◆ <b>OPPOSING TRENDS DETECTED.</b> ${S.decrease_zones.map(n => tag(n, "dec")).join(", ")} moved <span class="dec">down</span> while ${S.increase_zones.map(n => tag(n, "inc")).join(", ")} moved <span class="inc">up</span>. Both are significant after multiple-testing correction.</div>`
    : `<div class="callout calm">◇ No significant opposing trends between regions in this run. Regions marked ● have no statistically significant trend detected.</div>`;

  drawTable(); drawMarkers(); refreshSel(); drawProv();
  $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function drawTable() {
  const u = unit(), rows = [];
  const add = (key, name, st, cls, q, extra) => {
    const ok = st.status === "ok";
    rows.push(`<tr data-key="${key}"><td><input type="checkbox" data-key="${key}" aria-label="compare ${esc(name)}"></td>
      <td><b>${esc(name)}</b>${extra ? `<div class="mut">${extra}</div>` : ""}</td>
      <td class="t-${cls}">${GLYPH[cls]} ${LABEL[cls]}</td>
      <td>${ok ? `${sg(st.sen_slope)}<div class="mut">[${sg(st.sen_lo)}, ${sg(st.sen_hi)}]</div>` : "–"}</td>
      <td>${ok && st.pct_per_decade != null ? sg(st.pct_per_decade) + "%" : "–"}</td>
      <td>${ok ? pf(st.mk_p) : "–"}</td><td>${ok ? pf(q) : "–"}</td>
      <td class="mut">${ok ? `${st.n} yrs${st.gaps ? `, ${st.gaps} gap` : ""}<br>${esc(st.method.replace(" (positive autocorrelation detected)", "*"))}` : `only ${st.n} valid yrs`}</td></tr>`);
  };
  RES.zones.forEach((z, i) => add("z:" + i, z.name, z.stats, z.cls, z.q, z.n_points > 1 ? `${z.n_points} points` : ""));
  $("#ztable").innerHTML = `<thead><tr><th></th><th>REGION</th><th>TREND</th><th>SEN SLOPE<br>${esc(u)}/yr [95% CI]</th><th>% PER<br>DECADE</th><th>MK p</th><th>q (FDR)</th><th>DETAIL</th></tr></thead><tbody>${rows.join("")}</tbody>`;
  $("#tablenote").textContent = "● = no statistically significant trend detected (this is not proof of no change). * = autocorrelation-corrected test used. q = p adjusted across regions.";
  $$("#ztable tbody tr").forEach(tr => tr.onclick = e => {
    if (e.target.type === "checkbox") return;
    SEL = [tr.dataset.key]; refreshSel();
  });
  $$("#ztable input[type=checkbox]").forEach(cb => cb.onchange = () => {
    const k = cb.dataset.key;
    SEL = cb.checked ? [...SEL.filter(x => x !== k), k].slice(-3) : SEL.filter(x => x !== k);
    if (!SEL.length) SEL = [k]; refreshSel();
  });
}
function refreshSel() {
  $$("#ztable tbody tr").forEach(tr => tr.classList.toggle("sel", SEL.includes(tr.dataset.key)));
  $$("#ztable input[type=checkbox]").forEach(cb => cb.checked = SEL.includes(cb.dataset.key));
  Object.entries(MARKERS).forEach(([id, m]) => { const el = m.getElement(); if (el) el.firstChild.classList.toggle("sel", SEL.includes("p:" + id)); });
  drawChart(); drawCards();
}

function drawChart() {
  if (!RES) return;
  const traces = [], u = unit();
  SEL.forEach((k, i) => {
    const s = seriesOf(k), col = SCOL[i % 3], st = s.stats;
    traces.push({ x: RES.years, y: s.values, mode: "lines+markers", name: s.label, connectgaps: false,
      line: { color: col, width: 2 }, marker: { symbol: "square", size: 7, color: col } });
    if (st.status === "ok") {
      const x = [st.year_start, st.year_end];
      traces.push({ x, y: x.map(t => st.sen_intercept + st.sen_slope * t), mode: "lines", name: s.label + " · Sen trend", line: { color: col, width: 3, dash: "dash" } });
      if ($("#showlin").checked) traces.push({ x, y: x.map(t => st.lin_intercept + st.lin_slope * t), mode: "lines", name: s.label + " · linear fit", line: { color: col, width: 2, dash: "dot" } });
    }
  });
  const ax = { gridcolor: "#262b6e", zerolinecolor: "#262b6e", linecolor: "#5b63ff", tickfont: { size: 16 } };
  Plotly.react("chart", traces, {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "#070726", font: { family: "VT323, monospace", size: 17, color: "#e8e8ff" },
    margin: { l: 70, r: 20, t: 10, b: 50 }, height: 400, hovermode: "x unified",
    xaxis: { ...ax, title: { text: "Year" }, dtick: 5 }, yaxis: { ...ax, title: { text: u }, automargin: true },
    legend: { orientation: "h", y: -0.22, font: { size: 16 } }
  }, { displayModeBar: false, responsive: true });
}
function drawCards() {
  const u = unit();
  $("#cards").innerHTML = SEL.map((k, i) => {
    const s = seriesOf(k), st = s.stats, c = SCOL[i % 3];
    if (st.status !== "ok") return `<div class="card" style="--c:${c}"><h3>${esc(s.label)}</h3><p>Only ${st.n} valid years. At least 10 are needed to test a trend.</p></div>`;
    return `<div class="card" style="--c:${c}"><h3>${esc(s.label)}</h3><dl>
      <dt>Verdict</dt><dd>${GLYPH[s.cls]} ${LABEL[s.cls]}</dd>
      <dt>Sen slope</dt><dd>${sg(st.sen_slope)} ${esc(u)}/yr</dd>
      <dt>95% CI</dt><dd>[${sg(st.sen_lo)}, ${sg(st.sen_hi)}]</dd>
      <dt>Linear slope</dt><dd>${sg(st.lin_slope)} ± ${fmt((st.lin_hi - st.lin_lo) / 2)}</dd>
      <dt>R² / lin. p</dt><dd>${st.r2.toFixed(2)} / ${pf(st.lin_p)}</dd>
      <dt>Mann-Kendall p</dt><dd>${pf(st.mk_p)}</dd><dt>q (FDR)</dt><dd>${pf(s.q)}</dd>
      <dt>z / tau</dt><dd>${st.mk_z.toFixed(2)} / ${st.mk_tau.toFixed(2)}</dd>
      <dt>Lag-1 autocorr.</dt><dd>${st.lag1.toFixed(2)}${st.lag1_significant ? " (significant)" : ""}</dd>
      <dt>Test used</dt><dd>${esc(st.method)}</dd><dt>Valid years</dt><dd>${st.n} (${st.year_start}–${st.year_end})</dd></dl>
      ${st.note ? `<p class="hint">${esc(st.note)}</p>` : ""}</div>`;
  }).join("");
}

function drawProv() {
  const m = RES.meta, v = m.variable, rows = [
    ["Dataset", m.dataset], ["Variable", `${v.name} (${v.id}), API unit ${m.api_units_reported || v.api_unit}`], ["Source", v.source],
    ["Season", `${m.season.name}, ${m.start}–${m.end}`], ["Aggregation", v.agg === "sum_days" ? "monthly mm/day × days in month, summed over season" : "day-weighted seasonal mean"],
    ["Output unit", v.out_unit], ["Community", m.community], ["Locations", `${m.n_points - m.n_failed} retrieved of ${m.n_points} (${m.n_cached} from cache)`],
    ["Retrieved", m.retrieved_first === m.retrieved_last ? m.retrieved_first : `${m.retrieved_first} to ${m.retrieved_last}`],
    ["Significance", `α = ${m.alpha}, Benjamini–Hochberg FDR across locations and across regions`], ["Minimum record", `${m.min_valid_years} valid years`],
    ["Example request", m.example_request], ["Run at (UTC)", m.run_at],
    ["Software", Object.entries(m.software).map(([k, x]) => `${k} ${x}`).join(", ")]];
  if (m.synthetic) rows.unshift(["WARNING", "SYNTHETIC TEST DATA - NOT NASA"]);
  $("#prov").innerHTML = rows.map(([k, x]) => `<dt>${esc(k)}</dt><dd>${esc(x)}</dd>`).join("");
}

/* ---------------- explorer ---------------- */
let CATFILTER = "All";
function renderExplorer() {
  const q = $("#q").value.trim().toLowerCase(), cats = ["All", ...new Set(CAT.variables.map(v => v.category))];
  $("#chips").innerHTML = cats.map(c => `<button type="button" class="chip ${c === CATFILTER ? "on" : ""}" data-c="${esc(c)}">${esc(c).toUpperCase()}</button>`).join("");
  $$(".chip").forEach(b => b.onclick = () => { CATFILTER = b.dataset.c; renderExplorer(); });
  const hit = v => (CATFILTER === "All" || v.category === CATFILTER) &&
    (!q || [v.name, v.id, v.category, v.description, ...v.keywords].join(" ").toLowerCase().includes(q));
  const list = CAT.variables.filter(hit);
  $("#vars").innerHTML = list.length ? list.map(v => `<div class="card">
    <h3>${esc(v.name)}</h3><dl>
    <dt>Code</dt><dd>${esc(v.id)}</dd><dt>Category</dt><dd>${esc(v.category)}</dd><dt>Unit</dt><dd>${esc(v.api_unit)}</dd>
    <dt>Coverage</dt><dd>${esc(v.coverage)}</dd><dt>Resolution</dt><dd>${esc(v.resolution)}</dd></dl>
    <p>${esc(v.description)}</p><p class="hint">Source: ${esc(v.source)}<br>Method: ${esc(v.method)}</p>
    ${v.enabled ? `<button class="btn" type="button" data-v="${v.id}">INVESTIGATE &#9658;</button>` : `<p class="hint">&#9203; COMING SOON</p>`}</div>`).join("")
    : `<div class="px"><p>No variables match &ldquo;${esc(q)}&rdquo;.</p></div>`;
  $$("#vars button[data-v]").forEach(b => b.onclick = () => { $("#variable").value = b.dataset.v; showTab("mission"); });
}

/* ---------------- export ---------------- */
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; document.body.appendChild(a); a.click(); a.remove();
}
const stamp = () => `${RES.meta.variable.id}_${RES.meta.season.id}_${RES.meta.start}-${RES.meta.end}${RES.meta.synthetic ? "_SYNTHETIC" : ""}`;
function exportCSV() {
  const q = x => `"${String(x ?? "").replace(/"/g, '""')}"`, h = ["level", "name", "zone", "lat", "lon", "class", "n_years", "sen_slope", "sen_ci_low", "sen_ci_high",
    "linear_slope", "linear_p", "mk_p", "q_fdr", "method", ...RES.years.map(y => "y" + y)];
  const row = (lvl, name, zone, lat, lon, o) => { const s = o.stats, ok = s.status === "ok";
    return [lvl, name, zone, lat, lon, o.cls, s.n, ok ? s.sen_slope : "", ok ? s.sen_lo : "", ok ? s.sen_hi : "", ok ? s.lin_slope : "", ok ? s.lin_p : "", ok ? s.mk_p : "", o.q ?? "", ok ? s.method : "",
      ...(o.values || []).map(v => v ?? "")].map(q).join(","); };
  const lines = [h.map(q).join(",")];
  if (RES.meta.synthetic) lines.unshift("# SYNTHETIC TEST DATA - NOT NASA MEASUREMENTS");
  RES.zones.forEach(z => lines.push(row("region", z.name, z.name, "", "", z)));
  RES.points.filter(p => p.stats).forEach(p => lines.push(row("point", p.label, p.zone, p.lat, p.lon, p)));
  download(`terrascope_${stamp()}.csv`, lines.join("\n"), "text/csv");
}
function exportMD() {
  const m = RES.meta, v = m.variable, u = v.out_unit, S = RES.summary;
  const L = [`# TerraScope investigation report`, ""];
  if (m.synthetic) L.push("> **SYNTHETIC TEST DATA - NOT NASA MEASUREMENTS**", "");
  L.push(`**Question:** How has ${v.name.toLowerCase()} (${m.season.name}) changed over ${m.start}–${m.end}, and do regions differ?`, "",
    "## Findings", "", `| Region | Verdict | Sen slope (${u}/yr) | 95% CI | MK p | q (FDR) | Years |`, "|---|---|---|---|---|---|---|");
  RES.zones.forEach(z => { const s = z.stats, ok = s.status === "ok";
    L.push(`| ${z.name} | ${LABEL[z.cls]} | ${ok ? sg(s.sen_slope) : "-"} | ${ok ? `[${sg(s.sen_lo)}, ${sg(s.sen_hi)}]` : "-"} | ${ok ? pf(s.mk_p) : "-"} | ${ok ? pf(z.q) : "-"} | ${s.n} |`); });
  L.push("", S.opposing ? `**Opposing trends:** significant decrease in ${S.decrease_zones.join(", ")}; significant increase in ${S.increase_zones.join(", ")}.`
    : "**Opposing trends:** none significant in this run.", "",
    "\"No significant trend\" means no statistically significant trend was detected; it does not prove the absence of change.", "",
    "## Method", "", `- Data: ${m.dataset}; parameter ${v.id}; community ${m.community}; retrieved ${m.retrieved_first}.`,
    `- Aggregation: ${v.agg === "sum_days" ? "monthly mm/day x days in month, summed over the season" : "day-weighted seasonal mean"}; any missing month makes the season-year missing.`,
    `- Trend size: Sen's slope with 95% CI. Test: Mann-Kendall (Hamed-Rao modified when positive lag-1 autocorrelation is significant). alpha = ${m.alpha}.`,
    `- Multiple testing: Benjamini-Hochberg across ${m.n_points} locations and across regions.`,
    `- Software: ${Object.entries(m.software).map(([k, x]) => `${k} ${x}`).join(", ")}.`, "",
    "## Limitations", "", "- MERRA-2 is a reanalysis, not a gauge record.", "- Regions are sample points, not a full grid; region values are plain averages of their points.",
    "- Trends show what changed, not why.", "- Results depend on the chosen period and season.", "",
    "_Code generated with AI assistance (Claude, Anthropic). TerraScope is not affiliated with or endorsed by NASA._");
  download(`terrascope_report_${stamp()}.md`, L.join("\n"), "text/markdown");
}

boot().catch(e => { document.body.insertAdjacentHTML("afterbegin", `<p class="errbox">Could not start: ${esc(e.message)}</p>`); });
