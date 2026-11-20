# 第三方 3D 模型署名

## Audi R8(现用模型)

- 来源: 业主提供的素材包(`Audi R8.rar`,含 `.blend`/`.dae`/`.fbx` 与贴图),业主已确认拥有合法使用权,
  用于本工具内部合规监控场景(非对外商业分发)。原始素材未附带 license/readme 文件,来源与版权归属
  未在本仓库另行记录,由业主自行留存凭证。
- 车身造型/设计为 Audi(奥迪)品牌车型,存在外观专利/商业外观(trade dress)权利归属问题——本仓库
  仅存放业主自行确认拥有使用权的素材,不代表 Anthropic/Claude Code 或本项目对版权状态做出保证。
- **已处理**:原始模型正面/背面的奥迪四环车标(几何节点,非贴图贴花)已在转换时整体删除,以降低商标
  关联风险(业主 2026-09 确认)。
- 技术处理(`vendor/models/AudiR8/AudiR8.glb`,约 1.3MB):原始 `.dae`(COLLADA)经 trimesh 转换为
  glTF-Binary;修正坐标轴(源文件 Z-up 转为 glTF Y-up);按包围盒位置将 33 个网格节点归入 7 个分区
  (body_shell/front_end/rear_end/exhaust/glazing/mirrors/roof,详见 `data/vehicle_zones.json`);
  剔除工作室地面参照平面与车标节点;原始贴图未能在转换中正确保留,改用按分区指定的纯色材质
  (车漆深红、进气格栅/保险杠深灰、排气钢灰、玻璃深色)。
- 已知局限(如实记录,不作为"车轮"等独立分区的依据):源模型车轮几何已与车身主壳(`Mesh_000`)合并
  导出,无法作为独立可点选分区拆分;车窗玻璃在源模型中无独立于车身壳体的透明网格。
- **2026-11 镜像修复**:业主反馈俯视角度下车身/车轮大片缺失,排查后发现根因不是渲染/相机问题——
  原始 `.dae` 本身只建了半边车身(常见建模习惯,实车生产中靠"镜像"修改器实时生成另一半),而
  trimesh 转换时没有展开这个镜像,33 个网格节点里有 28 个只有单侧(X≥0 或 X<0)三角形,只有
  body_shell/rear_end 等少数几个节点本来就是左右对称导出的。逐节点检测哪些单侧、哪些本来就对称,
  对单侧的节点关于车身中轴(X=0)镜像一份顶点+顶点色,并反转镜像后三角形的环绕顺序(镜像会翻转
  手性,不翻环绕会导致法线/背面剔除方向反了),合并进原网格再整体导出覆盖原文件。不改变节点
  名称/数量(仍是 33 个,`data/vehicle_zones.json` 的 `gltf_nodes` 映射不用改),文件从约 1.27MB
  增至约 1.97MB。

## 座舱内饰(现用模型,座舱视角)

