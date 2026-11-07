// server/middleware/verifyAuth.js
// Verifies the Firebase ID token sent as `Authorization: Bearer <token>`.
// This is the ONLY source of identity the backend trusts — never a
// client-supplied uid/email in the request body.
const { admin } = require("../firebaseAdmin");

async function verifyAuth(req, res, next) {
  try {
    const header = req.headers.authorization || "";
    const match = header.match(/^Bearer (.+)$/);
    if (!match) {
      return res.status(401).json({ error: "Missing authentication token." });
    }

    // verifyIdToken checks the signature against Google's public keys,
    // the expiry, issuer and audience — it cannot be forged client-side.
    const decoded = await admin.auth().verifyIdToken(match[1]);

    const isGoogle = decoded.firebase?.sign_in_provider === "google.com";
    const verified = isGoogle || !!decoded.email_verified;

    if (!verified) {
      return res.status(403).json({ error: "Please verify your email before continuing." });
    }

    req.user = {
      uid: decoded.uid,
      email: decoded.email || null,
      emailVerified: verified,
    };
    next();
  } catch (err) {
    // Covers expired tokens, revoked sessions, malformed tokens, clock skew, etc.
    console.error("[verifyAuth] rejected:", err.message);
    res.status(401).json({ error: "Invalid or expired session. Please sign in again." });
  }
}

module.exports = verifyAuth;
