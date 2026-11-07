import { initI18n, t } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { apiGet } from "/assets/js/api.js";
import { renderNav } from "/assets/js/nav.js";
import { paintDonut } from "/assets/js/charts.js";
import { playIntro, shouldShowIntro } from "/assets/js/intro-animation.js";
import { randomQuote } from "/assets/js/quotes.js";
import { initTheme } from "/assets/js/theme.js";
import { initPushNotifications } from "/assets/js/notifications.js";
import { mountCalendar } from "/assets/js/calendar-view.js";
import { subjectColor, subjectIcon, subjectLabel } from "/assets/js/subject-meta.js";
import { esc } from "/assets/js/util.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

if (shouldShowIntro()) playIntro();
initPushNotifications();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
const { quote } = randomQuote();
document.getElementById("motivateTeaserText").textContent = lang === "ar" ? quote.ar : (quote.en || quote.ar);

const raf2 = (fn) => requestAnimationFrame(() => requestAnimationFrame(fn));

function countUp(el, to) {
  const start = performance.now();
  const step = (now) => {
    const p = Math.min(1, (now - start) / 1300);
    el.textContent = `${Math.round(to * (1 - Math.pow(1 - p, 3)))}%`;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

async function loadProgress() {
  const progress = await apiGet("/home/progress");
  raf2(() => paintDonut(document.getElementById("overallDonut"), progress.percent));
  countUp(document.getElementById("overallLabel"), Math.round(progress.percent));
  document.getElementById("overallCounts").textContent =
    `${t("home.done")}: ${progress.completed} · ${t("home.left")}: ${progress.remaining}`;

  const bars = document.getElementById("subjectBars");
  if (!progress.subjects.length) {
    bars.innerHTML = `<p class="text-small text-muted">${esc(t("home.empty"))}</p>`;
    return;
  }
  bars.innerHTML = progress.subjects.map((s, i) => `
    <div class="bar-col" style="--i:${i};--c:${subjectColor(s.subject_slug)}" title="${Math.round(s.percent)}% · ${s.completed}/${s.total}">
      <div class="col ${s.percent < 50 ? "bad" : ""}" data-pct="${s.percent}"></div>
      <span class="bar-ico">${subjectIcon(s.subject_slug, 17)}</span>
      <small>${esc(subjectLabel(s.subject_slug, lang, s.subject_name))}</small>
    </div>`).join("");
  raf2(() => bars.querySelectorAll(".col").forEach((c) => { c.style.height = `${Math.max(8, c.dataset.pct * 1.05)}px`; }));
}

await Promise.all([
  loadProgress(),
  mountCalendar(document.getElementById("calMount"), { big: false, onChange: loadProgress }),
]);