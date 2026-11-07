export function showToast(message, { duration = 2600 } = {}) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  window.setTimeout(() => el.remove(), duration);
}
