# NCAP 矩阵 — 源覆盖状态

更新:2026-06-17 · **全部 8 体系源文件到齐**(12 卷 + ASEAN 7z 补包)

## 各体系源就绪度

| 体系 | 源 | side_impact 可拆深度 | 备注 |
|---|---|---|---|
| C-NCAP(中国) | ✅ 附录 A-T 齐 | L1/L2/L3(附录G 可变形壁障 + 附录H 柱碰) | L3 阈值表按 §5.2 提取并比对 sample.json |
| JNCAP(日本) | ✅ R7-01~19 英文层 | L1/L2(R7-03 侧碰);L3 待拆 | ⚠ 见下「JNCAP 柱碰」 |
| ASEAN(东盟) | ✅ xlsm(27 sheet)+ 协议 | **L1/L2(协议)+ L3(xlsm 'AOP Side MDB ')** | 7z 补包已补齐 xlsm + 侧碰v3.3 + AEB/BST/AHB/LSS 协议 |
| Latin NCAP(拉美) | ✅ 自有 + Euro 原始协议 | L1/L2/L3(AOP + 采纳 Euro AE-MDB v8.3) | |
| ANCAP(澳洲) | ✅ 全协议 | **L1/L2 已跑通(回归 PASS)**;L3 协议内评分表 + Euro v8.3 | |
| Euro NCAP(欧盟) | ✅ crash protection 正文 + Euro v8.3 | L1/L2(正文)+ L3(AE-MDB v8.3) | |
| US NCAP(美国) | ✅ IIHS 齐 | L1/L2;L3=DIFFERENT_SCORING_MODEL | NHTSA 侧碰仅中文 .doc(次要) |
| Bharat(印度) | ✅ AIS-197 | 按章节拆 | 单文件多项 |

**源缺口:无(ASEAN 已由 7z 补包解决)。**

## ✅ side_impact 行已完成(§8 回归 32/32 PASS)

`build_side_impact.py` 8 体系实拆对 sample.json 逐字段通过:L1 子测试项(全8套)、C-NCAP L3 阈值(前排+二排7项)、ASEAN xlsm L3 区块。产出 `ncap_matrix.json`(side_impact 行)。

### JNCAP「侧面柱碰」基准已修正(业主确认)
`sample.json` 的 JNCAP `L1_subtests.侧面柱碰 = true`,但**全部 19 份 JNCAP R7 协议中没有任何柱碰(pole)测试**:
- R7-01 全宽正碰 / R7-02 偏置MPDB / **R7-03 侧面碰撞(仅 MDB,0 处 pole)** / R7-04 EV感电 /
  R7-05 后碰颈部 / R7-06·07 行人 / R7-08 SBR / R7-09~13 AEB / R7-14 车道 / R7-15 误踩 /
  R7-16 大灯 / R7-18·19 儿童座椅。
- 全 R7 文档 `pole` 命中数 = 0。

→ sample.json 已修正 JNCAP `侧面柱碰` true→false(业主 2026-06 确认);并新增 key_difference:
「JNCAP 是 8 套体系中唯一侧碰只做 MDB、不做柱碰的体系」。

## 已验证
- ANCAP `extract_ancap.py` side_impact L1/L2 回归对 sample.json 4/4 PASS。
- ASEAN xlsm `AOP Side MDB `(尾空格)结构 = sample.json:HEAD(HIC15/3ms)+CHEST(上中下肋,各4分)+
  Shoulder/Viscous + ABDOMEN + PELVIS,Value+Points 4分制 + airbag 修正(-1)。
- 拉美 Euro 原始协议齐(AE-MDB v8.3 / Oblique Pole v7.2 / Pedestrian v8.5 / Whiplash v3.3.1 等)。

## 下一步(待业主确认 JNCAP 基准后)
按 8 体系补完 side_impact 行(C-NCAP 阈值表 / JNCAP R7-03 / ASEAN xlsm / Euro·Latin AE-MDB v8.3 /
US 异构 / Bharat 章节)→ 跑 §8 回归 → 出 ncap_matrix.json side_impact 行 → 再推广其余测试项。

## ✅ 碰撞保护类 10 项 L1/L2 全拆完成(2026-06)
matrix 10 行(各带 diff_summary 差集摘要 + key_differences):frontal_rigid_full /
frontal_mpdb_offset / frontal_small_overlap / side_impact / side_pole / whiplash_rear /
post_crash_safety / ev_hazard / restraint_system / vru_passive。
- **L1(测/不测)全 8 体系实拆 + 回归断言**;每项独立 build_*.py(build_all.py 一键重建)。
- **L2 参数**(速度/假人/壁障)已填,无空白"测"格;C-NCAP 速度均按 §5.1 核对值
  (A/B=50、G=60、H/L=32、K=15、O=40;JNCAP 全宽经源核正 55→50)。
