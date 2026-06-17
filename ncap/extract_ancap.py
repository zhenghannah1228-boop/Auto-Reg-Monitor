"""ANCAP 提取器 — side_impact(概念验证:本批源文件齐全可端到端跑通)。
源:澳洲/ANCAP PROTOCOL - Crash Protection - Side Impact v1.1.pdf
L1/L2 从协议正文+评分表直接拆;L3 ANCAP 采纳 Euro AE-MDB 方法,评分细则待
拉美目录 Euro 原始协议到货后填(标版本),此处先记 status。"""
from extract_common import pdf_text, has, load_sample, assert_eq, report

SIDE_PDF = "澳洲/ANCAP PROTOCOL - Crash Protection - Side Impact v1.1.pdf"

def extract_side_impact():
    t = pdf_text(SIDE_PDF)
    L1 = {
        "可变形壁障侧碰": has(t, r"AE-?MDB"),
        "侧面柱碰": has(t, r"\bpole test\b", r"oblique pole"),
        "远端乘员_乘员互撞": has(t, r"far[- ]side") and has(t, r"occupant[- ]to[- ]occupant"),
    }
    L2 = {
        "假人": ["WorldSID 50th"] if has(t, r"WorldSID\s*50") else [],
        "座椅排": "前排+后排" if has(t, r"rear passenger") else "前排",
        "壁障": "MDB + Pole" if (has(t, r"AE-?MDB") and has(t, r"\bpole\b")) else None,
    }
    return {
        "version": "v1.1 / Overall v10.0",
        "source_files": [SIDE_PDF, "拉美/Euro NCAP – AE-MDB Side Impact Testing Protocol v8.3 Dec 2023.pdf(待到货)"],
        "L1_subtests": L1,
        "L2_params": {**L2, "_extraction_note": "采纳Euro方法(协议插图标注 reproduced from Euro NCAP);评分表见协议:AE-MDB 15/Pole 10/Far side 10/Occupant-to-Occupant"},
        "L3_thresholds": {"_source": "采纳Euro AE-MDB v8.3", "_status": "SOURCE_PENDING_NEXT_BATCH"},
    }

def main():
    got = extract_side_impact()
    print("ANCAP side_impact 提取结果:")
    print("  L1:", got["L1_subtests"])
    print("  L2:", {k: v for k, v in got["L2_params"].items() if not k.startswith("_")})
    # 回归断言:L1 三项必须与 sample.json 完全一致
    want = load_sample()["systems"]["ANCAP"]
    res = []
    assert_eq("ANCAP.L1", got["L1_subtests"], want["L1_subtests"], res)
    assert_eq("ANCAP.L2", {"假人": got["L2_params"]["假人"]}, {"假人": want["L2_params"]["假人"]}, res)
    print()
    ok = report(res)
    return 0 if ok else 1

if __name__ == "__main__":
    import sys; sys.exit(main())
