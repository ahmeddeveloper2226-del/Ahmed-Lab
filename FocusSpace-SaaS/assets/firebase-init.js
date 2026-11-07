// assets/firebase-init.js
// Single shared Firebase initialization. Every page imports from here so
// there is exactly one Firebase App instance per tab.
//
// NOTE: this apiKey is a public *client* identifier, not a secret — Firebase
// web API keys are meant to be embedded in frontend code (see Firebase docs
// "Is it safe to expose my Firebase apiKey?"). Actual access control lives
// in Firestore Security Rules and in the backend's verifyIdToken check, not
// in hiding this value.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signOut,
  updateProfile,
  setPersistence,
  browserLocalPersistence,
} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";
import {
  getFirestore,
  doc,
  getDoc,
  setDoc,
  addDoc,
  collection,
  query,
  orderBy,
  limit,
  getDocs,
  runTransaction,
  serverTimestamp,
} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyAI1I2BBfYIERfI7vaNKYytH3kq4nNrZ44",
  authDomain: "focusspace-fc0f3.firebaseapp.com",
  projectId: "focusspace-fc0f3",
  storageBucket: "focusspace-fc0f3.firebasestorage.app",
  messagingSenderId: "426281589068",
  appId: "1:426281589068:web:7dfb2bae68888c4c7ed7e9",
  measurementId: "G-Y1JGTKSMDH",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();
// Keep the session across tab closes (still fully revocable server-side by
// disabling the user in Firebase Console, and every request is re-verified
// against Google's servers via verifyIdToken — this only affects how long
// the *browser* remembers the sign-in).
setPersistence(auth, browserLocalPersistence).catch(() => {});

export {
  onAuthStateChanged,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signOut,
  updateProfile,
  doc,
  getDoc,
  setDoc,
  addDoc,
  collection,
  query,
  orderBy,
  limit,
  getDocs,
  runTransaction,
  serverTimestamp,
};

/** UTC calendar date as YYYY-MM-DD — used for streaks so "day" means the
 * same thing regardless of the user's/server's local timezone. */
function utcDateString(d = new Date()) {
  return d.toISOString().slice(0, 10);
}
function utcDateStringMinusDays(dateStr, days) {
  const d = new Date(dateStr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - days);
  return utcDateString(d);
}

/**
 * Saves a completed focus session to users/{uid}/sessions (immutable
 * history — Firestore rules forbid editing/deleting it after creation)
 * and, in the same transaction, updates the user's totalScore and
 * daily streak.
 *
 * Streak logic: a "day" is UTC-calendar-day based. Finishing another
 * session on a day you already logged one today doesn't change the
 * streak; finishing one on the very next day extends it by 1; any
 * bigger gap resets it to 1.
 *
 * NOTE ON TRUST: session score/duration/tasks are computed client-side
 * by the timer UI (the whole session flow already is, with no server
 * verification of elapsed time) — Firestore rules bound the values to
 * plausible ranges but can't fully prevent a determined user from
 * inflating their own history. Good enough to stop casual abuse; not
 * cryptographically tamper-proof. A fully tamper-proof version would
 * need the timer itself to be server-authoritative.
 */
export async function recordSessionResult(user, session) {
  const userRef = doc(db, "users", user.uid);
  const sessionRef = doc(collection(db, "users", user.uid, "sessions"));

  const today = utcDateString();
  const yesterday = utcDateStringMinusDays(today, 1);

  await runTransaction(db, async (tx) => {
    const userSnap = await tx.get(userRef);
    const prev = userSnap.exists() ? userSnap.data() : {};

    const prevScore = typeof prev.totalScore === "number" ? prev.totalScore : 0;
    const prevStreak = typeof prev.currentStreak === "number" ? prev.currentStreak : 0;
    const prevLongest = typeof prev.longestStreak === "number" ? prev.longestStreak : 0;
    const prevDate = prev.lastSessionDate || null;

    let newStreak;
    if (prevDate === today) newStreak = prevStreak; // already logged today
    else if (prevDate === yesterday) newStreak = prevStreak + 1; // consecutive day
    else newStreak = 1; // gap, or very first session

    tx.set(
      userRef,
      {
        totalScore: prevScore + session.score,
        currentStreak: newStreak,
        longestStreak: Math.max(prevLongest, newStreak),
        lastSessionDate: today,
      },
      { merge: true }
    );

    tx.set(sessionRef, {
      field: session.field || "General",
      sub: session.sub || "General",
      score: session.score,
      tasksDone: session.tasksDone,
      tasksTotal: session.tasksTotal,
      actualMinutes: session.actualMinutes,
      plannedMinutes: session.plannedMinutes,
      tasks: session.tasks || [],
      createdAt: serverTimestamp(),
    });
  });
}

/** True if this user's identity is considered verified (Google is
 * pre-verified by Google; email/password needs the emailVerified flag). */
export function isVerified(user) {
  if (!user) return false;
  if (user.providerData.some((p) => p.providerId === "google.com")) return true;
  return !!user.emailVerified;
}

/** Creates the user's Firestore profile doc on first sign-in, or just
 * bumps lastLoginAt on subsequent ones — never clobbers createdAt. */
export async function syncUserProfile(user) {
  const ref = doc(db, "users", user.uid);
  const existing = await getDoc(ref).catch(() => null);
  const base = {
    email: user.email || null,
    displayName: user.displayName || null,
    photoURL: user.photoURL || null,
    provider: user.providerData[0]?.providerId || "password",
    lastLoginAt: serverTimestamp(),
  };
  if (!existing || !existing.exists()) {
    base.createdAt = serverTimestamp();
  }
  await setDoc(ref, base, { merge: true });
}