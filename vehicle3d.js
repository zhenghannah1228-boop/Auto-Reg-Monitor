/* ================= 00 合规孪生(3D) =================
   独立 ES module,加载 vendor/three/ 本地化 Three.js。
   依赖 index.html 内联 classic <script> 中已定义的全局:
   DIMS, recs(), byCountry(), sbFetchAll, esc, $, $$, enhanceCountrySelect, refreshSelFilter, switchTab
   本模块通过 window.veh3dOnData 暴露一个钩子,供 index.html 的 renderAll() 在法规数据就绪后调用,
   以刷新详情面板里依赖真实数据的数字(不阻塞 3D 场景本身的加载)。 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const MODEL_URL = "./vendor/models/AudiR8/AudiR8.glb";
const COCKPIT_MODEL_URL = "./vendor/models/CockpitInterior/cockpit.glb";
const MECH_MODEL_URL = "./vendor/models/MechanicalParts/mechanical.glb";
const ZONES_URL = "./data/vehicle_zones.json";

// 实测 AudiR8.glb 整车包围盒(约 4.22×2.45×9.13)与真实 Audi R8 车身尺寸(约 1.94×1.24×4.43m)的
// 比例均值——机械零件素材本身是按真实米制建模的(见 CREDITS.md),用这一个比例统一换算成车身
// 模型自己的单位系统,不是瞎猜的缩放数。
const CAR_UNITS_PER_METER = 2.08;
// 两个零件的素材默认朝向摆到车上会显得不对(制动盘默认平放、转轴朝上,减震器默认横放)——
// 这两个修正角度是渲染截图肉眼核对过的,不是凭空猜的。
const MECH_ROT_FIX = {
  "brake-disc_body": [0, 0, Math.PI / 2],
  "shock-absorber_body": [0, 0, Math.PI / 2],
};

let ZONES = [];            // 合并静态种子 + 团队覆盖层后的区域定义数组
let nodeToZone = new Map();// gltf 节点名(小写) -> zoneId,整车视角(AudiR8.glb)用
let cockpitNodeToZone = new Map(); // gltf 节点名(小写) -> zoneId,座舱视角(cockpit.glb)用,两套模型各自独立命名空间
let curZoneId = null;
let curCountry = "";       // "" = 全部国家(聚合)
let viewMode = "ext";      // "ext" | "cockpit" —— veh3dSetView() 维护,showZoneDetail() 等需要据此区分当前在哪个 3D 场景里
let scene, camera, renderer, controls, carRoot, raycaster, hoverObj, hoverOrigEmissive;
let cockpitScene, cockpitCamera, cockpitRenderer, cockpitControls, cockpitRoot, cockpitRaycaster, cockpitHoverObj, cockpitHoverOrigEmissive;
let cockpitInited = false; // 懒加载:只在用户第一次切到座舱视角时才去拉 12MB 的 cockpit.glb
let cockpitHotspots = []; // 目前只有 airbag 一项(素材包没有对应部件),复用整车视角"虚线标签"的思路但没有占位 Box 网格
let xrayOn = false;
let hotspots = []; // [{zone, mesh, card}] —— 源模型无实体建模的维度(电池包/ECU-OTA域、
                    // 2026-09 新增的动力总成/底盘/空调/内饰等 18 个区域),用简易占位几何体 +
                    // 虚线标签展示,不冒充精细建模
let carCleanBox = null; // 整车模型刚加载完、还没加任何占位/机械零件时的包围盒缓存——hotspotWorldPos()
                         // 用这份"干净"的包围盒算比例坐标,避免大体积机械零件加入 carRoot 后
                         // Box3.setFromObject(carRoot) 把它们自己算进包围盒、污染后续区域的定位
let mechRoot = null, mechLoaded = false, mechLoading = false; // 机械零件模型(懒加载,见 loadMechanicalParts)

/* 18 个 hotspot 区域按 group 字段分 6 组,X-Ray 下按组切换显示——不然 18 张标签卡片同屏堆叠
   会完全看不清。ev/connectivity 是一期就有的默认展示组,其余 4 组默认收起,用户按需勾选。 */
