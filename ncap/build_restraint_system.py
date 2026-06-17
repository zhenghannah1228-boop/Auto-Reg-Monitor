"""restraint_system 乘员约束系统 — C-NCAP附录M / Latin CSSTR;余不在碰撞保护内单列。"""
import os, glob
from extract_common import SRC, merge_row, report
def has_f(*p):
    for x in p:
        if glob.glob(os.path.join(SRC, x), recursive=True): return True
    return False
def build():
    L1 = {"C-NCAP": has_f("中国/*C-NCAP*/**/附录M*约束*.pdf"), "Latin NCAP": has_f("拉美/*CSSTR*.pdf"),
          "JNCAP": False, "ASEAN": False, "ANCAP": False, "Euro NCAP": False, "US NCAP": False, "Bharat NCAP": False}
    meta = {"C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录M 乘员约束系统性能.pdf"],
                "L2_params": {"_note": "安全带/限力/预紧/气囊匹配;台车法"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
            "Latin NCAP": {"version": "2025", "source_files": ["拉美/Latin NCAP 2025 - CSSTR Protocol.pdf"], "L2_params": {"_note": "儿童约束系统(CSSTR)台车"}, "L3_thresholds": {"_status": "TO_EXTRACT"}}}
    systems = {}
    for s, t in L1.items():
        m = meta.get(s, {})
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"乘员约束系统": t}, "L2_params": m.get("L2_params", {}) if t else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "restraint_system", "cn_name": "乘员约束系统", "en_name": "Restraint System", "pillar": "碰撞保护",
           "systems": systems,
           "diff_summary": "仅 C-NCAP(附录M 乘员约束)与 Latin(CSSTR 儿童约束)单列约束系统台车项;其余体系把约束性能并入各碰撞工况评价,不单列",
           "key_differences": ["仅 C-NCAP 附录M(乘员约束系统:安全带/限力/预紧/气囊匹配)与 Latin CSSTR(儿童约束系统)设独立约束台车项",
               "其余 6 套(JNCAP/ASEAN/ANCAP/Euro/US/Bharat)不单列约束系统,约束性能体现在正/侧碰假人伤害结果中",
               "属差集型条目:跨体系冲星时,约束系统单列与否影响测试规划口径"]}
    n = merge_row(row)
    res = [(L1["C-NCAP"], "C-NCAP.约束=测", L1["C-NCAP"], True), (L1["Latin NCAP"], "Latin.CSSTR=测", L1["Latin NCAP"], True),
           (L1["Euro NCAP"] is False, "Euro.约束单列=不测", L1["Euro NCAP"], False)]
    print("restraint:", [s for s,v in L1.items() if v]); ok = report(res); print("matrix", n, "项"); return 0 if ok else 1
if __name__ == "__main__":
    import sys; sys.exit(build())
