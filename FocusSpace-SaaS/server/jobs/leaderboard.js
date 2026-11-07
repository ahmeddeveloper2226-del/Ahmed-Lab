// server/jobs/leaderboard.js
//
// Two scheduled jobs, both running inside this always-on server (Railway
// keeps the process alive, so a plain node-cron is enough here — no
// separate infra needed):
//
// 1. refreshSnapshot() — every 15 minutes, recomputes a small public
//    `leaderboard/current` doc (top streaks + masked display name only,
//    never full user docs) so the frontend can show it without needing
//    broad read access to every user's profile.
//
// 2. runWeeklyRewards() — once a week (Monday 00:00 UTC), reads the top 3
//    by current streak and extends their subscription for free:
//    1st = 60 days, 2nd = 30 days, 3rd = 14 days. Idempotent per ISO
//    week (records `leaderboardHistory/{weekId}`; re-running the same
//    week is a no-op) so a restart or an overlapping run can't double-pay.
const cron = require("node-cron");
const { db } = require("../firebaseAdmin");

const REWARD_DAYS = [60, 30, 14]; // 1st, 2nd, 3rd place
const DAY_MS = 24 * 60 * 60 * 1000;

function isoWeekId(date = new Date()) {
  // ISO week number, e.g. "2026-W38" — stable regardless of what day the
  // job happens to run on.
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d - yearStart) / DAY_MS + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

function maskedName(userData) {
  const raw = (userData.displayName || (userData.email || "").split("@")[0] || "Player").trim();
  if (raw.length <= 2) return raw[0] + "*";
  return raw[0] + "*".repeat(Math.max(1, raw.length - 2)) + raw[raw.length - 1];
}

async function refreshSnapshot() {
  try {
    const snap = await db.collection("users").orderBy("currentStreak", "desc").limit(10).get();
    const top = snap.docs.map((d) => {
      const u = d.data();
      return { name: maskedName(u), streak: u.currentStreak || 0 };
    });
    await db.collection("leaderboard").doc("current").set({
      top,
      updatedAt: Date.now(),
    });
  } catch (err) {
    console.error("[leaderboard/refreshSnapshot] failed:", err.message);
  }
}

async function runWeeklyRewards() {
  const weekId = isoWeekId();
  const historyRef = db.collection("leaderboardHistory").doc(weekId);

  try {
    const already = await historyRef.get();
    if (already.exists) {
      console.log(`[leaderboard/weeklyRewards] ${weekId} already paid out, skipping.`);
      return;
    }

    const snap = await db
      .collection("users")
      .orderBy("currentStreak", "desc")
      .orderBy("longestStreak", "desc")
      .limit(3)
      .get();

    if (snap.empty) {
      await historyRef.set({ weekId, winners: [], ranAt: Date.now(), note: "No eligible users." });
      return;
    }

    const winners = [];
    for (let i = 0; i < snap.docs.length; i++) {
      const uid = snap.docs[i].id;
      const u = snap.docs[i].data();
      const days = REWARD_DAYS[i];
      if (!days) break;

      const subRef = db.collection("subscriptions").doc(uid);
      const now = Date.now();

      await db.runTransaction(async (tx) => {
        const subSnap = await tx.get(subRef);
        const existing = subSnap.exists ? subSnap.data() : null;
        const baseTime = existing && Number(existing.expiresAt) > now ? Number(existing.expiresAt) : now;
        const newExpiry = baseTime + days * DAY_MS;
        tx.set(
          subRef,
          {
            status: "active",
            expiresAt: newExpiry,
            planId: existing?.planId || "leaderboard-reward",
            lastRewardDays: days,
            lastRewardWeek: weekId,
            updatedAt: now,
          },
          { merge: true }
        );
      });

      winners.push({ uid, name: maskedName(u), streak: u.currentStreak || 0, rewardDays: days, place: i + 1 });
      console.log(`[leaderboard/weeklyRewards] ${weekId}: place ${i + 1} -> uid ${uid}, +${days} days`);
    }

    await historyRef.set({ weekId, winners, ranAt: Date.now() });
  } catch (err) {
    console.error("[leaderboard/weeklyRewards] failed:", err.message);
  }
}

function start() {
  // Every 15 minutes.
  cron.schedule("*/15 * * * *", refreshSnapshot);
  // Every Monday at 00:00 UTC.
  cron.schedule("0 0 * * 1", runWeeklyRewards, { timezone: "UTC" });

  // Run once at boot too, so the leaderboard isn't empty right after a deploy.
  refreshSnapshot();
}

module.exports = { start, refreshSnapshot, runWeeklyRewards, isoWeekId };