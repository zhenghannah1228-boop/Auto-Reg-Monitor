# NCAP 矩阵 — 源覆盖状态(第 1 批源文件后)

更新:2026-06-16 · 本批到货 3/12 卷(08b 拉美后半 / 09 澳洲 / 10 美国+东盟+印度)

## 各体系源文件就绪度

| 体系 | 源到位 | 可拆深度(当前) | 阻塞 |
|---|---|---|---|
| C-NCAP(中国) | ❌ 未到 | — | 等卷 01/02/03 |
| JNCAP(日本) | ❌ 未到 | — | 等卷 06/07 |
| **ASEAN(东盟)** | ⚠ 仅行政件 | **L1/L2/L3 全阻塞** | **评分 xlsm + 侧碰/AEB 协议 PDF 缺失**(本批只有 Rating Plate/Logo/Label 等行政 Guideline,规格 §2.1 明确不进矩阵) |
| **Latin NCAP(拉美)** | ⚠ 仅自有协议 | L1/L2 可拆;L3 部分(AOP) | Euro 原始协议缺(影响交叉校验) |
| **ANCAP(澳洲)** | ✅ 齐 | **L1/L2 已跑通**(side_impact 回归 PASS);L3 协议内含评分表可补 | Euro AE-MDB v8.3 源缺(用于版本对齐) |
| **Euro NCAP(欧盟)** | ❌ 正文未到 + L3 源缺 | — | 等卷 04/05;且 §2.2 的 Euro 原始协议缺 |
| US NCAP(美国) | ✅ IIHS 齐 / ⚠ NHTSA 缺侧碰原文 | L1/L2 可拆;L3=DIFFERENT_SCORING_MODEL | NHTSA 原文/侧碰 缺(仅中文 .doc) |
| Bharat(印度) | ✅ AIS-197 齐 | 按章节可拆 | 无(单文件多项,需章节定位) |

## ⚠ 必须在下一批补的关键源(否则 L3 永久缺源)
1. `东盟/FINAL_ASEAN-NCAP-Spreadsheet-Version-0-New-Protocol-2026_2030.xlsm`(L3 黄金源)
   + 东盟测试协议 PDF(侧碰 v3.3、AEB-C2C、AEB-CM、LSS、BST/ARV/AHB)。
2. `拉美/Euro NCAP – *.pdf` 全套原始协议(AE-MDB Side v8.3、Oblique Pole v7.2、
   Pedestrian v8.5、Whiplash v3.3.1、AEB C2C/VRU、ODB、LSS、HV、Knee)——
   Euro / ANCAP / Latin 三体系的 L3 评分源。
3. (次要)`美国/NHTSA…/原文/侧碰/` 英文原文。

## 下一批预告(规格已列)
中国 C-NCAP(01/02/03)、日本 JNCAP(06/07)、欧盟 Euro NCAP(04/05a/05b)、拉美前半(08a)。

## 已验证可解析(文字层正常,可端到端提取)
ANCAP 全协议、Bharat AIS-197(182p)、US IIHS 侧碰(G/A/M/P)、Latin AOP(57p)。
`extract_ancap.py` 已对 sample.json 跑通 side_impact L1/L2 回归(4/4 PASS)。
