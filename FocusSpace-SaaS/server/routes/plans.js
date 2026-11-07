// server/routes/plans.js
const express = require("express");
const { COUNTRIES, getAllPlansForCountry } = require("../config/plans");

const router = express.Router();

// Public: list supported countries (for the dropdown).
router.get("/countries", (req, res) => {
  const list = Object.entries(COUNTRIES).map(([code, c]) => ({ code, name: c.name, currency: c.currency }));
  res.json({ countries: list });
});

// Public: get plan prices for a given country, computed server-side from
// the exchange rates in .env. The client never sends/controls a price.
router.get("/for-country/:code", (req, res) => {
  const code = String(req.params.code || "").toUpperCase();
  const plans = getAllPlansForCountry(code);
  if (!plans) {
    return res.status(400).json({ error: "Unsupported country. This service is available in Egypt and Gulf countries only." });
  }
  res.json({ country: code, plans });
});

module.exports = router;
