"""NCAP 提取公共工具:源路径、文字层读取、sample.json 回归断言。
严禁臆造:提取不到的层标 status,不编数值。"""
import os, re, json, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")

def pdf_text(rel, pages=None):
    import pdfplumber
    p = rel if os.path.isabs(rel) else os.path.join(SRC, rel)
    with pdfplumber.open(p) as pdf:
        ps = pdf.pages if pages is None else pdf.pages[pages[0]:pages[1]]
        return "\n".join((pg.extract_text() or "") for pg in ps)

def has(txt, *pats):
    """文字层是否含任一正则(大小写不敏感),用于 L1 子测试项布尔判定。"""
    return any(re.search(p, txt, re.I) for p in pats)

def load_sample():
    with open(os.path.join(HERE, "side_impact_sample.json"), encoding="utf-8") as f:
        return json.load(f)["test_item"]

def assert_eq(system, got, want, results):
    """逐字段比对(L1 布尔/L2 标量),记录到 results。"""
    for k, wv in want.items():
        gv = got.get(k)
        ok = gv == wv
        results.append((ok, f"{system}.{k}", gv, wv))

def report(results):
    bad = [r for r in results if not r[0]]
    for ok, key, gv, wv in results:
        print(("  ✓ " if ok else "  ✗ ") + key + ("" if ok else f"  got={gv!r} want={wv!r}"))
    print(f"\n{'PASS' if not bad else 'FAIL'} — {len(results)-len(bad)}/{len(results)} 字段匹配")
    return not bad


def _src_glob(gl):
    import glob
    g = glob.glob(os.path.join(SRC, gl), recursive=True)
    return g[0] if g else None

def num1(s):
    """从单元格取唯一干净数值;多 token / 公式(×≥≤△括号) / 空 → None(拒绝臆造garbled)。"""
    s = str(s or "").replace("\n", "")
    if any(x in s for x in ["×", "≥", "≤", "△", "(", ")", "（", "）"]):
        return None
    raw = re.findall(r"-?\d+(?:\.\d+)?", s)      # 带空格判定是否多 token(PDF 串列污染)
    if len(raw) != 1:
        return None
    v = raw[0]
    return float(v) if "." in v else int(v)

def cncap_L3_tables(gl):
    """C-NCAP 表模式 L3:抽『高性能限值/低性能限值』阈值表 → {组:{指标:[高,低]}}。
    附录 G/H/J 等结构表适用;garbled/公式单元格由 num1 拒绝(严禁臆造)。"""
    import pdfplumber
    f = _src_glob(gl)
    if not f:
        return {}
    out = {}
    with pdfplumber.open(f) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables():
                hdr = [str(c or "").replace("\n", "") for c in (tb[0] or [])]
                if "高性能限值" not in " ".join(hdr):
                    continue
                hi = next((i for i, c in enumerate(hdr) if "高性能" in c), None)
                lo = next((i for i, c in enumerate(hdr) if "低性能" in c), None)
                if hi is None:
                    continue
                has_grp = hi >= 2     # 有独立分组列(col0=组,如附录J 驾驶员/二排座椅);否则 col0 即指标
                grp = "_"
                for r in tb[1:]:
                    cells = [str(c or "").replace("\n", "") for c in r]
                    if has_grp and cells and cells[0].strip() and not re.fullmatch(r"[\d.\s]+", cells[0]):
                        grp = cells[0].strip()
                    lab = ""
                    lo_i = 1 if has_grp else 0    # 有组列时,指标从 col1 起找
                    for i in range(lo_i, min(hi, len(cells))):
                        c = cells[i].strip()
                        if c and not re.fullmatch(r"[\d.\s]+", c):
                            lab = c
                    hv = num1(cells[hi]) if hi < len(cells) else None
                    lv = num1(cells[lo]) if lo is not None and lo < len(cells) else None
                    if lab and hv is not None:
                        out.setdefault(grp, {})[lab] = [hv, lv]
    return out

def cncap_L3_text(gl, captions):
    """C-NCAP 文本模式 L3:阈值以文本行渲染(附录A/B 头部表等)。给定『表X.n』标题,
    抓其后到下一『表』之间、形如『指标 高 低 极限』的单值行(num1 拒绝多列 garbled)。"""
    import pdfplumber
    f = _src_glob(gl)
    if not f:
        return {}
    with pdfplumber.open(f) as pdf:
        txt = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    lines = [l.strip() for l in txt.split("\n")]
    out = {}
    NUM = r"-?\d+(?:\.\d+)?"
    # 单值列阈值行: 指标名 (/)? 高 低 极限?  —— 三段均单一数字才采纳;指标名须含已知关键词
    KW = ("HIC", "加速度", "Fx", "Fz", "My", "压缩", "粘性", "VC", "NIC",
          "压力", "指数", "位移", "弯矩", "剪切", "张力", "合力", "耻骨", "TI", "力")
    pat = re.compile(r"^(.+?)\s+(?:/\s+)?(" + NUM + r")\s+(" + NUM + r")(?:\s+(" + NUM + r"))?\s*$")
    for cap in captions:
        try:
            start = next(i for i, l in enumerate(lines) if cap in l)
        except StopIteration:
            continue
        block = {}
        for l in lines[start + 1:start + 14]:
            if l.startswith("表") and cap not in l:
                break
            m = pat.match(l)
            if not m:
                continue
            label = m.group(1).strip()
            if not any(k in label for k in KW):
                continue
            g = m.groups()
            vals = [float(x) if (x and "." in x) else (int(x) if x else None) for x in g[1:]]
            block[label] = [v for v in vals if v is not None]
        if block:
            out[cap] = block
    return out


def cncap_L3_paired(gl):
    """C-NCAP 配对模式 L3:阈值以『高性能限值:指标 值 / 低性能限值:指标 值』两行分列
    (附录O 腿型大腿弯矩等)→ {指标:[高,低]}。仅采纳高/低同指标配对者。"""
    import pdfplumber
    f = _src_glob(gl)
    if not f:
        return {}
    with pdfplumber.open(f) as pdf:
        txt = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    NUM = r"(\d+(?:\.\d+)?)"
    hp = dict(re.findall(r"高性能限值[:：]\s*([一-龥A-Za-z/]+?)\s*" + NUM, txt))
    lp = dict(re.findall(r"低性能限值[:：]\s*([一-龥A-Za-z/]+?)\s*" + NUM, txt))
    out = {}
    for k in hp:
        if k in lp:
            hv = float(hp[k]) if "." in hp[k] else int(hp[k])
            lv = float(lp[k]) if "." in lp[k] else int(lp[k])
            out[k] = [hv, lv]
    return out


def merge_row(row):
    """把一个测试项行并入 ncap_matrix.json(按 id 去重替换),数组形式。"""
    import json
    p = os.path.join(HERE, "ncap_matrix.json")
    arr = []
    if os.path.exists(p):
        arr = json.load(open(p, encoding="utf-8"))
    arr = [x for x in arr if x.get("id") != row.get("id")] + [row]
    # 固定顺序:碰撞保护族在前,稳定输出
    order = ["frontal_rigid_full", "frontal_mpdb_offset", "frontal_small_overlap",
             "side_impact", "side_pole", "whiplash_rear", "post_crash_safety",
             "ev_hazard", "restraint_system", "vru_passive",
             "adas_aeb", "vru_active", "lane_support", "blind_spot",
             "adaptive_highbeam", "occupant_monitoring"]
    arr.sort(key=lambda x: order.index(x["id"]) if x["id"] in order else 99)
    json.dump(arr, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(arr)
