/* ================= 00 合规孪生(3D) =================
   独立 ES module,加载 vendor/three/ 本地化 Three.js。
   依赖 index.html 内联 classic <script> 中已定义的全局:
   DIMS, recs(), byCountry(), sbFetchAll, esc, $, $$, enhanceCountrySelect, refreshSelFilter, switchTab,
   keyOf(), isDraft(), advGo()
   本模块通过 window.veh3dOnData 暴露一个钩子,供 index.html 的 renderAll() 在法规数据就绪后调用,
   以刷新详情面板里依赖真实数据的数字(不阻塞 3D 场景本身的加载)。 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const MODEL_URL = "./vendor/models/AudiR8/AudiR8.glb";
// 2026-11 座舱素材第二批(新增 9 个纯装饰零件)复用了同一个文件名,手动加 ?v= 破缓存——
// 和 index.html 里 vehicle3d.js 的 ?v= 是同一类问题(浏览器可能继续用磁盘缓存里的旧 12MB
// 版本,看不到新加的收音机/导航屏/儿童座椅等),同样约定:每次换 cockpit.glb 内容就手动往后挪。
const COCKPIT_MODEL_URL = "./vendor/models/CockpitInterior/cockpit.glb?v=20261120e";
const MECH_MODEL_URL = "./vendor/models/MechanicalParts/mechanical.glb";
// 2026-11 第三个独立场景(安全结构视角):业主提供的 AI 生成安全结构剖视模型,经减面+左右
// 对称化修正后接入,见 vendor/models/CREDITS.md「安全结构剖视模型」一节。
const SAFETY_MODEL_URL = "./vendor/models/SafetyStructure/safety_structure.glb?v=20261126a";
// 业主要求在安全结构视角里摆一个儿童座椅示意(CC0 素材,见 CREDITS.md)。这套安全结构模型只
// 建了一排舱室(左右镜像出的两个前排座位),业主用截图圈出的位置是其中一侧现成座位(严格说
// 是前排乘客座,不是后排)。**已知限制**:核实发现这一排两个座位现在都坐着假人(左右各约
// 5 万面的假人几何体),并不存在真正"空着"的座位。2026-11-26 业主进一步反馈:之前那组坐标
// 其实摆到了司机(方向盘所在)那一侧假人的对面,不是业主想要的位置;业主用截图圈出目标是
// A 柱根部/门槛附近的一处位置,朝向要求是"正面朝向车头(绿色保险杠)方向"。重新定位方法:
// 1) 在截图标注的位置附近用 Raycaster 拾取真实世界坐标；2) 提取该处 A 柱(safety_cage)在
// 这片区域的真实网格顶点,对 scale/position 做零重叠的网格搜索(同一套 B 柱验证方法,见
// CREDITS.md),找到从业主标注点往车头方向最多能挪到、且跟 A 柱零重叠的位置；
// 3) rotationY 由 -90° 改为 +90°,让椅子局部 +Z(儿童面朝一侧)对齐世界 +X(车头方向),
// 而不是原来朝向车尾。2026-11-26 七次修正:业主反馈椅子再往车尾方向挪、且位置偏高。
// 把 x/y 一起做二维网格搜索(而不是像之前那样固定一个轴单独调另一个轴——固定 y 时
// x=-0.23 一类的"车尾方向"位置实际会在更低的 y 上跟 A 柱重叠,只调 x 没发现),
// 确认 `x∈[-0.27,-0.225], y∈[-0.055,-0.035]` 这个区间与 A 柱零重叠,选用
// `x=-0.24, y=-0.04`(比上一版 `x=-0.12,y=-0.01` 更靠车尾、也更低)。**已知局限**:
// 只验证了跟 A 柱零重叠,没有重新核对跟假人躯干是否重叠(这片区域离假人较远,目测无
// 重叠,但未像 B 柱那样做严格数学验证)。改模型或布局后这组数字要重新核对。
const CHILD_SEAT_MODEL_URL = "./vendor/models/SafetyStructure/child-car-seat.glb?v=20261125a";
const CHILD_SEAT_TRANSFORM = { position: [-0.24, -0.04, 0.07], scale: 0.165, rotationY: Math.PI / 2 };
// 业主反馈安全结构模型自带的方向盘拓扑破碎(轮辋被拆成几十个互不相连的小碎片、颜色也很淡,
// 见 CREDITS.md 历次修复记录),2026-11-26 业主提供 grab3d.com 的 sports-steering-wheel
// CC0 素材整体替换(原方向盘的全部面片已从 safety_structure.glb 里删除)。朝向不是凭眼睛
// 调的:对原方向盘残留几何体的顶点做了 PCA,取方差最小的轴当作转向柱法线方向(约
// [0.4836, 0.8742, 0.0439]),新模型局部 +Z 轴是其轮面法线(同样用 PCA 在原始 glb 上验证
// 过,和素材 manifest 文字描述的"局部 Y"对不上,大概率是 Blender→glTF 导出时的轴约定转换
// 导致的,以实测为准),用 `quaternion.setFromUnitVectors` 把局部 +Z 对齐到这个法线上。
// 位置取原方向盘残留几何体的顶点质心;缩放按真实尺寸 0.34m 直径换算(项目约定 1 模型单位
// ≈ 4.5 真实米,见儿童座椅换算记录)。2026-11-26 业主截图确认司机是左边(z<0)那位假人,
// 不是最初 PCA 定出来的 z>0 一侧——原方向盘残留几何体本身就摆错了边(这套 AI 生成模型
// 的已知毛病),按业主指认把位置/法线整体做 Z 轴镜像挪到正确一侧。
const STEERING_WHEEL_MODEL_URL = "./vendor/models/SafetyStructure/sports-steering-wheel.glb?v=20261126a";
const STEERING_WHEEL_TRANSFORM = {
  position: [-0.11536751, -0.00977693, -0.08506728],
  scale: 0.34 / 4.5,
  normal: [0.48363289, 0.87416905, -0.04390529],
};
const ZONES_URL = "./data/vehicle_zones.json";
const TAXONOMY_URL = "./data/reg_taxonomy.json";

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
let safetyNodeToZone = new Map(); // gltf 节点名(小写) -> zoneId,安全结构视角(safety_structure.glb)用,第三套独立命名空间
let curZoneId = null;
let curCountry = "";       // "" = 全部国家(聚合)
let viewMode = "ext";      // "ext" | "cockpit" | "safety" —— veh3dSetView() 维护,showZoneDetail() 等需要据此区分当前在哪个 3D 场景里
let scene, camera, renderer, controls, carRoot, raycaster, hoverObj, hoverOrigEmissive;
let normalBgColor = null; // X-Ray 关闭时的纸面背景色缓存,setXray() 据此在蓝色 HUD 背景和它之间切换
const XRAY_BG_COLOR = 0x070b11; // 和座舱视角暗色 HUD 主题(#070b11)同一个底色,两处视觉语言统一
const XRAY_GLOW_COLOR = 0x2dd4ff; // 棱线/热点统一用这个蓝,和 .veh3d-cockpit-label 的 #2dd4ff 一致
let cockpitScene, cockpitCamera, cockpitRenderer, cockpitControls, cockpitRoot, cockpitRaycaster, cockpitHoverObj, cockpitHoverOrigEmissive;
let cockpitInited = false; // 懒加载:只在用户第一次切到座舱视角时才去拉 12MB 的 cockpit.glb
let cockpitHotspots = []; // 座舱视角悬浮标签(dashboard/ac_system/ecu_ota/seats/floor_mat/door_trim/airbag/
                           // adas_front_sensor 共 8 项,均无真实几何),复用整车视角"虚线标签"的思路但没有
                           // 占位 Box 网格,见 buildCockpitHotspots()
let safetyScene, safetyCamera, safetyRenderer, safetyControls, safetyRoot, safetyRaycaster, safetyHoverObj, safetyHoverOrigEmissive;
let safetyInited = false; // 懒加载:只在用户第一次切到安全结构视角时才去拉这个 9.3MB 的模型
let xrayOn = false;
let hotspots = []; // [{zone, mesh, card}] —— 源模型无实体建模的维度(电池包/ECU-OTA域、
                    // 2026-09 新增的动力总成/底盘/空调/内饰、2026-11 阶段一拆分出的三个 ADAS 传感器
                    // 分区等共 21 个区域),用简易占位几何体 + 虚线标签展示,不冒充精细建模
let carCleanBox = null; // 整车模型刚加载完、还没加任何占位/机械零件时的包围盒缓存——hotspotWorldPos()
                         // 用这份"干净"的包围盒算比例坐标,避免大体积机械零件加入 carRoot 后
                         // Box3.setFromObject(carRoot) 把它们自己算进包围盒、污染后续区域的定位
let mechRoot = null, mechLoaded = false, mechLoading = false; // 机械零件模型(懒加载,见 loadMechanicalParts)
let explodedOn = false; // 阶段三:炸开视图(仅整车视角),见 setExploded()
/* 导航侧栏飞向某个占位区域后,相机会贴近放大该区域——这时其余分组里还显示着标签的区域
   (比如默认同时勾选的三电+智能网联共 5 个)在屏幕上的投影点大概率落在放大后的画面边缘甚至
   画面外,防重叠布局又会把它们的卡片继续往外推,看起来就像"一堆部件飞到车外面了"(业主反馈
   过这个问题)——其实 3D 坐标本身没问题,问题是放大聚焦到一个区域时还硬要挤下其余所有标签。
   聚焦某个区域时只留它自己的标签,其余暂时隐藏(3D 发光方块本身仍然显示,只是不挂文字卡片),
   手动切换分组勾选、或进入炸开视图(本意就是要同时看清楚所有部件)时解除聚焦。 */
