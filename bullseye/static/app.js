/* Bulls Eye — front end (no build step) */
const ACT = { WALK: "Walk", GET: "Reach & grasp", GRASP: "Grasp", MOVE_OBJECT: "Move object", PUSH_PULL: "Push / pull / button",
  PLACE_ASIDE: "Place aside", PLACE: "Place", POSITION: "Position", INSERT_ALIGN: "Insert / align", INSPECT: "Inspect",
  SIT_STAND: "Sit / stand", BEND_ARISE: "Bend & arise", BODY_LARGE: "Climb / bend & sit / door", TOOL_USE: "Tool / equipment use", PROCESS: "Process time" };
const DIFFS = ["simple", "adjust", "precise"];
// Company wording (CS PRE BENDING-1 reference sheet) offered while typing a sub-operation
const PHRASES = ["WALK 5-8 STEPS", "WALK 2-3 STEPS", "WALK 33 STEPS", "TURN AND WALK 2-3 STEP BACK TO HOME POSITION", "MOVE THE 2-3 STEPS",
  "WITH IN REACH GRASP THE PENDENT", "WITH IN REACH GET THE MAGNETIC TACKLE", "GRASP THE TACKLE IN HAND", "GRASP THE SHEET IN ONE HAND FOR GUIDE",
  "MOVE TACKLE 3 INCHES WITH ORIENTATION", "PUSH /PULL 3 INCHES LEVER TO OPEN THE TACKLE", "PUSH /PULL 3 INCHES LEVER TO LOCK THE TACKLE",
  'PUSH THE PENDENT BUTTON TO LIFT <=1"', 'PUSH /PULL TO RELEASE THE TACKLE BY LEVER <12"', "PUSH THE PENDENT BUTTON TO MOVE 2-3 STEPS",
  "POSITION THE PLATE INTO STAND", "PLACE THE PLATE INTO STAND", "PLACE ASIDE METAL BRUSH", "PLACES ASIDE THE PENDENT AND TACKLE",
  "INSERT 2 INCHES INTO SHEET", "INSPECT THE LOCK CONDITION", "BEND AND ARISE TO GET THE ", "FASTEN 4 BOLTS WITH POWER WRENCH",
  "FASTEN SCREW 5 TURNS WITH SCREWDRIVER", "LOOSEN NUT 3 STROKES WITH WRENCH", "WRITE 6 DIGITS ON THE CARD", "READ THE GAUGE",
  "WIPE 1 SQ.FT WITH CLOTH", "MEASURE WITH STEEL TAPE", "SURFACE TREAT 15 SQ.FT", "GRASP THE METAL SCRUBER/ METAL BRUSH"];
const CODE_COLORS = { A: "#2563eb", AG: "#0891b2", G: "#16a34a", M: "#ea580c", P: "#7c3aed", I: "#db2777", X: "#ca8a04",
  B: "#0d9488", F: "#b91c1c", L: "#be123c", C: "#9333ea", S: "#65a30d", T: "#0369a1", R: "#a16207", W: "#475569", K: "#57534e" };
const CODE_NAMES = { A: "Action distance", AG: "Reach + grasp", G: "Gain control", M: "Controlled move", P: "Placement", I: "Insert / inspect", X: "Process time",
  B: "Body motion", F: "Fasten", L: "Loosen", C: "Cut", S: "Surface treat", T: "Think / inspect / read", R: "Record", W: "Keyboard", K: "Keypad" };
const AUTO_KEYS = new Set(["activity", "start_s", "end_s", "walk_steps_min", "walk_steps_max", "distance_in", "heavy", "difficulty", "tool_action", "tool_count"]);
const ICON = {
  up: '<svg viewBox="0 0 24 24"><path d="M5 20h14v-2H5zm7-16-6 6h4v6h4v-6h4z"/></svg>',
  xls: '<svg viewBox="0 0 24 24"><path d="M5 20h14v-2H5zM19 9h-4V3H9v6H5l7 7z"/></svg>',
  redo: '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4z"/></svg>',
  del: '<svg viewBox="0 0 24 24"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6zM19 4h-3.5l-1-1h-5l-1 1H5v2h14z"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6z"/></svg>',
  caret: '<svg class="caret" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
  auto: '<svg viewBox="0 0 24 24"><path d="M12 6v3l4-4-4-4v3a8 8 0 0 0-6.76 12.26l1.46-1.46A6 6 0 0 1 12 6m6.76 1.74L17.3 9.2A6 6 0 0 1 12 18v-3l-4 4 4 4v-3a8 8 0 0 0 6.76-12.26"/></svg>',
};

let cfg = {}, list = [], cur = null, sel = null, pollT = null, saveT = null;
const collapsed = new Set();
let showDetails = (() => { try { return localStorage.getItem("be.details") === "1"; } catch { return false; } })();

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = s => s == null || s === "" || isNaN(s) ? "" : `${String(Math.floor(s / 60)).padStart(2, "0")}:${(s % 60).toFixed(1).padStart(4, "0")}`;
const parseT = v => { v = String(v).trim(); if (!v) return null; let s = 0; for (const p of v.split(":")) { const n = parseFloat(p); if (isNaN(n)) return null; s = s * 60 + n; } return s; };
const n2 = v => (v || 0).toFixed(2);
const inr = v => "₹" + ((v || 0) < 10 ? (v || 0).toFixed(2) : Math.round(v).toLocaleString("en-IN"));
const kt = v => v >= 1000 ? (v / 1000).toFixed(1) + "k" : String(v || 0);
const LVL = { error: { i: "●", t: "Error" }, warn: { i: "▲", t: "Check" }, info: { i: "i", t: "Note" } };
const worst = iss => iss.some(i => i.level === "error") ? "error" : iss.some(i => i.level === "warn") ? "warn" : iss.length ? "info" : "";
let issuesOnly = false;
const codeColor = c => CODE_COLORS[c] || CODE_COLORS[(c || "")[0]] || "#64748b";
const api = async (url, opt = {}) => { const r = await fetch(url, opt); if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText); return r.json(); };
function toast(msg, err = false) { const t = document.createElement("div"); t.className = "toast" + (err ? " err" : ""); t.textContent = msg; $("#toasts").appendChild(t); setTimeout(() => t.remove(), err ? 6000 : 2600); }
const statusLabel = s => ({ ready: "Ready", error: "Error", processing: "Analysing", uploaded: "Queued" }[s] || s);

