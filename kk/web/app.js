// Kharcha Kavach mobile web app. Plain JavaScript, no build step.
// Every rupee figure shown comes from the server's figure store or official tables;
// this script never calculates or invents an amount.
"use strict";

const I18N = window.KK_I18N;
const SPEECH = { en: "en-IN", hi: "hi-IN", kn: "kn-IN", gu: "gu-IN", ta: "ta-IN", te: "te-IN" };
const LANG_NAME = { en: "English", hi: "हिन्दी", kn: "ಕನ್ನಡ", gu: "ગુજરાતી", ta: "தமிழ்", te: "తెలుగు" };
const COV_COLOR = { rule: "#2F7DE1", pending: "#8A93BB", basic: "#D8CFA8" };
const SECTIONS = ["implant", "pharmacy", "consumables", "room", "procedure", "diagnostics", "other"];
const VERDICT_ORDER = { red: 0, grey: 1, amber: 2, info: 3, green: 4 };
const VERDICT_COLOR = { red: "#D1253B", amber: "#F0A202", grey: "#6E7691", green: "#178A5A" };

const $ = (id) => document.getElementById(id);
const state = {
  lang: localStorage.getItem("kk_lang") || "en",
  step: 1, mode: "photo", files: [], lines: [], billChanged: true,
  answers: { state: "karnataka" }, session: null, limits: null, filter: "all", letterLang: {},
  voice: { lang: null, script: null, token: 0, mode: null, playing: false, paused: false, idx: -1 },
};
if (!I18N[state.lang]) state.lang = "en";

const t = (k) => (I18N[state.lang] && I18N[state.lang][k]) || I18N.en[k] || k;
const LOCALE = SPEECH;
// dates from the server are ISO strings; show them the way people write them (no new numbers are made)
function day(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(LOCALE[state.lang], { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(y, m - 1, d)));
}

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false)
    e.append(kid instanceof Node ? kid : document.createTextNode(kid));
  return e;
}

function toast(msg) {
  const box = $("toast");
  box.textContent = msg;
  box.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => box.classList.remove("show"), 2200);
}

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `${r.status} ${r.statusText}`);
  }
  return r.json();
}

// text segments from the server: {t} or {fig, t}; figures open the proof sheet
function segs(list) {
  const span = el("span");
  for (const s of list) span.append(s.fig ? el("button", { class: "fig", type: "button", onclick: () => showProof(s.fig) }, s.t) : s.t);
  return span;
}

/* ------------------------------------------------------------------ language */
function applyUI() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-t]").forEach((n) => { n.textContent = t(n.dataset.t); });
  document.querySelectorAll("[data-chip]").forEach((n) => { n.textContent = t(n.dataset.chip); });
  document.querySelectorAll(".langs button").forEach((b) => b.classList.toggle("on", b.dataset.lang === state.lang));
  $("treatment").placeholder = t("treat_ph");
  buildTriToggles();
  renderLines();
  renderLimits();
}

async function setLang(lang) {
  state.lang = lang;
  localStorage.setItem("kk_lang", lang);
  applyUI();
  if (state.session) {
    state.session = await api(`/api/audit/${state.session.id}?lang=${lang}`);
    if (state.savState && state.session.schemes && state.session.schemes.applies && state.savState !== state.session.schemes.state) {
      const r = await api(`/api/audit/${state.session.id}/schemes?state=${encodeURIComponent(state.savState)}&lang=${lang}`);
      Object.assign(state.session.proofs, r.proofs);
      state.session.schemes = r.schemes;
    }
    renderResult(false);
  }
}

/* ------------------------------------------------------------------ steps */
function showStep(n) {
  state.step = n;
  $("step-1").hidden = n !== 1;
  $("step-2").hidden = n !== 2;
  $("step-3").hidden = n !== 3;
  $("loading").hidden = true;
  $("hero").hidden = n !== 1;
  document.querySelectorAll("#steps li").forEach((li) => {
    const s = Number(li.dataset.step);
    li.classList.toggle("on", s === n);
    li.classList.toggle("done", s < n);
  });
  $("dis-wrap").hidden = state.mode === "type";
  window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

function setMode(mode) {
  state.mode = mode;
  state.billChanged = true;
  document.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  $("mode-photo").hidden = mode !== "photo";
  $("mode-type").hidden = mode !== "type";
  if (mode === "type" && !state.lines.length) addLine();
}

/* ------------------------------------------------------------------ files */
function addFiles(list) {
  for (const f of list) {
    if (/^image\//.test(f.type) || f.type === "application/pdf" || /\.pdf$/i.test(f.name)) state.files.push(f);
  }
  state.billChanged = true;
  renderThumbs();
}

function renderThumbs() {
  const box = $("thumbs");
  box.innerHTML = "";
  state.files.forEach((f, i) => {
    const isPdf = f.type === "application/pdf" || /\.pdf$/i.test(f.name);
    const preview = isPdf ? el("div", { class: "pdf" }, "PDF") : el("img", { src: URL.createObjectURL(f), alt: f.name });
    box.append(el("div", { class: "thumb" }, preview, el("span", { class: "n" }, String(i + 1)),
      el("button", { class: "x", type: "button", "aria-label": `${t("remove")} ${i + 1}`,
        onclick: () => { state.files.splice(i, 1); state.billChanged = true; renderThumbs(); } }, "✕")));
  });
}

/* ------------------------------------------------------------------ typed bill */
function addLine() {
  state.lines.push({ description: "", section: "other", qty: "", rate: "", amount: "" });
  state.billChanged = true;
  renderLines();
  const inputs = document.querySelectorAll(".line-row .item input");
  inputs[inputs.length - 1]?.focus();
}

function renderLines() {
  const box = $("lines");
  if (!box) return;
  box.innerHTML = "";
  state.lines.forEach((ln, i) => {
    const input = (key, label, mode) => el("label", { class: key === "description" ? "item" : "" }, t(label),
      el("input", { type: "text", inputmode: mode, value: ln[key], autocomplete: "off",
        oninput: (e) => { ln[key] = e.target.value; state.billChanged = true; } }));
    const chips = el("div", { class: "sec-chips" }, SECTIONS.map((s) => el("button", {
      type: "button", class: ln.section === s ? "on" : "",
      onclick: () => { ln.section = s; state.billChanged = true; renderLines(); } }, t("sec_" + s))));
    box.append(el("div", { class: "line-row" },
      input("description", "col_item", "text"),
      el("button", { class: "del", type: "button", "aria-label": t("remove"),
        onclick: () => { state.lines.splice(i, 1); state.billChanged = true; renderLines(); } }, "✕"),
      el("div", { class: "sec" }, chips),
      input("qty", "col_qty", "decimal"), input("rate", "col_rate", "decimal"), input("amount", "col_amount", "decimal")));
  });
}

/* ------------------------------------------------------------------ official limits (real data) */
async function loadLimits() {
  try { state.limits = await api("/api/limits"); } catch { state.limits = null; }
  renderLimits();
}

function renderLimits() {
  const box = $("limits");
  if (!box) return;
  box.innerHTML = "";
  const L = state.limits;
  if (!L) return;
  const gst = L.gst ? `${t("plus_gst")} ${L.gst.rate}%` : "";
  const colors = { stent_des: "#E0457B", stent_bms: "#2F7DE1" };
  for (const s of L.stents) {
    box.append(el("button", { type: "button", class: "lim", style: `--c:${colors[s.key]}`, onclick: () => showLimit(s, t(s.key === "stent_des" ? "lim_des" : "lim_bms")) },
      el("span", {}, t(s.key === "stent_des" ? "lim_des" : "lim_bms")),
      el("b", {}, s.display),
      el("small", {}, [gst, s.valid_to ? `${t("valid_till")} ${day(s.valid_to)}` : ""].filter(Boolean).join(", "))));
  }
  if (L.knee.length) {
    const kneeTo = L.knee[0].valid_to;
    box.append(el("button", { type: "button", class: "lim", style: "--c:#178A5A", onclick: showKnee },
      el("span", {}, t("lim_knee")),
      el("b", {}, `${L.knee.length} ${t("knee_parts")}`),
      el("small", {}, [gst, kneeTo ? `${t("valid_till")} ${day(kneeTo)}` : ""].filter(Boolean).join(", "))));
  }
}

function sourceBlock(src, heading) {
  return el("div", { class: "src" }, el("b", {}, heading),
    el("div", {}, src.title), el("div", { class: "role" }, src.ref),
    src.url ? el("a", { href: src.url, target: "_blank", rel: "noopener" }, t("open_source")) : null);
}

function showLimit(item, name) {
  const body = $("proof-body");
  body.innerHTML = "";
  body.append(el("h3", {}, name), el("div", { class: "big" }, item.display),
    el("div", { class: "role" }, [t("per_unit"), state.limits.gst ? `${t("plus_gst")} ${state.limits.gst.rate}%` : "",
      item.valid_to ? `${t("valid_till")} ${day(item.valid_to)}` : ""].filter(Boolean).join(", ")),
    sourceBlock(item.source, t("lim_source")));
  if (state.limits.gst) body.append(sourceBlock(state.limits.gst.source, "GST"));
  $("proof").showModal();
}

function showKnee() {
  const body = $("proof-body");
  body.innerHTML = "";
  const list = el("div", { class: "knee-list" });
  for (const k of state.limits.knee) {
    const label = `${k.system} · ${k.component.replace(/_/g, " ")} · ${k.material.replace(/_/g, " ")}`;
    list.append(el("button", { type: "button", onclick: () => showLimit(k, label) }, el("span", {}, label), el("b", {}, k.display)));
  }
  body.append(el("h3", {}, t("lim_knee")), list);
  $("proof").showModal();
}

/* ------------------------------------------------------------------ step 2 */
function buildTriToggles() {
  document.querySelectorAll(".yn").forEach((row) => {
    const name = row.dataset.name;
    const seg = row.querySelector(".seg");
    seg.innerHTML = "";
    for (const [v, label] of [["true", "yes"], ["false", "no"], ["", "dk"]]) {
      const cur = state.answers[name];
      const on = (v === "" && (cur === undefined || cur === null)) || String(cur) === v;
      seg.append(el("button", { type: "button", "data-v": v, class: on ? "on" : "",
        onclick: () => { if (v === "") delete state.answers[name]; else state.answers[name] = v === "true"; buildTriToggles(); } }, t(label)));
    }
  });
}

function choosePayer(p) {
  state.answers.payer = p;
  document.querySelectorAll("#payers button").forEach((b) => b.classList.toggle("on", b.dataset.payer === p));
  $("scheme-qs").hidden = !["pmjay", "state_scheme"].includes(p);
}

async function findPackages(text) {
  const box = $("packages");
  box.innerHTML = "";
  if (!text.trim()) return;
  try {
    const res = await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: state.lang }) });
    if (res.refused) { box.append(el("p", { class: "hint" }, res.message)); return; }
    if (!res.packages.length) { box.append(el("p", { class: "hint" }, t("no_packages"))); return; }
    box.append(el("p", { class: "hint" }, t("choose_pkg")));
    for (const p of res.packages) {
      box.append(el("button", { type: "button", class: "pkg" + (state.answers.package_code === p.procedure_code ? " on" : ""),
        onclick: () => { state.answers.package_code = p.procedure_code; findPackages(text); } }, `${p.procedure_code} · ${p.procedure_name}`));
    }
  } catch (e) { box.append(el("p", { class: "hint" }, e.message)); }
}

function startMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { $("treatment").focus(); return; }
  const rec = new SR();
  rec.lang = SPEECH[state.lang];
  rec.interimResults = false;
  $("mic").classList.add("live");
  rec.onresult = (e) => { const text = e.results[0][0].transcript; $("treatment").value = text; findPackages(text); };
  rec.onend = () => $("mic").classList.remove("live");
  rec.start();
}

function collectAnswers() {
  const a = { ...state.answers, language: state.lang };
  a.medicine_qty_in_dosage_units = $("tablets").checked || undefined;
  if (state.mode === "photo" && $("discharge").value) a.service_date = $("discharge").value;
  Object.keys(a).forEach((k) => (a[k] === undefined || a[k] === "") && delete a[k]);
  return a;
}

function typedBill() {
  return {
    header: { hospital_name: $("t-hospital").value || null, admission_date: $("t-adm").value || null,
      discharge_date: $("t-dis").value || null },
    lines: state.lines.filter((l) => l.description.trim() && l.amount.trim()).map((l) => ({
      description: l.description.trim(), section: l.section === "other" ? null : l.section,
      qty: l.qty.replace(/[^\d.]/g, "") || null, rate: l.rate.replace(/[^\d.]/g, "") || null,
      amount: l.amount.replace(/[^\d.]/g, "") })),
  };
}

