// assets/auth-guard.js
// Include this (type="module") on any page that requires a signed-in,
// verified user. It redirects unauthenticated/unverified visitors to
// login.html, syncs the Firestore profile doc, and exposes window.FS
// with helpers the page's own script can use.
import {
  auth, db, onAuthStateChanged, isVerified, syncUserProfile, signOut, recordSessionResult,
  doc, getDoc, collection, query, orderBy, limit, getDocs,
} from "./firebase-init.js";

function currentPageWithQuery() {
  return location.pathname.split("/").pop() + location.search;
}

function goToLogin(extra = "") {
  const next = encodeURIComponent(currentPageWithQuery());
  location.replace(`login.html?next=${next}${extra}`);
}

window.FS = window.FS || {};

window.FS.ready = new Promise((resolve) => {
  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      goToLogin();
      return;
    }
    if (!isVerified(user)) {
      goToLogin("&verify=1");
      return;
    }

    try {
      await syncUserProfile(user);
    } catch (e) {
      // Non-fatal — the page can still work even if the profile sync
      // hiccups (e.g. a transient network blip); Firestore rules will
      // still protect the data either way.
      console.error("[auth-guard] profile sync failed:", e.message);
    }

    window.FS.user = user;
    window.FS.logout = () => signOut(auth).then(() => (location.href = "login.html"));
    // Lets plain <script type="text/babel"> pages (which can't `import`)
    // save a completed session without knowing anything about Firestore.
    window.FS.recordSessionResult = (session) => recordSessionResult(user, session);
    // { totalScore, currentStreak, longestStreak, lastSessionDate } or
    // {} for a user who hasn't finished a session yet.
    window.FS.getUserStats = async () => {
      const snap = await getDoc(doc(db, "users", user.uid));
      return snap.exists() ? snap.data() : {};
    };
    // Most recent completed sessions, newest first.
    window.FS.getSessionHistory = async (max = 50) => {
      const q = query(collection(db, "users", user.uid, "sessions"), orderBy("createdAt", "desc"), limit(max));
      const snap = await getDocs(q);
      return snap.docs.map((d) => ({ id: d.id, ...d.data() }));
    };
    // Public leaderboard snapshot (masked names + streak only).
    window.FS.getLeaderboard = async () => {
      const snap = await getDoc(doc(db, "leaderboard", "current"));
      return snap.exists() ? snap.data() : { top: [], updatedAt: null };
    };
    // Always fetches a fresh (or cached-but-valid) ID token — Firebase
    // handles the ~1hr refresh internally, this call is cheap.
    window.FS.authedFetch = async (url, opts = {}) => {
      const token = await user.getIdToken();
      return fetch(url, {
        ...opts,
        credentials: "same-origin",
        headers: { ...(opts.headers || {}), Authorization: `Bearer ${token}` },
      });
    };

    resolve(user);
    window.dispatchEvent(new CustomEvent("fs-auth-ready", { detail: { user } }));
  });
});