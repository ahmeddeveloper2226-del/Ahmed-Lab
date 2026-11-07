/**
 * Procedural human skeleton: every bone is built in code (no model files, no
 * licences to worry about) as its own mesh so each one can be hovered, clicked
 * and named. Units are metres; the figure is ~1.75 m tall, faces +z, and the
 * model's LEFT side is +x (so the viewer sees the model's right on their left).
 */
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

export const BONE = [0.925, 0.885, 0.795];
export const CART = [0.72, 0.83, 0.87];
const TEETH = [0.97, 0.96, 0.91];
const DARK = [0.06, 0.05, 0.05];

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const lerp = THREE.MathUtils.lerp;
const clamp = THREE.MathUtils.clamp;
const ss = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

/* ------------------------------------------------------------------ noise */
function hash(ix, iy, iz) {
  let h = Math.imul(ix, 374761393) ^ Math.imul(iy, 668265263) ^ Math.imul(iz, 1274126177);
  h = Math.imul(h ^ (h >>> 13), 1103515245);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
}
function vnoise(x, y, z) {
  const ix = Math.floor(x), iy = Math.floor(y), iz = Math.floor(z);
  const fx = x - ix, fy = y - iy, fz = z - iz;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = fz * fz * (3 - 2 * fz);
  const c = (a, b, d) => hash(ix + a, iy + b, iz + d);
  return lerp(
    lerp(lerp(c(0, 0, 0), c(1, 0, 0), u), lerp(c(0, 1, 0), c(1, 1, 0), u), v),
    lerp(lerp(c(0, 0, 1), c(1, 0, 1), u), lerp(c(0, 1, 1), c(1, 1, 1), u), v), w);
}

/* ------------------------------------------------------------- primitives */
function colored(g, col) {
  g = g.index ? g.toNonIndexed() : g;
  g.deleteAttribute("normal"); g.deleteAttribute("uv");
  const n = g.attributes.position.count, c = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) c.set(col, i * 3);
  g.setAttribute("color", new THREE.BufferAttribute(c, 3));
  return g;
}

/** ellipsoid: centre [x,y,z], radii [rx,ry,rz], optional Euler rot */
function ell(c, r, o = {}) {
  const g = new THREE.SphereGeometry(1, o.w || 16, o.h || 11);
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...(o.rot || [0, 0, 0])));
  g.applyMatrix4(new THREE.Matrix4().compose(V(...c), q, V(...r)));
  return colored(g, o.col || BONE);
}

function pathLength(center) {
  let L = 0, p = center(0);
  for (let i = 1; i <= 16; i++) { const q = center(i / 16); L += q.distanceTo(p); p = q; }
  return L;
}

/**
 * Sweep an elliptical cross-section along a path. center(t)->Vector3,
 * r(t)->[rx,rz]; rx lies along `hint` (projected perpendicular to the path).
 */
function sweep({ center, hint = V(1, 0, 0), r, segs = 28, radial = 14, cap = true, col = BONE }) {
  const r0 = r(0), r1 = r(1);
  const e = clamp(Math.max(r0[0], r0[1], r1[0], r1[1]) / pathLength(center), 0.01, 0.35);
  const rings = [];
  for (let i = 0; i <= segs; i++) {
    const t = 0.5 - 0.5 * Math.cos(Math.PI * i / segs);
    const p = center(t);
    const T = center(Math.min(1, t + 0.004)).sub(center(Math.max(0, t - 0.004))).normalize();
    const h = typeof hint === "function" ? hint(p, t) : hint;
    let X = h.clone().sub(T.clone().multiplyScalar(h.dot(T)));
    if (X.lengthSq() < 1e-5) X = Math.abs(T.y) < 0.9 ? V(0, 1, 0).sub(T.clone().multiplyScalar(T.y)) : V(1, 0, 0);
    X.normalize();
    const Z = new THREE.Vector3().crossVectors(T, X);
    const [rx, rz] = r(t);
    let c = 1;
    if (cap) { if (t < e) c = Math.sqrt(1 - (1 - t / e) ** 2); else if (t > 1 - e) c = Math.sqrt(1 - (1 - (1 - t) / e) ** 2); }
    rings.push({ p, X, Z, rx: rx * c, rz: rz * c });
  }
  const pos = [];
  for (let i = 0; i < segs; i++) {
    for (let j = 0; j < radial; j++) {
      const v = (ii, jj) => {
        const R = rings[ii], a = (2 * Math.PI * (jj % radial)) / radial, ca = Math.cos(a), sa = Math.sin(a);
        return [R.p.x + R.X.x * R.rx * ca + R.Z.x * R.rz * sa, R.p.y + R.X.y * R.rx * ca + R.Z.y * R.rz * sa, R.p.z + R.X.z * R.rx * ca + R.Z.z * R.rz * sa];
      };
      const a = v(i, j), b = v(i, j + 1), c2 = v(i + 1, j), d = v(i + 1, j + 1);
      pos.push(...a, ...b, ...c2, ...b, ...d, ...c2);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  return colored(g, col);
}


/** superellipsoid (n>2 = squarer than an ellipsoid) */
function sell(c, r, n, o = {}) {
  const g = new THREE.SphereGeometry(1, o.w || 36, o.h || 26), p = g.attributes.position, e = 2 / n;
  const f = (v) => Math.sign(v) * Math.pow(Math.abs(v), e);
  const tp = o.taper || [1, 1];
  for (let i = 0; i < p.count; i++) {
    const y = f(p.getY(i)), k = ss(0.2, -1, y);                         // narrower toward the bottom
    p.setXYZ(i, c[0] + f(p.getX(i)) * r[0] * lerp(1, tp[0], k), c[1] + y * r[1], c[2] + f(p.getZ(i)) * r[2] * lerp(1, tp[1], k));
  }
  return colored(g, o.col || BONE);
}

const curveCenter = (pts) => { const c = new THREE.CatmullRomCurve3(pts.map((p) => V(...p)), false, "centripetal"); return (t) => c.getPointAt(t); };
const shaft = (A, B, o) => {
  const a = V(...A), b = V(...B);
  return sweep({ ...o, center: (t) => a.clone().lerp(b, t).add(o.bow ? o.bow(t) : V(0, 0, 0)) });
};
const rod = (A, B, r0, r1 = r0, o = {}) => shaft(A, B, { r: (t) => [lerp(r0, r1, t), lerp(r0, r1, t)], segs: 6, radial: 10, ...o });

/** A thin curved plate: fn(u,v)->Vector3 on the mid surface, th(u,v)->half thickness. */
function thickSurface(fn, nu, nv, th, col = BONE) {
  const W = nu + 1;
  const P = [], N = [];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) P.push(fn(i / nu, j / nv));
  const at = (i, j) => P[clamp(j, 0, nv) * W + clamp(i, 0, nu)];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) {
    const du = at(i + 1, j).clone().sub(at(i - 1, j)), dv = at(i, j + 1).clone().sub(at(i, j - 1));
    N.push(new THREE.Vector3().crossVectors(du, dv).normalize());
  }
  const F = [], B = [];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) {
    const k = j * W + i, t = th(i / nu, j / nv);
    F.push(P[k].clone().addScaledVector(N[k], t)); B.push(P[k].clone().addScaledVector(N[k], -t));
  }
  const pos = [];
  const tri = (a, b, c) => pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
  const f = (i, j) => F[j * W + i], b = (i, j) => B[j * W + i];
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
    tri(f(i, j), f(i + 1, j), f(i, j + 1)); tri(f(i + 1, j), f(i + 1, j + 1), f(i, j + 1));
    tri(b(i, j), b(i, j + 1), b(i + 1, j)); tri(b(i + 1, j), b(i, j + 1), b(i + 1, j + 1));
  }
  for (let i = 0; i < nu; i++) {
    tri(f(i, 0), b(i, 0), f(i + 1, 0)); tri(f(i + 1, 0), b(i, 0), b(i + 1, 0));
    tri(f(i, nv), f(i + 1, nv), b(i, nv)); tri(f(i + 1, nv), b(i + 1, nv), b(i, nv));
  }
  for (let j = 0; j < nv; j++) {
    tri(f(0, j), f(0, j + 1), b(0, j)); tri(f(0, j + 1), b(0, j + 1), b(0, j));
    tri(f(nu, j), b(nu, j), f(nu, j + 1)); tri(f(nu, j + 1), b(nu, j), b(nu, j + 1));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  return colored(g, col);
}

