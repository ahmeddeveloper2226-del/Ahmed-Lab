// ─────────────────────────────────────────────────────────────
//  index.js  —  Public API
// ─────────────────────────────────────────────────────────────

// Firebase
export { sendOTP, verifyOTP, logout, onAuthChange, isUserAllowed } from "./firebase/auth.js";
export { auth, db } from "./firebase/config.js";

// Fields data
export { WORK_FIELDS, STUDY_FIELDS, TIMER_GROUPS, TIMER_MAP, getTimerGroup } from "./logic/fields.js";

// Session logic
export {
  createTask,
  buildSessionPlan,
  calcSessionSummary,
  startTimer,
  getTaskDuration,
  parseDifficulty,
} from "./logic/sessionLogic.js";
