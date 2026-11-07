/**
 * Interactive 3D skeleton viewer. mountSkeleton(host) builds the UI inside
 * `host`, loads the procedural skeleton and returns { dispose() }.
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { buildSkeleton } from "./skeleton-builder.js";
import { GROUPS, REGIONS, UI, boneNames, boneInfo, regionOf, quizGroups, groupName, norm } from "./skeleton-data.js";

const ACCENT = 0x19d3c0, GOOD = 0x2ecc71, BAD = 0xff5a5f;
const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  quiz: '<path d="M9 9a3 3 0 1 1 4.5 2.6c-1 .6-1.5 1.1-1.5 2.4M12 17.5v.01"/><circle cx="12" cy="12" r="9.5"/>',
  rotate: '<path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v5h-5"/>',
  explode: '<path d="M12 3v6M12 15v6M3 12h6M15 12h6M6 6l3.5 3.5M14.5 14.5 18 18M18 6l-3.5 3.5M9.5 14.5 6 18"/>',
  focus: '<circle cx="12" cy="12" r="3"/><path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4"/>',
  reset: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  full: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
};
const icon = (n, s = 20) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[n]}</svg>`;

export async function mountSkeleton(host, opts = {}) {
  const lang = opts.lang || (document.documentElement.lang === "ar" ? "ar" : "en");
  const other = lang === "ar" ? "en" : "ar";
  const T = UI[lang];
  const dir = lang === "ar" ? "rtl" : "ltr";
  const regionName = (id) => REGIONS.find((r) => r.id === id)[lang];

  host.innerHTML = `
  <div class="sk-root" dir="${dir}">
    <canvas class="sk-canvas"></canvas>
    <div class="sk-top"><div class="sk-chips" role="tablist"></div></div>
    <div class="sk-tools">
      <button data-t="search" title="${T.search}">${icon("search")}</button>
      <button data-t="quiz" title="${T.quiz}">${icon("quiz")}</button>
      <button data-t="rotate" class="on" title="${T.rotate}">${icon("rotate")}</button>
      <button data-t="explode" title="${T.explode}">${icon("explode")}</button>
      <button data-t="focus" class="on" title="${T.focus}">${icon("focus")}</button>
      <button data-t="reset" title="${T.reset}">${icon("reset")}</button>
      <button data-t="full" title="${T.fullscreen}">${icon("full")}</button>
    </div>
    <div class="sk-explode" hidden><span>${T.explode}</span><input type="range" min="0" max="100" value="0" aria-label="${T.explode}"></div>
    <div class="sk-hint">${T.hint}</div>
    <svg class="sk-leader" aria-hidden="true"><line/></svg>
    <div class="sk-pin" hidden></div>
    <div class="sk-label" hidden></div>
    <div class="sk-tip" hidden></div>
    <aside class="sk-card" hidden></aside>
    <aside class="sk-search" hidden>
      <div class="sk-search-head"><input type="search" placeholder="${T.search}" autocomplete="off"><button class="sk-x" aria-label="${T.close}">${icon("close", 18)}</button></div>
      <div class="sk-list"></div>
    </aside>
    <div class="sk-quiz" hidden></div>
    <div class="sk-loading"><div class="sk-spin"></div><p>${T.loading}</p></div>
  </div>`;
  const root = host.querySelector(".sk-root");
  const $ = (s) => root.querySelector(s);
  const canvas = $(".sk-canvas"), loading = $(".sk-loading");

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  } catch {
    loading.innerHTML = `<p>${T.noWebgl}</p>`;
    return { dispose() { host.innerHTML = ""; } };
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const isDark = () => document.documentElement.dataset.theme === "dark";
  const applyTheme = () => { renderer.toneMappingExposure = isDark() ? 1.05 : 0.92; };
  applyTheme();
  const themeObs = new MutationObserver(applyTheme);
  themeObs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envTex; scene.environmentIntensity = 0.32;
  const camera = new THREE.PerspectiveCamera(30, 1, 0.03, 30);
  const HOME = { pos: new THREE.Vector3(0.8, 1.14, 4.55), target: new THREE.Vector3(0, 0.82, 0) };
  camera.position.copy(HOME.pos);
  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(HOME.target);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 0.12, maxDistance: 6, maxPolarAngle: 1.85, autoRotate: true, autoRotateSpeed: 0.9, screenSpacePanning: true, rotateSpeed: 0.8, zoomSpeed: 0.9 });
  controls.update();

  /* ---- lights & stage ---- */
  scene.add(new THREE.HemisphereLight(0xffffff, 0x5f7a7c, 0.35));
  const key = new THREE.DirectionalLight(0xffffff, 1.75);
  key.position.set(1.8, 3.4, 3.2); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.012;
  Object.assign(key.shadow.camera, { left: -1.1, right: 1.1, top: 2.1, bottom: -0.2, near: 0.5, far: 9 });
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xa6dcff, 0.55); fill.position.set(-3, 1.6, 2.2); scene.add(fill);
  const rim1 = new THREE.DirectionalLight(0x4ee0cc, 1.2); rim1.position.set(-2, 2.6, -3.6); scene.add(rim1);
  const rim2 = new THREE.DirectionalLight(0xc4b5ff, 0.8); rim2.position.set(2.4, 2.2, -3); scene.add(rim2);

  const floor = new THREE.Mesh(new THREE.CircleGeometry(1.1, 64), new THREE.ShadowMaterial({ opacity: 0.17 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const glowTex = (() => {
    const c = document.createElement("canvas"); c.width = c.height = 256; const g = c.getContext("2d");
    const gr = g.createRadialGradient(128, 128, 10, 128, 128, 128);
    gr.addColorStop(0, "rgba(25,211,192,0.38)"); gr.addColorStop(0.55, "rgba(25,211,192,0.12)"); gr.addColorStop(1, "rgba(25,211,192,0)");
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c);
  })();
  const glow = new THREE.Mesh(new THREE.CircleGeometry(0.95, 64), new THREE.MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false }));
  glow.rotation.x = -Math.PI / 2; glow.position.y = 0.002; scene.add(glow);
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.46, 0.475, 96), new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: 0.55, depthWrite: false }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.003; scene.add(ring);

  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));   // let the spinner paint
  /* ---- the skeleton ---- */
  const loadingText = loading.querySelector("p");
  const { bones, decor } = await buildSkeleton((f) => { loadingText.textContent = `${T.loading} ${Math.round(f * 100)}%`; });
  const skel = new THREE.Group(); scene.add(skel);
  const baseMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0, side: THREE.DoubleSide, emissive: new THREE.Color(ACCENT), emissiveIntensity: 0 });
  const ORIGIN = new THREE.Vector3(0, 0.95, 0);
  const parts = bones.map((bone) => {
    const mesh = new THREE.Mesh(bone.geometry, baseMat.clone());
    mesh.castShadow = true; mesh.receiveShadow = true;
    const g = bone.geometry; g.computeBoundingBox(); g.computeBoundingSphere();
    const center = g.boundingBox.getCenter(new THREE.Vector3());
    const dir = center.clone().sub(ORIGIN); dir.y *= 0.6; dir.multiplyScalar(0.6);
    const p = { mesh, bone, region: regionOf(bone), center, radius: g.boundingSphere.radius, dir, op: 0, opT: 1, em: 0, emT: 0, flash: null, names: boneNames(bone) };
    mesh.userData.p = p; skel.add(mesh);
    return p;
  });
  const decorMats = { cartilage: new THREE.MeshStandardMaterial({ color: 0xb7d2dc, roughness: 0.5 }), dark: new THREE.MeshStandardMaterial({ color: 0x070505, roughness: 1 }) };
  const decorMeshes = decor.map((d) => { const m = new THREE.Mesh(d.geometry, decorMats[d.kind]); m.castShadow = d.kind === "cartilage"; m.userData.region = d.region; skel.add(m); return m; });
  const regionSphere = {};
  for (const r of REGIONS) {
    const box = new THREE.Box3();
    parts.filter((p) => p.region === r.id).forEach((p) => { box.expandByPoint(p.center.clone().addScalar(p.radius)); box.expandByPoint(p.center.clone().addScalar(-p.radius)); });
    regionSphere[r.id] = box.getBoundingSphere(new THREE.Sphere());
  }
  loading.classList.add("done");
  setTimeout(() => loading.remove(), 600);

  /* ---- state ---- */
  const state = { selected: null, hovered: null, region: null, focus: true, groupMode: false, ex: 1, exT: 1 };
  const quiz = { on: false, queue: [], i: 0, score: 0, tries: 0, N: 10, target: null, locked: false };
  const name1 = (p) => p.names[lang], name2 = (p) => p.names[other];
  let pickList = parts.map((p) => p.mesh);
  const rebuildPick = () => { pickList = parts.filter((p) => !state.region || p.region === state.region).map((p) => p.mesh); };
  setTimeout(() => { state.exT = 0; }, 450);                                    // assemble animation

  /* ---- camera tween ---- */
  let tween = null;
  const flyTo = (target, position, dur = 0.85) => { tween = { t0: performance.now(), dur: dur * 1000, fT: controls.target.clone(), tT: target.clone(), fP: camera.position.clone(), tP: position.clone() }; };
  const fitDistance = (radius) => {
    const vf = THREE.MathUtils.degToRad(camera.fov) / 2, hf = Math.atan(Math.tan(vf) * camera.aspect), f = Math.min(vf, hf);
    return Math.max(0.2, (radius * 1.35) / Math.sin(f));
  };
  const flyToSphere = (c, r) => {
    const d = fitDistance(r), dirv = camera.position.clone().sub(controls.target).normalize();
    flyTo(c, c.clone().addScaledVector(dirv, d));
  };
  const stopAuto = () => { if (controls.autoRotate) { controls.autoRotate = false; setTool("rotate", false); } };
  controls.addEventListener("start", () => { tween = null; stopAuto(); });

  /* ---- chips ---- */
  const chips = $(".sk-chips");
  chips.innerHTML = [`<button class="on" data-r="">${T.all}</button>`, ...REGIONS.map((r) => `<button data-r="${r.id}">${r[lang]}</button>`)].join("");
  chips.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    chips.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    setRegion(b.dataset.r || null);
  });
  function setRegion(id) {
    state.region = id; rebuildPick(); stopAuto();
    if (state.selected && id && state.selected.region !== id) deselect();
    if (id) { const s = regionSphere[id]; flyToSphere(s.center, s.radius * 0.95); } else if (!state.selected) flyTo(HOME.target, HOME.pos);
  }

  /* ---- selection / card / label ---- */
  const card = $(".sk-card"), label = $(".sk-label"), pin = $(".sk-pin"), leader = $(".sk-leader line"), tip = $(".sk-tip");
  function select(p, { fly = true } = {}) {
    state.selected = p; state.groupMode = false; stopAuto();
    const info = boneInfo(p.bone), sameGroup = parts.filter((x) => x.bone.group === p.bone.group).length;
    const side = p.bone.side && T.side[p.bone.side];
    card.innerHTML = `
      <button class="sk-x" aria-label="${T.close}">${icon("close", 18)}</button>
      <h3>${name1(p)}</h3>
      <p class="sk-sub">${name2(p)}${p.names.la ? ` · <i>${p.names.la}</i>` : ""}</p>
      <div class="sk-badges">${[...info.badges.map((b) => `<span>${b[lang]}</span>`), side ? `<span class="side">${side}</span>` : ""].join("")}</div>
      <p class="sk-desc">${info.desc[lang]}</p>
      ${info.fact ? `<div class="sk-fact"><b>💡 ${T.didYouKnow}</b><span>${info.fact[lang]}</span></div>` : ""}
      ${sameGroup > 1 ? `<button class="sk-hl">${T.highlightAll} (${sameGroup})</button>` : ""}`;
    card.hidden = false; card.classList.remove("pop"); void card.offsetWidth; card.classList.add("pop");
    label.innerHTML = `<b>${name1(p)}</b><small>${name2(p)}</small>`;
    label.hidden = false; pin.hidden = false; $(".sk-hint").classList.add("gone");
    if (fly) flyToSphere(p.center.clone().add(p.mesh.position), Math.max(p.radius, 0.012));
  }
  function deselect() { state.selected = null; state.groupMode = false; card.hidden = true; label.hidden = true; pin.hidden = true; leader.removeAttribute("x2"); }
  card.addEventListener("click", (e) => {
    if (e.target.closest(".sk-x")) { deselect(); if (!state.region) flyTo(HOME.target, HOME.pos); return; }
    const hl = e.target.closest(".sk-hl");
    if (hl && state.selected) {
      state.groupMode = !state.groupMode;
      hl.textContent = state.groupMode ? T.highlighting : `${T.highlightAll} (${parts.filter((x) => x.bone.group === state.selected.bone.group).length})`;
      hl.classList.toggle("on", state.groupMode);
    }
  });

  /* ---- picking ---- */
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  const pick = (cx, cy) => {
    const r = canvas.getBoundingClientRect();
    ndc.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickList, false)[0];
    return hit ? hit.object.userData.p : null;
  };
  let down = null, move = null, hoverDirty = false;
  canvas.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  canvas.addEventListener("pointerup", (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y), dt = performance.now() - down.t; down = null;
    if (moved > 6 || dt > 600) return;
    const p = pick(e.clientX, e.clientY);
    if (quiz.on) return answer(p);
    if (p) select(p); else if (state.selected) { deselect(); if (!state.region) flyTo(HOME.target, HOME.pos); }
  });
  canvas.addEventListener("pointermove", (e) => { if (e.pointerType === "mouse" && !e.buttons) { move = { x: e.clientX, y: e.clientY }; hoverDirty = true; } });
  canvas.addEventListener("pointerleave", () => { state.hovered = null; tip.hidden = true; hoverDirty = false; });
  const updateHover = () => {
    if (!hoverDirty || !move) return; hoverDirty = false;
    const p = pick(move.x, move.y); state.hovered = p;
    canvas.style.cursor = p ? "pointer" : "grab";
    if (p && !quiz.on) {
      const r = root.getBoundingClientRect();
      tip.textContent = name1(p); tip.hidden = false;
      tip.style.transform = `translate(${move.x - r.left + 14}px, ${move.y - r.top + 16}px)`;
    } else tip.hidden = true;
  };

  /* ---- tools ---- */
  const tools = $(".sk-tools"), exBox = $(".sk-explode"), exInput = exBox.querySelector("input");
  function setTool(n, on) { tools.querySelector(`[data-t="${n}"]`)?.classList.toggle("on", on); }
  tools.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const t = b.dataset.t;
    if (t === "rotate") { controls.autoRotate = !controls.autoRotate; setTool("rotate", controls.autoRotate); }
    else if (t === "explode") { exBox.hidden = !exBox.hidden; setTool("explode", !exBox.hidden); if (!exBox.hidden && state.exT === 0) { exInput.value = 55; state.exT = 0.55; } }
    else if (t === "focus") { state.focus = !state.focus; setTool("focus", state.focus); }
    else if (t === "reset") { deselect(); chips.querySelector("button").click(); state.exT = 0; exInput.value = 0; flyTo(HOME.target, HOME.pos); }
    else if (t === "full") { if (document.fullscreenElement) document.exitFullscreen(); else root.requestFullscreen?.(); }
    else if (t === "search") openSearch();
    else if (t === "quiz") quiz.on ? endQuiz() : startQuiz();
  });
  exInput.addEventListener("input", () => { state.exT = exInput.value / 100; });

  /* ---- search ---- */
  const searchBox = $(".sk-search"), list = $(".sk-list"), sInput = searchBox.querySelector("input");
  const sorted = [...parts].sort((a, b) => REGIONS.findIndex((r) => r.id === a.region) - REGIONS.findIndex((r) => r.id === b.region));
  const index = sorted.map((p) => { const r = REGIONS.find((x) => x.id === p.region); return { p, key: norm(`${p.names.ar} ${p.names.en} ${p.names.la || ""} ${r.ar} ${r.en}`) }; });
  function renderList(q) {
    const words = norm(q.trim()).split(/\s+/).filter(Boolean);
    const items = index.filter((x) => words.every((w) => x.key.includes(w))).slice(0, 80);
    list.innerHTML = items.length ? items.map(({ p }) => `<button data-i="${parts.indexOf(p)}"><span class="dot r-${p.region}"></span><b>${name1(p)}</b><small>${name2(p)}</small></button>`).join("") : `<p class="none">${T.noResults}</p>`;
  }
  function openSearch() { if (quiz.on) return; searchBox.hidden = false; sInput.value = ""; renderList(""); setTimeout(() => sInput.focus(), 50); }
  const closeSearch = () => { searchBox.hidden = true; };
  sInput.addEventListener("input", () => renderList(sInput.value));
  searchBox.querySelector(".sk-x").addEventListener("click", closeSearch);
  list.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const p = parts[+b.dataset.i];
    if (state.region && p.region !== state.region) { chips.querySelector("button").click(); }
    closeSearch(); select(p);
  });

  /* ---- quiz ---- */
  const quizUI = $(".sk-quiz");
  const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
  function startQuiz() {
    closeSearch(); deselect(); chips.querySelector("button").click(); stopAuto();
    state.exT = 0; exInput.value = 0; exBox.hidden = true; setTool("explode", false);
    Object.assign(quiz, { on: true, queue: shuffle(quizGroups()).slice(0, quiz.N), i: 0, score: 0, tries: 0, locked: false });
    setTool("quiz", true); quizUI.hidden = false; root.classList.add("quizzing"); flyTo(HOME.target, HOME.pos); ask();
  }
  function renderQuiz(msg = "", cls = "") {
    const g = quiz.target;
    quizUI.innerHTML = `
      <div class="q-row"><span class="q-score">${T.quizScore}: ${quiz.score}/${quiz.N}</span><span class="q-n">${quiz.i + 1} ${T.quizOf} ${quiz.N}</span></div>
      <div class="q-ask">${T.quizFind} <b>${groupName(g)[lang]}</b>${quiz.tries >= 2 ? `<small> (${regionName(GROUPS[g].region)})</small>` : ""}</div>
      <div class="q-msg ${cls}">${msg || "&nbsp;"}</div>
      <div class="q-btns"><button data-q="skip">${T.quizSkip}</button><button data-q="stop">${T.quizStop}</button></div>`;
  }
  function ask() { quiz.target = quiz.queue[quiz.i]; quiz.tries = 0; quiz.locked = false; renderQuiz(); }
  const flash = (p, color, ms = 800) => { p.flash = { color, until: performance.now() + ms }; };
  function answer(p) {
    if (!p || quiz.locked) return;
    if (p.bone.group === quiz.target) {
      quiz.score++; quiz.locked = true; flash(p, GOOD, 1000); renderQuiz(T.quizOk, "ok");
      setTimeout(next, 1000);
    } else {
      quiz.tries++; flash(p, BAD, 700); renderQuiz(`${T.quizNo} ${name1(p)} — ${T.quizTry}`, "no");
      if (quiz.tries === 2) { const s = regionSphere[GROUPS[quiz.target].region]; flyToSphere(s.center, s.radius * 1.05); }
    }
  }
  function next() { if (!quiz.on) return; quiz.i++; if (quiz.i >= quiz.queue.length) finishQuiz(); else ask(); }
  function finishQuiz() {
    quiz.locked = true;
    quizUI.innerHTML = `<div class="q-done"><div class="q-big">${quiz.score}<small>/${quiz.N}</small></div><p>${T.quizDone}</p><div class="q-btns"><button data-q="again">${T.quizAgain}</button><button data-q="stop">${T.close}</button></div></div>`;
  }
  function endQuiz() { quiz.on = false; quizUI.hidden = true; root.classList.remove("quizzing"); setTool("quiz", false); }
  quizUI.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.q === "skip") next(); else if (b.dataset.q === "stop") endQuiz(); else if (b.dataset.q === "again") startQuiz();
  });

  /* ---- sizing / visibility ---- */
  const resize = () => {
    const w = host.clientWidth || 600, h = host.clientHeight || 500;
    renderer.setSize(w, h, false); camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  const ro = new ResizeObserver(resize); ro.observe(host); resize();
  let visible = true;
  const io = new IntersectionObserver((en) => { visible = en[0].isIntersecting; }); io.observe(host);
  const onKey = (e) => { if (e.key === "Escape" && !document.fullscreenElement) { if (!searchBox.hidden) closeSearch(); else if (state.selected) deselect(); } };
  document.addEventListener("keydown", onKey);

  /* ---- frame loop ---- */
  const v = new THREE.Vector3();
  let raf = 0, alive = true, last = performance.now();
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const emissiveColor = new THREE.Color();
  function frame() {
    if (!alive) return;
    raf = requestAnimationFrame(frame);
    if (!visible || document.hidden) return;
    const now = performance.now(), dt = Math.min(0.25, (now - last) / 1000); last = now;
    const kOp = 1 - Math.exp(-dt * 7), kEm = 1 - Math.exp(-dt * 14), kEx = 1 - Math.exp(-dt * 4.2);
    if (tween) {
      const k = Math.min(1, (now - tween.t0) / tween.dur), e = ease(k);
      controls.target.lerpVectors(tween.fT, tween.tT, e); camera.position.lerpVectors(tween.fP, tween.tP, e);
      if (k >= 1) tween = null;
    }
    controls.update();
    updateHover();
    state.ex += (state.exT - state.ex) * kEx;
    const sel = state.selected, grp = state.groupMode && sel ? sel.bone.group : null;
    for (const p of parts) {
      let vis = state.region && p.region !== state.region ? 0.06 : 1, em = 0, col = ACCENT;
      if (sel) {
        const isSel = p === sel || (grp && p.bone.group === grp);
        if (state.focus && !isSel) vis = Math.min(vis, 0.13);
        if (isSel) em = 0.55;
      }
      if (p === state.hovered && p !== sel) em = Math.max(em, 0.34);
      if (p.flash) { if (now < p.flash.until) { em = 0.9; col = p.flash.color; } else p.flash = null; }
      p.op += (vis - p.op) * kOp; p.em += (em - p.em) * kEm;
      const m = p.mesh.material;
      m.opacity = p.op; m.transparent = p.op < 0.995; m.depthWrite = p.op > 0.85;
      m.emissiveIntensity = p.em; m.emissive.copy(emissiveColor.setHex(col));
      p.mesh.visible = p.op > 0.012; p.mesh.castShadow = p.op > 0.6;
      p.mesh.position.copy(p.dir).multiplyScalar(state.ex);
    }
    const showDecor = state.ex < 0.04 && !(sel && state.focus);   // sockets/discs only when assembled and not isolating a bone
    for (const m of decorMeshes) m.visible = showDecor && (!state.region || m.userData.region === state.region);
    ring.material.opacity = 0.4 + 0.15 * Math.sin(now / 700);
    if (sel) placeLabel(sel);
    renderer.render(scene, camera);
  }
  function placeLabel(p) {
    v.copy(p.center).add(p.mesh.position).project(camera);
    const w = host.clientWidth, h = host.clientHeight;
    if (v.z > 1 || Math.abs(v.x) > 1.2 || Math.abs(v.y) > 1.2) { label.style.opacity = 0; pin.style.opacity = 0; return; }
    const x = (v.x * 0.5 + 0.5) * w, y = (-v.y * 0.5 + 0.5) * h;
    const lw = label.offsetWidth, lh = label.offsetHeight, right = x < w * 0.5;
    const lx = Math.max(8, Math.min(w - lw - 8, right ? x + 54 : x - 54 - lw)), ly = Math.max(64, Math.min(h - lh - 12, y - 56));
    label.style.opacity = 1; pin.style.opacity = 1;
    label.style.transform = `translate(${lx}px, ${ly}px)`;
    pin.style.transform = `translate(${x}px, ${y}px)`;
    const ex = right ? lx : lx + lw, ey = ly + lh / 2;
    leader.setAttribute("x1", x); leader.setAttribute("y1", y); leader.setAttribute("x2", ex); leader.setAttribute("y2", ey);
  }
  frame();

  return {
    api: {
      select: (id) => { const p = parts.find((x) => x.bone.id === id); if (p) select(p); },
      /** client-space position of a bone's centre (handy for tests/tours) */
      screenOf: (id) => {
        const p = parts.find((x) => x.bone.id === id); if (!p) return null;
        const r = canvas.getBoundingClientRect(), q = p.center.clone().add(p.mesh.position).project(camera);
        return { x: r.left + (q.x * 0.5 + 0.5) * r.width, y: r.top + (-q.y * 0.5 + 0.5) * r.height };
      },
      parts,
    },
    dispose() {
      alive = false; cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); themeObs.disconnect();
      document.removeEventListener("keydown", onKey); controls.dispose();
      parts.forEach((p) => { p.mesh.geometry.dispose(); p.mesh.material.dispose(); });
      decor.forEach((d) => d.geometry.dispose());
      glowTex.dispose(); envTex.dispose(); pmrem.dispose(); renderer.dispose(); renderer.forceContextLoss();
      host.innerHTML = "";
    },
  };
}
