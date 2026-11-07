/**
 * Exact + floating number tower for the scientific calculator.
 *   Q  – rational (BigInt n/d)
 *   X  – exact value  a + b·√r + c·π   (a,b,c rational, r squarefree integer)
 *   N  – { x: X|null, f: number }  exact value when we have one, always a float approximation
 * Anything that can't stay exact falls back to a float, like the real calculator does.
 */
export class MathError extends Error { constructor(msg = "Math ERROR") { super(msg); this.kind = "math"; } }

const babs = (a) => (a < 0n ? -a : a);
export function bgcd(a, b) { a = babs(a); b = babs(b); while (b) { const t = a % b; a = b; b = t; } return a; }
export const bpow = (b, e) => { let r = 1n; for (let i = 0n; i < e; i++) r *= b; return r; };
function isqrt(n) {
  if (n < 2n) return n;
  let x = BigInt(Math.floor(Math.sqrt(Number(n))));
  while (x * x > n) x--; while ((x + 1n) * (x + 1n) <= n) x++;
  return x;
}
function sqfree(m) {                                  // m = k² · s  (s squarefree); null if too big
  if (m > 1000000000000000n) return null;
  let n = Number(m), k = 1, s = 1;
  for (let p = 2; p * p * p <= n; p++) {
    if (n % p === 0) { let e = 0; while (n % p === 0) { n /= p; e++; } k *= p ** (e >> 1); if (e & 1) s *= p; }
  }
  const r = Math.round(Math.sqrt(n));
  if (r * r === n) k *= r; else s *= n;
  return [BigInt(k), BigInt(s)];
}
function iroot(n, k) {                                // exact k-th root of a non-negative BigInt, or null
  if (n < 2n) return n;
  let x = BigInt(Math.round(Math.pow(Number(n), 1 / k)));
  for (let d = -2n; d <= 2n; d++) { const y = x + d; if (y >= 0n && bpow(y, BigInt(k)) === n) return y; }
  return null;
}

export class Q {
  constructor(n, d = 1n) {
    if (d === 0n) throw new MathError();
    if (d < 0n) { n = -n; d = -d; }
    const g = bgcd(n, d) || 1n; this.n = n / g; this.d = d / g;
  }
  static of(n, d = 1) { return new Q(BigInt(n), BigInt(d)); }
  add(o) { return new Q(this.n * o.d + o.n * this.d, this.d * o.d); }
  sub(o) { return new Q(this.n * o.d - o.n * this.d, this.d * o.d); }
  mul(o) { return new Q(this.n * o.n, this.d * o.d); }
  div(o) { return new Q(this.n * o.d, this.d * o.n); }
  neg() { return new Q(-this.n, this.d); }
  isZero() { return this.n === 0n; }
  isInt() { return this.d === 1n; }
  sign() { return this.n < 0n ? -1 : this.n > 0n ? 1 : 0; }
  cmp(o) { const l = this.n * o.d, r = o.n * this.d; return l < r ? -1 : l > r ? 1 : 0; }
  eq(o) { return this.n === o.n && this.d === o.d; }
  toNumber() {
    const a = Number(this.n), b = Number(this.d);
    if (Number.isFinite(a) && Number.isFinite(b)) return a / b;
    const sn = this.n.toString().length, sd = this.d.toString().length, sh = Math.max(sn, sd) - 300;
    return Number(this.n / bpow(10n, BigInt(Math.max(0, sh)))) / Number(this.d / bpow(10n, BigInt(Math.max(0, sh))) || 1n);
  }
}
const Q0 = new Q(0n), Q1 = new Q(1n);

