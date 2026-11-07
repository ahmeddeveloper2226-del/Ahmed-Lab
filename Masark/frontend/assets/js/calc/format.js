/** Turns calculator values into display rows (the same tree the editor renders), Casio-style. */
import * as M from "./num.js";
import { chr, template, link } from "./tree.js";
import { isC } from "./parser.js";

const digitsRow = (str) => [...str].map((c) => chr(c === "-" ? "-" : c));
const big = (n) => digitsRow(n.toString());
function sciRow(m, e) {
  const row = digitsRow(m); row.push(chr("×"), chr("1"), chr("0"));
  const pw = template("pow"); pw.e.push(...digitsRow(String(e))); row.push(pw); return row;
}
export function floatRow(v, setup, eng = 0) {
  const p = eng ? M.engParts(v, eng) : M.floatParts(v, setup);
  return p.sci ? sciRow(p.m, p.e) : digitsRow(p.m);
}
const withSign = (neg, row) => (neg ? [chr("-"), ...row] : row);

function termRow(t, first) {
  const neg = t.coef < 0n, c = neg ? -t.coef : t.coef, out = [];
  if (!first) out.push(chr(neg ? "-" : "+")); else if (neg) out.push(chr("-"));
  if (t.k === "int") out.push(...big(c));
  else if (t.k === "surd") { if (c !== 1n) out.push(...big(c)); const sq = template("sqrt"); sq.r.push(...big(t.r)); out.push(sq); }
  else { if (c !== 1n) out.push(...big(c)); out.push(chr("π")); }
  return out;
}
export function exactRow(x) {
  const { sign, terms, den } = M.exactTerms(x);
  const num = []; terms.forEach((t, i) => num.push(...termRow(t, i === 0)));
  if (den === 1n) return withSign(sign < 0, num);
  const f = template("frac"); f.n.push(...num); f.d.push(...big(den));
  return withSign(sign < 0, [f]);
}
const wantExact = (v, setup, view) => v.x && !view.dec && (setup.fmt === "norm1" || setup.fmt === "norm2") && M.exactDigits(v.x) <= 10;

/** one real number → row */
export function numRow(v, setup, view = {}) {
  if (view.dms && !isC(v)) return dmsRow(v.f);
  if (view.mixed && wantExact(v, setup, view) && v.x.isRational() && !v.x.a.isInt() && M.bigDigits(v.x.a.n) + M.bigDigits(v.x.a.d) <= 10) {
    const q = v.x.a, w = q.n / q.d, rem = (q.n < 0n ? -q.n : q.n) % q.d;
    if (w !== 0n) { const m = template("mixed"); m.w.push(...big(w < 0n ? -w : w)); m.n.push(...big(rem)); m.d.push(...big(q.d)); return withSign(q.n < 0n, [m]); }
  }
  if (wantExact(v, setup, view) && !view.eng) return exactRow(v.x);
  if (v.x && v.x.isRational() && v.x.a.isInt() && !view.eng && (setup.fmt === "norm1" || setup.fmt === "norm2") && M.bigDigits(v.x.a.n) <= 10) return big(v.x.a.n);
  return floatRow(v.f, setup, view.eng || 0);
}
export function dmsRow(v) {
  const d = M.dms(v); const row = d.sg < 0 ? [chr("-")] : [];
  row.push(...digitsRow(String(d.d)), chr("°"), ...digitsRow(String(d.m)), chr("′"), ...digitsRow(String(d.s)), chr("″")); return row;
}
export function valueRow(v, setup, view = {}) {
  let row;
  if (isC(v)) {
    if (view.polar) {
      const r = M.sqrt(M.add(M.mul(v.re, v.re), M.mul(v.im, v.im)));
      row = [...numRow(r, setup, view), chr("∠"), ...numRow(view.arg, setup, view)];
    } else {
      const reZero = M.isZero(v.re), neg = M.sign(v.im) < 0, im = neg ? M.neg(v.im) : v.im;
      row = [];
      if (!reZero) { row.push(...numRow(v.re, setup, view)); row.push(chr(neg ? "-" : "+")); } else if (neg) row.push(chr("-"));
      if (!(M.isExact(im) && M.cmp(im, M.ONE) === 0)) row.push(...numRow(im, setup, view));
      row.push(chr("i"));
    }
  } else row = numRow(v, setup, view);
  return link(row);
}
export const plainText = (v, setup) => (isC(v) ? `${plainText(v.re, setup)}+${plainText(v.im, setup)}i` : (() => { const p = M.floatParts(v.f, setup); return p.sci ? `${p.m}E${p.e}` : p.m; })());

/** number literal with ×10^e for constants */
export function sciLiteral(mant, exp) {
  const row = digitsRow(mant);
  if (exp) { const e = template("exp"); e.e.push(...digitsRow(String(exp))); row.push(e); }
  return row;
}
