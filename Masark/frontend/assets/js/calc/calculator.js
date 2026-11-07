/**
 * Casio-style scientific calculator (natural display).
 * Modes: COMP, CMPLX, STAT, BASE-N, EQN, TABLE.   mountCalculator(host) → { dispose, api }
 */
import * as M from "./num.js";
import * as T from "./tree.js";
import * as P from "./parser.js";
import * as MD from "./modes.js";
import { valueRow, sciLiteral } from "./format.js";
import { renderRow, renderResult, rowText } from "./render.js";

const VARS = ["A", "B", "C", "D", "E", "F", "X", "Y", "M"];
const CONSTS = [["c  (speed of light)", "299792458", 0], ["g  (gravity)", "9.80665", 0], ["G  (gravitation)", "6.6743", -11], ["h  (Planck)", "6.62607015", -34], ["e  (elementary charge)", "1.602176634", -19],
  ["N_A  (Avogadro)", "6.02214076", 23], ["k  (Boltzmann)", "1.380649", -23], ["R  (gas constant)", "8.314462618", 0], ["m_e  (electron mass)", "9.1093837015", -31],
  ["m_p  (proton mass)", "1.67262192369", -27], ["m_n  (neutron mass)", "1.67492749804", -27], ["ε0  (permittivity)", "8.8541878128", -12], ["μ0  (permeability)", "1.25663706212", -6],
  ["F  (Faraday)", "96485.33212", 0], ["σ  (Stefan–Boltzmann)", "5.670374419", -8], ["atm  (standard pressure)", "101325", 0], ["Vm  (molar volume)", "0.022413969545", 0], ["α  (fine-structure)", "7.2973525693", -3], ["a0  (Bohr radius)", "5.29177210903", -11]];

const K = (l, cls, m, o = {}) => ({ l, cls, m, ...o });
const KEYS = {
  shift: K("SHIFT", "shiftk small", "x:shift"), alpha: K("ALPHA", "alphak small", "x:alpha"), mode: K("MODE", "mode small", "x:mode", { sl: "SETUP", s: "x:setup" }), on: K("ON", "on small", "x:on"),
  calc: K("CALC", "small", "x:calc", { sl: "SOLVE", s: "x:solve", al: "=", a: "c:=" }), integ: K("∫▫dx", "small", "t:int", { sl: "d/dx", s: "t:diff" }), optn: K("OPTN", "small", "x:optn"),
  inv: K("x<sup>-1</sup>", "", "x:inv", { sl: "x!", s: "c:!" }), frac: K("▫/▫", "", "t:frac", { sl: "▫▫/▫", s: "t:mixed" }), sqrt: K("√▫", "", "t:sqrt", { sl: "∛▫", s: "x:cbrt" }),
  sq: K("x<sup>2</sup>", "", "x:sq", { sl: "x<sup>3</sup>", s: "x:cube" }), pow: K("x<sup>▫</sup>", "", "x:pow", { sl: "<sup>▫</sup>√▫", s: "x:xroot" }),
  log: K("log", "", "f:log", { sl: "10<sup>x</sup>", s: "x:ten" }), ln: K("ln", "", "f:ln", { sl: "e<sup>x</sup>", s: "x:expe" }),
  neg: K("(−)", "", "c:-", { sl: "∠", s: "c:∠", al: "A", a: "c:A" }), dms: K("°′″", "small", "x:dms", { al: "B", a: "c:B" }), hyp: K("hyp", "small", "x:hyp", { sl: "Abs", s: "f:Abs", al: "C", a: "c:C" }),
  sin: K("sin", "", "f:sin", { sl: "sin<sup>-1</sup>", s: "f:asin", al: "D", a: "c:D" }), cos: K("cos", "", "f:cos", { sl: "cos<sup>-1</sup>", s: "f:acos", al: "E", a: "c:E" }), tan: K("tan", "", "f:tan", { sl: "tan<sup>-1</sup>", s: "f:atan", al: "F", a: "c:F" }),
  rcl: K("RCL", "small", "x:rcl", { sl: "STO", s: "x:sto" }), eng: K("ENG", "small", "x:eng", { sl: "←", s: "x:engdn", al: "i", a: "c:i" }), lp: K("(", "", "c:(", { sl: "%", s: "c:%" }),
  rp: K(")", "", "c:)", { sl: ",", s: "c:,", al: "X", a: "c:X" }), sd: K("S⇔D", "small", "x:sd", { sl: "a b/c", s: "x:mixedtoggle", al: "Y", a: "c:Y" }), mplus: K("M+", "small", "x:mplus", { sl: "M−", s: "x:mminus", al: "M", a: "c:M" }),
  7: K("7", "num", "c:7", { sl: "CONST", s: "x:const" }), 8: K("8", "num", "c:8"), 9: K("9", "num", "c:9", { sl: "CLR", s: "x:clr" }), del: K("DEL", "del small", "x:del"), ac: K("AC", "ac small", "x:ac", { sl: "OFF", s: "x:off" }),
  4: K("4", "num", "c:4"), 5: K("5", "num", "c:5"), 6: K("6", "num", "c:6"), mul: K("×", "opk", "c:×", { sl: "nPr", s: "c:nPr" }), div: K("÷", "opk", "c:÷", { sl: "nCr", s: "c:nCr" }),
  1: K("1", "num", "c:1", { sl: "STAT", s: "x:stat" }), 2: K("2", "num", "c:2"), 3: K("3", "num", "c:3"), plus: K("+", "opk", "c:+", { sl: "Pol", s: "f:Pol" }), minus: K("−", "opk", "c:-", { sl: "Rec", s: "f:Rec" }),
  0: K("0", "num", "c:0"), dot: K(".", "num", "c:.", { sl: "Ran#", s: "c:Ran#" }), exp: K("×10<sup>x</sup>", "num small", "x:exp", { sl: "π", s: "c:π", al: "e", a: "c:e" }), ans: K("Ans", "num small", "c:Ans", { sl: "DRG▸", s: "x:drg" }), eq: K("=", "eq", "x:eq"),
};