function arcTube({ R, tube, a0, a1, pos, normal, col = BONE, flat = 1 }) {
  const g = sweep({
    center: (t) => V(R * Math.cos(lerp(a0, a1, t)), R * Math.sin(lerp(a0, a1, t)), 0),
    hint: V(0, 0, 1), r: () => [tube * flat, tube], segs: 18, radial: 8,
  });
  const q = new THREE.Quaternion().setFromUnitVectors(V(0, 0, 1), V(...normal).normalize());
  g.applyMatrix4(new THREE.Matrix4().compose(V(...pos), q, V(1, 1, 1)));
  return g;
}

function xform(g, m) { g.applyMatrix4(m); return g; }
function mirror(parts) {
  return parts.map((src) => {
    const g = src.clone();
    const p = g.attributes.position.array, c = g.attributes.color.array;
    for (let i = 0; i < p.length; i += 3) p[i] *= -1;
    for (let t = 0; t < p.length; t += 9) for (let k = 0; k < 3; k++) {
      [p[t + 3 + k], p[t + 6 + k]] = [p[t + 6 + k], p[t + 3 + k]];
      [c[t + 3 + k], c[t + 6 + k]] = [c[t + 6 + k], c[t + 3 + k]];
    }
    return g;
  });
}


/** Faster stand-in for BufferGeometryUtils.toCreasedNormals (numeric weld keys, CSR groups). */
function creasedNormals(g, angle) {
  const pos = g.attributes.position.array, n = pos.length / 3, tris = n / 3;
  const fn = new Float32Array(tris * 3), fu = new Float32Array(tris * 3);
  for (let t = 0; t < tris; t++) {
    const o = t * 9;
    const ax = pos[o + 3] - pos[o], ay = pos[o + 4] - pos[o + 1], az = pos[o + 5] - pos[o + 2];
    const bx = pos[o + 6] - pos[o], by = pos[o + 7] - pos[o + 1], bz = pos[o + 8] - pos[o + 2];
    const cx = ay * bz - az * by, cy = az * bx - ax * bz, cz = ax * by - ay * bx, l = Math.hypot(cx, cy, cz) || 1;
    fn[t * 3] = cx; fn[t * 3 + 1] = cy; fn[t * 3 + 2] = cz;
    fu[t * 3] = cx / l; fu[t * 3 + 1] = cy / l; fu[t * 3 + 2] = cz / l;
  }
  const map = new Map(), grp = new Int32Array(n), Q = 20000;
  let ng = 0;
  for (let i = 0; i < n; i++) {
    const ix = Math.round(pos[i * 3] * Q) + 32768, iy = Math.round(pos[i * 3 + 1] * Q) + 32768, iz = Math.round(pos[i * 3 + 2] * Q) + 32768;
    const key = (ix * 65536 + iy) * 65536 + iz;
    let id = map.get(key);
    if (id === undefined) { id = ng++; map.set(key, id); }
    grp[i] = id;
  }
  const start = new Int32Array(ng + 1);
  for (let i = 0; i < n; i++) start[grp[i] + 1]++;
  for (let i = 0; i < ng; i++) start[i + 1] += start[i];
  const fill = start.slice(0, ng), list = new Int32Array(n);
  for (let i = 0; i < n; i++) list[fill[grp[i]]++] = i;
  const out = new Float32Array(n * 3), cosT = Math.cos(angle);
  for (let i = 0; i < n; i++) {
    const t = (i / 3) | 0, ux = fu[t * 3], uy = fu[t * 3 + 1], uz = fu[t * 3 + 2];
    let sx = 0, sy = 0, sz = 0;
    for (let k = start[grp[i]]; k < start[grp[i] + 1]; k++) {
      const tj = (list[k] / 3) | 0;
      if (fu[tj * 3] * ux + fu[tj * 3 + 1] * uy + fu[tj * 3 + 2] * uz > cosT) { sx += fn[tj * 3]; sy += fn[tj * 3 + 1]; sz += fn[tj * 3 + 2]; }
    }
    const l = Math.hypot(sx, sy, sz) || 1;
    out[i * 3] = sx / l; out[i * 3 + 1] = sy / l; out[i * 3 + 2] = sz / l;
  }
  g.setAttribute("normal", new THREE.BufferAttribute(out, 3));
  return g;
}

/** Merge parts into one organic-looking mesh: tiny noise wobble + creased normals. */
function finish(parts, { crease = 0.95, wob = 1 } = {}) {
  const g = mergeGeometries(parts.flat());
  g.computeBoundingSphere();
  const R = g.boundingSphere.radius, f = 2.5 / (R + 0.02), amp = (0.01 * R + 0.0002) * wob;
  const pa = g.attributes.position, ca = g.attributes.color;
  for (let i = 0; i < pa.count; i++) {
    const x = pa.getX(i), y = pa.getY(i), z = pa.getZ(i), u = x * f, v = y * f, w = z * f;
    // cheap smooth pseudo-noise (same input -> same output, so shared vertices never split)
    pa.setXYZ(i,
      x + (Math.sin(u * 1.7 + v * 2.3 + w * 1.1 + 1.0) * 0.6 + Math.sin(u * 3.9 - v * 1.4 + w * 2.6)) * amp * 0.62,
      y + (Math.sin(u * 2.9 - v * 1.3 + w * 2.1 + 2.3) * 0.6 + Math.sin(-u * 2.2 + v * 3.7 + w * 1.5)) * amp * 0.62,
      z + (Math.sin(u * 1.3 + v * 2.7 - w * 1.9 + 4.1) * 0.6 + Math.sin(u * 2.5 + v * 1.8 + w * 3.3)) * amp * 0.62);
    const sh = 0.945 + 0.055 * Math.sin(u * 5.3 + v * 4.1 + w * 6.7) + 0.04 * Math.sin(u * 11.0 - v * 9.0 + w * 7.0);
    ca.setXYZ(i, ca.getX(i) * sh, ca.getY(i) * sh, ca.getZ(i) * sh);
  }
  const out = creasedNormals(g, crease);
  out.computeBoundingBox(); out.computeBoundingSphere();
  return out;
}

/* ------------------------------------------------------------ the result  */
const tick = () => new Promise((r) => setTimeout(r, 0));

export async function buildSkeleton(onProgress = () => {}) {
  const bones = [];   // pickable: {id, group, side, index?, finger?, seg?, geometry}
  const decor = [];   // not pickable: {geometry, kind: "cartilage" | "dark"}
  const add = (meta, parts, opt) => bones.push({ id: meta.id || `${meta.group}_${meta.side}`, ...meta, geometry: finish(parts, opt) });
  const addPair = (meta, leftParts, opt) => {
    const idOf = (side) => (meta.id ? `${meta.id}_${side}` : `${meta.group}_${side}`);
    add({ ...meta, id: idOf("L"), side: "L" }, leftParts, opt);
    add({ ...meta, id: idOf("R"), side: "R" }, mirror(leftParts), opt);
  };
  const addDecor = (parts, kind, region, opt) => decor.push({ kind, region, geometry: finish(parts, { wob: 0.3, ...opt }) });

  /* ---------- spine centre-line (z of the vertebral bodies at height y) ---------- */
  const SPINE_PTS = [[1.60, -0.025], [1.52, -0.020], [1.47, -0.040], [1.44, -0.048], [1.33, -0.068], [1.19, -0.055],
    [1.15, -0.047], [1.04, -0.032], [1.01, -0.042], [0.95, -0.062], [0.90, -0.070]];
  const spineZ = (y) => {
    for (let i = 0; i < SPINE_PTS.length - 1; i++) {
      const [y0, z0] = SPINE_PTS[i], [y1, z1] = SPINE_PTS[i + 1];
      if (y <= y0 && y >= y1) return lerp(z0, z1, (y0 - y) / (y0 - y1));
    }
    return y > 1.6 ? -0.025 : -0.07;
  };

  /* =============================== SKULL =============================== */
  const step = async (n) => { onProgress(n / 6); await tick(); };
  await step(0);
  buildSkull({ add, addPair, addDecor });
  await step(1);
  /* =============================== SPINE =============================== */
  const vert = buildSpine({ add, addDecor, spineZ });
  await step(2);
  /* ============================== THORAX =============================== */
  buildThorax({ add, addPair, addDecor, spineZ, vert });
  await step(3);
  /* ======================= LIMBS + PELVIS ============================== */
  buildArm({ add, addPair });
  await step(4);
  buildPelvis({ addPair });
  await step(5);
  buildLeg({ addPair });
  onProgress(1);
  return { bones, decor };
}