export class X {
  constructor(a = Q0, b = Q0, r = 0n, c = Q0) { this.a = a; this.b = b; this.r = b.isZero() ? 0n : r; this.c = c; }
  static q(q) { return new X(q); }
  isRational() { return this.b.isZero() && this.c.isZero(); }
  toNumber() { return this.a.toNumber() + (this.b.isZero() ? 0 : this.b.toNumber() * Math.sqrt(Number(this.r))) + (this.c.isZero() ? 0 : this.c.toNumber() * Math.PI); }
  neg() { return new X(this.a.neg(), this.b.neg(), this.r, this.c.neg()); }
  add(o) {
    let r = 0n;
    if (this.b.isZero()) r = o.r; else if (o.b.isZero()) r = this.r; else if (this.r === o.r) r = this.r; else return null;
    return new X(this.a.add(o.a), this.b.add(o.b), r, this.c.add(o.c));
  }
  sub(o) { return this.add(o.neg()); }
  mul(o) {
    const [a1, b1, c1, a2, b2, c2] = [this.a, this.b, this.c, o.a, o.b, o.c];
    if (!c1.isZero() && !c2.isZero()) return null;
    if ((!b1.isZero() && !c2.isZero()) || (!c1.isZero() && !b2.isZero())) return null;
    let a = a1.mul(a2), b = Q0, r = 0n;
    const c = a1.mul(c2).add(c1.mul(a2));
    if (!b1.isZero() && !b2.isZero()) {
      if (this.r !== o.r) return null;
      a = a.add(b1.mul(b2).mul(new Q(this.r)));
      b = a1.mul(b2).add(b1.mul(a2)); r = this.r;
    } else if (!b1.isZero()) { b = b1.mul(a2); r = this.r; } else if (!b2.isZero()) { b = a1.mul(b2); r = o.r; }
    return new X(a, b, r, c);
  }
  div(o) {
    if (o.isRational()) { if (o.a.isZero()) throw new MathError(); const inv = Q1.div(o.a); return new X(this.a.mul(inv), this.b.mul(inv), this.r, this.c.mul(inv)); }
    if (this.a.isZero() && this.b.isZero() && o.a.isZero() && o.b.isZero()) return new X(this.c.div(o.c));       // cπ / dπ
    if (this.c.isZero() && o.c.isZero()) {                                                                         // rationalise
      const den = o.a.mul(o.a).sub(o.b.mul(o.b).mul(new Q(o.r)));
      if (den.isZero()) throw new MathError();
      const conj = new X(o.a, o.b.neg(), o.r), top = this.mul(conj);
      return top ? top.div(new X(den)) : null;
    }
    return null;
  }
  powInt(n) {
    const neg = n < 0n; let e = neg ? -n : n;
    const limit = this.isRational() ? 2000n : 24n; if (e > limit) return null;
    let res = new X(Q1), base = this;
    while (e > 0n) { if (e & 1n) { res = res.mul(base); if (!res) return null; } e >>= 1n; if (e) { base = base.mul(base); if (!base) return null; } }
    return neg ? new X(Q1).div(res) : res;
  }
}

/* ---- N: exact-or-float values ---- */
export const N = (x, f) => ({ x, f: x ? x.toNumber() : f });
export const nQ = (n, d = 1) => N(X.q(Q.of(n, d)));
export const nF = (f) => { if (!Number.isFinite(f)) throw new MathError(); return { x: null, f }; };
export const nX = (x) => (x ? N(x) : null);
export const ZERO = nQ(0), ONE = nQ(1);
export const PI = N(new X(Q0, Q0, 0n, Q1));
export const E_CONST = { x: null, f: Math.E };
const fin = (v) => { if (!Number.isFinite(v)) throw new MathError(); return v; };
const bothX = (a, b) => a.x && b.x;
export const isExact = (a) => !!a.x;
export const isQ = (a) => !!a.x && a.x.isRational();
export const qOf = (a) => a.x.a;
export const isInt = (a) => isQ(a) && a.x.a.isInt();
export const isZero = (a) => (a.x ? a.x.isRational() && a.x.a.isZero() : a.f === 0);
export const neg = (a) => (a.x ? N(a.x.neg()) : { x: null, f: -a.f });
export const add = (a, b) => (bothX(a, b) ? (nX(a.x.add(b.x)) || nF(fin(a.f + b.f))) : nF(fin(a.f + b.f)));
export const sub = (a, b) => (bothX(a, b) ? (nX(a.x.sub(b.x)) || nF(fin(a.f - b.f))) : nF(fin(a.f - b.f)));
export const mul = (a, b) => (bothX(a, b) ? (nX(a.x.mul(b.x)) || nF(fin(a.f * b.f))) : nF(fin(a.f * b.f)));
export function div(a, b) {
  if (isZero(b)) throw new MathError();
  if (bothX(a, b)) { const r = a.x.div(b.x); if (r) return N(r); }
  return nF(fin(a.f / b.f));
}
export const cmp = (a, b) => (isQ(a) && isQ(b) ? a.x.a.cmp(b.x.a) : a.f < b.f ? -1 : a.f > b.f ? 1 : 0);
export const sign = (a) => (a.x ? (a.f > 0 ? 1 : a.f < 0 ? -1 : 0) : Math.sign(a.f));
export const abs = (a) => (sign(a) < 0 ? neg(a) : a);
export const fromBig = (n) => N(X.q(new Q(n)));