/* ---------------- sidebar ---------------- */
async function loadConfig() {
  cfg = await api("/api/config");
  $("#cfg").innerHTML = `AI model <b>${esc(cfg.model)}</b><br>${cfg.seconds_per_index} s / index` +
    (cfg.has_key ? "" : `<br><span style="color:#ff6b6b">GEMINI_API_KEY missing in .env</span>`);
}
async function loadList() {
  list = await api("/api/studies");
  renderSideList();
  if (!location.hash.startsWith("#/s/") && $("#recent")) renderDashboard(false);
}
function renderSideList() {
  const q = $("#filter").value.trim().toLowerCase();
  const items = list.filter(s => !q || (s.title || "").toLowerCase().includes(q) || (s.study_by || "").toLowerCase().includes(q));
  $("#slist").innerHTML = items.map(s => `<li><a href="#/s/${s.id}" class="${cur && cur.id === s.id ? "on" : ""}">
      <div class="t"><span class="dot ${s.status}"></span>${esc(s.title || "Untitled study")}</div>
      <div class="s">${esc(s.date)}${s.status === "ready" ? ` · ${n2(s.cycle_min)} min` : ` · ${statusLabel(s.status)}`}</div></a></li>`).join("")
    || `<li class="s" style="padding:8px 10px;color:var(--side-mute)">${q ? "No match" : "No studies yet"}</li>`;
}
$("#filter").addEventListener("input", renderSideList);

/* ---------------- router ---------------- */
function route() {
  clearTimeout(pollT);
  const m = location.hash.match(/^#\/s\/([a-z0-9]+)/i);
  $$(".nav a").forEach(a => a.classList.toggle("on", (a.dataset.nav === "dash" && (!location.hash || location.hash === "#/")) || (a.dataset.nav === "new" && location.hash === "#/new")));
  if (m) return openStudy(m[1]);
  cur = null; renderSideList();
  renderDashboard(true);
  if (location.hash === "#/new") setTimeout(() => $("#upload")?.scrollIntoView({ behavior: "smooth" }), 50);
}
window.addEventListener("hashchange", route);

/* ---------------- dashboard ---------------- */
function renderDashboard(full) {
  const ready = list.filter(s => s.status === "ready");
  const vid = ready.reduce((a, s) => a + s.video_min, 0), cyc = ready.reduce((a, s) => a + s.cycle_min, 0);
  const eff = vid ? Math.round(cyc / vid * 100) : 0;
  const spend = list.reduce((a, s) => a + (s.cost_inr || 0), 0), aiStudies = list.filter(s => s.ai_runs).length;
  const approved = ready.filter(s => s.approved_by).length;
  const kpis = `
    <div class="card kpi red"><div class="lbl">Studies</div><div class="val">${list.length}</div><div class="sub">${ready.length} ready · ${list.filter(s => s.status === "processing" || s.status === "uploaded").length} in progress</div></div>
    <div class="card kpi blue"><div class="lbl">Video analysed</div><div class="val">${vid.toFixed(1)}<small>min</small></div><div class="sub">across ready studies</div></div>
    <div class="card kpi orange"><div class="lbl">MOST standard time</div><div class="val">${cyc.toFixed(1)}<small>min</small></div><div class="sub">sum of cycle times</div></div>
    <div class="card kpi green"><div class="lbl">Avg. method efficiency</div><div class="val">${eff}<small>%</small></div><div class="meter"><i style="width:${Math.min(eff, 100)}%"></i></div></div>
    <div class="card kpi cost"><div class="lbl">AI spend (total)</div><div class="val">${inr(spend)}</div><div class="sub">${aiStudies ? `avg ${inr(spend / aiStudies)} / study · ${vid ? inr(spend / vid) : "—"} / video-min` : "no AI runs yet"}</div></div>
    <div class="card kpi grey"><div class="lbl">Expert approved</div><div class="val">${approved}<small>/ ${ready.length}</small></div><div class="sub">${ready.length - approved} draft report(s)</div></div>`;
  const rows = list.map(s => `<tr class="click" data-href="#/s/${s.id}">
      <td><b>${esc(s.title || "Untitled study")}</b><div class="muted" style="font-size:12px">${esc(s.study_by || "—")}</div></td>
      <td>${esc(s.date)}</td><td><span class="chip ${s.status}">${statusLabel(s.status)}</span></td>
      <td class="num">${s.steps || "—"}</td><td class="num">${s.video_min ? n2(s.video_min) : "—"}</td>
      <td class="num"><b>${s.status === "ready" ? n2(s.cycle_min) : "—"}</b></td>
      <td class="num">${s.status === "ready" && s.video_min ? Math.round(s.cycle_min / s.video_min * 100) + "%" : "—"}</td>
      <td>${s.status !== "ready" ? "—" : s.approved_by ? `<span class="chip ready" title="Approved by ${esc(s.approved_by)}">✓ Approved</span>` : `<span class="chip ${s.errors ? "error" : "uploaded"}">${s.verified}/${s.steps} checked</span>`}</td>
      <td class="num">${s.ai_runs ? inr(s.cost_inr) : "—"}</td>
      <td class="num">${s.status === "ready" ? `<a class="btn sm" href="/api/studies/${s.id}/excel" onclick="event.stopPropagation()">${ICON.xls} Excel</a>` : ""}</td></tr>`).join("");
  const table = list.length ? `<table class="tbl"><thead><tr><th>Process</th><th>Date</th><th>Status</th><th class="num">Steps</th><th class="num">Video (min)</th><th class="num">MOST (min)</th><th class="num">Efficiency</th><th>Expert check</th><th class="num">AI cost</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
    : `<div class="empty-state">No studies yet. Upload your first video above.</div>`;

  if (!full && $("#dash-kpis")) { $("#dash-kpis").innerHTML = kpis; $("#recent").innerHTML = table; return; }
  $("#view").innerHTML = `<div class="page">
    <div class="hero"><div><h1>Video Time Study</h1><div class="muted">Upload a shop-floor video. Bulls Eye splits it into MOST steps, indexes every step and builds your Method Steps report.</div></div></div>
    <div class="kpis" id="dash-kpis">${kpis}</div>
    <div class="grid2">
      <form id="upload" class="card upload">
        <label class="drop" id="drop">
          <input type="file" name="file" accept=".mp4,.mts,.m2ts,.mov,.avi,.mkv" required>
          <span class="ic">${ICON.up}</span>
          <b>Drop a video here or click to browse</b>
          <span class="muted">MP4 · MTS · M2TS · MOV — straight from the camera</span>
          <span class="fileinfo" id="fileinfo"></span>
        </label>
        <div class="row2">
          <label class="field">Process name<input name="title" placeholder="e.g. CS PRE BENDING-1"></label>
          <label class="field">Study done by<input name="study_by" placeholder="Engineer name"></label>
        </div>
        <label class="field">Hint for the AI <span style="font-weight:400">(optional — what happens in the video)</span>
          <textarea name="hint" rows="2" placeholder="Operator engages magnetic tackle, lifts sheet with crane pendant, walks to stand, then brushes the surface"></textarea></label>
        <div class="progress" id="prog" hidden><i></i></div>
        <button class="btn primary lg" type="submit">${ICON.up} Upload &amp; analyse</button>
      </form>
      <div class="card how"><h3>How it works</h3><ol>
        <li><span class="n">1</span><div><b>Upload</b><span>MP4 or MTS from any camera or phone.</span></div></li>
        <li><span class="n">2</span><div><b>Convert</b><span>Deinterlaced and compressed on this PC to keep AI cost low.</span></div></li>
        <li><span class="n">3</span><div><b>AI breaks down the method</b><span>Every operation and sub-operation with timestamps, steps and distances.</span></div></li>
        <li><span class="n">4</span><div><b>MOST index &amp; review</b><span>Rules engine assigns codes and indexes. You verify against the video.</span></div></li>
        <li><span class="n">5</span><div><b>Export</b><span>Method Steps report in Excel with live formulas.</span></div></li>
      </ol></div>
    </div>
    <div class="card"><div class="card-head"><h3>Recent studies</h3><span class="muted" style="font-size:12px">${list.length} total</span></div><div id="recent">${table}</div></div>
  </div>`;
  bindUpload();
}
$("#view").addEventListener("click", e => { const tr = e.target.closest("tr[data-href]"); if (tr && !e.target.closest("a")) location.hash = tr.dataset.href; });

function bindUpload() {
  const form = $("#upload"), drop = $("#drop"), input = $("input[type=file]", form);
  const showFile = () => { const f = input.files[0]; $("#fileinfo").textContent = f ? `${f.name} · ${(f.size / 1048576).toFixed(1)} MB` : ""; };
  input.addEventListener("change", showFile);
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => { if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; showFile(); } });
  form.addEventListener("submit", e => {
    e.preventDefault();
    if (!input.files.length) return toast("Choose a video first", true);
    const btn = $("button[type=submit]", form), prog = $("#prog"), bar = $("i", prog);
    btn.disabled = true; prog.hidden = false;
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/studies");
    xhr.upload.onprogress = ev => { if (ev.lengthComputable) { const p = Math.round(ev.loaded / ev.total * 100); bar.style.width = p + "%"; btn.textContent = `Uploading… ${p}%`; } };
    xhr.onload = async () => {
      btn.disabled = false; prog.hidden = true;
      if (xhr.status >= 300) { btn.innerHTML = `${ICON.up} Upload &amp; analyse`; return toast("Upload failed: " + xhr.responseText, true); }
      const s = JSON.parse(xhr.responseText); toast("Uploaded — analysis started");
      await loadList(); location.hash = `#/s/${s.id}`;
    };
    xhr.onerror = () => { btn.disabled = false; btn.innerHTML = `${ICON.up} Upload &amp; analyse`; toast("Upload failed — is the server running?", true); };
    xhr.send(new FormData(form));
  });
}

