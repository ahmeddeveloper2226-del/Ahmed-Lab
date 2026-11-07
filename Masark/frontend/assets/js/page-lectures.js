import { initI18n } from "/assets/js/i18n.js";
import { requireAuth } from "/assets/js/auth-guard.js";
import { renderNav } from "/assets/js/nav.js";
import { initTheme } from "/assets/js/theme.js";
import { mountCalendar } from "/assets/js/calendar-view.js";

initTheme();
await initI18n();
renderNav();
await requireAuth();

await mountCalendar(document.getElementById("calMount"), { big: true });