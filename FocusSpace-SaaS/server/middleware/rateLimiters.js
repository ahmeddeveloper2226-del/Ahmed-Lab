// server/middleware/rateLimiters.js
const rateLimit = require("express-rate-limit");

// General API traffic — per IP.
const generalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 min
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many requests. Please try again later." },
});

// Payment creation is the most sensitive/expensive route — much tighter,
// per IP. Combined with paymentLimiterPerUser below so a single account
// can't just rotate IPs, and a single IP (e.g. shared NAT) doesn't lock
// out unrelated users.
const paymentLimiter = rateLimit({
  windowMs: 10 * 60 * 1000, // 10 min
  max: 6,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many payment attempts. Please wait a few minutes and try again." },
});

// Same route, keyed by the verified Firebase uid instead of IP. Must run
// AFTER verifyAuth (so req.user exists) — falls back to IP if somehow
// missing, which should never happen given the route order.
const paymentLimiterPerUser = rateLimit({
  windowMs: 10 * 60 * 1000,
  max: 6,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => req.user?.uid || req.ip,
  message: { error: "Too many payment attempts on this account. Please wait a few minutes and try again." },
});

// Subscription-status polling, keyed per uid — generous, since the
// frontend calls this on every page load, but still bounded.
const subscriptionLimiterPerUser = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 60,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => req.user?.uid || req.ip,
  message: { error: "Too many requests. Please slow down." },
});

// Paymob webhook: Paymob itself calls this, but keep a generous ceiling
// as a safety net against replay storms/abuse of the public endpoint.
const webhookLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
});

module.exports = {
  generalLimiter,
  paymentLimiter,
  paymentLimiterPerUser,
  subscriptionLimiterPerUser,
  webhookLimiter,
};