/* ===================================================================== */
/*  SKULL                                                                */
/* ===================================================================== */
function buildSkull({ add, addPair, addDecor }) {
  const C = [0, 1.668, -0.008], AX = 0.077, AY = 0.085, AZ = 0.102;
  const FACE = { c: [0, 1.620, 0.048], r: [0.054, 0.050, 0.046], n: 3, taper: [0.72, 0.86] };
  const faceZ = (x, y) => {
    const k = 1 - Math.pow(Math.abs(x / FACE.r[0]), FACE.n) - Math.pow(Math.abs((y - FACE.c[1]) / FACE.r[1]), FACE.n);
    return FACE.c[2] + FACE.r[2] * Math.pow(Math.max(k, 0.001), 1 / FACE.n);
  };
  const sph = new THREE.SphereGeometry(1, 64, 44);
  const pa = sph.attributes.position;
  const dirs = [];
  for (let i = 0; i < pa.count; i++) {
    const dx = pa.getX(i), dy = pa.getY(i), dz = pa.getZ(i);
    dirs.push([dx, dy, dz]);
    const front = ss(0.05, 0.95, dz), back = ss(-0.25, -0.95, dz) * (1 - Math.min(1, Math.abs(dy) * 0.9));
    const sx = AX * (1 - 0.22 * front) * (1 - 0.08 * ss(0, -0.9, dy));
    const sy = dy > 0 ? AY : AY * 0.86;
    const sz = AZ * (1 + 0.07 * back);
    pa.setXYZ(i, C[0] + dx * sx, C[1] + dy * sy, C[2] + dz * sz);
  }
  const idx = sph.index.array;
  const n3 = (x, y, z) => (vnoise(x * 2.7 + 5, y * 2.7, z * 2.7) - 0.5) * 0.09;
  const regionOf = (x, y, z) => {
    const n = n3(x, y, z), ax = Math.abs(x), side = x >= 0 ? "L" : "R";
    if (y < -0.22 && z > 0.30 && ax < 0.56) return "face";             // replaced by the facial bones
    if (y < -0.62) return z < 0.15 + n ? "occipital" : "sphenoid";
    const frontalEdge = 0.32 + 0.25 * Math.max(0, -y) + n;
    if (z > frontalEdge) return "frontal";
    if (ax > 0.5 && y < 0.16 && y > -0.62 && z > 0.04 + n) return "sphenoid";
    if (ax > 0.42 && y < 0.2 && z > -0.55 + n && z <= 0.04 + n) return "temporal_" + side;
    if (z < -0.55 + n) return "occipital";
    if (y < -0.3) return "temporal_" + side;
    return "parietal_" + side;
  };
  const triRegion = [];
  const vertRegions = Array.from({ length: pa.count }, () => new Set());
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t], b = idx[t + 1], c = idx[t + 2];
    const cx = dirs[a][0] + dirs[b][0] + dirs[c][0], cy = dirs[a][1] + dirs[b][1] + dirs[c][1], cz = dirs[a][2] + dirs[b][2] + dirs[c][2];
    const l = Math.hypot(cx, cy, cz) || 1;
    const r = regionOf(cx / l, cy / l, cz / l);
    triRegion.push(r);
    vertRegions[a].add(r); vertRegions[b].add(r); vertRegions[c].add(r);
  }
  const byRegion = {};
  for (let t = 0; t < idx.length; t += 3) (byRegion[triRegion[t / 3]] ||= []).push(t);
  const regionGeom = (name) => {
    const pos = [], col = [];
    for (const t of byRegion[name] || []) for (let k = 0; k < 3; k++) {
      const vi = idx[t + k];
      pos.push(pa.getX(vi), pa.getY(vi), pa.getZ(vi));
      const seam = vertRegions[vi].size > 1 ? 0.88 : 1;
      col.push(BONE[0] * seam, BONE[1] * seam, BONE[2] * seam);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    return g;
  };

  /* orbits: dark recessed discs + raised rims (rim is split between three bones) */
  const OX = 0.033, OY = 1.645, oz = faceZ(OX, OY);
  const orbitN = [0.28, 0, 1];
  const rim = (a0, a1, tube = 0.0042) => arcTube({ R: 0.0215, tube, a0: a0 * Math.PI, a1: a1 * Math.PI, pos: [OX, OY, oz + 0.0005], normal: orbitN, flat: 1.2 });
  const hole = (s) => ell([s * OX, OY, oz - 0.0012], [0.0188, 0.0178, 0.0035], { col: DARK, rot: [0, s * 0.27, 0] });
  addDecor([hole(1), hole(-1)], "dark", "head");

  /* frontal bone: forehead + brow arches + glabella + upper orbit rims */
  const brow = [rim(0.05, 0.95, 0.0062), ell([0.028, 1.666, oz - 0.002], [0.026, 0.0055, 0.0075], { rot: [0, 0.2, 0.10] })];
  add({ group: "frontal", side: "M" }, [regionGeom("frontal"), ell([0, 1.661, oz + 0.001], [0.011, 0.0075, 0.0065]), ...brow, ...mirror(brow)]);
  add({ group: "parietal", side: "L" }, [regionGeom("parietal_L")]);
  add({ group: "parietal", side: "R" }, [regionGeom("parietal_R")]);
  add({ group: "occipital", side: "M" }, [regionGeom("occipital"), ell([0, 1.652, -0.108], [0.007, 0.005, 0.006])]);
  add({ group: "sphenoid", side: "M" }, [regionGeom("sphenoid")]);
  const tExtras = [ell([0.060, 1.606, -0.036], [0.008, 0.013, 0.009], { rot: [0.2, 0, 0] }), rod([0.056, 1.608, -0.022], [0.052, 1.578, 0.002], 0.0022, 0.001)];
  add({ group: "temporal", side: "L" }, [regionGeom("temporal_L"), ...tExtras]);
  add({ group: "temporal", side: "R" }, [regionGeom("temporal_R"), ...mirror(tExtras)]);
  addDecor([ell([0.0705, 1.627, -0.014], [0.0035, 0.0055, 0.0055], { col: DARK }), ell([-0.0705, 1.627, -0.014], [0.0035, 0.0055, 0.0055], { col: DARK }),
    ell([0, 1.603, -0.030], [0.015, 0.004, 0.017], { col: DARK })], "dark", "head");

  /* zygomatic bone: cheek + arch + lateral/lower orbit rim */
  addPair({ group: "zygomatic" }, [
    ell([0.050, 1.621, 0.054], [0.0105, 0.0105, 0.0115]),
    sweep({ center: curveCenter([[0.054, 1.622, 0.048], [0.071, 1.626, 0.020], [0.073, 1.629, -0.004], [0.066, 1.630, -0.013]]), hint: V(0, 1, 0), r: () => [0.0042, 0.0034], segs: 14, radial: 8 }),
    rim(1.55, 2.1),
  ]);

  /* nasal bones */
  const nz = faceZ(0.0065, 1.642);
  addPair({ group: "nasal" }, [ell([0.0068, 1.641, nz + 0.001], [0.0068, 0.0145, 0.0045], { rot: [-0.30, 0, 0.06] })]);

  /* maxilla: the whole mid-face block + upper teeth + medial/lower orbit rims */
  const teeth = (yc, h, a, b, zc) => {
    const out = [];
    for (let k = -7; k < 7; k++) {
      const phi = (k + 0.5) * 0.19, m = Math.abs(k + 0.5), w = lerp(0.0026, 0.0048, ss(0, 6.5, m));
      out.push(ell([a * Math.sin(phi), yc, zc + b * Math.cos(phi)], [w, h, w * 1.15], { rot: [0, phi, 0], col: TEETH, w: 10, h: 8 }));
    }
    return out;
  };
  const maxRim = [rim(0.9, 1.55)];
  add({ group: "maxilla", side: "M" }, [
    sell(FACE.c, FACE.r, FACE.n, { taper: FACE.taper }), ...maxRim, ...mirror(maxRim),
    ...teeth(1.566, 0.0052, 0.027, 0.041, 0.050), ell([0, 1.606, faceZ(0, 1.606) + 0.001], [0.004, 0.004, 0.005]),
  ]);
  const apZ = faceZ(0, 1.618);
  addDecor([ell([0, 1.618, apZ - 0.0012], [0.0105, 0.0165, 0.004], { col: DARK })], "dark", "head");

  /* mandible */
  const mHalf = [
    sweep({ center: curveCenter([[0, 1.540, 0.080], [0.018, 1.540, 0.076], [0.034, 1.543, 0.060], [0.048, 1.547, 0.034], [0.057, 1.549, 0.006], [0.0605, 1.553, -0.014]]), hint: V(0, 1, 0), r: (t) => [lerp(0.0082, 0.0076, t), 0.0038], segs: 22, radial: 10 }),
    ell([0.0625, 1.592, -0.016], [0.0042, 0.037, 0.0165]), ell([0.0600, 1.628, -0.002], [0.0038, 0.014, 0.0085], { rot: [0.3, 0, 0] }),
    ell([0.0655, 1.633, -0.0205], [0.0075, 0.0068, 0.0095]), ell([0.0585, 1.556, -0.018], [0.0058, 0.0105, 0.0115]),
  ];
  add({ group: "mandible", side: "M" }, [...mHalf, ...mirror(mHalf), ell([0, 1.541, 0.080], [0.011, 0.0078, 0.0055]), ...teeth(1.556, 0.0050, 0.025, 0.039, 0.042)]);

  /* hyoid */
  const hHalf = [sweep({ center: curveCenter([[0.010, 1.504, 0.030], [0.026, 1.503, 0.020], [0.036, 1.502, 0.002], [0.038, 1.502, -0.008]]), hint: V(0, 1, 0), r: () => [0.0030, 0.0030], segs: 12, radial: 8 }), ell([0.011, 1.509, 0.030], [0.0022, 0.0045, 0.0022])];
  add({ group: "hyoid", side: "M" }, [ell([0, 1.504, 0.031], [0.012, 0.0036, 0.0042]), ...hHalf, ...mirror(hHalf)]);
}

