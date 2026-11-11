---
name: wp29-kanban-update
description: WP.29 母子看板 Excel 更新指南。当用户要求更新、维护、修复 WP29 看板（母子看板、子看板、法规追踪看板）时使用此 skill，包括录入新届次事件、修正状态标注、格式修复、交付前清洗等。涉及 openpyxl 操作 WP29_母子看板 xlsx 文件时务必先加载本 skill。
---

# WP.29 母子看板更新指南

> 维护 `WP29_母子看板_重排v5.xlsx`（或后续版本）的操作规范。
> 涵盖子看板结构、格式常量、状态标注规则、openpyxl 陷阱与交付前检查清单。

---

## 一、工作簿结构

| Sheet | 用途 |
|---|---|
| `WP.29 提案追踪 · 母看板` | 母看板：按届次汇总待表决/通过提案 |
| `单法规追踪·子看板` | 子看板：逐法规追踪事件演替（主要编辑对象） |
| `表决通过提案` | 历届表决记录 |
| `ECE` / `说明` / `更新` | 参考与说明 |

---

## 二、子看板区块布局（严格三行制）

每个法规区块恰好占 **3 行**：

```
行 N   : 表头行   — A列=法规编号(如R13), B:J合并=法规描述+状态
行 N+1 : 数据行   — 事件按时间顺序从左到右排列
行 N+2 : 分隔行   — 全空，高度19.5
```

### 2.1 表头行（行 N）

- **A 列**：法规编号（`R13`、`GTR9`、`新规-XXX`、`决议`、`Y类被安`、`EV改装`、`PTI R2` 等）
- **B:J 合并单元格**：格式为 `法规名称　|　GR组　|　N 个会期 / M 次动作　|　最新：{状态}`
- 行高 = **37.5**

### 2.2 数据行（行 N+1）

事件按时间顺序水平排列：

| 列 | 用途 |
|---|---|
| C (col 3) | 第 1 个事件 |
| D (col 4) | ▶ 箭头 |
| E (col 5) | 第 2 个事件 |
| F (col 6) | ▶ 箭头 |
| G (col 7) | 第 3 个事件 |
| H (col 8) | ▶ 箭头 |
| I (col 9) | 第 4 个事件 |

- 同一会期的多个议题合并写入同一单元格（不拆行）
- 一个区块只有 **1 行** 数据行，事件超过 4 个时合并同会期条目
- 行高根据内容行数自动计算（见 §3.2）

### 2.3 分隔行（行 N+2）

- 所有列为空，无填充色，行高 = **19.5**

### 2.4 禁止的布局

- ❌ 事件出现在分隔行上（常见于 openpyxl 行删除后位移错乱）
- ❌ 同一区块占用多行数据行（应合并同会期条目到单元格内）
- ❌ 空单元格残留背景色（颜色溢出）

---

## 三、格式常量

### 3.1 事件单元格

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

evt_font  = Font(name='Noto Sans CJK SC', size=9, color='2B2B2B')
evt_fill  = PatternFill('solid', fgColor='FFFFF3E0')   # 浅橙
evt_align = Alignment(horizontal='left', vertical='top', wrap_text=True)
```

### 3.2 箭头单元格

```python
arrow_font  = Font(name='Arial', size=12, bold=True, color='5A6B82')
arrow_align = Alignment(horizontal='center', vertical='center')
no_fill     = PatternFill(fill_type=None)
```

### 3.3 通用边框

```python
thin_border = Border(
    left=Side(style='thin', color='D9DEE6'),
    right=Side(style='thin', color='D9DEE6'),
    top=Side(style='thin', color='D9DEE6'),
    bottom=Side(style='thin', color='D9DEE6'),
)
```

### 3.4 行高标准

| 行类型 | 内容行数 | 高度 |
|---|---|---|
| 表头行 | — | 37.5 |
| 数据行 | ≤2 行 | 37.5 |
| 数据行 | 3–4 行 | 52.5 |
| 数据行 | 5–6 行 | 82.5 |
| 数据行 | >6 行 | 105.0 |
| 分隔行 | — | 19.5 |

计算方法：取数据行所有事件单元格中 `'\n'` 数 + 1 的最大值。

---

## 四、事件文本格式

每个事件单元格的内容格式：

```
【{会期名}　{日期}】
• {系列/补充件描述}　[{状态}]
  〔{文件编号}，{提交方}〕
