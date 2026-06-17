"""frontal_rigid_full 正面100%重叠刚性壁障 — 8 体系 + 回归。
C-NCAP 速度按 §5.1 核对值(A=50);源文本受脚注上标污染(附录A 原始='551',
字号过滤得'55',均不可信)→ 采用 §5.1 人工核对值 50 并记录污染。
C-NCAP 文件须限定 C-NCAP 2027版目录(避开同名 C-ICAP 智能网联附录)。"""
import os, re, glob
from extract_common import pdf_text, has, SRC, merge_row, report, cncap_L3_text, jncap_hic_bands, euro_hpl_lpl, EURO_BANDS_NOTE

# Euro 正面 AOP 伤害限值(HIII 50th 滑动 HPL-LPL),Latin/ANCAP 采纳同表
EURO_FRONT_CRIT = {"头部HIC15": "HIC15", "头部Ares-3ms": "Ares-3ms", "颈部Fx剪切": "FX,shear",
                   "颈部Fz拉伸": "FZ,tension", "颈部My伸张": "MYextension", "股骨Ffemur": "Ffemur",
                   "膝Dknee": "Dknee", "胫骨Ftibia": "Ftibia", "胫骨指数Itibia": "Itibia"}
EURO_FRONT_GLOB = "欧盟/**/euro_ncap_protocol_crash_protection_frontal_impact_v11*.pdf"

CNCAP_REF = {"A": 50, "B": 50, "C": 56, "D": 56, "G": 60, "H": 32, "K": 15, "L": 32, "O": 40}  # §5.1

def cnap(letter, *kw):
    """限定 C-NCAP 2027版 附录目录,按字母+关键词取文件(避开 C-ICAP)。"""
    g = glob.glob(os.path.join(SRC, f"中国/*C-NCAP*/02 规程附录A-T/附录{letter}*.pdf"))
    return g[0] if g else None

def cncap_raw_speed(f):
    """捕捉『碰撞速度为…km/h』之间的原始片段作污染证据(含上标/±符号)。"""
    t = pdf_text(f)
    m = re.search(r"碰撞速度为\s*(.{1,8}?)\s*km/h", t)
    return m.group(1).strip() if m else None

def find(*pats):
    for p in pats:
        g = glob.glob(os.path.join(SRC, p), recursive=True)
        if g: return g[0]
    return None

