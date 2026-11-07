/**
 * Masark device mode.
 *
 * Loaded as a plain (non-module) script in <head> of every page so the layout
 * is correct on first paint. It:
 *   1. reads the saved choice ("mobile" | "desktop") from localStorage and sets
 *      <html data-device="...">, which the CSS keys its layout off;
 *   2. on a phone that chose "desktop", widens the viewport so the desktop layout
 *      fits (like "Desktop site" in mobile browsers);
 *   3. if there is no saved choice yet (first visit), shows a full-screen chooser
 *      with a pre-selected suggestion; and
 *   4. exposes window.MasarkDevice for the Settings screen.
 *
 * The choice is per browser/device on purpose (not saved to the account): the
 * same student may use a phone and a laptop.
 */
(function () {
  "use strict";

  var KEY = "masark:device";
  var root = document.documentElement;
  var viewport = document.querySelector('meta[name="viewport"]');
  if (!viewport) {
    viewport = document.createElement("meta");
    viewport.name = "viewport";
    viewport.content = "width=device-width, initial-scale=1, viewport-fit=cover";
    document.head.appendChild(viewport);
  }
  var BASE_VIEWPORT = viewport.getAttribute("content");
  var DESKTOP_ON_PHONE_VIEWPORT = "width=1100, viewport-fit=cover";

  function read() {
    try {
      var v = localStorage.getItem(KEY);
      return v === "mobile" || v === "desktop" ? v : null;
    } catch (e) { return null; }
  }
  function write(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode */ } }

  function shortSide() { return Math.min(screen.width || 9999, screen.height || 9999); }
  function isPhoneSizedScreen() { return shortSide() < 700; }

  function guess() {
    var coarse = false;
    try { coarse = matchMedia("(pointer:coarse)").matches; } catch (e) { /* old browser */ }
    return (coarse && isPhoneSizedScreen()) || shortSide() < 500 ? "mobile" : "desktop";
  }

  /** Applies a mode to the page. Returns true if the viewport meta changed. */
  function apply(mode) {
    root.setAttribute("data-device", mode);
    var wanted = mode === "desktop" && isPhoneSizedScreen() ? DESKTOP_ON_PHONE_VIEWPORT : BASE_VIEWPORT;
    var changed = viewport.getAttribute("content") !== wanted;
    if (changed) viewport.setAttribute("content", wanted);
    return changed;
  }

  var saved = read();
  var current = saved || guess();
  apply(current);

  window.MasarkDevice = {
    /** Current mode ("mobile" | "desktop"). */
    get: function () { return read() || current; },
    /** True once the user has made an explicit choice. */
    isSet: function () { return read() !== null; },
    guess: guess,
    /** Saves + applies a mode. Returns true if a reload is advisable. */
    set: function (mode) {
      if (mode !== "mobile" && mode !== "desktop") return false;
      write(mode);
      current = mode;
      var changed = apply(mode);
      try { window.dispatchEvent(new CustomEvent("masark:device", { detail: mode })); } catch (e) { /* noop */ }
      return changed;
    },
  };

  // Keep other open tabs in sync.
  window.addEventListener("storage", function (e) {
    if (e.key === KEY && (e.newValue === "mobile" || e.newValue === "desktop")) {
      current = e.newValue;
      if (apply(e.newValue)) location.reload();
    }
  });

  if (saved) return;

  /* ------------------------------------------------------------------ *
   * First visit: ask which device the student is on.
   * ------------------------------------------------------------------ */
  var TEXT = {
    ar: {
      title: "إنت بتستخدم أنهي جهاز؟",
      sub: "هنظبط شكل الموقع على شاشتك. تقدر تغيّره بعدين من الإعدادات.",
      mobile: "موبايل", mobileHint: "شاشة صغيرة · شريط تنقل تحت",
      desktop: "لابتوب / كمبيوتر", desktopHint: "شاشة كبيرة · قايمة جانبية",
      suggested: "مقترح",
    },
    en: {
      title: "Which device are you using?",
      sub: "We'll fit the layout to your screen. You can change it later in Settings.",
      mobile: "Phone", mobileHint: "Small screen · bottom navigation",
      desktop: "Laptop / PC", desktopHint: "Large screen · side menu",
      suggested: "Suggested",
    },
  };

  var CSS = [
    "#dvChooser{position:fixed;inset:0;z-index:2000;display:grid;place-items:center;padding:24px 16px;overflow:auto;",
    "background:var(--gradient-hero,linear-gradient(135deg,#fff,#eafbf7 45%,#a6f5e7));color:var(--text,#0b2027);",
    "font-family:var(--font-body,'Cairo','Segoe UI',sans-serif)}",
    "#dvChooser .dv-box{width:100%;max-width:640px;text-align:center}",
    "#dvChooser .dv-mark{font-size:2.25rem;font-weight:800;margin-bottom:8px;",
    "background:var(--gradient-brand,linear-gradient(135deg,#34d3be,#0b7a73));-webkit-background-clip:text;background-clip:text;color:transparent}",
    "#dvChooser h1{margin:0 0 8px;font-size:clamp(1.4rem,4vw,1.9rem);font-weight:800}",
    "#dvChooser p{margin:0 0 24px;color:var(--text-muted,#547479);font-size:.95rem}",
    "#dvChooser .dv-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}",
    "@media(max-width:520px){#dvChooser .dv-grid{grid-template-columns:1fr}}",
    "#dvChooser .dv-card{position:relative;display:flex;flex-direction:column;align-items:center;gap:10px;",
    "padding:26px 16px;border:2px solid var(--border,#dcefea);border-radius:24px;cursor:pointer;",
    "background:var(--bg-card,#fff);color:inherit;font:inherit;",
    "box-shadow:0 8px 24px -8px rgba(11,32,39,.16);transition:transform .2s,border-color .2s,box-shadow .2s}",
    "#dvChooser .dv-card:hover,#dvChooser .dv-card:focus-visible{transform:translateY(-3px);border-color:var(--accent,#14b8a2);",
    "box-shadow:0 12px 28px -10px rgba(20,184,162,.45);outline:none}",
    "#dvChooser .dv-card svg{width:56px;height:56px;stroke:var(--accent-strong,#0b7a73);fill:none;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}",
    "#dvChooser .dv-name{font-size:1.2rem;font-weight:800}",
    "#dvChooser .dv-hint{font-size:.8rem;color:var(--text-muted,#547479)}",
    "#dvChooser .dv-badge{position:absolute;top:10px;inset-inline-end:10px;padding:2px 10px;border-radius:999px;",
    "font-size:.7rem;font-weight:800;color:#fff;background:var(--gradient-brand,#14b8a2)}",
  ].join("");

  var ICON_PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/></svg>';
  var ICON_LAPTOP = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4.5" y="5" width="15" height="10.5" rx="1.6"/><path d="M2.5 19h19"/></svg>';

  function showChooser() {
    if (document.getElementById("dvChooser")) return;
    var lang = "ar";
    try { lang = localStorage.getItem("masark:lang") === "en" ? "en" : "ar"; } catch (e) { /* noop */ }
    var T = TEXT[lang];
    var suggestion = guess();

    var style = document.createElement("style");
    style.id = "dvStyle";
    style.textContent = CSS;
    document.head.appendChild(style);

    var wrap = document.createElement("div");
    wrap.id = "dvChooser";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-modal", "true");
    wrap.setAttribute("aria-labelledby", "dvTitle");
    wrap.innerHTML =
      '<div class="dv-box">' +
        '<div class="dv-mark">مسارك</div>' +
        '<h1 id="dvTitle"></h1><p id="dvSub"></p>' +
        '<div class="dv-grid">' +
          '<button type="button" class="dv-card" data-mode="mobile">' + ICON_PHONE +
            '<span class="dv-name"></span><span class="dv-hint"></span></button>' +
          '<button type="button" class="dv-card" data-mode="desktop">' + ICON_LAPTOP +
            '<span class="dv-name"></span><span class="dv-hint"></span></button>' +
        '</div>' +
      '</div>';
    wrap.querySelector("#dvTitle").textContent = T.title;
    wrap.querySelector("#dvSub").textContent = T.sub;

    var cards = wrap.querySelectorAll(".dv-card");
    for (var i = 0; i < cards.length; i++) {
      (function (card) {
        var mode = card.getAttribute("data-mode");
        card.querySelector(".dv-name").textContent = T[mode];
        card.querySelector(".dv-hint").textContent = T[mode + "Hint"];
        if (mode === suggestion) {
          var badge = document.createElement("span");
          badge.className = "dv-badge";
          badge.textContent = T.suggested;
          card.appendChild(badge);
        }
        card.addEventListener("click", function () {
          var needsReload = window.MasarkDevice.set(mode);
          if (needsReload) { location.reload(); return; }
          wrap.remove();
          style.remove();
          document.body.style.overflow = "";
        });
      })(cards[i]);
    }

    document.body.appendChild(wrap);
    document.body.style.overflow = "hidden";
    var first = wrap.querySelector('[data-mode="' + suggestion + '"]');
    if (first) first.focus();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", showChooser);
  else showChooser();
})();
