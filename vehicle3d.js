/* ================= 00 合规孪生(3D) =================
   独立 ES module,加载 vendor/three/ 本地化 Three.js。
   依赖 index.html 内联 classic <script> 中已定义的全局:
   DIMS, recs(), byCountry(), sbFetchAll, esc, $, $$, enhanceCountrySelect, refreshSelFilter, switchTab
   本模块通过 window.veh3dOnData 暴露一个钩子,供 index.html 的 renderAll() 在法规数据就绪后调用,
   以刷新详情面板里依赖真实数据的数字(不阻塞 3D 场景本身的加载)。 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const MODEL_URL = "./vendor/models/CarConcept/CarConcept.glb";
const ZONES_URL = "./data/vehicle_zones.json";

let ZONES = [];            // 合并静态种子 + 团队覆盖层后的区域定义数组
let nodeToZone = new Map();// gltf 节点名(小写) -> zoneId
let curZoneId = null;
let curCountry = "";       // "" = 全部国家(聚合)
let scene, camera, renderer, controls, carRoot, raycaster, hoverObj, hoverOrigEmissive;

async function loadZones() {
  const seedResp = await fetch(ZONES_URL);
  const seed = await seedResp.json();
  const base = Array.isArray(seed.zones) ? seed.zones : [];
  let overrides = [];
  try {
    overrides = await sbFetchAll("vehicle_zone_overrides", "zone_id,data");
  } catch (e) {
    console.error("vehicle_zone_overrides 读取失败(不阻断静态种子展示):", e);
  }
  const ovrMap = new Map(overrides.filter(o => o.data && typeof o.data === "object").map(o => [o.zone_id, o.data]));
  ZONES = base.map(z => ovrMap.has(z.id) ? Object.assign({}, z, ovrMap.get(z.id)) : z);
  nodeToZone = new Map();
  ZONES.forEach(z => (z.gltf_nodes || []).forEach(n => nodeToZone.set(String(n).toLowerCase(), z.id)));
}

function zoneById(id) { return ZONES.find(z => z.id === id) || null; }

/* 匹配规则同 CLAUDE.md §3.2 layer 3 兜底:dims 命中优先,否则按 domain_keywords 正则匹配 domain/dimText */
function zoneMatch(r, zone) {
  if (Array.isArray(r.dims) && r.dims.length) {
    return r.dims.some(d => zone.dims.includes(d));
  }
  const kws = zone.domain_keywords || [];
  if (!kws.length) return false;
  const text = (r.domain || "") + " " + (r.dimText || "");
  return kws.some(k => text.includes(k));
}

/* 与 CLAUDE.md §3.5 完全一致:单维度 ≥3 条=绿 1-2 条=黄 0 条=红。不发明新的百分比口径 */
function zoneStats(zoneId, country) {
  const zone = zoneById(zoneId);
  if (!zone) return null;
  const all = (typeof recs === "function") ? recs() : [];
  const matched = all.filter(r => zoneMatch(r, zone));
  if (country) {
    const inCountry = matched.filter(r => r.country === country);
    const n = inCountry.length;
    const state = n >= 3 ? "g" : n >= 1 ? "a" : "r";
    return { mode: "country", country, count: n, state, total: matched.length };
  }
  const byCty = {};
  matched.forEach(r => { byCty[r.country] = (byCty[r.country] || 0) + 1; });
  const countriesWithData = Object.keys((typeof byCountry === "function") ? byCountry() : {});
  let green = 0;
  countriesWithData.forEach(c => { if ((byCty[c] || 0) >= 3) green++; });
  const state = matched.length === 0 ? "r" : (green === countriesWithData.length && countriesWithData.length > 0 ? "g" : "a");
  return { mode: "agg", greenCountries: green, totalCountries: countriesWithData.length, count: matched.length, state };
}

function stateLabel(s) {
  return { g: "✓ 覆盖良好", a: "⚠ 弱覆盖", r: "✗ 空白" }[s] || "—";
}

function fillCountrySelect() {
  const sel = $("#veh3d-cty");
  if (!sel) return;
  const cur = sel.value;
  const cs = Object.keys((typeof byCountry === "function") ? byCountry() : {}).sort((a, b) => a.localeCompare(b, "zh"));
  sel.innerHTML = '<option value="">全部国家(聚合)</option>' + cs.map(c => `<option value="${c}">${c}</option>`).join("");
  if (cs.includes(cur)) sel.value = cur;
  if (!sel._enh && typeof enhanceCountrySelect === "function") enhanceCountrySelect("veh3d-cty");
  if (typeof refreshSelFilter === "function") refreshSelFilter(sel);
  sel.onchange = () => { curCountry = sel.value; if (curZoneId) showZoneDetail(curZoneId); };
}

