#!/usr/bin/env python3
"""
美国联邦公报(Federal Register)→ reg_radar + recalls 同步器
抓取 federalregister.gov 官方 API 里 NHTSA + EPA 的汽车相关文件,双路由入库:
- 规则/拟议规则/法规类通知 → reg_radar(19 法规雷达)
- 不合规/缺陷请愿类通知(inconsequential noncompliance / defect petition)→ recalls(16 召回案例)
每条都带 govinfo.gov 官方 PDF 直链(A 档)。

工作原理:
- 官方 API 免 Key、返回 JSON,可按机构(NHTSA/EPA)、日期、类型筛。
- 按发布日窗口拉取,汽车相关性过滤(EPA 必须命中汽车词,滤掉水/空气/化学品噪音;
  两机构都滤掉信息征集、咨询会、Sunshine/Privacy 等纯行政件)。
- 按 document_number 去重、幂等。

- 纯静态站 + Supabase 无后端,本脚本由 GitHub Actions 定时(每周)运行。
- 仅用 Python 标准库;Supabase url + anonKey 从 config.js 解析(anonKey 公开,RLS 全放行)。

用法:
  python tools/federal_register_sync.py                    # 同步最近14天
  python tools/federal_register_sync.py --since 2026-07-01  # 指定起始发布日
  python tools/federal_register_sync.py --dry-run
"""
import re, sys, json, time, argparse, urllib.request, urllib.parse, os
from datetime import datetime, timedelta, timezone

FR_API = "https://www.federalregister.gov/api/v1/documents.json"
AGENCIES = ["national-highway-traffic-safety-administration", "environmental-protection-agency"]
UA = "Mozilla/5.0 (AutoRegMonitor FederalRegisterSync)"

# 汽车相关性关键词(EPA 必须命中其一;NHTSA 默认相关但仍用它辅助归类)
AUTO_KW = re.compile(r'\b(motor vehicle|vehicle|automobile|passenger car|light[- ]duty|heavy[- ]duty|'
    r'FMVSS|tire|tyre|engine|emission|greenhouse gas|tailpipe|fuel econom|CAFE|ZEV|'
    r'electric vehicle|\bEV\b|battery electric|EDR|ADS|automated driving|advanced driver|'
    r'brake|airbag|air bag|seat belt|occupant|crash|glazing|lighting|odometer)\b', re.I)
# 纯行政噪音(滤除)
NOISE_KW = re.compile(r'(information collection|paperwork reduction|advisory (council|committee)|'
    r'sunshine act|privacy act|meeting of the|request for nominations|'
    r'agency information|national emergency medical)', re.I)
# 召回/不合规请愿类(路由到 recalls)
RECALL_KW = re.compile(r'(inconsequential noncompliance|defect petition|noncompliance|'
    r'(grant|denial|receipt) of petition|petition for (a )?decision|safety recall|\brecall\b)', re.I)

def http_get_json(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url} :: {last}")

def cfg():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = open(os.path.join(root, "config.js"), encoding="utf-8").read()
    url = re.search(r'url:\s*"([^"]+)"', txt).group(1).rstrip("/")
    key = re.search(r'anonKey:\s*"([^"]+)"', txt).group(1)
    return url, key

FMVSS_PAT = re.compile(r'FMVSS\s*(?:No\.?\s*)?(\d+[A-Za-z]?)', re.I)
def extract_fmvss(text):
    seen = []
    for n in FMVSS_PAT.findall(text or ""):
        v = "FMVSS " + n.upper()
        if v not in seen: seen.append(v)
    return " & ".join(seen) if seen else None

def fetch_fr(since, until):
    docs, page = [], 1
    while True:
        q = [("per_page", "100"), ("page", str(page)), ("order", "newest"),
             ("conditions[publication_date][gte]", since),
             ("conditions[publication_date][lte]", until)]
        for a in AGENCIES:
            q.append(("conditions[agencies][]", a))
        for f in ("document_number", "title", "type", "abstract", "publication_date",
                  "effective_on", "html_url", "pdf_url", "agencies", "citation"):
            q.append(("fields[]", f))
        data = http_get_json(FR_API + "?" + urllib.parse.urlencode(q))
        res = data.get("results") or []
        docs += res
        if not res or page >= (data.get("total_pages") or 1) or page >= 15:
            break
        page += 1; time.sleep(0.3)
    return docs