const HOTSPOT_GROUPS = [
  { id: "ev", label: "三电系统" },
  { id: "connectivity", label: "智能网联" },
  { id: "powertrain", label: "动力总成" },
  { id: "chassis", label: "底盘/制动转向" },
  { id: "hvac", label: "空调" },
  { id: "interior", label: "内饰与乘员防护" },
];
let activeGroups = new Set(["ev", "connectivity"]);

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
  cockpitNodeToZone = new Map();
  ZONES.forEach(z => {
    (z.gltf_nodes || []).forEach(n => nodeToZone.set(String(n).toLowerCase(), z.id));
    (z.cockpit_nodes || []).forEach(n => cockpitNodeToZone.set(String(n).toLowerCase(), z.id));
  });
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
    { lbl: "监控部件区域数", v: ZONES.length, meta: "基于车辆模型实际节点划分" },
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
  const nodeInfo = viewMode === "cockpit"
    ? ((zone.cockpit_nodes || []).length ? `${zone.cockpit_nodes.length} 个座舱模型节点` : "占位标注 · 座舱素材无对应部件")
    : (zone.hotspot ? "占位标注 · 源模型无对应实体建模" : `${(zone.gltf_nodes || []).length} 个模型节点`);
  host.innerHTML = `
    <div class="pd-lbl">${esc(zoneId)} · ${nodeInfo}</div>
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

let _orthoHalfHeight = 1; // frameCamera() 算出的世界空间半高,resize 时按新宽高比重算 left/right,不动 top/bottom

function sizeRenderer() {
  const host = $("#veh3d-canvas");
  if (!host || !renderer || !camera) return;
  const w = host.clientWidth || 1, h = host.clientHeight || 1;
  renderer.setSize(w, h, false);
  const aspect = w / h;
  camera.left = -_orthoHalfHeight * aspect;
  camera.right = _orthoHalfHeight * aspect;
  camera.top = _orthoHalfHeight;
  camera.bottom = -_orthoHalfHeight;
  camera.updateProjectionMatrix();
}

/* 正投影(平行投影):没有消失点、物体大小不随镜头远近变化——这是业主明确要的"汽车线稿/
   工程图"效果,也顺带解决了之前透视相机贴近车身时(controls.minDistance 较小、45°广角)
   边缘部件视觉上"甩出去"的畸变问题(那不是车身数据错位,单独排查过整车 33 个网格节点的
   世界坐标包围盒,全部落在车身整体包络内;是广角透视镜头贴近物体时的固有畸变,换正投影后
   按构造就不存在这类畸变)。*/
function frameCamera(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = size.length() * 0.5 || 1;
  _orthoHalfHeight = radius * 1.15;
  const dist = radius * 4; // 正投影下相机距离不影响物体视觉大小,只要留够近远裁剪空间即可
  // 斜前方俯视角度。实测过把仰角(Y 分量)调更高(0.68)想让俯视感更明显,结果车轮在这具体
  // 模型上明显"甩出去"——这具体模型没有翼子板/轮拱内衬几何体去视觉上"接住"车轮,仰角一旦太陡,
  // 车轮的自然侧向外扩就会脱离车身正投影轮廓,看起来像飞出去(拿正投影/透视各测过一遍,现象一致,
  // 不是相机类型的问题)。0.38 这个仰角是实测干净、车轮視觉上仍贴合车身的上限附近,不再继续抬高。
  const dir = new THREE.Vector3(0.55, 0.38, 0.75).normalize();
  camera.position.copy(center).addScaledVector(dir, dist);
  camera.near = dist / 100;
  camera.far = dist * 10;
  camera.zoom = 1;
  sizeRenderer(); // 用当前画布宽高比设置 left/right/top/bottom
  controls.target.copy(center);
  controls.minZoom = 0.4;
  controls.maxZoom = 4;
  // 2026-09 排查"部分车身/车轮从画面消失"反馈时确认过:33 个网格节点在任意角度下 visible 都是
  // true、也都在视锥体内(逐网格 dump 过 Frustum.intersectsSphere),不是剔除/材质 bug——问题是
  // OrbitControls 默认极角不设限(0~180°),用户把车往下拖得足够狠时相机会转到车身水平线以下,
  // 从底盘方向往上看。这个模型只建了看得见的外观壳体,没有底盘/地板几何(underside 是空的),
  // 从那个方向看正好是"从没建模的洞往里看",格栅/保险杠这类薄且复杂的前端部件在这种反常视角下
  // 视觉上会收缩成看不见的窄边,车轮因为真实的左右外扩量在这个角度下显得像脱离车身——用实测
  // 142° 极角复现过,和"车轮飞出去"是同一类症状但触发条件不同(那次是仰角太陡,这次是能转到
  // 水平线以下)。不修渲染 hack,直接把极角限制在车身水平线以上,不让相机转到没建模的区域去。
  controls.minPolarAngle = 0.15;  // ≈8.6°,留一点余量避免正上方万向节死锁(车顶有建模,可以看)
  controls.maxPolarAngle = 1.45;  // ≈83°,不允许转到水平线以下
  controls.update();
}

/* data/vehicle_zones.json 里原先的 hotspot_pos 是手估的绝对坐标,实测和车身实际曲面对不上
   (量出来电池包一半悬在底盘外、ECU 偏出仪表台曲面),视觉上就是"贴纸贴在车上"而不是嵌入车身。
   排查过用射线从正上方往下打、找车身实际曲面来对齐——但这个素材本身只建了看得见的外观壳体,
   底盘/地板没有建模(underside 是空的),往下打的射线只会命中车顶一次,再往下就是空气,没有
   "地板"这层几何可以对齐。改为更稳的办法:hotspot_pos 存的不是绝对坐标,而是车身实际包围盒
   三轴上的比例(0~1,如 X 方向 0=最左 1=最右),运行时按当前模型的真实包围盒换算成世界坐标——
   占位盒体因此始终落在这具体模型的真实体量范围之内,不会因为手估数值偏差而钻出车身包络。 */
function hotspotWorldPos(fracPos) {
  const box = carCleanBox || (carRoot && new THREE.Box3().setFromObject(carRoot));
  if (!box) return fracPos;
  const [fx, fy, fz] = fracPos;
  return [
    box.min.x + fx * (box.max.x - box.min.x),
    box.min.y + fy * (box.max.y - box.min.y),
    box.min.z + fz * (box.max.z - box.min.z),
  ];
}

/* 电池包/ECU-OTA 域等无实体建模的维度:放一个简易占位几何体在车内大致位置(业主 2026-09 指示),
   仅在「X-Ray 透视」开启、车身变半透明后才可见——不做射线拾取,点击走下方 HTML 标签卡片,
   避免"占位盒子恰好被判定为最近命中"这种不真实的交互。 */
function buildHotspots() {
  hotspots.forEach(h => h.mesh.parent && h.mesh.parent.remove(h.mesh));
  hotspots = [];
  const layer = $("#veh3d-hotspot-layer");
  if (layer) layer.innerHTML = '<svg class="veh3d-hs-svg"></svg>';
  ZONES.filter(z => z.hotspot && Array.isArray(z.hotspot_pos)).forEach(zone => {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(0.42, 0.28, 0.55),
      new THREE.MeshStandardMaterial({ color: 0xc79a2e, emissive: 0x3a2c08, roughness: 0.4 })
    );
    mesh.userData.hotspotEl = true; // setXray() 据此跳过透视材质替换,可见性统一交给 refreshHotspotVisibility()
    mesh.position.fromArray(hotspotWorldPos(zone.hotspot_pos));
    mesh.visible = xrayOn && activeGroups.has(zone.group);
    carRoot.add(mesh);
    const card = document.createElement("div");
    card.className = "veh3d-hs-card";
    card.textContent = zone.label_cn;
    card.addEventListener("click", () => showZoneDetail(zone.id));
    if (layer) layer.appendChild(card);
    hotspots.push({ zone, mesh, card });
  });
  if (mechRoot) applyMechanicalHotspots(); // 若机械零件模型已经先加载完(用户之前开过 X-Ray),直接复用,不用重新拉取
}

/* 2026-11 第二批:engine/transmission/radiator_fan/front_suspension/rear_suspension/brakes 这
   6 个区域用 grab3d.com CC0 的真实零件模型替换占位 Box(素材/摆放方法见 CREDITS.md);
   clutch/steering_system/axle_driveshaft 等套件里没有对应零件的区域,仍保留占位 Box,不拿别的
   零件凑数。懒加载,只在用户第一次打开 X-Ray 透视时才去拉这个 ~5MB 的模型(见 loadMechanicalParts
   的调用处)。 */
function applyMechanicalHotspots() {
  if (!mechRoot || !carRoot) return;
  hotspots.forEach(hs => {
    const nodeName = hs.zone.mech_node;
    if (!nodeName) return;
    let src = null;
    mechRoot.traverse(o => { if (o.name === nodeName) src = o; });
    if (!src) return;
    const inst = src.clone();
    inst.traverse(o => { if (o.isMesh) o.userData.hotspotEl = true; });
    inst.scale.setScalar(CAR_UNITS_PER_METER);
    const rot = MECH_ROT_FIX[nodeName];
    if (rot) inst.rotation.set(rot[0], rot[1], rot[2]);
    inst.position.fromArray(hotspotWorldPos(hs.zone.hotspot_pos));
    if (hs.mesh && hs.mesh.parent) hs.mesh.parent.remove(hs.mesh);
    carRoot.add(inst);
    hs.mesh = inst;
  });
  refreshHotspotVisibility();
}

function loadMechanicalParts() {
  if (mechLoaded || mechLoading) return;
  mechLoading = true;
  new GLTFLoader().load(
    MECH_MODEL_URL,
    gltf => {
      mechRoot = gltf.scene;
      mechRoot.traverse(o => { if (o.isMesh && o.material) o.material = o.material.clone(); });
      mechRoot.updateMatrixWorld(true);
      mechLoaded = true;
      mechLoading = false;
      applyMechanicalHotspots();
    },
    undefined,
    err => {
      console.error("机械零件模型加载失败(不影响占位方块继续显示):", err);
      mechLoading = false;
    }
  );
}

/* group 勾选变化 / X-Ray 开关变化都走这一个函数,保持 mesh.visible 是唯一状态源——
   updateHotspotLayer() 每帧只看 mesh.visible,不重复判断分组逻辑。 */
function refreshHotspotVisibility() {
  hotspots.forEach(hs => { hs.mesh.visible = xrayOn && activeGroups.has(hs.zone.group); });
}

function buildGroupBar() {
  const bar = $("#veh3d-group-bar");
  if (!bar) return;
  bar.innerHTML = '<span class="veh3d-group-hint">X-Ray 透视下按系统分组显示占位标注:</span>' +
    HOTSPOT_GROUPS.map(g =>
      `<button type="button" class="veh3d-group-chip${activeGroups.has(g.id) ? " on" : ""}" data-g="${g.id}">${esc(g.label)}</button>`
    ).join("");
  bar.querySelectorAll(".veh3d-group-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      const g = btn.dataset.g;
      if (activeGroups.has(g)) activeGroups.delete(g); else activeGroups.add(g);
      btn.classList.toggle("on");
      refreshHotspotVisibility();
    });
  });
}

/* 座舱视角(2026-11 业主指示,替代此前固定机位的自绘 SVG 示意图):真实可拖动旋转/缩放的第二个
   Three.js 场景,加载 vendor/models/CockpitInterior/cockpit.glb(grab3d.com CC0 素材拼装,见
   vendor/models/CREDITS.md)。方向盘/仪表板/空调出风口/仪表盘总成(ECU-OTA 域锚点)/座椅/门饰板/
   脚垫这 7 个区域现在是真实几何节点,点击方式与整车视角完全一致(cockpit_nodes 字段,与整车视角
   的 gltf_nodes 是两套独立命名空间,见 loadZones());安全气囊素材包里没有对应部件,仍用下面的
   悬浮标签占位,不编造几何体。懒加载:只在用户第一次点"座舱视角"时才去拉这个 12MB 的模型,避免
   没人看这个视角时白白加载。 */
function resolveCockpitZoneFromObject(obj) {
  let o = obj;
  while (o) {
    const zid = cockpitNodeToZone.get(String(o.name || "").toLowerCase());
    if (zid) return zid;
    o = o.parent;
  }
  return null;
}

function setCockpitHover(obj) {
  if (cockpitHoverObj === obj) return;
  if (cockpitHoverObj && cockpitHoverObj.material && cockpitHoverOrigEmissive !== undefined) {
    try { cockpitHoverObj.material.emissive && cockpitHoverObj.material.emissive.copy(cockpitHoverOrigEmissive); } catch (e) {}
  }
  cockpitHoverObj = obj;
  if (obj && obj.material && obj.material.emissive) {
    cockpitHoverOrigEmissive = obj.material.emissive.clone();
    obj.material.emissive.setHex(0x1a5a7a); // 蓝色高光,呼应座舱视角的黑蓝 HUD 配色,不沿用整车视角的绿色
  } else {
    cockpitHoverOrigEmissive = undefined;
  }
}

function wireCockpitInteraction(canvasEl) {
  let downPos = null;
  canvasEl.addEventListener("pointerdown", e => { downPos = { x: e.clientX, y: e.clientY }; });
  canvasEl.addEventListener("pointerup", e => {
    if (!downPos) return;
    const moved = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
    downPos = null;
    if (moved > 6 || !cockpitRoot) return; // 拖拽旋转不算点击
    cockpitRaycaster.setFromCamera(pointerToNDC(e, canvasEl), cockpitCamera);
    const hits = cockpitRaycaster.intersectObject(cockpitRoot, true);
    if (!hits.length) return;
    showZoneDetail(resolveCockpitZoneFromObject(hits[0].object));
  });
  canvasEl.addEventListener("pointermove", e => {
    if (!cockpitRoot) return;
    cockpitRaycaster.setFromCamera(pointerToNDC(e, canvasEl), cockpitCamera);
    const hits = cockpitRaycaster.intersectObject(cockpitRoot, true);
    if (hits.length && resolveCockpitZoneFromObject(hits[0].object)) {
      setCockpitHover(hits[0].object);
      canvasEl.style.cursor = "pointer";
    } else {
      setCockpitHover(null);
      canvasEl.style.cursor = "grab";
    }
  });
  canvasEl.addEventListener("pointerleave", () => setCockpitHover(null));
}

function sizeCockpitRenderer() {
  const host = $("#veh3d-cockpit");
  if (!host || !cockpitRenderer || !cockpitCamera) return;
  const w = host.clientWidth || 1, h = host.clientHeight || 1;
  cockpitRenderer.setSize(w, h, false);
  cockpitCamera.aspect = w / h;
  cockpitCamera.updateProjectionMatrix();
}

/* 这套素材只有舱内部件(仪表板/座椅/门板/脚垫等),没有包裹它们的外观车身壳体——装配脚本里用
   modern-car-interior.glb 自带的 windshield_glass/steering_wheel 两个既有物体的实测世界坐标做
   拼装基准(见 CREDITS.md),"前方"是 +Z。这里取透视相机斜前方视角(与装配阶段用来验收拼装效果、
   确认过渲染正常的角度一致),让用户一进来就能看到仪表板正面,而不是从舱体背面开始看。
   如实记录一处局限:因为没有外观车身包着,拖到比较极端的角度能看到部件边缘悬空/背面裸露,
   正常浏览角度(斜前方 45°左右)不受影响,footnote 里也会提示。 */
function frameCockpitCamera(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = size.length() * 0.5 || 1;
  const dir = new THREE.Vector3(0.6, 0.55, -1).normalize();
  cockpitCamera.position.copy(center).addScaledVector(dir, radius * 1.3);
  cockpitCamera.near = radius / 50;
  cockpitCamera.far = radius * 20;
  sizeCockpitRenderer();
  cockpitControls.target.copy(center);
  cockpitControls.minDistance = radius * 0.25;
  cockpitControls.maxDistance = radius * 3;
  cockpitControls.update();
}

/* 安全气囊在素材包里没有独立部件,位置锚点取方向盘节点(asm_dash_car-dashboard_steering_wheel)
   的真实世界坐标包围盒中心——驾驶员气囊本来就装在方向盘轮毂里,这个锚点不是凑数据,只是没有
   单独的气囊几何体可供点选,所以仍用悬浮标签而不是可点击网格。 */
function buildCockpitHotspots() {
  cockpitHotspots.forEach(h => h.card.remove());
  cockpitHotspots = [];
  const layer = $("#veh3d-cockpit-labels");
  if (layer) layer.innerHTML = "";
  const zone = zoneById("airbag");
  if (!zone || !cockpitRoot) return;
  let wheelObj = null;
  cockpitRoot.traverse(o => { if (o.name === "asm_dash_car-dashboard_steering_wheel") wheelObj = o; });
  if (!wheelObj) return;
  const worldPos = new THREE.Box3().setFromObject(wheelObj).getCenter(new THREE.Vector3());
  const card = document.createElement("div");
  card.className = "veh3d-cockpit-label";
  card.textContent = zone.label_cn;
  card.addEventListener("click", () => showZoneDetail(zone.id));
  layer.appendChild(card);
  cockpitHotspots.push({ zone, worldPos, card });
}

const _cpVec = new THREE.Vector3();
function updateCockpitHotspotLayer() {
  if (!cockpitHotspots.length) return;
  const host = $("#veh3d-cockpit");
  if (!host) return;
  const w = host.clientWidth, h = host.clientHeight;
  cockpitHotspots.forEach(hs => {
    _cpVec.copy(hs.worldPos).project(cockpitCamera);
    if (_cpVec.z > 1 || _cpVec.z < -1) { hs.card.style.display = "none"; return; }
    hs.card.style.display = "block";
    hs.card.style.left = ((_cpVec.x * 0.5 + 0.5) * w) + "px";
    hs.card.style.top = ((-_cpVec.y * 0.5 + 0.5) * h) + "px";
  });
}

function setCockpitLoadingProgress(pct, done, error) {
  const el = $("#veh3d-cockpit-loading");
  if (!el) return;
  if (error) { el.textContent = "[ 座舱模型加载失败,请刷新重试 ]"; return; }
  if (done) { el.textContent = "[ 已加载 ]"; el.classList.add("hide"); return; }
  el.textContent = "[ 正在载入座舱模型… " + pct + "% ]";
}

function initCockpitScene() {
  if (cockpitInited) return;
  cockpitInited = true;
  const host = $("#veh3d-cockpit");
  if (!host) return;

  cockpitScene = new THREE.Scene();
  cockpitScene.background = new THREE.Color(0x070b11);

  cockpitCamera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);

  cockpitRenderer = new THREE.WebGLRenderer({ antialias: true });
  cockpitRenderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  host.insertBefore(cockpitRenderer.domElement, host.firstChild);
  sizeCockpitRenderer();

  cockpitScene.add(new THREE.HemisphereLight(0xffffff, 0x16202c, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(1.5, 3, 1.2);
  cockpitScene.add(key);
  const fill = new THREE.DirectionalLight(0xbfe6ff, 0.5);
  fill.position.set(-1.5, 1, -1);
  cockpitScene.add(fill);

  cockpitControls = new OrbitControls(cockpitCamera, cockpitRenderer.domElement);
  cockpitControls.enableDamping = true;
  cockpitControls.dampingFactor = 0.08;

  cockpitRaycaster = new THREE.Raycaster();
  wireCockpitInteraction(cockpitRenderer.domElement);

  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => sizeCockpitRenderer()).observe(host);
  } else {
    window.addEventListener("resize", sizeCockpitRenderer);
  }

  // 只在座舱视角可见时才渲染/更新 controls,避免切回整车视角后这个场景还在后台空转占用 GPU。
  cockpitRenderer.setAnimationLoop(() => {
    if (viewMode !== "cockpit") return;
    cockpitControls.update();
    cockpitRenderer.render(cockpitScene, cockpitCamera);
    updateCockpitHotspotLayer();
  });

  new GLTFLoader().load(
    COCKPIT_MODEL_URL,
    gltf => {
      cockpitRoot = gltf.scene;
      cockpitScene.add(cockpitRoot);
      cockpitRoot.traverse(o => { if (o.isMesh && o.material) o.material = o.material.clone(); });
      cockpitRoot.updateMatrixWorld(true);
      frameCockpitCamera(cockpitRoot);
      buildCockpitHotspots();
      setCockpitLoadingProgress(100, true, false);
    },
    evt => {
      const pct = evt.total ? Math.round((evt.loaded / evt.total) * 100) : Math.round(evt.loaded / 1e5);
      setCockpitLoadingProgress(Math.min(99, pct), false, false);
    },
    err => {
      console.error("座舱模型加载失败:", err);
      setCockpitLoadingProgress(0, false, true);
    }
  );
}

/* 整车视角/座舱视角切换:X-Ray、分组筛选条都是整车 3D 场景专属的控件,座舱视角下隐藏,
   避免用户以为座舱示意图也能透视/分组。 */
window.veh3dSetView = function (mode) {
  const isCockpit = mode === "cockpit";
  viewMode = isCockpit ? "cockpit" : "ext";
  const extBtn = $("#veh3d-view-ext"), cpBtn = $("#veh3d-view-cockpit");
  if (extBtn) extBtn.classList.toggle("on", !isCockpit);
  if (cpBtn) cpBtn.classList.toggle("on", isCockpit);
  const canvas = $("#veh3d-canvas"), cockpit = $("#veh3d-cockpit");
  if (canvas) canvas.style.display = isCockpit ? "none" : "";
  if (cockpit) cockpit.style.display = isCockpit ? "" : "none";
  if (isCockpit) { initCockpitScene(); sizeCockpitRenderer(); } // 懒加载;display:none 时宽高为 0,切回来后要重算一次
  const xrayBtn = $("#veh3d-xray-btn"), groupBar = $("#veh3d-group-bar");
  if (xrayBtn) xrayBtn.style.display = isCockpit ? "none" : "";
  if (groupBar) groupBar.style.display = isCockpit ? "none" : "";
  const hint = $("#veh3d-hint");
  if (hint) hint.textContent = isCockpit
    ? "拖动旋转 · 滚轮缩放 · 点击内饰部件/标签查看该区域合规范围"
    : "拖动旋转 · 滚轮缩放 · 点击部件/标签查看该区域合规范围";
  const foot = $("#veh3d-footnote");
  if (foot) foot.textContent = isCockpit
    ? "模型:grab3d.com CC0 座舱素材拼装(通用款式,无品牌标识,见 vendor/models/CREDITS.md)· 仪表板/方向盘/出风口/仪表盘总成/座椅/门饰板/脚垫为真实模型节点,可直接点击;安全气囊素材包无对应部件,仍用悬浮标签占位(锚定在方向盘轮毂实际位置)· 该素材只有舱内部件、没有包裹的外观车身,转到较极端角度会看到部件边缘悬空,正常浏览角度不受影响"
    : "模型:Audi R8(业主提供并确认可用,已去除车标,见 vendor/models/CREDITS.md)· 车身外观部件为真实模型节点,可直接点击,覆盖整车准入/环保全链条;动力总成/底盘/空调/内饰/三电/智能网联共 18 个系统源模型无实体建模,开启 X-Ray 后按系统分组以占位标注展示——其中发动机/变速器/散热器/前后悬架/制动盘 6 项已换成 grab3d.com CC0 真实零件模型(首次开 X-Ray 时加载),其余(离合器/转向系统/半轴传动轴等)仍是占位方块,详见区域数据 note · 其余维度见「维度矩阵」「国家详情」";
};

const _hsVec = new THREE.Vector3();
/* 18 个 hotspot 里同一分组常常在车身上物理位置很近(比如动力总成 4 个都挤在机舱区域),
   投影到屏幕后位置也会很近——早期"按下标交替偏移 34px"的写法只够分开 2 个,分组功能上线后
   同屏最多可能有 6 张卡片,必须做真正的防重叠:按屏幕 Y 排序后贪心下推,不再靠下标取巧。 */
function updateHotspotLayer() {
  if (!xrayOn || !hotspots.length) return;
  const host = $("#veh3d-canvas");
  const svg = document.querySelector("#veh3d-hotspot-layer .veh3d-hs-svg");
  if (!host || !svg) return;
  const w = host.clientWidth, h = host.clientHeight;
  const visible = [];
  hotspots.forEach(hs => {
    if (!hs.mesh.visible) { hs.card.style.display = "none"; return; } // 未勾选该分组,或未开 X-Ray
    _hsVec.setFromMatrixPosition(hs.mesh.matrixWorld);
    _hsVec.project(camera);
    if (_hsVec.z > 1) { hs.card.style.display = "none"; return; } // 在相机背面
    visible.push({ hs, x: (_hsVec.x * 0.5 + 0.5) * w, y: (-_hsVec.y * 0.5 + 0.5) * h });
  });
  visible.sort((a, b) => a.y - b.y);
  const CARD_H = 28;
  let lastCardY = -Infinity;
  let lines = "";
  visible.forEach(v => {
    const cardX = Math.min(w - 12, Math.max(12, v.x + 60));
    const cardY = Math.max(20, Math.max(v.y - 40, lastCardY + CARD_H));
    lastCardY = cardY;
    v.hs.card.style.display = "block";
    v.hs.card.style.left = cardX + "px";
    v.hs.card.style.top = cardY + "px";
    lines += `<line x1="${v.x}" y1="${v.y}" x2="${cardX}" y2="${cardY + 10}" class="veh3d-hs-line"/><circle cx="${v.x}" cy="${v.y}" r="3.5" class="veh3d-hs-dot"/>`;
  });
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.innerHTML = lines;
}

/* 车身材质来自按顶点色导出的资产,glTF 里标的是 alphaMode:OPAQUE——运行时改同一个材质的
   .opacity/.transparent 不可靠(浏览器测试中肉眼看不出变化,应是编译期就把 alpha 输出裁掉了)。
   改为加载时就构建好一份"opaque 材质"与一份"xray 材质"(后者从一开始就 transparent:true 构造),
   切换时直接整体替换 mesh.material,而不是运行时修改属性。
   纯调低透明度这一件事做出来的效果很糟——车身多层重叠面(尤其车轮:胎面+轮辋+轮辐+刹车盘)
   叠加后观感比车身更"实",整体又像一团灰蒙蒙的东西、没有轮廓,不像真正的透视图。改为工程图
   常见做法:极低不透明度的实体填充(给出体量感)+ EdgesGeometry 生成的清晰轮廓线(给出结构感),
   两者叠加,而不是单靠一个透明度数值硬撑。 */
function buildXrayMaterial(mat) {
  const m = mat.clone();
  m.transparent = true;
  // 任何非零填充不透明度,只要碰到模型里堆叠多层的密集区域(格栅缝隙、大灯多层结构、车轮
  // 胎面+轮辋+轮辐+刹车盘),多层透明面叠加后观感都会滚雪球一样趋近不透明,看起来像"实心的
  // 一块"——这个问题在车轮、前脸格栅两处都实测复现了,不是单个数值能调好的,索性把填充调到
  // 近乎全透明(不用 0,避免个别渲染路径把 opacity:0 当成整体剔除处理),结构感完全交给棱线。
  m.opacity = 0.02;
  m.depthWrite = false;
  return m;
}
function buildEdgeLines(mesh) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 32); // 32°阈值:只留有意义的棱线,滤掉高多边形噪点
  const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x1a2420, transparent: true, opacity: 0.55 }));
  line.visible = false;
  mesh.add(line); // 作为 mesh 的子节点,自动继承其局部变换
  return line;
}

function setXray(on) {
  xrayOn = on;
  if (carRoot) {
    carRoot.traverse(o => {
      if (!o.isMesh || !o.material) return;
      // 占位 Box 和机械零件(可能是多网格的真实模型,子网格本身不等于 hotspots[].mesh 这个容器
      // 对象)统一用这个标记跳过透视材质替换,可见性交给下面的 refreshHotspotVisibility() 统一处理
      if (o.userData.hotspotEl) return;
      if (!o.userData.opaqueMat) o.userData.opaqueMat = o.material;
      if (!o.userData.xrayMat) o.userData.xrayMat = buildXrayMaterial(o.userData.opaqueMat);
      if (!o.userData.edgeLine) o.userData.edgeLine = buildEdgeLines(o);
      o.material = on ? o.userData.xrayMat : o.userData.opaqueMat;
      o.userData.edgeLine.visible = on;
    });
  }
  refreshHotspotVisibility();
  const layer = $("#veh3d-hotspot-layer");
  if (layer) layer.style.display = on ? "block" : "none";
  const btn = $("#veh3d-xray-btn");
  if (btn) btn.classList.toggle("on", on);
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

  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100); // 真实边界在 frameCamera() 里按模型算
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
    updateHotspotLayer();
  });

  const xrayBtn = $("#veh3d-xray-btn");
  if (xrayBtn) xrayBtn.addEventListener("click", () => {
    const turningOn = !xrayOn;
    setXray(turningOn);
    if (turningOn) loadMechanicalParts(); // 懒加载:用户第一次真的打开 X-Ray 才去拉这个模型
  });
  buildGroupBar();

  fillCountrySelect();
  renderVeh3DKPIs();

  new GLTFLoader().load(
    MODEL_URL,
    gltf => {
      carRoot = gltf.scene;
      scene.add(carRoot);
      // 逐 mesh 克隆材质:部分模型(如按顶点色导出的资产)会让多个 mesh 共享同一材质实例,
      // 悬停高亮若直接改共享材质的 emissive 会连带染色整车,而非仅高亮当前部件。
      // 排查"部分车身消失"问题时验证过 side:DoubleSide 不是正确修复——这个模型部分节点的法线
      // 方向与三角形环绕不一致(trimesh 转换过程留下的),强制双面渲染会触发 three.js 标准材质
      // 着色器的背面法线翻转逻辑,反而让本来朝向正确的面被当成"背面"处理、按翻转后的法线来光照,
      // 实测表现为车身大片发黑——弊大于利,不采用。真正的消失问题是相机极角能转到车身水平线
      // 以下(见 frameCamera 里 minPolarAngle/maxPolarAngle 处的说明),和背面剔除无关。
      carRoot.traverse(o => { if (o.isMesh && o.material) o.material = o.material.clone(); });
      carRoot.updateMatrixWorld(true);
      carCleanBox = new THREE.Box3().setFromObject(carRoot); // 占位/机械零件还没加进来之前的"干净"包围盒
      frameCamera(carRoot);
      buildHotspots();
      setLoadingProgress(100, true, false);
    },
    evt => {
      const pct = evt.total ? Math.round((evt.loaded / evt.total) * 100) : Math.round(evt.loaded / 1e5);
      setLoadingProgress(Math.min(99, pct), false, false);
    },
    err => {
      console.error("车辆模型加载失败:", err);
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
