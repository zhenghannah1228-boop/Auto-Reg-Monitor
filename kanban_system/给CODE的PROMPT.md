# 给 Code 的标准 Prompt（投喂新推文用）

每次收到新推文，把下面对应版本的 prompt 连同推文一起发给 Claude/code 即可。
系统已在 `/mnt/project` 项目里（或你上传的 `kanban_system/` 里），脚本会自动处理大部分工作。

---

## 版本 A：发 PDF 推文时

> 这是 N 篇新的法规解读推文 PDF。请用 kanban_system 把它们编译进看板，流程如下：
>
> 1. 用 `scripts/compile_tweet.py --dir <推文目录>`（或逐个 `--pdf`）把它们追加进 `data/insights.json`，自动提取元数据、判类型、分维度、匹配法规库。
> 2. **逐篇人工精修**自动生成的初稿（这步很关键，别跳过）：
>    - 核对 `type` 四选一：compare(对比) / interpret(文本解读) / revision(修订) / system(体系科普)。判错的改正。
>    - 核对 `regulations`：法规编号是否抓全、抓对；带系列号的（如 UN R100.04）reg_no 保留完整版本、match_key 用基础号。
>    - 核对 `dimensions`：10 维度编号是否贴切（1整车准入/2环保/3射频/4电池/5补贴/6网安/7ADAS/8标签/9注册监管/10随车工具）。
>    - **补全 `summary`（一句话）、`topics`（3-5个标签）、`key_points`（2-4条核心要点，用我推文里的实际数据/限值/日期，不要泛泛）。**
>    - 有原文链接就填 `url`；填完把 `needs_review` 改成 `false`。
> 3. 跑 `scripts/build_kanban.py(随后跑 scripts/build_knowledge.py 重建知识体系视图 output/knowledge.html)` 重建看板和反向链接，再跑 `scripts/write_back_to_excel.py` 把"解读链接"列写回法规库副本。
> 4. 给我一句话小结：新增几篇、各什么类型、命中法规库几条、有哪些编号是法规库里还没有的（待补充）。

---

## 版本 B：发文字/链接时

> 这是 N 篇新推文的正文（或链接）。请用 kanban_system 编译进看板：
>
> 1. 把每篇正文存成 txt，用 `scripts/compile_tweet.py --text <文件> --source "<推文标题>"` 追加进 `data/insights.json`。（如果只给了链接，先抓取正文。）
> 2. 之后步骤同版本 A 的第 2~4 步：精修 type/regulations/dimensions、补全 summary/topics/key_points/url、置 needs_review=false、重建看板、写回 Excel、给小结。

---

## 质量标准（精修要达到的水平，参照已入库的优质条目）

`key_points` 是重点，好的要点长这样（含具体数值/日期/条款）：
- ✅ "UN R157速度上限从初版60km/h提至修订版130km/h；接管请求发出后驾驶员10秒内未响应则强制启动MRM。"
- ❌ "UN R157对自动驾驶提出了要求。"（太泛，没信息量）

`type` 判定口诀：
- 标题/正文出现两个及以上不同体系编号 + "对比/比较/差异/对比学习" → **compare**
- 讲"认证体系/层级/机构/编号区别/一文看懂/入门" → **system**
- 讲"修订/升级/新增/变化点/新旧/修订版" → **revision**
- 其余单一法规逐条解读 → **interpret**

## 体系科普类(type=system) → 直接编进「09 认证金字塔」(业主指示,2026-06 起)

如果这篇推文 type 被判为 `system`(讲某国认证体系/机构层级/编号区别),**不再生成独立的
pyramid_view,而是把推文信息直接 merge 进 09 标签页的数据源 `data/cert_pyramid.json`**:

1. **国家已有条目** → 丰富/校对(LLM 的活):
   - 把推文增量写进对应层的 `desc`/`refs`(新法规编号补进 refs,带名称);
   - 与推文冲突或更精确的口径,追加到 `external_recognition.note`,统一用
     **【推文校对】/【推文校丰】** 前缀标注来源性质;
   - 新机构补进 `sections.authorities`;`sources` 追加 `推文INS-XXX`。
2. **国家没有条目** → 新建标准四层(L1 母法→L2 技术基准→L3 审查/测试→L4 证书),
   `confidence` 按推文信息量定(通常 C,note 注明"基于推文的框架性描述,待官方资料核实")。
3. 改完用 jsdom/浏览器抽查该国渲染(层数/徽标/无 undefined),数据即视图,无需重建脚本。
4. `decode_pyramid.py`/`build_pyramid.py` 与 `data/pyramids.json` 已弃用为中间草稿工具,
   不再对外展示(pyramid_view.html 已从站点移除)。

## 常见需要人工兜底的情况
- **新法规体系编号**：compile_tweet 已内置 UN R/GB/EU/FMVSS/ADR/CONTRAN/INMETRO/AIS/CMVR/KMVSS/TIS/SNI/SASO/GSO 识别。遇到再没覆盖的(如某国独有标识)，手动补进 `regulations`，并在 `matcher.py`/`compile_tweet.py` 的 `REG_PATTERNS` 加一条。
- **图片为主、文字极少的推文**：自动摘要会很弱，务必人工补 summary 和 key_points。
- **GB 国标命中 0**：正常，因为法规库暂无中国清单文件；一旦你加入中国清单，重跑 write_back 会自动挂上，无需改代码。