let hotspotFocusId = null;
/* 炸开视图和流程动画都要临时强开 X-Ray + 一组分组,关闭时还原用户原先的勾选状态——两者共用
   这一份快照(而不是各自存一份),是因为直接从一个模式切到另一个模式时(比如炸开视图开着,
   点了流程动画,流程动画内部会调用 setExploded(false) 来关掉炸开)各自独立的快照会互相踩踏:
   后开启的模式会把前一个模式保存的、更早的原始状态当成快照来源,导致关闭时还原到错误的状态。
   只在"两个模式都未开启"时才真正记录/还原,期间无论切换多少次都不会丢失最初的原始状态
   (Codex 审查发现的问题,见 PR #313 合并后的 review comment)。 */
let preModeGroups = null, preModeXray = null;
function enterXrayOverride(groups) {
  // 用"是否已经有快照在生效"而不是 explodedOn/flowOn 两个标志位来判断是不是第一个开启的模式——
  // 调用这个函数时,调用方(setExploded/setFlow)自己的那个标志位早就先被置成 true 了,这时候
  // 再去判断"两者都没开"永远不成立,快照条件必须和两个模式各自的标志位解耦。
  if (preModeGroups === null) {
    preModeXray = xrayOn;
    preModeGroups = new Set(activeGroups);
  }
  if (!xrayOn) setXray(true);
  activeGroups = new Set(groups);
  buildGroupBar();
  refreshHotspotVisibility();
}
function exitXrayOverride() {
  if (explodedOn || flowOn) return; // 另一个模式还开着,继续保持覆盖状态,不还原
  if (preModeGroups) {
    activeGroups = preModeGroups;
    buildGroupBar();
    refreshHotspotVisibility();
    if (preModeXray === false) setXray(false);
    preModeGroups = null;
    preModeXray = null;
  }
}
const bodyZoneOrigLocalPos = new Map(); // 车身真实几何节点(Object3D)→ 炸开前的原始 local position,关闭炸开时精确还原
const hotspotOrigLocalPos = new Map();  // hotspots[].mesh(含被机械零件替换后的新对象)→ 炸开前的原始 local position

/* 21 个 hotspot 区域按 group 字段分 6 组,X-Ray 下按组切换显示——不然 21 张标签卡片同屏堆叠
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

/* 2026-11 阶段二(「车辆浏览器」四阶段计划):EPC 风格左侧部件导航侧栏,按分组列出全部 28 个区域
   (含车身外观这 7 个真实几何分区,HOTSPOT_GROUPS 没覆盖它们,因为那个列表专门对应 X-Ray 占位组
   勾选,和这里"目录导航"是两码事,故另开一份)。点击条目=相机飞向该区域 + 打开详情面板,不是
   简单的 showZoneDetail 快捷方式。 */
const NAV_GROUPS = [
  { id: "body", label: "车身外观" },
  { id: "ev", label: "三电系统" },
  { id: "connectivity", label: "智能网联" },
  { id: "powertrain", label: "动力总成" },
  { id: "chassis", label: "底盘/制动转向" },
  { id: "hvac", label: "空调" },
  { id: "interior", label: "内饰与乘员防护" },
  { id: "safety", label: "整车安全(结构剖视)" },
];
let navOpenGroups = new Set(["body"]); // 默认只展开车身外观,其余折叠,避免 30 项一次性铺开

/* 2026-11-25 业主要求部件导航侧栏"能看到业主提供的三级法规分类表里的所有二级、三级映射及
   范围关键词"——核对后发现这份表(一级5/二级20/三级51)和上面 NAV_GROUPS 这套"按物理部件
   分组"的导航树是两套不同的组织逻辑,互相都不能完全替代对方(这份表里框架性准入条例/政策/
   海关/标签铭牌/召回处罚/禁限用物质/ELV整车回收等 11 个类目在车辆上没有对应的单一可点选
   部件;反过来 roof/safety_body 两个区域一开始在表里也找不到直接对应类目,后来按"翻滚保护"
   "座椅安全带"的范围关键词把它们核实补上了)——业主确认"如果没有完全覆盖,则二者结合",
   做法:在同一个"部件导航"列表里,物理分组之后原样追加这份表按「二级」分组、「三级」
   (无三级细分的,二级本身就是条目)为条目的浏览结构,条目下附带「范围关键词」原文;条目
   对应 1 个或多个 3D 区域时点击飞向其中第一个(复用 navGoToZone,不是另一套跳转逻辑),
   对应 0 个区域时不可点击、仅展示文字(如实标注,不替它硬凑一个部件)。同一个区域完全可能
   同时出现在物理分组与这套分类分组下,不做去重——这是两种不同的浏览视角,不是重复数据。
   未使用额外的"按法规分"之类的标题/切换按钮,就是"部件导航"这同一份列表的延伸。 */
let TAX_LEAVES = []; // 原始行:[{id,l1,l2,l3,keywords,zones}]
let TAX_GROUPS = []; // 按 l2 分组后的渲染结构,懒计算一次(loadTaxonomy 完成后)

