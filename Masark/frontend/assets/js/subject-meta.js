/**
 * One place that knows every subject's icon, colour and label, so Home,
 * the lectures table and the Subjects tab always look the same.
 * Icons are inline SVG (24x24, stroke = currentColor).
 */
const ICONS = {
  arabic: `<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z"/><path d="m17 3.5.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8z"/>`,
  english: `<path d="M4 5h16v11H9l-5 4z"/><path d="m8.5 13 2-5 2 5M9.3 11.4h2.4M15 9h2M15 12h1"/>`,
  french: `<path d="M12 2v3M10 22l1.6-10h.8L14 22M8.5 22h7M10.6 12 9 8h6l-1.6 4M11 5h2M7.5 17h9"/>`,
  math: `<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 7h8M8 12h.01M12 12h.01M16 12h.01M8 16h.01M12 16h.01M16 16h.01"/>`,
  physics: `<circle cx="12" cy="12" r="1.6"/><ellipse cx="12" cy="12" rx="10" ry="4"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/>`,
  chemistry: `<path d="M9 3h6M10 3v6l-5.6 9.6A2 2 0 0 0 6.1 21.5h11.8a2 2 0 0 0 1.7-2.9L14 9V3"/><path d="M7.4 15h9.2"/>`,
  biology: `<path d="M5 19C5 10 10 5 20 4c0 10-5 15-14 15z"/><path d="M5 19c3-5 6-8 10-10"/>`,
  geology: `<path d="m3 20 6-11 4 6 2-3 6 8z"/><path d="m7.5 12.5 1.5 1.2 1.5-1.2"/>`,
  history: `<path d="M3 9 12 4l9 5zM5.5 9v9M9.8 9v9M14.2 9v9M18.5 9v9M3 21h18"/>`,
  geography: `<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3.2 3 3.2 15 0 18M12 3c-3.2 3-3.2 15 0 18"/>`,
  philosophy: `<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>`,
  psychology: `<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.5-4 3.3-6 6.5-6s6 2 6.5 6"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.5 0 4.2 1.7 4.5 5"/>`,
  economics: `<path d="M4 20V11M10 20V4M16 20v-7M22 20H2"/><path d="m13 8 3-3 3 3"/>`,
  religion: `<path d="M12 2c1 2.2 3 3 3 6H9c0-3 2-3.8 3-6zM6 22V13a6 6 0 0 1 12 0v9M4 22h16M12 22v-5"/>`,
  _default: `<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>`,
};

const META = {
  arabic:     { ar: "لغة عربية",       en: "Arabic",                 c: "#14B8A2" },
  english:    { ar: "لغة إنجليزية",    en: "English",                c: "#6366F1" },
  french:     { ar: "لغة فرنسية",      en: "French",                 c: "#EC4899" },
  math:       { ar: "رياضيات",         en: "Math",                   c: "#F59E0B" },
  physics:    { ar: "فيزياء",          en: "Physics",                c: "#0EA5E9" },
  chemistry:  { ar: "كيمياء",          en: "Chemistry",              c: "#A855F7" },
  biology:    { ar: "أحياء",           en: "Biology",                c: "#2DD4BF" },
  geology:    { ar: "جيولوجيا",        en: "Geology",                c: "#F97316" },
  history:    { ar: "تاريخ",           en: "History",                c: "#65A30D" },
  geography:  { ar: "جغرافيا",         en: "Geography",              c: "#3B82F6" },
  philosophy: { ar: "فلسفة ومنطق",     en: "Philosophy & Logic",     c: "#D946EF" },
  psychology: { ar: "علم نفس واجتماع", en: "Psychology & Sociology", c: "#8B5CF6" },
  economics:  { ar: "اقتصاد وإحصاء",   en: "Economics & Statistics", c: "#0D9488" },
  religion:   { ar: "تربية دينية",     en: "Religion",               c: "#06B6D4" },
};

const FALLBACK = ["#14B8A2", "#6366F1", "#F59E0B", "#0EA5E9", "#A855F7", "#F97316"];

export const SUBJECT_SLUGS = Object.keys(META);

export function subjectColor(slug) {
  if (META[slug]) return META[slug].c;
  let h = 0;
  for (const ch of String(slug || "")) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return FALLBACK[h % FALLBACK.length];
}

export function subjectLabel(slug, lang, fallback) {
  return META[slug] ? META[slug][lang === "ar" ? "ar" : "en"] : (fallback || slug || "");
}

export function subjectIcon(slug, size = 24) {
  return `<svg class="s-ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[slug] || ICONS._default}</svg>`;
}