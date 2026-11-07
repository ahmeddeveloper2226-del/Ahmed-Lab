// server/config/devAccess.js
// Accounts that get full access without paying (you, for development
// and demos).
//
// This is enforced SERVER-SIDE ONLY, against the email inside the
// verified Firebase ID token — never against anything the browser
// sends. A user cannot put themselves on this list: the email in the
// token is signed by Google and checked in verifyAuth, and the frontend
// never gets a say in it.
//
// Add more via the DEV_EMAILS env var (comma-separated) without touching
// code — anything there is merged with the built-in list below.

const BUILT_IN_DEV_EMAILS = [
  "intelligentera2226@gmail.com",
];

const DEV_EMAILS = new Set(
  [
    ...BUILT_IN_DEV_EMAILS,
    ...(process.env.DEV_EMAILS || "").split(","),
  ]
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
);

/**
 * @param {{email?: string|null}} user - req.user, populated by verifyAuth
 *   from the decoded ID token. Never pass a client-supplied object.
 */
function isDevAccount(user) {
  if (!user || !user.email) return false;
  return DEV_EMAILS.has(user.email.trim().toLowerCase());
}

module.exports = { isDevAccount, DEV_EMAILS };
