/** Maths behind the STAT, EQN and BASE-N modes (exact where possible, like the real calculator). */
import * as M from "./num.js";
import { MathError } from "./num.js";
import { isC } from "./parser.js";

const Z = M.ZERO, ONE = M.ONE, two = M.nQ(2);
const sqrtSafe = (v) => { if (M.sign(v) < 0) { if (Math.abs(v.f) < 1e-12) return Z; throw new MathError(); } return M.sqrt(v); };

/* ----------------------------------------------------------------- STAT */
const median = (a) => { const n = a.length, h = n >> 1; return n % 2 ? a[h] : M.div(M.add(a[h - 1], a[h]), two); };
export function stat1(xs, fs) {
  const rows = xs.map((x, i) => ({ x, f: fs ? fs[i] : ONE })).filter((r) => !M.isZero(r.f));
  if (!rows.length) throw new MathError();
  let n = Z, sx = Z, sxx = Z;
  for (const { x, f } of rows) { n = M.add(n, f); sx = M.add(sx, M.mul(f, x)); sxx = M.add(sxx, M.mul(f, M.mul(x, x))); }
  const mean = M.div(sx, n), varp = M.sub(M.div(sxx, n), M.mul(mean, mean));
  const out = [["n", n], ["Σx", sx], ["Σx²", sxx], ["x̄", mean], ["σx", sqrtSafe(varp)]];
  out.push(["sx", M.cmp(n, ONE) > 0 ? sqrtSafe(M.div(M.sub(sxx, M.mul(n, M.mul(mean, mean))), M.sub(n, ONE))) : null]);
  const sorted = rows.slice().sort((a, b) => M.cmp(a.x, b.x)), list = [];
  if (M.isInt(n) && Number(M.qOf(n).n) <= 20000) for (const r of sorted) { const k = M.isInt(r.f) ? Number(M.qOf(r.f).n) : 1; for (let i = 0; i < k; i++) list.push(r.x); }
  out.push(["minX", sorted[0].x]);
  if (list.length > 1) {
    const h = list.length >> 1, lower = list.slice(0, h), upper = list.slice(list.length % 2 ? h + 1 : h);
    out.push(["Q1", lower.length ? median(lower) : null], ["Med", median(list)], ["Q3", upper.length ? median(upper) : null]);
  }
  out.push(["maxX", sorted[sorted.length - 1].x]);
  return out.filter((r) => r[1] !== null);
}
function gauss(A) {                                   // exact Gauss–Jordan on an n×(n+1) matrix of N values
  const n = A.length; A = A.map((r) => r.slice());
  for (let c = 0; c < n; c++) {
    let p = -1, best = -1; for (let r = c; r < n; r++) if (!M.isZero(A[r][c]) && Math.abs(A[r][c].f) > best) { best = Math.abs(A[r][c].f); p = r; if (M.isExact(A[r][c])) break; }
    if (p < 0) throw new MathError();
    [A[c], A[p]] = [A[p], A[c]];
    const d = A[c][c]; A[c] = A[c].map((v) => M.div(v, d));
    for (let r = 0; r < n; r++) if (r !== c && !M.isZero(A[r][c])) { const f = A[r][c]; A[r] = A[r].map((v, j) => M.sub(v, M.mul(f, A[c][j]))); }
  }
  return A.map((r) => r[n]);
}
export function stat2(xs, ys, fs, quad = false) {
  const rows = xs.map((x, i) => ({ x, y: ys[i], f: fs ? fs[i] : ONE })).filter((r) => !M.isZero(r.f));
  if (rows.length < 2) throw new MathError();
  const S = { n: Z, x: Z, y: Z, xx: Z, yy: Z, xy: Z, x3: Z, x4: Z, xxy: Z };
  for (const { x, y, f } of rows) {
    const x2 = M.mul(x, x);
    S.n = M.add(S.n, f); S.x = M.add(S.x, M.mul(f, x)); S.y = M.add(S.y, M.mul(f, y)); S.xx = M.add(S.xx, M.mul(f, x2)); S.yy = M.add(S.yy, M.mul(f, M.mul(y, y)));
    S.xy = M.add(S.xy, M.mul(f, M.mul(x, y))); S.x3 = M.add(S.x3, M.mul(f, M.mul(x2, x))); S.x4 = M.add(S.x4, M.mul(f, M.mul(x2, x2))); S.xxy = M.add(S.xxy, M.mul(f, M.mul(x2, y)));
  }
  const mx = M.div(S.x, S.n), my = M.div(S.y, S.n);
  const out = [["n", S.n], ["Σx", S.x], ["Σx²", S.xx], ["Σy", S.y], ["Σy²", S.yy], ["Σxy", S.xy], ["x̄", mx], ["ȳ", my],
    ["σx", sqrtSafe(M.sub(M.div(S.xx, S.n), M.mul(mx, mx)))], ["σy", sqrtSafe(M.sub(M.div(S.yy, S.n), M.mul(my, my)))]];
  if (quad) {
    const [c, b, a] = gauss([[S.n, S.x, S.xx, S.y], [S.x, S.xx, S.x3, S.xy], [S.xx, S.x3, S.x4, S.xxy]]);
    out.push(["a", c], ["b", b], ["c", a]);
  } else {
    const den = M.sub(M.mul(S.n, S.xx), M.mul(S.x, S.x)); if (M.isZero(den)) throw new MathError();
    const b = M.div(M.sub(M.mul(S.n, S.xy), M.mul(S.x, S.y)), den), a = M.div(M.sub(S.y, M.mul(b, S.x)), S.n);
    const rd = M.mul(den, M.sub(M.mul(S.n, S.yy), M.mul(S.y, S.y)));
    out.push(["a", a], ["b", b], ["r", M.isZero(rd) ? null : M.div(M.sub(M.mul(S.n, S.xy), M.mul(S.x, S.y)), sqrtSafe(rd))]);
  }
  return out.filter((r) => r[1] !== null);
}