/** decimal literal → exact rational */
export function parseDecimal(str) {
  const m = /^(\d*)\.?(\d*)$/.exec(str); if (!m || (!m[1] && !m[2])) throw new MathError("Syntax ERROR");
  const frac = m[2] || "", n = BigInt((m[1] || "0") + frac);
  return N(X.q(new Q(n, bpow(10n, BigInt(frac.length)))));
}

export function sqrt(a) {
  if (sign(a) < 0) throw new MathError();
  if (isQ(a)) {
    const q = a.x.a, sf = sqfree(q.n * q.d);
    if (sf) { const [k, s] = sf; return N(s === 1n ? X.q(new Q(k, q.d)) : new X(Q0, new Q(k, q.d), s)); }
  }
  return nF(Math.sqrt(a.f));
}
export function root(a, n) {                          // n-th root, n integer ≥ 2
  if (n === 2) return sqrt(a);
  if (isQ(a)) {
    const q = a.x.a, neg_ = q.n < 0n;
    if (neg_ && n % 2 === 0) throw new MathError();
    const rn = iroot(babs(q.n), n), rd = iroot(q.d, n);
    if (rn !== null && rd !== null) return N(X.q(new Q(neg_ ? -rn : rn, rd)));
  }
  if (a.f < 0) { if (n % 2 === 0) throw new MathError(); return nF(-Math.pow(-a.f, 1 / n)); }
  return nF(Math.pow(a.f, 1 / n));
}
export function pow(a, b) {
  if (isZero(a) && isZero(b)) throw new MathError();
  if (isInt(b) && a.x) {
    const e = qOf(b).n, r = a.x.powInt(e);
    if (r) return N(r);
  }
  if (isQ(b) && !isInt(b) && a.x) {                    // rational exponent p/q
    const q = qOf(b), p = Number(q.n), d = Number(q.d);
    if (Math.abs(p) < 60 && d >= 2 && d <= 12) { const r = root(a, d); if (r.x) return pow(r, nQ(p)); }
  }
  if (a.f < 0 && !isInt(b)) {
    if (isQ(b) && qOf(b).d % 2n === 1n) { const v = Math.pow(-a.f, b.f); return nF(fin((qOf(b).n % 2n === 0n ? 1 : -1) * v)); }
    throw new MathError();
  }
  if (isZero(a) && b.f < 0) throw new MathError();
  return nF(fin(Math.pow(a.f, b.f)));
}
export function factorial(a) {
  if (!isInt(a) || sign(a) < 0) throw new MathError();
  const n = Number(qOf(a).n); if (n > 69) throw new MathError();
  let r = 1n; for (let i = 2n; i <= BigInt(n); i++) r *= i; return fromBig(r);
}
export function nPr(a, b) { return permComb(a, b, false); }
export function nCr(a, b) { return permComb(a, b, true); }
function permComb(a, b, comb) {
  if (!isInt(a) || !isInt(b) || sign(a) < 0 || sign(b) < 0) throw new MathError();
  const n = qOf(a).n, r = qOf(b).n; if (r > n || n > 9999999999n) throw new MathError();
  let p = 1n, k = comb && r > n - r ? n - r : r;
  for (let i = 0n; i < k; i++) { p = p * (n - i); if (comb) p = p / (i + 1n); }
  if (!comb) return fromBig(p);
  return fromBig(p);
}

