/**
 * Tokens → AST → value. Follows Casio ES precedence:
 *   functions/templates > postfix (!, %, °, ^) > unary minus > nPr/nCr > implicit multiplication > × ÷ > + −
 * so 1÷2π means 1÷(2π) and −2² = −4.
 */
import * as M from "./num.js";
import { MathError } from "./num.js";
import { tokenize } from "./tree.js";

export class SyntaxErr extends Error { constructor(tok) { super("Syntax ERROR"); this.kind = "syntax"; this.tok = tok || null; } }
export { MathError };

const START = new Set(["num", "const", "var", "lp", "fn", "node"]);
const FNS = new Set(["sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "log", "ln", "Pol", "Rec", "Int", "Intg", "Abs", "RanInt", "Conjg", "arg", "Re", "Im"]);

/* ------------------------------------------------------------------ parser */
class Parser {
  constructor(toks, rowRef) { this.t = toks; this.p = 0; this.rowRef = rowRef; }
  peek(o = 0) { return this.t[this.p + o]; }
  next() { return this.t[this.p++]; }
  err(tok) { return new SyntaxErr(tok || this.peek() || this.t[this.t.length - 1]); }
  top() {
    if (!this.t.length) throw new SyntaxErr({ row: this.rowRef, i: 0 });
    const e = this.expr(); if (this.p < this.t.length) throw this.err(); return e;
  }
  expr() {
    let l = this.term();
    while (this.peek() && this.peek().t === "op" && (this.peek().v === "+" || this.peek().v === "-")) { const op = this.next().v; l = { t: "bin", op, a: l, b: this.term() }; }
    return l;
  }
  term() {
    let l = this.implicit();
    while (this.peek() && this.peek().t === "op" && (this.peek().v === "×" || this.peek().v === "÷")) { const op = this.next().v; l = { t: "bin", op, a: l, b: this.implicit() }; }
    return l;
  }
  implicit() {
    let l = this.unary();
    while (this.peek() && START.has(this.peek().t)) l = { t: "bin", op: "×", a: l, b: this.unary(), implicit: true };
    return l;
  }
  unary() {
    const k = this.peek();
    if (k && k.t === "op" && k.v === "-") { this.next(); return { t: "neg", a: this.unary() }; }
    if (k && k.t === "op" && k.v === "+") { this.next(); return this.unary(); }
    return this.perm();
  }
  perm() {
    let l = this.postfix();
    while (this.peek() && this.peek().t === "infix") {
      const op = this.next().v; const r = this.postfix(); l = { t: op === "∠" ? "polar" : op === "nPr" ? "nPr" : "nCr", a: l, b: r };
    }
    return l;
  }
  postfix() {
    let a = this.primary();
    for (;;) {
      const k = this.peek(); if (!k) break;
      if (k.t === "pow") { this.next(); a = { t: "pow", a, b: parseRow(k.node.e) }; continue; }
      if (k.t === "post") {
        this.next();
        if (k.v === "!") a = { t: "fact", a };
        else if (k.v === "%") a = { t: "pct", a };
        else if (k.v === "°") {
          let m = null, s = null;
          if (this.peek() && this.peek().t === "num" && this.peek(1) && this.peek(1).t === "post" && this.peek(1).v === "′") { m = this.parseNum(this.next()); this.next(); }
          if (m && this.peek() && this.peek().t === "num" && this.peek(1) && this.peek(1).t === "post" && this.peek(1).v === "″") { s = this.parseNum(this.next()); this.next(); }
          a = { t: "deg", a, m, s };
        } else if (k.v === "r") a = { t: "radm", a };
        else if (k.v === "g") a = { t: "gram", a };
        else throw this.err(k);
        continue;
      }
      break;
    }
    return a;
  }
  parseNum(tok) { return this.numNode(tok); }
  numNode(tok) {
    let v;
    try { v = tok.implicitOne ? M.nQ(1) : M.parseDecimal(tok.v); } catch { throw this.err(tok); }
    const n = { t: "num", v };
    if (tok.exp) return { t: "bin", op: "×", a: n, b: { t: "pow", a: { t: "num", v: M.nQ(10) }, b: parseRow(tok.exp.e) } };
    return n;
  }
  args() {
    const out = [];
    if (!(this.peek() && this.peek().t === "lp")) return [this.unary()];
    this.next();
    if (this.peek() && this.peek().t === "rp") throw this.err();
    for (;;) {
      out.push(this.expr()); const k = this.peek();
      if (k && k.t === "sep") { this.next(); continue; }
      if (k && k.t === "rp") { this.next(); break; }
      if (!k) break;                                    // missing ")" at the end is fine
      throw this.err(k);
    }
    return out;
  }
  primary() {
    const k = this.next(); if (!k) throw this.err(this.t[this.t.length - 1]);
    switch (k.t) {
      case "num": return this.numNode(k);
      case "const": return { t: "const", name: k.v, tok: k };
      case "var": return { t: "var", name: k.v };
      case "lp": {
        if (this.peek() && this.peek().t === "rp") throw this.err();
        const e = this.expr(); const c = this.peek();
        if (c && c.t === "rp") this.next(); else if (c) throw this.err(c);
        return { t: "group", a: e };
      }
      case "fn": { if (!FNS.has(k.v)) throw this.err(k); return { t: "call", name: k.v, args: this.args(), tok: k }; }
      case "node": return this.template(k.node, k);
      default: throw this.err(k);
    }
  }
  template(n, tok) {
    const R = (r) => parseRow(r);
    switch (n.k) {
      case "frac": return { t: "bin", op: "÷", a: R(n.n), b: R(n.d), frac: true };
      case "sqrt": return { t: "sqrt", a: R(n.r) };
      case "root": return { t: "root", n: R(n.n), a: R(n.r) };
      case "abs": return { t: "call", name: "Abs", args: [R(n.r)] };
      case "logb": return { t: "logb", b: R(n.b), a: R(n.a) };
      case "int": return { t: "int", lo: R(n.lo), hi: R(n.hi), f: R(n.f) };
      case "sum": return { t: "sum", lo: R(n.lo), hi: R(n.hi), f: R(n.f) };
      case "diff": return { t: "diff", f: R(n.f), at: R(n.at) };
      case "mixed": return { t: "bin", op: "+", a: R(n.w), b: { t: "bin", op: "÷", a: R(n.n), b: R(n.d), frac: true } };
      default: throw new SyntaxErr(tok);
    }
  }
}
export function parseRow(row) { return new Parser(tokenize(row), row).top(); }
/** "lhs = rhs" for SOLVE */
export function parseEquation(row) {
  const toks = tokenize(row), at = toks.findIndex((t) => t.t === "eq");
  if (at < 0) return null;
  return { lhs: new Parser(toks.slice(0, at), row).top(), rhs: new Parser(toks.slice(at + 1), row).top() };
}
export const hasEquals = (row) => row.some((n) => n.k === "c" && n.v === "=");
/** variables used in an expression (for CALC) */
export function varsIn(ast, set = new Set()) {
  if (!ast || typeof ast !== "object") return set;
  if (ast.t === "var") set.add(ast.name);
  for (const k of ["a", "b", "n", "lo", "hi", "f", "at", "m", "s"]) if (ast[k]) varsIn(ast[k], set);
  if (ast.args) ast.args.forEach((x) => varsIn(x, set));
  return set;
}

/* -------------------------------------------------------------- complex ops */
export const isC = (v) => v && v.re !== undefined;
const toC = (v) => (isC(v) ? v : { re: v, im: M.ZERO });
const simp = (c) => (M.isZero(c.im) ? c.re : c);
export const cAdd = (a, b) => (!isC(a) && !isC(b) ? M.add(a, b) : (a = toC(a), b = toC(b), simp({ re: M.add(a.re, b.re), im: M.add(a.im, b.im) })));
export const cSub = (a, b) => (!isC(a) && !isC(b) ? M.sub(a, b) : (a = toC(a), b = toC(b), simp({ re: M.sub(a.re, b.re), im: M.sub(a.im, b.im) })));
export const cMul = (a, b) => {
  if (!isC(a) && !isC(b)) return M.mul(a, b);
  a = toC(a); b = toC(b);
  return simp({ re: M.sub(M.mul(a.re, b.re), M.mul(a.im, b.im)), im: M.add(M.mul(a.re, b.im), M.mul(a.im, b.re)) });
};
export const cDiv = (a, b) => {
  if (!isC(a) && !isC(b)) return M.div(a, b);
  a = toC(a); b = toC(b);
  const den = M.add(M.mul(b.re, b.re), M.mul(b.im, b.im)); if (M.isZero(den)) throw new MathError();
  return simp({ re: M.div(M.add(M.mul(a.re, b.re), M.mul(a.im, b.im)), den), im: M.div(M.sub(M.mul(a.im, b.re), M.mul(a.re, b.im)), den) });
};
export const cNeg = (a) => (isC(a) ? { re: M.neg(a.re), im: M.neg(a.im) } : M.neg(a));
export const conj = (a) => (isC(a) ? { re: a.re, im: M.neg(a.im) } : a);
export const cAbs = (a) => (isC(a) ? M.sqrt(M.add(M.mul(a.re, a.re), M.mul(a.im, a.im))) : M.abs(a));
function atan2N(y, x, unit) {
  if (M.isZero(x) && M.isZero(y)) throw new MathError();
  if (M.isZero(x)) return angleConst(M.sign(y) > 0 ? 90 : -90, unit);
  let a = M.invTrig("atan", M.div(y, x), unit);
  if (M.sign(x) < 0) a = M.add(a, angleConst(M.sign(y) >= 0 ? 180 : -180, unit));
  return a;
}
const angleConst = (deg, unit) => (unit === "deg" ? M.nQ(deg) : unit === "gra" ? M.nQ((deg * 10) / 9) : M.mul(M.PI, M.nQ(deg, 180)));
export const cArg = (a, unit) => { const c = toC(a); return atan2N(c.im, c.re, unit); };
function cFloat(c) { return { re: c.re.f, im: c.im.f }; }
const cFromF = (re, im) => simp({ re: M.nF(re), im: M.nF(im) });
export function cPow(a, b, cx) {
  if (!isC(a) && !isC(b)) {
    if (M.sign(a) < 0 && cx && !(M.isQ(b) && M.qOf(b).d % 2n === 1n)) return cPowF(toC(a), b);
    return M.pow(a, b);
  }
  if (!isC(b) && M.isInt(b)) {
    const e = M.qOf(b).n; let res = M.ONE, base = toC(a), n = e < 0n ? -e : e; if (n > 200n) return cPowF(toC(a), b);
    while (n > 0n) { if (n & 1n) res = cMul(res, base); n >>= 1n; if (n) base = cMul(base, base); }
    return e < 0n ? cDiv(M.ONE, res) : res;
  }
  return cPowF(toC(a), b);
}
function cPowF(a, b) {                                  // z^w through polar form (floats)
  const x = cFloat(a), w = isC(b) ? cFloat(b) : { re: b.f, im: 0 };
  const r = Math.hypot(x.re, x.im); if (r === 0) throw new MathError();
  const th = Math.atan2(x.im, x.re), lr = Math.log(r), er = Math.exp(w.re * lr - w.im * th), ang = w.im * lr + w.re * th;
  return cFromF(er * Math.cos(ang), er * Math.sin(ang));
}
export function cSqrt(a, cx) {
  if (!isC(a)) { if (M.sign(a) >= 0) return M.sqrt(a); if (!cx) throw new MathError(); return { re: M.ZERO, im: M.sqrt(M.neg(a)) }; }
  const x = cFloat(a), r = Math.hypot(x.re, x.im), re = Math.sqrt((r + x.re) / 2), im = Math.sign(x.im || 1) * Math.sqrt((r - x.re) / 2);
  return cFromF(re, im);
}

/* -------------------------------------------------------------- evaluation */
let budget = 0;
export function evalAst(ast, ctx) {
  if (--budget < 0) throw new MathError();
  const E = (n) => evalAst(n, ctx), unit = ctx.unit;
  switch (ast.t) {
    case "num": return ast.v;
    case "group": return E(ast.a);
    case "neg": return cNeg(E(ast.a));
    case "const": {
      const n = ast.name;
      if (n === "π") return M.PI; if (n === "e") return M.E_CONST;
      if (n === "Ans") return ctx.ans || M.ZERO;
      if (n === "Ran#") return M.parseDecimal(String(Math.floor(Math.random() * 1000) / 1000 || 0));
      if (n === "i") { if (!ctx.cx) throw new SyntaxErr(ast.tok); return { re: M.ZERO, im: M.ONE }; }
      throw new SyntaxErr(ast.tok);
    }
    case "var": return ctx.vars[ast.name] || M.ZERO;
    case "bin": {
      const a = E(ast.a), b = E(ast.b);
      return ast.op === "+" ? cAdd(a, b) : ast.op === "-" ? cSub(a, b) : ast.op === "×" ? cMul(a, b) : cDiv(a, b);
    }
    case "pow": return cPow(E(ast.a), E(ast.b), ctx.cx);
    case "sqrt": return cSqrt(E(ast.a), ctx.cx);
    case "root": { const n = E(ast.n), a = E(ast.a); if (isC(n) || isC(a) || !M.isInt(n) || M.sign(n) <= 0) { if (ctx.cx) return cPow(a, cDiv(M.ONE, n), true); throw new MathError(); } return M.root(a, Number(M.qOf(n).n)); }
    case "fact": return real(E(ast.a), M.factorial);
    case "pct": return cDiv(E(ast.a), M.nQ(100));
    case "nPr": return M.nPr(real(E(ast.a)), real(E(ast.b)));
    case "nCr": return M.nCr(real(E(ast.a)), real(E(ast.b)));
    case "polar": { const r = E(ast.a), th = real(E(ast.b)), t = M.toRad(th, unit); return cFromF(r.f * Math.cos(t.f), r.f * Math.sin(t.f)); }
    case "deg": {
      let v = real(E(ast.a));
      if (ast.m) v = M.add(v, M.div(real(E(ast.m)), M.nQ(60)));
      if (ast.s) v = M.add(v, M.div(real(E(ast.s)), M.nQ(3600)));
      return unit === "deg" ? v : unit === "rad" ? M.mul(v, M.div(M.PI, M.nQ(180))) : M.mul(v, M.nQ(10, 9));
    }
    case "radm": { const v = real(E(ast.a)); return unit === "rad" ? v : unit === "deg" ? M.mul(v, M.div(M.nQ(180), M.PI)) : M.mul(v, M.div(M.nQ(200), M.PI)); }
    case "gram": { const v = real(E(ast.a)); return unit === "gra" ? v : unit === "deg" ? M.mul(v, M.nQ(9, 10)) : M.mul(v, M.div(M.PI, M.nQ(200))); }
    case "logb": return M.logBase(real(E(ast.b)), real(E(ast.a)));
    case "call": return call(ast, ctx);
    case "int": return integral(ast, ctx);
    case "sum": return summation(ast, ctx);
    case "diff": return derivative(ast, ctx);
    default: throw new SyntaxErr();
  }
}
function real(v, f) {
  if (isC(v)) throw new MathError();
  return f ? f(v) : v;
}
function call(ast, ctx) {
  const { name } = ast, unit = ctx.unit, a = ast.args.map((x) => evalAst(x, ctx)), a0 = a[0];
  const need = (n) => { if (a.length !== n) throw new SyntaxErr(ast.tok); };
  switch (name) {
    case "Abs": need(1); return cAbs(a0);
    case "Conjg": need(1); return conj(a0);
    case "Re": need(1); return isC(a0) ? a0.re : a0;
    case "Im": need(1); return isC(a0) ? a0.im : M.ZERO;
    case "arg": need(1); return cArg(a0, unit);
    case "Int": need(1); { const v = real(a0); return M.isInt(v) ? v : M.nF(Math.trunc(v.f)); }
    case "Intg": need(1); { const v = real(a0); return M.isInt(v) ? v : M.nF(Math.floor(v.f)); }
    case "RanInt": { need(2); const lo = Math.ceil(real(a0).f), hi = Math.floor(real(a[1]).f); if (hi < lo) throw new MathError(); return M.nQ(lo + Math.floor(Math.random() * (hi - lo + 1))); }
    case "Pol": {
      need(2); const x = real(a0), y = real(a[1]);
      const r = M.sqrt(M.add(M.mul(x, x), M.mul(y, y))), th = atan2N(y, x, unit);
      ctx.vars.X = r; ctx.vars.Y = th; ctx.multi = [{ label: "r", val: r }, { label: "θ", val: th }]; return r;
    }
    case "Rec": {
      need(2); const r = real(a0), th = real(a[1]), x = M.mul(r, M.trig("cos", th, unit)), y = M.mul(r, M.trig("sin", th, unit));
      ctx.vars.X = x; ctx.vars.Y = y; ctx.multi = [{ label: "x", val: x }, { label: "y", val: y }]; return x;
    }
    default: break;
  }
  need(1);
  if (isC(a0)) return complexFn(name, a0, ctx);
  switch (name) {
    case "sin": case "cos": case "tan": return M.trig(name, a0, unit);
    case "asin": case "acos": case "atan": return M.invTrig(name, a0, unit);
    case "sinh": case "cosh": case "tanh": case "asinh": case "acosh": case "atanh": return M.hyper(name, a0);
    case "log": if (M.sign(a0) < 0 && ctx.cx) return cDiv(complexFn("ln", a0, ctx), M.nF(Math.LN10)); return M.log10(a0);
    case "ln": if (M.sign(a0) < 0 && ctx.cx) return complexFn("ln", a0, ctx); return M.ln(a0);
    default: throw new SyntaxErr(ast.tok);
  }
}
function complexFn(name, z, ctx) {
  const x = cFloat(z);
  switch (name) {
    case "ln": return cFromF(Math.log(Math.hypot(x.re, x.im)), Math.atan2(x.im, x.re));
    case "log": return cDiv(complexFn("ln", z, ctx), M.nF(Math.LN10));
    case "sin": return cFromF(Math.sin(x.re) * Math.cosh(x.im), Math.cos(x.re) * Math.sinh(x.im));
    case "cos": return cFromF(Math.cos(x.re) * Math.cosh(x.im), -Math.sin(x.re) * Math.sinh(x.im));
    default: throw new MathError();
  }
}

/* ------------------------------------------------------ numeric templates */
const fAt = (ast, ctx, x) => { const c = { ...ctx, vars: { ...ctx.vars, X: M.nF(x) } }; const v = evalAst(ast, c); if (isC(v)) throw new MathError(); return v.f; };
const snap = (v) => { const r = Math.round(v); return Math.abs(v - r) < 1e-9 * Math.max(1, Math.abs(v)) ? M.nQ(r) : M.nF(v); };
const GK_X = [0.991455371120813, 0.949107912342759, 0.864864423359769, 0.741531185599394, 0.586087235467691, 0.405845151377397, 0.207784955007898, 0];
const GK_W = [0.022935322010529, 0.063092092629979, 0.104790010322250, 0.140653259715525, 0.169004726639267, 0.190350578064785, 0.204432940075298, 0.209482141084728];
const G_W = [0.129484966168870, 0.279705391489277, 0.381830050505119, 0.417959183673469];
function gk(f, a, b) {
  const c = (a + b) / 2, h = (b - a) / 2; let k = 0, g = 0;
  for (let i = 0; i < 8; i++) {
    const xs = i === 7 ? [c] : [c - h * GK_X[i], c + h * GK_X[i]];
    for (const x of xs) { const y = f(x); k += GK_W[i] * y; if (i % 2 === 1) g += G_W[(i - 1) / 2] * y; }
  }
  return { k: k * h, err: Math.abs((k - g) * h) };
}
function adaptive(f, a, b, tol, depth) {
  const { k, err } = gk(f, a, b);
  if (depth <= 0 || err < tol) return k;
  const m = (a + b) / 2; return adaptive(f, a, m, tol / 2, depth - 1) + adaptive(f, m, b, tol / 2, depth - 1);
}
function integral(ast, ctx) {
  const lo = evalAst(ast.lo, ctx).f, hi = evalAst(ast.hi, ctx).f; if (lo === hi) return M.ZERO;
  const f = (x) => { const v = fAt(ast.f, ctx, x); if (!Number.isFinite(v)) throw new MathError(); return v; };
  budget = Math.max(budget, 400000);
  return snapIntegral(adaptive(f, lo, hi, 1e-11 * Math.max(1, Math.abs(hi - lo)), 18));
}
const snapIntegral = (v) => { const r = Math.round(v); return Math.abs(v - r) < 1e-10 ? M.nQ(r) : M.nF(v); };
function derivative(ast, ctx) {
  const x = evalAst(ast.at, ctx).f, h = 1e-3 * Math.max(1, Math.abs(x));
  const f = (t) => fAt(ast.f, ctx, t);
  const d = (8 * (f(x + h) - f(x - h)) - (f(x + 2 * h) - f(x - 2 * h))) / (12 * h);
  if (!Number.isFinite(d)) throw new MathError(); return snap(d);
}
function summation(ast, ctx) {
  const lo = evalAst(ast.lo, ctx), hi = evalAst(ast.hi, ctx);
  if (!M.isInt(lo) || !M.isInt(hi)) throw new MathError();
  const a = Number(M.qOf(lo).n), b = Number(M.qOf(hi).n); if (b - a > 200000) throw new MathError();
  let sum = M.ZERO; const c = { ...ctx, vars: { ...ctx.vars } };
  for (let k = a; k <= b; k++) { c.vars.X = M.nQ(k); sum = cAdd(sum, evalAst(ast.f, c)); }
  return sum;
}
export function findRoot(fx, guess = 0) {
  const tryNewton = (x0) => {
    let x = x0;
    for (let i = 0; i < 80; i++) {
      const y = fx(x); if (!Number.isFinite(y)) return null; if (Math.abs(y) < 1e-13) return x;
      const h = 1e-6 * Math.max(1, Math.abs(x)), d = (fx(x + h) - fx(x - h)) / (2 * h); if (!d || !Number.isFinite(d)) return null;
      const nx = x - y / d; if (Math.abs(nx - x) < 1e-14 * Math.max(1, Math.abs(x))) return Math.abs(fx(nx)) < 1e-8 ? nx : null; x = nx;
    }
    return Math.abs(fx(x)) < 1e-8 ? x : null;
  };
  let r = tryNewton(guess); if (r !== null) return r;
  for (const g of [1, -1, 10, -10, 100, -100, 0.1, -0.1]) { r = tryNewton(g); if (r !== null) return r; }
  let prev = null;                                      // bracket scan
  for (let x = -1000; x <= 1000; x += 0.5) {
    const y = fx(x); if (!Number.isFinite(y)) { prev = null; continue; }
    if (prev && prev.y * y <= 0) { let a = prev.x, b = x; for (let i = 0; i < 200; i++) { const m = (a + b) / 2; if (fx(a) * fx(m) <= 0) b = m; else a = m; } return (a + b) / 2; }
    prev = { x, y };
  }
  return null;
}

/* ---------------------------------------------------------------- public API */
export function evaluateRow(row, ctx) {
  budget = 200000; ctx.multi = null;
  const ast = parseRow(row);
  return { value: evalAst(ast, ctx), ast };
}
export function evaluateAst(ast, ctx) { budget = 200000; ctx.multi = null; return evalAst(ast, ctx); }
export function makeF(ast, ctx) { return (x) => fAt(ast, ctx, x); }