/* ------------------------------------------------------------------ EQN */
export const solveLinear = (A) => gauss(A);
export function quadratic(a, b, c) {
  if (M.isZero(a)) throw new MathError();
  const disc = M.sub(M.mul(b, b), M.mul(M.nQ(4), M.mul(a, c))), a2 = M.mul(two, a), nb = M.neg(b);
  if (M.sign(disc) >= 0) { const s = M.sqrt(disc); return [M.div(M.add(nb, s), a2), M.div(M.sub(nb, s), a2)]; }
  const re = M.div(nb, a2), im = M.div(M.sqrt(M.neg(disc)), a2);
  return [{ re, im }, { re, im: M.neg(im) }];
}
const divisors = (n) => { const out = []; for (let i = 1; i * i <= n && i < 1e5; i++) if (n % i === 0) { out.push(i); if (i !== n / i) out.push(n / i); } return out; };
export function cubic(a, b, c, d) {
  if (M.isZero(a)) throw new MathError();
  const co = [a, b, c, d];
  if (co.every((v) => M.isQ(v))) {                      // rational-root theorem on an integer version
    let L = 1n; for (const v of co) { const q = M.qOf(v).d; L = (L * q) / M_gcd(L, q); }
    const I = co.map((v) => M.qOf(v).n * (L / M.qOf(v).d));
    const p = Number(I[3] < 0n ? -I[3] : I[3]), q = Number(I[0] < 0n ? -I[0] : I[0]);
    const cands = new Set(); if (p === 0) cands.add("0/1"); else for (const dp of divisors(p)) for (const dq of divisors(q)) { cands.add(`${dp}/${dq}`); cands.add(`-${dp}/${dq}`); }
    for (const s of cands) {
      const [pn, qn] = s.split("/"), r = M.nQ(Number(pn), Number(qn));
      const v = M.add(M.mul(M.add(M.mul(M.add(M.mul(a, r), b), r), c), r), d);
      if (M.isZero(v)) {                                // synthetic division → quadratic
        const b1 = M.add(M.mul(a, r), b), c1 = M.add(M.mul(b1, r), c);
        return [r, ...quadratic(a, b1, c1)];
      }
    }
  }
  const A = b.f / a.f, B = c.f / a.f, C = d.f / a.f, p = B - (A * A) / 3, q = (2 * A ** 3) / 27 - (A * B) / 3 + C, sh = A / 3;
  const disc = (q / 2) ** 2 + (p / 3) ** 3;
  if (disc > 0) {
    const s = Math.sqrt(disc), u = Math.cbrt(-q / 2 + s), v = Math.cbrt(-q / 2 - s), re = -(u + v) / 2 - sh, im = (Math.sqrt(3) / 2) * (u - v);
    return [M.nF(u + v - sh), { re: M.nF(re), im: M.nF(im) }, { re: M.nF(re), im: M.nF(-im) }];
  }
  const r = Math.sqrt(-((p / 3) ** 3)), phi = Math.acos(clamp(-q / (2 * r || 1), -1, 1)), m = 2 * Math.cbrt(r);
  return [0, 1, 2].map((k) => M.nF(m * Math.cos((phi + 2 * Math.PI * k) / 3) - sh));
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const M_gcd = M.bgcd;

/* -------------------------------------------------------------- BASE-N */
export const BASES = { 2: "BIN", 8: "OCT", 10: "DEC", 16: "HEX" };
const DIG = "0123456789ABCDEF";
export const baseDigitOk = (ch, base) => { const i = DIG.indexOf(ch); return i >= 0 && i < base; };
const i32 = (v) => BigInt.asIntN(32, v);
/** evaluate a BASE-N expression given as a list of tokens ({d:"1F"} numbers, or operator strings) */
export function baseEval(tokens, base) {
  let p = 0; const peek = () => tokens[p], next = () => tokens[p++];
  const err = () => { throw new MathError("Syntax ERROR"); };
  const isOp = (t, s) => typeof t === "string" && s.includes(t);
  function orx() { let l = andx(); while (isOp(peek(), ["or", "xor", "xnor"])) { const o = next(), r = andx(); l = o === "or" ? l | r : o === "xor" ? l ^ r : ~(l ^ r); l = i32(l); } return l; }
  function andx() { let l = add(); while (isOp(peek(), ["and"])) { next(); l = i32(l & add()); } return l; }
  function add() { let l = mul(); while (isOp(peek(), ["+", "-"])) { const o = next(), r = mul(); l = i32(o === "+" ? l + r : l - r); } return l; }
  function mul() { let l = un(); while (isOp(peek(), ["×", "÷"])) { const o = next(), r = un(); if (o === "÷") { if (r === 0n) throw new MathError(); l = i32(l / r); } else l = i32(l * r); } return l; }
  function un() {
    const t = peek(); if (t === undefined) err();
    if (t === "-") { next(); return i32(-un()); }
    if (t === "Not" || t === "Neg") { next(); const v = un(); return i32(t === "Not" ? ~v : -v); }
    return prim();
  }
  function prim() {
    const t = next(); if (t === undefined) err();
    if (t === "(") { const v = orx(); if (peek() === ")") next(); return v; }
    if (typeof t === "object") { const v = BigInt("0x" + "0") + [...t.d].reduce((a, ch) => a * BigInt(base) + BigInt(DIG.indexOf(ch)), 0n); if (v > 0xffffffffn) throw new MathError(); return i32(v); }
    return err();
  }
  const v = orx(); if (p < tokens.length) err(); return v;
}
export function baseFormat(v, base) {
  if (base === 10) return v.toString();
  const u = BigInt.asUintN(32, v), s = u.toString(base).toUpperCase();
  return base === 2 ? s.padStart(Math.ceil(s.length / 4) * 4, "0") : s;
}