/* ---------------- angles & trig ---------------- */
export const toRad = (a, unit) => (unit === "deg" ? mul(a, div(PI, nQ(180))) : unit === "gra" ? mul(a, div(PI, nQ(200))) : a);
export const fromRad = (a, unit) => (unit === "deg" ? mul(a, div(nQ(180), PI)) : unit === "gra" ? mul(a, div(nQ(200), PI)) : a);
const SIN = { 0: nQ(0), 30: nQ(1, 2), 45: N(new X(Q0, Q.of(1, 2), 2n)), 60: N(new X(Q0, Q.of(1, 2), 3n)), 90: nQ(1) };
const COS = { 0: nQ(1), 30: SIN[60], 45: SIN[45], 60: nQ(1, 2), 90: nQ(0) };
const TAN = { 0: nQ(0), 30: N(new X(Q0, Q.of(1, 3), 3n)), 45: nQ(1), 60: N(new X(Q0, Q1, 3n)), 90: null };
/** angle as exact degrees (rational) if the value is an exact multiple of π or a rational in DEG mode */
function exactDegrees(a, unit) {
  if (!a.x) return null;
  if (unit === "deg") return a.x.isRational() ? a.x.a : null;
  if (unit === "rad") return a.x.a.isZero() && a.x.b.isZero() ? a.x.c.mul(Q.of(180)) : (a.x.isRational() && a.x.a.isZero() ? Q0 : null);
  if (unit === "gra") return a.x.isRational() ? a.x.a.mul(Q.of(9, 10)) : null;
  return null;
}
function refAngle(deg) {                              // → [reducedDegreesInt, quadrantInfo] if a "nice" angle
  if (!deg.isInt()) return null;
  let t = Number(((deg.n % 360n) + 360n) % 360n);
  if (!(t % 30 === 0 || t % 45 === 0)) return null;
  return t;
}
export function trig(name, a, unit) {
  const deg = exactDegrees(a, unit), t = deg ? refAngle(deg) : null;
  if (t !== null) {                                    // nice angle (multiple of 30° or 45°) → exact value
    const ref = t <= 90 ? t : t <= 180 ? 180 - t : t <= 270 ? t - 180 : 360 - t;
    if (name === "sin") return t > 180 ? neg(SIN[ref]) : SIN[ref];
    if (name === "cos") return t > 90 && t < 270 ? neg(COS[ref]) : COS[ref];
    if (t === 90 || t === 270) throw new MathError();
    const r2 = t % 180, a0 = r2 <= 90 ? r2 : 180 - r2;
    return r2 > 90 ? neg(TAN[a0]) : TAN[a0];
  }
  const rr = toRad(a, unit).f;
  if (name === "sin") return nF(clean(Math.sin(rr)));
  if (name === "cos") return nF(clean(Math.cos(rr)));
  const c = Math.cos(rr); if (Math.abs(c) < 1e-15) throw new MathError();
  return nF(Math.sin(rr) / c);
}
const clean = (v) => (Math.abs(v) < 1e-15 ? 0 : v);
const SPECIAL = [
  ["sin", nQ(0), 0], ["sin", nQ(1, 2), 30], ["sin", SIN[45], 45], ["sin", SIN[60], 60], ["sin", nQ(1), 90],
  ["cos", nQ(1), 0], ["cos", SIN[60], 30], ["cos", SIN[45], 45], ["cos", nQ(1, 2), 60], ["cos", nQ(0), 90],
  ["tan", nQ(0), 0], ["tan", TAN[30], 30], ["tan", nQ(1), 45], ["tan", TAN[60], 60],
];
export function invTrig(name, a, unit) {
  if ((name === "asin" || name === "acos") && Math.abs(a.f) > 1) throw new MathError();
  const key = name.slice(1);
  let deg = null;
  for (const [n, v, d] of SPECIAL) {
    if (n !== key) continue;
    if (key === "sin" && a.x && v.x && a.x.add(v.x.neg()) && isExactEq(a, v)) deg = d;
    else if (isExactEq(a, v)) deg = d;
    else if (key !== "tan" && isExactEq(a, neg(v)) && key === "sin") deg = -d;
    else if (key === "cos" && isExactEq(a, neg(v))) deg = 180 - d;
    else if (key === "tan" && isExactEq(a, neg(v))) deg = -d;
  }
  if (deg !== null) {
    if (unit === "deg") return nQ(deg);
    if (unit === "gra") return N(X.q(Q.of(deg * 10, 9)));
    return N(new X(Q0, Q0, 0n, Q.of(deg, 180)));
  }
  const rad = key === "sin" ? Math.asin(a.f) : key === "cos" ? Math.acos(a.f) : Math.atan(a.f);
  return nF(unit === "deg" ? (rad * 180) / Math.PI : unit === "gra" ? (rad * 200) / Math.PI : rad);
}
function isExactEq(a, b) {
  if (a.x && b.x) { const d = a.x.sub(b.x); return !!d && d.isRational() && d.a.isZero(); }
  return Math.abs(a.f - b.f) < 1e-14;
}
export function hyper(name, a) {
  if (isZero(a) && name !== "cosh") return nQ(0);
  if (isZero(a) && name === "cosh") return nQ(1);
  const v = { sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh, asinh: Math.asinh, acosh: Math.acosh, atanh: Math.atanh }[name](a.f);
  if (Number.isNaN(v)) throw new MathError(); return nF(v);
}
export function ln(a) {
  if (a.f <= 0) throw new MathError();
  if (a.x && isExactEq(a, ONE)) return nQ(0);
  if (!a.x && Math.abs(a.f - Math.E) < 1e-13) return nQ(1);
  return nF(Math.log(a.f));
}
export function logBase(b, a) {
  if (a.f <= 0 || b.f <= 0 || b.f === 1) throw new MathError();
  if (isQ(a) && isQ(b)) {                              // log_b(a) exact when a = b^k
    const A = qOf(a), B = qOf(b);
    for (let k = -30; k <= 30; k++) { if (k === 0) continue; const p = B.n === 1n && B.d === 1n ? null : powQ(B, k); if (p && p.eq(A)) return nQ(k); }
    if (A.eq(Q1)) return nQ(0);
  }
  return nF(Math.log(a.f) / Math.log(b.f));
}
const powQ = (q, k) => { try { const r = new X(q).powInt(BigInt(k)); return r ? r.a : null; } catch { return null; } };
export const log10 = (a) => logBase(nQ(10), a);
export function exp10(a) { if (isInt(a) && Math.abs(Number(qOf(a).n)) <= 300) return pow(nQ(10), a); return nF(fin(Math.pow(10, a.f))); }
export function expE(a) { if (isZero(a)) return nQ(1); return nF(fin(Math.exp(a.f))); }

