"""lane_support 车道支持(LDW/LKA/ELK)— 7 体系做、Bharat 不测。
ELK(紧急车道保持)按源精确核对单列:C-NCAP/Euro/ANCAP/Latin/ASEAN 含,JNCAP/US 无。"""
import glob, os
from extract_common import SRC, merge_row, report
def has_f(*p):
    return any(glob.glob(os.path.join(SRC, x), recursive=True) for x in p)

def build():
    SCN = ["车道偏离警告LDW", "车道保持LKA", "紧急车道保持ELK"]
    DO = {"C-NCAP": "中国/*C-NCAP*/**/附录Q*.pdf", "JNCAP": "日本/R7-14_en.pdf", "ASEAN": "东盟/*Lane-Support*.pdf",
          "Latin NCAP": "拉美/*SA Protocol*.pdf", "ANCAP": "澳洲/*Lane Departure*.pdf", "Euro NCAP": "拉美/*LSS*.pdf",
          "US NCAP": "美国/**/LDW_LKS*.pdf"}
    ELK = {"C-NCAP": True, "JNCAP": False, "ASEAN": True, "Latin NCAP": True, "ANCAP": True, "Euro NCAP": True, "US NCAP": False}
    ELKNOTE = {"JNCAP": "R7-14 仅 LDW/LKA,无 ELK(ELK明示0)", "US NCAP": "NHTSA 2013 LDW_LKS 仅 LDW/LKS,无 ELK",
               "ASEAN": "含路沿/对向场景(×10),未单用ELK术语"}
    systems = {}
    for s in ["C-NCAP", "JNCAP", "ASEAN", "Latin NCAP", "ANCAP", "Euro NCAP", "US NCAP", "Bharat NCAP"]:
        t = has_f(DO[s]) if s in DO else False
        cov = {"车道偏离警告LDW": t, "车道保持LKA": t, "紧急车道保持ELK": (t and ELK.get(s, False))}
        systems[s] = {"version": "", "source_files": [DO.get(s, "")] if t else (["印度/AIS_197-1.pdf(无LSS)"] if s == "Bharat NCAP" else []),
            "L1_subtests": cov,
            "L2_params": ({"子项": [k for k, v in cov.items() if v], "_note": ELKNOTE.get(s, "")} if t else {}),
            "L3_thresholds": {"_status": "DIFFERENT_SCORING_MODEL" if s == "US NCAP" else ("NOT_TESTED" if not t else "TO_EXTRACT")}}
    row = {"id": "lane_support", "cn_name": "车道支持(LDW/LKA/ELK)", "en_name": "Lane Support (LDW/LKA/ELK)", "pillar": "主动安全·避撞", "systems": systems,
        "diff_summary": "7 套均 LDW+LKA(Bharat 不测);ELK 紧急车道保持(路沿/对向车/超车):C-NCAP/Euro/ANCAP/Latin/ASEAN 含,JNCAP(R7-14)与 US(NHTSA 2013)仅基础 LDW/LKA 无 ELK",
        "key_differences": [
            "LDW(偏离警告)+LKA/LKS(车道保持)为 7 套共有(Bharat AIS-197 无 LSS)",
            "ELK 紧急车道保持(路沿/对向来车/超车)是高阶差异:C-NCAP(附录Q×14)、Euro(LSS×22)、ANCAP(×81)、Latin(SA×16)、ASEAN(路沿对向×10)做;JNCAP R7-14 与 US(NHTSA 2013)仅基础 LDW/LKA、无 ELK",
            "『要不要单独做 ELK』是工程师真问题:冲 Euro/ANCAP 五星须含 ELK,JNCAP/US 不要求",
            "US 为 NHTSA 通过/星级(异构);中/欧/澳为速度区间分档"]}
    n = merge_row(row)
    res = [(systems[s]["L1_subtests"]["车道保持LKA"], f"{s}.车道支持=测", True, True) for s in ["C-NCAP", "JNCAP", "ASEAN", "Latin NCAP", "ANCAP", "Euro NCAP", "US NCAP"]]
    res += [(any(systems["Bharat NCAP"]["L1_subtests"].values()) is False, "Bharat.车道=不测", False, False),
            (systems["JNCAP"]["L1_subtests"]["紧急车道保持ELK"] is False and systems["Euro NCAP"]["L1_subtests"]["紧急车道保持ELK"] is True, "ELK:JNCAP无/Euro有", True, True),
            (systems["US NCAP"]["L1_subtests"]["紧急车道保持ELK"] is False, "US.ELK=无(2013基础)", False, False)]
    print("lane_support ELK:", {s: systems[s]["L1_subtests"]["紧急车道保持ELK"] for s in DO})
    ok = report(res); print("matrix", n); return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