# EPA 固定源/区域大气计划(排除,非汽车)
EPA_STATIONARY = re.compile(r'(air plan|implementation plan|\bSIP\b|state plan|redesignation|'
    r'nonattainment|attainment|NESHAP|hazardous air pollutant|incinerat|plywood|solid waste|'
    r'ozone area|PM2\.?5|maintenance plan|regional haze|source-specific|title V|'
    r'negative declaration|designated facilit)', re.I)
# EPA 交通口(机动车/发动机排放,才收)
EPA_TRANSPORT = re.compile(r'(motor vehicle|light[- ]duty vehicle|heavy[- ]duty (vehicle|engine|truck)|'
    r'nonroad|greenhouse gas.{0,30}(vehicle|engine|standard)|tailpipe|vehicle emission|'
    r'engine.{0,20}(emission|certif)|\bTier [34]\b|nonconformance penalt|\bZEV\b|'
    r'electric vehicle|fuel econom|\bCAFE\b|evaporative emission|onboard diagnostic|'
    r'renewable fuel|clean vehicle|corporate average fuel|light[- ]duty truck)', re.I)

def is_auto(d):
    blob = (d.get("title") or "") + " " + (d.get("abstract") or "")
    if NOISE_KW.search(blob):
        return False
    ag = " ".join(a.get("slug", "") for a in (d.get("agencies") or []))
    if "environmental-protection-agency" in ag and "national-highway" not in ag:
        # EPA:必须命中交通口 且 非固定源/区域大气计划
        return bool(EPA_TRANSPORT.search(blob)) and not EPA_STATIONARY.search(blob)
    return bool(AUTO_KW.search(blob)) or "national-highway" in ag  # NHTSA 默认收

def dims_radar(blob):
    t = blob.lower(); d = [1]
    if re.search(r'emission|greenhouse gas|tailpipe|clean air|criteria pollutant', t): d.append(2)
    if re.search(r'electric vehicle|battery|\bzev\b|\bev\b|charg', t): d.append(4)
    if re.search(r'cybersecur|software update', t): d.append(6)
    if re.search(r'\bads\b|automated driving|advanced driver|\baeb\b|automatic emergency|lane', t): d.append(7)
    if re.search(r'\blabel|placard|odometer', t): d.append(8)
    return sorted(set(d))

def dims_recall(blob):
    t = blob.lower(); d = [0]
    if re.search(r'high[- ]voltage|traction battery|lithium', t): d.append(3)
    if re.search(r'camera|automated driving|\bads\b|stability control|automatic emergency', t): d.append(6)
    if re.search(r'\blabel|placard', t): d.append(7)
    return sorted(set(d))

STAGE = {"Rule": "已发布(终规)", "Proposed Rule": "拟议规则(NPRM)", "Notice": "通知"}

def agency_label(d):
    ag = " ".join(a.get("slug", "") for a in (d.get("agencies") or []))
    if "national-highway" in ag: return "NHTSA"
    if "environmental-protection-agency" in ag: return "EPA"
    return (d.get("agencies") or [{}])[0].get("name", "")[:40]

def map_radar(d):
    blob = (d.get("title") or "") + " " + (d.get("abstract") or "")
    lab = agency_label(d)
    return {
        "collected_date": None,  # 运行时填
        "region": "北美", "country": "美国",
        "agency": f"{lab}(美国联邦公报)",
        "title": f"[{lab}] " + (d.get("title") or "")[:220],
        "summary": (re.sub(r'\s+', ' ', d.get("abstract") or d.get("title") or "").strip())[:1500],
        "stage": STAGE.get(d.get("type"), d.get("type") or ""),
        "topics": [d.get("type") or "", lab, "联邦公报"],
        "dims": dims_radar(blob),
        "tbt_no": None,
        "source_url": d.get("pdf_url") or d.get("html_url"),
        "source_name": f"美国联邦公报 Federal Register · 文号 {d.get('document_number')} · {d.get('citation') or ''}".strip(" ·"),
        "pub_date": d.get("publication_date"),
        "effective_date": d.get("effective_on"),
        "search_kw": f"Federal Register {d.get('document_number')} {lab} " + (extract_fmvss(blob) or ""),
        "confidence": "待核实",
        "status": "待确认",
        "note": f"联邦公报自动同步·{d.get('document_number')}",
        "_docnum": d.get("document_number"),
    }

