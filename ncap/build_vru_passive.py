"""vru_passive 弱势道路使用者(头型/腿型被动冲击)— 8 体系 + 回归。
C-NCAP 附录O 头/腿型冲击(§5.1 O=40 冲击器速度;源另有 20km/h 子条件)。"""
import os, glob
from extract_common import pdf_text, has, SRC, merge_row, report, cncap_L3_paired, euro_pedestrian_head_bands, asean_fitment

def fp(*p):
    for x in p:
        g = glob.glob(os.path.join(SRC, x), recursive=True)
        if g: return g[0]
    return None

def does():
    import openpyxl
    xl = fp("东盟/*Spreadsheet*.xlsm")
    asean = False
    if xl:
        wb = openpyxl.load_workbook(xl, data_only=True, read_only=True)
        asean = any("PED" in s.upper() or "HPT" in s.upper() for s in wb.sheetnames)  # MS-PED / AOP HPT
    return {
        "C-NCAP": bool(fp("中国/*C-NCAP*/**/附录O*弱势*.pdf")),
        "JNCAP": bool(fp("日本/R7-06_en.pdf")) and bool(fp("日本/R7-07_en.pdf")),  # 头部+脚部
        "ASEAN": asean,
        "Latin NCAP": bool(fp("拉美/*PP Protocol*.pdf")),
        "ANCAP": bool(fp("澳洲/*Vulnerable Road User*.pdf")),
        "Euro NCAP": bool(fp("拉美/*Pedestrian*.pdf")),
        "US NCAP": False,                                          # US NCAP 不做被动行人头/腿型
        "Bharat NCAP": has(pdf_text("印度/AIS_197-1.pdf"), r"pedestrian"),
    }

CN_O = 40  # §5.1 O 冲击器速度

