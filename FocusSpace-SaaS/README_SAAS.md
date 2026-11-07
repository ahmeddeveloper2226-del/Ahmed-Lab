# FocusSpace — SaaS Edition

A self-serve subscription product: Firebase Auth accounts (Google +
email/password with verification), Firestore-backed subscriptions, and
Paymob payments, gated by country (Egypt + Gulf) and plan length.

## ⚠️ Do this first — two separate leaks to rotate

**1. Firebase service account key.** The `focusspace.json` file you had
in this project contains a full Admin SDK private key — not a public
client key. Anyone holding it can read/write your entire Firestore
database and manage your users, bypassing every security rule. It has
been **removed from these files** rather than copied forward. Rotate it
now:
1. Firebase Console -> Project Settings -> Service Accounts -> **Generate
   new private key**. This automatically invalidates the old one.
2. Put the new `project_id`, `client_email`, and `private_key` into your
   local `.env` (see below) — never into a file that gets zipped, chatted,
   or committed.

**2. Paymob keys**, if/when you fill them in `.env`: same rule — rotate
before real use, keep them only in your local, gitignored `.env`.

The `firebaseConfig` object with `apiKey` you shared in chat is fine to
keep as-is — that's a public *client* identifier Firebase expects to be
embedded in frontend code; it grants no access by itself. Real access
control is Firestore Security Rules + the backend verifying ID tokens,
both described below.

## Does this need a server? Yes — static hosting alone will not work.

- **Paymob's secret key/HMAC secret and the Firebase Admin key must
  never reach the browser.** They only ever live in `server/`'s `.env`.
- **Subscription activation comes only from a verified Paymob webhook**
  (HMAC-checked with `crypto.timingSafeEqual`), never from the page the
  user's browser redirects to after paying — a redirect can be faked,
  a signed webhook can't.
- **Firestore writes that grant access use the Admin SDK**
  (`server/firebaseAdmin.js`), not the public client SDK — a signed-in
  user can never write `subscriptions/{their-own-uid}` themselves (see
  `firestore.rules`).

Deploy `server/` to Render, Railway, Fly.io, or a small VPS. It also
serves the static frontend files directly (`server/index.js`), so you
deploy one thing.

## Setup

```bash
npm install
# fill in .env: Firebase Admin credentials (rotated) + Paymob keys (rotated)
npm start
```

### Enable sign-in methods
Firebase Console -> **Authentication -> Sign-in method**: enable
**Email/Password** and **Google**. For Google sign-in outside
`localhost`, add your production domain under **Authentication ->
Settings -> Authorized domains**.

### Reduce verification emails landing in spam
Firebase's default sender (`noreply@<project>.firebaseapp.com`) is
generally fine, but for better deliverability:
- **Authentication -> Templates -> Email address verification** — customize
  the sender name and subject line; generic auto-generated emails get
  flagged more often.
- Optionally add a **custom domain** for the email action handler
  (Authentication -> Templates -> gear icon -> "Customize action URL") and,
  if you send from a domain you own, set up SPF/DKIM for it.
- `login.html` already throttles resend requests (60s cooldown) —
  hammering "resend" repeatedly is itself a common cause of emails
  getting flagged.
- None of this is airtight (deliverability is ultimately mailbox-provider
  heuristics), so the UI also tells users to check Spam/Promotions and
  mark the sender "not spam".

### Deploy Firestore security rules
`firestore.rules` in this repo is the source of truth — deploy it via
the Firebase Console (Firestore -> Rules -> paste + Publish) or the
Firebase CLI (`firebase deploy --only firestore:rules`). Summary of what
it enforces:
- `users/{uid}`: a signed-in user can read/write **only their own**
  profile doc, and only a fixed, typed set of fields — no client can
  ever set arbitrary fields on their own doc.
- `users/{uid}/payments/*` and `subscriptions/{uid}`: users can **read**
  their own, but **never write** — only the backend's Admin SDK can,
  and only from the HMAC-verified webhook.
- `pendingOrders/*`: no client access at all, in either direction.
- Everything else: denied by default.

### Paymob webhook URL
In your Paymob dashboard, set the transaction callback (webhook) URL to:
`https://yourdomain.com/api/payment/webhook`

## How auth flows through the app

- `login.html` — the sign-in/sign-up page (Google button + email/password
  with a verification-pending screen + forgot-password flow), styled to
  match `index.html`.
