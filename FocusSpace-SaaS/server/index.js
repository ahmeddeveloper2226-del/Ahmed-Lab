require("dotenv").config();

// Fail fast and loud if Firebase Admin isn't configured — every gated
// route depends on it, so better to crash on boot than serve broken auth.
require("./firebaseAdmin");

const express = require("express");
const helmet = require("helmet");
const cors = require("cors");
const path = require("path");

const { generalLimiter } = require("./middleware/rateLimiters");
const plansRoutes = require("./routes/plans");
const paymentRoutes = require("./routes/payment");
const subscriptionRoutes = require("./routes/subscription");
const leaderboardJob = require("./jobs/leaderboard");

const app = express();

app.set("trust proxy", 1);
app.use(
  helmet({
    contentSecurityPolicy: false,
    // Helmet's default Cross-Origin-Opener-Policy ("same-origin") blocks
    // the popup window Firebase's signInWithPopup opens for Google
    // sign-in from talking back to this tab — the popup finishes, then
    // silently closes with no result. "unsafe-none" is what Firebase's
    // own hosting preset uses for this exact reason.
    crossOriginOpenerPolicy: { policy: "unsafe-none" },
  })
);
app.use(
  cors({
    origin: (process.env.ALLOWED_ORIGINS || "").split(",").filter(Boolean),
    methods: ["GET", "POST"],
    credentials: true,
  })
);
app.use((req, res, next) => {
  express.json({ limit: "50kb" })(req, res, next);
});
app.use(generalLimiter);

app.use("/api/plans", plansRoutes);
app.use("/api/payment", paymentRoutes);
app.use("/api/subscription", subscriptionRoutes);

app.get("/api/health", (req, res) => res.json({ ok: true }));

const frontendDir = path.join(__dirname, "..");
app.use(express.static(frontendDir, { index: "index.html", extensions: ["html"] }));

app.use((err, req, res, next) => {
  console.error("[unhandled]", err);
  res.status(500).json({ error: "Something went wrong." });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  leaderboardJob.start();
});