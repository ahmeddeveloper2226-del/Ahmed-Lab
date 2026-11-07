import { initI18n, t } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { apiGet, apiPost } from "/assets/js/api.js";
import { showToast } from "/assets/js/toast.js";
import { renderUrlLectureFlow } from "/assets/js/subject-url-flow.js";

await initI18n();
await requireAuth({ requireOnboarding: false });

/**
 * If the person already has a completed profile (i.e. they arrived here
 * via profile.html's "edit details" link, not first-time signup),
 * pre-fill steps 1-3 so they're editing, not starting from scratch. The
 * subjects step intentionally starts empty either way — this flow only
 * ever ADDS subjects; existing ones are managed from the المواد tab.
 */
async function prefillIfEditing() {
  try {
    const profile = await apiGet("/users/me");
    if (!profile.onboarding_completed) return;

    document.getElementById("fullName").value = profile.full_name || "";
    document.getElementById("age").value = profile.age || "";
    document.getElementById("phone").value = profile.phone_number || "";

    if (profile.academic_level) {
      state.level = profile.academic_level;
      document.querySelectorAll("#levelChips .chip").forEach((c) => c.classList.toggle("selected", c.dataset.value === state.level));
    }
    if (profile.academic_year) {
      state.year = profile.academic_year;
      document.querySelectorAll("#yearChips .chip").forEach((c) => c.classList.toggle("selected", c.dataset.value === state.year));
    }
    const availability = profile.availability || {};
    if (availability.weekday_hours != null) document.getElementById("weekdayHours").value = availability.weekday_hours;
    if (availability.weekend_hours != null) document.getElementById("weekendHours").value = availability.weekend_hours;
    (availability.off_days || []).forEach((day) => {
      state.offDays.add(day);
      document.querySelector(`#offDaysChips [data-day="${day}"]`)?.classList.add("selected");
    });
  } catch {
    /* first-time signup: /users/me may 404-equivalent empty, ignore */
  }
}

const SUBJECT_CATALOG = [
  "arabic", "english", "french", "math", "physics", "chemistry", "biology",
  "geology", "history", "geography", "philosophy", "psychology", "economics", "religion",
];
const SUBJECT_LABELS = {
  ar: { arabic: "لغة عربية", english: "لغة إنجليزية", french: "لغة فرنسية", math: "رياضيات",
        physics: "فيزياء", chemistry: "كيمياء", biology: "أحياء", geology: "جيولوجيا",
        history: "تاريخ", geography: "جغرافيا", philosophy: "فلسفة ومنطق", psychology: "علم نفس واجتماع",
        economics: "اقتصاد وإحصاء", religion: "تربية دينية" },
  en: { arabic: "Arabic", english: "English", french: "French", math: "Math",
        physics: "Physics", chemistry: "Chemistry", biology: "Biology", geology: "Geology",
        history: "History", geography: "Geography", philosophy: "Philosophy & Logic",
        psychology: "Psychology & Sociology", economics: "Economics & Statistics", religion: "Religion" },
};

const DAY_KEYS = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"];
document.getElementById("offDaysChips").innerHTML = DAY_KEYS.map((k, i) => `
  <button class="chip" type="button" data-day="${i}" data-i18n="onboarding.days.${k}"></button>
`).join("");

const state = {
  step: 0,
  level: "prep",
  year: "year_1",
  offDays: new Set(),
  subjects: [], // { subject_slug, subject_name, source_mode, platform, teacher_or_pack_id, teacher_or_pack_url, manual_lectures, already_completed_lecture_ids }
};

const steps = [...document.querySelectorAll(".onb-step")];
const dotsEl = document.getElementById("stepDots");
dotsEl.innerHTML = steps.map((_, i) => `<span class="step-dot ${i === 0 ? "active" : ""}"></span>`).join("");

await prefillIfEditing();

function renderStep() {
  steps.forEach((s, i) => s.classList.toggle("active", i === state.step));
  [...dotsEl.children].forEach((d, i) => d.classList.toggle("active", i === state.step));
  document.getElementById("backBtn").style.display = state.step === 0 ? "none" : "inline-flex";
  document.getElementById("nextBtn").textContent =
    state.step === steps.length - 1 ? t("onboarding.finish") : t("onboarding.continue");
  import("/assets/js/i18n.js").then((m) => m.applyTranslations());
}
renderStep();

document.querySelectorAll("#levelChips .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    state.level = chip.dataset.value;
    document.querySelectorAll("#levelChips .chip").forEach((c) => c.classList.toggle("selected", c === chip));
  });
});
document.querySelectorAll("#yearChips .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    state.year = chip.dataset.value;
    document.querySelectorAll("#yearChips .chip").forEach((c) => c.classList.toggle("selected", c === chip));
  });
});
document.getElementById("offDaysChips").addEventListener("click", (e) => {
  const chip = e.target.closest("[data-day]");
  if (!chip) return;
  const day = Number(chip.dataset.day);
  if (state.offDays.has(day)) { state.offDays.delete(day); chip.classList.remove("selected"); }
  else { state.offDays.add(day); chip.classList.add("selected"); }
});

document.getElementById("backBtn").addEventListener("click", () => {
  if (state.step > 0) { state.step -= 1; renderStep(); }
});

document.getElementById("nextBtn").addEventListener("click", async () => {
  if (state.step === 0) {
    if (!document.getElementById("fullName").value.trim() || !document.getElementById("age").value || !document.getElementById("phone").value.trim()) {
      showToast(t("common.error.generic"));
      return;
    }
  }
  if (state.step < steps.length - 1) {
    state.step += 1;
    renderStep();
    return;
  }
  await finishOnboarding();
});

