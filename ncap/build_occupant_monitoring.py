"""occupant_monitoring 座舱乘员监测与提醒 — 子项 SBR/儿童遗留CPD/驾驶员监测DMS。
源核对:ANCAP=儿童遗留(DMS×0/child×7)、JNCAP=仅SBR(R7-08)、C-NCAP附录N=监测+提醒。"""
import glob, os
from extract_common import SRC, merge_row, report, asean_fitment
def has_f(*p): return any(glob.glob(os.path.join(SRC,x),recursive=True) for x in p)
def build():
    SUB=["安全带提醒SBR","儿童遗留检测CPD","驾驶员监测DMS"]
    COVER={"C-NCAP":[1,1,0],   # 附录N原文核实:驾驶员监测DMS×0 → 仅SBR(×7)+儿童遗留(×1),无DMS
           "JNCAP":[1,0,0],    # R7-08 仅 SBR
           "ANCAP":[0,1,0],    # Occupant Monitoring=儿童遗留(child×7,DMS×0)
           "Euro NCAP":[0,1,0],# 儿童遗留/乘员状态
           "ASEAN":[1,1,0],    # 业主2026-06确认修正:SAT-SBR(安全带提醒)+ COP CPD(儿童遗留)装备率评分表,原[0,0,0]为漏项
           "Latin NCAP":[0,0,0],"US NCAP":[0,0,0],"Bharat NCAP":[0,0,0]}
    src={"C-NCAP":["中国/.../附录N 座舱乘员安全监测与提醒.pdf"],"JNCAP":["日本/R7-08_en.pdf(SBR)"],
         "ANCAP":["澳洲/ANCAP - Safe Driving - Occupant Monitoring v1.1.pdf"],"Euro NCAP":["欧盟/Euro NCAP/safe driving/..."],
         "ASEAN":["东盟/...xlsm sheet 'SAT-SBR'(安全带提醒 TFS6)","东盟/...xlsm sheet 'COP CPD'(儿童遗留检测 TFS5)"]}
    # ASEAN 乘员监测 L3:装备率(SAT-SBR 主表)+ COP CPD 并注
    asean_l3=asean_fitment("SAT-SBR")
    if asean_l3:
        cpd=asean_fitment("COP CPD")
        asean_l3["_note"]=("ASEAN 乘员监测含两张装备率评分表:SAT-SBR(安全带提醒,满分TFS=%s,本表)+ "
                           "COP CPD(儿童遗留检测,TFS=%s);均按装配档评分,DMS 不单列"%(asean_l3.get("_TFS"),cpd.get("_TFS")))
    systems={}
    for s in COVER:
        cov=dict(zip(SUB,[bool(b) for b in COVER[s]]));t=any(cov.values())
        if s=="ASEAN" and t and asean_l3:
            l3=asean_l3
        else:
            l3={"_status":"NOT_TESTED" if not t else "TO_EXTRACT"}
        systems[s]={"version":"","source_files":src.get(s,[]),"L1_subtests":cov,
            "L2_params":({"子项":[k for k,v in cov.items() if v]} if t else {}),
            "L3_thresholds":l3}
    row={"id":"occupant_monitoring","cn_name":"乘员监测提醒","en_name":"Occupant Monitoring & Reminder","pillar":"安全驾驶·辅助","systems":systems,
        "diff_summary":"异质差集:C-NCAP 附录N(SBR+儿童遗留)与 ASEAN(SAT-SBR+COP CPD,装备率)均含 SBR+CPD;JNCAP 仅 SBR;ANCAP/Euro 为儿童遗留CPD;Latin/US/Bharat 不测。DMS驾驶员监测各体系尚未单列动态评分",
        "key_differences":["子项异质是关键差集:C-NCAP/ASEAN(SBR+儿童遗留CPD)、JNCAP(仅SBR)、ANCAP(儿童遗留CPD,DMS×0)、Euro(儿童遗留/乘员状态)",
            "C-NCAP 附录N 经原文核实不含驾驶员监测DMS(驾驶员状态×0),仅 SBR+儿童遗留;无体系把 DMS 作独立动态评分项",
            "ASEAN 经源核实(SAT-SBR + COP CPD 装备率表)做 SBR+儿童遗留,但按『装备率』评分(是否装配),非性能/动态测试——与中欧日的测试制不同",
            "Latin/US/Bharat 不单列乘员监测提醒",
            "『监测/提醒』口径不一:提醒(SBR)vs 检测(儿童遗留)vs 监测(驾驶员状态),跨体系冲星须分清"]}
    n=merge_row(row)
    res=[(systems["JNCAP"]["L1_subtests"]["安全带提醒SBR"] and systems["JNCAP"]["L1_subtests"]["儿童遗留检测CPD"] is False,"JNCAP=仅SBR",True,True),
         (systems["ANCAP"]["L1_subtests"]["儿童遗留检测CPD"] and systems["ANCAP"]["L1_subtests"]["驾驶员监测DMS"] is False,"ANCAP=儿童遗留(非DMS)",True,True),
         (any(systems["US NCAP"]["L1_subtests"].values()) is False,"US.乘员监测=不测",False,False),
         (any(systems["C-NCAP"]["L1_subtests"].values()),"C-NCAP=测",True,True),
         (systems["ASEAN"]["L1_subtests"]["安全带提醒SBR"] and systems["ASEAN"]["L1_subtests"]["儿童遗留检测CPD"],"ASEAN=SBR+CPD(修正)",True,True),
         (systems["ASEAN"]["L1_subtests"]["驾驶员监测DMS"] is False,"ASEAN.DMS=不测",False,False),
         (asean_l3.get("_TFS")==6.0,"ASEAN.L3.SBR装备率TFS=6",asean_l3.get("_TFS"),6.0)]
    print("occupant_monitoring:",{s:[k for k,v in systems[s]["L1_subtests"].items() if v] for s in COVER if any(systems[s]["L1_subtests"].values())})
    ok=report(res);print("matrix",n);return 0 if ok else 1
if __name__=="__main__":
    import sys;sys.exit(build())
