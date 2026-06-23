# -*- coding: utf-8 -*-
"""
build_kncap.py — 把 K-NCAP(韩国 NCAP)作为第9个体系并入 ncap_matrix.json。
数据来源:业主提供的 KNCAP 官方公开评价方法说明 PDF 套件(14 份,韩文)。
严禁臆造:这批为公开"평가방법(评价方法)"说明,含 L1(测试项)+ L2(速度/假人/壁障/
测量部位),但**不含 L3 数值限值**(仅列测量人体部位),L3 一律标注"本批未给数值"。
compact cars.pdf 为微型电动车评分实例(参考),非协议来源。
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX = os.path.join(HERE, "ncap_matrix.json")

VER = "现行评价方案(本批官方资料未标注年度;据含 Adv BMS 电池安全/车对车 THOR/远侧/ISA/ESF 等新增项判断为 2025+ 方案)·韩国国土交通部(MOLIT)/KATRI"
L3_NO_NUM = "本批 KNCAP 官方资料为公开『평가방법(评价方法)』说明,仅列测量人体部位,未给数值限值;数值阈值见 KATRI 详细试验/评分规程(不在本批)"

# 每个矩阵 item id -> K-NCAP 体系条目
K = {
 "frontal_rigid_full": {
   "source_files": ["KNCAP/정면충돌 안전성.pdf(正面碰撞安全性)"],
   "L1_subtests": {"正面全宽固定壁障": True},
   "L2_params": {
     "速度": "56 km/h",
     "壁障": "固定壁(고정벽)100%重叠正面碰撞",
     "假人": ["5%ile Hybrid III(成人女性)"],
     "假人位置": "驾驶席+前排乘员席+2排乘员席 均为 5%ile Hybrid III",
     "测量部位": ["头部", "颈部", "胸部", "上部大腿"],
     "_note": "KNCAP 全宽正面用 56km/h + 全席 5%ile 女性假人(源:정면충돌 안전성 평가방법)"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "frontal_mpdb_offset": {
   "source_files": ["KNCAP/차대차상호충돌 안전성.pdf(车对车相互碰撞安全性)"],
   "L1_subtests": {"车对车50%偏置": True},
   "L2_params": {
     "速度": "56 km/h",
     "壁障": "50% 偏置 车对车(차대차)相互碰撞(评乘员保护 + 车辆相互碰撞相容性)",
     "假人": ["THOR(驾驶席)", "50%ile Hybrid III(前排乘员)", "Q6", "Q10(2排)"],
     "测量部位": ["(成人)头/颈/胸/腹/上部大腿/下部大腿", "(儿童)头/颈/胸"],
     "_note": "韩国以车对车50%偏置替代固定 MPDB 台车;驾驶席用 THOR 假人(源:차대차상호충돌 안전성)"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "frontal_small_overlap": {
   "source_files": [],
   "L1_subtests": {},
   "L2_params": {"_note": "本批 KNCAP 官方资料未见正面小偏置(small overlap)项目"},
   "L3_thresholds": {"_status": "NOT_IN_SCHEME", "_note": "本批 KNCAP 评价方法套件未设正面小偏置项"}
 },
 "side_impact": {
   "source_files": ["KNCAP/측면충돌 안전성.pdf(侧面碰撞安全性)", "KNCAP/원측면충돌안전성.pdf(远侧碰撞安全性)"],
   "L1_subtests": {"可移动壁障侧碰": True, "远侧乘员": True},
   "L2_params": {
     "速度": "60 km/h",
     "壁障": "1400 kg 可移动壁障(이동벽),90度 直角侧面碰撞",
     "假人": ["50%ile WorldSID(驾驶席,成人男性)", "Q6", "Q10(2排)"],
     "测量部位": ["(成人)头/胸/腹/耻骨(치골)", "(儿童)头/颈/胸"],
     "远侧(원측면)": "在侧碰与柱碰中评同乘席乘员;驾驶席与同乘席均置 50%ile WorldSID,测 头/颈/胸/腹/骨盆",
     "_note": "源:측면충돌 안전성 + 원측면충돌안전성 평가방법"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "side_pole": {
   "source_files": ["KNCAP/기둥측면충돌 안전성.pdf(柱侧面碰撞安全性)"],
   "L1_subtests": {"斜置柱碰": True},
   "L2_params": {
     "速度": "32 km/h",
     "壁障": "柱(기둥)75度 斜角 侧面碰撞",
     "假人": ["50%ile WorldSID(驾驶席)"],
     "测量部位": ["头部", "胸部", "腹部", "耻骨"],
     "_note": "KNCAP 柱碰 32km/h、75度斜角(源:기둥측면충돌 안전성)"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "whiplash_rear": {
   "source_files": ["KNCAP/좌석안전성.pdf(座椅安全性)"],
   "L1_subtests": {"后碰颈部(静态+动态)": True},
   "L2_params": {
     "类型": "后方追尾(후방추돌)颈部伤害评价",
     "假人": ["BioRID II(1排驾驶/乘员,动态)", "H-point Machine(静态)"],
     "评价方式": "1排驾驶/乘员席:静态+动载评价;2排乘员席:仅静态评价",
     "测量部位": ["(静态)头枕高度·后方间隙(backset)", "(动态)颈部加速度·剪切力·拉伸力·力矩"],
     "_note": "源:좌석안전성 평가방법"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "post_crash_safety": {
   "source_files": ["KNCAP/교통사고긴급통보장치(정보제공).pdf(交通事故紧急通报装置/eCall)"],
   "L1_subtests": {"eCall紧急通报(信息提供)": True},
   "L2_params": {
     "项目": "交通事故紧急通报装置(e-Call):事故自动检测并即时传送事故信息的自动申报体系",
     "评价": "评碰撞前后 eCall 专用终端装着形态及主要性能基准是否与国际基准相近(以『信息提供(정보제공)』形式)",
     "_note": "源:교통사고긴급통보장치(정보제공);为信息提供项,非计分必备项"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "ev_hazard": {
   "source_files": ["KNCAP/전기자동차 안전성.pdf(电动汽车安全性)"],
   "L1_subtests": {"Adv BMS电池主动安全保护": True},
   "L2_params": {
     "项目": "驱动蓄电池管理系统(BMS)主动安全保护功能(Adv BMS, Advanced Battery Management System)——为强化电池火灾安全性而评 BMS 保护功能",
     "评价维度": ["常时异常感知(停车中驱动蓄电池热失控的常时监测)", "异常发生警告及申报(运行/充电/停车中电池异常时向驾驶员、消防等关系机关警告并申报,含经制造商向关系机关申报)", "驱动蓄电池信息存储(异常发生时电池温度/状态信息存储与备份)"],
     "_note": "KNCAP 新能源以 Adv BMS 热失控『感知-警告/申报-信息存储』为评价核心(源:전기자동차 안전성),区别于多数体系的整车热扩散计时"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "restraint_system": {
   "source_files": ["KNCAP/첨단에어백장치.pdf(尖端安全气囊装置)", "KNCAP/어린이충돌안전성.pdf(儿童碰撞安全性)"],
   "L1_subtests": {"先进气囊(静态展开)": True, "儿童乘员保护": True},
   "L2_params": {
     "先进气囊": "驾驶席行气囊静态展开试验、测假人伤害值;前排乘员席审查制造商提供的试验成绩书确认气囊性能要件",
     "儿童乘员": "车对车与侧碰中 2排乘员席置 Q6、Q10 儿童假人,测 头/颈/胸",
     "_note": "源:첨단에어백장치 + 어린이충돌안전성 평가방법"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "vru_passive": {
   "source_files": ["KNCAP/외부통행자안전성.pdf(外部通行者安全性)"],
   "L1_subtests": {"头型(行人/骑行者)": True, "腿型(行人)": True},
   "L2_params": {
     "速度": "40 km/h",
     "头型": "行人及自行车乘者头部撞击车窗玻璃/发动机罩(본닛)时的头部伤害评价(40km/h)",
     "腿型": "行人腿部撞击保险杠时的伤害评价(40km/h)",
     "_note": "源:외부통행자안전성 평가方법;另该领域含『外部通行者冲击 비상자동제동장치』(行人 AEB),见 vru_active"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "adas_aeb": {
   "source_files": ["KNCAP/사고예방안전성.pdf(事故预防安全性)"],
   "L1_subtests": {"AEBS(对运动/静止车辆)": True},
   "L2_params": {
     "项目": "非常自动制动装置(AEBS, Advanced Emergency Braking System)",
     "场景": "感知运动中及静止的车辆,评提供警告、是否减速及碰撞时的碰撞相对速度",
     "_note": "源:사고예방안전성 AEBS"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "vru_active": {
   "source_files": ["KNCAP/외부통행자안전성.pdf", "KNCAP/사고예방안전성.pdf(ESF 含行人)"],
   "L1_subtests": {"行人AEB": True, "紧急转向ESF(含行人)": True},
   "L2_params": {
     "行人AEB": "外部通行者安全性领域含『外部通行者冲击 비상자동제동장치』(行人/VRU 自动紧急制动)",
     "紧急转向ESF": "Emergency Steering Function:感知前方静止车辆(EVT)及行人,评转向回避与否",
     "_note": "源:외부통행자안전성 标题分项 + 사고예방안전성 ESF;本批仅列项目,未给场景速度档"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "lane_support": {
   "source_files": ["KNCAP/사고예방안전성.pdf"],
   "L1_subtests": {"LKAS车道维持": True},
   "L2_params": {
     "项目": "车道维持支援装置(LKAS, Lane Keeping Assistance System)",
     "场景": "摄像头识别行驶车线,评车辆是否始终维持行驶车道(直线及曲线部)",
     "_note": "源:사고예방안전성 LKAS"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
 "blind_spot": {
   "source_files": ["KNCAP/사고예방안전성.pdf"],
   "L1_subtests": {"BSD盲点监视": True, "RCCAS后侧方接近防碰撞": True},
   "L2_params": {
     "BSD": "盲点监视装置:确认盲点警告作动与否及警告激活条件(速度及时间);满足评价基准时最多给 0.5 分",
     "RCCAS": "后侧方接近碰撞防止装置:后退中感知侧面接近车辆,碰撞危险时事前警告并自动制动",
     "_note": "源:사고예방안전성 BSD/RCCAS"
   },
   "L3_thresholds": {"_partial": "BSD 满足评价基准最多 0.5 分(本批仅此一处给出分值;其余无数值)", "_note": L3_NO_NUM}
 },
 "adaptive_highbeam": {
   "source_files": [],
   "L1_subtests": {},
   "L2_params": {"_note": "本批 KNCAP 事故预防安全性所列项为 AEBS/LKAS/BSD/RCCAS/ISA/ESF,未见自适应远光(AHB)"},
   "L3_thresholds": {"_status": "NOT_IN_SCHEME", "_note": "本批 KNCAP 资料未设自适应远光(AHB)项"}
 },
 "occupant_monitoring": {
   "source_files": ["KNCAP/좌석안전띠경고장치.pdf(座椅安全带警告装置/SBR)"],
   "L1_subtests": {"安全带提醒SBR(驾驶+前排)": True},
   "L2_params": {
     "项目": "座椅安全带警告装置(SBR):监测驾驶席、前排乘员席安全带着用与否,未着用时提供初期/中间/最终警告",
     "_note": "源:좌석안전띠경고장치;KNCAP 此项为安全带提醒(SBR);本批未见驾驶员状态监测/儿童遗留检测"
   },
   "L3_thresholds": {"_note": L3_NO_NUM}
 },
}

# 另有 ISA(智能限速)、ESF(紧急转向)等 KNCAP 项目无对应矩阵行,记入说明
EXTRA_NOTE = "K-NCAP 另含 ISA(智能最高速度限制,识别限速标志并维持限速)、ESF(紧急转向)等项目,无独立矩阵行;ISA 归主动安全、ESF 已并入 vru_active 说明。微型电动车评分实例见 compact cars.pdf(参考,非协议)。"

def main():
    d = json.load(open(MATRIX, encoding="utf-8"))
    added = 0
    for it in d:
        k = K.get(it["id"])
        if not k:
            continue
        entry = {
            "version": VER,
            "source_files": k["source_files"],
            "L1_subtests": k["L1_subtests"],
            "L2_params": k["L2_params"],
            "L3_thresholds": k["L3_thresholds"],
        }
        it["systems"]["K-NCAP"] = entry
        added += 1
    # 顶层备注(若结构允许)——这里 d 是 list,附在每条已足够;额外说明写入 coverage 注记
    json.dump(d, open(MATRIX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("K-NCAP added to %d / %d items" % (added, len(d)))
    print("EXTRA:", EXTRA_NOTE)

if __name__ == "__main__":
    main()
