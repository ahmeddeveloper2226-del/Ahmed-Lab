import { initI18n, t } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { apiGet, apiPost, apiPatch } from "/assets/js/api.js";
import { renderNav } from "/assets/js/nav.js";
import { showToast } from "/assets/js/toast.js";
import { initTheme } from "/assets/js/theme.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
const contentEl = document.getElementById("planContent");
const regenBtn = document.getElementById("regenerateBtn");

const DAY_KEYS = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"];
function dayLabel(isoDate) {
  const d = new Date(isoDate);
  const offset = (d.getDay() + 1) % 7; // JS Sun=0 -> our Saturday-start index
  return t(`study_plan.day.${DAY_KEYS[offset]}`);
}

function renderPlan(plan) {
  regenBtn.style.display = "inline-flex";
  const byDay = {};
  for (const task of plan.tasks) {
    (byDay[task.day] ||= []).push(task);
  }
  const days = Object.keys(byDay).sort();

  contentEl.innerHTML = `
    <div class="card-soft" style="margin-bottom:var(--sp-5)">
      ${lang === "ar" ? plan.summary_ar : plan.summary_en}
    </div>
    ${days.map((day) => `
      <div class="plan-day-group">
        <h3>${dayLabel(day)}</h3>
        <div class="card" style="margin-top:var(--sp-3)">
          ${byDay[day].map((task) => `
            <div class="plan-task-row">
              <button class="lecture-checkbox ${task.is_done ? "checked" : ""}" data-task="${task.id}" data-done="${task.is_done}" aria-label="toggle"></button>
              <div style="flex:1">
                <div style="font-weight:700">${task.subject_name}</div>
                ${task.lecture_title ? `<div class="text-small text-muted">${task.lecture_title}</div>` : ""}
                ${task.note ? `<div class="text-tiny text-muted" style="margin-top:2px">${task.note}</div>` : ""}
              </div>
              <span class="text-tiny text-muted">${t("study_plan.minutes", { n: task.estimated_minutes })}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `).join("")}
  `;

  contentEl.querySelectorAll("[data-task]").forEach((cb) => {
    cb.addEventListener("click", async () => {
      const wasDone = cb.dataset.done === "true";
      const next = !wasDone;
      cb.classList.toggle("checked", next);
      cb.classList.add("just-checked");
      cb.dataset.done = String(next);
      try {
        await apiPatch(`/study-plan/tasks/${cb.dataset.task}?is_done=${next}`);
      } catch {
        showToast(t("common.error.generic"));
        cb.classList.toggle("checked", wasDone);
        cb.dataset.done = String(wasDone);
      }
    });
  });
}

function renderEmpty() {
  contentEl.innerHTML = `
    <div class="empty-state">
      <p class="text-muted" data-i18n="study_plan.empty"></p>
      <button class="btn btn-primary" id="generateBtn" style="margin-top:var(--sp-4)" data-i18n="study_plan.generate"></button>
    </div>
  `;
  document.getElementById("generateBtn").addEventListener("click", () => generatePlan(false));
  import("/assets/js/i18n.js").then((m) => m.applyTranslations());
}

async function generatePlan(force) {
  contentEl.innerHTML = `<div class="skeleton" style="height:220px"></div>`;
  try {
    const plan = await apiPost("/study-plan/generate", { force });
    renderPlan(plan);
  } catch {
    showToast(t("common.error.generic"));
    renderEmpty();
  }
}

regenBtn.addEventListener("click", () => generatePlan(true));

async function init() {
  contentEl.innerHTML = `<div class="skeleton" style="height:220px"></div>`;
  try {
    const plan = await apiGet("/study-plan/current");
    if (plan) renderPlan(plan); else renderEmpty();
  } catch {
    renderEmpty();
  }
}
await init();
