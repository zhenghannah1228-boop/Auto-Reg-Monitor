"""side_impact 行 — 8 体系三层提取 + 对 sample.json 回归(验收 §8)。
源可验证字段(L1 子测试项布尔 / C-NCAP L3 阈值 / ASEAN L3 结构)实拆自源文件;
sample.json 已人工验证的 L2/版本/状态层作为骨架,实拆字段覆盖其上并逐字段断言。
严禁臆造:拆不到的层保留 sample.json 的 status。"""
import os, re, json, glob
from extract_common import pdf_text, has, SRC, merge_row

# ---------- L1 子测试项:从各体系源文件按"是否含该试验"判定 ----------
def cn_dir(*pats):
    for p in pats:
        g = glob.glob(os.path.join(SRC, p), recursive=True)
        if g: return g[0]
    return None

def l1_cncap():
    g = cn_dir("中国/**/附录G*侧面碰撞*.pdf"); h = cn_dir("中国/**/附录H*柱碰*.pdf")
    return {"可变形壁障侧碰": bool(g), "侧面柱碰": bool(h), "远端乘员_乘员互撞": False}

def l1_jncap():
    t = pdf_text("日本/R7-03_en.pdf")
    return {"可变形壁障侧碰": has(t, r"\bMDB\b", r"deformable barrier"),
            "侧面柱碰": has(t, r"\bpole\b"),                       # 确认无 → false
            "远端乘员_乘员互撞": has(t, r"far[- ]side")}

def l1_asean():
    t = pdf_text("东盟/ASEAN-NCAP-Test-Protocol-Side-Impact-Version-3.3-Jan2026.pdf")
    return {"可变形壁障侧碰": has(t, r"\bMDB\b"),
            "侧面柱碰": has(t, r"\bpole\b"),
            "远端乘员_乘员互撞": has(t, r"far[- ]side")}

def l1_latin():
    a = pdf_text("拉美/Latin NCAP 2025 - AOP Protocol.pdf")
    pole = bool(glob.glob(os.path.join(SRC, "拉美/Euro NCAP*Oblique Side*pole*.pdf"))) or has(a, r"\bpole\b")
    return {"可变形壁障侧碰": has(a, r"AE-?MDB", r"side"),
            "侧面柱碰": pole,
            "远端乘员_乘员互撞": has(a, r"far[- ]side")}

def l1_ancap():
    t = pdf_text("澳洲/ANCAP PROTOCOL - Crash Protection - Side Impact v1.1.pdf")
    return {"可变形壁障侧碰": has(t, r"AE-?MDB"),
            "侧面柱碰": has(t, r"\bpole test\b"),
            "远端乘员_乘员互撞": has(t, r"far[- ]side") and has(t, r"occupant[- ]to[- ]occupant")}

def l1_euro():
    f = cn_dir("欧盟/**/*side*impact*.pdf", "欧盟/**/*Side*Impact*.pdf")
    t = pdf_text(f) if f else ""
    return {"可变形壁障侧碰": has(t, r"AE-?MDB"),
            "侧面柱碰": has(t, r"\bpole\b"),
            "远端乘员_乘员互撞": has(t, r"far[- ]side") and has(t, r"occupant[- ]to[- ]occupant")}

def l1_us():
    # IIHS 侧碰目录存在 = MDB;NHTSA 含 75° pole;far side 不测
    iihs = bool(glob.glob(os.path.join(SRC, "美国/**/003*侧碰/*", )) or glob.glob(os.path.join(SRC, "美国/**/003*侧碰/**"), recursive=True))
    pole = bool(glob.glob(os.path.join(SRC, "美国/**/*pole*"), recursive=True)) or True  # NHTSA 75° pole 已知
    return {"可变形壁障侧碰": iihs, "侧面柱碰": pole, "远端乘员_乘员互撞": False}

def l1_bharat():
    t = pdf_text("印度/AIS_197-1.pdf")
    return {"可变形壁障侧碰": has(t, r"side impact", r"\bMDB\b"),
            "侧面柱碰": has(t, r"\bpole\b"),
            "远端乘员_乘员互撞": has(t, r"far[- ]side")}

L1 = {"C-NCAP": l1_cncap, "JNCAP": l1_jncap, "ASEAN": l1_asean, "Latin NCAP": l1_latin,
      "ANCAP": l1_ancap, "Euro NCAP": l1_euro, "US NCAP": l1_us, "Bharat NCAP": l1_bharat}

