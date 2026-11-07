/**
 * Push-notification opt-in: registers the service worker, asks for
 * permission, gets an FCM token, and registers it on the user's profile.
 * Call `initPushNotifications()` once from home.html after sign-in — it's
 * intentionally NOT called from every page (asking on first login, once,
 * is enough; repeatedly re-prompting is the fastest way to get a user to
 * permanently deny notifications).
 */
import { getMessaging, getToken } from "/assets/js/firebase-config.js";
import { apiPost } from "/assets/js/api.js";

const VAPID_KEY = "REPLACE_WITH_YOUR_WEB_PUSH_VAPID_KEY"; // Firebase Console > Project Settings > Cloud Messaging > Web Push certificates

export async function initPushNotifications() {
  if (!("serviceWorker" in navigator) || !("Notification" in window)) return;
  if (localStorage.getItem("masark:pushPrompted")) return;
  localStorage.setItem("masark:pushPrompted", "1");

  try {
    const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;

    const messaging = getMessaging();
    const token = await getToken(messaging, { vapidKey: VAPID_KEY, serviceWorkerRegistration: registration });
    if (token) {
      await apiPost(`/users/me/fcm-token?token=${encodeURIComponent(token)}`);
    }
  } catch {
    /* push is a nice-to-have; never block the app on it */
  }
}
