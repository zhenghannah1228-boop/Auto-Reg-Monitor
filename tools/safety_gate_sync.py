#!/usr/bin/env python3
"""
EU Safety Gate (RAPEX) → recalls 同步器
抓取欧盟消费品快速预警系统的每周报告,筛出「Motor vehicles(机动车)」类预警,
映射为召回记录并按 caseNumber/来源URL 去重后写入 Supabase recalls 表。

- 纯静态站 + Supabase,无后端;本脚本由 GitHub Actions 定时(每周)运行。
- 只用 Python 标准库(GH Actions runner 无需 pip 安装)。
- Supabase url + anonKey 从仓库根的 config.js 解析(anonKey 本就是公开的,RLS 全放行)。

用法:
  python tools/safety_gate_sync.py --weeks 8            # 同步最近 8 期报告的车辆预警
  python tools/safety_gate_sync.py --weeks 8 --dry-run  # 只打印映射结果,不写库
"""
import re, sys, json, time, argparse, urllib.request, urllib.error, os

LIST_URL = "https://ec.europa.eu/safety-gate-alerts/api/download/weeklyReport/list/xml/en"
UA = "Mozilla/5.0 (AutoRegMonitor SafetyGateSync)"

def http_get(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/xml"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e; time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url} :: {last}")

def cfg():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = open(os.path.join(root, "config.js"), encoding="utf-8").read()
    url = re.search(r'url:\s*"([^"]+)"', txt).group(1).rstrip("/")
    key = re.search(r'anonKey:\s*"([^"]+)"', txt).group(1)
    return url, key

def cdata(tag, block):
    m = re.search(rf'<{tag}>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</{tag}>', block, re.S)
    return (m.group(1).strip() if m else "")

def ddmmyyyy_to_iso(s):
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', s or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""

REF_PATS = [r'UN\s?R\s?\d+', r'ECE\s?R\s?\d+', r'Regulation\s*\(E[UC]\)\s*(?:No\s*)?\d+/?\d*',
            r'FMVSS\s?\d+', r'GTR\s?\d+', r'\bEN\s?\d{2,5}(?:-\d+)?\b']
def extract_refs(text):
    out = []
    for p in REF_PATS:
        for m in re.findall(p, text or "", re.I):
            v = re.sub(r'\s+', ' ', m).strip()
            if v not in out: out.append(v)
    return out[:8]

def measure_summary(measures):
    cats = re.findall(r'Category of measure\(s\):\s*([^A-Z]*[A-Za-z ,/()-]+?)(?=Type of|Date of|$)', measures or "")
    cats = [c.strip().rstrip(".") for c in cats if c.strip()]
    seen = []
    for c in cats:
        if c not in seen: seen.append(c)
    return " / ".join(seen)

def map_alert(a, report_iso, report_ref):
    case = cdata("caseNumber", a)
    ref_m = re.search(r'<reference>\s*<!\[CDATA\[(.*?)\]\]>', a, re.S)
    src = (ref_m.group(1).strip() if ref_m else "")
    brand = cdata("brand", a) or "(未标注)"
    name = cdata("name", a); model = cdata("type_numberOfModel", a)
    risk = cdata("riskType", a); danger = cdata("danger", a)
    measures = cdata("measures", a); remedy = measure_summary(measures)
    ncountry = cdata("notifyingCountry", a); origin = cdata("countryOfOrigin", a)
    level = cdata("level", a); code = cdata("companyRecallCode", a)
    mandatory = bool(re.search(r'compulsor|ordered by', measures, re.I))
    models = " · ".join(x for x in [name, ("" if model.lower() in ("individual approval", "") else model)] if x)
    reason = (f"{risk}:{danger}" if risk else danger).strip()
    note = ("欧盟 Safety Gate 每周自动同步 · 案号 " + case +
            (f" · 危险 {risk}" if risk else "") + (f" · {level}" if level else "") +
            (f" · 通报国 {ncountry}" if ncountry else "") + (f" · 原产国 {origin}" if origin else "") +
            (f" · 厂家召回码 {code}" if code else "") + f" · {report_ref}")
    return {
        "country": "欧盟", "agency": "欧盟 Safety Gate(RAPEX)" + (f" · 通报国 {ncountry}" if ncountry else ""),
        "oems": brand, "recall_date": report_iso, "mandatory": mandatory,
        "status": "强制召回" if mandatory else "自愿召回",
        "reason": reason[:1200], "reg_ref": None, "refs": extract_refs(danger),
        "dims": [0], "models": models[:300], "units": "",
        "remedy": remedy[:400], "source_url": src, "note": note[:900],
        "_case": case,
    }

def sb_get_existing_urls(base, key):
    url = base + "/rest/v1/recalls?source_url=like.*safety-gate-alerts*&select=source_url,note"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    urls = set(x.get("source_url") for x in rows if x.get("source_url"))
    cases = set()
    for x in rows:
        m = re.search(r'案号\s*(SR/\d+/\d+)', x.get("note") or "")
        if m: cases.add(m.group(1))
    return urls, cases

def sb_insert(base, key, rows):
    body = json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]).encode()
    req = urllib.request.Request(base + "/rest/v1/recalls", data=body, method="POST",
        headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=8, help="同步最近 N 期周报(默认 8)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base, key = cfg()
    lst = http_get(LIST_URL)
    reports = re.findall(r'<weeklyReport>(.*?)</weeklyReport>', lst, re.S)
    picks = []
    for wr in reports[:args.weeks]:
        ref = cdata("reference", wr)
        url = re.sub(r'&amp;', '&', (re.search(r'<URL>([^<]*)</URL>', wr) or [None, ""])[1] if False else re.search(r'<URL>([^<]*)</URL>', wr).group(1))
        pub = ddmmyyyy_to_iso(cdata("publicationDate", wr))
        picks.append((ref, url, pub))

    existing_urls, existing_cases = (set(), set()) if args.dry_run else sb_get_existing_urls(base, key)
    new_rows = []
    for ref, url, pub in picks:
        try:
            xml = http_get(url)
        except Exception as e:
            print(f"[warn] report {ref} fetch failed: {e}", file=sys.stderr); continue
        alerts = re.findall(r'<notifications\b.*?</notifications>', xml, re.S)
        veh = [a for a in alerts if re.search(r'<category>\s*<!\[CDATA\[Motor vehicles\]\]>', a)]
        for a in veh:
            row = map_alert(a, pub, ref)
            if not row["source_url"]:
                continue
            if row["source_url"] in existing_urls or row["_case"] in existing_cases:
                continue
            existing_urls.add(row["source_url"]); existing_cases.add(row["_case"])
            new_rows.append(row)
        print(f"report {ref} ({pub}): {len(veh)} vehicle alert(s)")

    print(f"\n新增 {len(new_rows)} 条(去重后)")
    if args.dry_run:
        for r in new_rows[:12]:
            print(json.dumps({k: r[k] for k in ("oems", "models", "recall_date", "status", "reason")}, ensure_ascii=False)[:200])
        return
    for i in range(0, len(new_rows), 25):
        sb_insert(base, key, new_rows[i:i+25])
    print(f"已写入 recalls 表 {len(new_rows)} 条。")

if __name__ == "__main__":
    main()