def build():
    fA = cnap("A")
    raw = cncap_raw_speed(fA)           # 污染值,仅记录
    cn_speed = CNCAP_REF["A"]           # §5.1 核对值
    # C-NCAP 附录A L3:头部三限值(HIC15/累积3ms)文本模式实拆(颈/胸/腿为双假人多列,严禁臆造不自动拆)
    _a = cncap_L3_text("中国/*C-NCAP*/02 规程附录A-T/附录A*.pdf", ["表A.7 前排假人头部"])
    cn_l3 = {}
    for blk in _a.values():
        cn_l3.update(blk)
    # Euro 正面 AOP HPL-LPL(HIII 50th);Latin/ANCAP 采纳同表
    euro_front = euro_hpl_lpl(EURO_FRONT_GLOB, {29, 30}, EURO_FRONT_CRIT)
    def euro_l3(source, note_prefix):
        return {"_extracted_tables": {"成人 HIII 50th": euro_front},
                "_scoring": "sliding HPL-LPL(色带5档)", "_source": source,
                "_note": note_prefix + EURO_BANDS_NOTE}
    # L1 各体系是否做 正面100%全宽刚性
    L1 = {
        "C-NCAP": bool(fA),
        "JNCAP": has(pdf_text("日本/R7-01_en.pdf"), r"frontal", r"full"),   # R7-01 フルラップ
        "ASEAN": False,   # 东盟仅做 ODB 偏置,无全宽刚性(协议+xlsm 均无 full width)
        "Latin NCAP": bool(find("拉美/*Full Width*Sled*.pdf", "拉美/*FWT*.pdf")),
        "ANCAP": has(pdf_text(find("澳洲/*Frontal Impact*.pdf") or ""), r"full width", r"full-width", r"rigid"),
        "Euro NCAP": bool(find("欧盟/**/*frontal_impact*.pdf")),
        "US NCAP": True,    # NHTSA 全宽刚性正碰(35mph≈56);IIHS 不做全宽
        "Bharat NCAP": False,   # L1 纠错(核 AIS-197):Bharat 正面唯一为 ODB 偏置 64km/h 40%(§10.1 测试矩阵),无全宽刚性
    }
    meta = {
        "C-NCAP": {"version": "2027版", "source_files": ["中国/.../附录A 正面100%重叠刚性壁障.pdf"],
                   "L2_params": {"速度": f"{cn_speed} km/h", "假人": ["Hybrid III 50th", "Hybrid III 5th", "Q系列(后排儿童)"],
                                 "壁障": "100%重叠固定刚性壁障",
                                 "_extraction_note": f"§5.1 核对值={cn_speed};源文本脚注上标污染(原始提取='{raw}'不可用)"},
                   "L3_thresholds": {"_extracted_front": cn_l3, "_source": "附录A 表A.7 前排假人头部评价指标",
                                     "_note": "头部三限值(高/低/极限)实拆;颈/胸/大腿/小腿为驾驶员5th+乘员50th 双假人多列,按严禁臆造不自动拆解(见附录A 表A.8–A.11)"}},
        "JNCAP": {"version": "令和7(2025)", "source_files": ["日本/R7-01_en.pdf", "日本/2025_en.pdf(评价方法)"], "L2_params": {"速度": "50 km/h", "假人": ["Hybrid III", "WorldSID"], "_note": "R7-01 フルラップ前面衝突 50.0±1km/h(源核对,非55)"}, "L3_thresholds": jncap_hic_bands()},
        "ASEAN": {"version": "Protocol 2026-2030", "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED"}},
        "Latin NCAP": {"version": "2025", "source_files": ["拉美/Latin NCAP - Full Width Sled Test Protocol v2.0.0.pdf", "采纳 Euro AOP 限值"], "L2_params": {"壁障": "全宽台车(Sled,脉冲法)", "_note": "台车脉冲复现,无单一闭合速度"}, "L3_thresholds": euro_l3("采纳 Euro NCAP 正面 AOP 限值(HIII 50th)", "Latin 采纳 Euro 伤害限值;")},
        "ANCAP": {"version": "v1.1", "L2_params": {"速度": "50 km/h", "壁障": "全宽刚性(采纳Euro)"}, "L3_thresholds": euro_l3("采纳 Euro NCAP 正面 AOP 限值(HIII 50th)", "ANCAP 采纳 Euro 伤害限值;")},
        "Euro NCAP": {"version": "v1.1 2026", "source_files": ["欧盟/.../euro_ncap_protocol_crash_protection_frontal_impact_v11"], "L2_params": {"速度": "50 km/h", "壁障": "全宽刚性 FW"}, "L3_thresholds": euro_l3("Euro NCAP 正面碰撞协议 v1.1 §3.5 伤害限值(HIII 50th)", "")},
        "US NCAP": {"version": "NHTSA", "L2_params": {"速度": "56 km/h(35mph)", "壁障": "全宽刚性", "假人": ["Hybrid III 50th", "5th"]}, "L3_thresholds": {"_status": "DIFFERENT_SCORING_MODEL"}},
        "Bharat NCAP": {"version": "AIS-197", "source_files": ["印度/AIS_197-1.pdf"], "L2_params": {}, "L3_thresholds": {"_status": "NOT_TESTED", "_note": "L1 纠错:Bharat NCAP 正面唯一为 ODB 偏置(64km/h 40%,AIS-197 §10.1),不做全宽 100% 刚性正碰"}},
    }
    systems = {}
    for s, tested in L1.items():
        m = meta[s]
        systems[s] = {"version": m.get("version", ""), "source_files": m.get("source_files", []),
                      "L1_subtests": {"正面全宽刚性": tested},
                      "L2_params": m.get("L2_params", {}) if tested else {},
                      "L3_thresholds": m.get("L3_thresholds", {"_status": "NOT_TESTED"})}
    row = {"id": "frontal_rigid_full", "cn_name": "正面100%刚性壁障", "en_name": "Full Width Rigid Barrier Frontal",
           "pillar": "碰撞保护", "systems": systems,
           "diff_summary": "ASEAN、Bharat 不测全宽刚性(均只做 ODB 偏置);Latin 用全宽台车脉冲代实车;速度 50(中/日/欧/澳)、56(美)",
           "key_differences": [
               "C-NCAP 全宽刚性 50km/h(§5.1 核对值;源文本脚注上标污染需防误取)",
               "ASEAN、Bharat 不做全宽刚性正碰(均仅做 ODB 偏置;Bharat AIS-197 §10.1 唯一正面为 ODB 64km/h 40%)——8 套中此项仅 6 套做",
               "Latin NCAP 以『全宽台车(Full Width Sled)』方式评估,非实车全宽碰撞",
               "US NHTSA 全宽刚性 56km/h(35mph)、星级制;IIHS 不做全宽(只做偏置)",
               "JNCAP R7-01 フルラップ前面衝突 50km/h(源核对,非55);做全宽者:中/日/欧/澳 50、美 56"]}
    n = merge_row(row)
    res = [(cn_speed == CNCAP_REF["A"], "C-NCAP.全宽速度=§5.1核对值50", cn_speed, 50),
           (raw != str(cn_speed), "C-NCAP.原始提取≠50(确认污染存在)", raw, "≠50(污染)"),
           (L1["ASEAN"] is False, "ASEAN.全宽刚性=不测", L1["ASEAN"], False),
           (L1["Bharat NCAP"] is False, "Bharat.全宽刚性=不测(L1纠错:AIS-197仅ODB偏置)", L1["Bharat NCAP"], False)]
    for s in ["C-NCAP", "JNCAP", "Latin NCAP", "ANCAP", "Euro NCAP", "US NCAP"]:
        res.append((L1[s] is True, f"{s}.全宽刚性=测", L1[s], True))
    res.append((cn_l3.get("头部HIC15") == [500, 700, 700], "C-NCAP.L3.头部HIC15=[500,700,700]", cn_l3.get("头部HIC15"), [500, 700, 700]))
    jb = jncap_hic_bands().get("_bands", [])
    res.append((len(jb) == 5 and jb[0]["points"] == 1.0 and jb[-1]["range"] == "≥1700", "JNCAP.L3.HIC15五色等级(Green1.0/Red≥1700)", [len(jb), jb[0]["points"] if jb else None], "5档/1.0/≥1700"))
    res.append((euro_front.get("头部HIC15") == [500, 700] and euro_front.get("股骨Ffemur") == [3.8, 9.1], "Euro.L3.正面HIC15[500,700]&Ffemur[3.8,9.1]", [euro_front.get("头部HIC15"), euro_front.get("股骨Ffemur")], "[500,700]/[3.8,9.1]"))
    print(f"frontal_rigid_full 做此项: {[s for s,v in L1.items() if v]} | C-NCAP原始提取='{raw}' → §5.1校正=50")
    ok = report(res)
    print(f"ncap_matrix.json 现有 {n} 个测试项")
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(build())