/* ===================================================================== */
/*  SPINE, SACRUM, COCCYX                                                */
/* ===================================================================== */
function vBody(w, d, h, col = BONE) {
  const g = new THREE.CylinderGeometry(1, 1, h, 26, 3, false);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const y = p.getY(i), f = 1 - 0.10 * (1 - (2 * y / h) ** 2);
    p.setXYZ(i, p.getX(i) * f * w / 2, y, p.getZ(i) * f * d / 2);
  }
  return colored(g, col);
}
function vArch(c, zb, hh, th) {
  return sweep({
    center: (t) => { const a = Math.PI * t; return V(c * Math.cos(a), 0, zb - c * 1.25 * Math.sin(a)); },
    hint: V(0, 1, 0), r: () => [hh, th], segs: 16, radial: 8,
  });
}

function buildSpine({ add, addDecor, spineZ }) {
  const seq = [];
  [1.585, 1.563, 1.543, 1.524, 1.505, 1.487, 1.469].forEach((y, i) => seq.push({ id: `C${i + 1}`, group: i === 0 ? "atlas" : i === 1 ? "axis" : "cervical", kind: i === 0 ? "atlas" : i === 1 ? "axis" : "cervical", n: i + 1, y }));
  for (let i = 0; i < 12; i++) seq.push({ id: `T${i + 1}`, group: "thoracic", kind: "thoracic", n: i + 1, y: 1.448 - i * 0.0239 });
  for (let i = 0; i < 5; i++) seq.push({ id: `L${i + 1}`, group: "lumbar", kind: "lumbar", n: i + 1, y: 1.153 - i * 0.032 });

  const spinousDrop = [0.018, 0.024, 0.030, 0.036, 0.040, 0.040, 0.038, 0.034, 0.028, 0.022, 0.015, 0.010];
  const dims = (v) => {
    const n = v.n;
    if (v.kind === "cervical") return { w: 0.023 + 0.0009 * (n - 3), d: 0.017 + 0.0005 * (n - 3), h: 0.0125 + 0.0003 * (n - 3), c: 0.0100 + 0.0001 * (n - 3) };
    if (v.kind === "thoracic") { const s = (n - 1) / 11; return { w: 0.027 + 0.012 * s, d: 0.022 + 0.008 * s, h: 0.0185 + 0.0045 * s, c: 0.0095 + 0.0008 * s }; }
    if (v.kind === "lumbar") return { w: 0.040 + 0.003 * (n - 1), d: 0.030 + 0.001 * (n - 1), h: 0.0255 + 0.0005 * (n - 1), c: 0.0120 + 0.0006 * (n - 1) };
    return { w: 0.022, d: 0.018, h: 0.020, c: 0.011 };
  };

  const local = (v) => {
    const { w, d, h, c } = dims(v), zb = -d / 2 + 0.001, parts = [];
    if (v.kind === "atlas") {
      const ax = 0.0185, az = 0.0155;
      parts.push(sweep({
        center: (t) => V(ax * Math.sin(2 * Math.PI * t), 0, -0.002 - az * Math.cos(2 * Math.PI * t)), hint: V(0, 1, 0),
        r: (t) => [0.0052, lerp(0.0040, 0.0062, 0.5 - 0.5 * Math.cos(2 * Math.PI * (t - 0.5)))], segs: 32, radial: 10, cap: false,
      }));
      for (const s of [-1, 1]) {
        parts.push(ell([s * 0.0178, 0, -0.002], [0.0095, 0.0078, 0.0115]));
        parts.push(rod([s * 0.020, 0, -0.004], [s * 0.037, -0.002, -0.008], 0.0048, 0.0034));
      }
      parts.push(ell([0, 0, az - 0.002], [0.004, 0.0032, 0.0032]), ell([0, 0, -az - 0.0035], [0.0036, 0.0036, 0.0036]));
      return parts;
    }
    if (v.kind === "axis") {
      parts.push(ell([0, 0, 0], [0.0115, 0.0105, 0.0090]), rod([0, 0.004, 0.001], [0, 0.0175, 0.0015], 0.0052, 0.0034));
      parts.push(vArch(0.0110, -0.0085, 0.0070, 0.0036), ell([0, -0.002, -0.032], [0.0040, 0.0085, 0.0165]));
      for (const s of [-1, 1]) {
        parts.push(ell([s * 0.0155, 0.0075, -0.002], [0.0070, 0.0030, 0.0085]), rod([s * 0.012, -0.002, -0.006], [s * 0.026, -0.004, -0.002], 0.0042, 0.0030));
      }
      return parts;
    }
    parts.push(vBody(w, d, h), vArch(c, zb, v.kind === "lumbar" ? 0.011 : v.kind === "thoracic" ? 0.0090 : 0.0068, v.kind === "lumbar" ? 0.0048 : 0.0036));
    for (const s of [-1, 1]) {
      if (v.kind === "cervical") {
        parts.push(rod([s * c, 0, zb], [s * (c + 0.015), -0.0015, zb + 0.0035], 0.0042, 0.0030));
        parts.push(ell([s * (c + 0.0025), 0.0035, zb - 0.005], [0.0045, 0.0035, 0.0045]));
      } else if (v.kind === "thoracic") {
        parts.push(rod([s * c, 0, zb - 0.003], [s * (c + 0.021), 0.0005, zb - 0.016], 0.0050, 0.0042), ell([s * (c + 0.021), 0.0005, zb - 0.016], [0.0046, 0.0046, 0.0046]));
        parts.push(ell([s * (w / 2 - 0.001), 0.0, zb + 0.004], [0.0048, 0.0050, 0.0050]), ell([s * (c + 0.0025), 0.0055, zb - 0.006], [0.0045, 0.0040, 0.0045]));
      } else {
        parts.push(rod([s * c, 0, zb - 0.002], [s * (c + 0.022), 0.001, zb - 0.002], 0.0056, 0.0042));
        parts.push(ell([s * (c + 0.004), 0.010, zb - 0.006], [0.0050, 0.0070, 0.0060]), ell([s * (c + 0.002), -0.011, zb - 0.005], [0.0045, 0.0060, 0.0055]));
      }
    }
    const zs = zb - c * 1.25;
    if (v.kind === "cervical") parts.push(rod([0, 0.0015, zs - 0.004], [0, -0.0035, zs - (v.n === 7 ? 0.034 : 0.022)], 0.0034, 0.0022));
    else if (v.kind === "thoracic") parts.push(rod([0, 0.003, zs - 0.004], [0, -spinousDrop[v.n - 1], zs - 0.030 - (v.n >= 4 && v.n <= 8 ? 0.006 : 0)], 0.0045, 0.0030));
    else parts.push(ell([0, 0, zs - 0.014], [0.0045, 0.0115, 0.0165]));
    return parts;
  };

  const thoracic = [];
  const discParts = [];
  seq.forEach((v, k) => {
    const z = spineZ(v.y), up = seq[k - 1]?.y ?? v.y + 0.02, dn = seq[k + 1]?.y ?? v.y - 0.02;
    const dir = V(0, up - dn, spineZ(up) - spineZ(dn)).normalize();
    const tilt = Math.atan2(dir.z, dir.y);
    const M = new THREE.Matrix4().compose(V(0, v.y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(tilt, 0, 0)), V(1, 1, 1));
    const parts = local(v).map((g) => xform(g, M));
    add({ id: v.id, group: v.group, index: v.n, side: "M", region: "spine" }, parts);
    if (v.kind === "thoracic") thoracic.push({ y: v.y, z });
    // disc below this vertebra
    const nx = seq[k + 1];
    if (nx && v.kind !== "atlas") {
      const a = dims(v), b = dims(nx), ym = (v.y + nx.y) / 2;
      const gap = Math.max(0.004, (v.y - nx.y) - (a.h + b.h) / 2);
      const dz = spineZ(ym);
      const g = new THREE.CylinderGeometry(1, 1, gap * 1.02, 24, 1);
      g.applyMatrix4(new THREE.Matrix4().compose(V(0, ym, dz), new THREE.Quaternion().setFromEuler(new THREE.Euler(tilt, 0, 0)), V(((a.w + b.w) / 4) * 1.01, 1, ((a.d + b.d) / 4) * 1.01)));
      discParts.push(colored(g, CART));
    }
  });
  // L5 / sacrum disc
  { const g = new THREE.CylinderGeometry(1, 1, 0.011, 24, 1); g.applyMatrix4(new THREE.Matrix4().compose(V(0, 1.0105, spineZ(1.0105)), new THREE.Quaternion().setFromEuler(new THREE.Euler(0.12, 0, 0)), V(0.026, 1, 0.0185))); discParts.push(colored(g, CART)); }
  addDecor(discParts, "cartilage", "spine", { crease: 0.9 });

  /* sacrum */
  const sacW = (v) => 0.024 + 0.100 * Math.pow(1 - v, 1.0);
  const sacrum = thickSurface(
    (u, v) => V((u - 0.5) * sacW(v), 1.0045 - 0.100 * v, -0.050 - 0.030 * (1 - (1 - v) ** 2) - 0.008 * Math.sin(Math.PI * u) * (1 - v)),
    16, 14,
    (u, v) => (0.0105 * (1 - v) + 0.0040) * (0.35 + 0.65 * Math.sqrt(Math.max(0, 1 - (2 * u - 1) ** 2))),
  );
  add({ id: "sacrum", group: "sacrum", side: "M", region: "pelvis" }, [sacrum, ell([0, 1.004, -0.046], [0.020, 0.004, 0.008])]);
  const foramina = [];
  for (const v of [0.18, 0.36, 0.54, 0.70]) for (const s of [-1, 1]) {
    foramina.push(ell([s * sacW(v) * 0.22, 1.0045 - 0.100 * v, -0.050 - 0.030 * (1 - (1 - v) ** 2) + 0.0075 * (1 - v) + 0.0025], [0.0028, 0.0034, 0.0022], { col: DARK, w: 8, h: 6 }));
  }
  addDecor(foramina, "dark", "pelvis");

  /* coccyx */
  add({ id: "coccyx", group: "coccyx", side: "M", region: "pelvis" }, [
    ell([0, 0.896, -0.072], [0.010, 0.0065, 0.0085]), ell([0, 0.883, -0.071], [0.0080, 0.0058, 0.0072]),
    ell([0, 0.872, -0.067], [0.0058, 0.0052, 0.0055]), ell([0, 0.863, -0.062], [0.0040, 0.0045, 0.0040]),
    ell([0.0085, 0.898, -0.071], [0.0030, 0.0045, 0.0030]), ell([-0.0085, 0.898, -0.071], [0.0030, 0.0045, 0.0030]),
  ]);
  return { thoracic };
}

