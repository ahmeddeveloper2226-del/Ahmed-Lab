/**
 * Sidebar (desktop, right side in RTL) / floating dock (mobile) + the shared
 * top bar (avatar · title · dark-mode + language toggles). One call to
 * renderNav() on any page renders both, so no page needs extra markup.
 * "جدول المحاضرات" is its own page (lectures.html); "الإعدادات" jumps to the
 * settings card on the profile page.
 */
import { t, getLang, loadLocale } from "./i18n.js";
import { toggleTheme } from "./theme.js";
import { auth, onAuthStateChanged } from "./firebase-config.js";

const TABS = [
  { path: "/home.html", key: "nav.home", icon: `<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/>` },
  { path: "/lectures.html", key: "nav.schedule", icon: `<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 2v4M16 2v4M4 10h16"/><circle cx="15" cy="16" r="2.5"/>` },
  { path: "/study-plan.html", key: "nav.study_plan", icon: `<path d="M6 3h11a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6z"/><path d="M10 8h5M10 12h5M3 7h3M3 12h3M3 17h3"/>` },
  { path: "/motivate.html", key: "nav.motivate", icon: `<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>` },
  { path: "/subjects.html", key: "nav.subjects", icon: `<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>` },
  { path: "/profile.html", key: "nav.profile", icon: `<circle cx="12" cy="8" r="4"/><path d="M4 21c1.8-4 5-6 8-6s6.2 2 8 6"/>` },
  { path: "/profile.html", hash: "#settings", key: "nav.settings", cls: "settings", icon: `<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>` },
];

function renderTopbar() {
  const main = document.querySelector(".app-main");
  if (!main || document.getElementById("topBar")) return;
  const bar = document.createElement("header");
  bar.id = "topBar";
  bar.className = "topbar";
  bar.innerHTML = `
    <a class="avatar-chip" id="tbAvatar" href="/profile.html" aria-label="profile"><span>·</span></a>
    <span class="tb-name" id="tbName"></span>
    <strong class="tb-title">${t("app.pick")}</strong>
    <button class="lang-btn" id="tbLang">${getLang() === "ar" ? "En" : "ع"}</button>
    <button class="tt" id="tbTheme" aria-label="theme"><span class="knob"></span></button>`;
  main.prepend(bar);
  bar.querySelector("#tbTheme").addEventListener("click", () => toggleTheme());
  bar.querySelector("#tbLang").addEventListener("click", async () => {
    await loadLocale(getLang() === "ar" ? "en" : "ar");
    window.location.reload();
  });
  onAuthStateChanged(auth, (u) => {
    if (!u) return;
    const nm = (u.displayName || (u.email || "").split("@")[0] || "").trim().split(/\s+/)[0];
    bar.querySelector("#tbName").textContent = nm;
    bar.querySelector("#tbAvatar").innerHTML = u.photoURL
      ? `<img src="${u.photoURL}" alt="">`
      : `<span>${(u.displayName || u.email || "?").trim().charAt(0).toUpperCase()}</span>`;
  });
}

export function renderNav() {
  const el = document.getElementById("tabBar");
  if (!el) return;
  const { pathname, hash } = window.location;
  el.innerHTML = TABS.map((tab) => {
    const active = pathname === tab.path && hash === (tab.hash || "");
    return `<a class="tab-link ${tab.cls || ""} ${active ? "active" : ""}" href="${tab.path}${tab.hash || ""}">
      <svg viewBox="0 0 24 24">${tab.icon}</svg><span>${t(tab.key)}</span></a>`;
  }).join("");
  renderTopbar();
  if (!el.dataset.bound) {
    el.dataset.bound = "1";
    window.addEventListener("hashchange", renderNav);
  }
}