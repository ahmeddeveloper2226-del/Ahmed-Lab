/**
 * Thin fetch wrapper: attaches the current Firebase ID token, resolves the
 * API base URL per environment, and normalizes errors so every page can
 * `catch` one consistent shape: { status, detail }.
 */
import { auth } from "./firebase-config.js";

// Same-origin by default now that the backend serves the frontend too
// (see app/main.py's StaticFiles mount) - a relative path works no matter
// which host/port you access the app through. Override window.MASARK_API_BASE
// before this script runs if you ever deploy frontend and backend separately.
export const API_BASE = window.MASARK_API_BASE || "/api/v1";

async function authHeader() {
  const user = auth.currentUser;
  if (!user) return {};
  const token = await user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

async function request(method, path, body) {
  const headers = { "Content-Type": "application/json", ...(await authHeader()) };
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    throw { status: 0, detail: "network_error" };
  }

  if (res.status === 204) return null;

  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }

  if (!res.ok) {
    throw { status: res.status, detail: data?.detail || "unknown_error" };
  }
  return data;
}

export const apiGet = (path) => request("GET", path);
export const apiPost = (path, body) => request("POST", path, body);
export const apiPut = (path, body) => request("PUT", path, body);
export const apiPatch = (path, body) => request("PATCH", path, body);
export const apiDelete = (path) => request("DELETE", path);