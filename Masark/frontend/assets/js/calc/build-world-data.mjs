/**
 * Builds frontend/assets/data/world.json for the Geography map tab.
 *
 *   cd tools && npm i d3-geo topojson-server topojson-simplify && node build-world-data.mjs
 *
 * Source: Natural Earth (public domain, https://www.naturalearthdata.com), downloaded from the
 * nvkelso/natural-earth-vector GitHub mirror into tools/ne-cache/ on first run.
 * Arabic names come from Natural Earth's NAME_AR fields; Natural Earth has none for rivers,
 * so the RIVERS table below carries curated Arabic names.
 */
import fs from "node:fs";
import path from "node:path";
import { geoContains, geoCentroid, geoArea, geoLength, geoBounds } from "d3-geo";
import { topology } from "topojson-server";
import { quantize } from "topojson-client";
import { presimplify, simplify, quantile } from "topojson-simplify";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const CACHE = path.join(HERE, "ne-cache");
const OUT = path.join(HERE, "..", "frontend", "assets", "data", "world.json");
const BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson";
const FILES = ["ne_50m_admin_0_countries", "ne_50m_rivers_lake_centerlines", "ne_50m_lakes", "ne_50m_geography_marine_polys",
  "ne_50m_geography_regions_polys", "ne_10m_geography_regions_elevation_points", "ne_50m_populated_places"];
fs.mkdirSync(CACHE, { recursive: true });
for (const f of FILES) {
  const p = path.join(CACHE, f + ".geojson");
  if (!fs.existsSync(p)) { console.log("downloading", f); fs.writeFileSync(p, Buffer.from(await (await fetch(`${BASE}/${f}.geojson`)).arrayBuffer())); }
}
const read = (f) => JSON.parse(fs.readFileSync(path.join(CACHE, f + ".geojson"), "utf8")).features;
const R = 6371.0088;
const r1 = (v) => Math.round(v * 100) / 100;

