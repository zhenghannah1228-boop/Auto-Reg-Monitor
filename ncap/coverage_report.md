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

## ⚠ 需业主确认:JNCAP「侧面柱碰」基准疑误
`sample.json` 的 JNCAP `L1_subtests.侧面柱碰 = true`,但**全部 19 份 JNCAP R7 协议中没有任何柱碰(pole)测试**:
- R7-01 全宽正碰 / R7-02 偏置MPDB / **R7-03 侧面碰撞(仅 MDB,0 处 pole)** / R7-04 EV感电 /
  R7-05 后碰颈部 / R7-06·07 行人 / R7-08 SBR / R7-09~13 AEB / R7-14 车道 / R7-15 误踩 /
  R7-16 大灯 / R7-18·19 儿童座椅。
- 全 R7 文档 `pole` 命中数 = 0。

→ 据源,JNCAP 侧碰只做 MDB、**不做柱碰**,`侧面柱碰` 应为 `false`。规格 §4 原表此格即标 `✓?`(待确认)。
**按"严禁臆造 / 疑似 bug 先与业主确认"原则,我不擅自把它填 true 去凑基准,也不静默改。请业主确认是否把 sample.json 的 JNCAP 侧面柱碰 改为 false。**

## 已验证
- ANCAP `extract_ancap.py` side_impact L1/L2 回归对 sample.json 4/4 PASS。
- ASEAN xlsm `AOP Side MDB `(尾空格)结构 = sample.json:HEAD(HIC15/3ms)+CHEST(上中下肋,各4分)+
  Shoulder/Viscous + ABDOMEN + PELVIS,Value+Points 4分制 + airbag 修正(-1)。
- 拉美 Euro 原始协议齐(AE-MDB v8.3 / Oblique Pole v7.2 / Pedestrian v8.5 / Whiplash v3.3.1 等)。

## 下一步(待业主确认 JNCAP 基准后)
按 8 体系补完 side_impact 行(C-NCAP 阈值表 / JNCAP R7-03 / ASEAN xlsm / Euro·Latin AE-MDB v8.3 /
US 异构 / Bharat 章节)→ 跑 §8 回归 → 出 ncap_matrix.json side_impact 行 → 再推广其余测试项。
