/**
 * Tiny, dependency-free chart helpers (a donut + a bar), since the app
 * only needs two simple, purposeful visualizations — pulling in a full
 * charting library would be overkill. Both read the green/red threshold
 * straight from the design tokens via CSS custom properties.
 */
export function paintDonut(el, percent) {
  const pct = Math.max(0, Math.min(100, percent));
  const good = pct >= 50;
  el.style.setProperty("--pct", pct);
  el.style.setProperty("--donut-color", good ? "var(--status-good)" : "var(--status-bad)");
}

export function paintBar(fillEl, percent) {
  const pct = Math.max(0, Math.min(100, percent));
  fillEl.style.width = `${pct}%`;
  fillEl.classList.toggle("behind", pct < 50);
}

export function statusPillHtml(percent, doneLabel, leftLabel, done, total) {
  const good = percent >= 50;
  return `<span class="status-pill ${good ? "good" : "bad"}">${Math.round(percent)}%</span>`;
}