• {第二条目}　[{状态}]
```

### 4.1 会期名写法

- WP.29 全体会议：`199届`、`200届`
- GR 工作组：`GRVA 26`、`GRBP84`、`GRSG 132`、`GRSP79`、`GRPE95`、`GRE95`
- 非正式工作组：`IWG RD-ASEP`、`IWG DETA`
- 特别会议：`EDO-07`
- 日期用 `MM/DD` 或 `MM/DD–DD`

### 4.2 状态标记

| 标记 | 含义 |
|---|---|
| `[已通过 36/0/0]` | WP.29 表决通过（赞成/反对/弃权） |
| `[已通过]` | 通过（无票数细节） |
| `[在研·起草]` | GR 级别起草阶段 |
| `[在研·审议]` | GR 级别审议阶段 |
| `[待审]` | 已提交待审议 |
| `[未列入·待核]` | 未列入议程，状态待核实 |
| `[新规·已通过 38/0/1]` | 新法规表决通过 |

---

## 五、表头状态描述规则

表头 B 列末尾 `最新：{状态}` 的填写规则：

### 5.1 已通过（最新事件为 WP.29 表决通过）

```
最新采纳：{系列} {补充件}（{N}届 {日期} 通过）
```

示例：
- `最新采纳：05系列 补充件1（199届 06/24 通过）`
- `最新采纳：01系列 补充件14（199届 06/24 通过）`
- `最新采纳：新法规（199届 06/24 通过）`
- `最新采纳：GTR勘误（199届 06/24 通过）`

多项合并：`最新采纳：04系列补充件3+03系列补充件6（199届 06/24 通过）`

### 5.2 待表决（有文件进入下届 WP.29 议程）

```
最新：★{N}届待表决
```

**关键规则**：只有文件确认进入下届 WP.29 全体会议议程的，才标"待表决"。
已结束的届次不能标待表决——那应该是"最新采纳"。

复合状态：`最新：★200届待表决 + 2项在研·起草(...)`

### 5.3 GR 级别在研（最新活动为 GR 工作组）

```
最新：{GR会期}在研·{阶段}({简述})
```

示例：
- `最新：GRBP84在研·审议(01系列/SWIN)`
- `最新：GRSG132在研·起草(03系列修正案)`
- `最新：IWG在研·起草(04系列修正案)`

### 5.4 待核

```
最新：{N}届 {描述}（未列入·待核）
```

### 5.5 判定优先级

从数据行最右侧（最新）事件开始判断：

1. 最新事件为 GR/IWG 在研 → 用 §5.3 格式
2. 最新事件为 WP.29 已通过 → 用 §5.1 格式
3. 有文件进入下届 WP.29 → 用 §5.2 格式（含 ★ 标记）
4. 状态不明 → 用 §5.4 格式

---

## 六、openpyxl 关键陷阱

### 6.1 `delete_rows()` 不可靠移位

**问题**：`ws.delete_rows(n, count)` 删除行后：
- B:J 合并范围 **不会可靠跟随移位**，导致表头合并跑到数据行上，数据单元格变成 `MergedCell` 对象，内容被销毁
- `row_dimensions`（行高）**不会跟随移位**，表头获得数据行高度，数据行被压扁

**对策**：
- 尽量 **不删除行**，改为清空内容 + 设为分隔行
- 如必须删除，**从下往上处理**（bottom-to-top），避免上方操作影响下方行号
- 删除后必须 **全表扫描修复** 合并范围和行高

### 6.2 合并单元格清空

清空含合并单元格的行时，先检查 `isinstance(cell, MergedCell)`，只操作非合并单元格：

```python
for c in range(1, 11):
    cell = ws.cell(row=r, column=c)
    if not isinstance(cell, openpyxl.cell.cell.MergedCell):
        cell.value = None
