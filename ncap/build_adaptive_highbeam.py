"""adaptive_highbeam 自适应远光(AHB/ADB)— ASEAN(MS-AHB)+ C-NCAP(附录S灯光含AHB)有源;
Euro/ANCAP 现实评AHB但本批无协议=源待补(≠不测,避免误导);JNCAP/Latin/US/Bharat 不单列。"""
import glob, os
from extract_common import SRC, merge_row, report
def has_f(*p): return any(glob.glob(os.path.join(SRC, x), recursive=True) for x in p)

def build():
    HAS = {"ASEAN": has_f("东盟/*AHB-ADB*.pdf"), "C-NCAP": has_f("中国/*C-NCAP*/**/附录S*.pdf")}
    PENDING = {"Euro NCAP", "ANCAP"}  # 现实评AHB,手头无协议 → source_pending(待补)
    src = {"ASEAN": ["东盟/MS_Test-Protocol-AHB-ADB v2.0.pdf"], "C-NCAP": ["中国/.../附录S 整车灯光性能(含AHB/ADB,×82)"]}
    systems = {}
    for s in ["C-NCAP", "JNCAP", "ASEAN", "Latin NCAP", "ANCAP", "Euro NCAP", "US NCAP", "Bharat NCAP"]:
        t = HAS.get(s, False)
        pend = s in PENDING
        systems[s] = {"version": "", "source_files": src.get(s, []),
            "L1_subtests": {"自适应远光AHB": t},
            "L2_params": ({"_note": "自适应远光/自适应远光照明 ADB;眩光抑制/切换响应"} if t else {}),
            "L3_thresholds": ({"_status": "SOURCE_PENDING", "_note": "现实评估AHB(Euro/ANCAP 灯光/AHB),本批交付源未含其协议——源待补,非不测"} if pend
                              else {"_status": "TO_EXTRACT" if t else "NOT_TESTED"})}
    row = {"id": "adaptive_highbeam", "cn_name": "自适应远光(AHB)", "en_name": "Adaptive High Beam / ADB", "pillar": "主动安全·避撞", "systems": systems,
        "diff_summary": "ASEAN(独立 MS-AHB/ADB)与 C-NCAP(附录S 灯光含 AHB)有源核实;Euro/ANCAP 现实评 AHB 但本批无协议=源待补(非不测);JNCAP/Latin/US/Bharat 不单列",
        "key_differences": [
            "ASEAN 有独立 MS-AHB/ADB 协议;C-NCAP 在『附录S 整车灯光性能』内含 AHB/ADB(×82)",
            "Euro/ANCAP 现实有 AHB 评估,但本批交付源未含其灯光/AHB 协议 → 标『源待补』,工程师勿误读为不评远光",
            "JNCAP R7-16 为『高機能前照灯装备確認』(配备确认,非动态AHB评分);Latin/US/Bharat 不单列 AHB"]}
    n = merge_row(row)
    res = [(systems["ASEAN"]["L1_subtests"]["自适应远光AHB"], "ASEAN.AHB=测", True, True),
           (systems["C-NCAP"]["L1_subtests"]["自适应远光AHB"], "C-NCAP.AHB=测(附录S)", True, True),
           (systems["Euro NCAP"]["L3_thresholds"]["_status"] == "SOURCE_PENDING", "Euro.AHB=源待补(非不测)", "SOURCE_PENDING", "SOURCE_PENDING"),
           (systems["ANCAP"]["L3_thresholds"]["_status"] == "SOURCE_PENDING", "ANCAP.AHB=源待补", "SOURCE_PENDING", "SOURCE_PENDING")]
    print("AHB 有源:", [s for s in systems if systems[s]["L1_subtests"]["自适应远光AHB"]], "| 源待补:", list(PENDING))
    ok = report(res); print("matrix", n); return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
