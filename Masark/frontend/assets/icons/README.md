Add real app icons here before deploying:
  - icon-192.png (192x192)
  - icon-512.png (512x512)
  - favicon.ico (or favicon.svg)

These are referenced by manifest.json, firebase-messaging-sw.js, and (once
you add <link rel="icon">/<link rel="manifest"> tags to each HTML page's
<head>) the browser tab/home-screen icon. Nothing renders without a name
mistake right now — the app works fine without them, this is purely
polish for install-to-home-screen / notification icons.
