/** Escape text before putting it in innerHTML (lecture titles come from scraped platforms). */
export function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
/** Only allow http(s) links; returns "" otherwise. */
export function safeUrl(u) {
  return /^https?:\/\//i.test(u || "") ? esc(u) : "";
}