/** DOM renderer for expression rows (natural display) */
import { rowsOf } from "./tree.js";

const GLYPH = { "-": "−", r: "ʳ", g: "ᵍ", "*": "×" };
const el = (cls, children = [], tag = "span") => { const e = document.createElement(tag); e.className = cls; for (const c of [].concat(children)) if (c != null) e.append(c); return e; };
const txt = (s) => document.createTextNode(s);

export function renderRow(row, cur, o = {}) {
  const r = el("r" + (o.top ? " top" : ""));
  const put = (i) => { if (cur && cur.row === row && cur.i === i) r.append(el("cur")); };
  put(0);
  row.forEach((n, i) => { r.append(renderNode(n, cur, o)); put(i + 1); });
  if (!row.length && !o.top && !o.noBox) r.append(el("box"));
  return r;
}
function renderNode(n, cur, o) {
  const R = (row) => renderRow(row, cur, o);
  switch (n.k) {
    case "c": {
      const v = n.v, k = /^[0-9.]$/.test(v) ? "num" : /^[+\-×÷=]$/.test(v) ? "op" : /^[A-FXYM]$/.test(v) || v === "i" || v === "e" || v === "π" ? "var" : "sym";
      return el(`ch ${k}`, txt(GLYPH[v] || v));
    }
    case "fn": return el("fn", txt(n.v.replace("asin", "sin⁻¹").replace("acos", "cos⁻¹").replace("atan", "tan⁻¹").replace("asinh", "sinh⁻¹")));
    case "frac": return el("frac", [el("fn-n", R(n.n)), el("fn-d", R(n.d))]);
    case "mixed": return el("mixed", [el("mw", R(n.w)), el("frac", [el("fn-n", R(n.n)), el("fn-d", R(n.d))])]);
    case "pow": return el("sup", R(n.e));
    case "exp": return el("expn", [el("ch op", txt("×10")), el("sup", R(n.e))]);
    case "sqrt": return el("sqrt", [el("rd", txt("√")), el("rb", R(n.r))]);
    case "root": return el("sqrt", [el("ri", R(n.n)), el("rd", txt("√")), el("rb", R(n.r))]);
    case "abs": return el("abs", [el("ab", txt("|")), R(n.r), el("ab", txt("|"))]);
    case "logb": return el("logb", [el("fn", txt("log")), el("sub", R(n.b)), el("ch sym", txt("(")), R(n.a), el("ch sym", txt(")"))]);
    case "int": return el("integral", [el("big", txt("∫")), el("lims", [el("lim hi", R(n.hi)), el("lim lo", R(n.lo))]), R(n.f), el("ch sym", txt("dx"))]);
    case "sum": return el("integral", [el("big", txt("Σ")), el("lims", [el("lim hi", R(n.hi)), el("lim lo", [txt("X="), R(n.lo)])]), R(n.f)]);
    case "diff": return el("diffn", [el("frac", [el("fn-n", txt("d")), el("fn-d", txt("dx"))]), el("ch sym", txt("(")), R(n.f), el("ch sym", txt(")")), el("sub", [txt("x="), R(n.at)])]);
    default: return txt("?");
  }
}
export function renderResult(row, o = {}) { return renderRow(row, null, { noBox: true, ...o, top: true }); }
export { rowsOf };

/** plain-text form of a row ("7/12", "2√8", "π/3") – used for tests and screen readers */
export function rowText(row) {
  return row.map((n) => {
    switch (n.k) {
      case "c": return GLYPH[n.v] || n.v;
      case "fn": return n.v;
      case "frac": return `(${rowText(n.n)})/(${rowText(n.d)})`.replace(/^\((\w+)\)\/\((\w+)\)$/, "$1/$2");
      case "mixed": return `${rowText(n.w)} ${rowText(n.n)}/${rowText(n.d)}`;
      case "pow": return `^(${rowText(n.e)})`;
      case "exp": return `×10^(${rowText(n.e)})`;
      case "sqrt": return `√(${rowText(n.r)})`;
      case "root": return `${rowText(n.n)}√(${rowText(n.r)})`;
      case "abs": return `|${rowText(n.r)}|`;
      case "logb": return `log_${rowText(n.b)}(${rowText(n.a)})`;
      case "int": return `∫(${rowText(n.lo)},${rowText(n.hi)},${rowText(n.f)})`;
      case "sum": return `Σ(${rowText(n.lo)},${rowText(n.hi)},${rowText(n.f)})`;
      case "diff": return `d/dx(${rowText(n.f)},${rowText(n.at)})`;
      default: return "?";
    }
  }).join("");
}
