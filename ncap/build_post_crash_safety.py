"""post_crash_safety 事故后安全 — C-NCAP附录K(§5.1 K=15)/JNCAP R7-04感电/ANCAP救援/Euro post-crash;余不测。"""
import os, glob
from extract_common import SRC, merge_row, report
def has_f(*p):
    for x in p:
        if glob.glob(os.path.join(SRC, x), recursive=True): return True
    return False
def build():
    L1 = {"C-NCAP": has_f("中国/*C-NCAP*/**/附录K*事故后*.pdf"), "JNCAP": has_f("日本/R7-04_en.pdf"),
          "ANCAP": has_f("澳洲/*Rescue*.pdf"), "Euro NCAP": has_f("欧盟/**/post crash*/**/*.pdf"),
          "ASEAN": False, "Latin NCAP": False, "US NCAP": False, "Bharat NCAP": False}
    meta = {"C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录K 事故后安全.pdf"],
                "L2_params": {"速度": "15 km/h(§5.1 K)", "_note": "事故后:门可开启/燃油泄漏/高压断电/eCall"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
            "JNCAP": {"version": "令和7", "source_files": ["日本/R7-04_en.pdf"], "L2_params": {"_note": "R7-04 碰撞后EV感电保护"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
            "ANCAP": {"version": "v1.1", "source_files": ["澳洲/ANCAP PROTOCOL - Post-Crash - Rescue & Extrication v1.1.pdf"], "L2_params": {"_note": "救援与脱困(Rescue & Extrication)"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
            "Euro NCAP": {"version": "v1.1", "source_files": ["欧盟/Euro NCAP/post crash safety/euro_ncap_protocol_post_crash_v11.pdf"], "L2_params": {"_note": "事故后安全(门解锁/断电/eCall/救援信息)"}, "L3_thresholds": {"_status": "TO_EXTRACT"}}}
    systems = {}
    for s, t in L1.items():
        m = meta.get(s, {})
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"事故后安全": t}, "L2_params": m.get("L2_params", {}) if t else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "post_crash_safety", "cn_name": "事故后安全", "en_name": "Post-Crash Safety", "pillar": "事故后安全",
           "systems": systems,
           "diff_summary": "4 套做事故后安全:C-NCAP(附录K 15km/h)、JNCAP(R7-04 碰后感电)、ANCAP(救援脱困)、Euro(post-crash);ASEAN/Latin/US/Bharat 不单列",
           "key_differences": ["做事故后安全 4 套:C-NCAP 附录K(门开启/燃油泄漏/高压断电/eCall)、JNCAP R7-04(碰撞后EV感电)、ANCAP(Rescue & Extrication 救援脱困)、Euro(post-crash)",
               "JNCAP 本项仅评碰撞后EV感电保护,范围窄于 C-NCAP/Euro 的综合事故后安全",
               "ANCAP 侧重救援与脱困(消防/急救可达性);ASEAN/Latin/US/Bharat 不单设事故后安全项"]}
    n = merge_row(row)
    res = [(L1[s], f"{s}.事故后=测", L1[s], True) for s in ["C-NCAP", "JNCAP", "ANCAP", "Euro NCAP"]]
    res += [(L1["US NCAP"] is False, "US.事故后=不测", L1["US NCAP"], False)]
    print("post_crash:", [s for s,v in L1.items() if v]); ok = report(res); print("matrix", n, "项"); return 0 if ok else 1
if __name__ == "__main__":
    import sys; sys.exit(build())
