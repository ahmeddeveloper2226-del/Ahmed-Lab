/**
 * The app's one signature motion moment (per frontend-design guidance:
 * spend boldness in exactly one place). Runs once per browser session
 * (sessionStorage-gated) right after a successful sign-in, before landing
 * on home.html: wordmark pops big and centered, shrinks into the corner,
 * then a motivational quote/verse fades in big before the real UI shows.
 */
import { getLang } from "./i18n.js";
import { randomQuote } from "./quotes.js";

const SESSION_KEY = "masark:introShown";

export function shouldShowIntro() {
  return !sessionStorage.getItem(SESSION_KEY);
}

export function playIntro({ onDone } = {}) {
  sessionStorage.setItem(SESSION_KEY, "1");
  const lang = getLang();
  const { quote } = randomQuote();

  const overlay = document.createElement("div");
  overlay.className = "intro-overlay";
  overlay.innerHTML = `
    <div class="intro-wordmark" id="introWordmark">مسارك</div>
    <div class="intro-quote" id="introQuote" style="display:none">
      ${lang === "ar" ? quote.ar : (quote.en || quote.ar)}
      ${quote.source ? `<div class="text-small text-muted" style="margin-top:8px">${quote.source}</div>` : ""}
    </div>
  `;
  document.body.appendChild(overlay);

  const wordmark = overlay.querySelector("#introWordmark");
  const quoteEl = overlay.querySelector("#introQuote");

  window.setTimeout(() => {
    wordmark.classList.add("shrink");
    quoteEl.style.display = "block";
  }, 950);

  window.setTimeout(() => {
    overlay.classList.add("overlay-fade-out");
  }, 2600);

  window.setTimeout(() => {
    overlay.remove();
    onDone?.();
  }, 3000);
}
