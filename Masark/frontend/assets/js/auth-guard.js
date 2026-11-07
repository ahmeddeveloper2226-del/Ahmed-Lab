/**
 * Route guard used at the top of every protected page (home, study-plan,
 * motivate, subjects, profile, onboarding). Waits for Firebase's auth
 * state to resolve (so a signed-in user isn't bounced to /login.html on a
 * hard refresh before the SDK has re-hydrated the session), calls
 * /auth/session to sync the Firestore profile stub, then routes based on
 * onboarding completion.
 *
 * Usage at the top of a page's module script:
 *   import { requireAuth } from "./auth-guard.js";
 *   const { profile } = await requireAuth({ requireOnboarding: true });
 */
import { auth, onAuthStateChanged } from "./firebase-config.js";
import { apiPost } from "./api.js";

function waitForAuthState() {
  return new Promise((resolve) => {
    const unsub = onAuthStateChanged(auth, (user) => {
      unsub();
      resolve(user);
    });
  });
}

export async function requireAuth({ requireOnboarding = true } = {}) {
  const user = await waitForAuthState();
  if (!user) {
    window.location.href = "/login.html";
    return null;
  }

  let session;
  try {
    session = await apiPost("/auth/session");
  } catch {
    window.location.href = "/login.html";
    return null;
  }

  const onCurrentPage = window.location.pathname;
  if (requireOnboarding && !session.onboarding_completed && onCurrentPage !== "/onboarding.html") {
    window.location.href = "/onboarding.html";
    return null;
  }
  // Note: onboarding.html is intentionally NOT auto-redirected away once
  // completed — profile.html's "edit details" link reuses this same page,
  // and page-onboarding.js pre-fills existing values when it detects an
  // already-completed profile (see its `prefillIfEditing()`).

  return { user, session };
}

/** For login.html: if already signed in, skip straight past it. */
export async function redirectIfSignedIn() {
  const user = await waitForAuthState();
  if (!user) return;
  try {
    const session = await apiPost("/auth/session");
    window.location.href = session.onboarding_completed ? "/home.html" : "/onboarding.html";
  } catch {
    /* stay on login if session bootstrap fails */
  }
}
