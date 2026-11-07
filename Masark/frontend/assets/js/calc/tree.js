/**
 * Expression model for the calculator's natural display.
 * A Row is an array of nodes. Nodes are either simple (chars, function names) or "templates"
 * (fraction, power, root …) that own child rows. The cursor is { row, i }.
 */
const SLOTS = { frac: ["n", "d"], pow: ["e"], sqrt: ["r"], root: ["n", "r"], abs: ["r"], logb: ["b", "a"], int: ["lo", "hi", "f"], sum: ["lo", "hi", "f"], diff: ["f", "at"], mixed: ["w", "n", "d"], exp: ["e"] };
export const rowsOf = (node) => (SLOTS[node.k] ? SLOTS[node.k].map((s) => node[s]) : []);
export const isTemplate = (node) => !!SLOTS[node.k];

export function newRow() { return []; }
export function link(row, owner = null, slot = 0) {
  row.owner = owner; row.slot = slot;
  for (const node of row) {
    node.row = row;
    if (SLOTS[node.k]) SLOTS[node.k].forEach((s, i) => { if (!node[s]) node[s] = []; link(node[s], node, i); });
  }
  return row;
}
export function template(k, rows = {}) {
  const node = { k };
  for (const s of SLOTS[k]) node[s] = rows[s] || [];
  return node;
}
export const chr = (v) => ({ k: "c", v });
export const fn = (v) => ({ k: "fn", v });

/** deep copy without parent pointers → plain JSON-able structure */
export function plain(row) {
  return row.map((n) => {
    if (!SLOTS[n.k]) return { k: n.k, v: n.v };
    const o = { k: n.k }; for (const s of SLOTS[n.k]) o[s] = plain(n[s]); return o;
  });
}
export const fromPlain = (arr) => link(JSON.parse(JSON.stringify(arr)));
export const cloneRow = (row) => fromPlain(plain(row));

/* ------------------------------------------------------------------ cursor */
export const makeCursor = (row) => ({ row, i: row.length });
export function moveRight(c) {
  const { row, i } = c;
  if (i < row.length) { const rs = rowsOf(row[i]); if (rs.length) { c.row = rs[0]; c.i = 0; } else c.i++; return; }
  const o = row.owner; if (!o) return;
  const rs = rowsOf(o);
  if (row.slot < rs.length - 1) { c.row = rs[row.slot + 1]; c.i = 0; } else { c.row = o.row; c.i = o.row.indexOf(o) + 1; }
}
export function moveLeft(c) {
  const { row, i } = c;
  if (i > 0) { const rs = rowsOf(row[i - 1]); if (rs.length) { const last = rs[rs.length - 1]; c.row = last; c.i = last.length; } else c.i--; return; }
  const o = row.owner; if (!o) return;
  const rs = rowsOf(o);
  if (row.slot > 0) { const prev = rs[row.slot - 1]; c.row = prev; c.i = prev.length; } else { c.row = o.row; c.i = o.row.indexOf(o); }
}
const ABOVE = { frac: [1, 0], int: [0, 1], sum: [0, 1], mixed: [2, 1] };   // [lowerSlot, upperSlot]
export function moveUp(c) {
  const o = c.row.owner;
  if (o && ABOVE[o.k] && c.row.slot === ABOVE[o.k][0]) { const r = rowsOf(o)[ABOVE[o.k][1]]; c.row = r; c.i = Math.min(c.i, r.length); return true; }
  if (c.i > 0 && c.row[c.i - 1].k === "pow") { const r = c.row[c.i - 1].e; c.row = r; c.i = r.length; return true; }
  return false;
}
export function moveDown(c) {
  const o = c.row.owner;
  if (o && ABOVE[o.k] && c.row.slot === ABOVE[o.k][1]) { const r = rowsOf(o)[ABOVE[o.k][0]]; c.row = r; c.i = Math.min(c.i, r.length); return true; }
  if (o && (o.k === "pow" || o.k === "exp")) { c.row = o.row; c.i = o.row.indexOf(o) + 1; return true; }
  return false;
}
export function insert(c, node) {
  c.row.splice(c.i, 0, node); node.row = c.row; c.i++;
  if (SLOTS[node.k]) { link(node.row, node.row.owner, node.row.slot); const rs = rowsOf(node); c.row = rs[0]; c.i = 0; }
  return node;
}
export const insertChar = (c, v) => insert(c, chr(v));
/** insert a template; the number literal just before the cursor moves into `intoSlot` (like the real calculator) */
export function insertTemplate(c, k, intoSlot = null) {
  let moved = [];
  if (intoSlot) {
    let j = c.i; while (j > 0 && c.row[j - 1].k === "c" && /^[0-9.]$/.test(c.row[j - 1].v)) j--;
    moved = c.row.splice(j, c.i - j); c.i = j;
  }
  const node = template(k); node[intoSlot || SLOTS[k][0]] = moved;
  c.row.splice(c.i, 0, node); node.row = c.row; c.i++;
  link(node.row, node.row.owner, node.row.slot);
  const rs = rowsOf(node);
  if (intoSlot && moved.length) { const next = SLOTS[k].indexOf(intoSlot) + 1; c.row = rs[Math.min(next, rs.length - 1)]; c.i = 0; } else { c.row = rs[0]; c.i = 0; }
  return node;
}
const allEmpty = (n) => rowsOf(n).every((r) => r.length === 0);
export function backspace(c) {
  const { row, i } = c;
  if (i > 0) {
    const nd = row[i - 1];
    if (!SLOTS[nd.k]) { row.splice(i - 1, 1); c.i--; return; }
    if (allEmpty(nd)) { row.splice(i - 1, 1); c.i--; return; }
    const rs = rowsOf(nd), last = rs[rs.length - 1]; c.row = last; c.i = last.length; return;
  }
  const o = row.owner; if (!o) return;
  if (allEmpty(o)) { const par = o.row, at = par.indexOf(o); par.splice(at, 1); c.row = par; c.i = at; return; }
  moveLeft(c);
}
export const clearRow = (row) => { row.length = 0; };
export const isEmpty = (row) => row.length === 0;