/* ---------------- study page ---------------- */
async function openStudy(id) {
  try { cur = await api(`/api/studies/${id}`); } catch { toast("Study not found", true); location.hash = "#/"; return; }
  sel = null; renderSideList();
  $("#view").innerHTML = `<div class="page">
    <div class="crumb"><a href="#/">Dashboard</a> / Study</div>
    <div class="study-head">
      <div>
        <input class="title-input" data-k="title" placeholder="Process name">
        <div class="meta"><span class="chip" id="st-chip"></span>
          <span>Study by <input data-k="study_by" placeholder="Engineer"></span>
          <span>Date <input data-k="date" placeholder="DD/MM/YYYY" style="width:110px"></span>
          <span id="ai-meta"></span></div>
      </div>
      <div class="head-actions">
        <span class="savestate" id="savestate"></span>
        <button class="btn danger" data-a="delete">${ICON.del} Delete</button>
        <button class="btn" data-a="reprocess">${ICON.redo} Re-run AI</button>
        <a class="btn primary" id="xls" href="/api/studies/${id}/excel">${ICON.xls} Export Excel</a>
      </div>
    </div>
    <div id="stage"></div>
    <div class="kpis" id="kpis"></div>
    <div id="review"></div>
    <div class="work" id="work">
      <div class="leftcol">
        <div class="card video-card">
          <video preload="metadata" controls playsinline></video>
          <div class="vbar">
            <span class="tc" id="tc">00:00.0 <small>/ 00:00.0</small></span>
            <div class="seg-btns" id="speed"><button data-r="0.25">¼×</button><button data-r="0.5">½×</button><button data-r="1" class="on">1×</button><button data-r="2">2×</button></div>
            <button class="btn sm" data-a="setstart" title="Set selected step START to current video time  [ key">⇤ Start</button>
            <button class="btn sm" data-a="setend" title="Set selected step END to current video time  ] key">End ⇥</button>
          </div>
          <div class="timeline">
            <div class="tl-head"><span>Step timeline</span><span id="tl-info"></span></div>
            <div class="track" id="track"><div class="playhead" id="ph"></div></div>
            <div class="tl-scale"><span>00:00</span><span id="tl-end"></span></div>
          </div>
          <div class="kbd-help"><kbd>Space</kbd> play/pause · <kbd>,</kbd> <kbd>.</kbd> ±0.1 s · <kbd>[</kbd> <kbd>]</kbd> set start/end · <kbd>↑</kbd> <kbd>↓</kbd> prev/next step · <kbd>V</kbd> verify &amp; next · <kbd>F</kbd> flag fault</div>
        </div>
        <div class="card card-body"><h3>Time by MOST code</h3><div class="stack" id="stack"></div><div class="legend" id="legend"></div></div>
      </div>
      <div class="card table-card">
        <div class="card-head"><h3>Method steps</h3>
          <div style="display:flex;gap:14px;align-items:center">
            <label class="switch"><input type="checkbox" id="issuesOnly" ${issuesOnly ? "checked" : ""}> Only steps to check</label>
            <label class="switch"><input type="checkbox" id="details" ${showDetails ? "checked" : ""}> MOST parameters</label>
          </div></div>
        <div class="tablewrap"><table class="grid" id="grid"></table></div>
        <div class="add-op"><button class="btn sm" data-a="addop">${ICON.plus} Add operation</button></div>
      </div>
    </div></div>`;

  $$(".study-head input[data-k]").forEach(inp => {
    inp.value = cur[inp.dataset.k] || "";
    inp.addEventListener("change", () => { cur[inp.dataset.k] = inp.dataset.k === "date" ? inp.value : inp.value.toUpperCase(); inp.value = cur[inp.dataset.k]; save(); });
  });
  $("#issuesOnly").addEventListener("change", e => { issuesOnly = e.target.checked; renderTable(); });
  $("#details").addEventListener("change", e => { showDetails = e.target.checked; try { localStorage.setItem("be.details", showDetails ? "1" : "0"); } catch {} renderTable(); });
  $("#speed").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; vid().playbackRate = +b.dataset.r; $$("#speed button").forEach(x => x.classList.toggle("on", x === b)); });
  $("#track").addEventListener("click", e => {
    const sg = e.target.closest(".sg");
    if (sg) return selectStep(+sg.dataset.oi, +sg.dataset.si, true);
    const r = e.currentTarget.getBoundingClientRect(); const d = duration();
    if (d && vid().src) vid().currentTime = (e.clientX - r.left) / r.width * d;
  });
  const v = vid();
  if (cur.proxy_file) v.src = `/api/studies/${id}/video`;
  v.addEventListener("timeupdate", onTime);
  v.addEventListener("loadedmetadata", () => { renderTimeline(); onTime(); });
  render();
  if (cur.status === "processing" || cur.status === "uploaded") pollT = setTimeout(() => poll(id), 3000);
}
const vid = () => $("#work video");
const duration = () => (vid() && isFinite(vid().duration) && vid().duration) || cur.video_duration_s || 0;
const allSteps = () => cur.operations.flatMap((op, oi) => op.steps.map((s, si) => ({ s, oi, si })));

