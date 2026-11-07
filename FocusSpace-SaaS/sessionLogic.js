// ─────────────────────────────────────────────────────────────
//  logic/sessionLogic.js
//  Core session planning logic + countdown timer
// ─────────────────────────────────────────────────────────────

import { getTimerGroup, TIMER_MAP } from "./fields.js";

// ── Difficulty ────────────────────────────────────────────────

/** @typedef {"easy" | "medium" | "hard"} Difficulty */

const VALID_DIFFICULTIES = new Set(["easy", "medium", "hard"]);

/**
 * @param {string} value
 * @returns {Difficulty | null}
 */
export function parseDifficulty(value) {
  const normalized = value.trim().toLowerCase();
  return VALID_DIFFICULTIES.has(normalized) ? normalized : null;
}

// ── Task Duration ─────────────────────────────────────────────

/**
 * Returns the allocated time (minutes) for a task
 * based on its parent field and difficulty.
 *
 * @param {string}     field
 * @param {Difficulty} difficulty
 * @returns {number | null}
 */
export function getTaskDuration(field, difficulty) {
  const group = getTimerGroup(field);
  if (!group) return null;

  return TIMER_MAP[group][difficulty] ?? null;
}

// ── Task Object ───────────────────────────────────────────────

/**
 * @typedef {Object} Task
 * @property {string}      name
 * @property {Difficulty}  difficulty
 * @property {number|null} duration    - allocated minutes
 * @property {boolean}     completed
 * @property {number|null} actualTime  - filled after session ends
 */

/**
 * Creates a validated Task object.
 *
 * @param {string} name
 * @param {Difficulty} difficulty
 * @param {string} field - parent field (used for duration lookup)
 * @returns {Task}
 */
export function createTask(name, difficulty, field) {
  const diff     = parseDifficulty(difficulty);
  const duration = diff ? getTaskDuration(field, diff) : null;

  return {
    name,
    difficulty: diff ?? difficulty,
    duration,
    completed:  false,
    actualTime: null,
  };
}

// ── Session Plan ──────────────────────────────────────────────

/**
 * @typedef {Object} SessionBlock
 * @property {"work" | "break"}  type
 * @property {number}            duration   - minutes
 * @property {Task|null}         task       - null for break blocks
 * @property {number}            startMin   - offset from session start (minutes)
 */

/**
 * @typedef {Object} SessionPlan
 * @property {"work" | "study"}  mode
 * @property {string}            field
 * @property {string}            subfield
 * @property {Task[]}            tasks
 * @property {SessionBlock[]}    blocks
 * @property {number}            totalMinutes
 * @property {number}            workMinutes
 * @property {number}            breakMinutes
 * @property {Date}              createdAt
 */

const BREAK_AFTER_BLOCKS = 1;   // insert a break every N work blocks
const BREAK_DURATION     = 10;  // minutes

/**
 * Sorts tasks: hard → medium → easy (peak energy first).
 * @param {Task[]} tasks
 * @returns {Task[]}
 */
function sortByDifficulty(tasks) {
  const order = { hard: 0, medium: 1, easy: 2 };
  return [...tasks].sort((a, b) => (order[a.difficulty] ?? 3) - (order[b.difficulty] ?? 3));
}

/**
 * Builds a full session plan from a list of tasks.
 *
 * @param {"work" | "study"} mode
 * @param {string}           field
 * @param {string}           subfield
 * @param {Task[]}           tasks
 * @returns {SessionPlan}
 */