async function loadTaxonomy() {
  try {
    const resp = await fetch(TAXONOMY_URL);
    const data = await resp.json();
    TAX_LEAVES = Array.isArray(data.leaves) ? data.leaves : [];
  } catch (e) {
    console.error("reg_taxonomy.json 读取失败(不阻断导航侧栏其余部分展示):", e);
    TAX_LEAVES = [];
  }
  const byL2 = new Map();
  TAX_LEAVES.forEach(leaf => {
    const key = leaf.l2;
    if (!byL2.has(key)) byL2.set(key, []);
    byL2.get(key).push(leaf);
  });
  TAX_GROUPS = Array.from(byL2.entries()).map(([l2, rows]) => ({
    id: "tax_" + l2,
    label: l2,
    flat: rows.length === 1 && !rows[0].l3, // 单行且无三级细分:不建手风琴,直接当一条平铺条目
    rows,
  }));
}

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
  safetyNodeToZone = new Map();
  ZONES.forEach(z => {
    (z.gltf_nodes || []).forEach(n => nodeToZone.set(String(n).toLowerCase(), z.id));
    (z.cockpit_nodes || []).forEach(n => cockpitNodeToZone.set(String(n).toLowerCase(), z.id));
    (z.safety_nodes || []).forEach(n => safetyNodeToZone.set(String(n).toLowerCase(), z.id));
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

/* 2026-11 阶段一:详情面板从"只显示覆盖统计数字"升级为"列出实际命中的法规条目"(参照 Renault
   编号+条目列表参考图),复用 zoneMatch 不重新发明匹配逻辑。country 为空时聚合全部国家,
   此时每行加国家名前缀区分。 */
function zoneRecords(zoneId, country) {
  const zone = zoneById(zoneId);
  if (!zone) return [];
  const all = (typeof recs === "function") ? recs() : [];
  return all.filter(r => zoneMatch(r, zone) && (!country || r.country === country));
}

/* keyOf/norm/isDraft/advGo 与 recs/byCountry 同理:index.html 顶层 const/function 在同一文档的
   全局词法环境里对模块脚本可见(不是 window 属性,但仍是裸标识符可读),按本文件既有约定统一
   加 typeof 守卫,避免任一方先加载时报错。 */
function regKey(r) {
  if (typeof keyOf === "function") return keyOf(r);
  return r.country + "|" + String(r.regId || r.cnName || "").replace(/\s+/g, "").toUpperCase();
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
    updateNavActive();
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
    : viewMode === "safety"
    ? ((zone.safety_nodes || []).length ? `${zone.safety_nodes.length} 个安全结构模型节点` : "该区域在安全结构视角无对应部件")
    : (zone.hotspot ? "占位标注 · 源模型无对应实体建模" : `${(zone.gltf_nodes || []).length} 个模型节点`);
  const regMatched = zoneRecords(zoneId, curCountry);
  const unRegs = Array.isArray(zone.un_regs) ? zone.un_regs : [];
  // 精确引用(r.refs 命中该区域标注的具体 UN R 号)排在最前,其余按日期倒序,无日期的记录排在
  // 最后(不是丢弃——之前的写法在既有有日期又有无日期记录时只对有日期的排序、把无日期的整批
  // 丢掉,但面板标题「共 N 条」的计数包含它们,导致列表和计数对不上,这里改成对完整的 regMatched
  // 排序,同一优先级内保留各自的相对顺序)。纯展示优先级调整,不改变 regMatched 本身的集合与
  // 数量(覆盖计数口径见 zoneStats(),不受此影响)。
  const isExactRef = r => unRegs.length > 0 && Array.isArray(r.refs) && r.refs.some(f => unRegs.includes(f));
  const regSorted = regMatched.slice().sort((a, b) => {
    const exactDiff = isExactRef(b) - isExactRef(a);
    if (exactDiff) return exactDiff;
    if (a.date && b.date) return b.date.localeCompare(a.date);
    if (!!a.date !== !!b.date) return a.date ? -1 : 1; // 有日期的排在没日期的前面
    return 0;
  });
  const regShow = regSorted.slice(0, 8);
  const unRegsRow = unRegs.length ? `
    <div class="pd-lbl" style="margin-top:8px;margin-bottom:4px">相关 UN 法规</div>
    <div>${unRegs.map(u => `<span class="rtag parent" style="margin:0 4px 4px 0">${esc(u)}</span>`).join("")}</div>` : "";
  const regListHtml = regShow.length ? `
    <div class="pd-lbl" style="margin-top:12px;margin-bottom:4px">命中法规条目(点击跳转详情${regMatched.length > regShow.length ? `,共 ${regMatched.length} 条,示前 ${regShow.length}` : ""})</div>
    <div class="revlist" id="veh3d-reglist">
      ${regShow.map(r => `<div class="ri" data-country="${esc(r.country || "")}" data-key="${esc(regKey(r))}" style="cursor:pointer">
        <div class="top"><span class="rid">${esc(r.regId || "—")}${r.amend ? `<span class="rtag amd">${esc(r.amend)}</span>` : ""}${(typeof isDraft === "function" && isDraft(r)) ? '<span class="rtag">草案</span>' : ""}${isExactRef(r) ? `<span class="rtag" style="background:#deead5;color:#3d6630" title="该条法规文本引用了本区域标注的 UN R 号">精确引用</span>` : ""}</span>
        ${r.date ? `<span class="rdate">${esc(r.date)}</span>` : ""}</div>
        <div class="rnm">${!curCountry ? `${esc(r.country || "")} · ` : ""}${esc(r.cnName || r.origName || "")}</div></div>`).join("")}
    </div>` : `<div class="pd-desc veh3d-empty" style="margin-top:12px">暂无命中的法规条目</div>`;
  host.innerHTML = `
    <div class="pd-lbl">${esc(zoneId)} · ${nodeInfo}</div>
    <div class="pd-title">${esc(zone.label_cn)}</div>
    <div class="pd-local">${esc(zone.label_en)}</div>
    ${unRegsRow}
    <div class="veh3d-status">${statusText}</div>
    <div class="veh3d-badge">适用法规数 ${st ? st.count : "—"} 条</div>
    <div class="pd-desc" style="margin-top:10px">${esc(zone.desc || "")}</div>
    ${regListHtml}
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
  host.querySelectorAll("#veh3d-reglist .ri").forEach(row => {
    row.addEventListener("click", () => {
      if (typeof advGo === "function") advGo(row.dataset.country, row.dataset.key);
    });
  });
  const emarkLink = host.querySelector("#veh3d-emark-link");
  if (emarkLink) emarkLink.addEventListener("click", goToEmark);
  updateNavActive();
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
      new THREE.MeshStandardMaterial({ color: XRAY_GLOW_COLOR, emissive: XRAY_GLOW_COLOR, emissiveIntensity: 0.6, roughness: 0.35 })
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
    // 机械零件是异步加载的,可能在用户已经打开炸开视图之后才替换到位——此时直接按炸开视图的
    // 同一套逻辑把新对象瞬间摆到爆炸位置(不再播动画,只是补齐状态),而不是让它先出现在原位
    // 等下一次开关炸开才归位,那样会有一瞬间"看起来没炸开"的错觉。
    if (explodedOn && carRoot) {
      const box = carCleanBox || new THREE.Box3().setFromObject(carRoot);
      const center = box.getCenter(new THREE.Vector3());
      const carRadius = box.getSize(new THREE.Vector3()).length() * 0.5 || 1;
      const dir = inst.position.clone().sub(center);
      if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
      dir.normalize();
      hotspotOrigLocalPos.set(inst, inst.position.clone());
      inst.position.addScaledVector(dir, carRadius * 0.55);
    }
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
      hotspotFocusId = null; // 用户手动勾选分组=明确想看一整类部件,解除导航飞向时留下的单点聚焦
      refreshHotspotVisibility();
    });
  });
}

/* ============ 阶段二:EPC 风格部件导航侧栏(列表 + 相机飞向) ============ */
function renderNavSidebar() {
  const list = $("#veh3d-nav-list");
  if (!list || !ZONES.length) return;
  const physicalHtml = NAV_GROUPS.map(g => {
    const zs = ZONES.filter(z => (z.group || "") === g.id);
    if (!zs.length) return "";
    const open = navOpenGroups.has(g.id);
    return `<div class="veh3d-nav-group${open ? " open" : ""}" data-g="${esc(g.id)}">
      <div class="veh3d-nav-group-hd"><span>${esc(g.label)}(${zs.length})</span><span class="chev">▶</span></div>
      <div class="veh3d-nav-items">
        ${zs.map(z => `<button type="button" class="veh3d-nav-item${z.id === curZoneId ? " active" : ""}" data-z="${esc(z.id)}">${esc(z.label_cn)}</button>`).join("")}
      </div>
    </div>`;
  }).join("");
  // 分类分组(见 loadTaxonomy 注释):flat=true 的单行类目直接平铺一条,其余按手风琴展开三级条目
  const taxHtml = TAX_GROUPS.map(g => {
    if (g.flat) {
      const row = g.rows[0];
      return renderTaxItem(row, true);
    }
    const open = navOpenGroups.has(g.id);
    return `<div class="veh3d-nav-group${open ? " open" : ""}" data-g="${esc(g.id)}">
      <div class="veh3d-nav-group-hd"><span>${esc(g.label)}(${g.rows.length})</span><span class="chev">▶</span></div>
      <div class="veh3d-nav-items">
        ${g.rows.map(row => renderTaxItem(row, false)).join("")}
      </div>
    </div>`;
  }).join("");
  list.innerHTML = physicalHtml + taxHtml;
  list.querySelectorAll(".veh3d-nav-group-hd").forEach(hd => {
    hd.addEventListener("click", () => {
      const grp = hd.closest(".veh3d-nav-group");
      const gid = grp.dataset.g;
      if (navOpenGroups.has(gid)) navOpenGroups.delete(gid); else navOpenGroups.add(gid);
      grp.classList.toggle("open");
    });
  });
  list.querySelectorAll(".veh3d-nav-item[data-z]").forEach(btn => {
    btn.addEventListener("click", () => navGoToZone(btn.dataset.z));
  });
  list.querySelectorAll(".veh3d-nav-item.tax:not(.disabled)").forEach(btn => {
    btn.addEventListener("click", () => navGoToZone(btn.dataset.zones.split(",")[0]));
  });
}

/* 分类条目:label = 三级名称(无三级细分时用二级本身),下方附一行范围关键词原文;
   zones 为空时整条禁用(灰态、无点击),非空时点击飞向 zones[0] 并打开详情面板。
   top=true 用于未分组的单行类目(如"框架法规"),缩进/样式与手风琴内条目区分开。 */
function renderTaxItem(row, top) {
  const label = row.l3 || row.l2;
  const hasZone = Array.isArray(row.zones) && row.zones.length > 0;
  const cls = "veh3d-nav-item tax" + (top ? " top" : "") + (hasZone ? "" : " disabled") +
    (hasZone && row.zones[0] === curZoneId ? " active" : "");
  const tag = hasZone ? "button" : "div";
  const typeAttr = hasZone ? ` type="button"` : "";
  const zonesAttr = hasZone ? ` data-zones="${esc(row.zones.join(","))}"` : "";
  const title = hasZone ? "" : ` title="该类目在当前车辆模型上暂无对应部件"`;
  return `<${tag}${typeAttr} class="${cls}"${zonesAttr}${title}>
    <span class="tax-label">${esc(label)}</span>
    ${row.keywords ? `<span class="tax-kw">${esc(row.keywords)}</span>` : ""}
  </${tag}>`;
}

function updateNavActive() {
  const list = $("#veh3d-nav-list");
  if (!list) return;
  list.querySelectorAll(".veh3d-nav-item[data-z]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.z === curZoneId);
  });
  list.querySelectorAll(".veh3d-nav-item.tax[data-zones]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.zones.split(",").includes(curZoneId));
  });
}

/* 收集某区域在指定场景里对应的全部真实网格节点的世界包围盒(整车视角传 nodeToZone,座舱视角传
   cockpitNodeToZone)——没有真实几何(纯 hotspot 占位)的区域调用方会 fall back 到对应的
   *_pos 比例坐标单点,不强求这里返回结果。 */
function zoneWorldBox(zone, root, nameToZoneMap) {
  if (!root) return null;
  const box = new THREE.Box3();
  let found = false;
  root.traverse(o => {
    if (o.isMesh && nameToZoneMap.get(String(o.name || "").toLowerCase()) === zone.id) {
      box.expandByObject(o);
      found = true;
    }
  });
  return found ? box : null;
}

/* 正投影(整车视角)下物体视觉大小只由 camera.zoom 决定、与相机距离无关,所以"飞向"=
   保持当前相机相对 target 的方向与距离不变、把 target 平移到目标区域中心,再按区域体量把
   zoom 调高;透视相机(座舱视角)则相反——物体大小只由距离决定,"飞向"=把相机沿同一方向
   移近到与区域体量匹配的距离,zoom 不参与。统一用一个 tween 对象,外部渲染循环每帧推进一次。 */
let camTween = null;
function flyCameraTo(cam, ctrls, targetCenter, radius, wholeHalfHeight) {
  if (!cam || !ctrls) return;
  const fromTarget = ctrls.target.clone();
  const fromPos = cam.position.clone();
  const offsetDir = fromPos.clone().sub(fromTarget);
  const baseLen = offsetDir.length() || 1;
  offsetDir.normalize();
  const toTarget = targetCenter.clone();
  const fromZoom = cam.zoom;
  let toPos, toZoom = fromZoom;
  if (cam.isOrthographicCamera) {
    toPos = toTarget.clone().addScaledVector(offsetDir, baseLen);
    const refHalf = wholeHalfHeight || 1;
    toZoom = Math.min(3.5, Math.max(1, refHalf / Math.max(radius * 1.6, 0.12)));
  } else {
    const desiredLen = Math.max(Math.min(baseLen, radius * 3.2), radius * 1.4, 0.35);
    toPos = toTarget.clone().addScaledVector(offsetDir, desiredLen);
  }
  const t0 = (typeof performance !== "undefined" ? performance.now() : Date.now());
  const dur = 650;
  camTween = {
    cam,
    step(now) {
      const t = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - t, 3); // ease-out cubic
      ctrls.target.lerpVectors(fromTarget, toTarget, e);
      cam.position.lerpVectors(fromPos, toPos, e);
      if (cam.isOrthographicCamera) {
        cam.zoom = fromZoom + (toZoom - fromZoom) * e;
        cam.updateProjectionMatrix();
      }
      return t >= 1;
    },
  };
}

/* 整车视角下某个区域当前的世界坐标中心(+半径,用于相机取景/流程动画画线都要用到)——真实
   几何区域用实际包围盒,占位区域优先用 hotspots[] 里当前的实际位置(炸开视图下真实飞出去的
   位置),不是重新按静态比例坐标算一遍"原始位置",否则炸开时两者会对不上。 */
function zoneExtWorldCenter(zone) {
  if (!carRoot) return null;
  const box = (zone.gltf_nodes && zone.gltf_nodes.length) ? zoneWorldBox(zone, carRoot, nodeToZone) : null;
  if (box) {
    return { center: box.getCenter(new THREE.Vector3()), radius: box.getSize(new THREE.Vector3()).length() * 0.5 || 0.6 };
  }
  if (Array.isArray(zone.hotspot_pos)) {
    const hs = hotspots.find(h => h.zone.id === zone.id);
    const center = hs ? new THREE.Vector3().setFromMatrixPosition(hs.mesh.matrixWorld)
      : new THREE.Vector3().fromArray(hotspotWorldPos(zone.hotspot_pos));
    return { center, radius: 0.6 }; // 占位区域无真实体量,给一个适中的默认取景半径
  }
  return null;
}

function navFlyToExtZone(zone) {
  if (!carRoot || !camera || !controls) return;
  const r = zoneExtWorldCenter(zone);
  if (!r) return;
  flyCameraTo(camera, controls, r.center, r.radius, _orthoHalfHeight);
}

function navFlyToCockpitZone(zone) {
  if (!cockpitRoot || !cockpitCamera || !cockpitControls) return;
  const box = (zone.cockpit_nodes && zone.cockpit_nodes.length) ? zoneWorldBox(zone, cockpitRoot, cockpitNodeToZone) : null;
  let center, radius;
  if (box) {
    center = box.getCenter(new THREE.Vector3());
    radius = box.getSize(new THREE.Vector3()).length() * 0.5 || 0.4;
  } else if (Array.isArray(zone.cockpit_hotspot_pos)) {
    center = new THREE.Vector3().fromArray(cockpitHotspotWorldPos(zone.cockpit_hotspot_pos));
    radius = 0.35;
  } else {
    return;
  }
  flyCameraTo(cockpitCamera, cockpitControls, center, radius, null);
}

/* 安全结构视角:两个区域(safety_cage/safety_body)都是真实几何节点,没有占位坐标 fallback
   (不像座舱视角还有 cockpit_hotspot_pos 兜底)——这套模型天生就只有这两块,无需占位示意。 */
function navFlyToSafetyZone(zone) {
  if (!safetyRoot || !safetyCamera || !safetyControls) return;
  const box = (zone.safety_nodes && zone.safety_nodes.length) ? zoneWorldBox(zone, safetyRoot, safetyNodeToZone) : null;
  if (!box) return;
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() * 0.5 || 0.1;
  flyCameraTo(safetyCamera, safetyControls, center, radius, null);
}

/* 导航侧栏点击入口:尊重用户当前视角,只有该区域在当前视角里完全没有对应点位(既无真实几何
   也无占位坐标)时才自动切到另一视角;座舱模型是懒加载的,首次切过去那一刻 cockpitRoot 可能
   还没下载完,此时跳过飞行动画(只切视角 + 开详情面板),不强行飞向一个还不存在的坐标系。 */
function navGoToZone(zoneId) {
  const zone = zoneById(zoneId);
  if (!zone) return;
  const hasExt = !!(zone.gltf_nodes || zone.hotspot_pos);
  const hasCockpit = !!(zone.cockpit_nodes || zone.cockpit_hotspot_pos);
  const hasSafety = !!(zone.safety_nodes && zone.safety_nodes.length);
  const hasInCurrent = viewMode === "cockpit" ? hasCockpit : viewMode === "safety" ? hasSafety : hasExt;
  if (!hasInCurrent) {
    if (hasExt) { veh3dSetView("ext"); }
    else if (hasCockpit) { veh3dSetView("cockpit"); }
    else if (hasSafety) { veh3dSetView("safety"); }
  }
  if (viewMode === "cockpit") {
    navFlyToCockpitZone(zone);
  } else if (viewMode === "safety") {
    navFlyToSafetyZone(zone);
  } else {
    if (zone.hotspot && !xrayOn) setXray(true);
    if (zone.group && !activeGroups.has(zone.group)) {
      activeGroups.add(zone.group);
      buildGroupBar();
      refreshHotspotVisibility();
    }
    // 不管飞向的是 hotspot 占位区域还是车身真实几何面板,都把焦点设成这个 zone.id——如果它
    // 不在 hotspots[] 里(车身面板),天然没有任何标签能匹配上,等效于"隐藏全部标签",同样避免
    // 放大车身某一块时背景还挂着一堆不相关的占位标签。
    hotspotFocusId = zone.id;
    navFlyToExtZone(zone);
  }
  showZoneDetail(zoneId);
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
   拼装基准(见 CREDITS.md),"前方"是 +Z。相机取斜前方俯视角度,让用户一进来就能同时看到仪表板
   正面(含方向盘)和前排座椅,不被头枕挡住视线(见下方角度注释),也不是从舱体背面开始看。
   如实记录一处局限:因为没有外观车身包着,拖到比较极端的角度能看到部件边缘悬空/背面裸露,
   正常浏览角度(斜前方俯视)不受影响,footnote 里也会提示。 */
function frameCockpitCamera(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = size.length() * 0.5 || 1;
  // 2026-11 业主反馈"座舱视角看起来没有方向盘"排查后改过这个默认角度:原来 dir=(0.6,0.55,-1)
  // 偏水平,从这个角度看方向盘正好被前排座椅头枕挡住(实测 before/after 对照截图确认,和方向盘
  // 位置对不对无关,纯粹是头枕挡住了视线)。改成更陡的俯视角(Y 分量从 0.55 提到 0.9),从头枕
  // 上方往下看,方向盘和仪表台能露出来;distance 倍数从 1.3 提到 1.5,配合更陡的角度留够取景范围。
  const dir = new THREE.Vector3(0.5, 0.9, -0.6).normalize();
  cockpitCamera.position.copy(center).addScaledVector(dir, radius * 1.5);
  cockpitCamera.near = radius / 50;
  cockpitCamera.far = radius * 20;
  sizeCockpitRenderer();
  cockpitControls.target.copy(center);
  cockpitControls.minDistance = radius * 0.25;
  cockpitControls.maxDistance = radius * 3;
  cockpitControls.update();
}

/* 2026-11 座舱视角改回 grab3d.com 原始单一座舱模型(业主决定,见 data/vehicle_zones.json 的
   note 字段与 vendor/models/CREDITS.md):不再拼装仪表板/座椅/门板/脚垫/出风口/仪表盘总成这些
   独立零件,这些区域(连同 airbag)统一用悬浮标签示意,和整车视角的 hotspot 占位系统同一思路——
   cockpit_hotspot_pos 是座舱模型当前真实包围盒三轴上的比例(0~1),不是写死的绝对坐标。
   steering_wheel 是例外:这个原始模型本身自带独立方向盘节点,继续走 cockpitNodeToZone 的
   真实点选路径,不在这里出现。 */
function cockpitHotspotWorldPos(fracPos) {
  if (!cockpitRoot) return fracPos;
  const box = new THREE.Box3().setFromObject(cockpitRoot);
  const [fx, fy, fz] = fracPos;
  return [
    box.min.x + fx * (box.max.x - box.min.x),
    box.min.y + fy * (box.max.y - box.min.y),
    box.min.z + fz * (box.max.z - box.min.z),
  ];
}
function buildCockpitHotspots() {
  cockpitHotspots.forEach(h => h.card.remove());
  cockpitHotspots = [];
  const layer = $("#veh3d-cockpit-labels");
  if (layer) layer.innerHTML = "";
  if (!cockpitRoot) return;
  ZONES.filter(z => Array.isArray(z.cockpit_hotspot_pos)).forEach(zone => {
    const worldPos = new THREE.Vector3().fromArray(cockpitHotspotWorldPos(zone.cockpit_hotspot_pos));
    const card = document.createElement("div");
    card.className = "veh3d-cockpit-label";
    card.textContent = zone.label_cn;
    card.addEventListener("click", () => showZoneDetail(zone.id));
    layer.appendChild(card);
    cockpitHotspots.push({ zone, worldPos, card });
  });
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
    if (camTween && camTween.cam === cockpitCamera && camTween.step(performance.now())) camTween = null;
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

/* 2026-11 第三个独立场景:安全结构视角(业主提供 AI 生成安全结构剖视模型,接入时要求"关联
   整车安全维度的区域映射",见 vendor/models/CREDITS.md「安全结构剖视模型」一节)。这套模型
   只有两个真实几何节点(safety_cage/safety_body),没有座舱视角那种"占位标签兜底"的需要——
   功能范围与座舱视角对齐(真实几何点选 + 详情面板 + 导航侧栏飞向),不包含 X-Ray/炸开视图/
   流程动画(那三者是整车视角占位区域专属的可视化手段,这里两个区域都是实体几何,用不上)。 */
function resolveSafetyZoneFromObject(obj) {
  let o = obj;
  while (o) {
    const zid = safetyNodeToZone.get(String(o.name || "").toLowerCase());
    if (zid) return zid;
    o = o.parent;
  }
  return null;
}

function setSafetyHover(obj) {
  if (safetyHoverObj === obj) return;
  if (safetyHoverObj && safetyHoverObj.material && safetyHoverOrigEmissive !== undefined) {
    try { safetyHoverObj.material.emissive && safetyHoverObj.material.emissive.copy(safetyHoverOrigEmissive); } catch (e) {}
  }
  safetyHoverObj = obj;
  if (obj && obj.material && obj.material.emissive) {
    safetyHoverOrigEmissive = obj.material.emissive.clone();
    obj.material.emissive.setHex(0x1a5a7a); // 与座舱视角同一蓝色高光,三个视角的交互反馈语言统一
  } else {
    safetyHoverOrigEmissive = undefined;
  }
}

function wireSafetyInteraction(canvasEl) {
  let downPos = null;
  canvasEl.addEventListener("pointerdown", e => { downPos = { x: e.clientX, y: e.clientY }; });
  canvasEl.addEventListener("pointerup", e => {
    if (!downPos) return;
    const moved = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
    downPos = null;
    if (moved > 6 || !safetyRoot) return;
    safetyRaycaster.setFromCamera(pointerToNDC(e, canvasEl), safetyCamera);
    const hits = safetyRaycaster.intersectObject(safetyRoot, true);
    if (!hits.length) return;
    const zid = resolveSafetyZoneFromObject(hits[0].object);
    if (zid) showZoneDetail(zid);
  });
  canvasEl.addEventListener("pointermove", e => {
    if (!safetyRoot) return;
    safetyRaycaster.setFromCamera(pointerToNDC(e, canvasEl), safetyCamera);
    const hits = safetyRaycaster.intersectObject(safetyRoot, true);
    if (hits.length && resolveSafetyZoneFromObject(hits[0].object)) {
      setSafetyHover(hits[0].object);
      canvasEl.style.cursor = "pointer";
    } else {
      setSafetyHover(null);
      canvasEl.style.cursor = "grab";
    }
  });
  canvasEl.addEventListener("pointerleave", () => setSafetyHover(null));
}

function sizeSafetyRenderer() {
  const host = $("#veh3d-safety");
  if (!host || !safetyRenderer || !safetyCamera) return;
  const w = host.clientWidth || 1, h = host.clientHeight || 1;
  safetyRenderer.setSize(w, h, false);
  safetyCamera.aspect = w / h;
  safetyCamera.updateProjectionMatrix();
}

/* 修复后的模型几何在自身局部坐标系里就是"干净"的单位(导出时没有额外的节点级缩放变换,
   不像源 GLB 那样有个 4.66x 的父节点缩放),包围盒框取物体本身即可,不需要换算比例。
   3/4 侧前方俯视角度,同时能看到结构笼的侧面纵深与车头防撞梁,和诊断阶段截图核对过的
   取景角度一致。 */
function frameSafetyCamera(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = size.length() * 0.5 || 1;
  const dir = new THREE.Vector3(0.65, 0.45, 0.9).normalize();
  safetyCamera.position.copy(center).addScaledVector(dir, radius * 1.6);
  safetyCamera.near = radius / 50;
  safetyCamera.far = radius * 20;
  sizeSafetyRenderer();
  safetyControls.target.copy(center);
  safetyControls.minDistance = radius * 0.3;
  safetyControls.maxDistance = radius * 3.5;
  safetyControls.update();
}

function setSafetyLoadingProgress(pct, done, error) {
  const el = $("#veh3d-safety-loading");
  if (!el) return;
  if (error) { el.textContent = "[ 安全结构模型加载失败,请刷新重试 ]"; return; }
  if (done) { el.textContent = "[ 已加载 ]"; el.classList.add("hide"); return; }
  el.textContent = "[ 正在载入安全结构模型… " + pct + "% ]";
}

function initSafetyScene() {
  if (safetyInited) return;
  safetyInited = true;
  const host = $("#veh3d-safety");
  if (!host) return;

  safetyScene = new THREE.Scene();
  safetyScene.background = new THREE.Color(0x070b11); // 与座舱视角同一套暗色 HUD 主题,三个视角视觉语言统一

  safetyCamera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);

  safetyRenderer = new THREE.WebGLRenderer({ antialias: true });
  safetyRenderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  host.insertBefore(safetyRenderer.domElement, host.firstChild);
  sizeSafetyRenderer();

  safetyScene.add(new THREE.HemisphereLight(0xffffff, 0x16202c, 1.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.8);
  key.position.set(2, 3, 2.4);
  safetyScene.add(key);
  const fill = new THREE.DirectionalLight(0xbfe6ff, 0.6);
  fill.position.set(-2, 1, -1.6);
  safetyScene.add(fill);

  safetyControls = new OrbitControls(safetyCamera, safetyRenderer.domElement);
  safetyControls.enableDamping = true;
  safetyControls.dampingFactor = 0.08;

  safetyRaycaster = new THREE.Raycaster();
  wireSafetyInteraction(safetyRenderer.domElement);

  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => sizeSafetyRenderer()).observe(host);
  } else {
    window.addEventListener("resize", sizeSafetyRenderer);
  }

  safetyRenderer.setAnimationLoop(() => {
    if (viewMode !== "safety") return;
    if (camTween && camTween.cam === safetyCamera && camTween.step(performance.now())) camTween = null;
    safetyControls.update();
    safetyRenderer.render(safetyScene, safetyCamera);
  });

  new GLTFLoader().load(
    SAFETY_MODEL_URL,
    gltf => {
      safetyRoot = gltf.scene;
      safetyScene.add(safetyRoot);
      // 导出脚本把 safety_cage/safety_body 两个节点的材质设成同一个 PBRMaterial 实例(共享同一张
      // 贴图,导出器会自动去重),不逐 mesh 克隆的话悬停高亮一个节点的 emissive 会连带染另一个。
      safetyRoot.traverse(o => { if (o.isMesh && o.material) o.material = o.material.clone(); });
      safetyRoot.updateMatrixWorld(true);
      frameSafetyCamera(safetyRoot);
      setSafetyLoadingProgress(100, true, false);
    },
    evt => {
      const pct = evt.total ? Math.round((evt.loaded / evt.total) * 100) : Math.round(evt.loaded / 1e5);
      setSafetyLoadingProgress(Math.min(99, pct), false, false);
    },
    err => {
      console.error("安全结构模型加载失败:", err);
      setSafetyLoadingProgress(0, false, true);
    }
  );

  // 儿童座椅是独立小模型,不挂在 safetyRoot 下——safetyRaycaster 的点选只对 safetyRoot 做
  // intersectObject,不单独加到 safetyRoot 就自动不参与区域点选/高亮,无需额外排除逻辑。
  new GLTFLoader().load(
    CHILD_SEAT_MODEL_URL,
    gltf => {
      const seat = gltf.scene;
      seat.position.fromArray(CHILD_SEAT_TRANSFORM.position);
      seat.scale.setScalar(CHILD_SEAT_TRANSFORM.scale);
      seat.rotation.y = CHILD_SEAT_TRANSFORM.rotationY;
      safetyScene.add(seat);
    },
    undefined,
    err => console.error("儿童座椅模型加载失败:", err)
  );

  // 同样是独立小模型,不挂在 safetyRoot 下,不参与区域点选。
  new GLTFLoader().load(
    STEERING_WHEEL_MODEL_URL,
    gltf => {
      const wheel = gltf.scene;
      wheel.position.fromArray(STEERING_WHEEL_TRANSFORM.position);
      wheel.scale.setScalar(STEERING_WHEEL_TRANSFORM.scale);
      wheel.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(...STEERING_WHEEL_TRANSFORM.normal).normalize()
      );
      safetyScene.add(wheel);
    },
    undefined,
    err => console.error("方向盘模型加载失败:", err)
  );
}

/* 整车/座舱/安全结构三视角切换:X-Ray、分组筛选条都是整车 3D 场景专属的控件,其余两个视角下隐藏,
   避免用户以为示意图/结构模型也能透视/分组。 */
window.veh3dSetView = function (mode) {
  const isCockpit = mode === "cockpit";
  const isSafety = mode === "safety";
  const isExt = !isCockpit && !isSafety;
  viewMode = isCockpit ? "cockpit" : isSafety ? "safety" : "ext";
  const extBtn = $("#veh3d-view-ext"), cpBtn = $("#veh3d-view-cockpit"), sfBtn = $("#veh3d-view-safety");
  if (extBtn) extBtn.classList.toggle("on", isExt);
  if (cpBtn) cpBtn.classList.toggle("on", isCockpit);
  if (sfBtn) sfBtn.classList.toggle("on", isSafety);
  const canvas = $("#veh3d-canvas"), cockpit = $("#veh3d-cockpit"), safety = $("#veh3d-safety");
  if (canvas) canvas.style.display = isExt ? "" : "none";
  if (cockpit) cockpit.style.display = isCockpit ? "" : "none";
  if (safety) safety.style.display = isSafety ? "" : "none";
  if (isCockpit) { initCockpitScene(); sizeCockpitRenderer(); } // 懒加载;display:none 时宽高为 0,切回来后要重算一次
  if (isSafety) { initSafetyScene(); sizeSafetyRenderer(); }
  const xrayBtn = $("#veh3d-xray-btn"), groupBar = $("#veh3d-group-bar"), explodeBtn = $("#veh3d-explode-btn"), flowBtn = $("#veh3d-flow-btn");
  if (xrayBtn) xrayBtn.style.display = isExt ? "" : "none";
  if (groupBar) groupBar.style.display = isExt ? "" : "none";
  if (explodeBtn) explodeBtn.style.display = isExt ? "" : "none";
  if (flowBtn) flowBtn.style.display = isExt ? "" : "none";
  if (!isExt && explodedOn) setExploded(false); // 炸开视图/流程动画是整车视角专属效果,离开前先还原,避免下次切回来状态对不上按钮
  if (!isExt && flowOn) setFlow(false);
  const hint = $("#veh3d-hint");
  if (hint) hint.textContent = isCockpit
    ? "拖动旋转 · 滚轮缩放 · 点击内饰部件/标签查看该区域合规范围"
    : isSafety
    ? "拖动旋转 · 滚轮缩放 · 点击安全笼/车身结构查看碰撞保护合规范围"
    : "拖动旋转 · 滚轮缩放 · 点击部件/标签查看该区域合规范围";
  const foot = $("#veh3d-footnote");
  if (foot) foot.textContent = isCockpit
    ? "模型:grab3d.com CC0 原始座舱模型(通用款式,无品牌标识,见 vendor/models/CREDITS.md)· 方向盘为真实模型节点,可直接点击;仪表板/空调/ECU-OTA域/座椅/脚垫/门饰板/安全气囊素材无对应独立几何,仍用悬浮标签示意位置(2026-11 简化为单一模型,不再拼装额外零件)· 该素材只有舱内部件、没有包裹的外观车身,转到较极端角度会看到部件边缘悬空,正常浏览角度不受影响"
    : isSafety
    ? "模型:业主提供的 AI 生成安全结构剖视模型(Tripo AI 按四视图生成,经减面+左右对称化修正,原始模型来源与修正方法见 vendor/models/CREDITS.md)· 安全笼/防撞梁等结构件(红黄绿三色,对称化处理)与车身外壳/座椅/假人(保留真实左右不对称)均为真实模型节点,可直接点击,关联「整车安全」维度碰撞保护类法规 · 已知局限:极少数假人表面因颜色分类阈值被误判为结构件、随结构件一起镜像,如实保留不作掩饰"
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
    if (hotspotFocusId && hs.zone.id !== hotspotFocusId) { hs.card.style.display = "none"; return; } // 聚焦单个区域时隐藏其余标签,见 hotspotFocusId 注释
    _hsVec.setFromMatrixPosition(hs.mesh.matrixWorld);
    _hsVec.project(camera);
    if (_hsVec.z > 1) { hs.card.style.display = "none"; return; } // 在相机背面
    visible.push({ hs, x: (_hsVec.x * 0.5 + 0.5) * w, y: (-_hsVec.y * 0.5 + 0.5) * h });
  });
  visible.sort((a, b) => a.y - b.y);
  const CARD_H = 28;
  let lastCardY = -Infinity;
  let lines = "";
  visible.forEach((v, i) => {
    const cardX = Math.min(w - 12, Math.max(12, v.x + 60));
    // 贪心下推到这里为止只保证"不和上一张重叠",不保证不超出画布——分组全开时最多 21 张卡片
    // 挤在同一竖排,早期版本在这里只夹了下限(20),没夹上限,多出来的卡片会被硬推到画布底部
    // 以下、甚至看起来"飞出车身外",这不是 3D 坐标错,是卡片防重叠布局本身没有边界(业主反馈
    // 过"部件跑到车外面了"排查到这里)。按剩余卡片数反向预留空间,让最后一张卡片正好不超出
    // 画布底边,挤不下时宁可轻微重叠也不超出可视区域。
    const maxY = h - 20 - (visible.length - 1 - i) * CARD_H;
    const cardY = Math.min(maxY, Math.max(20, Math.max(v.y - 40, lastCardY + CARD_H)));
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
/* 2026-11 业主要求 X-Ray 透视改成蓝色全息/HUD 风格(参考图:黑底+发光蓝色棱线+悬浮面板)——
   棱线从原来的深墨色工程图配色改成亮蓝 + 叠加混合(AdditiveBlending),线条互相重叠的地方
   (车身转折密集处)会自然叠加得更亮,对着纯黑背景有种"发光"的观感;没有真正接入 bloom
   后处理管线(项目目前没有 vendor 进 EffectComposer/UnrealBloomPass,这类后处理 shader 会
   明显增加复杂度和渲染开销),这个颜色+混合模式的组合是性价比更高的近似做法。 */
function buildEdgeLines(mesh) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 32); // 32°阈值:只留有意义的棱线,滤掉高多边形噪点
  const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({
    color: XRAY_GLOW_COLOR, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  line.visible = false;
  mesh.add(line); // 作为 mesh 的子节点,自动继承其局部变换
  return line;
}

function setXray(on) {
  xrayOn = on;
  if (on) loadMechanicalParts(); // 懒加载:不管是手动点按钮还是程序化开启(导航侧栏/炸开视图),第一次打开都要去拉这个模型
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
  const card = $("#veh3d-ext-card");
  if (card) card.classList.toggle("xray-on", on); // 驱动 index.html 里那一整套蓝色 HUD 配色
  if (scene && normalBgColor) scene.background = on ? new THREE.Color(XRAY_BG_COLOR) : normalBgColor;
}

/* ============ 阶段三:炸开视图(仅整车视角) ============ */
/* 车身真实几何(body_shell/front_end/rear_end/exhaust/glazing/mirrors/roof 这 7 个 zone,
   hotspot:false)按 zone 分组收集对应的 Object3D——和 zoneWorldBox() 用的是同一份 nodeToZone
   查表逻辑,这里要保留对象引用本身(用来改 position),不只是算一次包围盒。 */
function collectBodyZoneGroups() {
  const map = new Map();
  if (!carRoot) return map;
  carRoot.traverse(o => {
    if (!o.isMesh) return;
    const zid = nodeToZone.get(String(o.name || "").toLowerCase());
    if (!zid) return;
    const z = zoneById(zid);
    if (!z || z.hotspot) return; // hotspot 占位盒子/机械零件走 hotspots[] 那条路径,这里只管真实车身节点
    if (!map.has(zid)) map.set(zid, []);
    map.get(zid).push(o);
  });
  return map;
}

let explodeTween = null; // {t0, dur, items:[{obj,from,to}]} —— 和 camTween 同一思路,外部渲染循环每帧推进
function stepExplodeTween(now) {
  if (!explodeTween) return;
  const { t0, dur, items } = explodeTween;
  const t = Math.min(1, (now - t0) / dur);
  const e = 1 - Math.pow(1 - t, 3); // ease-out cubic
  items.forEach(it => it.obj.position.lerpVectors(it.from, it.to, e));
  if (t >= 1) explodeTween = null;
}

/* 炸开方向 = 该部件世界坐标相对整车中心的方向——车身主体(body_shell 含车轮、源模型未拆分)
   世界中心本身就接近整车中心,位移量天然很小,效果上正好是"车身主壳不动、其余部件向外飞开",
   不需要为它特殊处理。炸开距离按整车体量(carCleanBox 对角线长度的一半)按比例换算,换模型也
   不会出现距离离谱的问题。 */
function setExploded(on) {
  if (explodedOn === on || !carRoot) return;
  explodedOn = on;
  const box = carCleanBox || new THREE.Box3().setFromObject(carRoot);
  const center = box.getCenter(new THREE.Vector3());
  const carRadius = box.getSize(new THREE.Vector3()).length() * 0.5 || 1;
  const DIST_BODY = carRadius * 0.35;
  const DIST_HOTSPOT = carRadius * 0.55;

  if (on) {
    // 炸开时强开 X-Ray + 全部分组,否则电池包/ECU-OTA域等占位区域飞出去也看不见,失去意义;
    // 关闭时还原用户原先的勾选状态,不替用户做永久选择。炸开视图本来就是要同时看清楚全部
    // 部件,解除导航飞向可能留下的单点聚焦状态。
    hotspotFocusId = null;
    enterXrayOverride(HOTSPOT_GROUPS.map(g => g.id));
  }

  const items = [];
  collectBodyZoneGroups().forEach(objs => {
    objs.forEach(o => {
      if (!bodyZoneOrigLocalPos.has(o)) bodyZoneOrigLocalPos.set(o, o.position.clone());
      const orig = bodyZoneOrigLocalPos.get(o);
      const from = o.position.clone();
      let to;
      if (on) {
        const worldPos = new THREE.Vector3().setFromMatrixPosition(o.matrixWorld);
        const dir = worldPos.sub(center);
        if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
        dir.normalize();
        to = orig.clone().addScaledVector(dir, DIST_BODY);
      } else {
        to = orig.clone();
      }
      items.push({ obj: o, from, to });
    });
  });
  hotspots.forEach(hs => {
    if (!hotspotOrigLocalPos.has(hs.mesh)) hotspotOrigLocalPos.set(hs.mesh, hs.mesh.position.clone());
    const orig = hotspotOrigLocalPos.get(hs.mesh);
    const from = hs.mesh.position.clone();
    let to;
    if (on) {
      const dir = orig.clone().sub(center);
      if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
      dir.normalize();
      to = orig.clone().addScaledVector(dir, DIST_HOTSPOT);
    } else {
      to = orig.clone();
    }
    items.push({ obj: hs.mesh, from, to });
  });
  explodeTween = { t0: performance.now(), dur: 700, items };

  if (!on) exitXrayOverride();

  const btn = $("#veh3d-explode-btn");
  if (btn) btn.classList.toggle("on", on);
  if (on && camera && controls) flyCameraTo(camera, controls, center, carRadius * 1.5, _orthoHalfHeight); // 留够空间看炸开后的轮廓,不被裁掉
  if (on && flowOn) setFlow(false); // 和流程动画互斥——炸开后各部件位置会动,流程线段没法跟着实时重算,索性二选一
}

/* ============ 阶段四:流程动画(仅整车视角) ============
   参考 Toyota Mirai 的流程可视化 WebGL 示例,但这台车(奥迪 R8,燃油 V8)没有氢燃料电池那套
   物理管路,不能照搬"氢气流动"这个具体场景——改为画这台车真实具备、且和本应用的"合规"主题
   相关的两条路径:① 动力传递路径(发动机→离合器→变速器→半轴传动轴→车轮,纯机械动力流,
   对应整车准入/环保全链条维度)② ADAS 感知数据流(三个传感器分区→ECU/OTA 域→仪表板,
   对应 ADAS/网络安全维度)。沿路径画发光细管 + 若干沿管道循环移动的光点模拟"流动"观感,
   不接 bloom 后处理(和 X-Ray 棱线发光同样的性价比考量,见 buildEdgeLines 注释)。 */
const FLOW_PATHS = [
  { id: "power", label: "⚡ 动力传递路径", color: 0x2dd4ff, zones: ["engine", "clutch", "transmission", "axle_driveshaft", "body_shell"] },
  { id: "adas", label: "📡 ADAS 感知数据流", color: 0xffb020, zones: ["adas_front_sensor", "adas_corner_sensor", "adas_rear_sensor", "ecu_ota", "dashboard"] },
];
let flowOn = false;
let flowObjects = []; // 场景里新增的 tube/粒子网格,关闭时逐个移除,不留垃圾
let flowParticles = []; // [{mesh, curve, t, speed}]

function buildFlowPath(path) {
  const pts = [];
  path.zones.forEach(zid => {
    const z = zoneById(zid);
    if (!z) return;
    const r = zoneExtWorldCenter(z);
    if (r) pts.push(r.center);
  });
  if (pts.length < 2) return; // 该视角下这条路径上的区域凑不够两个有效点位,画不出线,跳过
  const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.15);
  const tubeGeo = new THREE.TubeGeometry(curve, Math.max(32, pts.length * 16), 0.065, 8, false);
  const tubeMat = new THREE.MeshBasicMaterial({
    color: path.color, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false,
  });
  const tube = new THREE.Mesh(tubeGeo, tubeMat);
  tube.userData.hotspotEl = true; // 复用 setXray() 的跳过标记,避免被 X-Ray 材质替换逻辑误处理
  tube.renderOrder = 10; // depthTest 关了之后靠 renderOrder 定层级,确保光点画在管道上面而不是被管道盖住
  carRoot.add(tube);
  flowObjects.push(tube);

  const N_PARTICLES = 3;
  for (let i = 0; i < N_PARTICLES; i++) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 12, 12),
      new THREE.MeshBasicMaterial({ color: path.color, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false })
    );
    mesh.userData.hotspotEl = true;
    mesh.renderOrder = 11;
    carRoot.add(mesh);
    flowObjects.push(mesh);
    flowParticles.push({ mesh, curve, t: i / N_PARTICLES, speed: 0.22 }); // 约 4.5 秒跑完整条路径
  }
}

const _flowTimer = new THREE.Timer(); // THREE.Clock 在这个版本已标记废弃,改用替代的 Timer
function stepFlowAnimation() {
  _flowTimer.update();
  const dt = _flowTimer.getDelta(); // 秒
  if (!flowOn || !flowParticles.length) return;
  flowParticles.forEach(p => {
    p.t = (p.t + p.speed * dt) % 1;
    p.mesh.position.copy(p.curve.getPointAt(p.t));
  });
}

function clearFlowObjects() {
  flowObjects.forEach(o => { if (o.parent) o.parent.remove(o); o.geometry && o.geometry.dispose(); o.material && o.material.dispose(); });
  flowObjects = [];
  flowParticles = [];
}

function buildFlowLegend() {
  const host = $("#veh3d-flow-legend");
  if (!host) return;
  host.innerHTML = flowOn ? FLOW_PATHS.map(p =>
    `<span class="veh3d-flow-chip" style="--c:#${p.color.toString(16).padStart(6, "0")}">${esc(p.label)}</span>`
  ).join("") : "";
}

function setFlow(on) {
  if (flowOn === on || !carRoot) return;
  flowOn = on;
  if (on) {
    // 流程动画要同时看清楚涉及的两条路径上的区域,和炸开视图同理:强开 X-Ray + 相关分组,
    // 关闭时还原用户原先的勾选状态;也和炸开视图互斥(见 setExploded 里的对称处理)。
    hotspotFocusId = null;
    enterXrayOverride(["powertrain", "chassis", "body", "connectivity", "interior"]);
    if (explodedOn) setExploded(false);
    FLOW_PATHS.forEach(buildFlowPath);
  } else {
    clearFlowObjects();
    exitXrayOverride();
  }
  const btn = $("#veh3d-flow-btn");
  if (btn) btn.classList.toggle("on", on);
  buildFlowLegend();
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

  await Promise.all([loadZones(), loadTaxonomy()]);
  renderNavSidebar();

  const panelBg = getComputedStyle(document.documentElement).getPropertyValue("--panel2").trim() || "#e5efdd";
  normalBgColor = new THREE.Color(panelBg);
  scene = new THREE.Scene();
  scene.background = normalBgColor;

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
    if (camTween && camTween.cam === camera && camTween.step(performance.now())) camTween = null;
    stepExplodeTween(performance.now());
    stepFlowAnimation();
    controls.update();
    renderer.render(scene, camera);
    updateHotspotLayer();
  });

  const xrayBtn = $("#veh3d-xray-btn");
  if (xrayBtn) xrayBtn.addEventListener("click", () => setXray(!xrayOn));
  const explodeBtn = $("#veh3d-explode-btn");
  if (explodeBtn) explodeBtn.addEventListener("click", () => setExploded(!explodedOn));
  const flowBtn = $("#veh3d-flow-btn");
  if (flowBtn) flowBtn.addEventListener("click", () => setFlow(!flowOn));
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
