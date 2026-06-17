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
