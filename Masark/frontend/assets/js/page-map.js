import { initI18n } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { renderNav } from "/assets/js/nav.js";
import { initTheme } from "/assets/js/theme.js";
import { UI } from "/assets/js/geo/geo-data.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
document.getElementById("gmTitle").textContent = UI[lang].title;
const { mountGeoMap } = await import("/assets/js/geo/geo-viewer.js");
const handle = await mountGeoMap(document.getElementById("gmHost"), { lang });
if (location.search.includes("debug")) window.masarkMap = handle;
