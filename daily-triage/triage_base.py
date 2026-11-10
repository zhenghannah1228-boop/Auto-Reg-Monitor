#!/usr/bin/env python3
"""
Daily 0all/0error triage script (reconstructed after container reset, 2026-11-10).
Usage: python3.13 -I triage_base.py <DATE_TAG> <file1.xlsx> [file2.xlsx]

Classification pipeline, in order, per CLAUDE.md section 7.2:
  1. Permanent exclude (fixed noisy domains / link patterns) -> 永久排除
  2. Already in historical baseline (same Link seen in an earlier day's 0all file) -> 基准重复
  3. EXCLUDE regex hit (obviously unrelated topic)
       - EXCLUDE hit and KW NOT hit -> 剔除
       - EXCLUDE hit AND KW also hit -> flagged for human review (kept in 纳入 list, marked)
  4. KW regex hit (admission-related) -> 纳入
  5. BACKUP_KW regex hit (peripheral: tariff/recall/subsidy) -> 备查
  6. Nothing matched -> 剔除 (NO_MATCH)
"""
import sys
import re
import glob
import os
import openpyxl

DATA_DIR = "/home/user/Auto-Reg-Monitor/daily-triage/data"

# ---- Permanent exclude: known noisy domains / link patterns ----
PERMANENT_EXCLUDE_DOMAINS = ["dominica.gov.dm", "motl.gov.et"]
PERMANENT_EXCLUDE_LINK_SUBSTR = ["DocDate="]

# ---- KW: admission-related regex (word-boundaried for short acronyms) ----
KW_PATTERNS = [
    r"\bvehicle", r"\bmotor vehicle", r"\bvehicles\b",
    r"\bUN\s*R\s*\d+", r"\bECE\b", r"\bUNECE\b", r"\bWP\.?29\b",
    r"\bGRVA\b", r"\bGRSG\b", r"\bGRPE\b", r"\bGRBP\b", r"\bGRE\b",
    r"\bADS\b", r"\bADAS\b", r"\bAEBS\b", r"\bCLIV\b", r"\bEDR\b", r"\bDSSAD\b",
    r"\bAVSR\b", r"\bTFCS\b", r"\bSLR\b", r"\bIWVTA\b", r"\bDETA\b", r"\bEqOP\b",
    r"\bPMP\b", r"\bEDO\b",
    r"\btyre", r"\btire", r"\bbrake", r"\bemission", r"\belectric vehicle",
    r"\bautonomous", r"\btype[\s-]approval", r"\btype approval",
    r"\bcertification\b", r"\bhomologation\b",
    r"\brecalls?\b",
    r"型式批准", r"整车", r"汽车", r"机动车", r"车辆",
]
KW_RE = re.compile("|".join(KW_PATTERNS), re.IGNORECASE)

# ---- EXCLUDE: clearly unrelated topics ----
EXCLUDE_PATTERNS = [
    r"\bfood\b", r"\baviation\b", r"\brailway\b", r"\belections?\b",
    r"\binsurance\b", r"\bhousing\b", r"\bbuilding bye[\s-]?law",
    r"\bcantonment\b", r"\bbudget performance\b", r"\bhorizon europe\b",
    r"\bcomitology\b", r"\bfisher(y|ies)\b", r"\bmaritime\b", r"\bdrug\b",
    r"\btourism\b",
]
EXCLUDE_RE = re.compile("|".join(EXCLUDE_PATTERNS), re.IGNORECASE)

# ---- BACKUP_KW: peripheral (tariff/incentive/recall-adjacent) ----
BACKUP_KW_PATTERNS = [
    r"\btariff\b", r"关税", r"补贴", r"\bincentive\b", r"\bsubsidy\b",
]
BACKUP_KW_RE = re.compile("|".join(BACKUP_KW_PATTERNS), re.IGNORECASE)


def read_rows(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    if not rows:
        return []
    header = [str(h) if h is not None else "" for h in rows[0]]
    try:
        link_idx = header.index("Link")
    except ValueError:
        return []
    date_idx = header.index("Date") if "Date" in header else None
    subject_idx = header.index("Subject") if "Subject" in header else None
    country_idx = header.index("国家") if "国家" in header else None

    out = []
    for r in rows[1:]:
        if link_idx >= len(r):
            continue
        link = r[link_idx]
        if not link:
            continue
        out.append({
            "link": str(link).strip(),
            "date": r[date_idx] if date_idx is not None and date_idx < len(r) else None,
            "subject": r[subject_idx] if subject_idx is not None and subject_idx < len(r) else "",
            "country": r[country_idx] if country_idx is not None and country_idx < len(r) else "",
        })
    return out


def build_baseline(date_tag, current_files):
    current_basenames = {os.path.basename(f) for f in current_files}
    baseline = set()
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "0all*.xlsx")))
    for f in all_files:
        if os.path.basename(f) in current_basenames:
            continue
        try:
            rows = read_rows(f)
        except Exception:
            continue
        for row in rows:
            baseline.add(row["link"])
    return baseline