/* ------------------------------------------------------------------ run the check */
async function runCheck() {
  const answers = collectAnswers();
  $("step-2").hidden = true;
  $("loading").hidden = false;
  $("check").disabled = true;
  try {
    if (state.session && !state.billChanged) {
      state.session = await api(`/api/audit/${state.session.id}/answers?lang=${state.lang}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answers }) });
    } else if (state.mode === "photo") {
      const fd = new FormData();
      state.files.forEach((f) => fd.append("files", f));
      fd.append("answers", JSON.stringify(answers));
      fd.append("lang", state.lang);
      state.session = await api("/api/audit", { method: "POST", body: fd });
    } else {
      state.session = await api(`/api/audit-structured?lang=${state.lang}`, { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bill: typedBill(), answers }) });
    }
    state.billChanged = false;
    state.filter = "all";
    showStep(3);
    renderResult(true);
  } catch (e) {
    $("loading").hidden = true;
    $("step-2").hidden = false;
    toast(t("err_server") + e.message);
  } finally {
    $("check").disabled = false;
  }
}

/* ------------------------------------------------------------------ result */
function renderResult(animate) {
  const s = state.session;
  if (animate) state.savState = null;   // a new check starts from the state chosen on the form
  // the seal: recoverable amount (red findings only) or a clear stamp
  const seal = $("seal");
  seal.innerHTML = "";
  seal.className = "seal";
  if (s.recoverable_fig) {
    seal.append(el("small", {}, t("res_refund")),
      el("strong", {}, el("button", { class: "fig", type: "button", onclick: () => showProof(s.recoverable_fig) }, s.proofs[s.recoverable_fig].display)));
  } else {
    seal.classList.add("clear");
    seal.append(el("strong", {}, t("res_none")));
  }
  if (!animate) seal.style.animation = "none";
  const ask = $("ask-amount");
  ask.innerHTML = "";
  if (s.amber_total_fig) ask.append(`${t("res_ask")}: `, el("button", { class: "fig", type: "button", onclick: () => showProof(s.amber_total_fig) }, s.proofs[s.amber_total_fig].display));

  // line verdict bar and legend
  const counts = { red: 0, amber: 0, grey: 0, green: 0 };
  s.lines.forEach((l) => { if (l.verdict in counts) counts[l.verdict] += 1; });
  const total = s.lines.length || 1;
  const bar = $("bar"), legend = $("legend");
  bar.innerHTML = ""; legend.innerHTML = "";
  for (const v of ["red", "grey", "amber", "green"]) {
    if (counts[v]) bar.append(el("span", { style: `width:${(counts[v] / total) * 100}%;background:${VERDICT_COLOR[v]}` }));
    legend.append(el("li", {}, el("i", { style: `background:${VERDICT_COLOR[v]}` }), t("legend_" + v), el("b", {}, String(counts[v]))));
  }

  renderRemedy();
  renderSavings();
  renderCoverage();
  resetVoice();
  resetChat();
  resetGuard();
  renderConfirm();
  renderReceipt(animate);
  renderPhoto();
  renderFindings();
  if (animate) { state.insRows = null; state.insCashless = ""; }
  renderLetters(); renderCalls(); renderInsurance();
  $("explain").innerHTML = "";
  $("report").href = `/api/audit/${s.id}/report?lang=${state.lang}`;

  const reds = s.findings.filter((f) => f.verdict === "red").length;
  const tab = document.querySelector('[data-tab="findings"]');
  tab.querySelector(".count")?.remove();
  if (reds) tab.append(el("span", { class: "count" }, String(reds)));
}

function renderConfirm() {
  const s = state.session;
  const box = $("confirm-lines");
  box.innerHTML = "";
  $("confirm").hidden = !s.needs_confirmation.length;
  for (const lid of s.needs_confirmation) {
    const line = s.lines.find((l) => l.id === lid);
    const row = el("div", { class: "cline", "data-line": lid }, el("b", {}, line.description));
    row.append(el("img", { src: `/api/audit/${s.id}/line/${lid}.png`, alt: "", class: "line-crop", onerror: (e) => {
      e.target.remove();
      if (line.amount) row.insertBefore(el("img", { src: `/api/audit/${s.id}/crop/${line.amount}.png`, alt: "" }), row.children[1]);
    } }));
    for (const key of ["qty", "rate", "amount"]) {
      row.append(el("label", {}, t("f_" + key), el("input", { type: "text", inputmode: "decimal", "data-key": key,
        value: (line.values && line.values[key]) || "" })));
    }
    box.append(row);
  }
}

function findingsFor(lineId) {
  return state.session.findings.filter((f) => f.line_id === lineId && f.verdict !== "green")
    .sort((a, b) => VERDICT_ORDER[a.verdict] - VERDICT_ORDER[b.verdict]);
}

function renderReceipt(animate) {
  const s = state.session;
  const r = $("receipt");
  r.innerHTML = "";
  r.classList.toggle("stamped", !!animate);
  const h = s.header;
  r.append(el("div", { class: "r-head" }, el("h3", {}, h.hospital_name || t("tab_bill")),
    (h.admission_date || h.discharge_date) ? el("p", {}, `${day(h.admission_date) || "…"} – ${day(h.discharge_date) || "…"}`) : null));
  let section = undefined, i = 0;
  for (const line of s.lines) {
    if (line.section !== section) {
      section = line.section;
      r.append(el("div", { class: "r-sec" }, t("sec_" + (SECTIONS.includes(section) ? section : "other"))));
    }
    const d = line.display || {};
    const meta = d.qty && d.rate ? `${d.qty} × ${d.rate}` : "";
    const detail = el("div", { class: "r-detail", hidden: true });
    const fs = findingsFor(line.id);
    for (const f of fs) detail.append(el("p", {}, el("b", {}, f.title + ": "), segs(f.text)));
    const mt = line.match || {};
    if (mt.status) {
      const box = el("div", { class: "match" }, el("b", {}, t("match_title")), " ",
        el("span", { class: `m-chip ${mt.status}` }, t("m_" + mt.status)));
      for (const r of mt.reasons || []) box.append(el("p", {}, segs(r)));
      detail.append(box);
    }
    const stamp = ["red", "amber", "grey"].includes(line.verdict)
      ? el("span", { class: `stamp ${line.verdict}`, style: `--i:${i++}` }, t("legend_" + line.verdict)) : null;
    const btn = el("button", { type: "button", class: `r-line ${line.verdict}`, "aria-expanded": "false",
      onclick: () => {
        detail.hidden = !detail.hidden;
        btn.classList.toggle("open", !detail.hidden);
        btn.setAttribute("aria-expanded", String(!detail.hidden));
      } },
      el("i", { class: "cov", style: `background:${COV_COLOR[(line.match || {}).status] || "transparent"}`, "aria-hidden": "true" }),
      el("span", { class: "d" }, line.description), el("span", { class: "m" }, meta),
      el("span", { class: "a" }, d.amount || ""), stamp);
    r.append(btn, detail);
  }
  if (s.total_display) r.append(el("div", { class: "r-total" }, el("span", {}, t("total_label")),
    el("button", { class: "fig", type: "button", onclick: () => showProof(s.total_fig) }, s.total_display)));
}

function renderPhoto() {
  const s = state.session;
  const views = $("bill-views"), box = $("photo-view");
  views.hidden = !s.pages;
  box.innerHTML = "";
  if (!s.pages) { setBillView("receipt"); return; }
  for (let p = 1; p <= s.pages; p++) {
    const wrap = el("div", { class: "page" });
    const img = el("img", { src: `/api/audit/${s.id}/page/${p}.png`, alt: `${t("tab_bill")} ${p}` });
    img.onload = () => {
      const sx = img.clientWidth / img.naturalWidth, sy = img.clientHeight / img.naturalHeight;
      for (const l of s.lines) {
        if (!l.bbox || l.bbox.page !== p) continue;
        wrap.append(el("div", { class: `box ${l.verdict}`, title: l.description,
          style: `left:${l.bbox.x0 * sx}px;top:${l.bbox.y0 * sy}px;width:${(l.bbox.x1 - l.bbox.x0) * sx}px;height:${(l.bbox.y1 - l.bbox.y0) * sy}px` }));
      }
    };
    wrap.append(img);
    box.append(wrap);
  }
}

function setBillView(v) {
  document.querySelectorAll("#bill-views button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  $("receipt").hidden = v !== "receipt";
  $("photo-view").hidden = v !== "photo";
}

function renderFindings() {
  const s = state.session;
  const filters = $("filters"), box = $("findings");
  filters.innerHTML = ""; box.innerHTML = "";
  const present = ["red", "grey", "amber", "info", "green"].filter((v) => s.findings.some((f) => f.verdict === v));
  for (const v of ["all", ...present]) {
    const n = v === "all" ? s.findings.length : s.findings.filter((f) => f.verdict === v).length;
    filters.append(el("button", { type: "button", class: state.filter === v ? "on" : "",
      onclick: () => { state.filter = v; renderFindings(); } },
      `${t(v === "all" ? "f_all" : v === "info" ? "f_info" : "legend_" + v)} (${n})`));
  }
  const list = s.findings.filter((f) => state.filter === "all" || f.verdict === state.filter)
    .sort((a, b) => VERDICT_ORDER[a.verdict] - VERDICT_ORDER[b.verdict]);
  if (!list.length) { box.append(el("p", { class: "empty" }, t("empty_findings"))); return; }
  for (const f of list) {
    box.append(el("article", { class: `finding ${f.verdict}` },
      el("header", {}, el("span", { class: `stamp ${f.verdict}` }, f.verdict_label), el("h4", {}, f.title),
        el("span", { class: "law" }, f.legal_label)),
      el("p", {}, segs(f.text)),
      f.conditions.map((c) => el("p", { class: "cond" }, c)),
      f.asks.map((a) => el("p", { class: "todo" }, a)),
      f.verdict === "red" && f.excess_fig ? el("button", { type: "button", class: "ghost card-btn",
        onclick: () => shareCard(f.excess_fig) }, t("card_btn")) : null,
      (f.basis || []).map((b) => el("p", { class: "basis" },
        el("b", {}, t("basis") + ": "), el("span", { lang: "en", class: "q" }, b.quote),
        " \u2014 ", b.url ? el("a", { href: b.url, target: "_blank", rel: "noopener" }, b.title) : b.title,
        b.ref ? `, ${b.ref}` : ""))));
  }
}

async function renderCalls() {
  const box = $("call-list");
  box.innerHTML = "";
  const list = await api(`/api/audit/${state.session.id}/calls?lang=${state.lang}`);
  $("calls").hidden = !list.length;
  const audio = $("call-audio");
  for (const c of list) {
    const play = el("button", { type: "button", class: "primary" }, t("call_listen"));
    play.onclick = () => {
      if (!audio.paused && audio.dataset.who === c.who) { audio.pause(); play.textContent = t("call_listen"); return; }
      audio.dataset.who = c.who;
      audio.src = `/api/audit/${state.session.id}/calls/${c.who}/audio?lang=${c.lang}`;
      audio.play().catch(() => toast(t("err_server")));
      play.textContent = t("v_stop");
      audio.onended = () => { play.textContent = t("call_listen"); };
    };
    box.append(el("details", { class: "call-script", open: c === list[0] },
      el("summary", {}, el("b", {}, t(`call_who_${c.who}`)),
        c.phone ? el("a", { class: "call", href: `tel:${c.phone}` }, `\u260e ${c.phone}`) : null),
      el("ol", {}, c.sentences.map((s) => el("li", {}, segs(s)))),
      el("div", { class: "btns" }, play,
        el("button", { type: "button", class: "ghost", onclick: async () => {
          await navigator.clipboard.writeText(c.text); toast(t("copied")); } }, t("copy")))));
  }
}

async function renderLetters() {
  const box = $("letters");
  box.innerHTML = "";
  const list = await api(`/api/audit/${state.session.id}/letters?lang=${state.lang}`);
  if (!list.length) { box.append(el("li", {}, el("p", { class: "empty" }, t("no_letters")))); return; }
  list.forEach((l, idx) => {
    const langs = Object.keys(l.letters);
    const cur = state.letterLang[l.channel] && l.letters[state.letterLang[l.channel]] ? state.letterLang[l.channel] : langs[0];
    const ta = el("textarea", { "aria-label": l.name }, l.letters[cur]);
    const lgButtons = el("div", { class: "lg seg" }, langs.map((lg) => el("button", { type: "button", class: lg === cur ? "on" : "",
      onclick: () => { state.letterLang[l.channel] = lg; renderLetters(); } }, lg.toUpperCase())));
    const file = () => {
      const blob = new Blob([ta.value], { type: "text/plain;charset=utf-8" });
      const a = el("a", { href: URL.createObjectURL(blob), download: `kharcha-kavach-${l.channel}-${cur}.txt` });
      document.body.append(a); a.click(); a.remove();
    };
    box.append(el("li", {}, el("details", { class: "letter", open: idx === 0 },
      el("summary", {}, el("b", {}, l.name),
        el("div", { class: "meta" },
          l.phone ? el("a", { class: "call", href: `tel:${l.phone.replace(/[^\d+]/g, "")}` }, `☎ ${t("call")} ${l.phone}`) : null,
          l.url ? el("a", { class: "web", href: l.url, target: "_blank", rel: "noopener" }, l.url.replace(/^https?:\/\//, "")) : null)),
      el("div", { class: "body" }, lgButtons, ta,
        el("div", { class: "btns" },
          el("button", { type: "button", class: "ghost", onclick: async () => { await navigator.clipboard.writeText(ta.value); toast(t("copied")); } }, t("copy")),
          el("button", { type: "button", class: "ghost", onclick: file }, t("download"))),
        sendBar(l, cur, ta), trackerBox(l.channel)))));
  });
}

// ---------------------------------------------------------------- complaint tracker (kk/tracker.py)
// The dates stay in this browser (localStorage); the server only computes the timeline.
const TRK_KEY = (ch) => `kk_trk:${state.session.id}:${ch}`;
function trkLoad(ch) {
  try { return JSON.parse(localStorage.getItem(TRK_KEY(ch))) || { events: {} }; } catch (e) { return { events: {} }; }
}
function trkSave(ch, v) { try { localStorage.setItem(TRK_KEY(ch), JSON.stringify(v)); } catch (e) { /* private mode */ } }

function trackerBox(channel) {
  const ui = state.session.more_ui || {};
  const box = el("details", { class: "tracker" }, el("summary", {}, ui.trk_l_track || "Track"));
  const body = el("div", { class: "trk-body" });
  box.append(body);
  box.addEventListener("toggle", () => { if (box.open && !body.dataset.loaded) drawTracker(channel, body); });
  return box;
}

async function drawTracker(channel, body) {
  const saved = trkLoad(channel);
  let r;
  try {
    r = await api(`/api/audit/${state.session.id}/tracker`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, events: saved.events, cause_on: saved.cause_on || null, lang: state.lang }) });
  } catch (e) { body.innerHTML = ""; body.append(el("p", { class: "hint" }, t("err_server") + e.message)); return; }
  Object.assign(state.session.proofs, r.proofs);
  const p = r.tracker, L = p.labels;
  body.dataset.loaded = "1";
  body.innerHTML = "";
  const redraw = () => { trkSave(channel, saved); drawTracker(channel, body); };
  const dateInput = (value, label, onchange) => {
    const i = el("input", { type: "date", value: value || "", "aria-label": label, max: p.today });
    i.addEventListener("change", () => onchange(i.value || null));
    return el("label", { class: "trk-date" }, el("span", {}, label), i);
  };
  body.append(el("p", { class: "hint" }, segs(p.intro)));
  if (channel === "consumer" || channel === "hospital_desk" || channel === "nppa" || channel === "insurer") {
    body.append(dateInput(saved.cause_on || p.cause_on, L.problem_date, (v) => { saved.cause_on = v; redraw(); }));
  }
  const ol = el("ol", { class: "trk-steps" });
  for (const st of p.steps) {
    const ev = saved.events[st.id] || {};
    const set = (k, v) => { saved.events[st.id] = { ...ev, [k]: v }; if (!v) delete saved.events[st.id][k]; redraw(); };
    const inputs = st.status === "not_needed" ? null : el("div", { class: "trk-inputs" },
      dateInput(ev.sent_on, L.sent, (v) => set("sent_on", v)),
      ev.sent_on ? dateInput(ev.reply_on, L.reply, (v) => set("reply_on", v)) : null,
      ev.reply_on ? el("label", { class: "trk-date" }, el("span", {}, L.outcome), (() => {
        const sel = el("select", { "aria-label": L.outcome },
          el("option", { value: "" }, "—"),
          el("option", { value: "solved", selected: ev.outcome === "solved" ? "selected" : null }, L.solved),
          el("option", { value: "not_solved", selected: ev.outcome === "not_solved" ? "selected" : null }, L.not_solved));
        sel.addEventListener("change", () => set("outcome", sel.value || null));
        return sel;
      })()) : null);
    const links = [];
    if (st.phone) links.push(el("a", { href: `tel:${st.phone.replace(/[^\d+]/g, "")}` }, `☎ ${st.phone}`));
    if (st.url) links.push(el("a", { href: st.url, target: "_blank", rel: "noopener" }, st.url.replace(/^https?:\/\//, "")));
    const basis = st.basis.filter((b) => b.title).map((b) => el("li", { class: b.suggestion ? "sugg" : "" },
      b.url ? el("a", { href: b.url, target: "_blank", rel: "noopener" }, b.title) : b.title, b.ref ? ` — ${b.ref}` : ""));
    ol.append(el("li", { class: `trk-step st-${st.status}` },
      el("h5", {}, st.name),
      st.status_text ? el("p", { class: "trk-status" }, segs(st.status_text)) : null,
      el("p", {}, segs(st.do)),
      ...st.lines.map((ln) => el("p", { class: "trk-line" }, segs(ln))),
      links.length ? el("p", { class: "trk-links" }, ...links) : null,
      inputs,
      basis.length ? el("details", { class: "trk-basis" }, el("summary", {}, L.basis), el("ul", {}, ...basis)) : null));
  }
  body.append(ol, el("p", { class: "hint small" }, segs(p.counted)));
  const btns = el("div", { class: "btns" });
  if (p.calendar.length) {
    btns.append(el("button", { type: "button", class: "ghost", onclick: () => {
      const blob = new Blob([p.ics], { type: "text/calendar;charset=utf-8" });
      const a = el("a", { href: URL.createObjectURL(blob), download: `kharcha-kavach-${channel}.ics` });
      document.body.append(a); a.click(); a.remove();
    } }, L.ics));
  }
  btns.append(el("button", { type: "button", class: "ghost", onclick: () => {
    try { localStorage.removeItem(TRK_KEY(channel)); } catch (e) { /* ignore */ }
    drawTracker(channel, body);
  } }, L.clear));
  body.append(btns);
}

// ---------------------------------------------------------------- insurance deductions (kk/insurance.py)
function renderInsurance() {
  const box = $("insurance"), s = state.session, ui = s.more_ui || {};
  box.innerHTML = "";
  box.open = s.payer === "private_insurance";
  const rows = state.insRows || (state.insRows = [{ item: "", amount: "", reason: "", line_id: "" }]);
  const out = el("div", { class: "ins-out", "aria-live": "polite" });
  const table = el("div", { class: "ins-rows" });
  const drawRows = () => {
    table.innerHTML = "";
    rows.forEach((r, i) => {
      const inp = (k, label, attrs = {}) => {
        const x = el("input", { value: r[k], "aria-label": label, placeholder: label, ...attrs });
        x.addEventListener("input", () => { r[k] = x.value; });
        return x;
      };
      const line = el("select", { "aria-label": ui.ins_l_line },
        el("option", { value: "" }, ui.ins_l_line),
        ...s.lines.map((l) => el("option", { value: l.id, selected: r.line_id === l.id ? "selected" : null },
          `${l.id} · ${l.description.slice(0, 40)}`)));
      line.addEventListener("change", () => { r.line_id = line.value; });
      table.append(el("div", { class: "ins-row" },
        inp("item", ui.ins_l_item), inp("amount", ui.ins_l_amount, { inputmode: "decimal" }),
        inp("reason", ui.ins_l_reason), line,
        el("button", { type: "button", class: "ghost", "aria-label": ui.ins_l_remove,
          onclick: () => { rows.splice(i, 1); if (!rows.length) rows.push({ item: "", amount: "", reason: "", line_id: "" }); drawRows(); } }, "✕")));
    });
  };
  drawRows();
  const cash = el("select", { "aria-label": ui.ins_l_cashless },
    el("option", { value: "" }, ui.ins_l_dk), el("option", { value: "yes" }, ui.ins_l_yes), el("option", { value: "no" }, ui.ins_l_no));
  cash.value = state.insCashless || "";
  cash.addEventListener("change", () => { state.insCashless = cash.value; });
  const check = async () => {
    const deductions = rows.filter((r) => r.amount && (r.item || r.line_id))
      .map((r) => ({ item: r.item, amount: r.amount, reason: r.reason, line_id: r.line_id || null }));
    out.innerHTML = "";
    if (!deductions.length) return out.append(el("p", { class: "hint" }, ui.ins_l_add));
    try {
      const res = await api(`/api/audit/${s.id}/insurance`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deductions, cashless: cash.value === "yes" ? true : cash.value === "no" ? false : null, lang: state.lang }) });
      Object.assign(state.session.proofs, res.proofs);
      const p = res.insurance;
      out.append(...[
        el("ul", { class: "ins-result" }, ...p.rows.map((r) => el("li", { class: `ins-${r.kind}` },
          ...r.lines.map((ln) => el("p", {}, segs(ln))),
          r.listed ? el("p", { class: "ins-listed" }, segs(r.listed)) : null,
          r.source_url ? el("p", { class: "ins-src" }, el("a", { href: r.source_url, target: "_blank", rel: "noopener" }, r.source_title)) : null))),
        p.total ? el("p", { class: "ins-total" }, segs(p.total)) : null,
        p.hospital ? el("p", { class: "ins-hosp" }, segs(p.hospital)) : null,
        p.insurer ? el("p", { class: "ins-ins" }, segs(p.insurer)) : null,
        p.optional ? el("p", { class: "ins-opt" }, segs(p.optional)) : null,
        p.next ? el("p", {}, segs(p.next)) : null,
        p.insurer ? trackerBox("insurer") : null,
        el("p", { class: "hint small" }, segs(p.source))].filter(Boolean));
    } catch (e) { out.append(el("p", { class: "hint" }, t("err_server") + e.message)); }
  };
  box.append(el("summary", {}, el("b", {}, ui.ins_title)),
    el("p", { class: "hint" }, segs(s.ins_intro)), table,
    el("div", { class: "btns" },
      el("button", { type: "button", class: "ghost", onclick: () => { rows.push({ item: "", amount: "", reason: "", line_id: "" }); drawRows(); } }, ui.ins_l_add),
      el("label", { class: "ins-cash" }, el("span", {}, ui.ins_l_cashless), cash),
      el("button", { type: "button", class: "primary", onclick: check }, ui.ins_l_check)),
    out);
}

/* ------------------------------------------------------------------ proof sheet */
function showProof(fid) {
  const s = state.session;
  const p = s.proofs[fid];
  if (!p) return;
  const body = $("proof-body");
  body.innerHTML = "";
  body.append(el("h3", {}, t("proof_title")), el("div", { class: "big" }, p.display));
  if (p.origin === "bill") {
    body.append(el("div", { class: "src" }, el("b", {}, t("proof_bill")),
      el("img", { src: `/api/audit/${s.id}/crop/${fid}.png`, alt: "", onerror: (e) => e.target.remove() })));
  } else if (p.origin === "user_confirmed") {
    body.append(el("div", { class: "src" }, el("b", {}, t("proof_user")), p.note ? el("div", { class: "role" }, p.note) : null));
  }
  if (p.rule) body.append(sourceBlock({ title: p.rule.source_title, ref: p.rule.ref, url: p.rule.source_url }, t("proof_rule")));
  if (p.note && p.origin !== "user_confirmed") body.append(el("div", { class: "pnote" }, p.note));
  if (p.formula) {
    body.append(el("div", { class: "src" }, el("b", {}, t("proof_formula")), el("div", {}, p.formula.text),
      el("div", { class: "inputs" }, p.formula.inputs.map((i) => el("button", { type: "button", onclick: () => showProof(i.id) }, i.display)))));
  }
  if (!$("proof").open) $("proof").showModal();
}

/* ------------------------------------------------------------------ remedies and coverage */
// The first summary line (the total) is on the seal; the rest say who decides each part.
function renderRemedy() {
  const s = state.session, box = $("remedy");
  box.innerHTML = "";
  const kinds = [];
  if (s.remedy.hospital) kinds.push("hospital");
  if (s.remedy.scheme) kinds.push("scheme");
  if (s.remedy.fallback) kinds.push("fallback");
  s.summary.slice(1).forEach((line, i) => box.append(el("p", { class: kinds[i] || "amber" }, segs(line))));
}

// ---------------------------------------------------------------- scheme savings (kk/schemes.py)
// What a government scheme could have paid. Awareness only: never part of the amount to challenge.
function schemeRow(r, labels) {
  const links = [];
  if (r.check_url) links.push(el("a", { href: r.check_url, target: "_blank", rel: "noopener" }, labels.check));
  if (r.phone) links.push(el("a", { href: `tel:${r.phone}` }, `${labels.call} ${r.phone}`));
  if (r.source_url) links.push(el("a", { class: "src", href: r.source_url, target: "_blank", rel: "noopener", title: r.source_title }, labels.source));
  return el("li", { class: "sav-row" + (r.saving_fig ? "" : " no-saving") },
    el("h4", {}, r.name),
    el("p", { class: "sav-line" }, segs(r.line)),
    el("ul", { class: "sav-who" }, ...r.who.map((w) => el("li", {}, segs(w)))),
    r.where ? el("p", { class: "sav-where" }, segs(r.where)) : null,
    r.note ? el("p", { class: "sav-note" }, segs(r.note)) : null,
    links.length ? el("p", { class: "sav-links" }, ...links) : null);
}

function renderSavings() {
  const box = $("savings"), p = (state.session || {}).schemes;
  box.innerHTML = "";
  box.hidden = !p || !p.applies;
  if (box.hidden) return;
  const pick = el("select", { class: "state-select", "aria-label": p.labels.pick_state });
  stateOptions(pick, p.state);
  if (!p.state) pick.prepend(el("option", { value: "", selected: "selected" }, "—"));
  pick.addEventListener("change", async () => {
    state.savState = pick.value;
    const r = await api(`/api/audit/${state.session.id}/schemes?state=${encodeURIComponent(pick.value)}&lang=${state.lang}`);
    Object.assign(state.session.proofs, r.proofs);
    state.session.schemes = r.schemes;
    renderSavings();
    $("savings").querySelector("select").focus();
  });
  const general = p.central.filter((r) => r.general), special = p.central.filter((r) => !r.general);
  box.append(...[
    el("h3", { id: "sav-title" }, p.title),
    p.best ? el("p", { class: "sav-best" }, segs(p.best)) : null,
    el("p", { class: "sav-intro" }, segs(p.intro)),
    p.left_out ? el("p", { class: "hint" }, segs(p.left_out)) : null,
    el("p", { class: "sav-not" }, segs(p.not_counted)),
    el("label", { class: "sav-pick" }, el("span", {}, p.labels.pick_state), pick),
    p.choose_state ? el("p", { class: "hint" }, segs(p.choose_state)) : null,
    p.head_state ? el("h4", { class: "sav-head" }, segs(p.head_state)) : null,
    p.no_state_scheme ? el("p", { class: "hint" }, segs(p.no_state_scheme)) : null,
    p.state_rows.length ? el("ul", { class: "sav-list" }, ...p.state_rows.map((r) => schemeRow(r, p.labels))) : null,
    el("h4", { class: "sav-head" }, segs(p.head_central)),
    el("ul", { class: "sav-list" }, ...general.map((r) => schemeRow(r, p.labels))),
    special.length ? el("details", { class: "sav-more" }, el("summary", {}, p.more),
      el("ul", { class: "sav-list" }, ...special.map((r) => schemeRow(r, p.labels)))) : null,
    el("p", { class: "sav-foot" }, segs(p.conds)),
    el("p", { class: "sav-foot" }, segs(p.have_card)),
    el("p", { class: "sav-foot small" }, segs(p.checked))].filter(Boolean));
}

function renderCoverage() {
  const s = state.session;
  const counts = { rule: 0, pending: 0, basic: 0 };
  s.lines.forEach((l) => { const st = (l.match || {}).status; if (st in counts) counts[st] += 1; });
  const n = s.lines.length || 1, bar = $("cov-bar"), key = $("cov-key"), lines = $("cov-lines");
  bar.innerHTML = ""; key.innerHTML = ""; lines.innerHTML = "";
  for (const k of ["rule", "pending", "basic"]) {
    if (counts[k]) bar.append(el("span", { style: `width:${(counts[k] / n) * 100}%;background:${COV_COLOR[k]}` }));
    if (counts[k]) key.append(el("li", {}, el("i", { style: `background:${COV_COLOR[k]}` }), t("m_" + k)));
  }
  for (const c of s.coverage || []) lines.append(el("p", {}, segs(c)));
  $("coverage").hidden = !(s.coverage || []).length;
}

/* ------------------------------------------------------------------ voice */
// Captions show the exact figures; speech says the same figures in words (built on the server).
function browserVoice(lang) {
  if (!("speechSynthesis" in window)) return null;
  const want = SPEECH[lang].toLowerCase();
  const vs = speechSynthesis.getVoices();
  return vs.find((v) => v.lang.replace("_", "-").toLowerCase() === want)
    || vs.find((v) => v.lang.replace("_", "-").toLowerCase().startsWith(lang + "-")) || null;
}

function renderVoiceLangs() {
  const box = $("v-langs");
  box.innerHTML = "";
  for (const lg of Object.keys(LANG_NAME)) {
    box.append(el("button", { type: "button", lang: lg, class: lg === state.voice.lang ? "on" : "", "aria-pressed": String(lg === state.voice.lang),
      onclick: () => { stopVoice(); state.voice.lang = lg; renderVoiceLangs(); loadVoice(); } }, LANG_NAME[lg]));
  }
}

function resetVoice() {
  stopVoice();
  state.voice.lang = state.lang;
  state.voice.script = null;
  renderVoiceLangs();
  loadVoice();
}

async function loadVoice() {
  const v = state.voice, s = state.session;
  const token = ++v.token;
  v.serverFailed = false;
  $("v-status").textContent = t("v_loading") + "…";
  $("v-captions").innerHTML = "";
  const ai = $("v-ai").checked ? 1 : 0;
  try {
    const script = await api(`/api/audit/${s.id}/voice?lang=${v.lang}&ai=${ai}`);
    if (token !== v.token) return;
    v.script = script;
    const ol = $("v-captions");
    ol.lang = v.lang;
    script.sentences.forEach((sent, i) => ol.append(el("li", { "data-i": String(i) }, segs(sent))));
    voiceStatus();
  } catch (e) {
    $("v-status").textContent = t("err_server") + e.message;
  }
}

function voiceStatus(mode) {
  const v = state.voice;
  if (!v.script) return;
  const src = v.script.source === "llm" ? t("v_src_llm") : t("v_src_template");
  const how = mode || (v.script.server_quality === "natural" ? "server"
    : browserVoice(v.lang) ? "device" : v.script.server_audio ? "server" : "none");
  $("v-status").textContent = `${src} ${t("v_" + how)}.`.replace("..", ".");
}

function highlight(i) {
  state.voice.idx = i;
  document.querySelectorAll("#v-captions li").forEach((li) => li.classList.toggle("on", Number(li.dataset.i) === i));
  const on = document.querySelector("#v-captions li.on");
  if (on) on.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function setPlaying(on) {
  state.voice.playing = on;
  $("v-play").classList.toggle("playing", on && !state.voice.paused);
  $("v-play").setAttribute("aria-label", t(on && !state.voice.paused ? "v_pause" : "v_play"));
}

function playVoice() {
  const v = state.voice;
  if (!v.script) return;
  const audio = $("v-audio");
  if (v.playing) {                       // toggle pause / resume
    v.paused = !v.paused;
    if (v.mode === "device") v.paused ? speechSynthesis.pause() : speechSynthesis.resume();
    if (v.mode === "server") v.paused ? audio.pause() : audio.play();
    return setPlaying(true);
  }
  const rate = Number($("v-rate").value);
  const lines = v.script.speech_lines;
  // a natural server voice beats an unknown device voice; otherwise the device's own voice
  // if the server voice failed once (for example, no internet for the online voice), use the device's
  const voice = v.script.server_quality === "natural" && !v.serverFailed ? null : browserVoice(v.lang);
  const token = ++v.token;
  v.paused = false;
  if (voice) {
    v.mode = "device";
    voiceStatus("device");
    speechSynthesis.cancel();
    const speak = (i) => {
      if (token !== v.token) return;
      if (i >= lines.length) { setPlaying(false); return highlight(-1); }
      if (!lines[i]) return speak(i + 1);
      const u = new SpeechSynthesisUtterance(lines[i]);
      u.voice = voice; u.lang = voice.lang; u.rate = rate;
      u.onstart = () => highlight(i);
      u.onend = () => speak(i + 1);
      u.onerror = () => speak(i + 1);
      speechSynthesis.speak(u);
    };
    setPlaying(true);
    return speak(0);
  }
  if (v.script.server_audio) {
    v.mode = "server";
    voiceStatus("server");
    const ai = $("v-ai").checked ? 1 : 0;
    audio.src = `/api/audit/${state.session.id}/voice.audio?lang=${v.lang}&ai=${ai}`;
    audio.playbackRate = rate;
    // highlight by share of spoken characters: an approximation for captions only, never for numbers
    const lens = lines.map((l) => l.length), total = lens.reduce((a, b) => a + b, 0) || 1;
    audio.ontimeupdate = () => {
      if (!audio.duration) return;
      let at = (audio.currentTime / audio.duration) * total, i = 0;
      while (i < lens.length - 1 && at > lens[i]) { at -= lens[i]; i += 1; }
      if (i !== v.idx) highlight(i);
    };
    audio.onended = () => { setPlaying(false); highlight(-1); };
    const failed = () => {
      setPlaying(false);
      if (token !== v.token) return;
      v.serverFailed = true;
      if (browserVoice(v.lang)) return playVoice();   // fall back to the device's own voice
      voiceStatus("none");
    };
    audio.onerror = failed;
    setPlaying(true);
    return audio.play().catch(failed);
  }
  voiceStatus("none");
}

function stopVoice() {
  const v = state.voice;
  v.token += 1;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  const audio = $("v-audio");
  if (audio) { audio.pause(); audio.removeAttribute("src"); }
  v.paused = false;
  setPlaying(false);
  highlight(-1);
}

/* ------------------------------------------------------------------ explainer chat */
// Answers come from the server, built from this bill's findings; amounts are tappable for proof.
const chat = { audio: new Audio(), token: 0 };

function bubble(kind, paras, lang) {
  const b = el("div", { class: `msg ${kind}`, lang: lang || state.lang });
  for (const p of paras) b.append(el("p", {}, Array.isArray(p) ? segs(p) : p));
  $("chat-log").append(b);
  b.scrollIntoView({ block: "nearest", behavior: "smooth" });
  return b;
}

function renderChips(list) {
  const box = $("chat-chips");
  box.innerHTML = "";
  for (const c of list) box.append(el("button", { type: "button", onclick: () => askChat(c.label, c.id) }, c.label));
}

async function resetChat() {
  chat.token += 1;
  chat.audio.pause();
  $("chat-log").innerHTML = "";
  $("chat-in").placeholder = t("chat_ph");
  $("chat-mic").setAttribute("aria-label", t("chat_mic"));
  try {
    const r = await api(`/api/audit/${state.session.id}/chat?lang=${state.lang}`);
    bubble("bot", r.answer, r.lang);
    renderChips(r.suggestions);
  } catch (e) { /* chat is optional: the rest of the result still works */ }
}

async function askChat(text, intent) {
  if (!text.trim()) return;
  bubble("me", [text]);
  $("chat-in").value = "";
  const wait = bubble("bot", ["…"]);
  try {
    const r = await api(`/api/audit/${state.session.id}/chat`, { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: intent ? null : text, intent: intent || null, lang: state.lang, ai: $("v-ai").checked }) });
    wait.remove();
    const b = bubble("bot", r.answer, r.lang);
    if (r.source === "llm") b.append(el("div", { class: "src" }, t("v_src_llm")));
    renderChips(r.suggestions);
    if ($("chat-voice").checked) speakAnswer(r, b);
  } catch (e) {
    wait.remove();
    bubble("bot", [t("err_server") + e.message]);
  }
}

function speakAnswer(r, b) {
  const token = ++chat.token;
  stopVoice();
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  chat.audio.pause();
  const lines = r.speech_lines.filter(Boolean);
  const done = () => b.classList.remove("speaking");
  b.classList.add("speaking");
  const voice = r.server_quality === "natural" ? null : browserVoice(r.lang);
  if (voice) {
    const go = (i) => {
      if (token !== chat.token || i >= lines.length) return done();
      const u = new SpeechSynthesisUtterance(lines[i]);
      u.voice = voice; u.lang = voice.lang; u.rate = Number($("v-rate").value);
      u.onend = () => go(i + 1); u.onerror = () => go(i + 1);
      speechSynthesis.speak(u);
    };
    return go(0);
  }
  if (r.server_quality === "none") return done();
  chat.audio.src = `/api/audit/${state.session.id}/chat/${r.n}/audio`;
  chat.audio.playbackRate = Number($("v-rate").value);
  chat.audio.onended = done;
  chat.audio.onerror = done;
  chat.audio.play().catch(done);
}

function chatMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return toast(t("v_none"));
  const rec = new SR();
  rec.lang = SPEECH[state.lang];
  rec.interimResults = false;
  $("chat-mic").classList.add("live");
  rec.onresult = (e) => { const said = e.results[0][0].transcript; askChat(said); };
  rec.onend = () => $("chat-mic").classList.remove("live");
  rec.onerror = () => $("chat-mic").classList.remove("live");
  rec.start();
}

/* ------------------------------------------------------------------ confirm, explain, reset */
async function confirmLines() {
  const corrections = {}, confirmed = [];
  document.querySelectorAll("#confirm-lines .cline").forEach((row) => {
    const lid = row.dataset.line;
    confirmed.push(lid);
    const line = state.session.lines.find((l) => l.id === lid);
    row.querySelectorAll("input").forEach((inp) => {
      const v = inp.value.replace(/[^\d.]/g, "");
      if (v && v !== ((line.values || {})[inp.dataset.key] || "")) (corrections[lid] = corrections[lid] || {})[inp.dataset.key] = v;
    });
  });
  state.session = await api(`/api/audit/${state.session.id}/confirm?lang=${state.lang}`, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ corrections, confirmed }) });
  renderResult(true);
}

async function explain() {
  const p = $("explain");
  p.textContent = t("explaining") + "…";
  const r = await api(`/api/audit/${state.session.id}/explain?lang=${state.lang}`);
  p.innerHTML = "";
  p.append(segs(r.segments));
}

function resetAll() {
  stopVoice();
  state.files = []; state.lines = []; state.session = null; state.billChanged = true;
  state.answers = { state: "karnataka" };
  renderThumbs(); renderLines(); buildTriToggles();
  document.querySelectorAll("#payers button").forEach((b) => b.classList.remove("on"));
  $("scheme-qs").hidden = true;
  ["treatment", "discharge", "t-hospital", "t-adm", "t-dis"].forEach((id) => { $(id).value = ""; });
  $("tablets").checked = false;
  $("packages").innerHTML = "";
  setMode("photo");
  showStep(1);
}

/* ------------------------------------------------------------------ wiring */
document.querySelectorAll(".langs button").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
document.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("on", x === b));
  document.querySelectorAll(".tabpanel").forEach((p) => { p.hidden = p.id !== "tab-" + b.dataset.tab; });
}));
document.querySelectorAll("#bill-views button").forEach((b) => b.addEventListener("click", () => setBillView(b.dataset.view)));
document.querySelectorAll("#payers button").forEach((b) => b.addEventListener("click", () => choosePayer(b.dataset.payer)));
// every state and UT (same list as kk/schemes.py STATES); names are proper nouns, kept in English
const STATES = [["andhra_pradesh","Andhra Pradesh"],["arunachal_pradesh","Arunachal Pradesh"],["assam","Assam"],["bihar","Bihar"],
  ["chhattisgarh","Chhattisgarh"],["goa","Goa"],["gujarat","Gujarat"],["haryana","Haryana"],["himachal_pradesh","Himachal Pradesh"],
  ["jharkhand","Jharkhand"],["karnataka","Karnataka"],["kerala","Kerala"],["madhya_pradesh","Madhya Pradesh"],["maharashtra","Maharashtra"],
  ["manipur","Manipur"],["meghalaya","Meghalaya"],["mizoram","Mizoram"],["nagaland","Nagaland"],["odisha","Odisha"],["punjab","Punjab"],
  ["rajasthan","Rajasthan"],["sikkim","Sikkim"],["tamil_nadu","Tamil Nadu"],["telangana","Telangana"],["tripura","Tripura"],
  ["uttar_pradesh","Uttar Pradesh"],["uttarakhand","Uttarakhand"],["west_bengal","West Bengal"],
  ["andaman_nicobar","Andaman and Nicobar Islands"],["chandigarh","Chandigarh"],["dnh_dd","Dadra and Nagar Haveli and Daman and Diu"],
  ["delhi","Delhi"],["jammu_kashmir","Jammu and Kashmir"],["ladakh","Ladakh"],["lakshadweep","Lakshadweep"],["puducherry","Puducherry"]];
function stateOptions(sel, value) {
  sel.innerHTML = "";
  for (const [id, name] of STATES) sel.append(el("option", { value: id, selected: id === value ? "selected" : undefined }, name));
}
stateOptions($("state-select"), state.answers.state);
$("state-select").addEventListener("change", (e) => { state.answers.state = e.target.value; });
document.querySelectorAll("[data-chip]").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("[data-chip]").forEach((x) => x.classList.toggle("on", x === b));
  $("treatment").value = b.textContent;
  findPackages(b.textContent);
}));

const drop = $("drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
$("files").addEventListener("change", (e) => { addFiles(e.target.files); e.target.value = ""; });
$("add-line").addEventListener("click", addLine);

$("to-2").addEventListener("click", () => {
  if (state.mode === "photo" && !state.files.length && !state.session) return toast(t("err_nofile"));
  if (state.mode === "type" && !typedBill().lines.length) return toast(t("err_noline"));
  showStep(2);
});
$("back-1").addEventListener("click", () => showStep(1));
$("check").addEventListener("click", runCheck);
$("treatment").addEventListener("change", (e) => findPackages(e.target.value));
$("mic").addEventListener("click", startMic);
$("confirm-btn").addEventListener("click", confirmLines);
$("explain-btn").addEventListener("click", explain);
$("v-play").addEventListener("click", playVoice);
$("chat-form").addEventListener("submit", (e) => { e.preventDefault(); askChat($("chat-in").value); });
$("chat-mic").addEventListener("click", chatMic);
$("v-stop").addEventListener("click", stopVoice);
$("v-ai").addEventListener("change", () => { stopVoice(); loadVoice(); });
$("v-rate").addEventListener("change", () => { const a = $("v-audio"); a.playbackRate = Number($("v-rate").value); });
if ("speechSynthesis" in window) speechSynthesis.onvoiceschanged = () => { if (state.voice.script && !state.voice.playing) voiceStatus(); };
$("edit").addEventListener("click", () => showStep(2));
$("new").addEventListener("click", resetAll);
$("delete").addEventListener("click", async () => {
  if (state.session) await api(`/api/audit/${state.session.id}`, { method: "DELETE" }).catch(() => {});
  resetAll();
  toast(t("deleted"));
});
$("proof-close").addEventListener("click", () => $("proof").close());
$("proof").addEventListener("click", (e) => { if (e.target === $("proof")) $("proof").close(); });

applyUI();
setMode("photo");
showStep(1);
loadLimits();


/* ------------------------------------------------------------ number guard */
// Lets anyone type the kind of sentence an AI might write and see the same check
// every AI sentence must pass: digits, number words and currency are only allowed inside slots.
async function resetGuard() {
  const out = $("guard-out"), chips = $("guard-chips");
  out.innerHTML = ""; chips.innerHTML = "";
  $("guard-in").placeholder = t("guard_ph");
  const ex = await api(`/api/audit/${state.session.id}/guard`);
  const samples = [t("guard_ex_bad")];
  if (ex.slot) samples.push(t("guard_ex_good").replace("{slot}", ex.slot));
  samples.forEach((txt) => chips.append(el("button", { type: "button", class: "m-chip",
    onclick: () => { $("guard-in").value = txt; tryGuard(txt); } }, txt)));
}

async function tryGuard(text) {
  if (!text.trim()) return;
  const r = await api(`/api/audit/${state.session.id}/guard`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang: state.lang }) });
  const out = $("guard-out");
  out.innerHTML = "";
  if (r.ok) {
    out.append(el("p", { class: "guard-ok" }, el("b", {}, t("guard_ok")), " "), el("p", {}, segs(r.segments)));
  } else {
    out.append(el("p", { class: "guard-no" }, el("b", {}, t("guard_blocked")), " ",
      r.codes.map((c) => t("guard_" + c)).join(" · ")));
  }
}

$("guard-form").addEventListener("submit", (e) => { e.preventDefault(); tryGuard($("guard-in").value); });

/* --------------------------------------------------------------- demo mode */
// ?demo=1 keeps the stage flow short: hides the chat and shows three languages.
if (new URLSearchParams(location.search).has("demo")) {
  document.body.classList.add("demo");
}
document.querySelectorAll("#samples button").forEach((b) => b.addEventListener("click", async () => {
  $("step-1").hidden = true; $("loading").hidden = false;
  state.session = await api(`/api/samples/${b.dataset.sample}?lang=${state.lang}`, { method: "POST" });
  showStep(3); renderResult(true);
}));


/* ------------------------------------------------------------- send & share */
// Nothing is sent by the app: each button opens the family's own WhatsApp, email or SMS
// with the letter filled in, and they press send there.
function sendBar(l, lang, ta) {
  const subject = (l.subjects && l.subjects[lang]) || "";
  const open = (url) => { window.location.href = url; };
  return el("div", { class: "send" },
    el("p", { class: "to" }, el("b", {}, t("send_to") + ": "), t(`to_${l.channel}`) || l.name),
    el("div", { class: "btns" },
      el("button", { type: "button", class: "primary",
        onclick: () => open(`https://wa.me/?text=${encodeURIComponent(subject + "\n\n" + ta.value)}`) }, t("send_whatsapp")),
      el("button", { type: "button", class: "ghost",
        onclick: () => open(`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(ta.value)}`) }, t("send_email")),
      el("button", { type: "button", class: "ghost",
        onclick: () => open(`sms:?&body=${encodeURIComponent(subject + "\n" + ta.value)}`) }, t("send_sms")),
      el("button", { type: "button", class: "ghost", onclick: () => shareFamily(subject, ta.value) }, t("send_family"))),
    el("p", { class: "hint" }, t("send_hint")));
}

// The proof card is drawn here, in the browser: browsers join Indian-script letters correctly on
// every computer and phone. The server draws the same card for the API and offline backups.
const CARD_FONT = '"Noto Sans","Noto Sans Devanagari","Noto Sans Kannada","Noto Sans Gujarati","Noto Sans Tamil","Noto Sans Telugu",sans-serif';
const CARD = { W: 1080, M: 64, NAVY: "#1E2A5E", MUTED: "#5A6688", RED: "#C0283A", GREEN: "#178A5A", LINE: "#D5DCEB" };

function cardWrap(ctx, text, width) {
  const lines = []; let cur = "";
  for (const w of String(text || "").split(/\s+/).filter(Boolean)) {
    const trial = cur ? cur + " " + w : w;
    if (ctx.measureText(trial).width <= width || !cur) cur = trial; else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  return lines;
}

async function drawCard(d) {
  const all = [d.title, d.hospital_label, d.stay_label, d.excess_label, d.rule_label, d.scan, d.foot, d.scheme || "",
               ...d.rows.map((r) => r.label)].join(" ");
  try { await Promise.all([400, 700].map((wt) => document.fonts.load(`${wt} 30px ${CARD_FONT}`, all))); } catch (e) { /* use what is loaded */ }
  const { W, M, NAVY, MUTED, RED, GREEN, LINE } = CARD;
  const c = document.createElement("canvas"); c.width = W; c.height = 1500;
  const x = c.getContext("2d");
  const font = (size, bold) => { x.font = `${bold ? 700 : 400} ${size}px ${CARD_FONT}`; };
  x.fillStyle = "#fff"; x.fillRect(0, 0, W, c.height); x.textBaseline = "top";
  x.fillStyle = NAVY; x.fillRect(0, 0, W, 170);
  x.fillStyle = "#fff"; font(54, true); x.fillText("Kharcha Kavach", M, 34);
  x.fillStyle = "#C9D3F0"; font(32); x.fillText(d.title, M, 106);
  let y = 210;
  const kv = (label, value, bold) => { x.fillStyle = MUTED; font(26); x.fillText(label, M, y + 2);
    x.fillStyle = NAVY; font(bold ? 30 : 28, bold); x.fillText(value, M + 330, y); y += 48; };
  kv(d.hospital_label, d.hospital, true);
  if (d.stay) kv(d.stay_label, d.stay, false);
  y += 18; x.fillStyle = LINE; x.fillRect(M, y, W - 2 * M, 3); y += 34;
  x.fillStyle = NAVY; font(46, true);
  for (const ln of cardWrap(x, d.item, W - 2 * M).slice(0, 2)) { x.fillText(ln, M, y); y += 62; }
  y += 20;
  const row = (label, value, colour, big, sub) => {
    font(30); x.fillStyle = MUTED;
    cardWrap(x, label, W - 2 * M - 420).slice(0, 2).forEach((ln, i) => x.fillText(ln, M, y + (big ? 18 : 6) + i * 38));
    font(big ? 72 : 46, true); x.fillStyle = colour;
    x.fillText(value, W - M - x.measureText(value).width, y);
    y += big ? 100 : 66;
    if (sub) { font(26); x.fillStyle = MUTED; x.fillText(sub, W - M - x.measureText(sub).width, y - 10); y += 34; }
  };
  for (const r of d.rows) row(r.label, r.value, NAVY, false, r.sub);
  if (d.scheme) { font(34, true); x.fillStyle = GREEN; x.fillText(d.scheme, M, y); y += 70; }
  y += 6; x.fillStyle = LINE; x.fillRect(M, y, W - 2 * M, 3); y += 26;
  row(d.excess_label, d.excess, RED, true);
  // official order and QR
  y += 40; const top = y, qs = 220, inner = W - 2 * M - qs - 40;
  x.strokeStyle = LINE; x.lineWidth = 3; x.beginPath();
  if (x.roundRect) x.roundRect(M - 16, top, W - 2 * M + 32, qs + 96, 22); else x.rect(M - 16, top, W - 2 * M + 32, qs + 96);
  x.stroke();
  font(26, true); x.fillStyle = NAVY; x.fillText(d.rule_label, M + 8, top + 22);
  let ty = top + 66; font(27); x.fillStyle = NAVY;
  for (const ln of cardWrap(x, d.rule_title, inner).slice(0, 4)) { x.fillText(ln, M + 8, ty); ty += 36; }
  if (d.rule_ref) { font(23); x.fillStyle = MUTED; for (const ln of cardWrap(x, d.rule_ref, inner).slice(0, 2)) { x.fillText(ln, M + 8, ty + 4); ty += 30; } }
  if (d.qr) {
    const img = new Image(); img.src = d.qr; await img.decode();
    x.imageSmoothingEnabled = false; x.drawImage(img, W - M - qs, top + 20, qs, qs);
    font(19); x.fillStyle = MUTED; let cy = top + qs + 30;
    for (const ln of cardWrap(x, d.scan, qs + 20).slice(0, 2)) { x.fillText(ln, W - M - qs / 2 - x.measureText(ln).width / 2, cy); cy += 24; }
  }
  let fy = top + qs + 130; font(24); x.fillStyle = MUTED;
  for (const ln of cardWrap(x, d.foot, W - 2 * M).slice(0, 3)) { x.fillText(ln, M, fy); fy += 34; }
  const out = document.createElement("canvas"); out.width = W; out.height = Math.min(1500, fy + 40);
  out.getContext("2d").drawImage(c, 0, 0);
  return new Promise((res) => out.toBlob(res, "image/png"));
}

async function cardFile(fid) {
  const q = fid ? `&fid=${encodeURIComponent(fid)}` : "";
  try {
    const d = await api(`/api/audit/${state.session.id}/proof-card.json?lang=${state.lang}${q}`);
    const blob = await drawCard(d);
    if (blob) return new File([blob], "kharcha-kavach-proof.png", { type: "image/png" });
  } catch (e) { /* fall back to the server image */ }
  const r = await fetch(`/api/audit/${state.session.id}/proof-card.png?lang=${state.lang}${q}`);
  if (!r.ok) return null;
  return new File([await r.blob()], "kharcha-kavach-proof.png", { type: "image/png" });
}

async function shareCard(fid) {
  const f = await cardFile(fid);
  if (!f) return;
  if (navigator.canShare && navigator.canShare({ files: [f] })) {
    try { await navigator.share({ files: [f], title: "Kharcha Kavach" }); return; } catch (e) { /* closed */ }
  }
  const a = el("a", { href: URL.createObjectURL(f), download: f.name });
  document.body.append(a); a.click(); a.remove();
  toast(t("card_saved"));
}

async function shareFamily(subject, text) {
  const f = await cardFile(null);
  const data = { title: subject, text: subject + "\n\n" + text };
  if (f && navigator.canShare && navigator.canShare({ files: [f], text: data.text })) data.files = [f];
  if (navigator.share) {
    try { await navigator.share(data); return; } catch (e) { /* closed or not allowed */ }
  }
  window.location.href = `https://wa.me/?text=${encodeURIComponent(data.text)}`;
}