export function buildSessionPlan(mode, field, subfield, tasks) {
  const sorted = sortByDifficulty(tasks);
  const blocks  = [];
  let cursor    = 0;  // minute offset from start

  sorted.forEach((task, index) => {
    const duration = task.duration ?? 30;

    // ── Work block ────────────────────────────────────────────
    blocks.push({
      type:     "work",
      duration,
      task,
      startMin: cursor,
    });
    cursor += duration;

    // ── Break block (not after the last task) ─────────────────
    const isLast      = index === sorted.length - 1;
    const breakNeeded = (index + 1) % BREAK_AFTER_BLOCKS === 0;

    if (!isLast && breakNeeded) {
      blocks.push({
        type:     "break",
        duration: BREAK_DURATION,
        task:     null,
        startMin: cursor,
      });
      cursor += BREAK_DURATION;
    }
  });

  const workMinutes  = blocks
    .filter((b) => b.type === "work")
    .reduce((sum, b) => sum + b.duration, 0);

  const breakMinutes = blocks
    .filter((b) => b.type === "break")
    .reduce((sum, b) => sum + b.duration, 0);

  return {
    mode,
    field,
    subfield,
    tasks:        sorted,
    blocks,
    totalMinutes: workMinutes + breakMinutes,
    workMinutes,
    breakMinutes,
    createdAt:    new Date(),
  };
}

// ── Session Summary ───────────────────────────────────────────

/**
 * @typedef {Object} SessionSummary
 * @property {number} focusScore       - 0 to 100
 * @property {number} completedTasks
 * @property {number} totalTasks
 * @property {number} plannedMinutes
 * @property {number} actualMinutes
 */

/**
 * Calculates the focus score at the end of a session.
 *
 * Focus score weights:
 *   60% → task completion rate
 *   40% → time accuracy (how close actual was to planned)
 *
 * @param {Task[]} tasks
 * @param {number} actualMinutes - total time the user actually spent
 * @returns {SessionSummary}
 */
export function calcSessionSummary(tasks, actualMinutes) {
  const totalTasks     = tasks.length;
  const completedTasks = tasks.filter((t) => t.completed).length;
  const plannedMinutes = tasks.reduce((s, t) => s + (t.duration ?? 0), 0);

  const completionScore = totalTasks > 0 ? completedTasks / totalTasks : 0;

  const timeAccuracy =
    plannedMinutes > 0
      ? Math.max(0, 1 - Math.abs(actualMinutes - plannedMinutes) / plannedMinutes)
      : 0;

  const focusScore = Math.round((completionScore * 0.6 + timeAccuracy * 0.4) * 100);

  return {
    focusScore,
    completedTasks,
    totalTasks,
    plannedMinutes,
    actualMinutes,
  };
}

// ── Countdown Timer ───────────────────────────────────────────

/**
 * @typedef {Object} TimerCallbacks
 * @property {(remaining: { minutes: number, seconds: number }) => void} onTick
 * @property {() => void} onComplete
 */

/**
 * @typedef {Object} TimerControls
 * @property {() => void} pause
 * @property {() => void} resume
 * @property {() => void} stop
 */

/**
 * Starts a countdown timer.
 *
 * @param {number}         minutes
 * @param {TimerCallbacks} callbacks
 * @returns {TimerControls}
 *
 * @example
 * const timer = startTimer(25, {
 *   onTick:     ({ minutes, seconds }) => console.log(`${minutes}:${seconds}`),
 *   onComplete: () => console.log("Done!"),
 * });
 *
 * timer.pause();
 * timer.resume();
 * timer.stop();
 */
export function startTimer(minutes, { onTick, onComplete }) {
  let remaining = minutes * 60;
  let intervalId = null;
  let running    = true;

  function tick() {
    if (remaining <= 0) {
      clearInterval(intervalId);
      onComplete?.();
      return;
    }

    onTick?.({
      minutes: Math.floor(remaining / 60),
      seconds: remaining % 60,
    });

    remaining -= 1;
  }

  // Fire immediately so UI shows full time before first decrement
  onTick?.({
    minutes: Math.floor(remaining / 60),
    seconds: remaining % 60,
  });

  intervalId = setInterval(tick, 1_000);

  return {
    pause()  {
      if (running) {
        clearInterval(intervalId);
        running = false;
      }
    },
    resume() {
      if (!running) {
        intervalId = setInterval(tick, 1_000);
        running    = true;
      }
    },
    stop()   {
      clearInterval(intervalId);
      running = false;
    },
  };
}
