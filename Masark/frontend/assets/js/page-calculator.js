import { initI18n } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { renderNav } from "/assets/js/nav.js";
import { initTheme } from "/assets/js/theme.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
document.getElementById("calcTitle").textContent = lang === "ar" ? "الآلة الحاسبة العلمية" : "Scientific calculator";
const { mountCalculator } = await import("/assets/js/calc/calculator.js");
const handle = await mountCalculator(document.getElementById("calcHost"), { lang });
if (location.search.includes("debug")) window.masarkCalc = handle;