- `assets/firebase-init.js` — the one shared Firebase App/Auth/Firestore
  instance every page imports.
- `assets/auth-guard.js` — included via `<script type="module">` on
  `index.html`, `homep.html`, and `plans.html`. Redirects to
  `login.html?next=<page>` if the visitor isn't signed in, or to
  `login.html?next=<page>&verify=1` if they're signed in but an
  email/password account isn't verified yet. On success it upserts the
  `users/{uid}` Firestore profile doc and exposes `window.FS` with
  `.user`, `.logout()`, and `.authedFetch(url, opts)` (a `fetch` wrapper
  that attaches `Authorization: Bearer <ID token>`).
- The backend's `verifyAuth` middleware (`server/middleware/verifyAuth.js`)
  verifies that token on every gated route and rejects unverified
  email/password accounts server-side too (never trust the client alone).

## What's stored, and where

- **`users/{uid}`** (Firestore, client-writable to own doc): `email`,
  `displayName`, `photoURL`, `provider`, `createdAt`, `lastLoginAt`.
- **`users/{uid}/payments/{paymobTransactionId}`** (Firestore,
  server-write-only): payment history per user.
- **`subscriptions/{uid}`** (Firestore, server-write-only): current
  plan/status/expiry, keyed by Firebase `uid` — this replaces the old
  SQLite `device_id`-keyed table, so access now follows the *account*,
  not the browser/device.
- **`pendingOrders/{merchantOrderId}`** (Firestore, server-only,
  never exposed to any client): in-flight checkout bookkeeping, with the
  authoritative server-computed price.

## Security measures applied

- `helmet` for standard HTTP security headers. (CSP is left off because
  the frontend uses inline `<script type="text/babel">` + inline styles;
  tightening this would need moving to build-time JSX and nonce'd
  styles — worth doing later, not blocking to ship.)
- `cors` locked to an explicit allow-list (`ALLOWED_ORIGINS`), not `*`.
- Rate limiting, **per IP and per authenticated uid**: general API
  (100/15min/IP), subscription status (60/15min/uid), payment creation
  (6/10min/IP **and** 6/10min/uid), webhook (30/min safety net).
- Every subscription/payment route requires a verified Firebase ID token
  (`verifyAuth`); orders are tied to `req.user.uid` from that token,
  never a client-supplied value. Unverified email/password accounts are
  rejected at this layer, independent of the frontend check.
- Firestore Security Rules deny all client writes to `subscriptions`,
  `payments`, and `pendingOrders` — only the Admin SDK, running on your
  server, can write them.
- **Prices are always computed server-side** from `.env` exchange rates —
  the client only ever sends a `planId` + `countryCode`, never an amount.
- Subscription is only ever activated by a **Paymob webhook whose HMAC
  signature was verified** with `crypto.timingSafeEqual` (constant-time,
  avoids timing attacks) — never by the client-side redirect.
- Idempotent webhook handling via a Firestore transaction (checks
  `pendingOrders` status inside the transaction, and the payment doc id
  is Paymob's own transaction id) so retried/duplicate webhook calls
  can't double-extend a subscription.
- Amount-paid vs amount-quoted is checked in the webhook to catch tampering.
- JSON body size capped (`50kb`) to reduce abuse/DoS surface.
- No stack traces or internal errors ever returned to the client.
- Secrets only ever read from `process.env`; `.env` is gitignored; the
  Admin service account JSON itself is never checked into this repo.

## Possible further improvements (not yet built, worth considering)

- A "my subscription" page showing renewal date + payment history (the
  data — `subscriptions/{uid}` and `users/{uid}/payments` — already
  exists; this would just be a read-only UI on top of it).
- Enable Content-Security-Policy once the frontend build moves off
  inline `<script type="text/babel">`.
- Auto-renewal (Paymob subscriptions/tokenized recurring billing) instead
  of manual repurchase.
- Email/SMS receipt on successful payment.
- Admin dashboard for subscriptions/refunds.
- Move exchange rates to a scheduled job pulling live FX rates.
- Structured logging + alerting on repeated webhook signature failures
  or repeated `verifyAuth` rejections from the same IP (could indicate
  a spoofing/credential-stuffing attempt).
- Deploy Firestore composite indexes / TTL policy on `pendingOrders` if
  the collection grows large (old pending/failed orders currently never
  expire — harmless but will accumulate).
