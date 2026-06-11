# 法规解读看板系统

把"推文解读"结构化进数据库，自动与你的法规库双向链接，并随每篇新推文持续丰富。

## 更新日志
- **v1.2**：① 新增「认证金字塔」能力——`decode_pyramid.py` 把 type=system 推文解码成
  4层金字塔(L1母法→L4证书)并 merge 进 `data/pyramids.json`(一国一塔)；
  `build_pyramid.py` 渲染成与监控台 09 tab 同款视图(`output/pyramid_view.html`)。
  已含印度/巴西(解码自推文)、马来西亚(范本)三塔。
  ② 编号识别扩到新兴市场：AIS/CMVR(印度)、KMVSS(韩)、TIS(泰)、SNI(印尼)、SASO/GSO(中东)。
- v1.1：新增 system 类型；匹配器支持系列号/修订号；CONTRAN/INMETRO/FMVSS 识别。
- v1.0：三类承载 + 双向链接 + 投喂脚本。

## 目录结构

```
kanban_system/
├── data/
│   └── insights.json          ← 解读数据库（唯一数据源，单一真相）
├── scripts/
│   ├── matcher.py             ← 核心匹配库（编号规范化 + 法规库索引 + 边界匹配）
│   ├── compile_tweet.py       ← 投喂脚本：新推文 → insights.json
│   ├── build_kanban.py        ← 生成看板 HTML + 反向链接清单
│   └── write_back_to_excel.py ← 把解读链接写回法规库 Excel 的「解读链接」列
├── inbox/                     ← 把新推文 PDF 丢这里待处理
└── output/
    ├── kanban.html            ← 可交互看板（三列：对比/文本/修订，可筛选搜索）
    ├── reverse_links.json     ← 法规编号 → 解读（机器可读）
    ├── reverse_links.csv      ← 同上，人工查看
    └── library_linked/        ← 写回了「解读链接」列的法规库副本
```

## 三类推文如何承载

`insights.json` 里每条解读有 `type` 字段：
- `compare`  两国/地区同主题对比（如 GB 15083 与 ECE R17，或 R79/R171/R157 三法规并列）
- `interpret` 单一法规文本解读（如 GB 48001 门把手、UN R64 应急轮胎）
- `revision` 单一法规修订新旧对比（如 UN R48.8、UN R100.04）
- `system`  认证体系/制度科普（如巴西 CONTRAN/UN R/FMVSS 体系区别）

看板按这四类分列展示。

## 关联机制（按法规编号精确匹配）

每条解读的 `regulations[].match_key` 是规范化后的编号（如 `UN R48`、`GB 15083`、`EU 2023/1542`）。
`matcher.py` 扫描 `/mnt/project` 下所有法规清单，把 match_key 匹配到具体的 (文件, sheet, 行号)。

- 匹配带**数字边界**：`UN R12` 不会误命中 `UN R121`。
- 一篇推文可挂多条法规（对比类天然涉及2+编号）。
- 因为多国清单共用 UN R 法规，一篇 UN R 解读会自动反向出现在所有引用它的国家文件里。

## 日常流程：收到新推文怎么办

### 输入是 PDF
```bash
cd kanban_system
python3 scripts/compile_tweet.py --pdf "inbox/推文——XXX.pdf"
# 或批量
python3 scripts/compile_tweet.py --dir inbox/
```

### 输入是纯文字 / 链接
```bash
# 从文件
python3 scripts/compile_tweet.py --text tweet.txt --source "推文——XXX"
# 或管道
echo "粘贴的推文正文…" | python3 scripts/compile_tweet.py --text - --source "推文——XXX"
```

compile_tweet 会自动：提取标题/日期/作者、识别法规编号、判定 type 与 10 维度、匹配法规库，
然后**追加**进 insights.json（按 source_file 去重，不会重复录入）。

> 自动解析的新条目带 `needs_review: true`，且 `topics`/`key_points`/`url` 留空。
> 这是「初稿」——你只需校对、补全要点和原文链接，再把 needs_review 改成 false。
> （如果把推文 PDF 连同这句话一起发给 Claude/code，可让它直接帮你填好这几个字段。）

### 重建看板与链接
```bash
python3 scripts/build_kanban.py          # 刷新 kanban.html 和 reverse_links
python3 scripts/write_back_to_excel.py   # 把链接写进法规库副本（output/library_linked/）
python3 scripts/write_back_to_excel.py --inplace  # 谨慎：直接改 /mnt/project 原文件
```

## insights.json 字段说明

| 字段 | 说明 |
|---|---|
| id | INS-年份-序号，自动生成 |
| title | 推文标题 |
| type | compare / interpret / revision |
| summary | 一句话摘要 |
| regulations[] | 关联法规：region/country/reg_no/match_key |
| topics[] | 主题标签（自由词） |
| dimensions[] | 10 维度编号（与项目维度框架一致） |
| key_points[] | 核心要点 |
| author / publish_date / region_focus | 元数据 |
| source_file | 来源文件名（去重键） |
| url | 推文原文链接（填了看板可点击跳转） |

## 给下一轮 code 的提示词模板

> "这是新推文 [PDF/正文]。请用 kanban_system/scripts/compile_tweet.py 编译进 insights.json，
> 然后帮我校对自动生成的字段（补全 topics、key_points、url，确认 type 和 dimensions），
> 最后重建看板和反向链接。"
