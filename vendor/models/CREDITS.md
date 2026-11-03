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

## Three.js

- 来源: [mrdoob/three.js](https://github.com/mrdoob/three.js)(r186),含 `OrbitControls`/`GLTFLoader` 附加模块
- 许可: MIT(见 `vendor/three/LICENSE`)

## Three.js

- 来源: [mrdoob/three.js](https://github.com/mrdoob/three.js)(r186),含 `OrbitControls`/`GLTFLoader` 附加模块
- 许可: MIT(见 `vendor/three/LICENSE`)
