// server/routes/payment.js
const express = require("express");
const crypto = require("crypto");
const { db } = require("../firebaseAdmin");
const { PLANS, COUNTRIES, getPlanPriceCents } = require("../config/plans");
const { initiatePayment, verifyHmac } = require("../utils/paymob");
const { paymentLimiter, paymentLimiterPerUser, webhookLimiter } = require("../middleware/rateLimiters");
const verifyAuth = require("../middleware/verifyAuth");

const router = express.Router();

// Requires a verified sign-in: verifyAuth runs first, so both rate
// limiters below can key on req.user.uid, and the order is permanently
// tied to that uid — never a client-supplied id.
router.post("/create-order", verifyAuth, paymentLimiter, paymentLimiterPerUser, async (req, res) => {
  try {
    const { planId, countryCode } = req.body || {};
    const country = COUNTRIES[String(countryCode || "").toUpperCase()];
    const plan = PLANS[planId];

    if (!country || !plan) {
      return res.status(400).json({ error: "Invalid plan or unsupported country." });
    }

    const amountCents = getPlanPriceCents(plan.id, countryCode.toUpperCase());
    if (!amountCents) {
      return res.status(400).json({ error: "Pricing unavailable for this country right now." });
    }

    const merchantOrderId = `sub_${req.user.uid}_${plan.id}_${Date.now()}_${crypto.randomBytes(4).toString("hex")}`;

    // Written by the Admin SDK only — clients can never read/write
    // pendingOrders directly (see firestore.rules).
    await db.collection("pendingOrders").doc(merchantOrderId).set({
      uid: req.user.uid,
      planId: plan.id,
      days: plan.days,
      countryCode: countryCode.toUpperCase(),
      amountCents,
      status: "pending",
      createdAt: Date.now(),
    });

    const { iframeUrl } = await initiatePayment({
      amountCents,
      merchantOrderId,
      billingData: {
        first_name: (req.user.email || "Customer").split("@")[0],
        last_name: "Customer",
        email: req.user.email || "customer@focusspace.app",
        phone_number: "+201000000000",
        apartment: "NA",
        floor: "NA",
        street: "NA",
        building: "NA",
        shipping_method: "NA",
        postal_code: "NA",
        city: country.name,
        country: country.name,
        state: "NA",
      },
    });

    res.json({ iframeUrl });
  } catch (err) {
    console.error("[payment/create-order] failed:", err.message);
    res.status(502).json({ error: "Could not start payment. Please try again shortly." });
  }
});

// Public endpoint (Paymob calls this directly, so no verifyAuth here) —
// but every write it makes is gated on a verified HMAC signature, and
// wrapped in a Firestore transaction for idempotency, so retried/duplicate
// calls can never double-extend a subscription or forge one out of thin air.
router.post("/webhook", webhookLimiter, express.json(), async (req, res) => {
  try {
    const obj = req.body?.obj;
    if (!obj) return res.status(400).send("Missing payload.");

    if (!verifyHmac(req.query, obj)) {
      return res.status(401).send("Invalid signature.");
    }

    const merchantOrderId = obj.order?.merchant_order_id;
    if (!merchantOrderId) return res.status(400).send("Missing merchant_order_id.");

    const orderRef = db.collection("pendingOrders").doc(merchantOrderId);

    const result = await db.runTransaction(async (tx) => {
      const orderSnap = await tx.get(orderRef);
      if (!orderSnap.exists) return { code: 404, msg: "Unknown order." };

      const order = orderSnap.data();
      if (order.status === "completed") return { code: 200, msg: "Already processed." };

      if (obj.success !== true || obj.pending === true) {
        tx.update(orderRef, { status: "failed" });
        return { code: 200, msg: "Payment not successful; recorded." };
      }

      if (Number(obj.amount_cents) !== Number(order.amountCents)) {
        tx.update(orderRef, { status: "amount_mismatch" });
        return { code: 400, msg: "Amount mismatch." };
      }

      const now = Date.now();
      const subRef = db.collection("subscriptions").doc(order.uid);
      const subSnap = await tx.get(subRef);
      const existing = subSnap.exists ? subSnap.data() : null;
      const baseTime = existing && Number(existing.expiresAt) > now ? Number(existing.expiresAt) : now;
      const newExpiry = baseTime + order.days * 24 * 60 * 60 * 1000;

      tx.set(
        subRef,
        {
          planId: order.planId,
          status: "active",
          expiresAt: newExpiry,
          lastPaymentAmountCents: order.amountCents,
          lastPaymentCountry: order.countryCode,
          updatedAt: now,
        },
        { merge: true }
      );

      // Payment doc id = Paymob's own transaction id -> re-deliveries of
      // the same webhook are naturally idempotent even outside the
      // "already completed" short-circuit above.
      const paymentRef = db.collection("users").doc(order.uid).collection("payments").doc(String(obj.id));
      tx.set(paymentRef, {
        planId: order.planId,
        amountCents: order.amountCents,
        countryCode: order.countryCode,
        paymobTransactionId: obj.id,
        merchantOrderId,
        createdAt: now,
      });

      tx.update(orderRef, { status: "completed", paymobTransactionId: obj.id });

      return { code: 200, msg: "OK" };
    });

    res.status(result.code).send(result.msg);
  } catch (err) {
    console.error("[payment/webhook] error:", err.message);
    res.status(500).send("Internal error.");
  }
});

module.exports = router;