/* ---------------------------------------------------------------- helpers */
const CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica", "Seven seas (open ocean)"];
const SUBREGIONS = [];
const idx = (arr, v) => { let i = arr.indexOf(v); if (i < 0) { arr.push(v); i = arr.length - 1; } return i; };
const SMALL = new Set(["of", "de", "du", "del", "la", "el", "al", "the", "and", "des", "do", "da", "dos"]);
const EXPAND = { "MTS.": "Mountains", "MTS": "Mountains", "MT.": "Mount", "RA.": "Range", "PLAT.": "Plateau", "PEN.": "Peninsula", "CORD.": "Cordillera", "UPLAND": "Upland", "IS.": "Islands" };
function nice(name) {
  if (!name) return name;
  if (name !== name.toUpperCase() && !/^[A-Z .’'-]+$/.test(name)) return name.trim().replace(/\s+/g, " ");
  return name.trim().replace(/\s+/g, " ").split(" ").map((w, i) => {
    const up = w.toUpperCase();
    if (EXPAND[up]) return EXPAND[up];
    const lw = w.toLowerCase();
    if (i > 0 && SMALL.has(lw)) return lw;
    return lw.replace(/(^|[-’'(])(\p{L})/gu, (m, a, b) => a + b.toUpperCase());
  }).join(" ");
}
const inBox = (b, [x, y]) => y >= b[0][1] && y <= b[1][1] && (b[0][0] <= b[1][0] ? x >= b[0][0] && x <= b[1][0] : x >= b[0][0] || x <= b[1][0]);
const polysOf = (g) => (g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : []);
const polyFeature = (poly) => ({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: poly } });
function bigPolygon(geom) {
  let best = null, ba = -1;
  for (const poly of polysOf(geom)) { const a = geoArea(polyFeature(poly)); if (a > ba) { ba = a; best = poly; } }
  return best;
}
function labelPoint(geom) {
  const big = bigPolygon(geom);
  const c = geoCentroid(polyFeature(big));
  return [r1(c[0]), r1(c[1])];
}
const roundCoords = (c) => (typeof c[0] === "number" ? [r1(c[0]), r1(c[1])] : c.map(roundCoords));

/* --------------------------------------------------------------- countries */
const AR_SUB = {};
const rawCountries = read("ne_50m_admin_0_countries");
const countries = rawCountries.map((f) => {
  const p = f.properties, a3 = p.ADM0_A3;
  return {
    type: "Feature", id: a3, geometry: f.geometry,
    properties: {
      n: p.NAME, a: p.NAME_AR, i: a3, ct: idx(CONTINENTS, p.CONTINENT), sr: idx(SUBREGIONS, p.SUBREGION), p: p.POP_EST,
      mc: p.MAPCOLOR7, ak: Math.round(geoArea(f) * R * R), lp: labelPoint(f.geometry),
    },
    _box: geoBounds(f),
  };
});
const countryAt = (pt) => { for (const c of countries) if (inBox(c._box, pt) && geoContains(c, pt)) return c.properties.i; return null; };

/* ------------------------------------------------------------------ rivers */
// [display name, Arabic, kind, rank (1 = most important), [Natural Earth names]]
const RIVERS = [
  ["Nile", "نهر النيل", "river", 1, ["Nile", "Albert Nile", "Victoria Nile", "Bahr el Jebel"]],
  ["White Nile", "النيل الأبيض", "river", 2, ["El Bahr el Abyad"]],
  ["Blue Nile", "النيل الأزرق", "river", 2, ["El Bahr el Azraq", "Abay"]],
  ["Atbara River", "نهر عطبرة", "river", 3, ["Atbara", "Setit"]],
  ["Damietta Branch", "فرع دمياط", "river", 3, ["Damietta Branch"]],
  ["Rosetta Branch", "فرع رشيد", "river", 3, ["Rosetta Branch"]],
  ["Suez Canal", "قناة السويس", "canal", 1, ["Suez Canal"]],
  ["Ismailia Canal", "ترعة الإسماعيلية", "canal", 4, ["Ismailiya Canal"]],
  ["Panama Canal", "قناة بنما", "canal", 2, ["Panama Canal"]],
  ["Amazon", "نهر الأمازون", "river", 1, ["Amazonas"]],
  ["Madeira", "نهر ماديرا", "river", 3, ["Madeira"]],
  ["Congo", "نهر الكونغو", "river", 1, ["Congo", "Lualaba"]],
  ["Niger", "نهر النيجر", "river", 1, ["Niger"]],
  ["Zambezi", "نهر الزامبيزي", "river", 2, ["Zambezi"]],
  ["Orange", "نهر أورانج", "river", 3, ["Orange"]],
  ["Limpopo", "نهر ليمبوبو", "river", 3, ["Limpopo"]],
  ["Senegal", "نهر السنغال", "river", 3, ["Sénégal"]],
  ["Volta", "نهر فولتا", "river", 4, ["Volta"]],
  ["Euphrates", "نهر الفرات", "river", 1, ["Euphrates", "Firat", "Al Furat"]],
  ["Tigris", "نهر دجلة", "river", 1, ["Tigris", "Dicle"]],
  ["Shatt al-Arab", "شط العرب", "river", 3, ["Shatt al Arab"]],
  ["Jordan", "نهر الأردن", "river", 3, ["Jordan"]],
  ["Indus", "نهر السند", "river", 1, ["Indus"]],
  ["Ganges", "نهر الغانج", "river", 1, ["Ganges"]],
  ["Brahmaputra", "نهر براهمابوترا", "river", 2, ["Brahmaputra", "Yarlung", "Dihang"]],
  ["Yangtze", "نهر اليانغتسي", "river", 1, ["Yangtze", "Chang Jiang", "Jinsha", "Tongtian", "Tuotuo"]],
  ["Yellow River", "النهر الأصفر", "river", 1, ["Huang"]],
  ["Mekong", "نهر ميكونغ", "river", 2, ["Mekong", "Lancang"]],
  ["Irrawaddy", "نهر إيراوادي", "river", 3, ["Ayeyarwady"]],
  ["Salween", "نهر سالوين", "river", 4, ["Salween"]],
  ["Amur", "نهر آمور", "river", 2, ["Amur", "Heilong Jiang"]],
  ["Ob", "نهر أوب", "river", 2, ["Ob"]],
  ["Irtysh", "نهر إرتيش", "river", 3, ["Irtysh", "Ertis", "Ertix"]],
  ["Yenisei", "نهر ينيسي", "river", 2, ["Yenisey", "Verkhniy Yenisey", "Malyy Yenisey"]],
  ["Lena", "نهر لينا", "river", 2, ["Lena"]],
  ["Kolyma", "نهر كوليما", "river", 4, ["Kolyma"]],
  ["Amu Darya", "نهر جيحون (أمو داريا)", "river", 3, ["Amu  Darya"]],
  ["Syr Darya", "نهر سيحون (سير داريا)", "river", 3, ["Syr Darya"]],
  ["Volga", "نهر الفولغا", "river", 1, ["Volga"]],
  ["Danube", "نهر الدانوب", "river", 1, ["Danube", "Donau"]],
  ["Rhine", "نهر الراين", "river", 2, ["Rhine", "Rhin", "Rhein"]],
  ["Elbe", "نهر إلبه", "river", 4, ["Elbe"]],
  ["Seine", "نهر السين", "river", 4, ["Seine"]],
  ["Loire", "نهر اللوار", "river", 4, ["Loire"]],
  ["Rhône", "نهر الرون", "river", 4, ["Rhône"]],
  ["Thames", "نهر التيمز", "river", 4, ["Thames"]],
  ["Po", "نهر بو", "river", 4, ["Po"]],
  ["Ebro", "نهر إيبرو", "river", 4, ["Ebro"]],
  ["Tagus", "نهر تاجة", "river", 4, ["Tajo", "Tejo"]],
  ["Vistula", "نهر فيستولا", "river", 4, ["Vistula"]],
  ["Dnieper", "نهر الدنيبر", "river", 2, ["Dnipro", "Dnepre"]],
  ["Don", "نهر الدون", "river", 3, ["Don"]],
  ["Ural", "نهر الأورال", "river", 3, ["Ural"]],
  ["Mississippi", "نهر المسيسيبي", "river", 1, ["Mississippi"]],
  ["Missouri", "نهر ميزوري", "river", 2, ["Missouri"]],
  ["Ohio", "نهر أوهايو", "river", 3, ["Ohio"]],
  ["Colorado", "نهر كولورادو", "river", 3, ["Colorado"]],
  ["Columbia", "نهر كولومبيا", "river", 3, ["Columbia"]],
  ["Rio Grande", "نهر ريو غراندي", "river", 3, ["Rio Grande"]],
  ["Yukon", "نهر يوكون", "river", 3, ["Yukon"]],
  ["Mackenzie", "نهر ماكنزي", "river", 2, ["Mackenzie"]],
  ["St. Lawrence", "نهر سانت لورانس", "river", 3, ["St. Lawrence"]],
  ["Hudson", "نهر هدسون", "river", 4, ["Hudson"]],
  ["Orinoco", "نهر أورينوكو", "river", 2, ["Orinoco"]],
  ["Paraná", "نهر بارانا", "river", 2, ["Paraná"]],
  ["Uruguay", "نهر أوروغواي", "river", 4, ["Uruguay"]],
  ["São Francisco", "نهر ساو فرانسيسكو", "river", 3, ["São  Francisco"]],
  ["Tocantins", "نهر توكانتينس", "river", 4, ["Tocantins"]],
  ["Magdalena", "نهر ماغدالينا", "river", 4, ["Magdalena"]],
  ["Murray", "نهر موراي", "river", 3, ["Murray"]],
  ["Darling", "نهر دارلينغ", "river", 4, ["Darling"]],
  ["Okavango", "نهر أوكافانغو", "river", 4, ["Okavango", "Cubango"]],
];

// Widely cited approximate river lengths (km). Natural Earth only has partial centre-lines, so we don't compute these.
const LEN = { "Nile": 6650, "Blue Nile": 1450, "Atbara River": 800, "Damietta Branch": 240, "Rosetta Branch": 239, "Suez Canal": 193, "Panama Canal": 82,
  "Amazon": 6400, "Madeira": 3250, "Congo": 4700, "Niger": 4180, "Zambezi": 2574, "Orange": 2200, "Limpopo": 1750, "Senegal": 1790, "Euphrates": 2800, "Tigris": 1850,
  "Shatt al-Arab": 200, "Jordan": 251, "Indus": 3180, "Ganges": 2525, "Brahmaputra": 2900, "Yangtze": 6300, "Yellow River": 5464, "Mekong": 4350, "Irrawaddy": 2170,
  "Salween": 2815, "Amur": 2824, "Ob": 3650, "Irtysh": 4248, "Yenisei": 3487, "Lena": 4400, "Kolyma": 2129, "Amu Darya": 2540, "Syr Darya": 2212, "Volga": 3530,
  "Danube": 2850, "Rhine": 1230, "Elbe": 1094, "Seine": 777, "Loire": 1006, "Rhône": 813, "Thames": 346, "Po": 652, "Ebro": 930, "Tagus": 1007, "Vistula": 1047,
  "Dnieper": 2290, "Don": 1870, "Ural": 2428, "Mississippi": 3734, "Missouri": 3767, "Ohio": 1579, "Colorado": 2330, "Columbia": 2000, "Rio Grande": 3034,
  "Yukon": 3190, "Mackenzie": 1738, "St. Lawrence": 1197, "Hudson": 507, "Orinoco": 2140, "Paraná": 4880, "Uruguay": 1610, "São Francisco": 2914, "Tocantins": 2639,
  "Magdalena": 1528, "Murray": 2508, "Darling": 1472, "Okavango": 1600 };
const riverFeats = read("ne_50m_rivers_lake_centerlines").filter((f) => f.geometry);
const byNE = new Map();
for (const f of riverFeats) { const n = f.properties.name; if (!n) continue; (byNE.get(n) || byNE.set(n, []).get(n)).push(f); }
const missing = [];
const rivers = RIVERS.map(([en, ar, kind, rank, names]) => {
  const lines = [];
  for (const n of names) { const fs_ = byNE.get(n); if (!fs_) { missing.push(n); continue; } for (const f of fs_) lines.push(...(f.geometry.type === "LineString" ? [f.geometry.coordinates] : f.geometry.coordinates)); }
  if (!lines.length) return null;
  const geometry = { type: "MultiLineString", coordinates: lines };
  const len = LEN[en] || 0;
  // countries along the course, in order of first appearance
  const seen = [];
  for (const line of lines) {
    const step = Math.max(1, Math.floor(line.length / 14));
    for (let i = 0; i < line.length; i += step) { const c = countryAt(line[i]); if (c && !seen.includes(c)) seen.push(c); }
  }
  return { type: "Feature", properties: { n: en, a: ar, k: kind, r: rank, ...(len ? { l: len } : {}), c: seen.slice(0, 10) }, geometry };
}).filter(Boolean);
if (missing.length) console.log("rivers not found in data:", missing.join(", "));

/* ------------------------------------------------------------------- lakes */
const KEEP_LAKES = new Set(["Lake Nasser", "Lake Nubia", "Dead Sea", "Lake Tana", "Lake Chad", "Lake Turkana", "Lake Albert", "Lake Kivu", "Lake Titicaca", "Great Salt Lake", "Lake Urmia", "Lake Van", "Aral Sea", "Lake Maracaibo", "Lake Nicaragua", "Great Lake Qarun", "Lake Qarun", "Lake Manzala", "Lake Mariout"]);
const lakesRaw = read("ne_50m_lakes").filter((f) => f.properties.name && f.properties.name_ar && (geoArea(f) * R * R >= 8000 || KEEP_LAKES.has(f.properties.name)));
const mergeBy = (feats, keyFn, propFn) => {
  const m = new Map();
  for (const f of feats) {
    const k = keyFn(f), polys = polysOf(f.geometry);
    if (!m.has(k)) m.set(k, { props: propFn(f), polys: [] });
    m.get(k).polys.push(...polys);
  }
  return [...m.values()].map(({ props, polys }) => ({ type: "Feature", properties: props, geometry: polys.length === 1 ? { type: "Polygon", coordinates: polys[0] } : { type: "MultiPolygon", coordinates: polys } }));
};
const countriesIn = (feature, box, nx = 9, ny = 9, top = 6) => {
  const hits = new Map();
  const [[x0, y0], [x1, y1]] = box;
  const w = x0 <= x1 ? x1 - x0 : 360 - (x0 - x1);
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
    let x = x0 + ((i + 0.5) / nx) * w; if (x > 180) x -= 360;
    const y = y0 + ((j + 0.5) / ny) * (y1 - y0);
    if (!geoContains(feature, [x, y])) continue;
    const c = countryAt([x, y]); if (c) hits.set(c, (hits.get(c) || 0) + 1);
  }
  return [...hits.entries()].sort((a, b) => b[1] - a[1]).slice(0, top).map((e) => e[0]);
};
const lakes = mergeBy(lakesRaw, (f) => f.properties.name, (f) => ({ n: f.properties.name, a: f.properties.name_ar, r: f.properties.scalerank }))
  .map((f) => ({ ...f, properties: { ...f.properties, ak: Math.round(geoArea(f) * R * R), lp: labelPoint(f.geometry), c: countriesIn(f, geoBounds(f), 6, 6, 4) } }));

/* ------------------------------------------------------------------ marine */
const OCEAN_LABELS = { "North Atlantic Ocean": [-38, 30], "South Atlantic Ocean": [-14, -22], "North Pacific Ocean": [-158, 28], "South Pacific Ocean": [-128, -22], "INDIAN OCEAN": [78, -20], "Arctic Ocean": [10, 84], "SOUTHERN OCEAN": [60, -66] };
const SEA_LABELS = { "Mediterranean Sea": [18, 34.5], "Red Sea": [38.5, 20.5], "Black Sea": [34.5, 43.3], "Caspian Sea": [51, 41.5], "Persian Gulf": [51.5, 27], "Arabian Sea": [64, 15], "Gulf of Mexico": [-90, 24.5], "Caribbean Sea": [-76, 15] };
const ARABIC_OCEAN = { "North Atlantic Ocean": "المحيط الأطلسي", "South Atlantic Ocean": "المحيط الأطلسي", "North Pacific Ocean": "المحيط الهادئ", "South Pacific Ocean": "المحيط الهادئ" };
const marineRaw = read("ne_50m_geography_marine_polys").filter((f) => f.properties.name_ar);
const marineOne = marineRaw.map((f) => {
  const p = f.properties;
  let n = nice(p.name), t = p.featurecla;
  if (/ocean/i.test(p.name)) {
    n = /atlantic/i.test(p.name) ? "Atlantic Ocean" : /pacific/i.test(p.name) ? "Pacific Ocean" : /indian/i.test(p.name) ? "Indian Ocean" : /southern/i.test(p.name) ? "Southern Ocean" : "Arctic Ocean";
  }
  return { f, n, t, a: ARABIC_OCEAN[p.name] || p.name_ar, r: t === "ocean" ? 0 : Math.max(1, p.scalerank || 3) };
});
const marine = mergeBy(marineOne.map((m) => ({ ...m.f, _m: m })), (f) => f._m.n + "|" + f._m.t, (f) => ({ n: f._m.n, a: f._m.a, t: f._m.t, r: f._m.r })).map((feat) => {
  const src = marineRaw.filter((x) => { const nn = nice(x.properties.name); return nn === feat.properties.n || (feat.properties.t === "ocean" && x.properties.featurecla === "ocean" && marineOne.find((m) => m.f === x)?.n === feat.properties.n); });
  const lps = feat.properties.t === "ocean"
    ? src.map((x) => OCEAN_LABELS[x.properties.name]).filter(Boolean)
    : [SEA_LABELS[feat.properties.n] || labelPoint(feat.geometry)];
  return { ...feat, properties: { ...feat.properties, lp: lps.length ? lps : [labelPoint(feat.geometry)] } };
});
// countries that touch each (non-ocean) water body: sample country coast vertices near the polygon
for (const m of marine) {
  if (m.properties.t === "ocean") continue;
  const box = geoBounds(m), hits = new Map();
  const pad = 1.2;
  for (const c of countries) {
    const b = c._box;
    if (b[1][1] < box[0][1] - pad || b[0][1] > box[1][1] + pad) continue;
    let count = 0;
    for (const poly of polysOf(c.geometry)) {
      const ring = poly[0], step = Math.max(1, Math.floor(ring.length / 220));
      for (let i = 0; i < ring.length; i += step) {
        const pt = ring[i];
        if (inBox([[box[0][0] - pad, box[0][1] - pad], [box[1][0] + pad, box[1][1] + pad]], pt) && (geoContains(m, pt) || nearPoly(m, pt))) count++;
      }
    }
    if (count >= 2) hits.set(c.properties.i, count);
  }
  m.properties.c = [...hits.entries()].sort((a, b) => b[1] - a[1]).slice(0, 16).map((e) => e[0]);
}
function nearPoly(m, [x, y]) {
  // cheap proximity test: any vertex of the water polygon within ~0.35 degrees
  for (const poly of polysOf(m.geometry)) for (const ring of poly) for (let i = 0; i < ring.length; i += 2) { const dx = Math.abs(ring[i][0] - x), dy = Math.abs(ring[i][1] - y); if (dx < 0.35 && dy < 0.35) return true; }
  return false;
}

/* ----------------------------------------------------------------- regions */
const REG_TYPES = { "Range/mtn": ["mountain", 3], Plateau: ["plateau", 3], Desert: ["desert", 4], Plain: ["plain", 3], Basin: ["basin", 4], Peninsula: ["peninsula", 3],
  "Pen/cape": ["peninsula", 3], Delta: ["delta", 4], Valley: ["valley", 4], Gorge: ["valley", 4], Isthmus: ["isthmus", 3], Lowland: ["plain", 4] };
const SKIP = /dome|station|talos|american highland|rockefeller|hollick|polar plateau|edward vii|pensacola|ellsworth|queen maud|transantarctic|cape (york|chelyuskin)|cà mau|cumberland|melville|gyda|chukchi|taymyr|liaodong|leizhou|kathiawar|ungava|gasp/i;
const regionsRaw = read("ne_50m_geography_regions_polys").filter((f) => {
  const p = f.properties, t = REG_TYPES[p.FEATURECLA];
  return t && p.SCALERANK <= t[1] && p.NAME_AR && p.NAME && !SKIP.test(p.NAME);
});
const REG_FIX = { "Peninsula Ibérica": "Iberian Plateau", "India": "Indian Peninsula", "Scandinavia": "Scandinavian Peninsula", "Crimea": "Crimean Peninsula", "Korea": "Korean Peninsula", "Florida": "Florida Peninsula", "Baja California": "Baja California Peninsula", "Pen. De Yucatán": "Yucatán Peninsula", "Punjab": "Punjab Plain", "Caatingas": "Caatinga", "Western Desert": "Western Desert (Egypt)", "Chaîne Annamitique": "Annamite Range", "Alti-planicie Mexicana": "Mexican Plateau" };
const regions = mergeBy(regionsRaw, (f) => nice(f.properties.NAME) + "|" + REG_TYPES[f.properties.FEATURECLA][0], (f) => {
  const n0 = nice(f.properties.NAME);
  return { n: REG_FIX[n0] || n0, a: f.properties.NAME_AR, t: REG_TYPES[f.properties.FEATURECLA][0], r: f.properties.SCALERANK };
}).map((f) => ({ ...f, properties: { ...f.properties, lp: labelPoint(f.geometry), c: countriesIn(f, geoBounds(f), 10, 10, 6) } }));

/* ------------------------------------------------------------------- peaks */
const elevRaw = read("ne_10m_geography_regions_elevation_points");
const peaks = [];
for (const f of elevRaw) {
  const p = f.properties, k = p.featurecla;
  const ok = (k === "mountain" && p.scalerank <= 4) || k === "depression" || (k === "pass" && p.name);
  if (!ok || !p.name || !p.name_ar || p.elevation == null) continue;
  const [x, y] = f.geometry.coordinates;
  peaks.push({ n: nice(p.name), a: p.name_ar, e: p.elevation, x: r1(x), y: r1(y), k: k === "mountain" ? "peak" : k, c: [countryAt([x, y])].filter(Boolean) });
}
if (!peaks.some((p) => /catherine/i.test(p.n))) peaks.push({ n: "Mount Catherine", a: "جبل كاترين", e: 2629, x: 33.95, y: 28.51, k: "peak", c: ["EGY"] });

/* ------------------------------------------------------------------ cities */
const places = read("ne_50m_populated_places");
const cities = [];
for (const f of places) {
  const p = f.properties, cap = p.ADM0CAP === 1;
  if (!(cap || p.POP_MAX >= 3000000 || p.ADM0_A3 === "EGY") || !p.NAME_AR) continue;
  cities.push({ n: p.NAME, a: p.NAME_AR, x: r1(p.LONGITUDE), y: r1(p.LATITUDE), p: p.POP_MAX, c: p.ADM0_A3, cap: cap ? 1 : 0 });
}

/* --------------------------------------------------------------- topology */
const clean = (feats, drop = ["_box"]) => ({ type: "FeatureCollection", features: feats.map((f) => {
  const g = { ...f, properties: { ...f.properties } }; for (const d of drop) delete g[d];
  const b = f._box || geoBounds(f); g.properties.bb = [r1(b[0][0]), r1(b[0][1]), r1(b[1][0]), r1(b[1][1])]; return g;
}) });
let topo = topology({ countries: clean(countries), lakes: clean(lakes), rivers: clean(rivers), marine: clean(marine), regions: clean(regions) }, 5e4);
topo = presimplify(topo);
topo = simplify(topo, quantile(topo, 0.42));
for (const arc of topo.arcs) for (let i = 0; i < arc.length; i++) arc[i] = arc[i].slice(0, 2);   // drop the simplification weights
topo = quantize(topo, 5e4);                                                                  // delta-encode again (much smaller)
const out = {
  meta: { source: "Natural Earth (public domain)", built: new Date().toISOString().slice(0, 10), continents: CONTINENTS, subregions: SUBREGIONS },
  topo, peaks, cities,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out, (k, v) => (typeof v === "number" ? Math.round(v * 1e6) / 1e6 : v)));
const kb = (o) => Math.round(JSON.stringify(o).length / 1024);
console.log(`countries ${countries.length} | rivers ${rivers.length} | lakes ${lakes.length} | marine ${marine.length} | regions ${regions.length} | peaks ${peaks.length} | cities ${cities.length}`);
console.log(`world.json ${Math.round(fs.statSync(OUT).size / 1024)} KB  (topology ${kb(topo)} KB, peaks ${kb(peaks)} KB, cities ${kb(cities)} KB)`);
