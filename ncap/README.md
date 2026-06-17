# NCAP 跨体系测试项映射矩阵 — 数据提取工作区

按交接规格 v2 实施。本目录是独立交付物(NCAP 测试项 × 8 体系三层映射矩阵),
仅通过 `un_r_refs` 与主项目法规库桥接,不与监控台业务混用。

## 目录
```
ncap/
├── side_impact_sample.json   人工验证的侧碰样板(回归基准,schema 2.0)
├── 源文件分卷说明.md          12 卷分卷清单(业主提供)
├── sources/                  解压后的 8 体系源文件(.gitignore,不入库,体积大)
├── extract_*.py              各体系提取脚本(待源文件到齐)
├── ncap_matrix.json          产出:全测试项 × 8 体系三层数据(待生成)
└── coverage_report.md        覆盖状态:各单元格 L3/仅L2/缺源
```

## 当前进度(第 1 批源文件,2026-06-16)

本批到货 3 卷(08b 拉美后半 / 09 澳洲 / 10 美国+东盟+印度)+ sample.json + 分卷说明。
**已验证可解析**:澳洲 ANCAP、印度 AIS-197、美国 IIHS、拉美 Latin 自有协议(文字层正常)。

### ⚠ 阻塞项(已向业主回报,待补)
1. **东盟 ASEAN xlsm 缺失** —— 本批 `东盟/` 只到 8 份行政 Guideline(评级牌/标签/Logo/进口
   程序等,规格 §2.1 明确"不进矩阵"),**官方评分 `*.xlsm`(L3 黄金源)与侧碰/AEB 等测试
   协议 PDF(L2)均不在内**。ASEAN 的 L2/L3 暂无法提取。
2. **拉美 Euro 原始协议缺失** —— `拉美/` 只有 Latin 自有协议(AOP/SA/PP/CSSTR/Overall/
   Moose/FWT),规格 §2.2 说本卷应含的 "Euro NCAP – AE-MDB Side Impact v8.3 / Oblique
   Pole v7.2 / Pedestrian v8.5 / Whiplash v3.3.1 / …" **一份都没有**。这批是 Euro/ANCAP/
   Latin 的 L3 评分源,缺它则三者 L3 无源。
3. **美国 NHTSA 原文/侧碰缺失** —— `NHTSA…/原文/` 只有 先进技术 + 翻滚;侧碰仅有中文 .doc。
   (US 为 DIFFERENT_SCORING_MODEL,影响较小;IIHS 侧碰资料齐全。)

### 待下一批(规格预告的剩余 9 卷)
中国 C-NCAP(01/02/03)、日本 JNCAP(06/07)、欧盟 Euro NCAP(04/05a/05b)、拉美前半(08a)。

## 纪律(防 v1 覆辙)
严禁臆造:缺源/缺层标 status;ASEAN L3 只从 xlsm 拆;拉美 Euro 协议反哺 Euro/ANCAP 且
标版本(2017–2023 旧版 vs 欧盟目录 2025/2026 新版,不混填);C-NCAP 速度防脚注上标污染并与
核对值零误差;JNCAP 取英文层;US 异构;Bharat 按 AIS-197 章节拆。每测试项必有非空 key_differences。
