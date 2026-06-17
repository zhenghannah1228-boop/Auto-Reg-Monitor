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

**(后续三批 L3 深拆把上述大部分『测·部分』转绿;最终边界见文末两张交付表。)**

## ✅ L3 批量深拆 — 第二批(2026-06)绿格 9→19 + 内存兜底
三目标全部落地,沉淀第 4/5 类评分模型提取器(均带回归锚点):

**1. JNCAP `jncap_hic_bands()`** — R7-xx 是试验方法(無阈值),真正评分在 `2025_en.pdf`(评价方法)。
头部 HIC15 **五色等级**(第4类模型):Green<650→1.00 / Yellow 650–1000→0.75 / Orange→0.50 /
Brown→0.25 / Red≥1700→0.00。颈/胸/大腿用评价函数图(图23 连续曲线)非离散阈值,严禁臆造不抽。
接入 frontal_rigid_full / frontal_mpdb_offset / side_impact 三处 JNCAP 头部 L3。
⚠ R7-xx 中『Neck load shall be 1000』等是 **CFC 滤波通道等级,非伤害阈值**(已识别陷阱不误取)。

**2. Bharat `bharat_L3(start,end)`** — AIS-197 按章节拆,采纳 **Euro/EEVC 滑动 HPL-LPL**(每部位满4点,capping)。
§3.2 正面(头HIC500/700·3ms72/88、颈剪切1.9/3.1、胸压缩22/42、股骨3.8/9.07)→ frontal_mpdb_offset;
§4.2 侧碰(头/胸/腹1.0/2.5·骨盆耻骨力3.0/6.0)→ side_impact;§5 柱碰头部 capping(HIC15<700/Peak<80g)
→ side_pole。去 HIC15 下标/3msec 噪声、仅采纳 HPL+LPL 均解析出者。

**3. ASEAN `asean_fitment(sheet)`** — 业主 2026-06 确认:主动安全按**装备率评分**(第5类模型,
Fitment Rating:标配 Option A→α1.0 / 选配→0.5 / 无→0,×国别系数),非性能阈值。
接入 adas_aeb(SAT-AEB CCRs/CCRm&CCRb/MS-AEB CM)/ lane_support(SAT-LKA)/ blind_spot(MS-BST TFS8)/
adaptive_highbeam(MS-AHB A–G 七档)。『ASEAN 不测性能、只看是否装配』本身即高价值跨体系差集。

前端 `cellClass`/`scoringName`/`renderL3` 扩 `_bands`/`_fitment`,五种评分制并排可读(色带带颜色块、
装备率显 Option→α + TFS 满分)。全 16 build 回归 PASS。

**内存兜底(L3 翻倍前)**:`pdf_text`/`cncap_L3_*` 逐页 `pg.flush_cache()`(side_impact 893→455MB、
R7-03 单文件 538→79MB);`build_all` 串行子进程 + `RLIMIT_AS` 软上限(默认2GB)+ 单 build 失败不中断。

**occupant_monitoring 基准修正(业主 2026-06 确认)**:ASEAN 有 SAT-SBR(安全带提醒 TFS6)+
COP CPD(儿童遗留检测 TFS5)两张装备率评分表,原标不测 `[0,0,0]` 系漏项,已修正为 SBR✓+CPD✓
(装备率 L3),DMS 仍不测。

## ✅ L3 深拆第三批(2026-06)绿格 20→32 —— Euro 表格型阈值 + 采纳链
- **Euro 正面 AOP**(`euro_hpl_lpl`):正碰协议 v1.1 §3.5 伤害限值在表格里(非文本层),多假人列
  按 [HIII5th/50th/THOR50th/95th] 排,取 **HIII 50th=第2个 num-num 对**(3行窗口合并续行)。
  实拆头HIC15[500,700]·Ares[72,80]、颈Fx[1.9,3.1]/Fz[2.7,3.3]/My[42,57]、股骨[3.8,9.1]、膝[6,15]、
  胫骨[2.0,8.0]/[0.4,1.3]。色带 Green1.25/Yellow1.0/Orange0.75/Brown0.5/Red0。
- **Euro 行人头型**(`euro_pedestrian_head_bands`):Pedestrian v8.5 §4 HIC15 五色网格(<650…≥1700)。
- **采纳链**:Latin/ANCAP 正碰+行人采纳 Euro AOP;Latin/ANCAP 侧碰采纳 Euro AE-MDB WorldSID 滑动限值
  (复用 Euro 侧碰 HPL-LPL)。ASEAN 行人头部按 AOP HPT 装备率(TFS8)。
