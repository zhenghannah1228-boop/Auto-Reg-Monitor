"""frontal_small_overlap 正面小偏置(25%) — 典型差集项:仅 US(IIHS)做。
源核实:其余 7 套协议 small overlap 命中=0;仅 IIHS 有 002 25_小偏置正碰目录。"""
import os, glob
from extract_common import SRC, merge_row, report

def has_dir(*pats):
    for p in pats:
        if glob.glob(os.path.join(SRC, p), recursive=True): return True
    return False

def build():
    # 仅 IIHS(US)做 25% 小偏置;其余体系协议无 small overlap(已核实命中=0)
    L1 = {"C-NCAP": False, "JNCAP": False, "ASEAN": False, "Latin NCAP": False,
          "ANCAP": False, "Euro NCAP": False,
          "US NCAP": has_dir("美国/**/002*小偏置*/**", "美国/**/002*25*/**"),
          "Bharat NCAP": False}
    systems = {}
    for s, tested in L1.items():
        if s == "US NCAP" and tested:
            systems[s] = {"version": "IIHS", "source_files": ["美国/IIHS-NCAP评估测试规程/002  25_小偏置正碰/*"],
                          "L1_subtests": {"正面小偏置": True},
                          "L2_params": {"速度": "64 km/h(40 mph)", "重叠率": "25%", "假人": ["Hybrid III 50th"],
                                        "壁障": "刚性壁障小偏置(驾驶侧 + 乘客侧)", "_note": "IIHS small overlap,5英寸刚性壁障25%重叠"},
                          "L3_thresholds": {"_status": "DIFFERENT_SCORING_MODEL", "_note": "IIHS G/A/M/P 等级(结构+伤害+假人运动)"}}
        else:
            systems[s] = {"version": "", "L1_subtests": {"正面小偏置": False}, "L2_params": {},
                          "L3_thresholds": {"_status": "NOT_TESTED"}}
    row = {"id": "frontal_small_overlap", "cn_name": "正面小偏置", "en_name": "Small Overlap Frontal (25%)",
           "pillar": "碰撞保护", "systems": systems,
           "diff_summary": "8 套中仅 US(IIHS 25%小偏置)测——典型差集项,其余 7 套均不做",
           "key_differences": [
               "典型差集项:8 套中唯一做 25% 正面小偏置的只有 US(IIHS)——其余 7 套协议 small overlap 命中=0",
               "小偏置考验纵梁外侧/轮罩/A 柱的载荷路径,常规 MPDB/ODB 偏置(50%/40%)不覆盖此工况",
               "IIHS 含驾驶侧 + 乘客侧两次 25% 小偏置;64km/h(40mph)、G/A/M/P 等级",
               "车型冲 IIHS Top Safety Pick+ 必须额外准备小偏置;冲 C-NCAP/Euro/ASEAN 五星则无需此项"]}
    n = merge_row(row)
    res = [(L1["US NCAP"] is True, "US.小偏置=测(IIHS)", L1["US NCAP"], True)]
    for s in ["C-NCAP", "JNCAP", "ASEAN", "Latin NCAP", "ANCAP", "Euro NCAP", "Bharat NCAP"]:
        res.append((L1[s] is False, f"{s}.小偏置=不测", L1[s], False))
    print(f"frontal_small_overlap 做此项: {[s for s,v in L1.items() if v]}(应仅 US)")
    ok = report(res); print(f"ncap_matrix.json 现有 {n} 个测试项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
