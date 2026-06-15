# 认证体系世界地图 · 设计交付包

05 标签页「认证体系地图」的可交付版本,供设计做 PPT。全部由
`node export/build_cert_map_export.js` 从 `data/cert_pyramid.json` +
`data/world_geo.json` 生成(与线上地图同一套分类与配色,改了数据重跑即可刷新)。

| 文件 | 用途 |
|---|---|
| `cert_map_clean.svg` | **纯地图矢量**(透明底,只有上色国家轮廓,无标题图例)。最灵活——拖进 PPT/Illustrator 可任意缩放、整体换品牌配色 |
| `cert_map_composed.svg` | **成稿矢量**(纸面底色 + 标题 + 图例),可直接当一页幻灯;矢量,字体用打开端的系统字 |
| `cert_map_composed.png` | 上图的 **2400×1350 高清位图**,中文已渲染,拿来即用/预览 |
| `cert_map_interactive.html` | **自包含交互页**(双击本地打开,无需联网)。可缩放、悬停看各国体系简介,右上角工具栏「保存为图片」导出 3× 高清 PNG |
| `cert_map_colors.csv` | **配色对照表**:国家 / 地图要素英文名 / 体系类别 / 标准体系 / HEX / 数据来源,设计据此换色 |

## 配色(同一标准体系同色)

自有完整型式批准按标准体系细分:EU-WVTA `#2f6d8c` · 美标 FMVSS `#2e7d32` ·
加标 CMVSS `#7cb342` · 韩标 KMVSS `#00897b` · 澳标 ADR `#ef8c2f` ·
日本保安基準 `#4db6ac` · 中国 GB/CCC `#c0392b` · 印度 CMVR/AIS `#d81b60` ·
欧亚 TR CU/EAEU `#3f51b5` · 自有(UN-R/欧盟调和) `#7d8aa0`。
其他:混合型 `#9575cd` · 采信外部型 `#c79a2e` · 暂无数据 `#efece1`。

## 注意

- 中国台湾/香港在该底图并入中国(无独立轮廓);UNECE/GSO/东盟等组织条目不单独着色;
  欧盟成员按 EU-WVTA 统一着色。
- 矢量 SVG 内中文用通用字体族(`sans-serif`/`serif`),在装有中文字体的设计机上正常显示;
  若导出端缺中文字体,用 `cert_map_composed.png` 或在 AI 里指定字体。