/* ===================================================================== */
/*  RIB CAGE + STERNUM                                                   */
/* ===================================================================== */
function buildThorax({ add, addPair, addDecor, spineZ, vert }) {
  const T = vert.thoracic;
  const A = [0.044, 0.074, 0.098, 0.116, 0.128, 0.138, 0.145, 0.150, 0.150, 0.143, 0.125, 0.100];
  const DROP = [0.012, 0.020, 0.030, 0.040, 0.050, 0.060, 0.068, 0.075, 0.075, 0.060, 0.040, 0.020];
  const THMAX = [2.35, 2.45, 2.5, 2.5, 2.5, 2.5, 2.5, 2.45, 2.4, 2.2, 1.55, 1.25];
  const ZE = [0.080, 0.092, 0.098, 0.100, 0.098, 0.095, 0.090, 0.082, 0.072, 0.058, 0.020, -0.020];
  const YS = [1.428, 1.395, 1.368, 1.340, 1.312, 1.285, 1.258];
  const sternZ = (y) => lerp(0.090, 0.108, clamp((1.437 - y) / 0.21, 0, 1));
  const LOWER = [[0.046, 1.250, 0.099], [0.062, 1.233, 0.095], [0.077, 1.216, 0.090]];
  const prof = (t, i) => {
    const head = 1 + 0.9 * Math.exp(-((t / 0.035) ** 2)), neck = 1 - 0.22 * Math.exp(-(((t - 0.07) / 0.02) ** 2));
    const tub = 1 + 0.30 * Math.exp(-(((t - 0.115) / 0.02) ** 2)), flare = 1 + 0.25 * ss(0.85, 1, t);
    return head * neck * tub * flare;
  };

  for (let i = 0; i < 12; i++) {
    const yp = T[i].y, zp = T[i].z - 0.016, x0 = i === 0 ? 0.014 : 0.018, a = A[i], th = THMAX[i];
    const D = (ZE[i] - zp) / ((1 - Math.cos(th)) / 2), N = 28, pts = [];
    for (let k = 0; k <= N; k++) {
      const q = th * k / N;
      pts.push([
        x0 + (a - x0) * Math.sin(q),
        yp - DROP[i] * Math.pow(q / th, 1.25),
        zp + D * (1 - Math.cos(q)) / 2 - 0.010 * Math.sin(Math.min(q / 0.9, 1) * Math.PI),
      ]);
    }
    const flat = i === 0;
    const small = i >= 10;
    const rib = sweep({
      center: curveCenter(pts), segs: 44, radial: 10,
      hint: flat ? V(0, 1, 0) : (p) => V(p.x, 0, p.z - 0.02),
      r: (t) => {
        const f = prof(t, i);
        if (flat) return [0.0030 * f, 0.0098 * f];
        if (small) return [0.0030 * f, 0.0042 * f];
        return [(0.0026 + 0.00012 * i) * f, (0.0062 + 0.0003 * i) * f];
      },
    });
    const parts = [rib];
    const E = V(...pts[N]), Eprev = V(...pts[N - 1]), tan = E.clone().sub(Eprev).normalize();
    const start = E.clone().addScaledVector(tan, -0.004);
    if (i < 7) {
      const S = V(0.0155, YS[i], sternZ(YS[i]));
      const M = E.clone().lerp(S, 0.55).add(V(0, 0.003 + i * 0.0008, 0.004));
      parts.push(sweep({ center: curveCenter([[start.x, start.y, start.z], [M.x, M.y, M.z], [S.x, S.y, S.z]]), hint: V(0, 0, 1), r: () => [0.0036, 0.0056], segs: 16, radial: 8, col: CART }));
    } else if (i < 10) {
      const S = V(...LOWER[i - 7]);
      const M = E.clone().lerp(S, 0.55).add(V(0, 0.008, 0.004));
      parts.push(sweep({ center: curveCenter([[start.x, start.y, start.z], [M.x, M.y, M.z], [S.x, S.y, S.z]]), hint: V(0, 0, 1), r: () => [0.0034, 0.0050], segs: 14, radial: 8, col: CART }));
    } else {
      parts.push(ell([E.x + tan.x * 0.003, E.y + tan.y * 0.003, E.z + tan.z * 0.003], [0.004, 0.004, 0.004], { col: CART, w: 8, h: 6 }));
    }
    addPair({ id: `rib_${i + 1}`, group: "rib", index: i + 1, region: "thorax" }, parts);
  }

  /* sternum */
  const manubrium = thickSurface(
    (u, v) => { const W = 0.044 + 0.014 * ss(0, 0.28, v) - 0.016 * ss(0.35, 1, v); return V((u - 0.5) * W, 1.437 - 0.054 * v, 0.088 + 0.012 * v + 0.004 * (1 - (2 * u - 1) ** 2)); },
    10, 10, (u) => 0.0050 - 0.0012 * Math.abs(2 * u - 1));
  const body = thickSurface(
    (u, v) => { const W = 0.027 + 0.007 * v + 0.0025 * Math.cos(2 * Math.PI * 4 * v); return V((u - 0.5) * W, 1.381 - 0.118 * v, 0.0975 + 0.013 * v + 0.003 * (1 - (2 * u - 1) ** 2)); },
    8, 24, (u) => 0.0048 - 0.0010 * Math.abs(2 * u - 1));
  const xiph = thickSurface(
    (u, v) => V((u - 0.5) * (0.0175 * Math.pow(1 - v, 0.9) + 0.0015), 1.262 - 0.034 * v, 0.110 + 0.006 * v),
    6, 8, (u, v) => 0.0032 * (1 - 0.3 * v));
  add({ id: "manubrium", group: "manubrium", side: "M", region: "thorax" }, [manubrium]);
  add({ id: "sternum_body", group: "sternum_body", side: "M", region: "thorax" }, [body]);
  add({ id: "xiphoid", group: "xiphoid", side: "M", region: "thorax" }, [xiph]);
}