/* --------------------------------------------------------------- tokenising */
const LETTERS = new Set(["A", "B", "C", "D", "E", "F", "X", "Y", "M"]);
export function charKind(v) {
  if (/^[0-9.]$/.test(v)) return "num";
  if (v === "π" || v === "e" || v === "i" || v === "Ans" || v === "Ran#") return "const";
  if (LETTERS.has(v)) return "var";
  if (v === "+" || v === "-" || v === "×" || v === "÷") return "op";
  if (v === "(") return "lp"; if (v === ")") return "rp"; if (v === ",") return "sep"; if (v === "=") return "eq";
  if (v === "!" || v === "%" || v === "°" || v === "′" || v === "″" || v === "r" || v === "g") return "post";
  if (v === "nPr" || v === "nCr") return "infix";
  if (v === "∠") return "infix";
  return "other";
}
/** flatten a row into tokens (templates stay single tokens holding their child rows) */
export function tokenize(row) {
  const out = []; let i = 0;
  while (i < row.length) {
    const n = row[i];
    if (n.k === "c" && charKind(n.v) === "num") {
      let s = ""; const start = i; while (i < row.length && row[i].k === "c" && charKind(row[i].v) === "num") { s += row[i].v; i++; }
      const tok = { t: "num", v: s, row, i: start };
      if (i < row.length && row[i].k === "exp") { tok.exp = row[i]; i++; }
      out.push(tok); continue;
    }
    if (n.k === "c") out.push({ t: charKind(n.v), v: n.v, row, i });
    else if (n.k === "fn") out.push({ t: "fn", v: n.v, row, i });
    else if (n.k === "pow") out.push({ t: "pow", node: n, row, i });
    else if (n.k === "exp") out.push({ t: "num", v: "1", exp: n, row, i, implicitOne: true });
    else out.push({ t: "node", node: n, row, i });
    i++;
  }
  return out;
}
/** build a row from plain text (used by tests and for restoring simple expressions) */
export function rowFromText(str) {
  const row = []; const FN = ["asinh", "acosh", "atanh", "sinh", "cosh", "tanh", "asin", "acos", "atan", "sin", "cos", "tan", "log", "ln", "Pol", "Rec", "Intg", "Int", "Abs", "RanInt", "Conjg", "arg", "Re", "Im"];
  for (let k = 0; k < str.length;) {
    const m = FN.find((f) => str.startsWith(f, k));
    if (m) { row.push(fn(m)); k += m.length; continue; }
    if (str.startsWith("Ans", k)) { row.push(chr("Ans")); k += 3; continue; }
    if (str.startsWith("nPr", k) || str.startsWith("nCr", k)) { row.push(chr(str.slice(k, k + 3))); k += 3; continue; }
    let c = str[k++]; if (c === "*") c = "×"; else if (c === "/") c = "÷";
    row.push(chr(c));
  }
  return link(row);
}
