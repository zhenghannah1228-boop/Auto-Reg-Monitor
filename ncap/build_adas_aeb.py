"""adas_aeb 自动紧急制动(AEB)— 8 体系场景级 L1/L2 + 回归。
AEB 跨体系差异最大:差集在『测哪些场景目标物』(C2C后向/行人日夜/自行车/摩托车/路口)。
场景覆盖均经源文件逐协议核对(见 coverage 注)。L3(速度区间分档/判定)留批量深拆。"""
import os, glob
from extract_common import pdf_text, has, SRC, merge_row, report, asean_fitment

def has_f(*p):
    for x in p:
        if glob.glob(os.path.join(SRC, x), recursive=True): return True
    return False

# 场景级覆盖(§4 将 AEB-车辆[附录Q]与 主动行人[附录P]分两行;本行只含『车辆目标』,
# 行人/自行车归 vru_active)。源核对见各协议 token 勘查。
SCN = ["C2C后向追尾", "路口对向车", "摩托车C2M"]
COVER = {
    "C-NCAP":      [1, 1, 1],   # 附录Q
    "JNCAP":       [0, 1, 0],   # 无直行C2C;R7-12 路口对车;无摩托
    "ASEAN":       [1, 0, 1],   # AEB-C2C v2.1 + AEB-CM(摩托)
    "Latin NCAP":  [1, 0, 1],   # SA:C2C + 摩托
    "ANCAP":       [1, 1, 1],   # Crash Avoidance-Frontal
    "Euro NCAP":   [1, 0, 0],   # AEB C2C v2.0.1=直行CCR;路口对车AEB属更新协议(源内未含)
    "US NCAP":     [1, 0, 0],   # NHTSA FCW/AEB 仅前车C2C
    "Bharat NCAP": [0, 0, 0],   # AIS-197 无AEB
}
SRCF = {
    "C-NCAP": ["中国/.../附录Q 主动安全先进驾驶辅助系统.pdf"], "JNCAP": ["日本/R7-12_en.pdf(路口对车)"],
    "ASEAN": ["东盟/AEB-Car-to-Car v2.1.pdf", "东盟/AEB_CM v1.2.pdf"], "Latin NCAP": ["拉美/Latin NCAP 2025 - SA Protocol v2.0.1.pdf"],
    "ANCAP": ["澳洲/ANCAP - Crash Avoidance - Frontal Collisions v1.1.pdf"],
    "Euro NCAP": ["拉美/Euro NCAP - AEB C2C v2.0.1.pdf"],
    "US NCAP": ["美国/NHTSA/.../FCW_NCAP_Test_Procedure.pdf"], "Bharat NCAP": ["印度/AIS_197-1.pdf(无AEB)"],
}
NOTE = {"JNCAP": "对车辆 AEB 仅路口对向车(R7-12 右直),无直行追尾C2C、无摩托",
        "ASEAN": "C2C + Car-to-Motorcycle(C2M),两轮车密集", "Latin NCAP": "C2C + 摩托;行人归 vru_active",
        "Euro NCAP": "提供源为 AEB C2C v2.0.1 直行CCR;路口对车AEB属新版协议未在源内", "US NCAP": "仅前车C2C(NHTSA 星级)",
        "Bharat NCAP": "AIS-197 无AEB;Bharat NCAP ADAS 协议未在交付源内"}

def build():
    systems = {}
    for s in COVER:
        cov = dict(zip(SCN, [bool(b) for b in COVER[s]]))
        tested = any(cov.values())
        L2 = {} if not tested else {"场景目标物": [k for k, v in cov.items() if v],
                                    "_note": NOTE.get(s, "速度区间分档见 L3")}
        st = "DIFFERENT_SCORING_MODEL" if s == "US NCAP" else ("NOT_TESTED" if not tested else "TO_EXTRACT")
        if s == "ASEAN" and tested:
            fit = asean_fitment("SAT-AEB CCRs")
            fit["_note"] = "ASEAN AEB 按装备率评分(SAT-AEB CCRs/CCRm&CCRb/MS-AEB CM 三 sheet 同档:标配α1.0/选配0.5/无0);测试协议有场景速度但打分看装配——非性能阈值"
            L3 = fit
        else:
            L3 = {"_status": st, "_note": NOTE.get(s, "") if not tested else "速度区间/判定(避撞↔减速)分档,待批量深拆"}
        systems[s] = {"version": "", "source_files": SRCF.get(s, []),
                      "L1_subtests": cov, "L2_params": L2, "L3_thresholds": L3}
    row = {"id": "adas_aeb", "cn_name": "AEB(对车辆)", "en_name": "AEB — Vehicle Targets (C2C/Junction/Motorcycle)", "pillar": "主动安全·避撞",
           "systems": systems,
           "diff_summary": "对车辆AEB:C-NCAP/ANCAP 全(C2C+路口车+摩托);JNCAP 无直行C2C只测路口对车;ASEAN/Latin 含摩托(两轮密集);Euro/US 仅直行C2C;Bharat 无AEB。(行人/自行车见 vru_active)",
           "key_differences": [
               "本行只统计『对车辆』AEB;行人/自行车主动保护归 vru_active(§4 附录Q vs 附录P 分列)",
               "JNCAP 独特:对车辆 AEB 不做直行追尾 C2C,只在路口测对向车(R7-12 右直)",
               "ASEAN、Latin 因两轮车密集做 Car-to-Motorcycle(C2M);Euro/US/JNCAP 不测摩托",
               "C-NCAP、ANCAP 含『路口对向车』AEB;Euro 提供源(C2C v2.0.1)仅直行CCR、US 仅前车C2C;Bharat AIS-197 无AEB",
               "评分制:中/欧/澳/日为速度区间分档(避撞→减速量),US 为 NHTSA 星级(异构)"]}
    n = merge_row(row)
    res = [
        (any(systems["Bharat NCAP"]["L1_subtests"].values()) is False, "Bharat.对车AEB=不测(AIS-197无)", False, False),
        (systems["US NCAP"]["L1_subtests"]["C2C后向追尾"] is True and systems["US NCAP"]["L1_subtests"]["摩托车C2M"] is False, "US=仅直行C2C", True, True),
        (systems["JNCAP"]["L1_subtests"]["C2C后向追尾"] is False and systems["JNCAP"]["L1_subtests"]["路口对向车"] is True, "JNCAP=无直行C2C/有路口车", True, True),
        (systems["ASEAN"]["L1_subtests"]["摩托车C2M"] is True, "ASEAN=做C2M摩托", True, True),
        (all(systems["C-NCAP"]["L1_subtests"].values()) and all(systems["ANCAP"]["L1_subtests"].values()), "C-NCAP&ANCAP=全车辆场景", True, True),
        (len(systems["ASEAN"]["L3_thresholds"].get("_fitment", [])) == 3, "ASEAN.L3.装备率档=3(A/B/C)", len(systems["ASEAN"]["L3_thresholds"].get("_fitment", [])), 3),
    ]
    print("adas_aeb 场景覆盖:")
    for s in COVER: print(f"  {s:13}", [k for k, v in zip(SCN, COVER[s]) if v] or "不测")
    ok = report(res); print(f"matrix {n} 项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
