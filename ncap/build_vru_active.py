"""vru_active 弱势者主动保护(AEB-VRU)— 行人/自行车主动制动。
§4 附录P;与 adas_aeb(对车辆)分列。源核对见 AEB-VRU 协议 token 勘查。"""
import glob, os
from extract_common import SRC, merge_row, report

SCN = ["AEB行人日间", "AEB行人夜间", "AEB自行车", "路口转向行人"]
COVER = {
    "C-NCAP":      [1, 1, 1, 1],   # 附录P 弱势交通参与者保护(主动)
    "JNCAP":       [1, 1, 1, 1],   # R7-09行人昼/R7-10行人夜/R7-11自行车/R7-13路口对人右左折
    "ASEAN":       [0, 0, 0, 0],   # 无 AEB-VRU 协议(MS-PED 为被动头/腿型,归 vru_passive)
    "Latin NCAP":  [1, 0, 0, 0],   # SA:含行人;无夜间/自行车/路口
    "ANCAP":       [1, 1, 1, 1],   # Crash Avoidance-Frontal(采纳Euro VRU)
    "Euro NCAP":   [1, 1, 1, 1],   # AEB VRU v2.0.4:行人日/夜 + 自行车 + 转向横穿
    "US NCAP":     [0, 0, 0, 0],   # NHTSA NCAP 不做主动行人AEB
    "Bharat NCAP": [0, 0, 0, 0],   # AIS-197 无AEB
}
SRCF = {"C-NCAP": ["中国/.../附录P 弱势交通参与者保护(主动安全).pdf"], "JNCAP": ["日本/R7-09/10/11/13_en.pdf"],
        "Latin NCAP": ["拉美/Latin NCAP 2025 - SA Protocol v2.0.1.pdf"], "ANCAP": ["澳洲/ANCAP - Crash Avoidance - Frontal v1.1.pdf"],
        "Euro NCAP": ["拉美/Euro NCAP - AEB VRU test protocol v2.0.4.pdf"]}
NOTE = {"ASEAN": "无AEB-VRU(MS-PED 为被动头/腿型→ vru_passive)", "Latin NCAP": "SA 含行人AEB;无夜间/自行车",
        "US NCAP": "NHTSA NCAP 不评主动行人AEB", "Bharat NCAP": "AIS-197 无AEB"}

def build():
    systems = {}
    for s in COVER:
        cov = dict(zip(SCN, [bool(b) for b in COVER[s]]))
        tested = any(cov.values())
        systems[s] = {"version": "", "source_files": SRCF.get(s, []),
                      "L1_subtests": cov,
                      "L2_params": ({"目标场景": [k for k, v in cov.items() if v], "_note": NOTE.get(s, "速度区间见L3")} if tested else {}),
                      "L3_thresholds": {"_status": "NOT_TESTED" if not tested else "TO_EXTRACT", "_note": NOTE.get(s, "")}}
    row = {"id": "vru_active", "cn_name": "弱势者主动保护(AEB-VRU)", "en_name": "Active VRU Protection (Pedestrian/Cyclist AEB)", "pillar": "主动安全·避撞",
           "systems": systems,
           "diff_summary": "AEB行人/自行车:C-NCAP/JNCAP/ANCAP/Euro 全(含夜间+自行车);Latin 仅行人;ASEAN/US/Bharat 不做主动VRU(ASEAN只做被动头腿型)",
           "key_differences": [
               "C-NCAP/JNCAP/ANCAP/Euro 做完整主动 VRU AEB(行人日+夜+自行车);Latin 仅行人(无夜间/自行车)",
               "ASEAN 不做主动 VRU(其 MS-PED 是被动头/腿型,归 vru_passive)——主被动之分是关键差集",
               "US NCAP、Bharat 不做主动行人 AEB(US 侧重 C2C;Bharat AIS-197 无 AEB)",
               "夜间行人 AEB(照度/前照灯影响)仅 C-NCAP/JNCAP/ANCAP/Euro 评,是高阶差异项"]}
    n = merge_row(row)
    res = [
        (all(systems[s]["L1_subtests"].values()) for s in ["C-NCAP", "JNCAP", "ANCAP", "Euro NCAP"])]
    res = [(all(systems[s]["L1_subtests"].values()), f"{s}.主动VRU=全场景", True, True) for s in ["C-NCAP", "JNCAP", "ANCAP", "Euro NCAP"]]
    res += [(any(systems["ASEAN"]["L1_subtests"].values()) is False, "ASEAN.主动VRU=不测(被动归vru_passive)", False, False),
            (any(systems["US NCAP"]["L1_subtests"].values()) is False, "US.主动VRU=不测", False, False),
            (systems["Latin NCAP"]["L1_subtests"]["AEB行人日间"] is True and systems["Latin NCAP"]["L1_subtests"]["AEB自行车"] is False, "Latin=仅行人", True, True)]
    print("vru_active 覆盖:")
    for s in COVER: print(f"  {s:13}", [k for k, v in zip(SCN, COVER[s]) if v] or "不测")
    ok = report(res); print(f"matrix {n} 项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
