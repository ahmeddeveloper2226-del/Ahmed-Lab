/**
 * Firebase client SDK bootstrap (modular v10, loaded from Google's CDN —
 * allowed in a published/deployed static site; if serving through the
 * Artifact-hosted preview instead, swap this import for the pinned CDN
 * build listed in that environment's allowed script hosts).
 *
 * NOTE: this apiKey is a public, client-side identifier (not a secret —
 * Firebase's real security boundary is Firestore/Storage rules + App
 * Check), so it's fine for it to live in frontend source. It was shared in
 * this project's planning conversation; if you'd rather issue a fresh one
 * anyway, do it from Firebase Console > Project Settings > General.
 */
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js";
import {
  getAuth, GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword,
  createUserWithEmailAndPassword, onAuthStateChanged, signOut,
} from "https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging.js";

const firebaseConfig = {
  apiKey: "AIzaSyC-sy0zBfPUTLJztoVVKglXnfg1ifEBznw",
  authDomain: "masark-38cee.firebaseapp.com",
  projectId: "masark-38cee",
  storageBucket: "masark-38cee.firebasestorage.app",
  messagingSenderId: "363744534715",
  appId: "1:363744534715:web:4adb601f3bc4427603c99e",
  measurementId: "G-N9LJQ67GQL"
};

export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const googleProvider = new GoogleAuthProvider();

export {
  signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword,
  onAuthStateChanged, signOut, getMessaging, getToken, onMessage,
};