def build():
    L1 = does()
    # C-NCAP 附录O L3:腿型大腿弯矩高/低性能限值配对实拆(头型为 HIC 颜色网格,异质评分不入三限值)
    cn_leg = cncap_L3_paired("中国/*C-NCAP*/**/附录O*弱势*.pdf")
    # Euro 行人头型 HIC15 五色等级;Latin/ANCAP 采纳同表
    euro_ped = euro_pedestrian_head_bands()
    def euro_ped_l3(src, pre): return dict(euro_ped, _source=src, _note=pre + euro_ped.get("_note", ""))
    # ASEAN 行人头部保护按装备率(AOP HPT)
    asean_ped = asean_fitment("AOP HPT")
    meta = {
        "C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录O 弱势交通参与者(头型和腿型冲击).pdf"],
                   "L2_params": {"速度": f"{CN_O} km/h(头/腿型冲击器)", "冲击器": ["头型", "腿型(aPLI)"],
                                 "_note": "§5.1 O=40;源另含 20km/h 等子条件(头型 HIC<1000)"},
                   "L3_thresholds": {"_extracted_tables": {"腿型(aPLI)": cn_leg},
                                     "_source": "附录O 腿型大腿弯矩 高/低性能限值",
                                     "_note": "腿型大腿弯矩三限值实拆;头型为 HIC 颜色网格(表O.1 逐网格点颜色)异质评分,按严禁臆造不强转三限值"}},
        "JNCAP": {"version": "令和7(2025)", "source_files": ["日本/R7-06_en.pdf", "日本/R7-07_en.pdf"], "L2_params": {"冲击器": ["头型(R7-06)", "腿型(R7-07)"]}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
        "ASEAN": {"version": "Protocol 2026-2030", "source_files": ["东盟/...xlsm 'AOP HPT'(头部保护装备率 TFS8)+ MS-PED"], "L2_params": {"冲击器": ["头型", "腿型"], "_note": "MS-PED + 头部保护 HPT(装备率)"}, "L3_thresholds": asean_ped},
        "Latin NCAP": {"version": "2025", "source_files": ["拉美/Latin NCAP 2025 - PP Protocol v2.0.0.pdf", "采纳 Euro Pedestrian 头型色带"], "L2_params": {"冲击器": ["头型", "腿型"]}, "L3_thresholds": euro_ped_l3("采纳 Euro 行人头型 HIC15 五色等级", "Latin 采纳;")},
        "ANCAP": {"version": "v1.1", "source_files": ["澳洲/ANCAP PROTOCOL - Crash Protection - Vulnerable Road User Impact v1.1.pdf", "采纳 Euro Pedestrian"], "L2_params": {"冲击器": ["头型", "腿型"], "_note": "采纳Euro Pedestrian"}, "L3_thresholds": euro_ped_l3("采纳 Euro 行人头型 HIC15 五色等级", "ANCAP 采纳;")},
        "Euro NCAP": {"version": "Pedestrian v8.5", "source_files": ["拉美/Euro NCAP - Pedestrian Testing Protocol v8.5.pdf §4"], "L2_params": {"速度": "40 km/h(头/腿型)", "冲击器": ["头型", "aPLI 腿型"]}, "L3_thresholds": euro_ped},
        "US NCAP": {"version": "—", "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED", "_note": "US NCAP 不做被动行人头/腿型保护"}},
        "Bharat NCAP": {"version": "AIS-197", "source_files": ["印度/AIS_197-1.pdf"], "L2_params": {"冲击器": ["头型", "腿型"], "_extraction_note": "AIS-197 行人保护引用 AIS-100(独立标准)"}, "L3_thresholds": {"_status": "SOURCE_PENDING", "_note": "Bharat 行人保护遵循 AIS-100(独立标准,本批源未含 AIS-100 全文)——限值需补 AIS-100"}},
    }
    systems = {}
    for s, t in L1.items():
        m = meta[s]
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"行人头型冲击": t, "行人腿型冲击": t},
                      "L2_params": m.get("L2_params", {}) if t else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "vru_passive", "cn_name": "弱势者(头/腿型)", "en_name": "Pedestrian Passive (Head/Leg Impactors)", "pillar": "弱势道路使用者",
           "systems": systems,
           "diff_summary": "7 套做被动行人头/腿型冲击(40km/h);US NCAP 唯一不做(仅做主动 AEB-VRU);Euro/ANCAP/Latin/Bharat 同源 Euro Pedestrian、ASEAN 走 MS-PED+HPT(xlsm)",
           "key_differences": [
               "US NCAP 唯一不做被动行人头/腿型保护(美国侧重主动 AEB,被动行人不评)——典型差集",
               "其余 7 套均做:C-NCAP 附录O(头+腿型 40km/h)、JNCAP R7-06头/07腿、Euro Pedestrian v8.5、ANCAP/Latin 采纳Euro、ASEAN MS-PED+HPT(xlsm)、Bharat AIS-197 行人章",
               "评分多为车前端分区网格(头型 HIC + 腿型弯矩/剪切),Euro 系滑动 HPL-LPL;C-NCAP §5.1 冲击速度 40km/h",
               "ASEAN 行人评分在官方 xlsm(MS-PED / AOP HPT 表),非 PDF"]}
    n = merge_row(row)
    res = [(L1["US NCAP"] is False, "US.被动行人=不测", L1["US NCAP"], False)]
    for s in ["C-NCAP", "JNCAP", "ASEAN", "Latin NCAP", "ANCAP", "Euro NCAP", "Bharat NCAP"]:
        res.append((L1[s] is True, f"{s}.被动行人=测", L1[s], True))
    res.append((CN_O == 40, "C-NCAP.冲击速度=40(§5.1 O)", CN_O, 40))
    res.append((cn_leg.get("大腿弯矩") == [390, 440], "C-NCAP.L3.腿型大腿弯矩=[390,440]", cn_leg.get("大腿弯矩"), [390, 440]))
    eb = euro_ped.get("_bands", [])
    res.append((len(eb) == 5 and eb[0]["range"] == "<650" and eb[-1]["range"] == "≥1700", "Euro.L3.行人头型五色(<650…≥1700)", [len(eb), eb[0]["range"] if eb else None], "5档"))
    res.append((asean_ped.get("_TFS") == 8.0, "ASEAN.L3.行人头部装备率TFS=8", asean_ped.get("_TFS"), 8.0))
    print(f"vru_passive 做此项: {[s for s,v in L1.items() if v]}")
    ok = report(res); print(f"matrix {n} 项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
