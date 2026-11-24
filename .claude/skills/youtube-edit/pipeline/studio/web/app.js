// Video Studio: board, video page, review. Plain JS, no build. Talks to server.py.
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const app = $("#app");
let timers = [];
const clearTimers = () => { timers.forEach(clearInterval); timers = []; };

async function api(path, opts = {}) {
  const o = { method: opts.method || "GET", headers: { "Content-Type": "application/json" } };
  if (o.method !== "GET") o.headers["X-Studio"] = "1";
  if (opts.body !== undefined) o.body = JSON.stringify(opts.body);
  const r = await fetch(path, o);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
function toast(msg) {
  const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.append(t);
  setTimeout(() => t.remove(), 2600);
}
const media = (name, rel) => `/media/${encodeURIComponent(name)}/${rel.split("/").map(encodeURIComponent).join("/")}`;

// ---- markdown (enough for briefs, scripts, write-ups) ----------------------------------------------------------
function md(src) {
  const lines = String(src || "").split("\n"); let out = [], i = 0;
  const inline = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<i>$2</i>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g, '$1<a href="$2" target="_blank">$2</a>');
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) { const lab = l.replace(/^```/, "").trim(); const buf = []; i++; while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]); i++;
      out.push((lab ? `<div class="small muted">${esc(lab)}</div>` : "") + `<pre><code>${esc(buf.join("\n"))}</code></pre>`); continue; }
    if (/^#{1,4} /.test(l)) { const n = l.match(/^#+/)[0].length; out.push(`<h${n + 1}>${inline(l.replace(/^#+ /, ""))}</h${n + 1}>`); i++; continue; }
    if (/^\s*>/.test(l)) { const buf = []; while (i < lines.length && /^\s*>/.test(lines[i])) buf.push(lines[i++].replace(/^\s*> ?/, "")); out.push(`<blockquote>${inline(buf.join(" "))}</blockquote>`); continue; }
    if (/^\|/.test(l)) { const rows = []; while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = r => r.replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      const body = rows.filter(r => !/^\|\s*-/.test(r));
      out.push("<table>" + body.map((r, k) => "<tr>" + cells(r).map(c => k ? `<td>${inline(c)}</td>` : `<th>${inline(c)}</th>`).join("") + "</tr>").join("") + "</table>"); continue; }
    if (/^\s*([-*•]|\d+\.) /.test(l)) { const ord = /^\s*\d+\./.test(l); const buf = [];
      while (i < lines.length && /^\s*([-*•]|\d+\.) /.test(lines[i])) buf.push(lines[i++].replace(/^\s*([-*•]|\d+\.) /, ""));
      out.push(`<${ord ? "ol" : "ul"}>` + buf.map(b => `<li>${inline(b)}</li>`).join("") + `</${ord ? "ol" : "ul"}>`); continue; }
    if (/^\s*(→|->)\s*demo:/i.test(l)) { out.push(`<p><span class="pill">demo</span> ${inline(l.replace(/^\s*(→|->)\s*demo:\s*/i, ""))}</p>`); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const buf = []; while (i < lines.length && lines[i].trim() && !/^(#|```|\||\s*>|\s*([-*•]|\d+\.) )/.test(lines[i])) buf.push(lines[i++]);
    out.push(`<p>${inline(buf.join(" "))}</p>`);
  }
  return out.join("\n");
}

// ---- router -----------------------------------------------------------------------------------------------------
let PH = [];
async function route() {
  clearTimers();
  const h = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  try {
    if (h[0] === "s" && h[1]) return await seriesPage(h[1]);
    if (h[0] === "v" && h[1]) {
      if (h[2] === "review") return await reviewPage(h[1], h[3] || "B");
      return await videoPage(h[1], h[2]);
    }
    return await board();
  } catch (e) { app.innerHTML = `<div class="panel">Something went wrong: ${esc(e.message)}</div>`; }
}
window.addEventListener("hashchange", route);
const crumbs = html => { $("#crumbs").innerHTML = html; };

// ---- board ------------------------------------------------------------------------------------------------------
let boardSeries = "";
try { boardSeries = localStorage.getItem("studio-series") || ""; } catch (e) { /* private window */ }
const lenBadge = (m, t = 6, mx = 10) => m == null ? "" : `<span class="pill len ${m > mx ? "over" : m > t ? "warn" : "okay"}">${m} min</span>`;
async function board() {
  crumbs("");
  let { videos, phases } = await api("/api/videos"); PH = phases;
  const { series } = await api("/api/series");
  if (boardSeries) videos = videos.filter(v => (v.series || []).includes(boardSeries));
  const byPhase = Object.fromEntries(phases.map(p => [p.id, []]));
  videos.forEach(v => (byPhase[v.phase] || (byPhase[v.phase] = [])).push(v));
  app.innerHTML = `<div class="row" style="margin-bottom:12px;justify-content:flex-start;gap:12px">
      <select id="sfilter" style="max-width:320px"><option value="">Every video</option>${series.map(x => `<option ${x.title === boardSeries ? "selected" : ""}>${esc(x.title)}</option>`).join("")}</select>
      ${series.map(x => `<a class="pill" href="#/s/${x.slug}">${esc(x.title)}</a>`).join(" ")}<span style="flex:1"></span></div>
    <div class="board">${phases.map(p => `<section class="col"><h3><span>${esc(p.title)}</span><span>${byPhase[p.id].length || ""}</span></h3>
    ${byPhase[p.id].map(v => `<a class="card ${v.waiting_on.startsWith("you") ? "you" : ""}" href="#/v/${encodeURIComponent(v.name)}">
      <div class="t">${esc(v.title)} ${v.open_questions ? `<span class="badge">${v.open_questions}</span>` : ""}</div>
      <div class="small muted">${esc(v.name)} ${lenBadge(v.minutes)}</div>
      ${(v.series || []).length ? `<div class="small">${v.series.map(x => `<span class="pill">${esc(x)}</span>`).join(" ")}</div>` : ""}
      <div class="w">Waiting on ${esc(v.waiting_on)}</div></a>`).join("")}</section>`).join("")}</div>`;
  $("#sfilter").onchange = e => { boardSeries = e.target.value; try { localStorage.setItem("studio-series", boardSeries); } catch (er) { /* fine */ } board(); };
  timers.push(setInterval(async () => { if (!document.hidden && location.hash.replace(/^#\/?/, "") === "" && !document.activeElement.matches("select")) board(); }, 15000));
}

$("#new-video").onclick = () => {
  const d = $("#dlg");
  d.innerHTML = `<form method="dialog" class="stack"><h2>New video</h2>
    <div><label>Working title</label><input name="title" required placeholder="Find stale deals with the Agent CLI"></div>
    <div><label>Folder name (optional; made from the title)</label><input name="name" placeholder="agents-3"></div>
    <div><label>Where the idea comes from</label><select name="origin">
      <option value="colleague">A colleague's work (an exercise, a post, a demo)</option>
      <option value="problem">A problem to solve</option>
      <option value="feature">A new feature</option>
      <option value="finished">A finished video that only needs packaging</option></select></div>
    <div class="row"><div><label>Series (comma-separated; a video can be in several)</label><input name="series" placeholder="HubSpot Is Going Headless"></div>
      <div><label>Presenter or colleague</label><input name="presenter" placeholder="Dennis"></div></div>
    <div class="row"><button class="btn" value="cancel">Cancel</button><button class="btn primary" value="ok">Create</button></div></form>`;
  d.showModal();
  d.querySelector("form").onsubmit = async ev => {
    if (ev.submitter?.value !== "ok") return;
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target)); f.series = (f.series || "").split(",").map(x => x.trim()).filter(Boolean);
    try { const r = await api("/api/videos", { method: "POST", body: f }); d.close(); location.hash = `#/v/${r.name}`; }
    catch (e) { toast(e.message); }
  };
};

// ---- video page -------------------------------------------------------------------------------------------------
const ACTION_LABELS = {
  sheets: "Make teleprompter and recording sheet", "finder-raw": "Open raw/ in Finder", "start-cut": "Start the cut",
  "start-cut-fast": "Start the cut (rush)", "approve-a": "Approve the cut", "rerun-cut": "Rerun the cut stage",
  "approve-b": "Approve the storyboard", "rerun-storyboard": "Rerun the storyboard stage", import: "Import the render",
  youtube: "Rebuild the YouTube package", shorten: "Shorten links", thumb: "Redraw thumbnails", drive: "Copy to Drive",
};
let cur = null;

async function videoPage(name, phaseId) {
  const d = await api(`/api/videos/${encodeURIComponent(name)}`); cur = d;
  const v = d.video, sel = phaseId || d.phase;
  const p = d.phases.find(x => x.id === sel) || d.phases[0];
  const idx = id => d.phases.findIndex(x => x.id === id);
  crumbs(`<a href="#/">Board</a> › ${esc(v.title || name)}`);
  const prog = d.progress[p.id] || { done: [] };
  const open = d.questions.filter(q => !q.answer && !(q.action === "split" && d.split && d.split.status === "proposed"));
  app.innerHTML = `<div class="vgrid">
    <nav class="panel phases">${d.phases.map(x => {
      const st = idx(x.id) < idx(d.phase) ? "done" : x.id === d.phase ? "cur" : "";
      return `<a class="${st} ${x.id === p.id ? "sel" : ""}" href="#/v/${encodeURIComponent(name)}/${x.id}"><span class="i">${st === "done" ? "✓" : st === "cur" ? "●" : "○"}</span>${esc(x.title)}</a>`; }).join("")}</nav>
    <section class="stack">
      <div class="panel"><h1>${esc(v.title || name)}</h1>
        <div class="muted small">${esc(name)} · ${esc(v.origin || "made before the studio")}${v.part ? ` · part ${v.part}` : ""} · now in <b>${esc(d.phases[idx(d.phase)].title)}</b>${d.stage ? ` · pipeline: ${esc(d.stage)}` : ""}</div>
        <div class="row" style="margin-top:8px;justify-content:flex-start;gap:6px;flex-wrap:wrap">${(v.series || []).map(x => `<a class="pill" href="#/s/${encodeURIComponent(x.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""))}">${esc(x)}</a>`).join("")}
          <button class="btn small" id="edit-series" style="flex:0">Series…</button>
          ${d.length.minutes != null ? `${lenBadge(d.length.minutes, d.length.target, d.length.max)} <span class="small muted">target under ${d.length.target} min, never over ${d.length.max}</span>` : ""}</div></div>
      ${d.split && d.split.status === "proposed" ? splitHtml(d.split) : ""}
      ${open.length ? `<div class="panel"><h2>Questions for you</h2>${open.map(qHtml).join("")}</div>` : ""}
      <div class="panel"><h2>${esc(p.title)}</h2><p class="muted">${esc(p.goal || "")}</p>
        ${p.where === "home" ? `<p class="pill">Happens on the home Mac</p>` : ""}
        <ul class="steps">${p.steps.map(s => `<li><div class="st"><input type="checkbox" data-step="${s.id}" ${prog.done.includes(s.id) ? "checked" : ""}>
          <div><b>${esc(s.title)}</b><div class="ins">${esc(s.instructions)}</div></div></div></li>`).join("")}</ul>
        <div class="actions">
          ${p.review ? `<a class="btn primary" href="#/v/${encodeURIComponent(name)}/review/${p.review}">Open the review</a>` : ""}
          ${(p.actions || []).map(a => `<button class="btn" data-act="${a}">${esc(ACTION_LABELS[a] || a)}</button>`).join("")}
          ${["ideation", "script", "results"].includes(p.id) ? `<button class="btn" data-approve>Approve this phase</button>` : ""}
          ${p.id !== d.phase ? `<button class="btn small" data-setphase>Move the video to this phase</button>` : ""}
        </div></div>
      ${p.docs.length ? `<div class="panel"><div class="tabs">${p.docs.map((doc, k) => `<button data-doc="${esc(doc)}" class="${k ? "" : "sel"}">${esc(doc)}${d.docs[doc] ? "" : " (new)"}</button>`).join("")}</div><div id="editor"></div></div>` : ""}
      <div class="panel forms"><h2>Ask Claude</h2>${p.forms.map(formHtml).join("")}</div>
      <div class="panel"><h2>Recent runs</h2><div id="jobs">${d.jobs.length ? "" : '<p class="muted small">Nothing yet.</p>'}</div></div>
    </section>
    <aside class="side stack"><div class="panel chat"><h2>Chat about this video</h2><div class="msgs" id="msgs"></div>
      <textarea id="chat-in" rows="3" placeholder="Anything about this video. Enter sends, Shift+Enter for a new line."></textarea></div>
      ${d.questions.filter(q => q.answer).length ? `<div class="panel"><h3>Answered</h3>${d.questions.filter(q => q.answer).slice(-5).map(qHtml).join("")}</div>` : ""}
    </aside></div>`;

  app.querySelectorAll("[data-step]").forEach(cb => cb.onchange = () =>
    api(`/api/videos/${name}/phase`, { method: "POST", body: { phase: p.id, step: cb.dataset.step, done: cb.checked } }).catch(e => toast(e.message)));
  app.querySelector("[data-approve]")?.addEventListener("click", async () => {
    await api(`/api/videos/${name}/phase`, { method: "POST", body: { phase: p.id, approve: true } }); toast("Approved"); location.hash = `#/v/${name}`; route(); });
  app.querySelector("[data-setphase]")?.addEventListener("click", async () => {
    await api(`/api/videos/${name}/phase`, { method: "POST", body: { phase: p.id, set: p.id } }); route(); });
  app.querySelectorAll("[data-act]").forEach(b => b.onclick = () => runAction(name, b.dataset.act));
  bindQuestions(name);
  bindForms(name, p);
  $("#edit-series").onclick = () => editSeries(name, v.series || [], d.all_series || []);
  app.querySelector("[data-split-accept]")?.addEventListener("click", async () => {
    const parts = [...app.querySelectorAll("[data-part]")].map(r => ({ name: r.querySelector("[name=n]").value, title: r.querySelector("[name=t]").value,
      promise: r.querySelector("[name=p]").value, minutes: r.querySelector("[name=m]").value }));
    const series = app.querySelector("[name=split-series]").value;
    try { const r = await api(`/api/videos/${name}/split`, { method: "POST", body: { accept: true, parts, series } }); toast(`Series made: ${r.parts.length} videos`); location.hash = `#/s/${r.series}`; }
    catch (e) { toast(e.message); } });
  app.querySelector("[data-split-dismiss]")?.addEventListener("click", async () => { await api(`/api/videos/${name}/split`, { method: "POST", body: { accept: false } }); route(); });
  if (p.docs.length) {
    const tabs = app.querySelectorAll("[data-doc]");
    tabs.forEach(t => t.onclick = () => { tabs.forEach(x => x.classList.remove("sel")); t.classList.add("sel"); openDoc(name, t.dataset.doc); });
    openDoc(name, p.docs[0]);
  }
  renderJobs(name, d.jobs);
  chat(name);
}

function splitHtml(sp) {
  return `<div class="panel" style="border:2px solid var(--orange)"><h2>Make this a series?</h2>
    ${sp.why ? `<p class="muted">${esc(sp.why)}</p>` : ""}
    <label>Series</label><input name="split-series" value="${esc(sp.series)}">
    <table style="width:100%;margin-top:10px;border-collapse:collapse"><tr class="small muted"><th align="left">#</th><th align="left">Folder</th><th align="left">Title</th><th align="left">Promise</th><th align="left">Min</th></tr>
    ${sp.parts.map((p, k) => `<tr data-part><td>${k + 1}</td><td><input name="n" value="${esc(p.name)}" ${k ? "" : "readonly"}></td><td><input name="t" value="${esc(p.title)}"></td>
      <td><input name="p" value="${esc(p.promise)}"></td><td style="width:70px"><input name="m" value="${esc(p.minutes)}"></td></tr>`).join("")}</table>
    <p class="small muted">Part 1 is this video. The others are created as studio projects with this video's research and links, and every part is linked to the others.</p>
    <div class="actions"><button class="btn primary" data-split-accept>Make it a series</button><button class="btn" data-split-dismiss>Keep one video</button></div></div>`;
}
function editSeries(name, mine, known) {
  const d = $("#dlg"); const all = [...new Set([...known, ...mine])];
  d.innerHTML = `<form method="dialog" class="stack"><h2>Series and playlists</h2><p class="small muted">A video can be in several.</p>
    ${all.map(t => `<label style="display:flex;gap:8px;align-items:center;color:var(--ink)"><input type="checkbox" style="width:auto" value="${esc(t)}" ${mine.includes(t) ? "checked" : ""}>${esc(t)}</label>`).join("") || '<p class="muted small">No series yet.</p>'}
    <div><label>New series</label><input name="new" placeholder="Agent auth"></div>
    <div class="row"><button class="btn" value="cancel">Cancel</button><button class="btn primary" value="ok">Save</button></div></form>`;
  d.showModal();
  d.querySelector("form").onsubmit = async ev => {
    if (ev.submitter?.value !== "ok") return; ev.preventDefault();
    const titles = [...d.querySelectorAll("input[type=checkbox]:checked")].map(i => i.value);
    const nw = d.querySelector("[name=new]").value.trim(); if (nw) titles.push(nw);
    await api(`/api/videos/${name}/series`, { method: "POST", body: { titles } }); d.close(); route();
  };
}

// ---- series page ----------------------------------------------------------------------------------------------------
async function seriesPage(slugName) {
  const s = await api(`/api/series/${encodeURIComponent(slugName)}`);
  crumbs(`<a href="#/">Board</a> › ${esc(s.title)}`);
  const total = s.videos.reduce((a, v) => a + (v.minutes || 0), 0);
  app.innerHTML = `<div class="vgrid" style="grid-template-columns:minmax(0,1fr) 420px"><section class="stack">
      <div class="panel"><h1>${esc(s.title)}</h1><div class="muted small">${s.videos.length} video${s.videos.length === 1 ? "" : "s"}${total ? ` · about ${Math.round(total)} min in all` : ""}</div></div>
      <div class="panel"><h2>The videos, in order</h2>${s.videos.map((v, k) => `<div class="row" style="margin-bottom:8px"><span style="flex:0 0 28px">${k + 1}.</span>
        <a href="#/v/${encodeURIComponent(v.name)}" style="flex:3">${esc(v.title)}</a><span class="pill" style="flex:0">${esc((PH.find(p => p.id === v.phase) || {}).title || v.phase)}</span>
        ${lenBadge(v.minutes)}<span style="flex:0;white-space:nowrap"><button class="btn small" data-up="${k}" ${k ? "" : "disabled"}>↑</button> <button class="btn small" data-down="${k}" ${k < s.videos.length - 1 ? "" : "disabled"}>↓</button></span></div>`).join("") || '<p class="muted">No videos yet: add one from its page (Series…).</p>'}</div>
      <div class="panel"><h2>About the series</h2><div id="editor"></div></div></section>
    <aside class="stack"><div class="panel stack"><div><label>Playlist link</label><input id="pl" value="${esc(s.playlist || "")}" placeholder="https://www.youtube.com/playlist?list=…"></div>
      <div><label>Playlist description</label><textarea id="pd" rows="5" style="font-family:inherit">${esc(s.description || "")}</textarea></div>
      <div><label>Cover image (path on this Mac)</label><input id="pc" value="${esc(s.cover || "")}" placeholder="videos/_playlists/${esc(s.slug)}/playlist-cover.jpg"></div>
      <button class="btn primary" id="ssave">Save</button></div></aside></div>`;
  const order = s.videos.map(v => v.name);
  const put = body => api(`/api/series/${s.slug}`, { method: "PUT", body });
  app.querySelectorAll("[data-up],[data-down]").forEach(b => b.onclick = async () => {
    const k = +(b.dataset.up ?? b.dataset.down), j = b.dataset.up != null ? k - 1 : k + 1; [order[k], order[j]] = [order[j], order[k]];
    await put({ parts: order }); route(); });
  $("#ssave").onclick = async () => { await put({ playlist: $("#pl").value, description: $("#pd").value, cover: $("#pc").value }); toast("Saved"); };
  const ed = $("#editor");
  ed.innerHTML = `<div class="editor"><textarea></textarea><div class="preview"></div></div>`;
  const ta = ed.querySelector("textarea"), pv = ed.querySelector(".preview"); ta.value = s.md; pv.innerHTML = md(s.md);
  let tm = null; ta.oninput = () => { pv.innerHTML = md(ta.value); clearTimeout(tm); tm = setTimeout(() => put({ md: ta.value }), 1200); };
}

function qHtml(q) {
  return `<div class="q ${q.answer ? "answered" : ""}" data-q="${q.id}"><div>${esc(q.text)}</div>
    ${q.answer ? `<div class="small"><b>You:</b> ${esc(q.answer)}</div>` : `<div class="actions" style="margin-top:6px">${(q.options || []).map(o => `<button class="btn small" data-ans="${esc(o)}">${esc(o)}</button>`).join("")}</div>
    <div class="row" style="margin-top:6px"><input placeholder="Or your own answer"><button class="btn small" data-own style="flex:0">Answer</button></div>`}
    <div class="small muted">${esc(q.from)} · ${esc(q.asked)}</div></div>`;
}
function bindQuestions(name, root = app) {
  root.querySelectorAll(".q:not(.answered)").forEach(el => {
    const send = async a => { await api(`/api/videos/${name}/questions`, { method: "POST", body: { id: el.dataset.q, answer: a } }); toast("Answered"); route(); };
    el.querySelectorAll("[data-ans]").forEach(b => b.onclick = () => send(b.dataset.ans));
    el.querySelector("[data-own]")?.addEventListener("click", () => { const t = el.querySelector("input").value.trim(); if (t) send(t); });
  });
}

function formHtml(f) {
  return `<details data-form="${f.id}" ${f.id === "freeform" ? "" : ""}><summary>${esc(f.label)}</summary><div class="stack" style="margin-top:8px">
    ${(f.fields || []).map(x => `<div><label>${esc(x.label)}</label>${x.type === "textarea" ? `<textarea name="${x.id}" rows="4" placeholder="${esc(x.placeholder || "")}"></textarea>` : `<input name="${x.id}" placeholder="${esc(x.placeholder || "")}">`}</div>`).join("")}
    <button class="btn primary" data-run>${f.action ? "Record" : "Ask Claude"}</button></div></details>`;
}
function bindForms(name, p) {
  app.querySelectorAll("[data-form]").forEach(el => el.querySelector("[data-run]").onclick = async () => {
    const fields = {}; el.querySelectorAll("[name]").forEach(i => fields[i.name] = i.value);
    try { const r = await api(`/api/videos/${name}/request`, { method: "POST", body: { phase: p.id, form: el.dataset.form, fields } });
      toast("Started"); el.open = false; followJob(name, r.job); } catch (e) { toast(e.message); }
  });
}

async function runAction(name, act, args) {
  if (act === "approve-a" && !args) {
    const g = prompt("Approve the cut. Camera grade (blacks, punchier or none):", "blacks"); if (g === null) return;
    const n = prompt("Anything to add (optional):", "") ?? ""; args = { grade: g, note: n };
  }
  if (act === "approve-b" && !args) { const n = prompt("Approve the storyboard. Anything to add (optional):", ""); if (n === null) return; args = { note: n }; }
  if (act === "import" && !args) { const pth = prompt("Path of the finished video on this Mac:", "~/Desktop/"); if (!pth) return; args = { path: pth }; }
  if (act === "shorten" && !args && cur?.video?.legacy) args = { hubspot: confirm("Is this HubSpot content? (Bitly is HubSpot's account, for HubSpot videos only)") };
  try { const r = await api(`/api/videos/${name}/action`, { method: "POST", body: { action: act, args } }); toast("Started: " + (ACTION_LABELS[act] || act)); followJob(name, r.job); }
  catch (e) { toast(e.message); }
}

function jobHtml(j) {
  return `<div class="job" data-job="${j.id}"><div class="row"><b>${esc(j.label || j.kind)}</b><span class="small muted" style="text-align:right">${esc(j.started)} · ${j.running ? "running…" : j.exit === 0 ? "done" : "exit " + j.exit}${j.cost ? ` · $${Number(j.cost).toFixed(2)}` : ""}</span></div>
    ${j.reply ? `<div class="reply">${esc(j.reply)}</div>` : ""}<details ${j.running ? "open" : ""}><summary class="small">Log</summary><pre>${esc(j.log || "")}</pre></details></div>`;
}
async function renderJobs(name, list) {
  const box = $("#jobs"); if (!box) return;
  for (const j of list.slice(0, 6)) {
    const full = await api(`/api/videos/${name}/jobs/${j.id}`).catch(() => j);
    box.insertAdjacentHTML("beforeend", jobHtml(full));
    if (full.running) followJob(name, j.id, true);
  }
}
function followJob(name, id, existing) {
  const box = $("#jobs");
  if (box && !existing) { box.querySelector("p.muted")?.remove(); box.insertAdjacentHTML("afterbegin", `<div class="job" data-job="${id}">starting…</div>`); }
  const t = setInterval(async () => {
    const j = await api(`/api/videos/${name}/jobs/${id}`).catch(() => null); if (!j) return;
    const el = document.querySelector(`[data-job="${id}"]`); if (el) el.outerHTML = jobHtml(j);
    const pre = document.querySelector(`[data-job="${id}"] pre`); if (pre) pre.scrollTop = pre.scrollHeight;
    if (!j.running) { clearInterval(t); if (j.kind !== "chat") toast(`${j.label}: ${j.exit === 0 ? "done" : "failed"}`); }
  }, 2000);
  timers.push(t);
}

async function openDoc(name, path) {
  const d = await api(`/api/videos/${name}/doc?path=${encodeURIComponent(path)}`);
  const ed = $("#editor");
  ed.innerHTML = `<div class="editor"><textarea ${d.read_only ? "readonly" : ""} spellcheck="true"></textarea><div class="preview"></div></div>
    <div class="row" style="margin-top:8px"><span class="small muted" id="savestate">${d.read_only ? "Generated: change it with a request or an action" : d.exists ? "Saved" : "Not created yet: it saves when you type"}</span>
    ${d.read_only ? "" : `<button class="btn" id="save" style="flex:0">Save <span class="kbd">⌘S</span></button>`}</div>`;
  const ta = ed.querySelector("textarea"), pv = ed.querySelector(".preview"), ss = $("#savestate");
  ta.value = d.text; pv.innerHTML = path.endsWith(".txt") ? `<pre>${esc(d.text)}</pre>` : md(d.text);
  let dirty = false, tm = null;
  const save = async () => { if (!dirty) return; await api(`/api/videos/${name}/doc?path=${encodeURIComponent(path)}`, { method: "PUT", body: { text: ta.value } }); dirty = false; ss.textContent = "Saved " + new Date().toLocaleTimeString(); };
  ta.oninput = () => { dirty = true; ss.textContent = "Editing…"; pv.innerHTML = path.endsWith(".txt") ? `<pre>${esc(ta.value)}</pre>` : md(ta.value); clearTimeout(tm); tm = setTimeout(save, 1500); };
  ta.onkeydown = e => { if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); } };
  ed.querySelector("#save")?.addEventListener("click", save);
}

async function chat(name) {
  const box = $("#msgs"), inp = $("#chat-in"); if (!box) return;
  const draw = async () => {
    const { messages } = await api(`/api/videos/${name}/chat`);
    box.innerHTML = messages.length ? messages.map(m => `<div class="m ${m.role}">${m.text ? (m.role === "claude" ? md(m.text) : esc(m.text)) : "<i>thinking…</i>"}</div>`).join("")
      : '<p class="muted small">Ask anything about this video. Claude works in this video only, in its own session.</p>';
    box.scrollTop = box.scrollHeight;
    return messages.some(m => m.role === "claude" && !m.text);
  };
  let pending = await draw();
  const t = setInterval(async () => { if (pending) pending = await draw(); }, 2500); timers.push(t);
  inp.onkeydown = async e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); const text = inp.value.trim(); if (!text) return; inp.value = "";
      try { await api(`/api/videos/${name}/chat`, { method: "POST", body: { text } }); pending = await draw(); } catch (er) { toast(er.message); } }
  };
}

// ---- review ------------------------------------------------------------------------------------------------------
async function reviewPage(name, which) {
  const d = await api(`/api/videos/${encodeURIComponent(name)}`); cur = d;
  const rv = d.reviews[which] || {}, v = d.video;
  const title = { A: "Checkpoint A: the cut", B: "Checkpoint B: storyboard and preview", package: "Packaging: title and thumbnail" }[which];
  crumbs(`<a href="#/">Board</a> › <a href="#/v/${encodeURIComponent(name)}">${esc(v.title || name)}</a> › ${esc(title)}`);
  let items = (await api(`/api/videos/${name}/comments/${which}`)).items;
  const vid = which === "package" ? rv.video : rv.video;
  const open = d.questions.filter(q => !q.answer);
  app.innerHTML = `<div class="rgrid"><section class="stack">
      <div class="panel"><h1>${esc(title)}</h1><div class="muted small">Press <span class="kbd">C</span> to comment on the moment you're watching (the frame is kept). Drag on a frame to box what you mean. Drag a still onto a comment to attach it.</div></div>
      ${vid ? `<div class="panel"><video id="vid" src="${media(name, vid)}" controls preload="metadata"></video><div class="timeline" id="tl"><div class="ph" id="ph"></div></div></div>` : `<div class="panel muted">No video for this review yet.</div>`}
      ${(rv.stills || []).concat(rv.variants || []).length ? `<div class="panel"><h3>Stills and variants</h3><div class="stills">${(rv.stills || []).map(s => `<img draggable="true" data-still="${esc(s)}" src="${media(name, s)}" title="${esc(s)} (click to comment on it)">`).join("")}</div>
        ${(rv.variants || []).map(x => `<div style="margin-top:10px"><div class="small muted">${esc(x)}</div><video src="${media(name, x)}" controls preload="metadata"></video></div>`).join("")}</div>` : ""}
      ${which === "package" ? `<div class="panel"><h2>Thumbnails</h2><div class="thumbs">${(rv.thumbs || []).map((t, k) => `<figure><img draggable="true" data-still="${esc(t)}" src="${media(name, t)}"><button class="btn small" data-pick-thumb="${k}">Use this one</button></figure>`).join("") || '<p class="muted">None yet: "Redraw thumbnails" on the packaging phase.</p>'}</div>
        <h2 style="margin-top:16px">Titles</h2>${(rv.titles || []).map((t, k) => `<div class="row" style="margin-bottom:6px"><span>${k === 0 ? "<b>" : ""}${esc(t)}${k === 0 ? "</b> (first: the one used)" : ""}</span><button class="btn small" style="flex:0" data-pick-title="${k}">Use this</button></div>`).join("")}</div>` : ""}
      ${rv.doc ? `<div class="panel"><details><summary><b>${esc(rv.doc)}</b></summary><div class="preview" id="wdoc" style="margin-top:8px"></div></details></div>` : ""}
    </section>
    <aside class="stack">
      ${open.length ? `<div class="panel"><h2>Questions for you</h2>${open.map(qHtml).join("")}</div>` : ""}
      <div class="panel"><div class="row"><h2 style="margin:0">Your notes</h2><button class="btn small" id="add" style="flex:0">+ Note</button></div><div id="cms" style="margin-top:10px"></div>
        <div class="actions" style="margin-top:10px"><button class="btn primary" id="send">Send notes to Claude</button>
        ${which === "A" ? `<button class="btn" data-act="approve-a">Approve the cut</button>` : which === "B" ? `<button class="btn" data-act="approve-b">Approve the storyboard</button>` : ""}</div>
        <div id="jobs" style="margin-top:10px"></div></div></aside></div>`;

  if (rv.doc) api(`/api/videos/${name}/doc?path=${encodeURIComponent(rv.doc)}`).then(x => { $("#wdoc").innerHTML = md(x.text); }).catch(() => {});
  bindQuestions(name);
  app.querySelectorAll("[data-act]").forEach(b => b.onclick = () => runAction(name, b.dataset.act));
  app.querySelectorAll("[data-pick-thumb]").forEach(b => b.onclick = async () => { await runAction(name, "pick-thumb", { index: +b.dataset.pickThumb }); setTimeout(route, 2500); });
  app.querySelectorAll("[data-pick-title]").forEach(b => b.onclick = async () => { await runAction(name, "pick-title", { index: +b.dataset.pickTitle }); setTimeout(route, 2500); });
  const video = $("#vid"), tl = $("#tl"), cms = $("#cms");
  let saveT = null;
  const persist = () => { clearTimeout(saveT); saveT = setTimeout(() => api(`/api/videos/${name}/comments/${which}`, { method: "POST", body: { items } }), 600); };
  const fmt = t => t == null ? "still" : `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}.${Math.floor((t % 1) * 10)}`;

  function drawMarkers() {
    if (!tl || !video || !video.duration) return;
    tl.querySelectorAll(".mk").forEach(m => m.remove());
    items.filter(c => c.t != null).forEach(c => { const m = document.createElement("div"); m.className = "mk"; m.style.left = (100 * c.t / video.duration) + "%"; m.title = c.text;
      m.onclick = e => { e.stopPropagation(); video.currentTime = c.t; }; tl.append(m); });
  }
  function drawComments() {
    cms.innerHTML = items.length ? "" : '<p class="muted small">No notes yet. Press C while watching, or click a still.</p>';
    items.forEach((c, k) => {
      const el = document.createElement("div"); el.className = "cm" + (c.sent ? " sent" : "");
      const img = c.frame || c.still;
      el.innerHTML = `<div class="head"><a href="#" data-jump>${esc(fmt(c.t))}</a><span>${c.sent ? "sent " + esc(c.sent) : ""} <button class="btn small" data-del>✕</button></span></div>
        ${img ? `<div class="frame"><img src="${media(name, img)}" draggable="false">${c.box ? `<div class="box"></div>` : ""}</div>` : ""}
        ${c.still && c.frame ? `<div class="small muted">with still ${esc(c.still)}</div>` : ""}
        <textarea placeholder="What should change?">${esc(c.text)}</textarea>`;
      el.querySelector("[data-jump]").onclick = e => { e.preventDefault(); if (video && c.t != null) { video.currentTime = c.t; video.scrollIntoView({ block: "center" }); } };
      el.querySelector("[data-del]").onclick = () => { items.splice(k, 1); persist(); drawComments(); drawMarkers(); };
      el.querySelector("textarea").oninput = e => { c.text = e.target.value; persist(); };
      const fr = el.querySelector(".frame");
      if (fr) {
        const im = fr.querySelector("img");
        const place = () => { const b = fr.querySelector(".box"); if (!b || !c.box || !im.naturalWidth) return; const s = im.clientWidth / im.naturalWidth;
          Object.assign(b.style, { left: c.box[0] * s + "px", top: c.box[1] * s + "px", width: c.box[2] * s + "px", height: c.box[3] * s + "px" }); };
        im.onload = place; place();
        let st = null;
        fr.onmousedown = e => { const r = im.getBoundingClientRect(); st = [e.clientX - r.left, e.clientY - r.top]; };
        fr.onmouseup = e => { if (!st) return; const r = im.getBoundingClientRect(); const en = [e.clientX - r.left, e.clientY - r.top]; const s = im.naturalWidth / im.clientWidth;
          const x = Math.min(st[0], en[0]) * s, y = Math.min(st[1], en[1]) * s, w = Math.abs(en[0] - st[0]) * s, h = Math.abs(en[1] - st[1]) * s; st = null;
          if (w < 6 || h < 6) return; c.box = [x, y, w, h].map(Math.round); persist(); drawComments(); };
      }
      el.ondragover = e => { e.preventDefault(); el.classList.add("drop"); };
      el.ondragleave = () => el.classList.remove("drop");
      el.ondrop = e => { e.preventDefault(); const s = e.dataTransfer.getData("text/still"); if (s) { c.still = s; persist(); drawComments(); } };
      cms.append(el);
    });
    drawMarkers();
  }
  async function addAtNow() {
    if (!video) return addFromStill(null);
    video.pause();
    const id = "c" + Date.now().toString(36);
    const c = { id, t: Math.round(video.currentTime * 100) / 100, text: "" };
    try {
      const cv = document.createElement("canvas"); cv.width = video.videoWidth; cv.height = video.videoHeight;
      cv.getContext("2d").drawImage(video, 0, 0); const r = await api(`/api/videos/${name}/frame`, { method: "POST", body: { id, png: cv.toDataURL("image/png") } });
      c.frame = r.frame;
    } catch (e) { /* the note still works without the frame */ }
    items.push(c); items.sort((a, b) => (a.t ?? 1e9) - (b.t ?? 1e9)); persist(); drawComments();
    const ta = [...cms.querySelectorAll(".cm")][items.indexOf(c)]?.querySelector("textarea"); ta?.focus();
  }
  function addFromStill(s) { items.push({ id: "c" + Date.now().toString(36), t: null, still: s, text: "" }); persist(); drawComments(); [...cms.querySelectorAll("textarea")].pop()?.focus(); }
  app.querySelectorAll("[data-still]").forEach(im => {
    im.ondragstart = e => e.dataTransfer.setData("text/still", im.dataset.still);
    im.onclick = () => addFromStill(im.dataset.still);
  });
  $("#add").onclick = addAtNow;
  const key = e => { if (e.key.toLowerCase() === "c" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); addAtNow(); } };
  document.addEventListener("keydown", key); timers.push(setInterval(() => { if (!location.hash.includes("/review/")) document.removeEventListener("keydown", key); }, 1000));
  if (video) {
    video.onloadedmetadata = drawMarkers;
    video.ontimeupdate = () => { const ph = $("#ph"); if (ph && video.duration) ph.style.left = (100 * video.currentTime / video.duration) + "%"; };
    tl.onclick = e => { const r = tl.getBoundingClientRect(); if (video.duration) video.currentTime = video.duration * (e.clientX - r.left) / r.width; };
  }
  $("#send").onclick = async () => {
    const unsent = items.filter(c => !c.sent && c.text.trim());
    if (!unsent.length) return toast("Write a note first");
    await api(`/api/videos/${name}/comments/${which}`, { method: "POST", body: { items } });
    try { const r = await api(`/api/videos/${name}/notes`, { method: "POST", body: { review: which } }); toast("Notes sent"); followJob(name, r.job);
      items = (await api(`/api/videos/${name}/comments/${which}`)).items; drawComments(); } catch (e) { toast(e.message); }
  };
  drawComments();
}

route();