/* ---------------- display ---------------- */
const digitsOf = (n) => babs(n).toString().length;
export const trimZeros = (s) => (s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s);
export function floatParts(v, setup = {}) {
  const fmt = setup.fmt || "norm1", n = setup.n ?? 0;
  if (v === 0) return { m: "0", e: 0, sci: false };
  const a = Math.abs(v);
  if (fmt === "fix") { const s = v.toFixed(n); return { m: s, e: 0, sci: false }; }
  if (fmt === "sci") { const d = n === 0 ? 10 : n; const [m, e] = v.toExponential(d - 1).split("e"); return { m: m, e: parseInt(e, 10), sci: true }; }
  const lo = fmt === "norm2" ? 1e-9 : 1e-2;
  if (a >= 1e10 || a < lo) { const [m, e] = v.toExponential(9).split("e"); return { m: trimZeros(m), e: parseInt(e, 10), sci: true }; }
  return { m: trimZeros(v.toPrecision(10)), e: 0, sci: false };
}
export function engParts(v, shift = 0) {
  if (v === 0) return { m: "0", e: 0, sci: false };
  const e = Math.floor(Math.log10(Math.abs(v)) + 1e-12), ee = Math.floor(e / 3) * 3 + shift * 3, m = v / Math.pow(10, ee);
  return { m: trimZeros(m.toPrecision(10)), e: ee, sci: true };
}
export function dms(v) {
  const sg = v < 0 ? -1 : 1; let a = Math.abs(v), d = Math.floor(a + 1e-12); let mm = (a - d) * 60, m = Math.floor(mm + 1e-9), s = (mm - m) * 60;
  s = Math.round(s * 1000) / 1000; if (s >= 60) { s -= 60; m += 1; } if (m >= 60) { m -= 60; d += 1; }
  return { sg, d, m, s: trimZeros(s.toFixed(3)) };
}
/** exact value → { sign, num: [{k:'int'|'surd'|'pi', coef, r}], den } for natural display */
export function exactTerms(x) {
  const D = [x.a.d, x.b.d, x.c.d].reduce((l, d) => (l * d) / bgcd(l, d), 1n);
  const A = x.a.n * (D / x.a.d), B = x.b.n * (D / x.b.d), C = x.c.n * (D / x.c.d);
  const terms = []; if (A !== 0n) terms.push({ k: "int", coef: A }); if (B !== 0n) terms.push({ k: "surd", coef: B, r: x.r }); if (C !== 0n) terms.push({ k: "pi", coef: C });
  if (!terms.length) terms.push({ k: "int", coef: 0n });
  let sign = 1;
  if (terms.every((t) => t.coef < 0n)) { sign = -1; terms.forEach((t) => { t.coef = -t.coef; }); }
  return { sign, terms, den: D };
}
export function exactDigits(x) { const t = exactTerms(x); return t.terms.reduce((s, q) => s + digitsOf(q.coef), 0) + digitsOf(t.den); }
export const bigDigits = digitsOf;
