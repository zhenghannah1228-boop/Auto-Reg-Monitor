"""blind_spot 盲点监测(BSD/BST)— ASEAN(MS-BST)+ ANCAP(Lane Departure内BSM);余不测。"""
import glob, os
from extract_common import SRC, merge_row, report
def has_f(*p): return any(glob.glob(os.path.join(SRC,x),recursive=True) for x in p)
def build():
    DO={"ASEAN":has_f("东盟/*BST-Detection*.pdf"),"ANCAP":has_f("澳洲/*Lane Departure*.pdf")}  # ANCAP BSM 在 Lane Departure 协议(×13)
    L1={s:DO.get(s,False) for s in ["C-NCAP","JNCAP","ASEAN","Latin NCAP","ANCAP","Euro NCAP","US NCAP","Bharat NCAP"]}
    src={"ASEAN":["东盟/MS_Test-Protocol-BST-Detection v2.1 + BST-Visualization v2.0.pdf"],"ANCAP":["澳洲/ANCAP - Crash Avoidance - Lane Departure v1.1(BSM)"]}
    systems={s:{"version":"","source_files":src.get(s,[]),"L1_subtests":{"盲点监测BST":t},
        "L2_params":({"_note":"盲点检测+(ASEAN另含可视化Visualization)"} if t else {}),
        "L3_thresholds":{"_status":"TO_EXTRACT" if t else "NOT_TESTED"}} for s,t in L1.items()}
    row={"id":"blind_spot","cn_name":"盲点监测(BSD)","en_name":"Blind Spot Detection","pillar":"主动安全·避撞","systems":systems,
        "diff_summary":"仅 ASEAN(MS-BST 检测+可视化)与 ANCAP(并入车道偏离/变道场景)评盲点监测;C-NCAP/JNCAP/Latin/Euro/US/Bharat 不单列——典型差集",
        "key_differences":["盲点监测为窄覆盖项:ASEAN 有独立 MS-BST(Detection + Visualization 两协议)、ANCAP 在 Lane Departure/变道安全内评(×13)",
            "C-NCAP/JNCAP/Latin/Euro/US/Bharat 不单列盲点监测(部分作整车配置加分但无专项测试)",
            "ASEAN 因摩托车密集额外重视盲点可视化(BST-Visualization)——区域特色"]}
    n=merge_row(row)
    res=[(L1["ASEAN"],"ASEAN.盲点=测",True,True),(L1["ANCAP"],"ANCAP.盲点=测",True,True),
         (L1["C-NCAP"] is False,"C-NCAP.盲点=不测(无专项)",False,False),(L1["Euro NCAP"] is False,"Euro.盲点=不测",False,False)]
    print("blind_spot:",[s for s,t in L1.items() if t]);ok=report(res);print("matrix",n);return 0 if ok else 1
if __name__=="__main__":
    import sys;sys.exit(build())
