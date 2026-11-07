// server/routes/subscription.js
const express = require("express");
const verifyAuth = require("../middleware/verifyAuth");
const { subscriptionLimiterPerUser } = require("../middleware/rateLimiters");
const { db } = require("../firebaseAdmin");
const { isDevAccount } = require("../config/devAccess");

const router = express.Router();

router.get("/status", verifyAuth, subscriptionLimiterPerUser, async (req, res) => {
  try {
    // Developer accounts get access without paying. Checked against the
    // email in the *verified* ID token (req.user), so this can't be
    // spoofed from the browser.
    if (isDevAccount(req.user)) {
      return res.json({
        subscribed: true,
        planId: "dev",
        expiresAt: null,
        dev: true,
      });
    }

    const snap = await db.collection("subscriptions").doc(req.user.uid).get();
    if (!snap.exists) return res.json({ subscribed: false });

    const row = snap.data();
    const subscribed = row.status === "active" && Number(row.expiresAt) > Date.now();
    res.json({
      subscribed,
      planId: row.planId || null,
      expiresAt: row.expiresAt || null,
    });
  } catch (err) {
    console.error("[subscription/status] failed:", err.message);
    res.status(500).json({ error: "Could not check subscription status." });
  }
});

module.exports = router;