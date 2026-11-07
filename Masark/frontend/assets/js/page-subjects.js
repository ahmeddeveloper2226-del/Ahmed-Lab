import { initI18n, t } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { apiGet, apiPost, apiPatch, apiDelete } from "/assets/js/api.js";
import { renderNav } from "/assets/js/nav.js";
import { paintDonut } from "/assets/js/charts.js";
import { showToast } from "/assets/js/toast.js";
import { initTheme } from "/assets/js/theme.js";
import { renderUrlLectureFlow } from "/assets/js/subject-url-flow.js";
import { SUBJECT_SLUGS, subjectColor, subjectLabel, subjectIcon } from "/assets/js/subject-meta.js";
import { esc, safeUrl } from "/assets/js/util.js";
import { lecToolsHtml, installLectureTools } from "/assets/js/lecture-tools.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
const $ = (id) => document.getElementById(id);
const pctOf = (e) => (e.total_lectures ? Math.round((100 * e.completed_lectures) / e.total_lectures) : 0);
const raf2 = (fn) => requestAnimationFrame(() => requestAnimationFrame(fn));
const OPEN_ICON = `<svg viewBox="0 0 24 24"><path d="M7 17 17 7M8 7h9v9"/></svg>`;
const ARROW = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>`;
const PLUS = `<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`;

let enrollments = [];
let current = null;
let gridDirty = false;
// Subjects that get an extra interactive tab (Biology: 3D skeleton, Geography: world map, Math: calculator)
const TOOL_TABS = {
  biology: { key: "skeleton", label: "subjects.tab.skeleton" },
  geography: { key: "geomap", label: "subjects.tab.geomap" },
  math: { key: "calculator", label: "subjects.tab.calculator" },
};
const TOOL_BADGE = { biology: "3D", geography: "MAP", math: "fx" };
const FLUSH_TABS = new Set(Object.values(TOOL_TABS).map((x) => x.key));
let skeletonHandle = null;                       // the live interactive tool (skeleton / map / calculator), if its tab is open
const stopSkeleton = () => { skeletonHandle?.dispose?.(); skeletonHandle = null; };

/* ------------------------------------------------------------------ */
/* Tile grid                                                            */
/* ------------------------------------------------------------------ */
const grid = $("subjectGrid");

async function loadGrid() {
  grid.innerHTML = [0, 1, 2].map(() => `<div class="skeleton sj-skel"></div>`).join("");
  try {
    enrollments = await apiGet("/subjects");
  } catch {
    grid.innerHTML = `<p class="cal-hint" style="grid-column:1/-1">${esc(t("common.error.generic"))}</p>`;
    return;
  }
  $("subjectCount").textContent = t("subjects.count", { n: enrollments.length });

  const tiles = enrollments.map((s, i) => {
    const pct = pctOf(s);
    const slug = s.subject_slug;
    return `
      <button class="sj-tile" style="--c:${subjectColor(slug)};--i:${i};--w:${pct}%" data-id="${esc(s.id)}">
        <span class="sj-glow"></span>
        <span class="sj-watermark">${subjectIcon(slug, 180)}</span>
        <span class="sj-top">
          <span class="sj-badge">${subjectIcon(slug, 32)}</span>
          <span class="sj-pill ${pct >= 50 ? "good" : "bad"}">${pct}%</span>
        </span>
        ${TOOL_BADGE[slug] ? `<span class="sj-3d">${TOOL_BADGE[slug]}</span>` : ""}
        <span class="sj-mid">
          <strong class="sj-name">${esc(subjectLabel(slug, lang, s.subject_name))}</strong>
          <span class="sj-meta">${esc(t("subjects.progress", { done: s.completed_lectures, total: s.total_lectures }))}</span>
        </span>
        <span class="sj-foot">
          <span class="sj-bar"><i></i></span>
          <span class="sj-arrow">${ARROW}</span>
        </span>
      </button>`;
  });
  tiles.push(`
    <button class="sj-tile sj-add" style="--i:${enrollments.length}" data-add="1">
      <span class="sj-plus">${PLUS}</span>
      <strong>${esc(t("subjects.add"))}</strong>
    </button>`);
  grid.innerHTML = tiles.join("")
    + (enrollments.length ? "" : `<p class="cal-hint" style="grid-column:1/-1">${esc(t("subjects.empty"))}</p>`);
  raf2(() => grid.querySelectorAll(".sj-tile").forEach((el) => el.classList.add("in")));
}

grid.addEventListener("click", (e) => {
  const tile = e.target.closest(".sj-tile");
  if (!tile) return;
  if (tile.dataset.add) openAddSubject();
  else openDetail(tile.dataset.id);
});

/* 3D tilt + glare that follows the pointer (mouse only, respects reduced motion) */
if (matchMedia("(hover:hover) and (pointer:fine)").matches && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  grid.addEventListener("pointermove", (e) => {
    const tile = e.target.closest(".sj-tile");
    if (!tile) return;
    const r = tile.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top) / r.height;
    tile.style.setProperty("--ry", `${(x - 0.5) * 12}deg`);
    tile.style.setProperty("--rx", `${(0.5 - y) * 12}deg`);
    tile.style.setProperty("--mx", `${x * 100}%`);
    tile.style.setProperty("--my", `${y * 100}%`);
  });
  grid.addEventListener("pointerout", (e) => {
    const tile = e.target.closest(".sj-tile");
    if (!tile || tile.contains(e.relatedTarget)) return;
    tile.style.setProperty("--rx", "0deg");
    tile.style.setProperty("--ry", "0deg");
  });
}

await loadGrid();

/* ------------------------------------------------------------------ */
/* Detail sheet                                                         */
/* ------------------------------------------------------------------ */
const sheet = $("detailSheet");
const panel = $("dsPanel");
const detailTabs = $("detailTabs");
const detailBody = $("detailBody");

const TABS = [
  { key: "overview", label: "subjects.tab.overview" },
  { key: "lectures", label: "subjects.tab.lectures" },
  { key: "procrastination_ai", label: "subjects.tab.procrastination_ai" },
  { key: "help_ai", label: "subjects.tab.help_ai" },
];

function closeDetail() {
  stopSkeleton();
  sheet.classList.remove("open");
  document.body.style.overflow = "";
  if (gridDirty) { gridDirty = false; loadGrid(); }
}
$("closeDetailBtn").addEventListener("click", closeDetail);
sheet.addEventListener("click", (e) => { if (e.target === sheet) closeDetail(); });
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (sheet.classList.contains("open")) closeDetail();
  else closeSheet();
});

function updateHeroSub() {
  $("dsSub").textContent = t("subjects.progress", { done: current.completed_lectures, total: current.total_lectures });
}

function openDetail(id) {
  const e = enrollments.find((x) => x.id === id);
  if (!e) return;
  current = e;
  panel.style.setProperty("--c", subjectColor(e.subject_slug));
  $("dsBadge").innerHTML = subjectIcon(e.subject_slug, 34);
  $("detailTitle").textContent = subjectLabel(e.subject_slug, lang, e.subject_name);
  updateHeroSub();
  const tabs = TOOL_TABS[e.subject_slug] ? [TABS[0], TOOL_TABS[e.subject_slug], ...TABS.slice(1)] : TABS;
  detailTabs.innerHTML = tabs.map((tab, i) => `<button class="detail-tab ${i === 0 ? "active" : ""}" data-tab="${tab.key}">${esc(t(tab.label))}</button>`).join("");
  sheet.classList.add("open");
  document.body.style.overflow = "hidden";
  renderTab("overview");
}

detailTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".detail-tab");
  if (!btn) return;
  detailTabs.querySelectorAll(".detail-tab").forEach((b) => b.classList.toggle("active", b === btn));
  renderTab(btn.dataset.tab);
});

function renderTab(key) {
  stopSkeleton();
  detailBody.classList.toggle("flush", FLUSH_TABS.has(key));
  detailBody.classList.remove("swap");
  void detailBody.offsetWidth;
  detailBody.classList.add("swap");
  if (key === "skeleton") return renderSkeleton();
  if (key === "geomap") return renderGeoMap();
  if (key === "calculator") return renderCalculator();
  if (key === "overview") return renderOverview();
  if (key === "lectures") return renderLecturesTab();
  if (key === "procrastination_ai") return renderProcrastinationChat();
  if (key === "help_ai") return renderHelpChat();
}

/** Mounts an interactive tool module into the (flush) detail body; disposed by stopSkeleton() on tab change / close. */
async function mountTool(hostId, hostClass, openHref, openLabel, loader) {
  detailBody.innerHTML = `<div class="${hostClass}"><div id="${hostId}" class="${hostClass}"></div><a class="${hostClass === "gm-embed" ? "gm-open" : "sk-open"}" href="${openHref}" target="_blank" rel="noopener">${esc(t(openLabel))} ↗</a></div>`;
  const host = $(hostId);
  try {
    const mod = await loader();
    if (!host.isConnected || !detailBody.classList.contains("flush")) return;      // user switched tab while loading
    const handle = await mod(host, { lang });
    if (!host.isConnected) { handle.dispose(); return; }
    skeletonHandle = handle;
  } catch (err) {
    console.error("interactive tab failed", err);
    host.innerHTML = `<p class="cal-hint" style="margin:24px">${esc(t("common.error.generic"))}</p>`;
  }
}
const renderGeoMap = () => mountTool("gmHost", "gm-embed", "/map.html", "subjects.map_full", async () => (await import("/assets/js/geo/geo-viewer.js")).mountGeoMap);
const renderCalculator = () => mountTool("calcHost", "calc-embed", "/calculator.html", "subjects.calc_full", async () => (await import("/assets/js/calc/calculator.js")).mountCalculator);

async function renderSkeleton() {
  detailBody.innerHTML = `<div class="sk-embed"><div id="skHost" class="sk-embed"></div><a class="sk-open" href="/skeleton.html" target="_blank" rel="noopener">${esc(t("subjects.sk_full"))} ↗</a></div>`;
  const host = $("skHost");
  try {
    const { mountSkeleton } = await import("/assets/js/skeleton/skeleton-viewer.js");
    if (!host.isConnected || !detailBody.classList.contains("flush")) return;      // user switched tab while loading
    const handle = await mountSkeleton(host, { lang });
    if (!host.isConnected) { handle.dispose(); return; }
    skeletonHandle = handle;
  } catch (err) {
    console.error("skeleton viewer failed", err);
    host.innerHTML = `<p class="cal-hint" style="margin:24px">${esc(t("common.error.generic"))}</p>`;
  }
}

function renderOverview() {
  const e = current;
  const pct = pctOf(e);
  const left = Math.max(0, e.total_lectures - e.completed_lectures);
  detailBody.innerHTML = `
    <div class="ov-grid">
      <div class="donut-wrap"><div class="donut" id="ovDonut" style="width:150px;height:150px"><span class="donut-label" style="font-size:1.6rem">${pct}%</span></div></div>
      <div class="ov-stats">
        <div class="ov-stat"><b>${e.completed_lectures}</b><span>${esc(t("home.done"))}</span></div>
        <div class="ov-stat"><b>${left}</b><span>${esc(t("home.left"))}</span></div>
        <div class="ov-stat"><b>${e.total_lectures}</b><span>${esc(t("subjects.total"))}</span></div>
      </div>
    </div>
    <button class="btn btn-outline btn-block ov-remove" id="removeSubjectBtn">${esc(t("subjects.remove"))}</button>`;
  raf2(() => paintDonut($("ovDonut"), pct));
  $("removeSubjectBtn").addEventListener("click", async () => {
    if (!confirm(t("subjects.remove_confirm"))) return;
    const removeBtn = $("removeSubjectBtn");
    if (removeBtn.disabled) return; // ignore double clicks while deleting
    const removeLabel = removeBtn.innerHTML;
    removeBtn.disabled = true;
    removeBtn.innerHTML = `<span class="spinner"></span>`;
    try {
      await apiDelete(`/subjects/${e.id}`);
      gridDirty = true;
      closeDetail();
    } catch {
      showToast(t("common.error.generic"));
      removeBtn.disabled = false;
      removeBtn.innerHTML = removeLabel;
    }
  });
}

async function renderLecturesTab() {
  const e = current;
  detailBody.innerHTML = `<div class="skeleton" style="height:220px"></div>`;
  try {
    const months = await apiGet("/home/calendar");
    const groups = [];
    for (const month of months) {
      const rows = [];
      for (const week of month.weeks) for (const lec of week.subjects[e.subject_slug] || []) rows.push(lec);
      if (rows.length) groups.push({ label: lang === "ar" ? month.label_ar : month.label_en, rows });
    }
    if (!groups.length) {
      detailBody.innerHTML = `<p class="cal-hint">${esc(t("home.empty"))}</p>`;
      return;
    }
    detailBody.innerHTML = groups.map((g) => `
      <h4 class="ls-month">${esc(g.label)}</h4>
      <div class="lec-grid" style="margin-bottom:var(--sp-4)">
        ${g.rows.map((lec) => {
          const url = safeUrl(lec.lecture_url);
          return `<div class="lec-card ${lec.is_completed ? "done" : ""}" style="--c:${subjectColor(e.subject_slug)}">
            <button class="lecture-checkbox ${lec.is_completed ? "checked" : ""}" data-lecture="${esc(lec.id)}" data-completed="${!!lec.is_completed}" aria-label="toggle"></button>
            <div class="lec-body"><span class="lec-title">${esc(lec.title)}</span></div>
            ${url ? `<a class="lec-open" href="${url}" target="_blank" rel="noopener" title="${esc(t("home.open_lecture"))}">${OPEN_ICON}</a>` : ""}
            ${lecToolsHtml(lec, e.id)}
          </div>`;
        }).join("")}
      </div>`).join("");
    installLectureTools(detailBody);
    detailBody.querySelectorAll(".lecture-checkbox").forEach((cb) => {
      cb.addEventListener("click", async () => {
        const was = cb.dataset.completed === "true";
        const next = !was;
        const card = cb.closest(".lec-card");
        const apply = (v) => { cb.classList.toggle("checked", v); cb.dataset.completed = String(v); card.classList.toggle("done", v); };
        apply(next);
        cb.classList.remove("just-checked");
        void cb.offsetWidth;
        cb.classList.add("just-checked");
        try {
          await apiPatch(`/subjects/${e.id}/lectures/${cb.dataset.lecture}`, { is_completed: next });
          e.completed_lectures += next ? 1 : -1;
          gridDirty = true;
          updateHeroSub();
        } catch {
          showToast(t("common.error.generic"));
          apply(was);
        }
      });
    });
  } catch {
    detailBody.innerHTML = `<p class="cal-hint">${esc(t("common.error.generic"))}</p>`;
  }
}

/* ---- chats ---- */
function chatShellHtml(introText, placeholderKey) {
  return `
    <div class="chat-shell">
      <div class="chat-scroll" id="chatScroll" style="flex:1;overflow-y:auto">
        <div class="chat-bubble from-model">${esc(introText)}</div>
      </div>
      <div class="chat-input-row">
        <input class="input" id="chatInput" placeholder="${esc(t(placeholderKey))}">
        <button class="btn btn-primary" id="chatSendBtn">${esc(t("common.send"))}</button>
      </div>
    </div>`;
}

function renderProcrastinationChat() {
  detailBody.innerHTML = chatShellHtml(t("subjects.procrastination.intro"), "subjects.procrastination.placeholder");
  wireChat(async (message) => (await apiPost("/ai/procrastination", { message })).reply);
}

function renderHelpChat() {
  const e = current;
  detailBody.innerHTML = chatShellHtml(t("subjects.help.placeholder"), "subjects.help.placeholder");
  wireChat(async (message) => (await apiPost("/ai/subject-qa", { subject_slug: e.subject_slug, question: message })).answer);
}

function wireChat(sendFn) {
  const scroll = $("chatScroll");
  const input = $("chatInput");
  const sendBtn = $("chatSendBtn");

  function bubble(text, from) {
    const div = document.createElement("div");
    div.className = `chat-bubble from-${from}`;
    div.textContent = text;
    scroll.appendChild(div);
    scroll.scrollTop = scroll.scrollHeight;
    return div;
  }

  async function send() {
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    bubble(message, "user");
    sendBtn.disabled = true;
    const typing = document.createElement("div");
    typing.className = "chat-bubble from-model typing";
    typing.innerHTML = "<i></i><i></i><i></i>";
    scroll.appendChild(typing);
    scroll.scrollTop = scroll.scrollHeight;
    try {
      const reply = await sendFn(message);
      typing.remove();
      bubble(reply, "model");
    } catch {
      typing.remove();
      bubble(t("common.error.generic"), "model");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }
  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (ev) => { if (ev.key === "Enter") send(); });
}

/* ------------------------------------------------------------------ */
/* Add-subject sheet (icon picker)                                      */
/* ------------------------------------------------------------------ */
const addSheet = $("addSubjectSheet");
const addContent = $("addSubjectContent");
$("addSubjectBtn").addEventListener("click", openAddSubject);
addSheet.addEventListener("click", (e) => { if (e.target === addSheet) closeSheet(); });
function closeSheet() { addSheet.classList.remove("open"); addContent.innerHTML = ""; }

function openAddSubject() {
  let slug = SUBJECT_SLUGS[0];
  let source = "platform";
  addSheet.classList.add("open");
  addContent.innerHTML = `
    <h2>${esc(t("subjects.pick"))}</h2>
    <div class="pick-grid" id="pickGrid">
      ${SUBJECT_SLUGS.map((s, i) => `
        <button class="pick-item ${i === 0 ? "selected" : ""}" data-slug="${s}" style="--c:${subjectColor(s)};--i:${i}">
          <span>${subjectIcon(s, 26)}</span>${esc(subjectLabel(s, lang))}
        </button>`).join("")}
    </div>
    <p class="text-small text-muted">${esc(t("onboarding.subjects.choose_source"))}</p>
    <div class="chip-group" id="sourceChips" style="margin:var(--sp-3) 0">
      <button class="chip selected" data-source="platform">${esc(t("onboarding.subjects.from_platform"))}</button>
      <button class="chip" data-source="manual">${esc(t("onboarding.subjects.manual"))}</button>
    </div>
    <div id="sourcePanel"></div>`;
  const panelEl = $("sourcePanel");

  $("pickGrid").addEventListener("click", (e) => {
    const item = e.target.closest(".pick-item");
    if (!item) return;
    slug = item.dataset.slug;
    $("pickGrid").querySelectorAll(".pick-item").forEach((b) => b.classList.toggle("selected", b === item));
  });
  $("sourceChips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    source = chip.dataset.source;
    $("sourceChips").querySelectorAll(".chip").forEach((c) => c.classList.toggle("selected", c === chip));
    renderSourcePanel();
  });

  async function submitSubject(payload) {
    try {
      await apiPost("/subjects", payload);
      closeSheet();
      showToast(t("subjects.added"));
      loadGrid();
    } catch {
      showToast(t("common.error.generic"));
    }
  }

  function renderSourcePanel() {
    if (source === "manual") {
      panelEl.innerHTML = `
        <div class="field"><textarea class="input" id="manualLectures" rows="5"></textarea></div>
        <button class="btn btn-primary btn-block" id="confirmManual">${esc(t("onboarding.subjects.add"))}</button>`;
      $("confirmManual").addEventListener("click", () => {
        const lines = $("manualLectures").value.split("\n").map((l) => l.trim()).filter(Boolean);
        submitSubject({
          subject_slug: slug,
          subject_name: subjectLabel(slug, lang),
          source_mode: "manual",
          manual_lectures: lines.map((title, order) => ({ title, order })),
          already_completed_lecture_ids: [],
        });
      });
      return;
    }
    renderUrlLectureFlow(panelEl, {
      onConfirm: (fields) => submitSubject({
        subject_slug: slug,
        subject_name: subjectLabel(slug, lang),
        source_mode: "platform",
        manual_lectures: [],
        ...fields,
      }),
    });
  }
  renderSourcePanel();
}