async function poll(id) {
  if (!cur || cur.id !== id) return;
  try {
    const s = await api(`/api/studies/${id}`);
    if (s.status !== cur.status || s.proxy_file !== cur.proxy_file) { await loadList(); if (s.status === "ready") toast("Analysis complete ✓"); if (s.status === "error") toast("Analysis failed", true); return openStudy(id); }
  } catch {}
  pollT = setTimeout(() => poll(id), 3000);
}

function render() { renderHead(); renderStage(); renderKpis(); renderReview(); renderTimeline(); renderBreakdown(); renderTable(); }

function renderReview() {
  const el = $("#review");
  if (cur.status !== "ready" && !cur.operations.length) { el.innerHTML = ""; return; }
  const a = cur.audit || {}, [ok, why] = cur.can_approve || [false, ""];
  const pct = a.steps ? Math.round(a.verified / a.steps * 100) : 0;
  const found = [];
  (cur.issues || []).forEach(i => found.push({ ...i, where: "Whole study", oi: -1 }));
  cur.operations.forEach((op, oi) => op.steps.forEach((s, si) => s.issues.forEach(i => { if (i.level !== "info") found.push({ ...i, where: `${op.opn_no}.${si + 1} ${s.description}`, oi, si }); })));
  found.sort((x, y) => (x.level === "error" ? 0 : 1) - (y.level === "error" ? 0 : 1));
  const appr = cur.approved_by
    ? `<div class="appr ok"><div><b>✓ Approved by ${esc(cur.approved_by)}</b><span>${esc(cur.approved_at)} · Excel is stamped "VERIFIED BY"</span></div><button class="btn sm" data-a="unapprove">Withdraw approval</button></div>`
    : `<div class="appr"><div><b>Expert approval</b><span>${ok ? "All steps verified — ready to approve" : esc(why)}</span></div>
        <input id="apprName" placeholder="Expert name" value="${esc(cur.study_by || "")}"><button class="btn primary sm" data-a="approve" ${ok ? "" : "disabled"}>Approve study</button></div>`;
  el.innerHTML = `<div class="card review">
    <div class="rv-top">
      <div class="rv-prog"><div class="lbl">Expert verification <b>${a.verified || 0} / ${a.steps || 0}</b> steps checked</div>
        <div class="meter big"><i style="width:${pct}%"></i></div>
        <div class="rv-chips">
          <span class="chip error" title="Must be fixed before approval">● ${a.errors || 0} errors</span>
          <span class="chip uploaded" title="Likely wrong — look at the video">▲ ${a.warnings || 0} to check</span>
          <span class="chip" title="AI said it was unsure">◐ ${a.low_conf || 0} low confidence</span>
          <span class="chip" title="Expert flagged">⚑ ${a.flagged || 0} flagged</span>
        </div></div>
      ${appr}
    </div>
    ${found.length ? `<details class="rv-list" ${found.length <= 6 ? "open" : ""}><summary>${found.length} finding(s) from the automatic fault finder — click one to jump to it</summary>
      <ul>${found.slice(0, 60).map(f => `<li class="${f.level}" ${f.oi >= 0 ? `data-a="goto" data-oi="${f.oi}" data-si="${f.si}"` : ""}><span class="lv">${LVL[f.level].i}</span><b>${esc(f.where)}</b><span>${esc(f.msg)}</span></li>`).join("")}</ul></details>`
      : `<div class="rv-clean">✓ The automatic fault finder found no problems. The expert must still watch and verify each step.</div>`}
  </div>`;
}