- 新增绿格:frontal_rigid_full / frontal_mpdb_offset 的 Euro+Latin+ANCAP(6)、vru_passive 的
  Euro+Latin+ANCAP+ASEAN(4)、side_impact 的 Latin+ANCAP(2)= 12 格。

## ✅ L1 纠错(业主指示,2026-06):Bharat 全宽正碰 → 不测
核 AIS-197 测试矩阵:Bharat NCAP 正面**唯一**为 Offset Deformable Barrier(ODB)64km/h 40% 偏置
(§10.1 / Annexure-I),**不做全宽 100% 刚性正碰**。原 `frontal_rigid_full` 把 Bharat 标"测"系 L1
误判(正则误命中 "frontal impact"),已纠正为**不测**。此项做全宽者由 7 套降为 6 套(中/日/欧/澳/美/Latin)。

---

# 📦 交付说明 · L3 深拆最终状态(2026-06 收尾)

128 格:**测 33 / 测·部分 37 / 不测 48 / 异构 8 / 待补 2**。已实拆 **6 类评分模型**并排可比:
三限值(C-NCAP)/ 滑动 HPL-LPL(Euro·Bharat·Latin·ANCAP)/ Value+Points(ASEAN 碰撞 xlsm)/
5色等级(JNCAP 头部·Euro 行人)/ 装备率 fitment(ASEAN 主动安全)/ pass-fail 合规限值(Bharat 行人 AIS-100)。
`build_all.py` 一键重建,16 项各带回归断言。

> **核心价值(跨体系差集)由 L1/L2 完全成立**;L3 是"看得见的细节加成"。下列两表是经业主逐类拍板的
> **最终边界**——不是遗漏,是"能拆的都拆了,剩下的按决策不拆 / 等外部补料"。

## 表一 · 已知边界(按决策不再深拆 · 不影响差集)

| 类 | 测试项 / 体系 | 格数 | 评分模型 | 不拆原因(业主拍板) |
|---|---|---|---|---|
| ① | adas_aeb · vru_active · lane_support(中/欧/日/澳/拉)+ blind_spot(ANCAP)+ adaptive_highbeam(C-NCAP 附录S) | 17 | 速度区间/避撞档 | **不建新结构**:差集已靠 L1/L2 成立,拆到速度档颗粒度投入产出比失衡(工作量最大、数据最细、最少人看) |
| ③ | post_crash_safety(天线/eCall)· ev_hazard(高压 pass-fail)· restraint_system(约束组件) | 8 | pass-fail / 组件 | **本质无伤害阈值表**,判定型,不硬塞三限值 |
| ② | whiplash_rear(Euro 鞭打曲线·JNCAP 评价函数)· side_pole(Euro/Latin/ANCAP,柱碰用 WorldSID 但协议未独列表) | 7 | 图形/曲线 | 阈值在图里、文本取不到;**优先级低,暂不 OCR** |
| ④ | occupant_monitoring(C-NCAP 附录N 点分配 · JNCAP SBR · Euro/ANCAP CPD) | 4 | 点分配(异质) | 点制各异,**优先级低,暂不逐体系建点结构** |
| — | US 全系 | 8 | NHTSA 星级 / IIHS G·A·M·P | 异构等级制,标 `DIFFERENT_SCORING_MODEL`(显示为"异构",非"测·部分") |

(① 的 ASEAN 同类项已是"装备率绿",是另一种模型,不在此列。)

## 表二 · 待外部补料(给材料即可补,已留接口)

| 测试项 / 体系 | 状态 | 需要的外部材料 |
|---|---|---|
| adaptive_highbeam · Euro | 待补 | Euro NCAP **灯光/AHB 协议**(现实评估 AHB,本批源未含) |
| adaptive_highbeam · ANCAP | 待补 | ANCAP **AHB 协议**(同上) |

> ✅ **已补料**:Bharat vru_passive —— 业主提供 **AIS-100 (Rev.1)** 后已实拆(`bharat_ais100_pedestrian`):
> 头型 HIC1000/1700 区、下腿型 MCL≤22mm·ACL/PCL≤13mm·胫骨弯矩≤340Nm、上腿型 合力≤7.5kN·弯矩≤510Nm
> (UN GTR9 系 pass-fail 合规限值);该格已转绿"测"。
> 剩余两格(Euro/ANCAP AHB)收到协议后沿用既有提取器即可补,接口已就位。

---

> **原则复述**:能查证按原文拆;模型异质/图形/源缺则如实标边界,**严禁臆造塞进统一结构**。
> 全程每项 L3 带回归断言锚点(如 HIC15=[500,700]、NIC=[8,30]、TFS=8),`build_all.py` 16/16 PASS。