function renderVeh3DKPIs() {
  const host = $("#veh3d-kpis");
  if (!host) return;
  const all = (typeof recs === "function") ? recs() : [];
  const total = all.length;
  const zoneAgg = ZONES.map(z => zoneStats(z.id, ""));
  const readyN = zoneAgg.filter(s => s && s.state === "g").length;
  const blankN = zoneAgg.filter(s => s && s.count === 0).length;
  const tiles = [
    { lbl: "监控部件区域数", v: ZONES.length, meta: "基于 CarConcept 模型实际节点划分" },
    { lbl: "全库法规总数", v: total, meta: total ? "与「总览排行」同口径" : "数据加载中…" },
    { lbl: "就绪区域数", v: readyN, meta: "全部国家该区域均 ≥3 条", hot: readyN > 0 },
    { lbl: "空白区域数", v: blankN, meta: "尚无匹配法规记录" },
  ];
  host.innerHTML = tiles.map(t => `<div class="kpi${t.hot ? " hot" : ""}"><div class="lbl">${esc(t.lbl)}</div>
    <div class="v">${t.v}</div><div class="meta">${esc(t.meta)}</div></div>`).join("");
}

function showZoneDetail(zoneId) {
  curZoneId = zoneId;
  const zone = zoneById(zoneId);
  const host = $("#veh3d-detail");
  if (!host) return;
  if (!zone) {
    host.innerHTML = `<div class="pd-lbl">车辆区域</div><div class="pd-title">未识别部件</div>
      <div class="pd-desc veh3d-empty">该部件尚未纳入区域划分,或不在当前合规监控范围内。</div>`;
    return;
  }
  const st = zoneStats(zoneId, curCountry);
  const dot = st ? `<span class="veh3d-dot ${st.state}"></span>` : "";
  const statusText = !st ? "法规数据加载中…"
    : st.mode === "country" ? `${dot}${esc(curCountry)}:${stateLabel(st.state)}(${st.count} 条)`
      : `${dot}聚合:${st.greenCountries}/${st.totalCountries} 国已达标覆盖`;
  const dimsRow = zone.dims.map(i =>
    `<div class="vd-row" data-dim="${i}">${esc((typeof DIMS !== "undefined" ? DIMS[i] : "维度" + i))}</div>`
  ).join("");
  host.innerHTML = `
    <div class="pd-lbl">${esc(zoneId)} · ${(zone.gltf_nodes || []).length} 个模型节点</div>
    <div class="pd-title">${esc(zone.label_cn)}</div>
    <div class="pd-local">${esc(zone.label_en)}</div>
    <div class="veh3d-status">${statusText}</div>
    <div class="veh3d-badge">适用法规数 ${st ? st.count : "—"} 条</div>
    <div class="pd-desc" style="margin-top:10px">${esc(zone.desc || "")}</div>
    <div class="veh3d-dims">
      <div class="pd-lbl" style="margin-bottom:4px">涉及维度(点击跳转维度矩阵)</div>
      ${dimsRow}
    </div>
    <div class="btn light" id="veh3d-emark-link" style="margin-top:12px;text-align:center;cursor:pointer">→ 查看 E-mark 评估</div>`;
  host.querySelectorAll(".vd-row").forEach(row => {
    row.addEventListener("click", () => {
      if (typeof switchTab === "function") switchTab("p-dim");
    });
  });
  const emarkLink = host.querySelector("#veh3d-emark-link");
  if (emarkLink) emarkLink.addEventListener("click", goToEmark);
}

/* 浅联动:跳转 23 E-mark 评估标签页,并触发其惰性加载(与 index.html 主 tab-click 链一致,
   因为程序化 switchTab() 不会经过该 if-chain)。不做条目级定位——E-mark 评估工具目前
   没有 URL 参数/postMessage 接口,按 UN R 编号组织,与本页的维度分区不是一一对应关系。 */
function goToEmark() {
  if (typeof switchTab === "function") switchTab("p-emark");
  const f = document.getElementById("emark-frame");
  if (f && !f.src) f.src = f.dataset.src;
}