function renderHead() {
  const c = $("#st-chip"); c.className = "chip " + cur.status; c.textContent = statusLabel(cur.status);
  $("#ai-meta").innerHTML = cur.status === "ready" && cur.tokens_in ?`<span title="Tokens in / out">AI ${esc(cur.model)} · ${(cur.tokens_in / 1000).toFixed(1)}k / ${(cur.tokens_out / 1000).toFixed(1)}k tokens</span>` : "";
  $("#xls").style.display = cur.operations.length ? "" : "none";
}

function renderStage() {
  const st = $("#stage");
  if (cur.status === "ready") { st.innerHTML = ""; $("#work").style.display = ""; return; }
  const busy = cur.status === "processing" || cur.status === "uploaded";
  const stage = cur.status === "uploaded" ? 1 : !cur.proxy_file ? 1 : 2;
  const steps = [["Uploaded", "Video received"], ["Converting", "Deinterlace & compress"], ["AI analysis", "Finding MOST steps"], ["Ready", "Review & export"]];
  st.innerHTML = `<div class="card stage">
    <h3>${busy ? "Analysing video…" : "Analysis stopped"}</h3>
    <div class="muted" style="font-size:13px">${busy ? "This usually takes 1–3 minutes. You can leave this page — it keeps running." : "Fix the problem below, then click Re-run AI."}</div>
    <div class="stepper">${steps.map(([l, sub], i) => {
      const cls = i < stage || (!busy && i < stage) ? "done" : i === stage && busy ? "now" : "";
      return `<div class="stp ${cls}"><span class="c">${i < stage ? "✓" : i + 1}</span><span class="l">${l}<small>${sub}</small></span>${i < 3 ? '<span class="bar"></span>' : ""}</div>`;
    }).join("")}</div>
    ${cur.status === "error" ? `<div class="errbox">⚠ ${esc(cur.error)}</div>` : ""}</div>`;
  $("#work").style.display = cur.operations.length || cur.proxy_file ? "" : "none";
}

function renderKpis() {
  const vm = cur.video_duration_s / 60, cm = cur.total_cycle_time_s / 60, diff = vm - cm;
  const eff = vm ? Math.round(cm / vm * 100) : 0;
  const steps = allSteps(), off = steps.filter(x => x.s.offline).reduce((a, x) => a + x.s.cycle_time, 0) / 60;
  $("#kpis").innerHTML = `
    <div class="card kpi blue"><div class="lbl">Video time</div><div class="val">${vm ? n2(vm) : "—"}<small>min</small></div><div class="sub">${fmt(cur.video_duration_s) || "—"} recorded</div></div>
    <div class="card kpi orange"><div class="lbl">MOST cycle time</div><div class="val">${cm ? n2(cm) : "—"}<small>min</small></div><div class="sub">${cur.total_cycle_time_s.toFixed(1)} s standard</div></div>
    ${vm && cm && diff < 0
      ? `<div class="card kpi red" title="Your factor is ${cfg.seconds_per_index} s per index (standard MOST = 0.36 s), so MOST time can exceed fast real work"><div class="lbl">MOST over video</div><div class="val">+${n2(-diff)}<small>min</small></div><div class="sub">MOST time exceeds the video — check indexes or Sec/Index (${cfg.seconds_per_index})</div></div>`
      : `<div class="card kpi red"><div class="lbl">Non-value / waste</div><div class="val">${vm && cm ? n2(diff) : "—"}<small>min</small></div><div class="sub">${vm && cm ? Math.round(diff / vm * 100) + "% of video" : "video − MOST"}</div></div>`}
    <div class="card kpi green"><div class="lbl">Method efficiency</div><div class="val">${eff || "—"}<small>${eff ? "%" : ""}</small></div><div class="meter"><i style="width:${Math.min(eff, 100)}%"></i></div></div>
    <div class="card kpi cost" title="Gemini ${esc(cur.model)} · ₹${cfg.usd_inr}/USD · input $${cfg.price_in}/M, output+thinking $${cfg.price_out}/M tokens"><div class="lbl">AI cost of this study</div>
      <div class="val">${cur.ai_runs || cur.ai_cached ? inr(cur.cost_inr) : "—"}</div>
      <div class="sub">${cur.ai_cached ? `<b>saved AI result reused · ₹0 · identical to earlier analysis</b><br>` : ""}${cur.ai_runs ? `${cur.ai_runs} run${cur.ai_runs > 1 ? "s" : ""} · ${vm ? inr(cur.cost_inr / vm) : "—"} per video-min<br>last run: ${kt(cur.tokens_in)} in · ${kt(cur.tokens_out)} out · ${kt(cur.tokens_think)} thinking` : "no AI run yet"}</div></div>
    <div class="card kpi grey"><div class="lbl">Method steps</div><div class="val">${steps.length}<small>steps</small></div><div class="sub">${cur.operations.length} operations · ${n2(off)} min off-line</div></div>`;
}

