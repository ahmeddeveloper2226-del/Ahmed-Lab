// server/firebaseAdmin.js
// Initializes the Firebase Admin SDK from environment variables only.
// NEVER commit the service account file — .env (gitignored) holds these.
// Only this server process can write to `subscriptions/*` and
// `users/*/payments/*` in Firestore; the client SDK is blocked from
// those paths by firestore.rules.
const admin = require("firebase-admin");

// Most "Failed to parse private key" / "Invalid PEM" errors happen because
// a hosting platform's env-var UI mangles the multi-line PEM string
// (strips real newlines, or double-escapes/un-escapes the literal `\n`,
// or wraps the whole value in extra quotes that become PART of the
// value). Whole-value base64 sidesteps all of that, so it's the
// recommended path for deployment; the split PEM var still works for
// local dev with a plain .env file.
function loadCredential() {
  // Option A (recommended for Render/Railway/Fly/etc.): one base64 blob
  // of the ENTIRE service account JSON file.
  //   macOS/Linux: base64 -i serviceAccount.json | tr -d '\n'
  //   or:          node -e "console.log(Buffer.from(require('fs').readFileSync('serviceAccount.json')).toString('base64'))"
  const b64Full = process.env.FIREBASE_SERVICE_ACCOUNT_BASE64;
  if (b64Full) {
    let parsed;
    try {
      parsed = JSON.parse(Buffer.from(b64Full.trim(), "base64").toString("utf8"));
    } catch (e) {
      throw new Error(
        "FIREBASE_SERVICE_ACCOUNT_BASE64 did not decode to valid JSON. " +
        "Make sure you base64'd the *entire* service account file with no line wrapping."
      );
    }
    return validate({
      projectId: parsed.project_id,
      clientEmail: parsed.client_email,
      privateKey: parsed.private_key,
    });
  }

  // Option B: just the private key base64'd on its own, paired with the
  // other two fields as plain env vars.
  const b64Key = process.env.FIREBASE_PRIVATE_KEY_BASE64;
  const projectId = process.env.FIREBASE_PROJECT_ID;
  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  if (b64Key) {
    const privateKey = Buffer.from(b64Key.trim(), "base64").toString("utf8");
    return validate({ projectId, clientEmail, privateKey });
  }

  // Option C: the raw PEM string as FIREBASE_PRIVATE_KEY (works fine
  // locally in a real .env file; fragile on some hosting UIs — prefer
  // Option A there). Handles literal "\n", accidental wrapping quotes,
  // and stray surrounding whitespace.
  let rawKey = process.env.FIREBASE_PRIVATE_KEY;
  if (rawKey) {
    rawKey = rawKey.trim();
    if (
      (rawKey.startsWith('"') && rawKey.endsWith('"')) ||
      (rawKey.startsWith("'") && rawKey.endsWith("'"))
    ) {
      rawKey = rawKey.slice(1, -1);
    }
    rawKey = rawKey.replace(/\\n/g, "\n");
  }
  return validate({ projectId, clientEmail, privateKey: rawKey });
}

function validate({ projectId, clientEmail, privateKey }) {
  const missing = [];
  if (!projectId) missing.push("FIREBASE_PROJECT_ID");
  if (!clientEmail) missing.push("FIREBASE_CLIENT_EMAIL");
  if (!privateKey) missing.push("FIREBASE_PRIVATE_KEY (or FIREBASE_PRIVATE_KEY_BASE64 / FIREBASE_SERVICE_ACCOUNT_BASE64)");
  if (missing.length) {
    throw new Error(
      `Missing Firebase Admin credentials: ${missing.join(", ")}. ` +
      "Copy them from your (rotated) Firebase service account JSON — see README_SAAS.md."
    );
  }
  if (!privateKey.includes("BEGIN PRIVATE KEY") || !privateKey.includes("END PRIVATE KEY")) {
    throw new Error(
      "FIREBASE_PRIVATE_KEY does not look like a valid PEM key after parsing " +
      "(missing BEGIN/END markers). This almost always means the hosting " +
      "platform's env var UI altered the newlines/quotes. Switch to " +
      "FIREBASE_SERVICE_ACCOUNT_BASE64 instead — see README_SAAS.md."
    );
  }
  return { projectId, clientEmail, privateKey };
}

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(loadCredential()),
  });
}

const db = admin.firestore();

module.exports = { admin, db };
