"""ev_hazard 新能源危险工况 — C-NCAP 附录L(§5.1 L=32) + Euro HV;余不测。"""
import os, glob
from extract_common import SRC, merge_row, report
def has_f(*p):
    for x in p:
        if glob.glob(os.path.join(SRC, x), recursive=True): return True
    return False
def build():
    L1 = {"C-NCAP": has_f("中国/*C-NCAP*/**/附录L*新能源*.pdf"), "Euro NCAP": has_f("拉美/*High Voltage*.pdf"),
          "JNCAP": False, "ASEAN": False, "Latin NCAP": False, "ANCAP": False, "US NCAP": False, "Bharat NCAP": False}
    meta = {"C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录L 新能源汽车危险工况.pdf"],
                "L2_params": {"速度": "32 km/h(§5.1 L)", "_note": "新能源危险工况:碰撞后高压电安全/热事件等"},
                "L3_thresholds": {"_status": "TO_EXTRACT", "_note": "高压绝缘/电解液泄漏/热失控等判定"}},
            "Euro NCAP": {"version": "HV v1.1 2022", "source_files": ["拉美/Euro NCAP - Testing of High Voltage Electric Vehicles V1.1.pdf"],
                "L2_params": {"_note": "高压电动车碰撞后电安全(绝缘电阻/隔离/泄漏)"}, "L3_thresholds": {"_status": "TO_EXTRACT"}}}
    systems = {}
    for s, t in L1.items():
        m = meta.get(s, {})
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"新能源危险工况": t}, "L2_params": m.get("L2_params", {}) if t else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "ev_hazard", "cn_name": "新能源危险工况", "en_name": "EV Hazard (HV Electric Safety)", "pillar": "碰撞保护",
           "systems": systems,
           "diff_summary": "仅 C-NCAP(附录L 32km/h)与 Euro(HV Electric)做新能源危险/高压电安全;其余 6 套不单列(部分在事故后安全内含电安全)",
           "key_differences": ["仅 C-NCAP 附录L『新能源危险工况』(§5.1 32km/h)与 Euro『High Voltage EV Testing』专项做 EV 危险/高压电安全",
               "JNCAP R7-04(碰撞后感电保护)归入『事故后安全』而非本项;US/ASEAN/Latin/ANCAP/Bharat 不单列 EV 危险工况",
               "评价聚焦碰撞后高压绝缘/电气隔离/电解液泄漏/热事件,与传统碰撞伤害指标不同维度"]}
    n = merge_row(row)
    res = [(L1["C-NCAP"], "C-NCAP.EV危险=测", L1["C-NCAP"], True), (L1["Euro NCAP"], "Euro.HV=测", L1["Euro NCAP"], True),
           (L1["US NCAP"] is False, "US.EV危险=不测", L1["US NCAP"], False), (L1["JNCAP"] is False, "JNCAP.EV危险=不测(归post-crash)", L1["JNCAP"], False)]
    print("ev_hazard:", [s for s,v in L1.items() if v]); ok = report(res); print("matrix", n, "项"); return 0 if ok else 1
if __name__ == "__main__":
    import sys; sys.exit(build())