function renderTimeline() {
  const d = duration(), track = $("#track");
  if (!track) return;
  $$(".sg", track).forEach(x => x.remove());
  $("#tl-end").textContent = fmt(d).slice(0, 5);
  if (!d) return;
  const frag = document.createDocumentFragment();
  for (const { s, oi, si } of allSteps()) {
    if (s.start_s == null) continue;
    const end = s.end_s != null && s.end_s > s.start_s ? s.end_s : s.start_s + 0.5;
    const el = document.createElement("div");
    el.className = "sg" + (sel && sel.oi === oi && sel.si === si ? " sel" : "");
    el.dataset.oi = oi; el.dataset.si = si;
    el.style.left = (s.start_s / d * 100) + "%"; el.style.width = Math.max((end - s.start_s) / d * 100, 0.3) + "%";
    el.style.background = codeColor(s.code);
    el.title = `${cur.operations[oi].opn_no}.${si + 1} ${s.description}\n${s.code} ${s.index} · ${fmt(s.start_s)} → ${fmt(s.end_s)}`;
    frag.appendChild(el);
  }
  track.appendChild(frag);
  const covered = allSteps().reduce((a, { s }) => a + (s.end_s != null && s.start_s != null ? Math.max(0, s.end_s - s.start_s) : 0), 0);
  $("#tl-info").textContent = `${Math.round(covered / d * 100)}% of video covered`;
}

function renderBreakdown() {
  const by = {};
  for (const { s } of allSteps()) by[s.code || "?"] = (by[s.code || "?"] || 0) + s.cycle_time;
  const total = Object.values(by).reduce((a, b) => a + b, 0);
  const ent = Object.entries(by).sort((a, b) => b[1] - a[1]);
  $("#stack").innerHTML = total ? ent.map(([c, v]) => `<i style="width:${v / total * 100}%;background:${codeColor(c)}" title="${esc(c)} ${v.toFixed(1)} s"></i>`).join("") : "";
  $("#legend").innerHTML = total ? ent.map(([c, v]) => `<div><span class="sw" style="background:${codeColor(c)}"></span><b>${esc(c)}</b><span class="muted">${CODE_NAMES[c] || ""}</span><span class="v">${Math.round(v / total * 100)}%</span></div>`).join("")
    : `<span class="muted">No steps yet</span>`;
}

function renderTable() {
  const D = showDetails;
  const cols = 8 + (D ? 11 : 0);
  const head = `<tr><th class="c">#</th><th class="c" title="Automatic fault finder + AI confidence">Check</th><th>Sub-operation</th><th>Activity</th><th class="c">Start</th><th class="c">End</th>
    ${D ? `<th class="c">Steps min</th><th class="c">Steps max</th><th class="c">Dist (in)</th><th class="c">Heavy</th><th>Difficulty</th><th title="Tool Use data-card column">Tool</th><th class="c" title="Turns / strokes / cuts / sq ft / digits ...">Count</th><th class="c">Freq</th><th class="c">Div</th><th class="c">Men</th>` : ""}
    <th class="c">Code</th><th class="c">Index</th><th class="r">Cycle s</th>${D ? `<th class="c">Off-line</th>` : ""}<th class="c" title="Expert: V = verified, F = flag fault">Expert</th></tr>`;
  const inp = (oi, si, k, v, cls = "n") => `<td class="${cls}"><input data-oi="${oi}" data-si="${si}" data-k="${k}" value="${esc(v)}"></td>`;
  let rows = "";
  cur.operations.forEach((op, oi) => {
    const isC = collapsed.has(oi);
    rows += `<tr class="op ${isC ? "collapsed" : ""}"><td colspan="${cols + 1}"><div class="op-line">
      <button class="icon-btn" data-a="toggle" data-oi="${oi}" title="Collapse / expand">${ICON.caret}</button>
      <span class="op-no">${op.opn_no}</span>
      <input data-oi="${oi}" data-k="name" value="${esc(op.name)}">
      <span class="op-stat">${op.steps.length} steps · video ${op.video_time.toFixed(1)} s</span>
      <span class="op-ct" title="MOST cycle time">${op.cycle_time.toFixed(1)} s</span>
      <button class="icon-btn" data-a="addstep" data-oi="${oi}" title="Add step">${ICON.plus}</button>
      <button class="icon-btn del" data-a="delop" data-oi="${oi}" title="Delete operation">${ICON.del}</button>
    </div></td></tr>`;
    if (isC) return;
    op.steps.forEach((s, si) => {
      const w = worst(s.issues || []);
      if (issuesOnly && s.review === "ok" && w !== "error") return;
      const on = sel && sel.oi === oi && sel.si === si ? " sel" : "";
      const tip = (s.issues || []).map(i => `${LVL[i.level].t}: ${i.msg}`).join("\n") + (s.note ? `\nExpert note: ${s.note}` : "");
      rows += `<tr class="step${on} rv-${s.review || "none"}" data-oi="${oi}" data-si="${si}">
        <td class="idx">${si + 1}</td>
        <td class="c chk" title="${esc(tip || "No automatic findings")}">${w ? `<span class="lvl ${w}">${LVL[w].i}</span>` : `<span class="lvl none">✓</span>`}${s.confidence === "low" || s.confidence === "medium" ? `<span class="conf ${s.confidence}" title="AI confidence: ${s.confidence}">${s.confidence === "low" ? "◐" : "◑"}</span>` : ""}</td>
        <td class="desc"><input list="phrases" data-oi="${oi}" data-si="${si}" data-k="description" value="${esc(s.description)}"></td>
        <td class="act"><select data-oi="${oi}" data-si="${si}" data-k="activity">${Object.entries(ACT).map(([k, l]) => `<option value="${k}" ${k === s.activity ? "selected" : ""}>${l}</option>`).join("")}</select></td>
        ${inp(oi, si, "start_s", fmt(s.start_s), "t")}${inp(oi, si, "end_s", fmt(s.end_s), "t")}
        ${D ? `${inp(oi, si, "walk_steps_min", s.walk_steps_min ?? "")}${inp(oi, si, "walk_steps_max", s.walk_steps_max ?? "")}${inp(oi, si, "distance_in", s.distance_in ?? "")}
          <td class="c"><input type="checkbox" class="tog" data-oi="${oi}" data-si="${si}" data-k="heavy" ${s.heavy ? "checked" : ""}></td>
          <td><select data-oi="${oi}" data-si="${si}" data-k="difficulty">${DIFFS.map(d => `<option ${d === s.difficulty ? "selected" : ""}>${d}</option>`).join("")}</select></td>
          <td><select data-oi="${oi}" data-si="${si}" data-k="tool_action"><option value="">—</option>${(cfg.tools || []).map(t => `<option value="${t}" ${t === s.tool_action ? "selected" : ""}>${t.replace(/_/g, " ").toLowerCase()}</option>`).join("")}</select></td>
          ${inp(oi, si, "tool_count", s.tool_count ?? "")}
          ${inp(oi, si, "freq", s.freq)}${inp(oi, si, "div_freq", s.div_freq)}${inp(oi, si, "men", s.men)}` : ""}
        <td class="c"><span class="code ${s.manual ? "manual" : ""}" style="--cc:${codeColor(s.code)}"><input data-oi="${oi}" data-si="${si}" data-k="code" value="${esc(s.code)}"></span></td>
        ${inp(oi, si, "index", s.index, "n" + (s.manual ? " manual" : ""))}
        <td class="r ct">${s.cycle_time.toFixed(1)}</td>
        ${D ? `<td class="c"><input type="checkbox" class="tog" data-oi="${oi}" data-si="${si}" data-k="offline" ${s.offline ? "checked" : ""}></td>` : ""}
        <td style="white-space:nowrap">
          <button class="rv-btn ok ${s.review === "ok" ? "on" : ""}" data-a="verify" data-oi="${oi}" data-si="${si}" title="Verified — matches the video (key V)">✓</button><button class="rv-btn flag ${s.review === "flag" ? "on" : ""}" data-a="flag" data-oi="${oi}" data-si="${si}" title="${s.review === "flag" ? esc("Flagged: " + s.note + " — click to clear") : "Flag a fault (key F)"}">⚑</button>${s.manual ? `<button class="icon-btn" data-a="auto" data-oi="${oi}" data-si="${si}" title="Back to automatic MOST index">${ICON.auto}</button>` : ""}<button class="icon-btn del" data-a="delstep" data-oi="${oi}" data-si="${si}" title="Delete step">${ICON.x}</button></td>
      </tr>`;
    });
  });
  if (!cur.operations.length) rows = `<tr><td colspan="${cols + 1}" class="empty-state">${cur.status === "ready" ? "No steps found. Add an operation manually or re-run the AI with a hint." : "Steps will appear here when the AI finishes."}</td></tr>`;
  const g = $("#grid");
  g.innerHTML = `<thead>${head}</thead><tbody>${rows}</tbody>`;
  if (!$("#phrases")) document.body.insertAdjacentHTML("beforeend", `<datalist id="phrases">${PHRASES.map(p => `<option value="${esc(p)}">`).join("")}</datalist>`);
  g.onchange = onEdit;
}

