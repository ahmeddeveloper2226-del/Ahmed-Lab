// server/utils/paymob.js
// Talks to Paymob's Accept API. All secret values come from process.env —
// never hardcode keys here.

const crypto = require("crypto");

const PAYMOB_BASE = "https://accept.paymob.com/api";

async function paymobFetch(path, options) {
  const res = await fetch(`${PAYMOB_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`Paymob ${path} failed: ${res.status} ${JSON.stringify(data)}`);
  }
  return data;
}

// Step 1: authenticate with the API key to get a short-lived auth token.
async function getAuthToken() {
  const data = await paymobFetch("/auth/tokens", {
    method: "POST",
    body: JSON.stringify({ api_key: process.env.PAYMOB_API_KEY }),
  });
  return data.token;
}

// Step 2: register an order.
async function createOrder({ authToken, amountCents, merchantOrderId }) {
  const data = await paymobFetch("/ecommerce/orders", {
    method: "POST",
    body: JSON.stringify({
      auth_token: authToken,
      delivery_needed: false,
      amount_cents: amountCents,
      currency: "EGP", // Paymob's order currency is fixed per integration; conversion is display-only elsewhere.
      merchant_order_id: merchantOrderId,
      items: [],
    }),
  });
  return data.id;
}

// Step 3: request a payment key scoped to this order/integration.
async function getPaymentKey({ authToken, amountCents, orderId, billingData }) {
  const data = await paymobFetch("/acceptance/payment_keys", {
    method: "POST",
    body: JSON.stringify({
      auth_token: authToken,
      amount_cents: amountCents,
      expiration: 3600,
      order_id: orderId,
      billing_data: billingData,
      currency: "EGP",
      integration_id: Number(process.env.PAYMOB_INTEGRATION_ID),
    }),
  });
  return data.token;
}

function buildIframeUrl(paymentKey) {
  return `https://accept.paymob.com/api/acceptance/iframes/${process.env.PAYMOB_IFRAME_ID}?payment_token=${paymentKey}`;
}

/**
 * Full flow: returns { iframeUrl, orderId } ready to hand to the client.
 */
async function initiatePayment({ amountCents, merchantOrderId, billingData }) {
  const authToken = await getAuthToken();
  const orderId = await createOrder({ authToken, amountCents, merchantOrderId });
  const paymentKey = await getPaymentKey({ authToken, amountCents, orderId, billingData });
  return { iframeUrl: buildIframeUrl(paymentKey), orderId };
}

/**
 * Verifies Paymob's HMAC signature on a transaction webhook payload.
 * This is the ONLY thing that should be trusted to mark a subscription
 * active — never trust the client-side "success" redirect alone.
 *
 * Paymob computes HMAC over a specific, ordered concatenation of fields
 * from the `obj` (transaction) payload. See Paymob docs for the exact
 * field order for your integration type; this list matches the standard
 * card transaction callback.
 */
function verifyHmac(query, obj) {
  const hmacFromPaymob = query.hmac;
  if (!hmacFromPaymob) return false;

  const orderedFields = [
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order.id",
    "owner",
    "pending",
    "source_data.pan",
    "source_data.sub_type",
    "source_data.type",
    "success",
  ];

  const getField = (path) =>
    path.split(".").reduce((o, key) => (o == null ? undefined : o[key]), obj);

  const concatenated = orderedFields.map((f) => String(getField(f) ?? "")).join("");

  const computed = crypto
    .createHmac("sha512", process.env.PAYMOB_HMAC_SECRET)
    .update(concatenated)
    .digest("hex");

  // Constant-time comparison to avoid timing attacks.
  const a = Buffer.from(computed, "utf8");
  const b = Buffer.from(hmacFromPaymob, "utf8");
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = { initiatePayment, verifyHmac };