/* ===================================================================== */
/*  SHOULDER GIRDLE, ARM, HAND  (built for the left side, mirrored)      */
/* ===================================================================== */
function longBone(A, B, rFn, o = {}) { return shaft(A, B, { hint: V(1, 0, 0), segs: 18, radial: 10, r: rFn, ...o }); }

function buildArm({ add, addPair }) {
  /* clavicle */
  const clav = sweep({
    center: curveCenter([[0.017, 1.433, 0.088], [0.050, 1.441, 0.098], [0.095, 1.447, 0.082], [0.140, 1.449, 0.040], [0.172, 1.445, 0.008]]),
    hint: V(0, 1, 0), segs: 30, radial: 12,
    r: (t) => [t < 0.15 ? lerp(0.0072, 0.0052, t / 0.15) : t < 0.6 ? 0.0050 : lerp(0.0050, 0.0030, (t - 0.6) / 0.4),
      t < 0.15 ? 0.0070 : t < 0.65 ? 0.0052 : lerp(0.0052, 0.0095, ss(0.65, 0.95, t))],
  });
  addPair({ id: "clavicle", group: "clavicle" }, [clav, ell([0.017, 1.433, 0.088], [0.0085, 0.0075, 0.0075])]);

  /* scapula: built in its own plane, then rotated onto the back of the rib cage */
  const xm = (v) => 0.012 * Math.pow(v, 1.3), Wd = (v) => 0.010 + 0.078 * Math.pow(1 - v, 1.25);
  const sc = [
    thickSurface((u, v) => V(xm(v) + u * Wd(v) * 1.08, -0.145 * v - 0.022 * u * (1 - v) ** 2, -0.004 * Math.sin(Math.PI * u) * Math.sin(Math.PI * Math.pow(v, 0.7))),
      12, 16, (u) => 0.0028 + 0.0020 * ss(0.85, 1, u)),
    sweep({ center: curveCenter([[0.003, -0.037, -0.008], [0.04, -0.034, -0.012], [0.085, -0.014, -0.015], [0.112, 0.003, -0.012]]), hint: V(0, 0, 1), r: (t) => [lerp(0.0035, 0.0075, ss(0, 0.35, t)), 0.0020], segs: 14, radial: 8 }),
    ell([0.122, 0.000, -0.006], [0.014, 0.0035, 0.011]), ell([0.092, -0.062, 0.003], [0.0045, 0.018, 0.012], { w: 14, h: 10 }),
    ell([0.083, -0.060, 0.0], [0.010, 0.016, 0.008]),
    sweep({ center: curveCenter([[0.080, -0.027, 0.004], [0.082, -0.018, 0.020], [0.092, -0.012, 0.036], [0.100, -0.015, 0.046]]), hint: V(1, 0, 0), r: () => [0.0045, 0.0045], segs: 10, radial: 8 }),
  ];
  const M = new THREE.Matrix4().compose(V(0.068, 1.438, -0.074), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -0.61, 0)), V(1, 1, 1));
  addPair({ id: "scapula", group: "scapula" }, sc.map((g) => xform(g, M)));

  /* humerus */
  addPair({ id: "humerus", group: "humerus" }, [
    ell([0.158, 1.376, -0.008], [0.0235, 0.0235, 0.0235], { w: 20, h: 14 }), ell([0.176, 1.386, -0.004], [0.011, 0.013, 0.014]), ell([0.162, 1.378, 0.016], [0.007, 0.012, 0.008]),
    longBone([0.168, 1.358, -0.006], [0.190, 1.098, -0.004],
      (t) => [0.0125 * (1 + 0.45 * (1 - ss(0, 0.18, t))) + 0.0095 * ss(0.78, 1, t), 0.0120 * (1 + 0.2 * (1 - ss(0, 0.15, t))) - 0.0015 * ss(0.78, 1, t)],
      { bow: (t) => V(0, 0, 0.004 * Math.sin(Math.PI * t)), segs: 24 }),
    ell([0.171, 1.098, -0.004], [0.0075, 0.0095, 0.0075]), ell([0.209, 1.100, -0.003], [0.007, 0.008, 0.007]),
    ell([0.185, 1.087, 0.004], [0.0105, 0.0115, 0.0125]), ell([0.200, 1.088, 0.006], [0.010, 0.0105, 0.011]),
  ]);
  /* ulna */
  addPair({ id: "ulna", group: "ulna" }, [
    ell([0.187, 1.095, -0.019], [0.0125, 0.0145, 0.0115]), ell([0.187, 1.075, 0.010], [0.0085, 0.008, 0.0105]),
    longBone([0.187, 1.072, -0.002], [0.200, 0.832, 0.004], (t) => [lerp(0.0090, 0.0050, ss(0, 0.4, t)) * (1 - 0.3 * ss(0.8, 1, t)), lerp(0.0100, 0.0060, ss(0, 0.4, t)) * (1 - 0.3 * ss(0.8, 1, t))]),
    ell([0.2005, 0.826, 0.0035], [0.0058, 0.0058, 0.0058]), rod([0.199, 0.826, 0.001], [0.2005, 0.812, 0.0], 0.0022, 0.0012),
  ]);
  /* radius */
  addPair({ id: "radius", group: "radius" }, [
    ell([0.207, 1.078, 0.012], [0.0108, 0.0042, 0.0108]), rod([0.205, 1.075, 0.012], [0.205, 1.062, 0.012], 0.0055, 0.0050), ell([0.200, 1.056, 0.015], [0.005, 0.008, 0.006]),
    longBone([0.205, 1.066, 0.012], [0.226, 0.828, 0.012], (t) => [0.0052 + 0.0095 * ss(0.82, 1, t) + 0.0010 * Math.sin(Math.PI * t), 0.0052 + 0.0043 * ss(0.82, 1, t)], { bow: (t) => V(0.006 * Math.sin(Math.PI * t), 0, 0) }),
    ell([0.226, 0.822, 0.010], [0.014, 0.0075, 0.0095]), ell([0.234, 0.814, 0.008], [0.0045, 0.008, 0.0045]),
  ]);

  /* carpals */
  const sm = { w: 12, h: 9 };
  const carpals = {
    scaphoid: [[0.225, 0.805, 0.012], [0.0095, 0.007, 0.0075], [0, 0, -0.5]],
    lunate: [[0.213, 0.803, 0.011], [0.0075, 0.0070, 0.0070]],
    triquetrum: [[0.201, 0.802, 0.010], [0.0070, 0.0060, 0.0070]],
    pisiform: [[0.198, 0.797, 0.020], [0.0045, 0.0050, 0.0045]],
    trapezium: [[0.232, 0.790, 0.014], [0.0075, 0.0065, 0.0070]],
    trapezoid: [[0.222, 0.789, 0.013], [0.0055, 0.0055, 0.0065]],
    capitate: [[0.211, 0.789, 0.011], [0.0075, 0.0085, 0.0070]],
    hamate: [[0.199, 0.789, 0.011], [0.0075, 0.0075, 0.0075]],
  };
  for (const [name, [c, r, rot]] of Object.entries(carpals)) {
    const parts = [ell(c, r, { ...sm, rot })];
    if (name === "hamate") parts.push(ell([0.199, 0.783, 0.019], [0.003, 0.005, 0.003], sm));
    addPair({ id: name, group: name }, parts);
  }

  /* metacarpals + fingers */
  const mcs = [
    [[0.235, 0.786, 0.016], [0.250, 0.740, 0.022], 0.0058], [[0.224, 0.784, 0.012], [0.2275, 0.722, 0.012], 0.0050],
    [[0.213, 0.783, 0.011], [0.214, 0.718, 0.011], 0.0048], [[0.202, 0.783, 0.011], [0.202, 0.722, 0.011], 0.0046],
    [[0.192, 0.784, 0.011], [0.1895, 0.730, 0.010], 0.0044],
  ];
  const slim = (A, B, r, tw = 1) => shaft(A, B, { hint: V(1, 0, 0), segs: 8, radial: 8, r: (t) => [r * tw * (0.78 + 0.5 * Math.exp(-((t / 0.14) ** 2)) + 0.5 * Math.exp(-(((1 - t) / 0.14) ** 2))), r * (0.78 + 0.45 * Math.exp(-((t / 0.14) ** 2)) + 0.45 * Math.exp(-(((1 - t) / 0.14) ** 2)))] });
  mcs.forEach(([A, B, r], i) => addPair({ id: `mc_${i + 1}`, group: "metacarpal", index: i + 1 }, [slim(A, B, r)]));

  const fingerDir = [V(0.22, -1, 0.10), V(0.03, -1, 0.02), V(0, -1, 0.02), V(-0.03, -1, 0.02), V(-0.07, -1, 0.02)].map((d) => d.normalize());
  const lens = [[0.033, 0, 0.027], [0.041, 0.024, 0.019], [0.045, 0.028, 0.020], [0.042, 0.026, 0.019], [0.033, 0.019, 0.016]];
  const segNames = ["proximal", "middle", "distal"];
  mcs.forEach(([, head, r], f) => {
    let p = V(...head).addScaledVector(fingerDir[f], 0.0035);
    lens[f].forEach((L, s) => {
      if (!L) return;
      const q = p.clone().addScaledVector(fingerDir[f], L);
      addPair({ id: `ph_hand_${f + 1}_${segNames[s]}`, group: "phalanx_hand", finger: f + 1, seg: segNames[s] },
        [slim([p.x, p.y, p.z], [q.x, q.y, q.z], r * (0.9 - 0.12 * s), 1)]);
      p = q.clone().addScaledVector(fingerDir[f], 0.0032);
    });
  });
}

