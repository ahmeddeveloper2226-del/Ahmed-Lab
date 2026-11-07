import { initI18n, t } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { apiGet } from "/assets/js/api.js";
import { renderNav } from "/assets/js/nav.js";
import { randomQuote } from "/assets/js/quotes.js";
import { initTheme } from "/assets/js/theme.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
const ROTATE_SECONDS = 180; // "changes every three minutes" per the brief

let lastIndex = -1;
let secondsLeft = ROTATE_SECONDS;

function showQuote() {
  const { quote, index } = randomQuote(lastIndex);
  lastIndex = index;
  document.getElementById("quoteText").textContent = lang === "ar" ? quote.ar : (quote.en || quote.ar);
  document.getElementById("quoteText").classList.remove("motivate-text");
  void document.getElementById("quoteText").offsetWidth; // restart animation
  document.getElementById("quoteText").classList.add("motivate-text");
  document.getElementById("quoteSource").textContent = quote.source || "";
  secondsLeft = ROTATE_SECONDS;
}

function tick() {
  secondsLeft -= 1;
  document.getElementById("nextInLabel").textContent = t("motivate.next_in", { s: secondsLeft });
  if (secondsLeft <= 0) showQuote();
}

showQuote();
document.getElementById("nextInLabel").textContent = t("motivate.next_in", { s: secondsLeft });
setInterval(tick, 1000);
document.getElementById("nextQuoteBtn").addEventListener("click", showQuote);

apiGet("/home/progress").then((progress) => {
  document.getElementById("statDone").textContent = progress.completed;
  document.getElementById("statLeft").textContent = progress.remaining;
  document.getElementById("statPercent").textContent = `${Math.round(progress.percent)}%`;
}).catch(() => {});
