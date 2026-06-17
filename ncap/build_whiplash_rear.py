"""whiplash_rear 鞭打/后碰颈部 — 8 体系 + 回归。
C-NCAP 附录J 低速后碰(NIC 指标,§5.1 J=低速,无固定 km/h)。"""
import os, glob
from extract_common import pdf_text, has, SRC, merge_row, report

def fp(*p):
    for x in p:
        g = glob.glob(os.path.join(SRC, x), recursive=True)
        if g: return g[0]
    return None

def does():
    return {
        "C-NCAP": bool(fp("中国/*C-NCAP*/**/附录J*颈部*.pdf")),
        "JNCAP": bool(fp("日本/R7-05_en.pdf")) and has(pdf_text("日本/R7-05_en.pdf"), r"neck", r"rear"),
        "ASEAN": False,                                              # 东盟无鞭打/后碰协议
        "Latin NCAP": bool(fp("拉美/*whiplash*.pdf")),
        "ANCAP": bool(fp("澳洲/*Rear Impact*.pdf")),
        "Euro NCAP": bool(fp("拉美/*Whiplash*.pdf")),
        "US NCAP": bool(fp("美国/**/004*/*头枕*动态*.pdf")),         # IIHS 头枕动态(后碰)
        "Bharat NCAP": has(pdf_text("印度/AIS_197-1.pdf"), r"whiplash", r"rear impact"),  # 确认 False(仅neck准则)
    }

def build():
    L1 = does()
    meta = {
        "C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录J 低速后碰撞颈部保护.pdf"],
                   "L2_params": {"速度": "低速后碰(脉冲)", "假人": ["BioRID II"], "_note": "§5.1 J=低速;以颈部伤害指数 NIC 评价,无固定闭合速度"},
                   "L3_thresholds": {"_note": "NIC 等颈部指标分组评分(第一组NIC最高2分…)", "_status": "TO_EXTRACT"}},
        "JNCAP": {"version": "令和7(2025)", "source_files": ["日本/R7-05_en.pdf"], "L2_params": {"假人": ["BioRID"], "_note": "R7-05 後面衝突頚部保護"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
        "ASEAN": {"version": "—", "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED"}},
        "Latin NCAP": {"version": "v1.1", "source_files": ["拉美/rear-whiplash-test-protocol-v11.pdf"], "L2_params": {"假人": ["BioRID II"], "壁障": "后碰台车脉冲"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
        "ANCAP": {"version": "v1.1", "source_files": ["澳洲/ANCAP PROTOCOL - Crash Protection - Rear Impact v1.1.pdf"], "L2_params": {"假人": ["BioRID II"], "_note": "采纳Euro Whiplash"}, "L3_thresholds": {"_status": "TO_EXTRACT"}},
        "Euro NCAP": {"version": "Whiplash v3.3.1", "source_files": ["拉美/Euro NCAP - Whiplash Dynamic Assessment v3.3.1.pdf"], "L2_params": {"假人": ["BioRID II"], "壁障": "动态台车(低/中/高脉冲)"}, "L3_thresholds": {"_status": "TO_EXTRACT", "_scoring": "sliding HPL-LPL"}},
        "US NCAP": {"version": "IIHS v4", "source_files": ["美国/IIHS/.../车辆座椅头枕评估规程-动态标准(第4版).pdf"], "L2_params": {"假人": ["BioRID"], "_note": "座椅/头枕动态后碰"}, "L3_thresholds": {"_status": "DIFFERENT_SCORING_MODEL", "_note": "IIHS G/A/M/P 等级"}},
        "Bharat NCAP": {"version": "AIS-197", "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED", "_note": "AIS-197 无后碰/鞭打专项(仅各碰撞内含颈部准则)"}},
    }
    systems = {}
    for s, t in L1.items():
        m = meta[s]
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"后碰鞭打颈部保护": t},
                      "L2_params": m.get("L2_params", {}) if t else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "whiplash_rear", "cn_name": "鞭打(后碰颈部)", "en_name": "Rear Whiplash (Neck Protection)", "pillar": "碰撞保护",
           "systems": systems,
           "diff_summary": "做鞭打 6 套(均用 BioRID II);ASEAN、Bharat 不做(Bharat AIS-197 仅在各碰撞内含颈部准则、无后碰专项);US 为 IIHS 头枕动态等级制",
           "key_differences": [
               "做后碰鞭打 6 套:C-NCAP(附录J 低速 NIC)、JNCAP(R7-05)、Latin(v1.1)、ANCAP(Rear Impact)、Euro(Whiplash v3.3.1)、US(IIHS 头枕动态)",
               "ASEAN 不做鞭打/后碰;Bharat AIS-197 无后碰专项(0 处 whiplash/rear impact,仅正/侧碰内含颈部准则)——非漏项",
               "假人统一 BioRID II;C-NCAP 用颈部伤害指数 NIC 分组评分,Euro/ANCAP/Latin 用动态台车(低/中/高脉冲)滑动评分",
               "US 为 IIHS 座椅/头枕动态后碰、G/A/M/P 等级(异构),非限值制"]}
    n = merge_row(row)
    res = [(L1["ASEAN"] is False, "ASEAN.鞭打=不测", L1["ASEAN"], False),
           (L1["Bharat NCAP"] is False, "Bharat.鞭打=不测(源0处)", L1["Bharat NCAP"], False)]
    for s in ["C-NCAP", "JNCAP", "Latin NCAP", "ANCAP", "Euro NCAP", "US NCAP"]:
        res.append((L1[s] is True, f"{s}.鞭打=测", L1[s], True))
    print(f"whiplash 做此项: {[s for s,v in L1.items() if v]}")
    ok = report(res); print(f"matrix {n} 项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
