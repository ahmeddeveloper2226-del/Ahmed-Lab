/**
 * Firebase Cloud Messaging service worker — handles push notifications
 * that arrive while the app isn't in the foreground (the daily "lectures
 * left" / homework reminders sent by backend/app/jobs/scheduler.py).
 *
 * Must be served from the site root (not /assets/) — FCM requires the
 * service worker's scope to cover the whole origin.
 */
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "REPLACE_WITH_YOUR_ROTATED_FIREBASE_API_KEY",
  authDomain: "masark-38cee.firebaseapp.com",
  projectId: "masark-38cee",
  storageBucket: "masark-38cee.firebasestorage.app",
  messagingSenderId: "REPLACE_WITH_YOUR_SENDER_ID",
  appId: "REPLACE_WITH_YOUR_APP_ID",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const { title, body, icon } = payload.notification || {};
  self.registration.showNotification(title || "مسارك", {
    body,
    icon: icon || "/assets/icons/icon-192.png",
    badge: "/assets/icons/icon-192.png",
  });
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow("/home.html"));
});
