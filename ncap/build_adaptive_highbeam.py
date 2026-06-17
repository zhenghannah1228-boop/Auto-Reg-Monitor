"""adaptive_highbeam 自适应远光(AHB/ADB)— ASEAN(MS-AHB)+ C-NCAP(附录S灯光含AHB);余源内不含。"""
import glob, os
from extract_common import SRC, merge_row, report
def has_f(*p): return any(glob.glob(os.path.join(SRC,x),recursive=True) for x in p)
def build():
    L1={"ASEAN":has_f("东盟/*AHB-ADB*.pdf"),"C-NCAP":has_f("中国/*C-NCAP*/**/附录S*.pdf")}
    L1={s:L1.get(s,False) for s in ["C-NCAP","JNCAP","ASEAN","Latin NCAP","ANCAP","Euro NCAP","US NCAP","Bharat NCAP"]}
    src={"ASEAN":["东盟/MS_Test-Protocol-AHB-ADB v2.0.pdf"],"C-NCAP":["中国/.../附录S 整车灯光性能(含AHB/ADB,×82)"]}
    systems={s:{"version":"","source_files":src.get(s,[]),"L1_subtests":{"自适应远光AHB":t},
        "L2_params":({"_note":"自适应远光/自适应远光照明 ADB;含眩光抑制/切换响应"} if t else {}),
        "L3_thresholds":{"_status":"TO_EXTRACT" if t else "NOT_TESTED"}} for s,t in L1.items()}
    row={"id":"adaptive_highbeam","cn_name":"自适应远光(AHB)","en_name":"Adaptive High Beam / ADB","pillar":"主动安全·避撞","systems":systems,
        "diff_summary":"ASEAN(独立 MS-AHB/ADB)与 C-NCAP(附录S 灯光性能内含 AHB)评自适应远光;Euro/ANCAP 现实虽有但本批源未含,JNCAP/Latin/US/Bharat 不单列",
        "key_differences":["ASEAN 有独立 MS-AHB/ADB 协议;C-NCAP 在『附录S 整车灯光性能』内含 AHB/ADB(自适应远光×82)",
            "Euro/ANCAP 现实有 AHB 评估,但本批交付源未含其灯光/AHB 协议——标源待补,非定论",
            "JNCAP R7-16 为『高機能前照灯装备確認』(配备确认,非动态AHB评分);Latin/US/Bharat 不单列 AHB"]}
    n=merge_row(row)
    res=[(L1["ASEAN"],"ASEAN.AHB=测",True,True),(L1["C-NCAP"],"C-NCAP.AHB=测(附录S)",True,True),
         (L1["US NCAP"] is False,"US.AHB=不测",False,False)]
    print("AHB:",[s for s,t in L1.items() if t]);ok=report(res);print("matrix",n);return 0 if ok else 1
if __name__=="__main__":
    import sys;sys.exit(build())
