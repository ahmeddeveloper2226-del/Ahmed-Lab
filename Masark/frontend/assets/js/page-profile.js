import { initI18n, loadLocale, getLang } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { apiGet, apiPatch } from "/assets/js/api.js";
import { renderNav } from "/assets/js/nav.js";
import { paintBar } from "/assets/js/charts.js";
import { initTheme, getTheme, toggleTheme } from "/assets/js/theme.js";
import { auth, signOut } from "/assets/js/firebase-config.js";

initTheme();
await initI18n();
renderNav();
const { user } = await requireAuth();

document.getElementById("darkModeToggle").checked = getTheme() === "dark";
document.querySelectorAll("[data-lang]").forEach((btn) => {
  btn.classList.toggle("selected", btn.dataset.lang === getLang());
  btn.addEventListener("click", async () => {
    await loadLocale(btn.dataset.lang);
    document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("selected", b === btn));
    apiPatch("/users/me", { language: btn.dataset.lang }).catch(() => {});
    renderNav();
  });
});

document.getElementById("darkModeToggle").addEventListener("change", () => toggleTheme());

// Device mode (phone / laptop layout). Stored per browser, not on the account.
document.querySelectorAll("[data-device]").forEach((btn) => {
  btn.classList.toggle("selected", btn.dataset.device === window.MasarkDevice?.get());
  btn.addEventListener("click", () => {
    if (!window.MasarkDevice || btn.dataset.device === window.MasarkDevice.get()) return;
    window.MasarkDevice.set(btn.dataset.device);
    window.location.reload(); // re-applies the viewport and the layout cleanly
  });
});

async function loadProfile() {
  const profile = await apiGet("/users/me");
  document.getElementById("profileName").textContent = profile.full_name || user.displayName || "";
  document.getElementById("profileEmail").textContent = profile.email || user.email || "";

  const avatarEl = document.getElementById("avatar");
  if (user.photoURL) {
    avatarEl.innerHTML = `<img src="${user.photoURL}" alt="">`;
  } else {
    avatarEl.textContent = (profile.full_name || "?").trim().charAt(0).toUpperCase();
  }
}

async function loadProgress() {
  const progress = await apiGet("/home/progress");
  document.getElementById("overallPct").textContent = `${Math.round(progress.percent)}%`;
  paintBar(document.getElementById("overallBar"), progress.percent);
}

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await signOut(auth);
  window.location.href = "/login.html";
});

document.getElementById("editBtn").addEventListener("click", () => {
  window.location.href = "/onboarding.html";
});

await Promise.all([loadProfile(), loadProgress()]);