```

### 6.3 清空 = 值 + 格式

清空单元格时必须同时清除值和填充色，否则产生"颜色溢出"：

```python
cell.value = None
cell.fill = PatternFill(fill_type=None)
cell.border = Border()
```

### 6.4 区块名称模式不统一

区块检测不能只匹配 `R`/`GTR`/`新规` 前缀。还有：`决议`、`Y类被安`、`EV改装`、`PTI R2` 等。
安全的检测方法：A 列和 B 列同时非空。

```python
blocks = []
for r in range(1, ws.max_row+1):
    a = ws.cell(row=r, column=1).value
    b = ws.cell(row=r, column=2).value
    if a and str(a).strip() and b and str(b).strip():
        blocks.append((r, str(a).strip()))
```

---

## 七、更新流程

### 7.1 添加新事件

1. 定位目标法规区块（按 A 列查找）
2. 在数据行找到最右侧已有事件的下一个空事件列（C→E→G→I）
3. 如果 4 列已满，将同会期条目合并到同一单元格
4. 写入事件文本（§4 格式），设置 `evt_font` / `evt_fill` / `evt_align` / `thin_border`
5. 前方加 ▶ 箭头（`arrow_font` / `arrow_align` / `no_fill` / `thin_border`）
6. 更新表头 B 列的"最新"状态描述（§5 规则）
7. 根据最长单元格行数更新数据行高度（§3.4）

### 7.2 批量状态更新（如新一届会议结束后）

典型场景：199 届结束 → 相关区块从"待表决"改为"最新采纳"。

1. 扫描所有表头含"待表决"但**不含**下届标记（如 ★200届）的区块
2. 从数据行解析最新事件的实际状态（已通过/在研/待核）
3. 按 §5 规则生成新的状态描述
4. 替换表头 B 列中 `最新[：:].*$` 部分

### 7.3 从 v4 或备份恢复数据

当数据行被损坏（合并范围覆盖、内容丢失）：

1. 读取备份文件中同名区块的事件数据
2. 移除 v5 数据行上的非法 B:J 合并范围
3. 确保表头行有正确的 B:J 合并范围
4. 按水平布局写入事件（C→▶→E→▶→G→▶→I）
5. 设置格式和行高

---

## 八、交付前检查清单

每次修改后、发给客户前，逐项检查：

### 8.1 布局完整性

```python
# 每个区块必须：表头 + 单行数据 + 分隔行
for block in blocks:
    assert 数据行有且仅有 1 行
    assert 数据行 C 列有内容
    assert 分隔行全空
    assert 分隔行无背景色
```

### 8.2 无颜色溢出

```python
# 所有空单元格的 fill 必须为 None
for cell in all_empty_cells:
    assert cell.fill.fgColor.rgb in ('00000000', None)
```

### 8.3 无内部工作备注

以下口吻的文字不适合给客户看，必须清除或改为中性措辞：

- `⚠此前记录误将...` / `经核对PDF原文确认...` / `已移出并各自归位`
- `△...` 开头的内部注释
- `笔误`、`占位号` 等纠错措辞
- 任何"此前"/"之前错误地"/"经核对发现"类反思性说明

**可保留**的客观事实说明（改用中性措辞）：
- ✅ `源文件标"补充件13"，因13已于199届通过，按序递补为14`
- ❌ `荷兰GRSG/2026/20草案的笔误/占位号，该13已于199届通过`

### 8.4 状态描述一致性

```python
# 所有"待表决"必须关联下一届标记
for block with '待表决' in header:
    assert '★{下届}届' in header

