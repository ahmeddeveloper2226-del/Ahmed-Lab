/**
 * Renders the "paste a lecture-page link" mini-flow into `panelEl`:
 * one textarea + a preview button that calls the backend's
 * /platforms/lectures-by-url (which auto-detects the platform from the
 * link's domain and runs the AI agent against that exact page - no
 * platform picker, no browse/discover step). Once the student has
 * previewed and ticked off already-watched lectures, `onConfirm` is
 * called with the fields subjects.py's add_subject endpoint expects.
 *
 * Used identically by page-onboarding.js and page-subjects.js so the two
 * "add a subject" flows can never drift apart.
 */
import { apiGet } from "/assets/js/api.js";
import { t } from "/assets/js/i18n.js";

export function renderUrlLectureFlow(panelEl, { onConfirm }) {
  panelEl.innerHTML = `
    <div class="field">
      <textarea class="input" id="lectureUrlInput" rows="2"
        placeholder="${t("onboarding.subjects.lecture_url_placeholder")}"></textarea>
    </div>
    <button class="btn btn-outline btn-block" id="previewLecturesBtn">
      ${t("onboarding.subjects.preview_lectures")}
    </button>
    <div id="urlLecturePreview"></div>
  `;

  const previewBtn = panelEl.querySelector("#previewLecturesBtn");
  const urlInput = panelEl.querySelector("#lectureUrlInput");
  const previewEl = panelEl.querySelector("#urlLecturePreview");

  previewBtn.addEventListener("click", async () => {
    const url = urlInput.value.trim();
    if (!url) return;

    previewBtn.disabled = true;
    const originalLabel = previewBtn.textContent;
    previewBtn.innerHTML = `<span class="spinner"></span>`;
    previewEl.innerHTML = "";

    try {
      // The agent has to actually browse the live page - this can take a
      // several seconds, noticeably longer than a normal API call.
      const result = await apiGet(`/platforms/lectures-by-url?url=${encodeURIComponent(url)}`);
      const lectures = result.items || [];

      if (!lectures.length) {
        previewEl.innerHTML = `<p class="text-small text-muted" style="margin-top:12px">${t("common.error.generic")}</p>`;
        return;
      }

      previewEl.innerHTML = `
        <p class="text-small text-muted" style="margin:12px 0 6px">${t("onboarding.subjects.mark_done")}</p>
        <div style="max-height:220px;overflow-y:auto">
          ${lectures.map((l, i) => `
            <label class="lecture-pick-row" style="display:flex;align-items:center;gap:10px;padding:10px 2px;border-bottom:1px solid var(--border)">
              <input type="checkbox" data-lecture-idx="${i}" style="flex-shrink:0">
              <span>${l.title}</span>
            </label>
          `).join("")}
        </div>
        <button class="btn btn-primary btn-block" id="confirmUrlSubject" style="margin-top:var(--sp-4)">
          ${t("onboarding.subjects.add")}
        </button>
      `;

      const confirmBtn = previewEl.querySelector("#confirmUrlSubject");
      confirmBtn.addEventListener("click", async () => {
        if (confirmBtn.disabled) return; // ignore double clicks
        const completedIds = [...previewEl.querySelectorAll("[data-lecture-idx]:checked")]
          .map((cb) => lectures[Number(cb.dataset.lectureIdx)].external_id);
        const confirmLabel = confirmBtn.innerHTML;
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = `<span class="spinner"></span>`;
        try {
          await onConfirm({
          platform: result.detected_platform || null,
          teacher_or_pack_id: null,
          teacher_or_pack_url: url,
          already_completed_lecture_ids: completedIds,
          _platformLabel: result.detected_platform_name || url,
          _lectureCount: lectures.length,
          });
        } finally {
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = confirmLabel;
        }
      });
    } catch {
      previewEl.innerHTML = `<p class="text-small" style="color:var(--status-bad)">${t("common.error.generic")}</p>`;
    } finally {
      previewBtn.disabled = false;
      previewBtn.textContent = originalLabel;
    }
  });
}