- 来源: [grab3d.com](https://grab3d.com) 的 CC0 1.0 Universal(公共领域,无需署名)素材,业主自行找到并
  提供链接(2026-11):基础舱体 [modern-car-interior](https://grab3d.com/models/vehicles/modern-car-interior/)
  (来自 "Cozy Car Interior Kit"),叠加同一许可家族 "Cozy Car Parts" 套件里的独立部件:车门饰板
  (car-door-panel)、中控台(center-console)、仪表板(car-dashboard,自带方向盘)、仪表盘总成
  (instrument-cluster)、出风口(car-air-vent)、座椅(car-seat)、脚垫(car-floor-mat)。均为通用款式,
  无品牌标识/车标,程序化建模(各素材 manifest.json 内 AI 声明字段确认非 AI 生成)。license 条款见各
  下载包自带的 `LICENSE.txt`(CC0,公共领域放弃版权,可自由使用/修改/商用、无需署名)。
- 技术处理(`vendor/models/CockpitInterior/cockpit.glb`,约 12MB):用 trimesh 以 `modern-car-interior.glb`
  的舱体为基座,其余 7 个部件按世界坐标拼装进场景——坐标基准取自基座模型自带的 `windshield_glass`/
  `steering_wheel` 两个既有物体的实测世界坐标包围盒(而非素材 manifest 里含糊的"朝向 -Y"等 Blender
  导出前坐标系描述,实测更可靠);删除了基座自带的方向盘节点(`modern-car-interior_steering_wheel`),
  改用 car-dashboard 自带的、与其仪表板造型本就对齐的方向盘。左右对称的部件(门饰板/出风口/座椅)
  只下载一份,另一侧用程序化镜像(顶点 X 坐标取反 + 三角形环绕顺序反转,与 Audi R8 镜像修复用的
  同一手法)生成,避免下载两份重复素材。多次复用同一来源部件时,构造新 Trimesh 对象共享(而非
  深拷贝)原始 `visual`/材质对象,使导出器能对嵌入贴图去重,避免贴图随复用次数线性膨胀(实测
  从未去重前的 56.6MB 降到约 12MB)。
- 节点命名前缀对应关系(供核对 `data/vehicle_zones.json` 的 `cockpit_nodes` 字段):`asm_dash_*`=仪表板,
  `asm_cluster_*`=仪表盘总成,`asm_vent_l_*`/`asm_vent_r_*`=左右出风口,`asm_seat_driver_*`/
  `asm_seat_pax_*`=驾驶/副驾座椅,`asm_door_l_*`/`asm_door_r_*`=左右门饰板,`asm_mat_*`=脚垫,
  `asm_console_*`=中控台(无对应合规分区,纯视觉填充);未加前缀的 `modern-car-interior_*` 节点为
  基座舱体本身(车身壳体、挡风玻璃、环境光饰条等,作为未映射的视觉背景保留)。
- 已知局限:素材包内没有独立的安全气囊(airbag)部件,`airbag` 分区在座舱视角里仍为示意热点标注,
  不编造几何体。
- **2026-11 第二批(纯视觉填充,业主指示)**:同一 [Cozy Car Interior Kit](https://grab3d.com/kits/cozy-car-interior/)
  里另外 9 个零件——车载收音机(car-radio)、导航界面(car-navigation-screen)、踏板(car-pedals)、
  电话架(car-phone-holder)、钥匙遥控器(car-key-fob)、换挡杆(gear-shift)、扬声器(car-speaker,
  左右各一)、遮阳板(sun-visor)、儿童安全座椅(child-car-seat)——合并进同一个 cockpit.glb,纯粹
  让座舱看起来更完整、更真实,**不对应任何新的可点选合规分区**(不在 `data/vehicle_zones.json`
  的 `cockpit_nodes` 字段里出现,点击这些部件会按"未识别部件"处理,和中控台等既有的纯装饰件
  一致)。位置基准沿用既有舱内地标(仪表板/风挡/中控台/门板/座椅的实测世界坐标包围盒,见上文),
  收音机与扬声器的默认朝向(素材分别是"平放显示面朝上"和"喇叭朝上像摆桌上")不适合直接装车,
  各加了一个渲染截图核对过的 90° 修正旋转。**儿童安全座椅如实处理**:这套素材没有后排座椅几何,
  没有编造"已装在后排"的画面,摆在副驾座椅后方地板上当作随车存放的道具。

## 机械零件(现用模型,整车视角 X-Ray 透视)

- 来源: [grab3d.com](https://grab3d.com) 的 CC0 1.0 Universal 素材,来自
  [Cozy Car Parts & Garage Kit](https://grab3d.com/kits/cozy-car-parts/)(与座舱素材同一许可家族,
  2026-11):V8 Engine、Manual Gearbox(手动变速箱)、Brake Disc(制动盘,含卡钳)、Shock Absorber
  (减震器)、Car Radiator(散热器)。均为通用款式,无品牌标识,license 条款见各下载包自带的
  `LICENSE.txt`(CC0,公共领域放弃版权,可自由使用/修改/商用、无需署名)。实测这些模型本身就是
  按真实世界米制单位建模(如 V8 发动机约 0.69×0.76×0.81m、制动盘直径约 0.32m),不是随意缩放的
  游戏资产比例。
- 技术处理(`vendor/models/MechanicalParts/mechanical.glb`,约 5.2MB):5 个零件的节点名本就互不
  冲突(`v8-engine_body`/`gearbox_body`/`brake-disc_body`/`shock-absorber_body`/
  `car-radiator_body`),用 trimesh 原样合并进一个文件,不在导出阶段做任何平移/缩放/旋转——减震器
  要分别用在前悬架和后悬架两个分区,运行时各自 `clone()` 一份摆到不同位置更合理,不必在文件里
  存两份重复几何。位置/缩放/旋转统一在 `vehicle3d.js` 运行时按各分区的 `hotspot_pos` 现算(与
  AudiR8 车身自身单位 ≈2 单位/米 的实测换算比例一致),制动盘与减震器各加了一个固定的 90°
  修正旋转(素材默认朝向分别是"平放"和"横放",不加这个旋转摆到车上会看起来像倒地的轮子/
  横躺的减震器,这个旋转是通过渲染截图肉眼核对过的,不是凭空猜的角度)。
- 已知局限:这套零件没有半轴/传动轴/转向系统/离合器对应的单独模型,这几个分区仍是占位方块,
  不拿别的零件凑数;摆放位置复用整车视角既有的 hotspot_pos 比例坐标,本来就是示意性的,不是
  精确到螺栓孔位的装配图。

## Three.js

- 来源: [mrdoob/three.js](https://github.com/mrdoob/three.js)(r186),含 `OrbitControls`/`GLTFLoader` 附加模块
- 许可: MIT(见 `vendor/three/LICENSE`)

## Three.js

- 来源: [mrdoob/three.js](https://github.com/mrdoob/three.js)(r186),含 `OrbitControls`/`GLTFLoader` 附加模块
- 许可: MIT(见 `vendor/three/LICENSE`)
