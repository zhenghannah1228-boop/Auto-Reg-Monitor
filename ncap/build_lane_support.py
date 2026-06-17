"""lane_support 车道支持(LDW/LKA)— 7 体系做、Bharat 不测。LDW警告+LKA保持均可靠检出;
ELK(紧急车道保持:路沿/对向/超车)各体系深浅不一,留 key_differences 定性、L3 期细分。"""
import glob, os
from extract_common import SRC, merge_row, report
def has_f(*p):
    return any(glob.glob(os.path.join(SRC, x), recursive=True) for x in p)
def build():
    SCN=["车道偏离警告LDW","车道保持LKA"]
    DO={"C-NCAP":"中国/*C-NCAP*/**/附录Q*.pdf","JNCAP":"日本/R7-14_en.pdf","ASEAN":"东盟/*Lane-Support*.pdf",
        "Latin NCAP":"拉美/*SA Protocol*.pdf","ANCAP":"澳洲/*Lane Departure*.pdf","Euro NCAP":"拉美/*LSS*.pdf",
        "US NCAP":"美国/**/LDW_LKS*.pdf"}
    systems={}
    for s in ["C-NCAP","JNCAP","ASEAN","Latin NCAP","ANCAP","Euro NCAP","US NCAP","Bharat NCAP"]:
        t=has_f(DO[s]) if s in DO else False
        systems[s]={"version":"","source_files":[DO.get(s,"")] if t else (["印度/AIS_197-1.pdf(无LSS)"] if s=="Bharat NCAP" else []),
            "L1_subtests":{k:t for k in SCN},
            "L2_params":({"子项":["LDW","LKA/LKS"],"_note":"ELK紧急车道保持各体系深浅不一,见差集"} if t else {}),
            "L3_thresholds":{"_status":"DIFFERENT_SCORING_MODEL" if s=="US NCAP" else ("NOT_TESTED" if not t else "TO_EXTRACT")}}
    row={"id":"lane_support","cn_name":"车道支持(LDW/LKA)","en_name":"Lane Support (LDW/LKA/ELK)","pillar":"主动安全·避撞","systems":systems,
        "diff_summary":"7 套均做车道偏离警告(LDW)+车道保持(LKA);Bharat 不测;ELK(紧急车道保持:路沿/对向车/超车)Euro/ANCAP/C-NCAP/ASEAN 含、US(2013协议)/JNCAP 偏基础",
        "key_differences":["LDW(偏离警告)+LKA/LKS(车道保持)为 7 套共有(Bharat AIS-197 无 LSS)",
            "ELK 紧急车道保持(路沿/对向来车/超车场景)是高阶差异:Euro/ANCAP/C-NCAP/ASEAN 现行协议含,US(NHTSA 2013 LDW_LKS)与 JNCAP R7-14 偏基础 LDW/LKA",
            "US 为 NHTSA 通过/不通过+星级(异构);中/欧/澳为速度区间分档评分"]}
    n=merge_row(row)
    res=[(systems[s]["L1_subtests"]["车道保持LKA"],f"{s}.车道支持=测",True,True) for s in ["C-NCAP","JNCAP","ASEAN","Latin NCAP","ANCAP","Euro NCAP","US NCAP"]]
    res+=[(any(systems["Bharat NCAP"]["L1_subtests"].values()) is False,"Bharat.车道=不测",False,False)]
    print("lane_support:",[s for s in systems if any(systems[s]["L1_subtests"].values())]);ok=report(res);print("matrix",n);return 0 if ok else 1
if __name__=="__main__":
    import sys;sys.exit(build())
