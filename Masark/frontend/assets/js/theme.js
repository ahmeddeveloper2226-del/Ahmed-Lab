/**
 * Light/dark theme toggle. Persists locally immediately (snappy UI) and
 * syncs to the backend profile in the background if the user is signed in
 * (fire-and-forget — a failed sync just means it'll pick up local storage
 * again on next load, never blocks the UI).
 */
import { apiPatch } from "./api.js";

export function getTheme() {
  return localStorage.getItem("masark:theme") || "light";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("masark:theme", theme);
}

export function toggleTheme() {
  const next = getTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  apiPatch("/users/me", { theme: next }).catch(() => {});
  return next;
}

export function initTheme() {
  applyTheme(getTheme());
}