function selectStep(oi, si, seek) {
  sel = { oi, si };
  $$("#grid tr.step.sel, #track .sg.sel").forEach(x => x.classList.remove("sel"));
  const tr = $(`#grid tr.step[data-oi="${oi}"][data-si="${si}"]`);
  if (tr) { tr.classList.add("sel"); tr.scrollIntoView({ block: "nearest", behavior: "smooth" }); }
  $(`#track .sg[data-oi="${oi}"][data-si="${si}"]`)?.classList.add("sel");
  const s = cur.operations[oi]?.steps[si];
  if (seek && s && s.start_s != null && vid().src) vid().currentTime = s.start_s;
}

let lastPlaying = "";
function onTime() {
  const v = vid(), d = duration(), t = v.currentTime || 0;
  $("#tc").innerHTML = `${fmt(t)} <small>/ ${fmt(d)}</small>`;
  if (d) $("#ph").style.left = (t / d * 100) + "%";
  const hit = allSteps().find(({ s }) => s.start_s != null && s.end_s != null && t >= s.start_s && t < s.end_s);
  const key = hit ? `${hit.oi}-${hit.si}` : "";
  if (key !== lastPlaying) {
    lastPlaying = key;
    $$("#grid tr.step.playing").forEach(x => x.classList.remove("playing"));
    if (hit) $(`#grid tr.step[data-oi="${hit.oi}"][data-si="${hit.si}"]`)?.classList.add("playing");
  }
}

function onEdit(e) {
  const el = e.target, k = el.dataset.k, oi = +el.dataset.oi;
  if (!k) return;
  if (el.dataset.si === undefined) { cur.operations[oi][k] = el.value.toUpperCase(); return save(); }
  const s = cur.operations[oi].steps[+el.dataset.si];
  let v = el.type === "checkbox" ? el.checked : el.value;
  if (k === "start_s" || k === "end_s") v = parseT(v);
  else if (k === "walk_steps_min" || k === "walk_steps_max") v = v === "" ? null : parseInt(v);
  else if (k === "distance_in" || k === "tool_count") v = v === "" ? null : parseFloat(v);
  else if (k === "tool_action") v = v || null;
  else if (k === "freq" || k === "div_freq") v = parseFloat(v) || 1;
  else if (k === "index" || k === "men") v = parseInt(v) || 0;
  else if (k === "description" || k === "code") v = String(v).toUpperCase();
  s[k] = v;
  if (k === "code" || k === "index") s.manual = true;
  if (AUTO_KEYS.has(k)) s.manual = false;
  save();
}

