/**
 * Interactive world map (Canvas 2D). mountGeoMap(host) builds the UI inside `host`,
 * loads /assets/data/world.json (Natural Earth, built by tools/build-world-data.mjs)
 * and returns { dispose() }.
 */
import * as G from "/assets/vendor/geo/geo-lib.js";
import { UI, TYPE, CONT, SUB_AR, CONT_BOX, ARAB, LAYER_OF, LAYER_SWATCH, REGION_STYLE, palette, THEME } from "./geo-data.js";

const R_EARTH = 6371;
const ACCENT = "#19d3c0";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const ICON = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>', quiz: '<path d="M9 9a3 3 0 1 1 4.5 2.6c-1 .6-1.5 1.1-1.5 2.4M12 17.5v.01"/><circle cx="12" cy="12" r="9.5"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>', globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3.2 3 3.2 15 0 18M12 3c-3.2 3-3.2 15 0 18"/>',
  flat: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M8 5v14M16 5v14M3 12h18"/>', paint: '<path d="M12 3a9 9 0 1 0 0 18c1.4 0 2-1 2-2 0-1.6-1-1.7-1-3 0-1 .8-2 2-2h2a4 4 0 0 0 4-4c0-4-4-7-9-7Z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7" r="1"/>',
  reset: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>', full: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>', close: '<path d="M6 6l12 12M18 6 6 18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>', minus: '<path d="M5 12h14"/>',
};
const icon = (n, s = 20) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[n]}</svg>`;

export async function mountGeoMap(host, opts = {}) {
  const lang = opts.lang || (document.documentElement.lang === "ar" ? "ar" : "en");
  const T = UI[lang], TY = TYPE[lang], dir = lang === "ar" ? "rtl" : "ltr";
  const nf = new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US");

  host.innerHTML = `
  <div class="gm-root" dir="${dir}">
    <canvas class="gm-canvas"></canvas>
    <div class="gm-top"><div class="gm-chips"></div></div>
    <div class="gm-tools">
      <button data-t="search" title="${T.search}">${icon("search")}</button>
      <button data-t="quiz" title="${T.quiz}">${icon("quiz")}</button>
      <button data-t="layers" title="${T.layers}">${icon("layers")}</button>
      <button data-t="proj" title="${T.globe}">${icon("globe")}</button>
      <button data-t="color" title="${T.colorMode}">${icon("paint")}</button>
      <button data-t="reset" title="${T.reset}">${icon("reset")}</button>
      <button data-t="full" title="${T.fullscreen}">${icon("full")}</button>
    </div>
    <div class="gm-zoom"><button data-z="1" title="${T.zoomIn}">${icon("plus")}</button><button data-z="-1" title="${T.zoomOut}">${icon("minus")}</button></div>
    <aside class="gm-layers"></aside>
    <div class="gm-hint">${T.hint}</div>
    <div class="gm-coord"></div>
    <div class="gm-credit">${T.attribution}</div>
    <div class="gm-tip" hidden></div>
    <aside class="gm-card" hidden></aside>
    <aside class="gm-search" hidden><div class="gm-search-head"><input type="search" placeholder="${T.search}" autocomplete="off"><button class="gm-x" aria-label="${T.close}">${icon("close", 18)}</button></div><div class="gm-list"></div></aside>
    <div class="gm-quiz" hidden></div>
    <div class="gm-loading"><div class="gm-spin"></div><p>${T.loading}</p></div>
  </div>`;
  const root = host.querySelector(".gm-root");
  const $ = (s) => root.querySelector(s);
  const canvas = $(".gm-canvas"), ctx = canvas.getContext("2d");
  const loading = $(".gm-loading");

  /* ------------------------------------------------------------------ data */
  let data;
  try { data = await (await fetch("/assets/data/world.json")).json(); } catch { loading.innerHTML = `<p>${T.failed}</p>`; return { dispose() { host.innerHTML = ""; } }; }
  try { await document.fonts?.ready; } catch { /* ignore */ }
  const topo = data.topo, feat = (k) => G.feature(topo, topo.objects[k]).features;
  const countriesF = feat("countries"), borders = G.mesh(topo, topo.objects.countries, (a, b) => a !== b);
  const nbr = G.neighbors(topo.objects.countries.geometries);
  const items = [], byId = new Map();
  const push = (it) => { it.id = it.id; items.push(it); byId.set(it.id, it); return it; };
  countriesF.forEach((f, i) => push({ id: "c:" + f.id, cat: "country", type: "country", f, p: f.properties, bb: f.properties.bb, ar: f.properties.a, en: f.properties.n, idx: i }));
  feat("marine").forEach((f) => push({ id: "w:" + f.properties.n + f.properties.t, cat: "water", type: f.properties.t, f, p: f.properties, bb: f.properties.bb, ar: f.properties.a, en: f.properties.n }));
  feat("rivers").forEach((f) => push({ id: "r:" + f.properties.n, cat: "river", type: f.properties.k, f, p: f.properties, bb: f.properties.bb, ar: f.properties.a, en: f.properties.n }));
  feat("lakes").forEach((f) => push({ id: "l:" + f.properties.n, cat: "lake", type: "lake", f, p: f.properties, bb: f.properties.bb, ar: f.properties.a, en: f.properties.n }));
  feat("regions").forEach((f) => push({ id: "g:" + f.properties.n + f.properties.t, cat: f.properties.t, type: f.properties.t, f, p: f.properties, bb: f.properties.bb, ar: f.properties.a, en: f.properties.n }));
  data.peaks.forEach((p, i) => push({ id: "p:" + i, cat: "peak", type: p.k, pt: [p.x, p.y], p, ar: p.a, en: p.n }));
  data.cities.forEach((p, i) => push({ id: "t:" + i, cat: "city", type: p.cap ? "capital" : "city", pt: [p.x, p.y], p, ar: p.a, en: p.n }));
  const nm = (it) => (lang === "ar" ? it.ar : it.en) || it.en;
  const nm2 = (it) => (lang === "ar" ? it.en : it.ar);
  const countryByA3 = new Map(items.filter((i) => i.cat === "country").map((i) => [i.p.i, i]));
  const cname = (a3) => { const c = countryByA3.get(a3); return c ? nm(c) : a3; };
  const rank = (it) => it.p.r ?? 3;
  const bbCenter = (bb) => { const x1 = bb[0] <= bb[2] ? bb[2] : bb[2] + 360; let cx = (bb[0] + x1) / 2; if (cx > 180) cx -= 360; return [cx, (bb[1] + bb[3]) / 2]; };
  const inBB = (bb, [x, y], pad = 0) => y >= bb[1] - pad && y <= bb[3] + pad && (bb[0] <= bb[2] ? x >= bb[0] - pad && x <= bb[2] + pad : x >= bb[0] - pad || x <= bb[2] + pad);
  const pcount = (cat) => items.filter((i) => i.cat === cat);
  const polyItems = items.filter((i) => i.f && i.cat !== "river");
  const regionCats = ["mountain", "plateau", "desert", "plain", "basin", "delta", "valley", "peninsula", "isthmus"];
  const regionItems = items.filter((i) => regionCats.includes(i.cat)).sort((a, b) => (b.p.bb ? 1 : 0) - (a.p.bb ? 1 : 0));
  regionItems.sort((a, b) => G.geoArea(b.f) - G.geoArea(a.f));
  const waterItems = pcount("water"), lakeItems = pcount("lake"), riverItems = pcount("river"), peakItems = pcount("peak"), cityItems = pcount("city"), countryItems = pcount("country");

  /* ----------------------------------------------------------------- state */
  const S = {
    mode: "flat", k: 1, tx: 0, ty: 0, lon: 30, lat: 22, cont: null, colorMode: "continent", sel: null, hover: null, others: [],
    layers: { countries: true, borders: true, graticule: true, water: true, rivers: true, lakes: true, mountains: true, plateaus: true, deserts: true, lowlands: false, peninsulas: false, peaks: true, cities: true },
  };
  const quiz = { on: false, cats: [], pool: [], i: 0, score: 0, tries: 0, N: 10, target: null, locked: false, phase: "pick" };
  let W = 800, H = 500, dpr = 1, s0 = 1, baseT = [400, 250], globeR = 220, dirty = true, lite = 0, anim = null, alive = true, raf = 0;
  const flat = G.geoNaturalEarth1(), globe = G.geoOrthographic().clipAngle(90);
  const proj = () => (S.mode === "flat" ? flat : globe);
  const isDark = () => document.documentElement.dataset.theme === "dark";
  const th = () => (isDark() ? THEME.dark : THEME.light);

  function resize() {
    W = host.clientWidth || 800; H = host.clientHeight || 500; dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    flat.fitExtent([[8, 58], [W - 8, H - 22]], { type: "Sphere" });
    s0 = flat.scale(); baseT = flat.translate().slice(); globeR = Math.min(W, H * 1.02) * 0.42;
    applyProj(); dirty = true;
  }
  function applyProj() {
    if (S.mode === "flat") {
      flat.scale(s0 * S.k).translate([baseT[0] + S.tx, baseT[1] + S.ty]);
      const l = flat([-180, 0])[0], r = flat([180, 0])[0], t = flat([0, 90])[1], b = flat([0, -90])[1];
      let dx = 0, dy = 0; const mw = r - l, mh = b - t;
      if (mw <= W - 60) dx = W / 2 - (l + r) / 2; else { if (l > 30) dx = 30 - l; if (r < W - 30) dx = W - 30 - r; }
      if (mh <= H - 90) dy = (H + 36) / 2 - (t + b) / 2; else { if (t > 60) dy = 60 - t; if (b < H - 20) dy = H - 20 - b; }
      if (dx || dy) { S.tx += dx; S.ty += dy; flat.translate([baseT[0] + S.tx, baseT[1] + S.ty]); }
    } else {
      globe.scale(globeR * S.k).translate([W / 2, H / 2 + 14]).rotate([-S.lon, -S.lat, 0]);
    }
  }
  const markDirty = (interacting = false) => { dirty = true; if (interacting) lite = performance.now() + 160; };

  /* ------------------------------------------------------- view animations */
  function viewForBox(bb) {
    const [x0, y0, x1r, y1] = bb, x1 = x0 <= x1r ? x1r : x1r + 360;
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, wx = Math.max(x1 - x0, 1), wy = Math.max(y1 - y0, 1);
    if (S.mode === "globe") {
      const ang = Math.max(wx * Math.cos((cy * Math.PI) / 180), wy) * (Math.PI / 180);
      const k = clamp(0.75 / Math.sin(clamp(ang / 2 + 0.05, 0.02, 1.5)) * 0.5, 1, 40);
      return { k, lon: cx > 180 ? cx - 360 : cx, lat: cy };
    }
    const t = G.geoNaturalEarth1().fitExtent([[8, 58], [W - 8, H - 22]], { type: "Sphere" });
    const pts = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [cx, cy]].map(([x, y]) => t([x > 180 ? x - 360 : x, y]));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const bw = Math.max(Math.max(...xs) - Math.min(...xs), 30), bh = Math.max(Math.max(...ys) - Math.min(...ys), 30);
    const k = clamp(Math.min((W * 0.62) / bw, (H * 0.55) / bh), 1, 70);
    const c = pts[4];
    return { k, tx: -k * (c[0] - baseT[0]), ty: -k * (c[1] - baseT[1]) };
  }
  function flyTo(v, ms = 900) {
    anim = { t0: performance.now(), ms, from: { k: S.k, tx: S.tx, ty: S.ty, lon: S.lon, lat: S.lat }, to: { k: v.k ?? S.k, tx: v.tx ?? S.tx, ty: v.ty ?? S.ty, lon: v.lon ?? S.lon, lat: v.lat ?? S.lat } };
    if (S.mode === "globe") { let d = anim.to.lon - anim.from.lon; if (d > 180) anim.to.lon -= 360; if (d < -180) anim.to.lon += 360; }
  }
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const home = () => (S.mode === "flat" ? { k: 1, tx: 0, ty: 0 } : { k: 1, lon: 30, lat: 22 });
  const flyBox = (bb) => flyTo(viewForBox(bb));
  function flyItem(it) {
    if (it.pt) { const [x, y] = it.pt; return flyBox([x - 3, y - 2, x + 3, y + 2]); }
    const bb = it.bb; const w = bb[0] <= bb[2] ? bb[2] - bb[0] : bb[2] + 360 - bb[0];
    if (it.cat === "country" && w > 150) { const [lx, ly] = it.p.lp; return flyBox([lx - 25, ly - 14, lx + 25, ly + 14]); }
    flyBox(bb);
  }

  /* ------------------------------------------------------------ patterns */
  const patterns = {};
  function pattern(kind, color) {
    const key = kind + color; if (patterns[key]) return patterns[key];
    const c = document.createElement("canvas"); c.width = c.height = 14; const g = c.getContext("2d"); g.strokeStyle = color; g.fillStyle = color; g.lineWidth = 1.3; g.globalAlpha = 0.9;
    if (kind === "mount") { g.beginPath(); g.moveTo(2, 11); g.lineTo(7, 3); g.lineTo(12, 11); g.stroke(); }
    else if (kind === "lines") { g.beginPath(); g.moveTo(0, 4); g.lineTo(14, 4); g.moveTo(0, 11); g.lineTo(14, 11); g.stroke(); }
    else { g.beginPath(); g.arc(4, 4, 1.1, 0, 7); g.arc(11, 10, 1.1, 0, 7); g.fill(); }
    return (patterns[key] = ctx.createPattern(c, "repeat"));
  }

  /* ---------------------------------------------------------------- render */
  const lineDefs = [["eq", 0, "lat"], ["cancer", 23.4366, "lat"], ["capricorn", -23.4366, "lat"], ["arctic", 66.5634, "lat"], ["antarctic", -66.5634, "lat"], ["pm", 0, "lon"], ["idl", 180, "lon"]];
  const lineGeo = (kind, v) => { const pts = []; if (kind === "lat") for (let x = -180; x <= 180; x += 3) pts.push([x, v]); else for (let y = -90; y <= 90; y += 3) pts.push([v === 180 ? 179.999 : v, y]); return { type: "LineString", coordinates: pts }; };
  const specialLines = lineDefs.map(([id, v, kind]) => ({ id, v, kind, geo: lineGeo(kind, v) }));
  const grat = G.geoGraticule().step([30, 30])();
  const layerOn = (id) => S.layers[id] || (quiz.on && quiz.need?.has(id));
  const kmPerPx = () => R_EARTH / proj().scale();
  const centerPt = () => (S.mode === "globe" ? [S.lon, S.lat] : null);
  const visiblePt = (pt) => (S.mode === "globe" ? G.geoDistance(pt, [S.lon, S.lat]) < 1.3 : true);
  const toXY = (pt) => (visiblePt(pt) ? proj()(pt) : null);
  const onScreen = (xy, m = 20) => xy && xy[0] > -m && xy[0] < W + m && xy[1] > -m && xy[1] < H + m;

  function fillColorOf(it, pal) {
    if (S.colorMode === "political") return pal[((it.p.mc ?? 1) - 1 + 7) % 7];
    return pal[it.p.ct] ?? pal[0];
  }

  function render() {
    const t = th(), P = proj(), path = G.geoPath(P, ctx), fast = performance.now() < lite;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const pal = palette(isDark(), S.colorMode);
    /* background */
    if (S.mode === "flat") {
      const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, t.ocean[0]); g.addColorStop(1, t.ocean[1]);
      ctx.fillStyle = g; ctx.beginPath(); path({ type: "Sphere" }); ctx.fill(); ctx.strokeStyle = t.coast; ctx.globalAlpha = 0.5; ctx.lineWidth = 1; ctx.stroke(); ctx.globalAlpha = 1;
    } else {
      const cx = W / 2, cy = H / 2 + 14, r = globe.scale();
      const halo = ctx.createRadialGradient(cx, cy, r * 0.98, cx, cy, r * 1.16); halo.addColorStop(0, "rgba(90,190,255,.35)"); halo.addColorStop(1, "rgba(90,190,255,0)");
      ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(cx, cy, r * 1.16, 0, 7); ctx.fill();
      const g = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.1, cx, cy, r); g.addColorStop(0, t.ocean[0]); g.addColorStop(1, t.ocean[1]);
      ctx.fillStyle = g; ctx.beginPath(); path({ type: "Sphere" }); ctx.fill();
    }
    /* graticule */
    if (layerOn("graticule")) {
      ctx.strokeStyle = t.grat; ctx.lineWidth = 0.7; ctx.beginPath(); path(grat); ctx.stroke();
      ctx.lineWidth = 1.1; ctx.strokeStyle = t.line; ctx.setLineDash([6, 4]);
      for (const l of specialLines) { ctx.beginPath(); path(l.geo); ctx.stroke(); }
      ctx.setLineDash([]);
    }
    /* selected water body highlight (under the land) */
    const sel = S.sel, hov = S.hover;
    for (const it of [sel, hov]) if (it && it.cat === "water") { ctx.fillStyle = "rgba(25,211,192,.30)"; ctx.beginPath(); path(it.f); ctx.fill(); }
    /* countries */
    if (layerOn("countries")) {
      const groups = new Map();
      for (const it of countryItems) {
        const dim = S.cont !== null && it.p.ct !== S.cont; const col = fillColorOf(it, pal), key = col + (dim ? "d" : "");
        if (!groups.has(key)) groups.set(key, { col, dim, list: [] }); groups.get(key).list.push(it);
      }
      for (const { col, dim, list } of groups.values()) {
        ctx.globalAlpha = dim ? 0.28 : 1; ctx.fillStyle = col; ctx.beginPath(); for (const it of list) path(it.f); ctx.fill();
        ctx.lineWidth = layerOn("borders") ? 0.7 : 0.3; ctx.strokeStyle = layerOn("borders") ? t.border : t.coast; ctx.stroke();
      }
      ctx.globalAlpha = 1;
      if (layerOn("borders")) { ctx.lineWidth = 0.55; ctx.strokeStyle = t.coast; ctx.globalAlpha = 0.55; ctx.beginPath(); path(borders); ctx.stroke(); ctx.globalAlpha = 1; }
    }
    /* highlights */
    const drawHL = (it, a, w) => {
      if (!it) return;
      if (it.cat === "country") { ctx.fillStyle = `rgba(25,211,192,${a})`; ctx.beginPath(); path(it.f); ctx.fill(); ctx.strokeStyle = ACCENT; ctx.lineWidth = w; ctx.stroke(); }
    };
    if (S.sel && S.sel.cat === "country") S.sel.p && nbr[S.sel.idx].forEach((j) => { ctx.fillStyle = "rgba(25,211,192,.12)"; ctx.beginPath(); path(countryItems[j].f); ctx.fill(); });
    drawHL(S.hover !== S.sel ? S.hover : null, 0.22, 1.4); drawHL(S.sel, 0.38, 2.2);
    /* regions */
    if (!fast) {
      for (const it of regionItems) {
        const lid = LAYER_OF[it.cat]; if (!layerOn(lid)) continue;
        const st = REGION_STYLE[it.cat], isSel = it === S.sel || it === S.hover;
        ctx.globalAlpha = isSel ? Math.min(1, st.a + 0.3) : st.a; ctx.fillStyle = st.fill; ctx.beginPath(); path(it.f); ctx.fill();
        if (st.pattern) { ctx.globalAlpha = isSel ? 0.9 : 0.4; ctx.fillStyle = pattern(st.pattern, st.stroke); ctx.fill(); }
        ctx.globalAlpha = isSel ? 1 : 0.55; ctx.strokeStyle = st.stroke; ctx.lineWidth = isSel ? 1.8 : 0.7; ctx.setLineDash(isSel ? [] : [3, 3]); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
      }
    }
    /* lakes */
    if (layerOn("lakes")) { ctx.fillStyle = t.lake; ctx.strokeStyle = t.river; ctx.lineWidth = 0.6; ctx.beginPath(); for (const it of lakeItems) path(it.f); ctx.fill(); ctx.stroke();
      for (const it of [S.sel, S.hover]) if (it && it.cat === "lake") { ctx.strokeStyle = ACCENT; ctx.lineWidth = 2.2; ctx.beginPath(); path(it.f); ctx.stroke(); } }
    /* rivers */
    if (layerOn("rivers")) {
      const kk = Math.max(S.k, 0.5), widen = 1 + 0.22 * Math.log2(kk);
      for (const it of riverItems) {
        const r = rank(it), minK = r <= 2 ? 0 : r === 3 ? 1.35 : 2.4; if (S.k < minK && it !== S.sel && it !== S.hover) continue;
        const isSel = it === S.sel || it === S.hover, canal = it.type === "canal";
        ctx.strokeStyle = isSel ? ACCENT : canal ? "#e0883a" : t.river; ctx.lineWidth = (isSel ? 3 : (r <= 1 ? 1.7 : r === 2 ? 1.3 : 1) * widen) * (canal ? 1.15 : 1);
        ctx.setLineDash(canal ? [5, 3] : []); ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); path(it.f); ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    /* points: peaks + cities */
    const pts = [];
    if (layerOn("peaks") && !fast) for (const it of peakItems) { if (S.k < 2.2 && it !== S.sel && it !== S.hover && !(quiz.on && quiz.cats.includes("peaks"))) continue; const xy = toXY(it.pt); if (onScreen(xy)) pts.push({ it, xy }); }
    if (layerOn("cities") && !fast) for (const it of cityItems) {
      const minK = it.p.cap ? (it.p.p > 6e6 ? 1.2 : 2.2) : it.p.c === "EGY" ? 3 : 3.5; if (S.k < minK && it !== S.sel) continue;
      const xy = toXY(it.pt); if (onScreen(xy)) pts.push({ it, xy });
    }
    for (const { it, xy } of pts) {
      const isSel = it === S.sel || it === S.hover; ctx.save(); ctx.translate(xy[0], xy[1]);
      if (it.cat === "peak") {
        const dep = it.type === "depression"; ctx.beginPath(); const s = isSel ? 8 : 5.5;
        if (dep) { ctx.moveTo(-s, -s * 0.7); ctx.lineTo(s, -s * 0.7); ctx.lineTo(0, s); } else { ctx.moveTo(-s, s * 0.8); ctx.lineTo(s, s * 0.8); ctx.lineTo(0, -s); }
        ctx.closePath(); ctx.fillStyle = isSel ? ACCENT : dep ? "#2aa5a0" : "#7a4f3a"; ctx.fill(); ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.2; ctx.stroke();
      } else {
        ctx.beginPath(); ctx.arc(0, 0, isSel ? 6 : it.p.cap ? 3.6 : 2.6, 0, 7); ctx.fillStyle = isSel ? ACCENT : it.p.cap ? "#e8505b" : "#555"; ctx.fill(); ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.2; ctx.stroke();
        if (it.p.cap) { ctx.beginPath(); ctx.arc(0, 0, 6, 0, 7); ctx.strokeStyle = "rgba(232,80,91,.55)"; ctx.lineWidth = 1; ctx.stroke(); }
      }
      ctx.restore();
    }
    if (!fast) drawLabels(t, pts);
    drawGlobeRim();
    drawScale(t);
  }
  function drawGlobeRim() {
    if (S.mode !== "globe") return;
    const cx = W / 2, cy = H / 2 + 14, r = globe.scale(); ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke();
  }

  /* ---------------------------------------------------------------- labels */
  const hideNames = (cat) => quiz.on && quiz.phase === "play" && ((quiz.catsHit || []).includes(cat) || (cat === "capital" && quiz.cats.includes("capitals")));
  function drawLabels(t, pts) {
    const placed = []; const P = proj();
    const fits = (x, y, w, h) => { if (x < 4 || y < 54 || x + w > W - 4 || y + h > H - 18) return false; for (const r of placed) if (x < r.x + r.w && x + w > r.x && y < r.y + r.h && y + h > r.y) return false; return true; };
    const text = (str, cx, cy, o = {}) => {
      const size = o.size || 12; ctx.font = `${o.weight || 700} ${o.italic ? "italic " : ""}${size}px Cairo, system-ui, sans-serif`;
      if ("letterSpacing" in ctx) ctx.letterSpacing = o.spacing ? o.spacing + "px" : "0px";
      const w = ctx.measureText(str).width + 4, h = size + 4, x = cx - w / 2, y = cy - h / 2;
      if (!o.force && !fits(x, y, w, h)) return false;
      placed.push({ x, y, w, h }); ctx.textAlign = "center"; ctx.textBaseline = "middle";
      if (o.angle) { ctx.save(); ctx.translate(cx, cy); ctx.rotate(o.angle); cx = 0; cy = 0; }
      ctx.lineJoin = "round"; ctx.lineWidth = 3.2; ctx.strokeStyle = t.halo; ctx.strokeText(str, cx, cy); ctx.fillStyle = o.color || t.text; ctx.fillText(str, cx, cy);
      if (o.angle) ctx.restore();
      return true;
    };
    const cand = [];
    const sc = P.scale(), kpp = R_EARTH / sc;
    /* selected first so it always shows */
    const selList = [S.sel, S.hover].filter(Boolean);
    for (const it of selList) {
      const xy = it.pt ? toXY(it.pt) : toXY(labelPtOf(it)); if (!onScreen(xy, -4)) continue;
      cand.push({ pr: 1e9, str: nm(it), xy, o: { size: 14, weight: 800, color: "#fff", force: true, bg: true } });
    }
    /* water */
    if (layerOn("water")) for (const it of waterItems) {
      if (hideNames("water")) break; const r = it.p.r; const minK = r === 0 ? 0 : r <= 1 ? 1.1 : r === 2 ? 1.8 : r === 3 ? 3 : 5; if (S.k < minK) continue;
      const lps = it.type === "ocean" ? it.p.lp : [it.p.lp[0]];
      lps.forEach((lp) => { const xy = toXY(lp); if (onScreen(xy)) cand.push({ pr: 800 - r * 60, str: nm(it), xy, o: { size: r === 0 ? 17 : r <= 1 ? 13.5 : 12, italic: true, weight: 600, color: t.waterText, spacing: r === 0 ? 3 : 1 } }); });
    }
    /* countries */
    if (layerOn("countries") && !hideNames("country") && true) for (const it of countryItems) {
      if (it === S.sel || it === S.hover) continue; const d = Math.sqrt(it.p.ak) / kpp; if (d < 34) continue;
      const xy = toXY(it.p.lp); if (!onScreen(xy)) continue; const dim = S.cont !== null && it.p.ct !== S.cont;
      cand.push({ pr: 600 + Math.log(it.p.ak + 1), str: nm(it), xy, o: { size: clamp(9 + d / 28, 10, 15.5), weight: 700, color: dim ? "rgba(120,130,140,.6)" : t.text, spacing: d > 220 ? 1.5 : 0 } });
    }
    /* mountains etc. regions */
    for (const it of regionItems) {
      const lid = LAYER_OF[it.cat]; if (!layerOn(lid) || hideNames(it.cat)) continue; const r = rank(it);
      const minK = r <= 1 ? 1.4 : r === 2 ? 2.2 : r === 3 ? 3.2 : 4.5; if (S.k < minK) continue;
      const xy = toXY(it.p.lp); if (!onScreen(xy)) continue; const st = REGION_STYLE[it.cat];
      cand.push({ pr: 500 - r * 20, str: nm(it), xy, o: { size: 11.5, italic: it.cat !== "mountain", weight: 700, color: isDark() ? "#e8d4c4" : st.stroke } });
    }
    /* lakes + rivers */
    if (layerOn("lakes") && !hideNames("lake")) for (const it of lakeItems) { if (S.k < 2.4 && it.p.ak < 20000) continue; const xy = toXY(it.p.lp); if (onScreen(xy)) cand.push({ pr: 450, str: nm(it), xy, o: { size: 11, italic: true, color: t.waterText } }); }
    if (layerOn("rivers") && !hideNames("river")) for (const it of riverItems) {
      const r = rank(it); const minK = r <= 1 ? 1.2 : r === 2 ? 1.9 : r === 3 ? 2.8 : 4.2; if (S.k < minK) continue;
      const lab = riverLabel(it); if (!lab) continue; cand.push({ pr: 470 - r * 10, str: nm(it), xy: lab.xy, o: { size: 11, italic: true, weight: 600, color: it.type === "canal" ? "#c46a1b" : t.waterText, angle: lab.angle } });
    }
    /* points */
    for (const { it, xy } of pts) {
      if (it.cat === "peak") { if (S.k < 2.6 && it !== S.sel) continue; if (hideNames("peak")) continue; cand.push({ pr: 420, str: `${nm(it)} ${nf.format(it.p.e)}${T.meters}`, xy: [xy[0], xy[1] - 13], o: { size: 11, color: isDark() ? "#f1cdb8" : "#6d4c41" } }); }
      else { if (it.p.cap && hideNames("capital")) continue; cand.push({ pr: it.p.cap ? 440 + Math.log(it.p.p + 1) : 380 + Math.log(it.p.p + 1), str: nm(it), xy: [xy[0], xy[1] - 11], o: { size: it.p.cap ? 11.5 : 10.5, weight: it.p.cap ? 700 : 600, color: t.text } }); }
    }
    cand.sort((a, b) => b.pr - a.pr);
    for (const c of cand) {
      if (c.o.bg) {
        ctx.font = `800 14px Cairo, system-ui, sans-serif`; const w = ctx.measureText(c.str).width + 18, x = clamp(c.xy[0] - w / 2, 6, W - w - 6), y = clamp(c.xy[1] - 34, 60, H - 40);
        ctx.fillStyle = "rgba(10,40,48,.88)"; ctx.beginPath(); ctx.roundRect?.(x, y, w, 24, 12); if (!ctx.roundRect) ctx.rect(x, y, w, 24); ctx.fill();
        ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(c.str, x + w / 2, y + 12.5); placed.push({ x, y, w, h: 24 }); continue;
      }
      text(c.str, c.xy[0], c.xy[1], c.o);
    }
    if ("letterSpacing" in ctx) ctx.letterSpacing = "0px";
    /* line names (equator, tropics …) */
    if (layerOn("graticule") && S.k >= 1) {
      for (const l of specialLines) {
        const pt = l.kind === "lat" ? [S.mode === "globe" ? S.lon - 22 : -168, l.v] : [l.v === 180 ? 179 : l.v, S.mode === "globe" ? S.lat + 28 : 62]; const xy = toXY(pt); if (!onScreen(xy, -10)) continue;
        text(T.lines[l.id], xy[0], xy[1] - 8, { size: 10, italic: true, weight: 600, color: isDark() ? "#ffb59d" : "#c0452d", force: false });
      }
    }
  }
  function labelPtOf(it) { return it.p.lp ? (Array.isArray(it.p.lp[0]) ? it.p.lp[0] : it.p.lp) : bbCenter(it.bb); }
  function riverLabel(it) {
    const lines = it.f.geometry.coordinates; let best = null, bl = 0;
    for (const ln of lines) { if (ln.length > bl) { bl = ln.length; best = ln; } }
    if (!best) return null; const i = Math.floor(best.length / 2), a = toXY(best[Math.max(0, i - 2)]), b = toXY(best[Math.min(best.length - 1, i + 2)]), m = toXY(best[i]);
    if (!a || !b || !m || !onScreen(m)) return null; let ang = Math.atan2(b[1] - a[1], b[0] - a[0]); if (ang > Math.PI / 2) ang -= Math.PI; if (ang < -Math.PI / 2) ang += Math.PI;
    return { xy: [m[0], m[1] - 7], angle: clamp(ang, -0.9, 0.9) };
  }
  function drawScale(t) {
    const P = proj(), cx = W / 2, cy = H / 2, a = P.invert([cx - 40, cy]), b = P.invert([cx + 40, cy]); if (!a || !b) return;
    const km = G.geoDistance(a, b) * R_EARTH, per = km / 80, nice = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]; let len = nice[0];
    for (const n of nice) if (n / per <= 120) len = n; const px = len / per, x = 16, y = H - 16;
    ctx.strokeStyle = t.text; ctx.fillStyle = t.text; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.lineTo(x, y); ctx.lineTo(x + px, y); ctx.lineTo(x + px, y - 5); ctx.stroke();
    ctx.font = "700 11px Cairo, system-ui, sans-serif"; ctx.textAlign = "left"; ctx.textBaseline = "bottom"; ctx.lineWidth = 3; ctx.strokeStyle = t.halo; const s = `${nf.format(len)} ${T.km}`; ctx.strokeText(s, x + px + 6, y + 1); ctx.fillText(s, x + px + 6, y + 1);
  }

  /* ----------------------------------------------------------- hit testing */
  const distSeg = (px, py, a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy; let tt = l2 ? ((px - a[0]) * dx + (py - a[1]) * dy) / l2 : 0; tt = clamp(tt, 0, 1); return Math.hypot(px - a[0] - tt * dx, py - a[1] - tt * dy); };
  function hitAt(sx, sy, only) {
    const P = proj(), geo = P.invert([sx, sy]), out = [];
    const want = (c) => (!only || only.includes(c));
    if (quiz.on === false && S.mode === "globe" && !geo) return out;
    const near = (it, tol) => { const xy = toXY(it.pt); return xy ? Math.hypot(xy[0] - sx, xy[1] - sy) : 1e9; };
    if (want("peak") && layerOn("peaks")) peakItems.map((it) => ({ it, d: near(it) })).filter((x) => x.d < 11).sort((a, b) => a.d - b.d).forEach((x) => out.push(x.it));
    if (want("city") && layerOn("cities")) cityItems.filter((it) => (it.p.cap ? S.k >= (it.p.p > 6e6 ? 1.2 : 2.2) : S.k >= (it.p.c === "EGY" ? 3 : 3.5))).map((it) => ({ it, d: near(it) })).filter((x) => x.d < 9).sort((a, b) => a.d - b.d).forEach((x) => out.push(x.it));
    if (want("river") && layerOn("rivers")) {
      const margin = 10 / Math.max(P.scale() / 57.3, 0.5) + 1, found = [];
      for (const it of riverItems) {
        const r = rank(it), minK = r <= 2 ? 0 : r === 3 ? 1.35 : 2.4; if (S.k < minK) continue; if (geo && !inBB(it.bb, geo, margin)) continue;
        let best = 1e9; for (const ln of it.f.geometry.coordinates) { let prev = null; for (let i = 0; i < ln.length; i += 1) { const xy = toXY(ln[i]); if (xy && prev) best = Math.min(best, distSeg(sx, sy, prev, xy)); prev = xy; } }
        if (best < 7) found.push({ it, d: best });
      }
      found.sort((a, b) => a.d - b.d).forEach((x) => out.push(x.it));
    }
    if (!geo) return out;
    if (want("lake") && layerOn("lakes")) for (const it of lakeItems) if (inBB(it.bb, geo) && G.geoContains(it.f, geo)) out.push(it);
    const regs = []; for (const it of regionItems) if (want(it.cat) && layerOn(LAYER_OF[it.cat]) && inBB(it.bb, geo) && G.geoContains(it.f, geo)) regs.push(it);
    regs.sort((a, b) => G.geoArea(a.f) - G.geoArea(b.f)).forEach((x) => out.push(x));
    if (want("country") && layerOn("countries")) for (const it of countryItems) if (inBB(it.bb, geo) && G.geoContains(it.f, geo)) out.push(it);
    if (want("water") && layerOn("water")) { const w = []; for (const it of waterItems) if (inBB(it.bb, geo) && G.geoContains(it.f, geo)) w.push(it); w.sort((a, b) => b.p.r - a.p.r).forEach((x) => out.push(x)); }
    return out;
  }

  /* ------------------------------------------------------------------ card */
  const card = $(".gm-card");
  const fmtPop = (n) => (n >= 1e9 ? `${(n / 1e9).toFixed(1)} ${T.billion}` : n >= 1e6 ? `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)} ${T.million}` : n >= 1e3 ? `${nf.format(Math.round(n / 1e3))} ${T.thousand}` : nf.format(n));
  const list = (codes) => codes.map(cname).join(lang === "ar" ? "، " : ", ");
  function rows(it) {
    const p = it.p, r = [];
    if (it.cat === "country") {
      const caps = data.cities.filter((c) => c.c === p.i && c.cap).map((c) => (lang === "ar" ? c.a : c.n));
      if (caps.length) r.push([T.capital, caps.join(lang === "ar" ? "، " : ", ")]);
      r.push([T.continent, CONT[lang][p.ct]]); const sub = data.meta.subregions[p.sr]; r.push([T.region, lang === "ar" ? SUB_AR[sub] || sub : sub]);
      if (p.p) r.push([T.population, fmtPop(p.p)]); r.push([T.area, `${nf.format(p.ak)} ${T.areaApprox}`]);
      const ns = nbr[it.idx].map((j) => nm(countryItems[j])); r.push([T.neighbors, ns.length ? ns.join(lang === "ar" ? "، " : ", ") : T.noNeighbors]);
    } else if (it.cat === "water") { if (p.c?.length) r.push([T.borders, list(p.c)]); }
    else if (it.cat === "river") { if (p.l) r.push([T.length, `≈ ${nf.format(p.l)} ${T.km}`]); if (p.c?.length) r.push([T.passes, list(p.c)]); }
    else if (it.cat === "lake") { r.push([T.area, `${nf.format(p.ak)} ${T.areaApprox}`]); if (p.c?.length) r.push([T.countriesHere, list(p.c)]); }
    else if (it.cat === "peak") { r.push([T.elevation, p.e < 0 ? `${nf.format(Math.abs(p.e))} ${T.meters} ${T.belowSea}` : `${nf.format(p.e)} ${T.meters}`]); if (p.c?.length) r.push([T.countriesHere, list(p.c)]); }
    else if (it.cat === "city") { r.push([T.population, fmtPop(p.p)]); r.push([T.countriesHere, cname(p.c)]); }
    else if (p.c?.length) r.push([T.countriesHere, list(p.c)]);
    return r;
  }
  function typeLabel(it) { return it.cat === "country" ? TY.country : TY[it.type] || TY[it.cat] || ""; }
  function select(it, others = [], fly = true) {
    S.sel = it; S.others = others.filter((o) => o !== it).slice(0, 5);
    card.innerHTML = `<button class="gm-x" aria-label="${T.close}">${icon("close", 18)}</button>
      <div class="gm-badge cat-${it.cat}">${esc(typeLabel(it))}</div><h3>${esc(nm(it))}</h3><p class="gm-sub">${esc(nm2(it) || "")}</p>
      <dl class="gm-rows">${rows(it).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
      ${S.others.length ? `<div class="gm-also"><span>${T.alsoHere}</span>${S.others.map((o) => `<button data-id="${esc(o.id)}">${esc(nm(o))}</button>`).join("")}</div>` : ""}`;
    card.hidden = false; card.classList.remove("pop"); void card.offsetWidth; card.classList.add("pop"); $(".gm-hint").classList.add("gone");
    if (fly) flyItem(it); markDirty();
  }
  const deselect = () => { S.sel = null; S.others = []; card.hidden = true; markDirty(); };
  card.addEventListener("click", (e) => {
    if (e.target.closest(".gm-x")) return deselect();
    const b = e.target.closest(".gm-also button"); if (b) { const it = byId.get(b.dataset.id); if (it) select(it, [S.sel, ...S.others]); }
  });

  /* ---------------------------------------------------------- interaction */
  const tip = $(".gm-tip"), coord = $(".gm-coord");
  const pointers = new Map(); let drag = null, pinch = null, downAt = null, hoverReq = null;
  const rect = () => canvas.getBoundingClientRect();
  function zoomAt(f, px, py) {
    const nk = clamp(S.k * f, 1, S.mode === "flat" ? 80 : 40); if (nk === S.k) return; anim = null;
    if (S.mode === "flat") { const real = nk / S.k; S.tx = px - baseT[0] - (px - baseT[0] - S.tx) * real; S.ty = py - baseT[1] - (py - baseT[1] - S.ty) * real; }
    S.k = nk; applyProj(); markDirty(true);
  }
  canvas.addEventListener("wheel", (e) => { e.preventDefault(); const r = rect(); zoomAt(Math.exp(-e.deltaY * 0.0016), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId); pointers.set(e.pointerId, { x: e.clientX, y: e.clientY }); downAt = { x: e.clientX, y: e.clientY, t: performance.now() }; anim = null;
    if (pointers.size === 1) drag = { x: e.clientX, y: e.clientY }; else if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) }; drag = null; }
  });
  canvas.addEventListener("pointermove", (e) => {
    const r = rect(), px = e.clientX - r.left, py = e.clientY - r.top; hoverReq = { x: px, y: py, cx: e.clientX, cy: e.clientY };
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinch && pointers.size === 2) { const [a, b] = [...pointers.values()], d = Math.hypot(a.x - b.x, a.y - b.y); zoomAt(d / pinch.d, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top); pinch.d = d; return; }
    if (drag && pointers.has(e.pointerId)) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
      if (S.mode === "flat") { S.tx += dx; S.ty += dy; } else { const f = (180 / Math.PI) / (globeR * S.k); S.lon = ((S.lon - dx * f + 540) % 360) - 180; S.lat = clamp(S.lat + dy * f, -85, 85); }
      applyProj(); markDirty(true); canvas.style.cursor = "grabbing";
    } else hover();
  });
  const endPtr = (e) => {
    pointers.delete(e.pointerId); if (pointers.size < 2) pinch = null; if (pointers.size === 0) drag = null; else if (pointers.size === 1) { const [p] = [...pointers.values()]; drag = { x: p.x, y: p.y }; }
    canvas.style.cursor = "grab";
  };
  canvas.addEventListener("pointerup", (e) => {
    const moved = downAt ? Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) : 99, dt = downAt ? performance.now() - downAt.t : 999; endPtr(e);
    if (moved < 6 && dt < 600) { const r = rect(); onTap(e.clientX - r.left, e.clientY - r.top); }
  });
  canvas.addEventListener("pointercancel", endPtr);
  canvas.addEventListener("dblclick", (e) => { const r = rect(); zoomAt(2.2, e.clientX - r.left, e.clientY - r.top); });
  canvas.addEventListener("pointerleave", () => { S.hover = null; tip.hidden = true; coord.textContent = ""; markDirty(); });
  function hover() {
    if (!hoverReq || quiz.on && false) return; const { x, y, cx } = hoverReq; hoverReq = null;
    const P = proj(), geo = P.invert([x, y]); coord.textContent = geo ? `${Math.abs(geo[1]).toFixed(1)}°${geo[1] >= 0 ? "N" : "S"}  ${Math.abs(geo[0]).toFixed(1)}°${geo[0] >= 0 ? "E" : "W"}` : "";
    const hits = hitAt(x, y, quiz.on ? quiz.cats.map(catOfQuiz).flat() : null), h = hits[0] || null;
    if (h !== S.hover) { S.hover = h; markDirty(); }
    canvas.style.cursor = h ? "pointer" : "grab";
    if (h && !quiz.on) { const r = root.getBoundingClientRect(); tip.textContent = nm(h); tip.hidden = false; tip.style.transform = `translate(${x + 14}px, ${y + 16}px)`; } else tip.hidden = true;
  }
  function onTap(x, y) {
    if (quiz.on) { answer(hitAt(x, y, quiz.catsHit)[0] || null); return; }
    const hits = hitAt(x, y); if (hits.length) select(hits[0], hits, false); else if (S.sel) deselect();
  }
  const onKey = (e) => {
    if (e.key === "Escape" && !document.fullscreenElement) { if (!searchBox.hidden) closeSearch(); else if (S.sel) deselect(); }
  };
  document.addEventListener("keydown", onKey);

  /* ------------------------------------------------------------------ UI */
  const chips = $(".gm-chips");
  chips.innerHTML = [`<button class="on" data-c="">${T.all}</button>`, ...CONT[lang].slice(0, 7).map((c, i) => `<button data-c="${i}">${c}</button>`)].join("");
  chips.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return; chips.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    S.cont = b.dataset.c === "" ? null : +b.dataset.c; deselect();
    if (S.cont === null) flyTo(home()); else flyBox(CONT_BOX[S.cont]); markDirty();
  });
  const layersBox = $(".gm-layers");
  const layerKeys = Object.keys(T.layer);
  layersBox.innerHTML = `<h4>${T.layers}</h4><div class="gm-lgrid">${layerKeys.map((k) => `<button data-l="${k}" class="${S.layers[k] ? "on" : ""}"><i style="--c:${LAYER_SWATCH[k]}"></i>${T.layer[k]}</button>`).join("")}</div>`;
  layersBox.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; const k = b.dataset.l; S.layers[k] = !S.layers[k]; b.classList.toggle("on", S.layers[k]); markDirty(); });
  const setTool = (n, on) => root.querySelector(`.gm-tools [data-t="${n}"]`)?.classList.toggle("on", on);
  layersBox.classList.add("shut"); setTool("layers", false);
  root.querySelector(".gm-tools").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return; const t = b.dataset.t;
    if (t === "layers") { layersBox.classList.toggle("shut"); setTool("layers", !layersBox.classList.contains("shut")); }
    else if (t === "proj") { switchMode(); }
    else if (t === "color") { S.colorMode = S.colorMode === "continent" ? "political" : "continent"; b.title = `${T.colorMode}: ${S.colorMode === "continent" ? T.byContinent : T.political}`; setTool("color", S.colorMode === "political"); markDirty(); }
    else if (t === "reset") { deselect(); chips.querySelector("button").click(); flyTo(home()); }
    else if (t === "full") { if (document.fullscreenElement) document.exitFullscreen(); else root.requestFullscreen?.(); }
    else if (t === "search") openSearch();
    else if (t === "quiz") quiz.on ? endQuiz() : startQuiz();
  });
  root.querySelector(".gm-zoom").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) zoomAt(+b.dataset.z > 0 ? 1.8 : 1 / 1.8, W / 2, H / 2); });
  function switchMode() {
    const toGlobe = S.mode === "flat"; let c = [S.lon, S.lat];
    if (toGlobe) { const g = flat.invert([W / 2, H / 2]); c = g || [30, 22]; }
    S.mode = toGlobe ? "globe" : "flat"; S.k = 1; S.tx = 0; S.ty = 0; if (toGlobe) { S.lon = c[0]; S.lat = clamp(c[1], -70, 70); }
    const btn = root.querySelector('[data-t="proj"]'); btn.innerHTML = icon(toGlobe ? "flat" : "globe"); btn.title = toGlobe ? T.flat : T.globe; setTool("proj", toGlobe);
    applyProj(); if (S.sel) flyItem(S.sel); markDirty();
  }

  /* search */
  const searchBox = $(".gm-search"), sList = $(".gm-list"), sInput = searchBox.querySelector("input");
  const norm = (s) => String(s || "").toLowerCase().replace(/[\u064B-\u065F\u0670]/g, "").replace(/[أإآ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه");
  const catOrder = ["country", "city", "water", "river", "lake", "mountain", "plateau", "desert", "peak", "plain", "basin", "delta", "valley", "peninsula", "isthmus"];
  const index = items.map((it) => ({ it, key: norm(`${it.ar} ${it.en}`) })).sort((a, b) => catOrder.indexOf(a.it.cat) - catOrder.indexOf(b.it.cat));
  function renderList(q) {
    const words = norm(q.trim()).split(/\s+/).filter(Boolean);
    const res = index.filter((x) => words.every((w) => x.key.includes(w))).sort((a, b) => (norm(nm(a.it)).startsWith(words[0] || "") ? 0 : 1) - (norm(nm(b.it)).startsWith(words[0] || "") ? 0 : 1)).slice(0, 60);
    sList.innerHTML = res.length ? res.map(({ it }) => `<button data-id="${esc(it.id)}"><i class="cat-${it.cat}"></i><b>${esc(nm(it))}</b><small>${esc(typeLabel(it))}</small></button>`).join("") : `<p class="none">${T.noResults}</p>`;
  }
  function openSearch() { if (quiz.on) return; searchBox.hidden = false; sInput.value = ""; renderList(""); setTimeout(() => sInput.focus(), 40); }
  const closeSearch = () => { searchBox.hidden = true; };
  sInput.addEventListener("input", () => renderList(sInput.value));
  searchBox.querySelector(".gm-x").addEventListener("click", closeSearch);
  sList.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return; const it = byId.get(b.dataset.id); closeSearch(); if (!it) return;
    const lid = LAYER_OF[it.cat]; if (lid && !S.layers[lid]) { S.layers[lid] = true; layersBox.querySelector(`[data-l="${lid}"]`)?.classList.add("on"); }
    select(it, []);
  });

  /* quiz */
  const quizUI = $(".gm-quiz");
  const QCATS = ["countries", "arab", "capitals", "water", "rivers", "land", "peaks"];
  const catOfQuiz = (c) => ({ countries: ["country"], arab: ["country"], capitals: ["country"], water: ["water"], rivers: ["river"], land: ["mountain", "plateau", "desert"], peaks: ["peak"] }[c] || []);
  const needLayers = (cats) => new Set(cats.flatMap((c) => ({ countries: ["countries"], arab: ["countries"], capitals: ["countries"], water: ["water"], rivers: ["rivers"], land: ["mountains", "plateaus", "deserts"], peaks: ["peaks"] }[c])));
  const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
  function startQuiz() {
    closeSearch(); deselect(); quiz.on = true; quiz.phase = "pick"; quiz.cats = []; setTool("quiz", true); root.classList.add("quizzing"); quizUI.hidden = false; renderQuizPick(); markDirty();
  }
  function renderQuizPick() {
    quizUI.innerHTML = `<div class="q-title">${T.quizPick}</div><div class="q-cats">${QCATS.map((c) => `<button data-qc="${c}" class="${quiz.cats.includes(c) ? "on" : ""}">${T.qc[c]}</button>`).join("")}</div>
      <div class="q-btns"><button data-q="go" ${quiz.cats.length ? "" : "disabled"}>${T.quiz}</button><button data-q="stop">${T.quizStop}</button></div>`;
  }
  function poolFor(c) {
    if (c === "countries") return countryItems.filter((i) => i.p.ak > 90000 || i.p.p > 15e6);
    if (c === "arab") return countryItems.filter((i) => ARAB.has(i.p.i));
    if (c === "capitals") return countryItems.filter((i) => data.cities.some((x) => x.c === i.p.i && x.cap) && (i.p.p > 8e6 || ARAB.has(i.p.i)));
    if (c === "water") return waterItems.filter((i) => i.p.r <= 2 && i.type !== "reef");
    if (c === "rivers") return riverItems.filter((i) => i.p.r <= 2 && i.type === "river" || i.id === "r:Suez Canal");
    if (c === "land") return regionItems.filter((i) => ["mountain", "plateau", "desert"].includes(i.cat) && i.p.r <= 2);
    if (c === "peaks") return peakItems.filter((i) => i.type === "peak");
    return [];
  }
  function beginQuiz() {
    quiz.pool = shuffle(quiz.cats.flatMap((c) => shuffle(poolFor(c)).slice(0, 6).map((it) => ({ it, c })))).slice(0, quiz.N);
    quiz.catsHit = [...new Set(quiz.cats.flatMap(catOfQuiz))]; quiz.need = needLayers(quiz.cats); quiz.i = 0; quiz.score = 0; quiz.phase = "play";
    S.cont = null; chips.querySelectorAll("button").forEach((x, i) => x.classList.toggle("on", i === 0)); flyTo(home()); ask(); markDirty();
  }
  function ask() { const q = quiz.pool[quiz.i]; quiz.target = q; quiz.tries = 0; quiz.locked = false; renderQuiz(); }
  function renderQuiz(msg = "", cls = "") {
    const q = quiz.target, it = q.it; const what = q.c === "capitals" ? `${T.quizCapitalOf} <b>${esc((data.cities.find((c) => c.c === it.p.i && c.cap) || {})[lang === "ar" ? "a" : "n"] || "")}</b>` : `${T.quizFind} <b>${esc(nm(it))}</b>`;
    quizUI.innerHTML = `<div class="q-row"><span>${T.quizScore}: ${quiz.score}/${quiz.N}</span><span>${quiz.i + 1} ${T.quizOf} ${quiz.pool.length}</span></div><div class="q-ask">${what}</div>
      <div class="q-msg ${cls}">${msg || "&nbsp;"}</div><div class="q-btns"><button data-q="skip">${T.quizSkip}</button><button data-q="stop">${T.quizStop}</button></div>`;
  }
  function answer(h) {
    if (!h || quiz.locked || quiz.phase !== "play") return; const it = quiz.target.it;
    if (h === it) { quiz.score++; quiz.locked = true; S.sel = it; renderQuiz(T.quizOk, "ok"); markDirty(); setTimeout(() => { S.sel = null; nextQ(); }, 1100); }
    else { quiz.tries++; S.hover = h; renderQuiz(`${T.quizNo} ${nm(h)} — ${T.quizTry}`, "no"); markDirty();
      if (quiz.tries === 2) { const ct = it.p?.ct ?? (it.bb ? null : null); const bb = it.bb || (it.pt ? [it.pt[0] - 40, it.pt[1] - 25, it.pt[0] + 40, it.pt[1] + 25] : null); if (bb) flyBox([bb[0] - 12, Math.max(-85, bb[1] - 10), bb[2] + 12, Math.min(85, bb[3] + 10)]); } }
  }
  function nextQ() { if (!quiz.on) return; quiz.i++; if (quiz.i >= quiz.pool.length) { quiz.locked = true; quizUI.innerHTML = `<div class="q-done"><div class="q-big">${quiz.score}<small>/${quiz.pool.length}</small></div><p>${T.quizDone}</p><div class="q-btns"><button data-q="again">${T.quizAgain}</button><button data-q="stop">${T.close}</button></div></div>`; flyTo(home()); } else ask(); }
  function endQuiz() { quiz.on = false; quiz.need = null; S.sel = null; S.hover = null; quizUI.hidden = true; root.classList.remove("quizzing"); setTool("quiz", false); markDirty(); }
  quizUI.addEventListener("click", (e) => {
    const c = e.target.closest("[data-qc]"); if (c) { const k = c.dataset.qc; quiz.cats = quiz.cats.includes(k) ? quiz.cats.filter((x) => x !== k) : [...quiz.cats, k]; renderQuizPick(); return; }
    const b = e.target.closest("[data-q]"); if (!b) return; const a = b.dataset.q;
    if (a === "go") beginQuiz(); else if (a === "skip") nextQ(); else if (a === "stop") endQuiz(); else if (a === "again") { quiz.phase = "pick"; renderQuizPick(); }
  });

  /* ---------------------------------------------------------- loop / theme */
  const ro = new ResizeObserver(resize); ro.observe(host);
  const themeObs = new MutationObserver(() => markDirty()); themeObs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  let io = new IntersectionObserver((en) => { if (en[0].isIntersecting) markDirty(); }); io.observe(host);
  function frame() {
    if (!alive) return; raf = requestAnimationFrame(frame);
    if (anim) { const k = Math.min(1, (performance.now() - anim.t0) / anim.ms), e = ease(k), a = anim.from, b = anim.to; S.k = a.k + (b.k - a.k) * e; S.tx = a.tx + (b.tx - a.tx) * e; S.ty = a.ty + (b.ty - a.ty) * e; S.lon = a.lon + (b.lon - a.lon) * e; S.lat = a.lat + (b.lat - a.lat) * e; applyProj(); dirty = true; lite = performance.now() + 60; if (k >= 1) { anim = null; lite = 0; } }
    const needFull = lite && performance.now() > lite; if (needFull) { lite = 0; dirty = true; }
    if (dirty) { dirty = false; render(); }
  }
  resize(); loading.classList.add("done"); setTimeout(() => loading.remove(), 600); frame();
  return {
    api: { select: (id) => { const it = byId.get(id); if (it) select(it, []); }, items, state: S,
      screenOf: (name) => { const it = items.find((i) => i.ar === name || i.en === name); if (!it) return null; const xy = toXY(it.pt || labelPtOf(it)); if (!xy) return null; const r = canvas.getBoundingClientRect(); return { x: r.left + xy[0], y: r.top + xy[1] }; } },
    dispose() { alive = false; cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); themeObs.disconnect(); document.removeEventListener("keydown", onKey); host.innerHTML = ""; },
  };
}