/* ===================================================================== */
/*  PELVIS (hip bone = ilium + ischium + pubis)                          */
/* ===================================================================== */
function buildPelvis({ addPair }) {
  const H = [0.088, 0.917, 0.003];
  const top = new THREE.CatmullRomCurve3([[0.113, 0.998, 0.082], [0.132, 1.022, 0.060], [0.144, 1.040, 0.022], [0.141, 1.044, -0.020], [0.110, 1.034, -0.060], [0.054, 0.992, -0.084]].map((p) => V(...p)), false, "centripetal");
  const bot = new THREE.CatmullRomCurve3([[0.100, 0.958, 0.056], [0.095, 0.940, 0.020], [0.088, 0.925, -0.010], [0.075, 0.918, -0.035], [0.065, 0.945, -0.062], [0.052, 0.975, -0.082]].map((p) => V(...p)), false, "centripetal");
  const ilium = thickSurface((u, v) => bot.getPoint(u).lerp(top.getPoint(u), v).add(V(0.020 * Math.sin(Math.PI * v) * (0.5 + 0.5 * Math.sin(Math.PI * u)), 0.004 * v, 0.0)),
    22, 12, (u, v) => 0.0028 + 0.0030 * ss(0.82, 1, v));
  const n = [0.85, -0.25, 0.45];
  addPair({ id: "ilium", group: "ilium" }, [
    ilium, ell([0.092, 0.930, 0.004], [0.022, 0.026, 0.024]),
    arcTube({ R: 0.0285, tube: 0.0042, a0: 0, a1: Math.PI * 2, pos: [H[0] + 0.002, H[1] - 0.001, H[2] + 0.001], normal: n, flat: 1.25 }),
  ]);
  addPair({ id: "ischium", group: "ischium" }, [
    sweep({ center: curveCenter([[0.082, 0.896, -0.010], [0.078, 0.865, -0.034], [0.074, 0.840, -0.040]]), hint: V(1, 0, 0), r: (t) => [lerp(0.011, 0.013, t), lerp(0.011, 0.013, t)], segs: 10, radial: 10 }),
    ell([0.075, 0.836, -0.040], [0.016, 0.013, 0.014]),
    sweep({ center: curveCenter([[0.074, 0.838, -0.038], [0.062, 0.830, -0.018], [0.050, 0.836, 0.012], [0.042, 0.846, 0.040], [0.038, 0.852, 0.052]]), hint: V(1, 0, 0), r: () => [0.0048, 0.0065], segs: 16, radial: 8 }),
  ]);
  addPair({ id: "pubis", group: "pubis" }, [
    sweep({ center: curveCenter([[0.078, 0.896, 0.022], [0.060, 0.893, 0.044], [0.035, 0.890, 0.066], [0.012, 0.884, 0.078]]), hint: V(0, 1, 0), r: (t) => [lerp(0.0075, 0.0060, t), lerp(0.0085, 0.0075, t)], segs: 14, radial: 10 }),
    ell([0.026, 0.897, 0.074], [0.006, 0.005, 0.006]), ell([0.007, 0.874, 0.079], [0.007, 0.016, 0.006]),
    sweep({ center: curveCenter([[0.010, 0.866, 0.078], [0.028, 0.852, 0.068], [0.038, 0.851, 0.052]]), hint: V(0, 1, 0), r: () => [0.0045, 0.0052], segs: 10, radial: 8 }),
  ]);
}