# 已结束届次不能标"待表决"
for block with latest_event from concluded_session:
    assert '待表决' not in header
```

### 8.5 行高标准化

```python
for block in blocks:
    assert header_height == 37.5
    assert separator_height == 19.5
    assert data_height in (37.5, 52.5, 82.5, 105.0)
```

---

## 九、完整验证脚本模板

```python
import openpyxl
from openpyxl.styles import PatternFill

wb = openpyxl.load_workbook('WP29_母子看板_重排v5.xlsx')
ws = wb['单法规追踪·子看板']

blocks = []
for r in range(1, ws.max_row+1):
    a = ws.cell(row=r, column=1).value
    b = ws.cell(row=r, column=2).value
    if a and str(a).strip() and b and str(b).strip():
        blocks.append((r, str(a).strip()))

errors = []
for i, (row, name) in enumerate(blocks):
    next_h = blocks[i+1][0] if i+1 < len(blocks) else ws.max_row+1

    # 表头行高
    if ws.row_dimensions[row].height != 37.5:
        errors.append(f'{name} row {row}: header height={ws.row_dimensions[row].height}')

    # 表头 B:J 合并
    has_merge = any(mg.min_row == row and mg.min_col == 2 and mg.max_col == 10
                    for mg in ws.merged_cells.ranges)
    if not has_merge:
        errors.append(f'{name} row {row}: missing B:J header merge')

    # 数据行检查
    data_rows = []
    for dr in range(row+1, next_h):
        has_data = any(
            ws.cell(row=dr, column=c).value and str(ws.cell(row=dr, column=c).value).strip()
            for c in [3,5,7,9]
            if not isinstance(ws.cell(row=dr, column=c), openpyxl.cell.cell.MergedCell)
        )
        if has_data:
            data_rows.append(dr)
            if ws.row_dimensions[dr].height == 19.5:
                errors.append(f'{name} row {dr}: data on separator row')

    if len(data_rows) == 0:
        errors.append(f'{name}: no data row')
    elif len(data_rows) > 1:
        errors.append(f'{name}: {len(data_rows)} data rows {data_rows}')

    # 空单元格颜色溢出
    for dr in range(row+1, next_h):
        for c in range(1, 11):
            cell = ws.cell(row=dr, column=c)
            if isinstance(cell, openpyxl.cell.cell.MergedCell):
                continue
            if not (cell.value and str(cell.value).strip()):
                fill = cell.fill
                if fill and fill.fgColor and fill.fgColor.rgb not in ('00000000', '0', None):
                    errors.append(f'{name} row {dr} col {c}: color bleed ({fill.fgColor.rgb})')
                    break  # 每区块只报一次

    # 内部备注检查
    for dr in range(row+1, next_h):
        for c in [3,5,7,9]:
            cell = ws.cell(row=dr, column=c)
            if isinstance(cell, openpyxl.cell.cell.MergedCell):
                continue
            v = str(cell.value or '')
            for kw in ['⚠此前', '经核对', '笔误', '△此前']:
                if kw in v:
                    errors.append(f'{name} row {dr} col {c}: internal note ({kw}...)')

    # 待表决一致性
    b_val = str(ws.cell(row=row, column=2).value or '')
    if '待表决' in b_val and '★' not in b_val:
        errors.append(f'{name}: "待表决" without ★ session marker')

if errors:
    print(f'{len(errors)} issues:')
    for e in errors:
        print(f'  {e}')
else:
    print('All checks passed!')

wb.close()
```

---

## 十、母看板与子看板联动

母看板（`WP.29 提案追踪 · 母看板`）按届次罗列待表决/已通过提案。
更新时注意：

- 新届次已结束 → 母看板中该届的"待表决"条目应标记结果
- 子看板中对应法规的"待表决"→"最新采纳"（§7.2 流程）
- 母看板去重：相同提案不应在多个届次重复出现
