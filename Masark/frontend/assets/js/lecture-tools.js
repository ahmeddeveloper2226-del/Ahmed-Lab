/**
 * Per-lecture study tools shown on every lecture card (done or not):
 *   1) "Notes & rules"                 - free text the student keeps for the lecture
 *   2) "If you understood, explain"    - teach the lecture to an AI classmate
 *
 * Usage (any page that renders .lec-card elements):
 *   lecToolsHtml(lec, enrollmentId)   -> markup for the two buttons
 *   installLectureTools(rootEl, onFlagsChange?)  -> one delegated click handler
 * The cards themselves only need to carry data-* attributes (see lecToolsHtml).
 */
import { t } from "/assets/js/i18n.js";
import { apiGet, apiPut, apiPost, apiDelete } from "/assets/js/api.js";
import { showToast } from "/assets/js/toast.js";
import { esc } from "/assets/js/util.js";

const NOTE_ICON = `<svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></svg>`;
const AI_ICON = `<svg viewBox="0 0 24 24"><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/></svg>`;
const CLOSE_ICON = `<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>`;

/* ------------------------------------------------------------------ */
/* Buttons on the card                                                  */
/* ------------------------------------------------------------------ */
export function lecToolsHtml(lec, enrollmentId) {
  const attrs = `data-enrollment="${esc(enrollmentId)}" data-lecture="${esc(lec.id)}" data-title="${esc(lec.title)}"`;
  return `<div class="lec-tools">
    <button type="button" class="lec-tool ${lec.has_notes ? "has-data" : ""}" data-tool="notes" ${attrs}>${NOTE_ICON}<span>${esc(t("lt.notes_btn"))}</span></button>
    <button type="button" class="lec-tool ${lec.has_explain ? "has-data" : ""}" data-tool="explain" ${attrs}>${AI_ICON}<span>${esc(t("lt.explain_btn"))}</span></button>
  </div>`;
}

/** One delegated listener per container, so re-rendered cards keep working. */
const installed = new WeakSet();
export function installLectureTools(root, onFlag) {
  if (installed.has(root)) return; // tabs re-render often; never stack listeners
  installed.add(root);
  root.addEventListener("click", (e) => {
    const btn = e.target.closest(".lec-tool");
    if (!btn) return;
    e.preventDefault();
    const { enrollment, lecture, title, tool } = btn.dataset;
    const ctx = { enrollmentId: enrollment, lectureId: lecture, title };
    // Keep the dot on the button and in the cached data in sync.
    const flag = (kind, value) => {
      btn.classList.toggle("has-data", value);
      onFlag?.(ctx, kind, value);
    };
    if (tool === "notes") openNotes(ctx, (v) => flag("has_notes", v));
    else openExplain(ctx, (v) => flag("has_explain", v));
  });
}