def map_recall(d):
    title = d.get("title") or ""
    blob = title + " " + (d.get("abstract") or "")
    m = re.match(r'^(.*?),?\s+(Grant|Denial|Receipt|Notice) of (?:Receipt of )?Petition', title)
    oems = (m.group(1) if m else title.split(",")[0]).strip()[:200]
    if re.search(r'\bdenial of petition', title, re.I): status = "不合规请愿被否(须整改/召回)"
    elif re.search(r'\bgrant of petition', title, re.I): status = "不合规请愿获批(免召回)"
    elif re.search(r'\breceipt of petition', title, re.I): status = "不合规请愿受理(待决)"
    else: status = "缺陷/不合规请愿"
    return {
        "country": "美国", "agency": "美国NHTSA · 联邦公报(不合规/缺陷请愿)",
        "oems": oems, "models": "",
        "recall_date": d.get("publication_date"),
        "mandatory": False, "status": status,
        "reason": (re.sub(r'\s+', ' ', d.get("abstract") or title).strip())[:1200],
        "reg_ref": extract_fmvss(blob), "refs": [],
        "dims": dims_recall(blob), "units": "", "remedy": "",
        "source_url": d.get("pdf_url") or d.get("html_url"),
        "note": (f"美国联邦公报 · 文号 {d.get('document_number')} · 不合规/缺陷请愿 · 联邦公报自动同步")[:900],
        "_docnum": d.get("document_number"),
    }

def sb_existing(base, key, path, like):
    like = urllib.parse.quote(like, safe="=.*&")
    url = base + f"/rest/v1/{path}?{like}&select=note,source_url"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    nums = set()
    for x in rows:
        for f in (x.get("note") or "", x.get("source_url") or ""):
            for mnum in re.findall(r'(\d{4}-\d{4,6})', f):
                nums.add(mnum)
    return nums

def sb_insert(base, key, path, rows):
    body = json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]).encode()
    req = urllib.request.Request(base + f"/rest/v1/{path}", data=body, method="POST",
        headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="起始发布日 YYYY-MM-DD(默认14天前)")
    ap.add_argument("--until", help="截止发布日 YYYY-MM-DD(默认今天)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    today = datetime.now(timezone.utc).date()
    since = args.since or str(today - timedelta(days=14))
    until = args.until or str(today)
    coll = str(today)

    base, key = cfg()
    docs = [d for d in fetch_fr(since, until) if is_auto(d)]
    print(f"联邦公报 {since}~{until} 汽车相关文件 {len(docs)} 篇")

    radar, recalls = [], []
    for d in docs:
        blob = (d.get("title") or "") + " " + (d.get("abstract") or "")
        if RECALL_KW.search(blob):
            recalls.append(map_recall(d))
        else:
            r = map_radar(d); r["collected_date"] = coll; radar.append(r)

    if not args.dry_run:
        ex_r = sb_existing(base, key, "reg_radar", "note=like.*联邦公报自动同步*")
        ex_c = sb_existing(base, key, "recalls", "note=like.*联邦公报自动同步*")
        radar = [x for x in radar if x["_docnum"] not in ex_r]
        recalls = [x for x in recalls if x["_docnum"] not in ex_c]
    # 批内去重
    def dedup(rows):
        seen, out = set(), []
        for r in rows:
            if r["_docnum"] in seen: continue
            seen.add(r["_docnum"]); out.append(r)
        return out
    radar, recalls = dedup(radar), dedup(recalls)

    print(f"→ 法规雷达 reg_radar 新增 {len(radar)} 篇;召回案例 recalls 新增 {len(recalls)} 篇")
    if args.dry_run:
        for r in radar[:15]: print("  [雷达]", r["pub_date"], r["stage"], "|", r["title"][:75])
        for r in recalls[:15]: print("  [召回]", r["recall_date"], r["status"], "|", r["oems"], "|", r["reason"][:50])
        return
    for i in range(0, len(radar), 20): sb_insert(base, key, "reg_radar", radar[i:i+20])
    for i in range(0, len(recalls), 20): sb_insert(base, key, "recalls", recalls[i:i+20])
    print(f"已写入:reg_radar {len(radar)} 篇、recalls {len(recalls)} 篇。")

if __name__ == "__main__":
    main()