$("#view").addEventListener("click", e => {
  if (!cur || !$("#grid")) return;
  const b = e.target.closest("[data-a]");
  const tr = e.target.closest("tr.step");
  if (tr && !b && !e.target.matches("input,select")) return selectStep(+tr.dataset.oi, +tr.dataset.si, true);
  if (tr && e.target.matches("input,select") && !b) { sel = { oi: +tr.dataset.oi, si: +tr.dataset.si }; return; }
  if (!b) return;
  const a = b.dataset.a, oi = +b.dataset.oi, si = +b.dataset.si, v = vid();
  const blank = () => ({ description: "NEW STEP", activity: "WALK", start_s: v.src ? +v.currentTime.toFixed(1) : null, end_s: null,
    walk_steps_min: null, walk_steps_max: null, distance_in: null, heavy: false, difficulty: "simple", tool_action: null, tool_count: null, oprt: "3",
    freq: 1, div_freq: 1, men: 1, offline: false, manual: false, code: "", index: 0, cycle_time: 0,
    confidence: "manual", review: "", note: "", issues: [] });
  switch (a) {
    case "reprocess":
    {
      const force = e.shiftKey;
      if (!confirm(force
        ? "NEW AI analysis (Shift held): Gemini is called again and costs money. Your manual edits will be replaced. Continue?"
        : "Re-run the analysis? If the video and AI settings are unchanged, the saved AI result is reused: identical steps, ₹0.\n(Shift+click Re-run AI to force a new paid analysis.)\nYour manual edits will be replaced.")) return;
      const fd = new FormData(); if (force) fd.append("force", "true");
      api(`/api/studies/${cur.id}/reprocess`, { method: "POST", body: fd }).then(() => { toast(force ? "New AI analysis started" : "Analysis restarted"); loadList(); openStudy(cur.id); });
    }
      return;
    case "delete":
      if (!confirm("Delete this study and its video permanently?")) return;
      api(`/api/studies/${cur.id}`, { method: "DELETE" }).then(async () => { toast("Study deleted"); cur = null; await loadList(); location.hash = "#/"; });
      return;
    case "setstart": case "setend": return setTime(a === "setstart" ? "start_s" : "end_s");
    case "toggle": collapsed.has(oi) ? collapsed.delete(oi) : collapsed.add(oi); return renderTable();
    case "addstep": cur.operations[oi].steps.push(blank()); collapsed.delete(oi); return save();
    case "delstep": cur.operations[oi].steps.splice(si, 1); sel = null; return save();
    case "auto": cur.operations[oi].steps[si].manual = false; return save();
    case "verify": return review(oi, si, "ok");
    case "flag": return review(oi, si, "flag");
    case "goto": collapsed.delete(oi); if (issuesOnly) { issuesOnly = false; $("#issuesOnly").checked = false; } renderTable(); return selectStep(oi, si, true);
    case "approve": {
      const name = $("#apprName").value.trim();
      if (!name) return toast("Enter the expert's name", true);
      api(`/api/studies/${cur.id}/approve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) })
        .then(s => { cur = s; render(); loadList(); toast("Study approved ✓ — Excel now stamped VERIFIED"); }).catch(err => toast(err.message, true));
      return;
    }
    case "unapprove":
      api(`/api/studies/${cur.id}/unapprove`, { method: "POST" }).then(s => { cur = s; render(); loadList(); toast("Approval withdrawn"); });
      return;
    case "addop": cur.operations.push({ opn_no: 0, name: "NEW OPERATION", steps: [blank()], cycle_time: 0, video_time: 0 }); return save();
    case "delop": if (confirm(`Delete operation ${cur.operations[oi].opn_no} and its ${cur.operations[oi].steps.length} steps?`)) { cur.operations.splice(oi, 1); sel = null; save(); } return;
  }
});

function review(oi, si, kind) {
  const s = cur.operations[oi]?.steps[si]; if (!s) return;
  sel = { oi, si };
  if (kind === "ok") { s.review = s.review === "ok" ? "" : "ok"; if (s.review === "ok") s.note = ""; }
  else if (s.review === "flag") { s.review = ""; s.note = ""; }
  else {
    const note = prompt(`What is wrong with step ${cur.operations[oi].opn_no}.${si + 1}?\n"${s.description}"`, s.note || "");
    if (note === null) return;
    s.review = "flag"; s.note = note.trim() || "Fault found";
  }
  save();
}

function setTime(k) {
  if (!sel) return toast("Click a step row first", true);
  const s = cur.operations[sel.oi]?.steps[sel.si]; if (!s) return;
  s[k] = +vid().currentTime.toFixed(1); s.manual = false;
  toast(`${k === "start_s" ? "Start" : "End"} set to ${fmt(s[k])}`); save();
}

async function save() {
  clearTimeout(saveT);
  $("#savestate").textContent = "Saving…";
  try {
    const body = { title: cur.title, study_by: cur.study_by, date: cur.date, operations: cur.operations };
    cur = await api(`/api/studies/${cur.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    renderHead(); renderKpis(); renderReview(); renderTimeline(); renderBreakdown(); renderTable();
    if (sel) selectStep(sel.oi, sel.si, false);
    $("#savestate").textContent = "✓ All changes saved";
    saveT = setTimeout(() => { if ($("#savestate")) $("#savestate").textContent = ""; }, 2500);
    const li = list.find(x => x.id === cur.id); if (li) { li.title = cur.title; li.cycle_min = cur.total_cycle_time_s / 60; renderSideList(); }
  } catch (err) { $("#savestate").textContent = ""; toast("Save failed: " + err.message, true); }
}

document.addEventListener("keydown", e => {
  if (!cur || !$("#grid") || e.target.matches("input,textarea,select") || e.ctrlKey || e.metaKey || e.altKey) return;
  const v = vid(); if (!v || !v.src) return;
  if (e.key === " ") { e.preventDefault(); v.paused ? v.play() : v.pause(); }
  else if (e.key === ",") v.currentTime = Math.max(0, v.currentTime - 0.1);
  else if (e.key === ".") v.currentTime += 0.1;
  else if ((e.key === "v" || e.key === "V") && sel) {
    // verify and jump to next step — fast expert review loop
    review(sel.oi, sel.si, "ok");
    const all = allSteps(), i = all.findIndex(x => x.oi === sel.oi && x.si === sel.si);
    if (i >= 0 && i < all.length - 1 && cur.operations[sel.oi].steps[sel.si].review === "ok") setTimeout(() => selectStep(all[i + 1].oi, all[i + 1].si, true), 150);
  }
  else if ((e.key === "f" || e.key === "F") && sel) review(sel.oi, sel.si, "flag");
  else if (e.key === "[") setTime("start_s");
  else if (e.key === "]") setTime("end_s");
  else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const all = allSteps(); if (!all.length) return;
    let i = sel ? all.findIndex(x => x.oi === sel.oi && x.si === sel.si) : -1;
    i = e.key === "ArrowDown" ? Math.min(all.length - 1, i + 1) : Math.max(0, i - 1);
    selectStep(all[i].oi, all[i].si, true);
  }
});

loadConfig(); loadList().then(route);
setInterval(() => { if (!cur) loadList().catch(() => {}); }, 8000);
