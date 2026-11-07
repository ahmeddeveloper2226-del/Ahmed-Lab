/**
 * The month -> subject filter -> week table, shared by Home (compact) and the
 * Lectures tab (big). Months show first; nothing else appears until a month
 * is clicked. Clicking the same month again collapses it.
 */
import { t } from "/assets/js/i18n.js";
import { apiGet, apiPatch } from "/assets/js/api.js";
import { showToast } from "/assets/js/toast.js";
import { subjectLabel, subjectColor, subjectIcon } from "/assets/js/subject-meta.js";
import { esc, safeUrl } from "/assets/js/util.js";
import { lecToolsHtml, installLectureTools } from "/assets/js/lecture-tools.js";

const CAL_ICON = `<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="4"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>`;
const OPEN_ICON = `<svg viewBox="0 0 24 24"><path d="M7 17 17 7M8 7h9v9"/></svg>`;

export async function mountCalendar(root, { big = false, onChange } = {}) {
  const lang = document.documentElement.lang === "ar" ? "ar" : "en";
  root.classList.add("cal-view");
  root.classList.toggle("big", big);
  root.innerHTML = `<div class="month-grid"></div><div class="chip-group filter-row" hidden></div><div class="weeks"></div>`;
  const monthGrid = root.querySelector(".month-grid");
  const filterRow = root.querySelector(".filter-row");
  const weeksEl = root.querySelector(".weeks");

  let months = [];
  let active = -1;
  let filter = "all";

  monthGrid.innerHTML = [0, 1, 2, 3].map(() => `<div class="month-card skeleton"></div>`).join("");
  try {
    months = await apiGet("/home/calendar");
  } catch {
    monthGrid.innerHTML = `<p class="cal-hint" style="grid-column:1/-1">${esc(t("common.error.generic"))}</p>`;
    return;
  }
  if (!months.length) {
    monthGrid.innerHTML = `<p class="cal-hint" style="grid-column:1/-1">${esc(t("home.empty"))}</p>`;
    return;
  }

  const pctOf = (m) => (m.total_lectures ? Math.round((100 * m.completed_lectures) / m.total_lectures) : 0);
  const fmt = (d) => new Date(d).toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB", { day: "numeric", month: "short" });

  monthGrid.innerHTML = months.map((m, i) => `
    <button class="month-card" data-m="${i}" style="--i:${i}" aria-pressed="false">
      <span class="mc-icon">${CAL_ICON}<b>${i + 1}</b></span>
      <strong>${esc(lang === "ar" ? m.label_ar : m.label_en)}</strong>
      <span class="mc-pct">${pctOf(m)}%</span>
      <span class="text-tiny mc-count">${m.completed_lectures}/${m.total_lectures}</span>
      <span class="mc-track"><i style="width:${pctOf(m)}%"></i></span>
    </button>`).join("");

  function refreshCards() {
    months.forEach((m, i) => {
      m.completed_lectures = m.weeks.reduce((n, w) => n + Object.values(w.subjects).flat().filter((l) => l.is_completed).length, 0);
      const card = monthGrid.children[i];
      card.querySelector(".mc-count").textContent = `${m.completed_lectures}/${m.total_lectures}`;
      card.querySelector(".mc-pct").textContent = `${pctOf(m)}%`;
      card.querySelector(".mc-track i").style.width = `${pctOf(m)}%`;
    });
  }

  function lecCard(lec, slug) {
    const s = lec.subject_slug || slug;
    const url = safeUrl(lec.lecture_url);
    return `
      <div class="lec-card ${lec.is_completed ? "done" : ""}" style="--c:${subjectColor(s)}">
        <button class="lecture-checkbox ${lec.is_completed ? "checked" : ""}" data-enrollment="${esc(lec.enrollment_id)}" data-lecture="${esc(lec.id)}" data-completed="${!!lec.is_completed}" aria-label="toggle"></button>
        <div class="lec-body">
          <span class="lec-title">${esc(lec.title)}</span>
        </div>
        ${url ? `<a class="lec-open" href="${url}" target="_blank" rel="noopener" title="${esc(t("home.open_lecture"))}" aria-label="${esc(t("home.open_lecture"))}">${OPEN_ICON}</a>` : ""}
        ${lecToolsHtml(lec, lec.enrollment_id)}
      </div>`;
  }

  function column(kind, lecs, slug) {
    const body = lecs.length
      ? lecs.map((l) => lecCard(l, slug)).join("")
      : `<div class="col-empty">${esc(t(kind === "done" ? "cal.none_done" : "cal.all_done"))}</div>`;
    return `<div class="sjb-col ${kind}">
      <h5>${esc(t(kind === "done" ? "home.done" : "home.left"))}<b>${lecs.length}</b></h5>
      <div class="col-list">${body}</div>
    </div>`;
  }

  function subjectBlock(slug, lecs) {
    const done = lecs.filter((l) => l.is_completed);
    const left = lecs.filter((l) => !l.is_completed);
    return `<div class="sj-block" style="--c:${subjectColor(slug)}">
      <div class="sjb-head">
        <span class="sjb-ico">${subjectIcon(slug, 18)}</span>
        <strong>${esc(subjectLabel(slug, lang))}</strong>
        <span class="sjb-count">${done.length}/${lecs.length}</span>
      </div>
      <div class="sjb-cols">${column("done", done, slug)}${column("left", left, slug)}</div>
    </div>`;
  }

  function weekRowHtml(week, wi, isStatic) {
    const blocks = Object.entries(week.subjects)
      .filter(([slug, lecs]) => lecs.length && (filter === "all" || slug === filter))
      .map(([slug, lecs]) => subjectBlock(slug, lecs))
      .join("");
    if (!blocks) return "";
    return `<div class="week-row ${isStatic ? "static" : ""}" data-w="${wi}" style="--i:${wi}">
      <span class="week-pill">${esc(t("home.week"))} ${week.week_index}<small>${fmt(week.start_date)} - ${fmt(week.end_date)}</small></span>
      <div class="wk-subjects">${blocks}</div>
    </div>`;
  }

  function renderWeeks() {
    if (active < 0) {
      filterRow.hidden = true;
      weeksEl.innerHTML = `<p class="cal-hint">${esc(t("cal.pick_month"))}</p>`;
      return;
    }
    const month = months[active];
    const slugs = [...new Set(month.weeks.flatMap((w) => Object.keys(w.subjects)))];
    filterRow.hidden = false;
    filterRow.innerHTML = [`<button class="chip ${filter === "all" ? "selected" : ""}" data-f="all">${esc(t("home.all"))}</button>`]
      .concat(slugs.map((s) => `<button class="chip with-ico ${filter === s ? "selected" : ""}" data-f="${esc(s)}">${subjectIcon(s, 15)}${esc(subjectLabel(s, lang))}</button>`))
      .join("");

    const html = month.weeks.map((week, wi) => weekRowHtml(week, wi, false)).join("");
    weeksEl.innerHTML = html || `<p class="cal-hint">${esc(t("cal.no_lectures"))}</p>`;
  }

  function setActive(i) {
    active = i;
    filter = "all";
    [...monthGrid.children].forEach((c, idx) => {
      c.classList.toggle("active", idx === i);
      c.setAttribute("aria-pressed", String(idx === i));
    });
    renderWeeks();
    if (i >= 0) {
      requestAnimationFrame(() => {
        const y = weeksEl.getBoundingClientRect().top;
        if (y > window.innerHeight * 0.6) window.scrollBy({ top: y - window.innerHeight * 0.4, behavior: "smooth" });
      });
    }
  }

  renderWeeks();

  monthGrid.addEventListener("click", (e) => {
    const card = e.target.closest("[data-m]");
    if (!card) return;
    const i = Number(card.dataset.m);
    setActive(i === active ? -1 : i);
  });
  filterRow.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-f]");
    if (!chip) return;
    filter = chip.dataset.f;
    renderWeeks();
  });
  // Notes & rules / explain-to-AI buttons. Keep the "has data" dot in the
  // cached lecture objects so it survives the week being re-drawn.
  installLectureTools(weeksEl, ({ enrollmentId, lectureId }, kind, value) => {
    months.forEach((m) => m.weeks.forEach((w) => Object.values(w.subjects).flat().forEach((l) => {
      if (String(l.id) === lectureId && String(l.enrollment_id) === enrollmentId) l[kind] = value;
    })));
  });
  weeksEl.addEventListener("click", async (e) => {
    const cb = e.target.closest(".lecture-checkbox");
    if (!cb) return;
    const { lecture, enrollment } = cb.dataset;
    const was = cb.dataset.completed === "true";
    const next = !was;
    let rowEl = cb.closest(".week-row");

    const setLec = (v) => months.forEach((m) => m.weeks.forEach((w) => Object.values(w.subjects).flat().forEach((l) => {
      if (String(l.id) === lecture && String(l.enrollment_id) === enrollment) l.is_completed = v;
    })));
    // Re-draw just this week so the lecture slides to the other column.
    const redraw = (movedId) => {
      const wi = Number(rowEl.dataset.w);
      const tmp = document.createElement("div");
      tmp.innerHTML = weekRowHtml(months[active].weeks[wi], wi, true);
      const fresh = tmp.firstElementChild;
      if (!fresh) return;
      rowEl.replaceWith(fresh);
      rowEl = fresh;
      if (movedId) {
        const moved = [...fresh.querySelectorAll(".lecture-checkbox")].find((c) => c.dataset.lecture === movedId && c.dataset.enrollment === enrollment);
        moved?.closest(".lec-card")?.classList.add("moved");
      }
    };

    setLec(next);
    refreshCards();
    redraw(lecture);
    try {
      await apiPatch(`/subjects/${enrollment}/lectures/${lecture}`, { is_completed: next });
      onChange?.();
    } catch {
      showToast(t("common.error.generic"));
      setLec(was);
      refreshCards();
      redraw(null);
    }
  });
}