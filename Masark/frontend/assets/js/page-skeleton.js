import { initI18n } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { renderNav } from "/assets/js/nav.js";
import { initTheme } from "/assets/js/theme.js";
import { UI } from "/assets/js/skeleton/skeleton-data.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
document.getElementById("skTitle").textContent = UI[lang].title;
const { mountSkeleton } = await import("/assets/js/skeleton/skeleton-viewer.js");
const handle = await mountSkeleton(document.getElementById("skHost"), { lang });
if (location.search.includes("debug")) window.masarkSkeleton = handle;
