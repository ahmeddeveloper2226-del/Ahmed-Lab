// server/config/plans.js
// Plan definitions (source of truth is USD). Never trust a price sent from the client.

const PLANS = {
  monthly: { id: "monthly", label: "1 Month", days: 30, usd: 10 },
  quarterly: { id: "quarterly", label: "3 Months", days: 90, usd: 30 },
  yearly: { id: "yearly", label: "1 Year", days: 365, usd: 80 },
};

// Supported countries: Egypt + Gulf only, as requested.
// Each maps to a currency code and the .env exchange-rate variable name.
const COUNTRIES = {
  EG: { name: "Egypt", currency: "EGP", rateEnv: "USD_TO_EGP_RATE" },
  SA: { name: "Saudi Arabia", currency: "SAR", rateEnv: "USD_TO_SAR_RATE" },
  AE: { name: "United Arab Emirates", currency: "AED", rateEnv: "USD_TO_AED_RATE" },
  OM: { name: "Oman", currency: "OMR", rateEnv: "USD_TO_OMR_RATE" },
  KW: { name: "Kuwait", currency: "KWD", rateEnv: "USD_TO_KWD_RATE" },
  QA: { name: "Qatar", currency: "QAR", rateEnv: "USD_TO_QAR_RATE" },
  BH: { name: "Bahrain", currency: "BHD", rateEnv: "USD_TO_BHD_RATE" },
};

function getRate(countryCode) {
  const country = COUNTRIES[countryCode];
  if (!country) return null;
  const rate = parseFloat(process.env[country.rateEnv]);
  if (!rate || rate <= 0) return null;
  return rate;
}

// Returns price in the smallest currency unit (e.g. piastres/fils), which is
// what Paymob's `amount_cents` expects — this also avoids floating point bugs.
function getPlanPriceCents(planId, countryCode) {
  const plan = PLANS[planId];
  const rate = getRate(countryCode);
  if (!plan || !rate) return null;
  const amount = plan.usd * rate;
  return Math.round(amount * 100);
}

function getAllPlansForCountry(countryCode) {
  const country = COUNTRIES[countryCode];
  if (!country) return null;
  return Object.values(PLANS).map((plan) => {
    const cents = getPlanPriceCents(plan.id, countryCode);
    return {
      id: plan.id,
      label: plan.label,
      days: plan.days,
      currency: country.currency,
      amount: cents !== null ? +(cents / 100).toFixed(2) : null,
    };
  });
}

module.exports = { PLANS, COUNTRIES, getRate, getPlanPriceCents, getAllPlansForCountry };