/* ===================================================================== */
/*  LEG + FOOT                                                           */
/* ===================================================================== */
function buildLeg({ addPair }) {
  const big = { w: 22, h: 16 };
  addPair({ id: "femur", group: "femur" }, [
    ell([0.088, 0.917, 0.003], [0.0245, 0.0245, 0.0245], big), rod([0.090, 0.915, 0.003], [0.115, 0.888, 0.001], 0.0125, 0.0140),
    ell([0.122, 0.895, -0.004], [0.011, 0.014, 0.015]), ell([0.099, 0.858, -0.012], [0.0065, 0.009, 0.007]),
    longBone([0.110, 0.884, 0.0], [0.064, 0.545, 0.004],
      (t) => [0.0135 * (1 + 0.25 * (1 - ss(0, 0.12, t))) + 0.0085 * ss(0.78, 1, t), 0.0140 * (1 + 0.2 * (1 - ss(0, 0.12, t))) + 0.0050 * ss(0.78, 1, t)],
      { bow: (t) => V(0, 0, 0.018 * Math.sin(Math.PI * t)), segs: 28, radial: 14 }),
    ell([0.045, 0.518, -0.004], [0.0215, 0.0245, 0.0295], big), ell([0.083, 0.518, -0.004], [0.0210, 0.0240, 0.0285], big), ell([0.064, 0.530, 0.022], [0.020, 0.020, 0.012]),
  ]);
  addPair({ id: "patella", group: "patella" }, [ell([0.064, 0.522, 0.049], [0.0215, 0.0245, 0.0095], { ...big, rot: [0.1, 0, 0] })]);
  addPair({ id: "tibia", group: "tibia" }, [
    ell([0.046, 0.486, 0.004], [0.0235, 0.008, 0.0285], big), ell([0.083, 0.488, 0.002], [0.0215, 0.008, 0.026], big),
    ell([0.064, 0.452, 0.030], [0.009, 0.017, 0.010]), ell([0.064, 0.495, 0.004], [0.007, 0.008, 0.007]),
    longBone([0.064, 0.478, 0.008], [0.060, 0.098, 0.004],
      (t) => [lerp(0.0140, 0.0115, ss(0, 0.5, t)) + 0.0040 * ss(0.88, 1, t), lerp(0.0185, 0.0150, ss(0, 0.5, t)) - 0.002 * ss(0.88, 1, t)], { segs: 26, radial: 12 }),
    ell([0.050, 0.082, 0.0], [0.0095, 0.0165, 0.0105]), ell([0.062, 0.088, 0.004], [0.0155, 0.008, 0.016]),
  ]);
  addPair({ id: "fibula", group: "fibula" }, [
    longBone([0.093, 0.470, -0.010], [0.083, 0.092, -0.012], (t) => [0.0050, 0.0045 + 0.0010 * Math.sin(Math.PI * t)],
      { bow: (t) => V(0.003 * Math.sin(Math.PI * t), 0, -0.004 * Math.sin(Math.PI * t)), segs: 22 }),
    ell([0.094, 0.476, -0.010], [0.0092, 0.0092, 0.0092]), ell([0.083, 0.082, -0.012], [0.0075, 0.0185, 0.0105]),
  ]);

  /* tarsals */
  const sm = { w: 12, h: 9 };
  addPair({ id: "calcaneus", group: "calcaneus" }, [ell([0.070, 0.032, -0.040], [0.017, 0.027, 0.040], { rot: [-0.15, 0, 0], w: 16, h: 12 }), ell([0.070, 0.012, -0.060], [0.012, 0.010, 0.010], sm)]);
  addPair({ id: "talus", group: "talus" }, [ell([0.065, 0.066, -0.002], [0.020, 0.014, 0.026], { w: 16, h: 12 }), ell([0.062, 0.056, 0.022], [0.010, 0.009, 0.012], sm)]);
  addPair({ id: "navicular", group: "navicular" }, [ell([0.056, 0.048, 0.036], [0.012, 0.014, 0.006], sm)]);
  addPair({ id: "cuboid", group: "cuboid" }, [ell([0.085, 0.036, 0.036], [0.012, 0.011, 0.014], sm)]);
  [[0.047, 0.040, 0.054, 0.0075, 0.0125, 0.010], [0.062, 0.043, 0.053, 0.0075, 0.010, 0.008], [0.075, 0.040, 0.054, 0.008, 0.0105, 0.0095]]
    .forEach(([x, y, z, a, b, c], i) => addPair({ id: `cuneiform_${i + 1}`, group: "cuneiform", index: i + 1 }, [ell([x, y, z], [a, b, c], sm)]));

  /* metatarsals + toes */
  const mts = [
    [[0.046, 0.036, 0.062], [0.040, 0.016, 0.145], 0.0072], [[0.060, 0.040, 0.060], [0.057, 0.014, 0.158], 0.0048],
    [[0.073, 0.038, 0.060], [0.075, 0.013, 0.150], 0.0046], [[0.085, 0.034, 0.056], [0.092, 0.012, 0.142], 0.0044],
    [[0.094, 0.030, 0.046], [0.108, 0.011, 0.130], 0.0044],
  ];
  const slim = (A, B, r) => shaft(A, B, { hint: V(1, 0, 0), segs: 8, radial: 8, r: (t) => [r * (0.8 + 0.5 * Math.exp(-((t / 0.14) ** 2)) + 0.5 * Math.exp(-(((1 - t) / 0.14) ** 2))), r * (0.8 + 0.45 * Math.exp(-((t / 0.14) ** 2)) + 0.45 * Math.exp(-(((1 - t) / 0.14) ** 2)))] });
  mts.forEach(([A, B, r], i) => addPair({ id: `mt_${i + 1}`, group: "metatarsal", index: i + 1 }, i === 4 ? [slim(A, B, r), ell([0.098, 0.028, 0.044], [0.006, 0.006, 0.008], sm)] : [slim(A, B, r)]));
  const toeLens = [[0.030, 0, 0.025], [0.020, 0.011, 0.009], [0.019, 0.011, 0.009], [0.017, 0.010, 0.008], [0.014, 0.008, 0.007]];
  const segNames = ["proximal", "middle", "distal"];
  mts.forEach(([, head, r], f) => {
    const d = V(f === 0 ? -0.04 : (f - 2) * 0.05, -0.02, 1).normalize();
    let p = V(...head).addScaledVector(d, 0.0035);
    toeLens[f].forEach((L, s) => {
      if (!L) return;
      const q = p.clone().addScaledVector(d, L);
      addPair({ id: `ph_foot_${f + 1}_${segNames[s]}`, group: "phalanx_foot", finger: f + 1, seg: segNames[s] }, [slim([p.x, p.y, p.z], [q.x, q.y, q.z], r * (f === 0 ? 0.95 : 0.7) * (1 - 0.1 * s))]);
      p = q.clone().addScaledVector(d, 0.0030);
    });
  });
}
