"""adaptive_highbeam 自适应远光(AHB/ADB)。
源核实后定性(业主 2026-06 确认):
- ASEAN:MS AHB-ADB v2.0 独立协议 + 装备率评分(MS-AHB xlsm)→ 绿"测"。
- C-NCAP:附录S 整车灯光性能内含 AHB/ADB(×82)→ 测。
- Euro / ANCAP:**无独立 AHB/灯光协议**;AHB/ADB 是 **Safe Driving 评估协议内的一个评分子项**
  (业主确认),故资料包里本就没有独立 AHB 文件。→ L1=测(确做),但无独立阈值表 → 测·部分,
  **非"待补/等文件"**(文件本就不存在)。
- JNCAP R7-16=高機能前照灯『装备确认』(非动态AHB评分);Latin/US/Bharat 不单列。"""
import glob, os
from extract_common import SRC, merge_row, report, asean_fitment
def has_f(*p): return any(glob.glob(os.path.join(SRC, x), recursive=True) for x in p)

def build():
    HAS = {"ASEAN": has_f("东盟/*AHB-ADB*.pdf") or has_f("东盟/*AHB_ADB*.pdf"),
           "C-NCAP": has_f("中国/*C-NCAP*/**/附录S*.pdf")}
    WITHIN_SD = {"Euro NCAP", "ANCAP"}   # AHB 是 Safe Driving 评估的评分子项,无独立协议(业主确认)
    src = {"ASEAN": ["东盟/ASEAN NCAP MS AHB-ADB v2.0(2024)"], "C-NCAP": ["中国/.../附录S 整车灯光性能(含AHB/ADB,×82)"],
           "Euro NCAP": ["欧盟/Euro NCAP Safe Driving 评估(AHB/ADB 为其评分子项,无独立协议)"],
           "ANCAP": ["澳洲/ANCAP Safe Driving(采纳 Euro;AHB 为 Safe Driving 子项,无独立协议)"]}
    systems = {}
    for s in ["C-NCAP", "JNCAP", "ASEAN", "Latin NCAP", "ANCAP", "Euro NCAP", "US NCAP", "Bharat NCAP"]:
        within = s in WITHIN_SD
        t = HAS.get(s, False) or within     # Euro/ANCAP 确做 AHB(Safe Driving 子项)
        if s == "ASEAN" and HAS.get(s):
            # 源核实(MS AHB-ADB v2.0):夜间路面照度·切换·车速 等真实测试条件
            l2 = {"速度": "50±10 / 80±20 km/h(两档)",
                  "夜间路面照度": "有路灯 ≥15 lux / 无路灯 <5 lux",
                  "评估点": "A、B 两点相距 3.3 m(最小 5 lux)",
                  "_note": "ADB 自动切换 Low↔High,探测对向/前车减眩光;评分按装备率(MS-AHB),测试条件见此协议"}
        elif within:
            l2 = {"_note": "AHB/ADB 为 Safe Driving 评估的一个评分子项;无独立 AHB/灯光协议(故无独立阈值表)"}
        else:
            l2 = {"_note": "自适应远光/自适应远光照明 ADB;眩光抑制/切换响应"} if t else {}
        if s == "ASEAN" and HAS.get(s):
            l3 = asean_fitment("MS-AHB")
        elif within:
            l3 = {"_status": "WITHIN_SAFE_DRIVING",
                  "_note": "Euro/ANCAP 无独立 AHB 协议;AHB/ADB 作为 Safe Driving 评估的评分子项计分,无独立阈值表——非『待补/缺文件』(独立文件本就不存在)"}
        else:
            l3 = {"_status": "TO_EXTRACT" if t else "NOT_TESTED"}
        systems[s] = {"version": "v2.0" if s == "ASEAN" and HAS.get(s) else "",
                      "source_files": src.get(s, []),
                      "L1_subtests": {"自适应远光AHB": t},
                      "L2_params": l2 if t else {},
                      "L3_thresholds": l3}
    row = {"id": "adaptive_highbeam", "cn_name": "自适应远光(AHB)", "en_name": "Adaptive High Beam / ADB", "pillar": "主动安全·避撞", "systems": systems,
        "diff_summary": "ASEAN(独立 MS-AHB/ADB 协议+装备率)、C-NCAP(附录S 灯光含 AHB)有独立协议;"
                        "Euro/ANCAP 确做 AHB 但作为 Safe Driving 评估子项、无独立协议/阈值(故无独立文件);"
                        "JNCAP R7-16 仅装备确认;Latin/US/Bharat 不单列",
        "key_differences": [
            "ASEAN 有独立 MS-AHB/ADB 协议(装备率评分);C-NCAP 在『附录S 整车灯光性能』内含 AHB/ADB(×82)",
            "Euro/ANCAP 确评 AHB/ADB,但它是 **Safe Driving 评估协议的一个评分子项**,无独立 AHB/灯光协议——"
            "资料包找不到独立 AHB 文件是因为它本就不存在(非缺料);故标『测·部分』(无独立阈值表),不标『待补』",
            "JNCAP R7-16 为『高機能前照灯装备確認』(配备确认,非动态AHB评分);Latin/US/Bharat 不单列 AHB"]}
    n = merge_row(row)
    res = [(systems["ASEAN"]["L1_subtests"]["自适应远光AHB"], "ASEAN.AHB=测", True, True),
           (systems["C-NCAP"]["L1_subtests"]["自适应远光AHB"], "C-NCAP.AHB=测(附录S)", True, True),
           (systems["Euro NCAP"]["L1_subtests"]["自适应远光AHB"] and systems["Euro NCAP"]["L3_thresholds"]["_status"] == "WITHIN_SAFE_DRIVING",
            "Euro.AHB=测·Safe Driving子项(非待补)", True, True),
           (systems["ANCAP"]["L1_subtests"]["自适应远光AHB"] and systems["ANCAP"]["L3_thresholds"]["_status"] == "WITHIN_SAFE_DRIVING",
            "ANCAP.AHB=测·Safe Driving子项", True, True),
           (systems["Latin NCAP"]["L1_subtests"]["自适应远光AHB"] is False, "Latin.AHB=不单列", False, False)]
    print("AHB:", {s: ("测" if systems[s]["L1_subtests"]["自适应远光AHB"] else "不测") for s in systems})
    ok = report(res); print("matrix", n); return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
