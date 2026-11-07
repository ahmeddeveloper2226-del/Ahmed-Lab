/**
 * Minimal i18n: loads /assets/locales/{lang}.json, exposes t(key, vars),
 * and flips document dir/lang. Language + theme are the two prefs the
 * backend also stores on the profile (see users.py PATCH /users/me) so a
 * change here is pushed there too when the user is signed in.
 */
const SUPPORTED = ["ar", "en"];
let strings = {};
let currentLang = localStorage.getItem("masark:lang") || "ar";

export function getLang() { return currentLang; }

export async function loadLocale(lang) {
  if (!SUPPORTED.includes(lang)) lang = "ar";
  const res = await fetch(`/assets/locales/${lang}.json`);
  strings = await res.json();
  currentLang = lang;
  localStorage.setItem("masark:lang", lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  applyTranslations();
}

export function t(key, vars = {}) {
  let str = strings[key] ?? key;
  for (const [k, v] of Object.entries(vars)) {
    str = str.replace(`{${k}}`, v);
  }
  return str;
}

export function applyTranslations(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
  });
}

export async function initI18n() {
  await loadLocale(currentLang);
}