function sizeRenderer() {
  const host = $("#veh3d-canvas");
  if (!host || !renderer || !camera) return;
  const w = host.clientWidth || 1, h = host.clientHeight || 1;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function frameCamera(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = size.length() * 0.5 || 1;
  const vFov = camera.fov * (Math.PI / 180);
  const hFov = 2 * Math.atan(Math.tan(vFov / 2) * camera.aspect);
  const dist = Math.max(radius / Math.sin(vFov / 2), radius / Math.sin(hFov / 2)) * 1.15;
  const dir = new THREE.Vector3(0.55, 0.38, 0.75).normalize();
  camera.position.copy(center).addScaledVector(dir, dist);
  camera.near = Math.max(dist / 100, 0.01);
  camera.far = dist * 10;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.minDistance = dist * 0.3;
  controls.maxDistance = dist * 3;
  controls.update();
}

function resolveZoneFromObject(obj) {
  let o = obj;
  while (o) {
    const zid = nodeToZone.get(String(o.name || "").toLowerCase());
    if (zid) return zid;
    o = o.parent;
  }
  return null;
}

function setHover(obj) {
  if (hoverObj === obj) return;
  if (hoverObj && hoverObj.material && hoverOrigEmissive !== undefined) {
    try { hoverObj.material.emissive && hoverObj.material.emissive.copy(hoverOrigEmissive); } catch (e) {}
  }
  hoverObj = obj;
  if (obj && obj.material && obj.material.emissive) {
    hoverOrigEmissive = obj.material.emissive.clone();
    obj.material.emissive.setHex(0x33754c);
  } else {
    hoverOrigEmissive = undefined;
  }
}

function pointerToNDC(e, canvasEl) {
  const r = canvasEl.getBoundingClientRect();
  return new THREE.Vector2(
    ((e.clientX - r.left) / r.width) * 2 - 1,
    -((e.clientY - r.top) / r.height) * 2 + 1
  );
}

function wireInteraction(canvasEl) {
  let downPos = null;
  canvasEl.addEventListener("pointerdown", e => { downPos = { x: e.clientX, y: e.clientY }; });
  canvasEl.addEventListener("pointerup", e => {
    if (!downPos) return;
    const moved = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
    downPos = null;
    if (moved > 6 || !carRoot) return; // 拖拽旋转不算点击
    raycaster.setFromCamera(pointerToNDC(e, canvasEl), camera);
    const hits = raycaster.intersectObject(carRoot, true);
    if (!hits.length) return;
    const zid = resolveZoneFromObject(hits[0].object);
    showZoneDetail(zid);
  });
  canvasEl.addEventListener("pointermove", e => {
    if (!carRoot) return;
    raycaster.setFromCamera(pointerToNDC(e, canvasEl), camera);
    const hits = raycaster.intersectObject(carRoot, true);
    if (hits.length && resolveZoneFromObject(hits[0].object)) {
      setHover(hits[0].object);
      canvasEl.style.cursor = "pointer";
    } else {
      setHover(null);
      canvasEl.style.cursor = "grab";
    }
  });
  canvasEl.addEventListener("pointerleave", () => setHover(null));
}

function setLoadingProgress(pct, done, error) {
  const el = $("#veh3d-loading");
  if (!el) return;
  if (error) { el.textContent = "[ 车辆模型加载失败,请刷新重试 ]"; return; }
  if (done) { el.textContent = "[ 已加载 ]"; el.classList.add("hide"); return; }
  el.textContent = "[ 正在载入车辆模型… " + pct + "% ]";
}

let _inited = false;
async function initVeh3D() {
  if (_inited) return;
  const host = $("#veh3d-canvas");
  if (!host) return;
  _inited = true;

  await loadZones();

  const panelBg = getComputedStyle(document.documentElement).getPropertyValue("--panel2").trim() || "#e5efdd";
  scene = new THREE.Scene();
  scene.background = new THREE.Color(panelBg);

  camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.set(4, 2.4, 5);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  host.appendChild(renderer.domElement);
  sizeRenderer();

  scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2a2a, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 1.4);
  key.position.set(5, 8, 6);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.5);
  fill.position.set(-6, 3, -4);
  scene.add(fill);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  raycaster = new THREE.Raycaster();
  wireInteraction(renderer.domElement);

  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => sizeRenderer()).observe(host);
  } else {
    window.addEventListener("resize", sizeRenderer);
  }

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });

  fillCountrySelect();
  renderVeh3DKPIs();

  new GLTFLoader().load(
    MODEL_URL,
    gltf => {
      carRoot = gltf.scene;
      scene.add(carRoot);
      carRoot.updateMatrixWorld(true);
      frameCamera(carRoot);
      setLoadingProgress(100, true, false);
    },
    evt => {
      const pct = evt.total ? Math.round((evt.loaded / evt.total) * 100) : Math.round(evt.loaded / 1e5);
      setLoadingProgress(Math.min(99, pct), false, false);
    },
    err => {
      console.error("CarConcept.glb 加载失败:", err);
      setLoadingProgress(0, false, true);
    }
  );
}

/* renderAll() 在法规数据(store)就绪后调用此钩子,刷新依赖真实数据的数字;不影响 3D 场景本身的独立加载 */
window.veh3dOnData = function () {
  if (!_inited) return;
  fillCountrySelect();
  renderVeh3DKPIs();
  if (curZoneId) showZoneDetail(curZoneId);
};

function bootVeh3D() {
  initVeh3D().catch(e => {
    console.error("合规孪生(3D)初始化失败:", e);
    setLoadingProgress(0, false, true);
  });
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootVeh3D);
} else {
  bootVeh3D();
}