/* ------------------------------------------------------------------ */
/* Shared sheet shell                                                   */
/* ------------------------------------------------------------------ */
function openSheet(title, icon, bodyHtml, { beforeClose } = {}) {
  const wrap = document.createElement("div");
  wrap.className = "sheet-backdrop open lt-sheet";
  wrap.innerHTML = `
    <div class="sheet-panel lt-panel" role="dialog" aria-modal="true">
      <div class="lt-head">
        <span class="lt-head-ico">${icon}</span>
        <div class="lt-head-txt"><strong>${esc(title.main)}</strong><small>${esc(title.sub)}</small></div>
        <button type="button" class="lt-close" aria-label="${esc(t("lt.close"))}">${CLOSE_ICON}</button>
      </div>
      <div class="lt-body">${bodyHtml}</div>
    </div>`;
  document.body.appendChild(wrap);
  document.body.classList.add("lt-lock");
  let closing = false;
  const close = async () => {
    if (closing) return;
    closing = true;
    // e.g. the notes card saves unsaved text first so nothing is ever lost.
    let ok;
    try { ok = await beforeClose?.(); } catch { ok = true; }
    if (ok === false) { closing = false; return; } // save failed: stay open, keep the text
    wrap.remove();
    if (!document.querySelector(".lt-sheet")) document.body.classList.remove("lt-lock");
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (ev) => { if (ev.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  wrap.addEventListener("click", (ev) => { if (ev.target === wrap) close(); });
  wrap.querySelector(".lt-close").addEventListener("click", close);
  return { wrap, close, q: (sel) => wrap.querySelector(sel) };
}

/* ------------------------------------------------------------------ */
/* 1) Notes & rules                                                     */
/* ------------------------------------------------------------------ */
function openNotes({ enrollmentId, lectureId, title }, onHasData) {
  const base = `/subjects/${encodeURIComponent(enrollmentId)}/lectures/${encodeURIComponent(lectureId)}/notes`;
  let autosave = async () => {};
  const sheet = openSheet(
    { main: t("lt.notes_title"), sub: title },
    NOTE_ICON,
    `<label class="lt-label" for="ltNotes">${esc(t("lt.notes_label"))}</label>
     <textarea id="ltNotes" class="input lt-area" rows="7" maxlength="20000" placeholder="${esc(t("lt.notes_ph"))}" disabled></textarea>
     <label class="lt-label" for="ltRules">${esc(t("lt.rules_label"))}</label>
     <textarea id="ltRules" class="input lt-area" rows="6" maxlength="20000" placeholder="${esc(t("lt.rules_ph"))}" disabled></textarea>
     <div class="lt-foot">
       <span class="lt-status text-tiny" id="ltStatus">${esc(t("lt.loading"))}</span>
       <button type="button" class="btn btn-primary" id="ltSave" disabled>${esc(t("lt.save"))}</button>
     </div>`,
    { beforeClose: () => autosave() }
  );
  const notesEl = sheet.q("#ltNotes");
  const rulesEl = sheet.q("#ltRules");
  const saveBtn = sheet.q("#ltSave");
  const status = sheet.q("#ltStatus");
  let saved = { notes: "", rules: "" };
  let loaded = false;

  const dirty = () => notesEl.value !== saved.notes || rulesEl.value !== saved.rules;
  const refreshStatus = () => { if (loaded) status.textContent = dirty() ? t("lt.unsaved") : t("lt.saved"); };

  async function save() {
    if (!loaded || !dirty()) return true;
    saveBtn.disabled = true;
    status.textContent = t("lt.saving");
    const payload = { notes: notesEl.value, rules: rulesEl.value };
    try {
      await apiPut(base, payload);
      saved = payload;
      onHasData(Boolean(payload.notes.trim() || payload.rules.trim()));
      status.textContent = t("lt.saved");
      showToast(t("lt.saved"));
      return true;
    } catch {
      status.textContent = t("lt.save_failed");
      showToast(t("lt.save_failed"));
      return false;
    } finally {
      saveBtn.disabled = false;
    }
  }

  // Closing (X, backdrop or Esc) with unsaved text saves it first.
  autosave = async () => (dirty() ? save() : true);

  notesEl.addEventListener("input", refreshStatus);
  rulesEl.addEventListener("input", refreshStatus);
  saveBtn.addEventListener("click", save);
  sheet.wrap.addEventListener("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") { ev.preventDefault(); save(); }
  });

  (async () => {
    try {
      const data = await apiGet(base);
      saved = { notes: data.notes || "", rules: data.rules || "" };
      notesEl.value = saved.notes;
      rulesEl.value = saved.rules;
      notesEl.disabled = rulesEl.disabled = saveBtn.disabled = false;
      loaded = true;
      status.textContent = saved.notes || saved.rules ? t("lt.saved") : "";
      notesEl.focus();
    } catch {
      status.textContent = t("common.error.generic");
    }
  })();
}

/* ------------------------------------------------------------------ */
/* 2) "If you understood, then explain" AI chat                         */
/* ------------------------------------------------------------------ */
/** Tiny, safe formatter for AI text: escapes first, then **bold**, "- " bullets, ## headings. */
export function renderRich(text) {
  const lines = String(text ?? "").split(/\r?\n/);
  const out = [];
  let inList = false;
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  const closeList = () => { if (inList) { out.push("</ul>"); inList = false; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    const heading = line.match(/^\s*#{1,4}\s+(.*)$/);
    if (bullet) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else {
      closeList();
      if (heading) out.push(`<h4>${inline(heading[1])}</h4>`);
      else if (line.trim()) out.push(`<p>${inline(line)}</p>`);
    }
  }
  closeList();
  return out.join("");
}

function openExplain({ enrollmentId, lectureId, title }, onHasData) {
  const base = `/subjects/${encodeURIComponent(enrollmentId)}/lectures/${encodeURIComponent(lectureId)}/explain`;
  const sheet = openSheet(
    { main: t("lt.explain_title"), sub: title },
    AI_ICON,
    `<div class="lt-chat">
       <div class="chat-scroll lt-scroll" id="ltScroll"></div>
       <div class="lt-actions">
         <button type="button" class="btn btn-outline btn-sm" id="ltFinish">${esc(t("lt.finish"))}</button>
         <button type="button" class="btn btn-ghost btn-sm" id="ltReset">${esc(t("lt.reset"))}</button>
       </div>
       <div class="chat-input-row">
         <textarea class="input lt-input" id="ltInput" rows="2" maxlength="4000" placeholder="${esc(t("lt.explain_ph"))}"></textarea>
         <button type="button" class="btn btn-primary" id="ltSend">${esc(t("common.send"))}</button>
       </div>
     </div>`
  );
  const scroll = sheet.q("#ltScroll");
  const input = sheet.q("#ltInput");
  const sendBtn = sheet.q("#ltSend");
  const finishBtn = sheet.q("#ltFinish");
  const resetBtn = sheet.q("#ltReset");
  let hasUserMsg = false;
  let busy = false;

  const toBottom = () => { scroll.scrollTop = scroll.scrollHeight; };
  function bubble(text, from, rich = false) {
    const div = document.createElement("div");
    div.className = `chat-bubble from-${from}`;
    if (rich) { div.classList.add("rich"); div.innerHTML = renderRich(text); } else div.textContent = text;
    scroll.appendChild(div);
    toBottom();
    return div;
  }
  function showSummary(text) {
    scroll.querySelector(".lt-summary")?.remove();
    const card = document.createElement("div");
    card.className = "lt-summary rich";
    card.innerHTML = `<div class="lt-summary-head">${AI_ICON}<strong>${esc(t("lt.summary_title"))}</strong></div>${renderRich(text)}`;
    scroll.appendChild(card);
    toBottom();
  }
  function typing() {
    const el = document.createElement("div");
    el.className = "chat-bubble from-model typing";
    el.innerHTML = "<i></i><i></i><i></i>";
    scroll.appendChild(el);
    toBottom();
    return el;
  }
  function setBusy(v) {
    busy = v;
    sendBtn.disabled = finishBtn.disabled = resetBtn.disabled = v;
  }
  const errMsg = (err) => (err?.status === 429 ? t("lt.too_many") : t("common.error.generic"));

  function drawIntro() { bubble(t("lt.explain_intro"), "model"); }

  async function send() {
    const message = input.value.trim();
    if (!message || busy) return;
    input.value = "";
    bubble(message, "user");
    setBusy(true);
    const dots = typing();
    try {
      const { reply } = await apiPost(base, { message });
      dots.remove();
      bubble(reply, "model", true);
      hasUserMsg = true;
      onHasData(true);
    } catch (err) {
      dots.remove();
      bubble(errMsg(err), "model");
      input.value = message; // give the text back so nothing is lost
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  async function finish() {
    if (busy) return;
    if (!hasUserMsg) { showToast(t("lt.need_chat")); return; }
    setBusy(true);
    const dots = typing();
    try {
      const { summary } = await apiPost(`${base}/summary`, {});
      dots.remove();
      showSummary(summary);
    } catch (err) {
      dots.remove();
      bubble(errMsg(err), "model");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (busy || !hasUserMsg) return;
    if (!window.confirm(t("lt.reset_confirm"))) return;
    setBusy(true);
    try {
      await apiDelete(base);
      scroll.innerHTML = "";
      hasUserMsg = false;
      onHasData(false);
      drawIntro();
    } catch (err) {
      showToast(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  sendBtn.addEventListener("click", send);
  finishBtn.addEventListener("click", finish);
  resetBtn.addEventListener("click", reset);
  // Enter sends, Shift+Enter makes a new line (explanations are often multi-line).
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); send(); }
  });

  // Load the saved chat for this lecture.
  scroll.innerHTML = `<div class="skeleton" style="height:90px;border-radius:18px"></div>`;
  (async () => {
    try {
      const data = await apiGet(base);
      scroll.innerHTML = "";
      drawIntro();
      for (const m of data.messages || []) bubble(m.content, m.role === "user" ? "user" : "model", m.role !== "user");
      hasUserMsg = (data.messages || []).some((m) => m.role === "user");
      if (data.summary) showSummary(data.summary);
      toBottom();
    } catch {
      scroll.innerHTML = "";
      bubble(t("common.error.generic"), "model");
    }
    input.focus();
  })();
}