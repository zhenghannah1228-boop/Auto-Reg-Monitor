# NCAP 跨体系测试项映射矩阵

8 套 NCAP 体系(C-NCAP/JNCAP/ASEAN/Latin/ANCAP/Euro/US/Bharat)× 16 测试项的三层映射:
**L1 测/不测 · L2 参数(速度/假人/壁障/场景)· L3 评分阈值**。核心价值=跨体系差集(key_differences)。

## 怎么看(两种入口)

1. **监控台第 14 标签「NCAP矩阵」**(推荐):打开监控台 `index.html` → 点顶部「14 NCAP矩阵」标签,
   内嵌全功能矩阵。点单元格展开 L2/L3,点测试项名看差集要点。
2. **独立页(ASCII 链接,可直接打开)**:
   `https://zhenghannah1228-boop.github.io/Auto-Reg-Monitor/ncap/ncap_matrix_view.html`
   > ⚠ 旧的中文名链接 `NCAP_融合视图模块.html` 在 GitHub Pages 上因非 ASCII 路径编码易 404,
   > 已改用 ASCII 名 `ncap_matrix_view.html` 作部署入口(内容同源)。
3. 离线:`NCAP_融合视图_自包含.html` 内嵌数据,双击用浏览器直接打开(无需 http)。

## 文件
```
ncap/
├── ncap_matrix.json            产出:16 测试项 × 8 体系三层数据(数据源,各 build 生成)
├── ncap_matrix_view.html       部署用查看器(ASCII 名,fetch ./ncap_matrix.json;监控台 iframe 内嵌此页)
├── NCAP_融合视图模块.html        查看器工作副本(与上同内容)
├── NCAP_融合视图_自包含.html     离线版(内嵌数据,file:// 可开)
├── extract_common.py           公共提取器(6 类评分模型 + 内存兜底 + 回归断言工具)
├── build_*.py                  16 个测试项各一,独立可跑;build_all.py 一键重建全矩阵
├── side_impact_sample.json     侧碰回归基准
├── coverage_report.md          ★交付说明:协议版本表 + 矩阵分布 + 已知边界两表
└── sources/                    8 体系源文件(.gitignore,不入库,体积大)
```

## 当前状态(2026-06,定版)

128 格:**测 33 / 测·部分 39 / 不测 48 / 异构 8 / 待补 0**。已实拆 **6 类评分模型**:
三限值(C-NCAP)/ 滑动 HPL-LPL(Euro·Bharat·Latin·ANCAP)/ Value+Points(ASEAN 碰撞 xlsm)/
5色等级(JNCAP 头部·Euro 行人)/ 装备率 fitment(ASEAN 主动安全)/ pass-fail 合规限值(Bharat 行人 AIS-100)。
`build_all.py` 串行重建 + RLIMIT_AS 内存兜底,16 项各带回归断言,16/16 PASS。

**采用的协议版本**与**剩余「测·部分」边界清单**见 `coverage_report.md`(顶部版本表 + 文末两张交付表)。

## 纪律
严禁臆造:缺源/缺层标 status;ASEAN L3 只从 xlsm 拆;Latin/ANCAP 采纳 Euro 并标版本;
C-NCAP 速度防脚注上标污染并与 §5.1 核对值零误差;JNCAP 取英文层 + 评价方法 2025;
US 异构;Bharat 按 AIS-197/AIS-100 章节拆。每测试项必有非空 key_differences,每 L3 必有回归锚点。