- **L3 深拆**目前仅 side_impact 的 C-NCAP(三限值)/ASEAN(xlsm Value+Points)/
  Euro(滑动 HPL-LPL)= 绿"测";其余 42 格为"测·部分"(L1/L2 定、L3 待深拆),
  US 6 格异构(星级/IIHS 等级)。L3 深拆为下一阶段(按各项 §5.2 表/ xlsm / Euro 协议推进)。
- 前端着色:绿=L3已拆全 / 金=测·部分(L3待拆) / 蓝=异构 / 斜纹=不测。

## ✅ 主动安全类 6 项 L1/L2 完成(2026-06)— 全矩阵 16 项骨架铺满
adas_aeb(对车辆)/ vru_active(主动行人)/ lane_support / blind_spot / adaptive_highbeam /
occupant_monitoring。各 build_*.py 回归 PASS;均做了"遇不确定先核对"的源勘查:
- **AEB 按 §4 拆两行**:adas_aeb=对车辆(C2C/路口车/摩托)、vru_active=对行人/自行车;
  JNCAP 无直行C2C(仅路口对车)、ASEAN/Latin 做C2M摩托、US 仅前车C2C、Bharat AIS-197 无AEB。
- **vru_active**:C-NCAP/JNCAP/ANCAP/Euro 全(含夜间行人+自行车);Latin 仅行人;ASEAN(MS-PED是被动→vru_passive)/US/Bharat 不做。
- **lane_support**:7 套均 LDW+LKA(Bharat 不测);ELK 深浅不一(定性,L3 细分)。
- **blind_spot**:仅 ASEAN(MS-BST)+ ANCAP(并入车道/变道);余不单列。
- **adaptive_highbeam**:ASEAN(MS-AHB)+ C-NCAP(附录S 灯光含AHB);Euro/ANCAP 现实有但源未含(标待补)。
- **occupant_monitoring**:子项异质——C-NCAP(SBR+儿童遗留)、JNCAP(仅SBR)、ANCAP/Euro(儿童遗留CPD)。
- 全矩阵 128 格:绿(L3拆全)3 / 金(测·部分,L1-L2定L3待拆)67 / 蓝(US异构)8 / 不测 50。
- 待业主确认的软判定:C-NCAP 附录N 是否含 DMS;Euro/ANCAP AHB 源待补;lane ELK 分体系细分。

## ✅ L3 批量深拆 — 第一批(2026-06)绿格 3→9
`extract_common.py` 沉淀三类可复用 C-NCAP 提取器(均带回归锚点,严禁臆造):
- **`cncap_L3_tables(gl)`** 表模式:抽『高性能限值/低性能限值』结构表 → {组:{指标:[高,低]}}。
  `num1()` 拒绝多 token / 公式 / PDF garbled 单元格(如附录J 上颈部Fx+『2 23 40/N』被丢弃,不臆造)。
- **`cncap_L3_text(gl,captions)`** 文本模式:阈值以文本行渲染时(附录A/B 头部表),按表标题定位、
  关键词门控抓『指标 高 低 极限』单值行;双假人多列行(颈/胸/腿 6 数字)自动跳过(不臆造)。
- **`cncap_L3_paired(gl)`** 配对模式:『高性能限值:指标 值 / 低性能限值:指标 值』两行分列(附录O 腿型)。

本批新增绿格(C-NCAP 三限值实拆 + 回归锚点):
| 测试项 | 源 | 锚点 | 体系 |
|---|---|---|---|
| frontal_rigid_full | 附录A 表A.7 | 头部HIC15=[500,700,700] | C-NCAP |
| frontal_mpdb_offset | 附录B 头部 + ASEAN xlsm AOP Frontal ODB | HIC15=[500,700,700] / ODB区块 | C-NCAP·ASEAN |
| side_pole | 附录H | 柱碰HIC15=[500,700] | C-NCAP |
| whiplash_rear | 附录J | 驾驶员NIC=[8,30]、上颈Fz+=[475,1130] | C-NCAP |
| vru_passive | 附录O | 腿型大腿弯矩=[390,440] | C-NCAP |

(side_impact 既有 C-NCAP/ASEAN/Euro 三绿不变。)前端 `cellClass` 绿判定扩 `_extracted_tables`/`_blocks`;
`renderL3` 新增分组阈值表渲染。

**仍为测·部分(非懒拆,系评分模型异质,严禁强转三限值):**
- 附录K 事故后=eCall 天线增益/角度评分;附录L 新能源=高压绝缘/泄漏/热失控 pass-fail;
  附录M 约束=部件/翻滚评价;附录O 头型=HIC 颜色网格(逐网格点),均非『高/低/极限』三限值模型。
- Euro 正碰/鞭打协议正文未以 HPL/LPL 文本暴露阈值表(侧碰 v1.1 p21 是唯一已验证 HPL-LPL 源),
  不强抽以免臆造;Bharat AIS-197 单文件多项,按章节拆待续。
- **下一阶段**:JNCAP R7-xx 阈值、ASEAN 其余 xlsm 评分表(SAT/MS-*)、Bharat AIS-197 章节细拆。
