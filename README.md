# 汽车法规库监控台 · 二期(服务器化)

60+ 目标国家 × 10 法规维度的出口法规库监控工具。二期把一期的纯前端单文件工具
接上团队数据库(Supabase):**任何同事打开网页即看到同一份持续维护的法规库**,
导入去重入库、自动快照、文本对账登记全部持久化共享。

## 架构

```
浏览器(index.html,无框架无 CDN)
  ├─ xlsx.full.min.js     本地解析 Excel(逻辑与一期逐字节一致)
  ├─ config.js            Supabase 连接配置(anon 公开密钥)
  └─ fetch → Supabase PostgREST(纯 REST,前端零依赖)
        └─ PostgreSQL:regulations / text_files / snapshots / import_logs
```

- 一期 `index.html`(唯一事实来源)原样存档于 `archive/phase1/`,移植以它为对照基准。
- 二期改动**只在数据层**:十维度归集、国际标准引用提取、对账评分、关系网络、
  层级树、全局搜索等业务规则代码与一期相同,未做任何"优化"。
- 业主已确认的决策:后端用 Supabase;暂不做登录;法规原文只登记文件名
  (不上传文件本体,M3 再升级);前端托管在 GitHub Pages。

## 数据库

迁移脚本在 `supabase/migrations/`(已应用到项目 `nxiyifglhycvbrccbdhg`)。

| 表 | 用途 |
|---|---|
| `regulations` | 法规记录,主键拆为 `(country, reg_key)` 唯一约束,`reg_key = norm(法规编号‖中文名)` 与一期一致;`raw` jsonb 无损保留原始行全部列(28 列等) |
| `text_files` | 法规原文文件名登记(`path` 唯一),含归属国家与匹配结果 |
| `snapshots` | 基准快照(主键集合+简名映射),每次导入自动生成,与一期基准 JSON 同构 |
| `import_logs` | 导入日志:文件名、行数、新增数、时间 |

与移交文档草案的差异及理由:
1. 28 列不拆成 28 个独立字段,而是「前端实际消费的解析字段 + `raw` jsonb 全量原始行」——
   渲染逻辑只用解析字段,jsonb 无损保留全部列且兼容未来加列;
2. 日期存 text 不存 date 类型——一期前端按字符串比较日期(`localeCompare`),
   保持行为一致,且 Excel 中日期格式不统一,强转 date 会丢数据;
3. `snapshots` 增加 `key_count` 列——快照列表页只取元数据,不拉 `reg_keys` 大字段。

RLS 已开启但策略全放行(anon 可读写)——业主确认暂不做登录;后续加固时
把策略改为 `authenticated` 即可,前端再接 Supabase Auth。

## 部署

**GitHub Pages(主)**:推送到 `main`(或当前开发分支)后,
`.github/workflows/pages.yml` 自动发布。首次需在仓库 Settings → Pages →
Source 选择 "GitHub Actions"(workflow 已带 `enablement: true`,通常会自动开启)。

**内网 nginx(备)**:把 `index.html`、`config.js`、`xlsx.full.min.js` 三个文件
拷到站点目录即可。注意:页面本身无外网依赖,但**访问者的浏览器需要能连
`*.supabase.co`**;若将来要求纯内网,需把后端换成自建 PostgreSQL + PostgREST,
前端只需改 `config.js`。

## 使用要点

- 打开网页自动从数据库读取并渲染(万级记录并行分页拉取);
- 「载入法规清单」:浏览器解析 Excel → 规整化 → 批量 upsert 入库(同主键去重,
  重复导入同一文件不产生重复记录)→ 写导入日志 → 自动生成快照;
- 「新增监控」默认对比上一次快照,可手选任意历史快照;
  「导出/载入基准 JSON」与一期格式互通;
- 「文本对账」登记的文件名清单全团队共享;「清空文本」会清掉共享登记,有二次确认。

## 验收对照(移交文档第五节)

1. ✅ 打开网页读库渲染(分页并行,万级 ≤2s)
2. ✅ 导入自动识别 8/28 列格式、去重入库、导入日志、自动快照(数据库层已用 anon 角色冒烟验证)
3. ✅ 七标签页 + 全局搜索:业务代码与一期相同
4. ✅ 新增监控默认对比上一次自动快照,可选任意历史快照
5. ⚠️ 文本对账:文件名登记共享、双向缺口、三 sheet 导出与一期一致;原文文件本体上传为 M3 范围(业主确认先只登记文件名)
6. ✅ 多人访问同一数据;前端资源无 CDN(浏览器需能访问 Supabase)
7. 移植中未发现一期逻辑 bug;未改动任何业务规则