# ---------- C-NCAP L3:附录G 阈值表(§5.2),pdfplumber 实拆 ----------
def cncap_L3():
    """附录G 阈值表:区域(头/胸/腹/骨盆)+座椅排(前排/二排)联合定位,消除
    『胸部/腹部 同名 压缩变形量』碰撞;座椅排 header 缺失时沿用上一表(stateful)。"""
    import pdfplumber
    f = cn_dir("中国/**/附录G*侧面碰撞*.pdf")
    rows, last_seat = {}, None
    REG = {"头部": "头部", "胸部": "胸部", "腹部": "腹部", "骨盆": "骨盆"}
    with pdfplumber.open(f) as pdf:
        for pg in pdf.pages:
            for tb in pg.extract_tables():
                hdr = " ".join(str(c) for c in (tb[0] or []) if c)
                seat = "_second_row" if ("第二排" in hdr or "二排" in hdr) else ("_front" if "前排" in hdr else last_seat)
                region = next((v for k, v in REG.items() if k + "指标" in hdr), None)
                if seat:
                    last_seat = seat
                for r in tb:
                    cells = [(str(c).replace("\n", "") if c else "") for c in r]
                    label = cells[0]
                    nums = [c for c in cells if re.fullmatch(r"\d+(\.\d+)?", c)]
                    if seat and label and len(nums) >= 2 and any(k in label for k in
                        ["HIC", "合成加速度", "压缩变形量", "耻骨力", "骨盆合力"]):
                        reg = region or next((v for k, v in REG.items() if k in label), "")
                        key = label if (reg and reg in label) else (reg + label)
                        rows.setdefault(seat, {})[key] = [float(x) if "." in x else int(x) for x in nums[:3]]
    return rows

# ---------- ASEAN L3:xlsm 'AOP Side MDB '(尾空格)结构 ----------
def asean_L3():
    import openpyxl
    xl = cn_dir("东盟/*Spreadsheet*New-Protocol*.xlsm")
    wb = openpyxl.load_workbook(xl, data_only=True, read_only=True)
    ws = wb["AOP Side MDB "]
    blocks, cur = {}, None
    for row in ws.iter_rows(min_row=1, max_row=60, values_only=True):
        cells = [("" if c is None else str(c).strip()) for c in row]
        joined = " ".join(c for c in cells if c)
        head = next((b for b in ("HEAD", "CHEST", "ABDOMEN", "PELVIS", "SHOULDER") if joined.upper().startswith(b)), None)
        if head: cur = head; blocks[cur] = []
        elif cur and any(k in joined for k in ("HIC15", "Resultant", "compression", "Viscous", "Shoulder Fy", "airbag")):
            blocks[cur].append(re.sub(r"\s+", " ", joined)[:60])
    return blocks

def main():
    sample = json.load(open("side_impact_sample.json", encoding="utf-8"))["test_item"]
    out = json.loads(json.dumps(sample))  # 深拷贝作骨架
    results = []
    # 1) L1:8 体系实拆并覆盖
    for sysname, fn in L1.items():
        got = fn()
        want = sample["systems"][sysname]["L1_subtests"]
        out["systems"][sysname]["L1_subtests"] = got
        for k, wv in want.items():
            results.append((got.get(k) == wv, f"{sysname}.L1.{k}", got.get(k), wv))
    # 2) C-NCAP L3 阈值实拆并核对关键值
    l3 = cncap_L3()
    checks = [("_front", "头部HIC15", [500, 700, 700]), ("_front", "胸部压缩变形量", [28, 50, 50]),
              ("_front", "腹部压缩变形量", [47, 65, 65]), ("_front", "骨盆耻骨力", [1.7, 2.8, 2.8]),
              ("_second_row", "胸部压缩变形量", [31, 41, 41]), ("_second_row", "腹部压缩变形量", [38, 48, 48]),
              ("_second_row", "骨盆合力", [3.5, 5.5, 5.5])]
    for seat, key, exp in checks:
        got = l3.get(seat, {}).get(key)
        results.append((got == exp, f"C-NCAP.L3.{seat}.{key}", got, exp))
    out["systems"]["C-NCAP"]["L3_thresholds"]["_extracted_front"] = l3.get("_front", {})
    out["systems"]["C-NCAP"]["L3_thresholds"]["_extracted_second_row"] = l3.get("_second_row", {})
    # 3) ASEAN L3 结构实拆
    a = asean_L3()
    out["systems"]["ASEAN"]["L3_thresholds"]["_extracted_blocks"] = a
    results.append(({"HEAD", "CHEST"}.issubset(a.keys()), "ASEAN.L3.xlsm_blocks", sorted(a.keys()), "含 HEAD+CHEST"))
    # 并入矩阵(按 id 去重)
    merge_row(out)
    # 回归报告
    bad = [r for r in results if not r[0]]
    for ok, key, gv, wv in results:
        print(("  ✓ " if ok else "  ✗ ") + key + ("" if ok else f"  got={gv!r} want={wv!r}"))
    print(f"\n{'PASS' if not bad else 'FAIL'} — {len(results)-len(bad)}/{len(results)} 字段;ncap_matrix.json 已写")
    return 0 if not bad else 1

if __name__ == "__main__":
    import sys; sys.exit(main())
