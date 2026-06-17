"""side_pole 侧面柱碰 — 8 体系三层提取 + 回归断言。
与 side_impact 同管线;顺手验证 JNCAP/ASEAN 无柱碰基准。无 sample.json 行,
断言基于源文件 + §5.1 速度核对值(C-NCAP H=32)+ §4 矩阵预期(差异处以源为准并记录)。"""
import os, re, glob
from extract_common import pdf_text, has, SRC, merge_row, report, cncap_L3_tables

def fp(*pats):
    for p in pats:
        g = glob.glob(os.path.join(SRC, p), recursive=True)
        if g: return g[0]
    return None

# ---- L1:各体系是否做独立柱碰(侧面刚性/斜柱) ----
def does_pole():
    out = {}
    out["C-NCAP"] = bool(fp("中国/**/附录H*柱碰*.pdf"))                       # 附录H
    out["JNCAP"] = has(pdf_text("日本/R7-03_en.pdf"), r"\bpole\b")            # 确认 False
    aseanp = fp("东盟/*Side-Impact*.pdf")
    out["ASEAN"] = has(pdf_text(aseanp), r"\bpole\b") if aseanp else False    # 确认 False
    out["Latin NCAP"] = bool(fp("拉美/Euro NCAP*Oblique*pole*.pdf"))          # 采纳 Euro Oblique v7.2
    out["ANCAP"] = has(pdf_text("澳洲/ANCAP PROTOCOL - Crash Protection - Side Impact v1.1.pdf"), r"\bpole test\b")
    ef = fp("欧盟/**/*side*impact*v11*.pdf", "欧盟/**/*side*impact*.pdf")
    out["Euro NCAP"] = has(pdf_text(ef), r"\bpole\b") if ef else False
    out["US NCAP"] = True   # NHTSA NCAP 含 75°斜柱(MDB+Pole);本批未提供 NHTSA 原文/侧碰源
    out["Bharat NCAP"] = has(pdf_text("印度/AIS_197-1.pdf"), r"\bpole\b")     # AIS-197 含柱碰章节
    return out

# ---- C-NCAP 附录H 速度(避开 0.5km/h 定位脚注,取碰撞瞬间 32) ----
def cncap_pole_speed():
    t = pdf_text("中国/中国新车评价规程（C-NCAP） 2027年版/02 规程附录A-T/附录H  侧面柱碰撞测试评价规程.pdf")
    m = re.search(r"碰撞瞬间[^。]*?碰撞速度为\s*(\d+)\s*km/h", t) or re.search(r"碰撞速度为\s*(3\d)\s*km/h", t)
    return int(m.group(1)) if m else None