async function finishOnboarding() {
  const btn = document.getElementById("nextBtn");
  btn.disabled = true;
  const originalLabel = btn.textContent;
  btn.innerHTML = `<span class="spinner"></span>`;
  try {
    await apiPost("/users/me/onboarding", {
      full_name: document.getElementById("fullName").value.trim(),
      age: Number(document.getElementById("age").value),
      phone_number: document.getElementById("phone").value.trim(),
      academic_level: state.level,
      academic_year: state.year,
      availability: {
        weekday_hours: Number(document.getElementById("weekdayHours").value),
        weekend_hours: Number(document.getElementById("weekendHours").value),
        off_days: [...state.offDays],
      },
    });

    for (const subject of state.subjects) {
      await apiPost("/subjects", subject);
    }

    window.location.href = "/home.html";
  } catch (err) {
    showToast(t("common.error.generic"));
    btn.disabled = false;
    btn.textContent = originalLabel;
  }
}

/* ------------------------------------------------------------------ */
/* Subject list rendering                                              */
/* ------------------------------------------------------------------ */
function renderSubjectsList() {
  const lang = document.documentElement.lang;
  const el = document.getElementById("subjectsList");
  if (state.subjects.length === 0) {
    el.innerHTML = `<p class="text-muted text-small">${t("subjects.empty")}</p>`;
    return;
  }
  el.innerHTML = state.subjects.map((s, i) => `
    <div class="subject-card">
      <div class="subject-card-head">
        <strong>${s.subject_name}</strong>
        <button class="btn btn-icon btn-sm" data-remove="${i}" aria-label="remove">✕</button>
      </div>
      <p class="text-small text-muted" style="margin-top:4px">
        ${s.source_mode === "manual" ? t("onboarding.subjects.manual") : (s._platformLabel || s.platform)}
        ${s.manual_lectures?.length ? ` · ${s.manual_lectures.length}` : (s._lectureCount ? ` · ${s._lectureCount}` : "")}
      </p>
    </div>
  `).join("");
  el.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.subjects.splice(Number(btn.dataset.remove), 1);
      renderSubjectsList();
    });
  });
}
renderSubjectsList();

/* ------------------------------------------------------------------ */
/* Add-subject sheet flow                                              */
/* ------------------------------------------------------------------ */
const sheet = document.getElementById("addSubjectSheet");
const sheetContent = document.getElementById("addSubjectContent");

document.getElementById("addSubjectBtn").addEventListener("click", () => openAddSubject());
sheet.addEventListener("click", (e) => { if (e.target === sheet) closeSheet(); });

function closeSheet() { sheet.style.display = "none"; sheetContent.innerHTML = ""; }

function openAddSubject() {
  const lang = document.documentElement.lang === "ar" ? "ar" : "en";
  sheet.style.display = "block";
  sheetContent.innerHTML = `
    <h2>${t("onboarding.subjects.add")}</h2>
    <div class="field" style="margin-top:var(--sp-4)">
      <select class="select" id="subjectSelect">
        ${SUBJECT_CATALOG.map((s) => `<option value="${s}">${SUBJECT_LABELS[lang][s]}</option>`).join("")}
      </select>
    </div>
    <p class="text-small text-muted">${t("onboarding.subjects.choose_source")}</p>
    <div class="chip-group" id="sourceChips" style="margin:var(--sp-3) 0">
      <button class="chip selected" data-source="platform">${t("onboarding.subjects.from_platform")}</button>
      <button class="chip" data-source="manual">${t("onboarding.subjects.manual")}</button>
    </div>
    <div id="sourcePanel"></div>
  `;
  let source = "platform";
  const panel = document.getElementById("sourcePanel");

  document.querySelectorAll("#sourceChips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      source = chip.dataset.source;
      document.querySelectorAll("#sourceChips .chip").forEach((c) => c.classList.toggle("selected", c === chip));
      renderSourcePanel();
    });
  });

  async function renderSourcePanel() {
    if (source === "manual") {
      panel.innerHTML = `
        <div class="field">
          <label>${t("onboarding.subjects.manual")}</label>
          <textarea class="input" id="manualLectures" rows="5" placeholder="عنوان المحاضرة ١\nعنوان المحاضرة ٢"></textarea>
        </div>
        <button class="btn btn-primary btn-block" id="confirmManual">${t("onboarding.subjects.add")}</button>
      `;
      document.getElementById("confirmManual").addEventListener("click", () => {
        const lines = document.getElementById("manualLectures").value.split("\n").map((l) => l.trim()).filter(Boolean);
        const slug = document.getElementById("subjectSelect").value;
        state.subjects.push({
          subject_slug: slug,
          subject_name: SUBJECT_LABELS[lang][slug],
          source_mode: "manual",
          manual_lectures: lines.map((title, order) => ({ title, order })),
          already_completed_lecture_ids: [],
        });
        renderSubjectsList();
        closeSheet();
      });
      return;
    }

    renderUrlLectureFlow(panel, {
      onConfirm: (fields) => {
        const slug = document.getElementById("subjectSelect").value;
        state.subjects.push({
          subject_slug: slug,
          subject_name: SUBJECT_LABELS[lang][slug],
          source_mode: "platform",
          manual_lectures: [],
          ...fields,
        });
        renderSubjectsList();
        closeSheet();
      },
    });
  }

  renderSourcePanel();
}