export async function mountCalculator(host, opts = {}) {
  const lang = opts.lang || (document.documentElement.lang === "ar" ? "ar" : "en");
  const ar = lang === "ar";
  host.innerHTML = `
  <div class="calc-root" tabindex="0" aria-label="${ar ? "آلة حاسبة علمية" : "Scientific calculator"}">
    <div class="calc-body">
      <div class="calc-top"><div class="calc-brand">MASARK</div><div class="solar"></div><div class="calc-model"><b>SC-991EX</b>NATURAL-V.P.A.M.</div></div>
      <div class="lcd"><div class="lcd-glass"><div class="lcd-status"></div><div class="lcd-screen"></div></div></div>
      <div class="keys"></div>
    </div>
    <div class="calc-help" dir="${ar ? "rtl" : "ltr"}"></div>
  </div>`;
  const root = host.querySelector(".calc-root"), statusEl = host.querySelector(".lcd-status"), screenEl = host.querySelector(".lcd-screen"), keysEl = host.querySelector(".keys");

  /* ------------------------------------------------------------- state */
  const newRow = () => T.link([]);
  const S = {
    on: true, mode: "COMP", shift: false, alpha: false, hyp: false, pending: null, unit: "deg", fmt: { fmt: "norm1", n: 0 },
    vars: Object.fromEntries(VARS.map((v) => [v, M.ZERO])), ans: null, row: newRow(), cur: null, result: null, fresh: false, err: null,
    history: [], hpos: -1, screen: "main", menu: null, grid: null, lines: null, back: null, base: 10, stat: null, eqn: null, table: null,
  };
  S.cur = T.makeCursor(S.row);
  const ctx = () => ({ unit: S.unit, cx: S.mode === "CMPLX", vars: S.vars, ans: S.ans });
  const setup = () => S.fmt;

  /* ---------------------------------------------------------- helpers */
  const clearInputState = () => { S.err = null; S.result = null; };
  const resetMain = () => { S.row = newRow(); S.cur = T.makeCursor(S.row); S.result = null; S.err = null; S.fresh = false; S.hpos = -1; };
  const onGrid = () => S.screen === "grid";
  function prep(kind) {
    if (S.screen !== "main" && S.screen !== "grid" && S.screen !== "table") return;
    S.err = null;
    if (S.screen === "main" && S.fresh) {
      S.fresh = false;
      if (S.mode === "BASE") { resetMain(); return; }
      if (kind === "op" || kind === "post" || kind === "pow" || kind === "infix") { resetMain(); T.insertChar(S.cur, "Ans"); } else resetMain();
    } else if (S.screen === "main") S.result = null;
  }
  const kindOf = (v) => (/^[+×÷]$/.test(v) || v === "-" ? "op" : /^[!%°′″rg]$/.test(v) ? "post" : v === "nPr" || v === "nCr" || v === "∠" ? "infix" : "new");
  const exitTpl = (node) => { S.cur.row = node.row; S.cur.i = node.row.indexOf(node) + 1; };

  /* ---------------------------------------------------------- results */
  function setResult(value, multi = null, extra = {}) {
    S.result = { value, multi, view: { dec: false, dms: false, eng: 0, mixed: false, polar: false }, ...extra };
    if (!multi) S.ans = value; else S.ans = multi[0].val;
    S.fresh = true; S.hpos = -1;
    S.history.push(T.plain(S.row)); if (S.history.length > 40) S.history.shift();
  }
  function fail(e, tok) {
    if (e instanceof P.SyntaxErr || e.kind === "syntax" || e.message === "Syntax ERROR") S.err = { msg: "Syntax ERROR", tok: e.tok || tok || null };
    else if (e instanceof M.MathError || e.kind === "math") S.err = { msg: "Math ERROR", tok: null };
    else { console.error(e); S.err = { msg: "Math ERROR", tok: null }; }
    S.result = null; S.fresh = false;
  }
  function evalMain() {
    if (T.isEmpty(S.row)) return;
    if (S.mode === "BASE") return evalBase();
    try {
      if (P.hasEquals(S.row)) throw new P.SyntaxErr();
      const c = ctx(), r = P.evaluateRow(S.row, c);
      setResult(r.value, c.multi);
    } catch (e) { fail(e); }
  }
  function evalBase() {
    try {
      const toks = []; let cur = "";
      const flush = () => { if (cur) { toks.push({ d: cur }); cur = ""; } };
      for (const n of S.row) {
        if (n.k === "c" && /^[0-9A-F]$/.test(n.v)) cur += n.v;
        else { flush(); if (n.k === "c") toks.push(n.v); else if (n.k === "fn") toks.push(n.v); else throw new P.SyntaxErr(); }
      }
      flush();
      const v = MD.baseEval(toks.filter((t) => t !== "Ans"), S.base);
      S.result = { base: v, view: {} }; S.fresh = true; S.ans = M.fromBig(v);
    } catch (e) { fail(e); }
  }

  /* --------------------------------------------------------- screens */
  function openMenu(title, items, o = {}) { S.menu = { title, items, sel: 0, digit0: !!o.digit0, back: o.back || S.screen === "menu" ? S.menu?.back || "main" : S.screen }; S.screen = "menu"; }
  function closeMenu() { S.screen = S.menu?.back || "main"; S.menu = null; if (S.screen === "grid" && S.grid) focusCell(S.grid.r, S.grid.c); }
  function pickMenu(i) { const it = S.menu.items[i]; if (!it) return; const m = S.menu; S.menu = null; S.screen = m.back || "main"; it.run(); }
  function openGrid(g) {
    S.grid = { r: 0, c: 0, ...g }; S.screen = "grid"; focusCell(0, 0);
  }
  function focusCell(r, c) { const g = S.grid; g.r = r; g.c = c; const cell = g.cells[r][c]; S.cur = { row: cell, i: cell.length }; }
  function commitCell() {
    const g = S.grid; let c = g.c + 1, r = g.r;
    if (c >= g.cells[0].length) { c = 0; r++; }
    if (r >= g.cells.length) { if (g.grow && g.cells.length < g.max) { g.cells.push(g.cells[0].map(() => T.link([]))); } else return g.done?.(); }
    focusCell(r, c);
  }
  const cellVal = (row, dflt = null) => {
    if (T.isEmpty(row)) return dflt;
    return P.evaluateRow(row, ctx()).value;
  };

  /* -------------------------------------------------------- modes */
  function setMode(m) {
    S.mode = m; S.screen = "main"; S.menu = null; S.grid = null; S.lines = null; S.table = null; resetMain();
    if (m === "STAT") openMenu("STAT", [["1-VAR", "1"], ["A+BX", "2"], ["_+CX²", "3"]].map(([t, k]) => ({ t: `${k}: ${t}`, run: () => startStat(k) })), { back: "main" });
    else if (m === "EQN") openMenu("EQN", ["aX+bY=c", "aX+bY+cZ=d", "aX²+bX+c=0", "aX³+bX²+cX+d=0"].map((t, i) => ({ t: `${i + 1}: ${t}`, run: () => startEqn(i) })), { back: "main" });
    else if (m === "TABLE") { S.screen = "table"; S.table = { phase: "fx" }; }
    else if (m === "BASE") S.base = 10;
  }
  function startStat(k) {
    S.stat = { type: k }; const two = k !== "1";
    const mk = () => T.link([]);
    openGrid({ title: `STAT ${k === "1" ? "1-VAR" : k === "2" ? "A+BX" : "_+CX²"}`, headers: two ? ["x", "y"] : ["x", "FREQ"], cells: Array.from({ length: 4 }, () => [mk(), mk()]), grow: true, max: 40, kind: "stat", done: () => {} });
  }
  function statResults() {
    try {
      const g = S.grid, k = S.stat.type, xs = [], ys = [], fs = []; let any = false;
      for (const [x, b] of g.cells) { if (T.isEmpty(x)) continue; any = true; xs.push(cellVal(x)); if (k === "1") fs.push(T.isEmpty(b) ? M.ONE : cellVal(b)); else { if (T.isEmpty(b)) throw new P.SyntaxErr(); ys.push(cellVal(b)); } }
      if (!any) return;
      const out = k === "1" ? MD.stat1(xs, fs) : MD.stat2(xs, ys, null, k === "3");
      S.lines = { title: "STAT RESULTS", items: out.map(([l, v]) => ({ label: l, row: valueRow(v, setup()) })), scroll: 0, back: "grid" }; S.screen = "lines";
    } catch (e) { fail(e); S.screen = "main"; }
  }
  function startEqn(t) {
    S.eqn = { t }; const mk = () => T.link([]);
    const dims = [[2, 3, ["a", "b", "c"], ["X+Y"]], [3, 4, ["a", "b", "c", "d"]], [1, 3, ["a", "b", "c"]], [1, 4, ["a", "b", "c", "d"]]][t];
    openGrid({ title: ["aX+bY=c", "aX+bY+cZ=d", "aX²+bX+c=0", "aX³+bX²+cX+d=0"][t], headers: dims[2], cells: Array.from({ length: dims[0] }, () => Array.from({ length: dims[1] }, mk)), kind: "eqn", done: solveEqn });
  }
  function solveEqn() {
    try {
      const g = S.grid, t = S.eqn.t, vals = g.cells.map((r) => r.map((c) => cellVal(c, M.ZERO)));
      const items = [];
      const names = ["X", "Y", "Z"];
      if (t < 2) MD.solveLinear(vals).forEach((v, i) => items.push({ label: names[i] + "=", row: valueRow(v, setup()) }));
      else { const roots = t === 2 ? MD.quadratic(...vals[0]) : MD.cubic(...vals[0]); roots.forEach((v, i) => items.push({ label: `X${i + 1}=`, row: valueRow(v, setup()) })); }
      S.lines = { title: "EQN", items, scroll: 0, back: "grid" }; S.screen = "lines";
    } catch (e) { fail(e); S.screen = "main"; }
  }
  function tableFlow() {
    const tb = S.table;
    if (tb.phase === "fx") {
      if (T.isEmpty(S.row)) return;
      try { tb.ast = P.parseRow(S.row); } catch (e) { fail(e); return; }
      tb.phase = "range";
      const mk = (s) => T.link([...s].map(T.chr));
      openGrid({ title: "TABLE", headers: ["Start", "End", "Step"], cells: [[mk("1")], [mk("5")], [mk("1")]], kind: "table", done: tableRun });
    }
  }
  function tableRun() {
    try {
      const g = S.grid, [a, b, st] = g.cells.map((r) => cellVal(r[0])); if (M.sign(st) <= 0 || M.cmp(b, a) < 0) throw new M.MathError();
      const items = []; let x = a, n = 0;
      while (M.cmp(x, b) <= 0 && n < 30) {
        const c = { ...ctx(), vars: { ...S.vars, X: x } }; let fv; try { fv = P.evaluateAst(S.table.ast, c); } catch { fv = null; }
        items.push({ label: valueRow(x, setup()), row: fv ? valueRow(fv, setup()) : T.link([T.chr("?")]), table: true }); x = M.add(x, st); n++;
      }
      S.lines = { title: "TABLE   X  |  f(X)", items, scroll: 0, back: "table", table: true }; S.screen = "lines";
    } catch (e) { fail(e); S.screen = "main"; }
  }

  /* --------------------------------------------------------- CALC/SOLVE */
  function promptVars(names, title, start, done) {
    const mk = (n) => { const v = S.vars[n]; return T.link(v && !M.isZero(v) ? [...valueRow(v, { fmt: "norm1", n: 0 }).map((x) => x)].filter((x) => x.k === "c").map((x) => T.chr(x.v)) : []); };
    openGrid({ title, headers: names, rowHeaders: names, cells: names.map((n) => [mk(n)]), kind: "prompt", done: () => { try { const vals = {}; S.grid.cells.forEach((r, i) => { vals[names[i]] = cellVal(r[0], M.ZERO); }); done(vals); } catch (e) { fail(e); S.screen = "main"; } } });
  }
  function doCalc() {
    if (T.isEmpty(S.row)) return;
    try {
      const ast = P.parseRow(S.row), names = [...P.varsIn(ast)].filter((v) => v !== "M").sort();
      if (!names.length) return evalMain();
      const keep = T.plain(S.row);
      promptVars(names, "CALC", 0, (vals) => {
        S.screen = "main"; S.row = T.fromPlain(keep); S.cur = T.makeCursor(S.row); Object.assign(S.vars, vals);
        try { const c = ctx(), v = P.evaluateAst(ast, c); setResult(v, c.multi); } catch (e) { fail(e); }
      });
    } catch (e) { fail(e); }
  }
  function doSolve() {
    if (T.isEmpty(S.row)) return;
    try {
      const eq = P.parseEquation(S.row) || { lhs: P.parseRow(S.row), rhs: { t: "num", v: M.ZERO } }, keep = T.plain(S.row);
      promptVars(["X"], "SOLVE  Solve for X?", 0, (vals) => {
        S.screen = "main"; S.row = T.fromPlain(keep); S.cur = T.makeCursor(S.row);
        try {
          const f = (x) => { const c = { ...ctx(), vars: { ...S.vars, X: M.nF(x) } }; return P.evaluateAst(eq.lhs, c).f - P.evaluateAst(eq.rhs, c).f; };
          const r = P.findRoot(f, vals.X.f); if (r === null) throw new M.MathError();
          const rv = Math.abs(r - Math.round(r)) < 1e-9 * Math.max(1, Math.abs(r)) ? M.nQ(Math.round(r)) : M.nF(r); S.vars.X = rv;
          setResult(rv, [{ label: "X=", val: rv }, { label: "L−R=", val: M.nQ(0) }]);
        } catch (e) { fail(e); }
      });
    } catch (e) { fail(e); }
  }

  /* ------------------------------------------------------------ actions */
  function insertConst(m, e) { prep("new"); for (const n of sciLiteral(m, e)) T.insert(S.cur, n.k === "exp" ? n : n); if (S.cur.row.owner && e) exitTpl(S.cur.row.owner); }
  const ops = {
    shift() { S.shift = !S.shift; S.alpha = false; return true; },
    alpha() { S.alpha = !S.alpha; S.shift = false; return true; },
    hyp() { S.hyp = !S.hyp; return true; },
    on() { S.on = true; },
    off() { S.on = false; },
    ac() {
      if (S.screen === "menu") return closeMenu();
      if (S.screen === "lines") { const b = S.lines.back; S.lines = null; S.screen = b || "main"; if (b === "table") { S.table.phase = "fx"; S.screen = "table"; } if (b === "grid" && S.grid) focusCell(S.grid.r, S.grid.c); return; }
      if (S.screen === "grid") {
        if (S.grid.kind === "stat") return statResults();
        if (S.grid.kind === "prompt" || S.grid.kind === "table") { S.screen = S.grid.kind === "table" ? "table" : "main"; if (S.grid.kind === "table") S.table.phase = "fx"; return; }
        S.grid.cells.forEach((r) => r.forEach((c) => T.clearRow(c))); focusCell(0, 0); return;
      }
      if (S.screen === "main" || S.screen === "table") { resetMain(); if (S.table) S.table.phase = "fx"; }
    },
    del() {
      if (S.err) { S.err = null; return; }
      if (S.screen === "main" || onGrid() || S.screen === "table") { if (S.result) { S.result = null; S.fresh = false; } T.backspace(S.cur); }
    },
    eq() {
      if (S.screen === "menu") return pickMenu(S.menu.sel);
      if (S.screen === "grid") return commitCell();
      if (S.screen === "lines") return ops.ac();
      if (S.screen === "table") return tableFlow();
      if (S.err) return;
      evalMain();
    },
    exp() { prep("op"); T.insert(S.cur, T.template("exp")); },
    pow() { prep("pow"); T.insert(S.cur, T.template("pow")); },
    sq() { prep("pow"); const n = T.insert(S.cur, T.template("pow")); n.e.push(T.chr("2")); exitTpl(n); },
    cube() { prep("pow"); const n = T.insert(S.cur, T.template("pow")); n.e.push(T.chr("3")); exitTpl(n); },
    inv() { prep("pow"); const n = T.insert(S.cur, T.template("pow")); n.e.push(T.chr("-"), T.chr("1")); exitTpl(n); },
    ten() { prep("new"); T.insertChar(S.cur, "1"); T.insertChar(S.cur, "0"); T.insert(S.cur, T.template("pow")); },
    expe() { prep("new"); T.insertChar(S.cur, "e"); T.insert(S.cur, T.template("pow")); },
    cbrt() { prep("new"); const n = T.insertTemplate(S.cur, "root"); n.n.push(T.chr("3")); S.cur.row = n.r; S.cur.i = 0; },
    xroot() { prep("new"); T.insertTemplate(S.cur, "root", "n"); },
    dms() {
      if (S.result && S.fresh && S.result.value && !P.isC(S.result.value)) { S.result.view.dms = !S.result.view.dms; return; }
      prep("post"); const row = S.cur.row; let last = null;
      for (let j = S.cur.i - 1; j >= 0; j--) { const n = row[j]; if (n.k === "c" && /[°′″]/.test(n.v)) { last = n.v; break; } if (!(n.k === "c" && /[0-9.]/.test(n.v))) break; }
      const prevIsNum = S.cur.i > 0 && row[S.cur.i - 1].k === "c" && /[0-9.°′]/.test(row[S.cur.i - 1].v);
      T.insertChar(S.cur, !prevIsNum ? "°" : last === "°" ? "′" : last === "′" ? "″" : "°");
    },
    sd() { if (S.result && S.result.value) { S.result.view.dec = !S.result.view.dec; S.result.view.mixed = false; } },
    mixedtoggle() { if (S.result && S.result.value) { S.result.view.mixed = !S.result.view.mixed; S.result.view.dec = false; } },
    eng() { if (S.result && S.result.value) S.result.view.eng = (S.result.view.eng || 0) + 1; },
    engdn() { if (S.result && S.result.value) S.result.view.eng = (S.result.view.eng || 0) - 1; },
    mplus() { memAdd(1); }, mminus() { memAdd(-1); },
    rcl() { S.pending = "rcl"; }, sto() { S.pending = "sto"; },
    calc() { doCalc(); }, solve() { doSolve(); },
    mode() {
      openMenu("MODE", [["COMP", "COMP"], ["CMPLX", "CMPLX"], ["STAT", "STAT"], ["BASE-N", "BASE"], ["EQN", "EQN"], ["TABLE", "TABLE"]].map(([t, m], i) => ({ t: `${i + 1}: ${t}`, run: () => setMode(m) })), { back: "main" });
    },
    setup() {
      const pick = (f) => () => { f(); };
      openMenu("SETUP", [
        { t: "1: Deg", run: pick(() => { S.unit = "deg"; }) }, { t: "2: Rad", run: pick(() => { S.unit = "rad"; }) }, { t: "3: Gra", run: pick(() => { S.unit = "gra"; }) },
        { t: "4: Fix", run: () => openMenu("Fix 0~9", Array.from({ length: 10 }, (_, d) => ({ t: String(d), run: () => { S.fmt = { fmt: "fix", n: d }; } })), { digit0: true, back: "main" }) },
        { t: "5: Sci", run: () => openMenu("Sci 1~9 (0=10)", Array.from({ length: 10 }, (_, d) => ({ t: String(d), run: () => { S.fmt = { fmt: "sci", n: d }; } })), { digit0: true, back: "main" }) },
        { t: "6: Norm", run: () => openMenu("Norm", [{ t: "1: Norm 1", run: () => { S.fmt = { fmt: "norm1", n: 0 }; } }, { t: "2: Norm 2", run: () => { S.fmt = { fmt: "norm2", n: 0 }; } }], { back: "main" }) },
      ], { back: "main" });
    },
    clr() { openMenu("CLR", [{ t: "1: Setup", run: () => { S.unit = "deg"; S.fmt = { fmt: "norm1", n: 0 }; } }, { t: "2: Memory", run: () => { for (const v of VARS) S.vars[v] = M.ZERO; S.ans = null; } }, { t: "3: All", run: () => { for (const v of VARS) S.vars[v] = M.ZERO; S.ans = null; S.unit = "deg"; S.fmt = { fmt: "norm1", n: 0 }; S.history = []; resetMain(); } }], { back: "main" }); },
    drg() { prep("post"); openMenu("DRG▸", [{ t: "1: °", run: () => T.insertChar(S.cur, "°") }, { t: "2: ʳ", run: () => T.insertChar(S.cur, "r") }, { t: "3: ᵍ", run: () => T.insertChar(S.cur, "g") }], { back: S.screen }); },
    const() {
      openMenu("CONST", CONSTS.map(([t, m, e], i) => ({ t: `${String(i + 1).padStart(2, "0")}: ${t}`, run: () => insertConst(m, e) })), { back: S.screen });
    },
    stat() { if (S.mode === "STAT" && S.stat) { if (S.screen === "lines") return; statResults(); } },
    optn() {
      if (S.mode === "CMPLX") return openMenu("OPTN", [["Abs", "f:Abs"], ["arg", "f:arg"], ["Conjg", "f:Conjg"], ["Re", "f:Re"], ["Im", "f:Im"], ["▸r∠θ", "x:polar"], ["▸a+bi", "x:rect"]].map(([t, a], i) => ({ t: `${i + 1}: ${t}`, run: () => act(a) })), { back: "main" });
      if (S.mode === "BASE") return openMenu("LOGIC", ["and", "or", "xor", "xnor", "Not", "Neg"].map((w, i) => ({ t: `${i + 1}: ${w}`, run: () => { if (/^(Not|Neg)$/.test(w)) { prep("new"); T.insert(S.cur, T.fn(w)); T.insertChar(S.cur, "("); } else { prep("op"); T.insertChar(S.cur, w); } } })), { back: "main" });
      openMenu("OPTN", [["log▫▫", "t:logb"], ["Σ( )", "t:sum"], ["Int(", "f:Int"], ["Intg(", "f:Intg"], ["Pol(", "f:Pol"], ["Rec(", "f:Rec"], ["Ran#", "c:Ran#"], ["RanInt(", "f:RanInt"]].map(([t, a], i) => ({ t: `${i + 1}: ${t}`, run: () => act(a) })), { back: S.screen });
    },
    polar() { const r = S.result; if (!r || !r.value) return; r.view.polar = true; r.view.arg = P.cArg(r.value, S.unit); },
    rect() { const r = S.result; if (r) r.view.polar = false; },
  };
  function memAdd(sign) {
    try {
      let v = S.result && S.result.value; if (!v && !T.isEmpty(S.row)) v = P.evaluateRow(S.row, ctx()).value;
      if (!v || P.isC(v)) return;
      S.vars.M = sign > 0 ? P.cAdd(S.vars.M, v) : P.cSub(S.vars.M, v);
    } catch (e) { fail(e); }
  }
  const BASE_ROW = { sq: 10, pow: 16, log: 2, ln: 8 };

  function act(a, keyId) {
    const t = a[0], v = a.slice(2);
    if (S.mode === "BASE" && S.screen === "main" && ["sq", "pow", "log", "ln"].includes(keyId) && !S.shift && !S.alpha) { S.base = BASE_ROW[keyId]; S.result = S.result ? { ...S.result } : null; return; }
    if (t === "c") {
      if (S.screen === "menu") return;
      if (S.mode === "BASE" && S.screen === "main" && /^[0-9A-F]$/.test(v) && !MD.baseDigitOk(v, S.base)) return;
      if (S.mode === "BASE" && S.screen === "main" && /^[A-F]$/.test(v) && !S.alpha && false) return;
      prep(kindOf(v)); T.insertChar(S.cur, v);
    } else if (t === "f") { prep("new"); T.insert(S.cur, T.fn(v)); T.insertChar(S.cur, "("); }
    else if (t === "t") { prep("new"); if (v === "frac") T.insertTemplate(S.cur, "frac", "n"); else if (v === "mixed") T.insertTemplate(S.cur, "mixed"); else T.insertTemplate(S.cur, v); }
    else if (t === "x") { const f = ops[v]; if (f) return f(); }
  }

  /* ---------------------------------------------------------- key press */
  function press(id) {
    const k = KEYS[id]; if (!k) return;
    if (!S.on && id !== "on") return;
    if (id === "shift" || id === "alpha" || id === "hyp") { ops[id](); return draw(); }
    let a = S.shift && k.s ? k.s : S.alpha && k.a ? k.a : k.m;
    if (S.shift && !k.s && id !== "shift") a = k.m;                // shift on a key without a 2nd function: use the normal one
    if (S.pending) {
      const p = S.pending; S.pending = null;
      const letter = k.a && /^c:[A-FXYM]$/.test(k.a) ? k.a.slice(2) : /^[A-FXYM]$/.test(k.l) ? k.l : null;
      if (letter) {
        if (p === "rcl") { prep("new"); T.insertChar(S.cur, letter); }
        else { const v = S.result && S.result.value ? S.result.value : S.ans; if (v) S.vars[letter] = v; }
      }
      S.shift = S.alpha = false; return draw();
    }
    if (S.hyp && ["sin", "cos", "tan"].includes(id)) { a = `f:${S.shift ? "a" : ""}${id}h`; S.hyp = false; }
    if (S.screen === "menu" && /^[0-9]$/.test(id)) { const m = S.menu, i = m.digit0 ? +id : +id - 1; if (m.items[i]) pickMenu(i); S.shift = S.alpha = false; return draw(); }
    const keepEdit = !(a === "x:shift" || a === "x:alpha");
    act(a, id);
    if (keepEdit) { S.shift = false; S.alpha = false; }
    draw();
  }
  function arrow(dir) {
    if (!S.on) return;
    if (S.err) { const t = S.err.tok; S.err = null; if (t && t.row && T.rowsOf && rowInTree(t.row)) { S.cur = { row: t.row, i: Math.min(t.i ?? 0, t.row.length) }; } else { S.cur = T.makeCursor(S.row); } S.fresh = false; return draw(); }
    if (S.screen === "menu") { const m = S.menu, n = m.items.length; if (dir === "up") m.sel = (m.sel + n - 1) % n; if (dir === "down") m.sel = (m.sel + 1) % n; return draw(); }
    if (S.screen === "lines") { const l = S.lines; l.scroll = Math.max(0, Math.min(Math.max(0, l.items.length - (l.table ? 5 : 4)), l.scroll + (dir === "down" ? 1 : dir === "up" ? -1 : 0))); return draw(); }
    if (S.screen === "grid") {
      const g = S.grid;
      if (dir === "up" || dir === "down") { if (!(dir === "up" ? T.moveUp(S.cur) : T.moveDown(S.cur))) { const r = Math.max(0, Math.min(g.cells.length - 1, g.r + (dir === "down" ? 1 : -1))); focusCell(r, g.c); } }
      else if (dir === "left") { if (S.cur.i === 0 && !S.cur.row.owner && g.c > 0) focusCell(g.r, g.c - 1); else T.moveLeft(S.cur); }
      else { if (S.cur.i === S.cur.row.length && !S.cur.row.owner && g.c < g.cells[0].length - 1) focusCell(g.r, g.c + 1); else T.moveRight(S.cur); }
      return draw();
    }
    if (S.fresh && S.result) { S.result = null; S.fresh = false; }
    if (dir === "left") T.moveLeft(S.cur); else if (dir === "right") T.moveRight(S.cur);
    else if (dir === "up") { if (!T.moveUp(S.cur)) historyStep(-1); } else if (!T.moveDown(S.cur)) historyStep(1);
    draw();
  }
  function rowInTree(row) { let r = row; while (r.owner) r = r.owner.row; return r === S.row; }
  function historyStep(d) {
    if (!S.history.length) return;
    let p = S.hpos < 0 ? (d < 0 ? S.history.length - 1 : -1) : S.hpos + d;
    if (p < 0 || p >= S.history.length) return; S.hpos = p;
    S.row = T.fromPlain(S.history[p]); S.cur = T.makeCursor(S.row); S.result = null; S.fresh = false;
  }

  /* --------------------------------------------------------------- draw */
  const el = (cls, kids = [], tag = "div") => { const e = document.createElement(tag); e.className = cls; for (const k of [].concat(kids)) if (k != null) e.append(k); return e; };
  const txt = (s) => document.createTextNode(s);
  function drawStatus() {
    const flag = (t, on) => { const s = el("", txt(t), "span"); if (on) s.className = "on"; return s; };
    statusEl.replaceChildren(flag("S", S.shift), flag("A", S.alpha), flag("hyp", S.hyp), flag(S.unit === "deg" ? "D" : S.unit === "rad" ? "R" : "G", true), flag(S.fmt.fmt === "fix" ? "FIX" : S.fmt.fmt === "sci" ? "SCI" : "", S.fmt.fmt === "fix" || S.fmt.fmt === "sci"),
      flag("M", S.vars.M && !M.isZero(S.vars.M)), flag(S.pending === "sto" ? "STO" : S.pending === "rcl" ? "RCL" : "", !!S.pending), el("sp", [], "span"), flag(S.mode === "BASE" ? "BASE-N" : S.mode, true));
  }
  function resultRowEl() {
    const r = S.result;
    if (S.err) { return el("l-res err", [txt(S.err.msg), el("", [txt(S.err.tok ? "[AC] : Cancel   [◀][▶] : Goto" : "[AC] : Cancel   [◀][▶] : Goto")], "small")]); }
    if (!r) return el("l-res");
    if (r.multi) return el("l-multi", r.multi.map((m) => el("", [el("", txt(m.label), "i"), renderResult(valueRow(m.val, setup(), r.view))])));
    return el("l-res", renderResult(valueRow(r.value, setup(), r.view)));
  }
  function drawMain() {
    const wrap = document.createDocumentFragment();
    if (S.mode === "BASE") {
      wrap.append(el("l-bases", [["BIN", 2], ["OCT", 8], ["DEC", 10], ["HEX", 16]].map(([n, b]) => { const s = el(S.base === b ? "on" : "", txt(n), "span"); return s; })));
    }
    const label = S.mode === "TABLE" && S.screen === "table" ? el("l-hint", txt("f(X) ="), "div") : null;
    if (label) wrap.append(label);
    wrap.append(el("l-expr", renderRow(S.row, S.err || S.result ? (S.err ? S.cur : null) : S.cur, { top: true })));
    if (S.mode === "BASE" && S.result && S.result.base !== undefined) {
      const v = S.result.base;
      wrap.append(el("l-res", txt(MD.baseFormat(v, S.base))), el("l-small", [[16, "HEX"], [10, "DEC"], [2, "BIN"], [8, "OCT"]].filter(([b]) => b !== S.base).map(([b, n]) => el("", txt(`${n} ${MD.baseFormat(v, b)}`), "span"))));
    } else wrap.append(resultRowEl());
    return wrap;
  }
  function drawMenu() {
    const m = S.menu, f = document.createDocumentFragment(); f.append(el("l-title", txt(m.title)));
    const win = 5, start = Math.max(0, Math.min(m.sel - 2, m.items.length - win)), vis = m.items.slice(start, start + win);
    f.append(el("l-list", vis.map((it, i) => el("it" + (start + i === m.sel ? " sel" : ""), txt(it.t)))));
    f.append(el("l-hint", txt(m.items.length > win ? "▲▼  [=] select   [AC] back" : "[1]-[" + Math.min(9, m.items.length) + "]  or  ▲▼ [=]   [AC] back")));
    return f;
  }
  function drawGrid() {
    const g = S.grid, f = document.createDocumentFragment(); f.append(el("l-title", txt(g.title)));
    const rh = g.rowHeaders, cols = g.cells[0].length + (rh ? 1 : 0), grid = el("l-grid"); grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    if (!rh) { for (const h of g.headers) grid.append(el("h", txt(h))); } else { grid.append(el("h", txt(""))); grid.append(el("h", txt("value"))); }
    const first = Math.max(0, Math.min(g.r - 1, g.cells.length - 3)); // window of rows
    g.cells.slice(first, first + (rh ? 4 : 3)).forEach((r, ri) => {
      if (rh) grid.append(el("h", txt(rh[first + ri] + " =")));
      r.forEach((c, ci) => { const focused = first + ri === g.r && ci === g.c; grid.append(el("cell" + (focused ? " f" : ""), renderRow(c, focused ? S.cur : null, { top: true }))); });
    });
    f.append(grid, el("l-hint", txt(g.kind === "stat" ? "[=] next   [AC] results" : "[=] next / solve   [AC] back")));
    return f;
  }
  function drawLines() {
    const l = S.lines, f = document.createDocumentFragment(); f.append(el("l-title", txt(l.title)));
    const rows = l.items.slice(l.scroll, l.scroll + (l.table ? 5 : 4));
    f.append(el("l-lines", rows.map((it) => el("ln", [typeof it.label === "string" ? el("", txt(it.label), "b") : el("v", renderResult(it.label)), el("v", renderResult(it.row))]))));
    if (l.items.length > rows.length) f.append(el("l-hint", txt(`▲▼  ${l.scroll + 1}-${l.scroll + rows.length} / ${l.items.length}   [AC] back`)));
    else f.append(el("l-hint", txt("[AC] back")));
    return f;
  }
  function draw() {
    drawStatus();
    root.classList.toggle("off", !S.on);
    keysEl.querySelector('[data-k="shift"]')?.classList.toggle("act", S.shift);
    keysEl.querySelector('[data-k="alpha"]')?.classList.toggle("act", S.alpha);
    const f = S.screen === "menu" ? drawMenu() : S.screen === "grid" ? drawGrid() : S.screen === "lines" ? drawLines() : drawMain();
    screenEl.replaceChildren(f);
    const cur = screenEl.querySelector(".cur"); if (cur) cur.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }

  /* -------------------------------------------------------------- build keys */
  const keyBtn = (id, extra = "") => {
    const k = KEYS[id], cell = el("kcell"); cell.style.cssText = extra;
    if (k.sl || k.al) cell.append(el("sl", [k.sl ? (() => { const s = el("sh", [], "span"); s.innerHTML = k.sl; return s; })() : null, k.al ? (() => { const s = el("al", [], "span"); s.innerHTML = k.al; return s; })() : null]));
    const b = el("key " + (k.cls || ""), [], "button"); b.innerHTML = k.l; b.dataset.k = id; b.type = "button"; b.setAttribute("aria-label", k.l.replace(/<[^>]+>/g, ""));
    cell.append(b); return cell;
  };
  const top = el("padrow");
  top.append(keyBtn("shift", "grid-column:1;grid-row:1"), keyBtn("alpha", "grid-column:2;grid-row:1"), keyBtn("mode", "grid-column:5;grid-row:1"), keyBtn("on", "grid-column:6;grid-row:1"),
    keyBtn("calc", "grid-column:1;grid-row:2"), keyBtn("integ", "grid-column:2;grid-row:2"), keyBtn("optn", "grid-column:5;grid-row:2"), keyBtn("inv", "grid-column:6;grid-row:2"));
  const padWrap = el("padwrap"); padWrap.innerHTML = `<div class="pad"><button class="u" data-a="up" aria-label="up">▲</button><button class="d" data-a="down" aria-label="down">▼</button><button class="l" data-a="left" aria-label="left">◀</button><button class="r rr" data-a="right" aria-label="right">▶</button></div>`;
  top.append(padWrap); keysEl.append(top);
  const rowOf = (ids, cls) => { const r = el("krow " + cls); ids.forEach((i) => r.append(keyBtn(i))); return r; };
  keysEl.append(rowOf(["frac", "sqrt", "sq", "pow", "log", "ln"], "c6"), rowOf(["neg", "dms", "hyp", "sin", "cos", "tan"], "c6"), rowOf(["rcl", "eng", "lp", "rp", "sd", "mplus"], "c6"),
    rowOf(["7", "8", "9", "del", "ac"], "c5"), rowOf(["4", "5", "6", "mul", "div"], "c5"), rowOf(["1", "2", "3", "plus", "minus"], "c5"), rowOf(["0", "dot", "exp", "ans", "eq"], "c5"));
  keysEl.querySelectorAll("button[data-k]").forEach((b) => b.setAttribute("title", ""));
  const onDown = (e) => {
    const b = e.target.closest("button[data-k], button[data-a]"); if (!b || !keysEl.contains(b)) return;
    e.preventDefault(); navigator.vibrate?.(6); b.classList.add("press"); setTimeout(() => b.classList.remove("press"), 90);
    if (b.dataset.a) arrow(b.dataset.a); else press(b.dataset.k);
  };
  keysEl.addEventListener("pointerdown", onDown);
  keysEl.addEventListener("click", (e) => e.preventDefault());

  /* ------------------------------------------------------------ keyboard */
  const KB = { "+": "plus", "-": "minus", "*": "mul", "/": "div", ".": "dot", "(": "lp", ")": "rp", Enter: "eq", "=": "eq", Backspace: "del", Escape: "ac", "^": "pow", r: "sqrt" };
  const onKeyDown = (e) => {
    if (!host.isConnected || e.ctrlKey || e.metaKey || e.altKey) return;
    const tg = e.target; if (tg && (tg.tagName === "INPUT" || tg.tagName === "TEXTAREA" || tg.isContentEditable)) return;
    const key = e.key; let handled = true;
    if (/^[0-9]$/.test(key)) press(key);
    else if (KB[key]) press(KB[key]);
    else if (key === "!") { S.shift = true; press("inv"); }
    else if (key === "%") { S.shift = true; press("lp"); }
    else if (key === "p") { S.shift = true; press("exp"); }
    else if (key === "s") press("sin"); else if (key === "c") press("cos"); else if (key === "t") press("tan"); else if (key === "l") press("log"); else if (key === "n") press("ln");
    else if (key === "ArrowLeft") arrow("left"); else if (key === "ArrowRight") arrow("right"); else if (key === "ArrowUp") arrow("up"); else if (key === "ArrowDown") arrow("down");
    else handled = false;
    if (handled) e.preventDefault();
  };
  document.addEventListener("keydown", onKeyDown);

  /* ---------------------------------------------------------------- help */
  const help = host.querySelector(".calc-help");
  help.innerHTML = ar
    ? `<h4>طريقة الاستخدام</h4><ul><li><b>SHIFT</b> (ذهبي) و <b>ALPHA</b> (أحمر) لتفعيل الوظائف المكتوبة فوق الأزرار.</li><li><b>S⇔D</b> لتحويل النتيجة بين الكسر/الجذر والعدد العشري، و <b>SHIFT + S⇔D</b> للكسر العددي المختلط.</li><li><b>MODE</b> للتبديل بين: COMP، CMPLX (أعداد مركبة)، STAT (إحصاء)، BASE-N، EQN (معادلات)، TABLE (جداول). و <b>SHIFT + MODE</b> للإعدادات (درجات/راديان، Fix/Sci).</li><li><b>CALC</b> لتعويض قيم المتغيرات، و <b>SHIFT + CALC</b> لحل معادلة (اكتب = بـ ALPHA + CALC)، و <b>∫dx</b> للتكامل و <b>SHIFT + ∫dx</b> للتفاضل.</li><li><b>STO</b> = SHIFT + RCL ثم اضغط حرف المتغير. <b>SHIFT + 7</b> الثوابت الفيزيائية.</li><li>من لوحة المفاتيح: <kbd>0-9</kbd> <kbd>+ − * /</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd> <kbd>Esc</kbd> <kbd>^</kbd> <kbd>s c t</kbd> والأسهم.</li></ul>`
    : `<h4>How to use</h4><ul><li><b>SHIFT</b> (gold) and <b>ALPHA</b> (red) unlock the functions printed above the keys.</li><li><b>S⇔D</b> switches a result between fraction/radical and decimal; <b>SHIFT + S⇔D</b> gives a mixed fraction.</li><li><b>MODE</b> switches between COMP, CMPLX, STAT, BASE-N, EQN and TABLE; <b>SHIFT + MODE</b> opens the setup (Deg/Rad, Fix/Sci).</li><li><b>CALC</b> evaluates with variable values, <b>SHIFT + CALC</b> solves an equation (type = with ALPHA + CALC), <b>∫dx</b> integrates and <b>SHIFT + ∫dx</b> differentiates.</li><li><b>STO</b> = SHIFT + RCL then a variable key. <b>SHIFT + 7</b> opens physical constants.</li><li>Keyboard: <kbd>0-9</kbd> <kbd>+ − * /</kbd> <kbd>Enter</kbd> <kbd>Backspace</kbd> <kbd>Esc</kbd> <kbd>^</kbd> <kbd>s c t</kbd> and arrows.</li></ul>`;

  draw();
  return {
    api: {
      press, arrow, S,
      /** text of the current expression/result – used by tests */
      read() {
        if (S.screen === "lines") return { expr: "", result: S.lines.items.map((it) => `${typeof it.label === "string" ? it.label : rowText(it.label)}${rowText(it.row)}`).join("; "), error: "", screen: "lines" };
        if (S.screen === "menu") return { expr: "", result: S.menu.items.map((i) => i.t).join(" | "), error: "", screen: "menu" };
        return { expr: rowText(S.row), result: S.result ? (S.result.multi ? S.result.multi.map((m) => `${m.label}${rowText(valueRow(m.val, setup(), S.result.view))}`).join(" ") : S.result.value ? rowText(valueRow(S.result.value, setup(), S.result.view)) : String(S.result.base)) : "", error: S.err ? S.err.msg : "", screen: S.screen }; },
      keys(seq) { for (const k of seq.split(" ")) { if (k === "<") arrow("left"); else if (k === ">") arrow("right"); else if (k === "^") arrow("up"); else if (k === "v") arrow("down"); else press(k); } },
    },
    dispose() { document.removeEventListener("keydown", onKeyDown); host.innerHTML = ""; },
  };
}