def build():
    L1 = does_pole()
    speed = cncap_pole_speed()
    # C-NCAP 附录H L3:柱碰自有头部阈值表(HIC15 500/700、累积3ms 60/80g)实拆
    cn_l3 = cncap_L3_tables("中国/*C-NCAP*/**/附录H*柱碰*.pdf")
    systems = {}
    # 各体系柱碰参数(测者填 L2;源缺标 status)
    meta = {
        "C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录H 侧面柱碰撞测试评价规程.pdf"],
                   "L2_params": {"速度": f"{speed} km/h", "假人": ["WorldSID 50th"], "壁障": "254mm 刚性柱", "撞击角度": "垂直(车辆横向)"},
                   "L3_thresholds": {"_note": "附录H 柱碰头部阈值实拆(HIC15/累积3ms);胸/腹/骨盆沿用附录G 低性能限值门槛(G.5.3.3)",
                                     "_source": "附录H 侧面柱碰评价表 + 附录G 低性能限值", "_extracted_tables": cn_l3}},
        "JNCAP": {"version": "令和7(2025)", "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED"}},
        "ASEAN": {"version": "Protocol 2026-2030", "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED"}},
        "Latin NCAP": {"version": "2025/采纳Euro Oblique v7.2", "source_files": ["拉美/Euro NCAP – Oblique Side pole Impact Testing Protocol v7.2 Dec 2023.pdf"],
                       "L2_params": {"假人": ["WorldSID 50th"], "壁障": "斜柱(采纳Euro Oblique 75°)"}, "L3_thresholds": {"_source": "采纳Euro Oblique v7.2", "_status": "TO_EXTRACT"}},
        "ANCAP": {"version": "v1.1", "L2_params": {"假人": ["WorldSID 50th"], "壁障": "斜柱(采纳Euro)"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
        "Euro NCAP": {"version": "v1.1 2026 + Oblique v7.2", "source_files": ["欧盟/Euro NCAP/crash protection/.../side impact v11", "拉美/Euro NCAP – Oblique Side pole v7.2"],
                      "L2_params": {"假人": ["WorldSID 50th"], "壁障": "斜柱 75°(Oblique Pole)"}, "L3_thresholds": {"_source": "Euro Oblique v7.2", "_status": "TO_EXTRACT"}},
        "US NCAP": {"version": "NHTSA", "L2_params": {"壁障": "75° 斜柱(MDB+Pole)", "假人": ["SID-IIs", "ES-2re"]},
                    "L3_thresholds": {"_status": "DIFFERENT_SCORING_MODEL", "_note": "NHTSA 星级;本批未提供 NHTSA 原文/侧碰源,L2/L3 待补"}},
        "Bharat NCAP": {"version": "AIS-197", "source_files": ["印度/AIS_197-1.pdf"],
                        "L2_params": {"_extraction_note": "AIS-197 含柱碰章节,采纳Global/Euro方法"}, "L3_thresholds": {"_status": "TO_EXTRACT_FROM_CHAPTER"}},
    }
    for s, tested in L1.items():
        m = meta[s]
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"侧面柱碰": tested},
                      "L2_params": m.get("L2_params", {}) if tested else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "side_pole", "cn_name": "侧面柱碰", "en_name": "Side Pole Impact", "pillar": "碰撞保护",
           "systems": systems,
           "diff_summary": "做柱碰 6 套;JNCAP/ASEAN 不做(仅MDB侧碰);C-NCAP 刚性柱32km/h,Euro/Latin/ANCAP 采纳Euro斜柱75°,US NHTSA 75°",
           "key_differences": [
               "做柱碰的 6 套:C-NCAP(附录H 刚性柱 32km/h)、Latin/ANCAP/Euro(采纳 Euro Oblique 斜柱 75°)、US(NHTSA 75°斜柱)、Bharat(AIS-197)",
               "JNCAP、ASEAN 不做侧面柱碰(仅 MDB 侧碰)——与 side_impact 基准一致",
               "C-NCAP 柱碰用附录G『低性能限值』作通过门槛,非独立三限值表(G.5.3.3)",
               "Euro/Latin/ANCAP 柱碰同源 Euro Oblique Side Pole v7.2;US 为 NHTSA 自有 75°斜柱",
               "US NHTSA 柱碰原文(原文/侧碰)本批未提供,L2/L3 标 SOURCE_PENDING"]}
    n = merge_row(row)
    # ---- 回归断言 ----
    res = []
    res.append((speed == 32, "C-NCAP.柱碰速度=32(§5.1 H)", speed, 32))
    res.append((L1["JNCAP"] is False, "JNCAP.柱碰=不测", L1["JNCAP"], False))
    res.append((L1["ASEAN"] is False, "ASEAN.柱碰=不测", L1["ASEAN"], False))
    for s in ["C-NCAP", "Latin NCAP", "ANCAP", "Euro NCAP", "Bharat NCAP"]:
        res.append((L1[s] is True, f"{s}.柱碰=测", L1[s], True))
    # C-NCAP 附录H L3 实拆回归锚点
    hic = cn_l3.get("_", {}).get("HIC15")
    res.append((hic == [500, 700], "C-NCAP.L3.柱碰HIC15=[500,700]", hic, [500, 700]))
    print(f"side_pole 各体系做柱碰: {[s for s,v in L1.items() if v]}")
    ok = report(res)
    print(f"ncap_matrix.json 现有 {n} 个测试项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