def is_permanent_excluded(link):
    for d in PERMANENT_EXCLUDE_DOMAINS:
        if d in link:
            return True
    for s in PERMANENT_EXCLUDE_LINK_SUBSTR:
        if s in link:
            return True
    return False


def classify(row, baseline):
    link = row["link"]
    subject = row["subject"] or ""

    if is_permanent_excluded(link):
        return "永久排除", None

    if link in baseline:
        return "基准重复", None

    kw_m = KW_RE.search(subject) or KW_RE.search(link)
    ex_m = EXCLUDE_RE.search(subject)

    if ex_m and kw_m:
        return "纳入", {"kw": kw_m.group(0), "conflict": True}
    if ex_m and not kw_m:
        return "剔除", {"reason": ex_m.group(0)}
    if kw_m:
        return "纳入", {"kw": kw_m.group(0), "conflict": False}

    bk_m = BACKUP_KW_RE.search(subject) or BACKUP_KW_RE.search(link)
    if bk_m:
        return "备查", {"kw": bk_m.group(0)}

    return "剔除", {"reason": "NO_MATCH"}


def main():
    if len(sys.argv) < 3:
        print("Usage: triage_base.py <DATE_TAG> <file1.xlsx> [file2.xlsx]")
        sys.exit(1)
    date_tag = sys.argv[1]
    files = sys.argv[2:]

    baseline = build_baseline(date_tag, files)
    print(f"Baseline built: {len(baseline)} unique links from historical files")

    merged = {}
    for i, f in enumerate(files):
        rows = read_rows(f)
        label = chr(ord('A') + i)
        print(f"Source {label} ({f}): {len(rows)} rows with Link")
        for row in rows:
            if row["link"] not in merged:
                merged[row["link"]] = row
    print(f"Merged (deduped): {len(merged)} rows")
    print()

    results = {"纳入": [], "备查": [], "剔除": [], "基准重复": [], "永久排除": []}
    for link, row in merged.items():
        cat, info = classify(row, baseline)
        results[cat].append((row, info))

    print("=== Classification Results ===")
    print(f"纳入 (KW hit): {len(results['纳入'])}")
    print(f"备查 (BACKUP_KW only): {len(results['备查'])}")
    print(f"剔除 (EXCLUDE/NO_MATCH): {len(results['剔除'])}")
    print(f"基准重复: {len(results['基准重复'])}")
    print(f"永久排除: {len(results['永久排除'])}")
    print()

    print("=" * 80)
    print("【纳入】准入相关")
    print("=" * 80)
    by_country = {}
    for row, info in results["纳入"]:
        by_country.setdefault(row["country"] or "未分类", []).append((row, info))
    for country, items in by_country.items():
        print(f"\n## {country} ({len(items)}条)")
        for row, info in items:
            conflict = "  ⚠️KW+EXCLUDE同时命中，需人工复核" if info and info.get("conflict") else ""
            print(f"  - {row['date']} | {row['subject']} [命中: {info['kw']}]{conflict}")
            print(f"    {row['link']}")

    print()
    print("=" * 80)
    print("【备查】外围相关")
    print("=" * 80)
    for row, info in results["备查"]:
        print(f"  - {row['date']} | {row['subject']} [命中: {info['kw']}]")
        print(f"    {row['link']}")

    print()
    print("=" * 80)
    print("【剔除说明】")
    print("=" * 80)
    print(f"共 {len(results['剔除'])} 条剔除:")
    reason_counts = {}
    for row, info in results["剔除"]:
        reason = info["reason"] if info else "?"
        reason_counts.setdefault(reason, []).append(row["country"] or "?")
    for reason, countries in reason_counts.items():
        uniq_countries = sorted(set(countries))
        print(f"  - {reason}: {len(countries)}条 (来源: {', '.join(uniq_countries)})")

    print()
    print(f"基准重复: {len(results['基准重复'])}条")
    print(f"永久排除: {len(results['永久排除'])}条")


if __name__ == "__main__":
    main()
