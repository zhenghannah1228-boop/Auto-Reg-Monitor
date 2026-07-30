#!/usr/bin/env python3
"""
法规雷达每日自动扫集 — daily_radar_scan.py

每日东八区零点 (UTC 16:00) 由 GitHub Actions 触发,
扫前一天各主要来源发布的汽车准入类法规, 写入:
  reg_radar   — 新法规条目(note 字段含唯一源 ID, 幂等)
  scan_runs   — 本次运行日志
  scan_matrix — 有新发现的国家更新扫集状态格(仅更新已有行)

数据源:
  A | 美国联邦公报 Federal Register   (federalregister.gov/api)
  A | 欧盟 EUR-Lex SPARQL             (publications.europa.eu/webapi/rdf/sparql)
  A | 英国 legislation.gov.uk         (Atom feed for SIs)
  B | UNECE 新闻 RSS                   (unece.org)

用法:
  python tools/daily_radar_scan.py                      # 昨天
  python tools/daily_radar_scan.py --date 2026-07-28   # 指定日期
  python tools/daily_radar_scan.py --dry-run            # 不写库,仅打印
"""

import re, sys, json, time, argparse, urllib.request, urllib.parse, os
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (AutoRegMonitor DailyRadarScan/1.0)"


# ── 通用工具 ──────────────────────────────────────────────────────────────────

def http_get(url, headers=None, tries=4, timeout=60):
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(2 ** i)
    print(f"  [WARN] GET 失败({tries}次): {url[:80]} :: {last}", file=sys.stderr)
    return None


def http_post(url, body_bytes, headers=None, tries=4, timeout=90):
    hdrs = {"User-Agent": UA, "Content-Type": "application/octet-stream"}
    if headers:
        hdrs.update(headers)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body_bytes, method="POST", headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(2 ** i)
    print(f"  [WARN] POST 失败({tries}次): {url[:80]} :: {last}", file=sys.stderr)
    return None


def cfg():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = open(os.path.join(root, "config.js"), encoding="utf-8").read()
    url = re.search(r'url:\s*"([^"]+)"', txt).group(1).rstrip("/")
    key = re.search(r'anonKey:\s*"([^"]+)"', txt).group(1)
    return url, key


# ── 维度推断(1-10, 1-based) ───────────────────────────────────────────────────

_DIMS_RULES = [
    (1,  re.compile(r'\b(type[- ]approv|WVTA|IWVTA|road.worthiness|IVA\b|FMVSS|整车|型式批准|准入|TRIAS|homologat)', re.I)),
    (2,  re.compile(r'\b(emission|exhaust|greenhouse gas|tailpipe|fuel econom|CAFE|Euro[- ][4-7]|Tier\s*[34]|clean air|\bCO2\b|排放|节能|环保|碳)', re.I)),
    (3,  re.compile(r'\b(radio|spectrum|\bRF\b|wireless|electromagnetic|\bRED\b|\bFCC\b|型式.*无线|射频|无线电|电磁兼容)', re.I)),
    (4,  re.compile(r'\b(battery|charg|traction|\bEV\b|electric vehicle|BEV|PHEV|high[- ]voltage|储能|充电|电池|新能源)', re.I)),
    (5,  re.compile(r'\b(subsid|incentive|purchas.*credit|tax credit|EV.*grant|补贴|激励|奖励)', re.I)),
    (6,  re.compile(r'\b(cybersecur|software update|\bOTA\b|data protect|UN\s*R155|UN\s*R156|网络安全|信息安全|数据安全)', re.I)),
    (7,  re.compile(r'\b(ADAS|automated driv|autonomous|\bAEB\b|automatic emergency|lane.keep|lane.depart|自动驾驶|智能网联|辅助驾驶)', re.I)),
    (8,  re.compile(r'\b(label|marking|plate|placard|\bVIN\b|标识|标签|铭牌)', re.I)),
    (9,  re.compile(r'\b(registrat|import.*vehicle|vehicle.*import|custom|duty|tariff|注册|登记|上牌|关税|进口)', re.I)),
    (10, re.compile(r'\b(tool.kit|spare.wheel|\bjack\b|first.aid|随车工具|随车备品)', re.I)),
]

def infer_dims(blob):
    dims = [d for d, pat in _DIMS_RULES if pat.search(blob)]
    return sorted(set(dims)) or [1]


# ── 数据源 A: 美国联邦公报 ────────────────────────────────────────────────────

FR_API      = "https://www.federalregister.gov/api/v1/documents.json"
FR_AGENCIES = ["national-highway-traffic-safety-administration",
               "environmental-protection-agency"]

_FR_AUTO_KW = re.compile(
    r'\b(motor vehicle|vehicle|automobile|passenger car|light[- ]duty|heavy[- ]duty|'
    r'FMVSS|tire|tyre|engine|emission|greenhouse gas|tailpipe|fuel econom|CAFE|ZEV|'
    r'electric vehicle|\bEV\b|battery electric|EDR|ADS|automated driving|advanced driver|'
    r'brake|airbag|air bag|seat belt|occupant|crash|glazing|lighting|odometer)\b', re.I)
_FR_NOISE   = re.compile(
    r'(information collection|paperwork reduction|advisory (council|committee)|'
    r'sunshine act|privacy act|meeting of the|request for nominations|'
    r'agency information|national emergency medical)', re.I)
_EPA_STAT   = re.compile(
    r'(air plan|implementation plan|\bSIP\b|state plan|redesignation|nonattainment|'
    r'NESHAP|hazardous air|incinerat|solid waste|ozone area|PM2\.?5|maintenance plan|'
    r'regional haze|title V|negative declaration)', re.I)
_EPA_TRANS  = re.compile(
    r'(motor vehicle|light[- ]duty vehicle|heavy[- ]duty|nonroad|'
    r'greenhouse gas.{0,30}(vehicle|engine)|tailpipe|vehicle emission|'
    r'engine.{0,20}(emission|certif)|\bTier [34]\b|nonconformance penalt|\bZEV\b|'
    r'electric vehicle|fuel econom|\bCAFE\b|evaporative emission|onboard diagnostic|'
    r'renewable fuel|clean vehicle)', re.I)
_FR_STAGE   = {"Rule": "已发布(终规)", "Proposed Rule": "拟议规则(NPRM)", "Notice": "通知"}

def _fr_is_auto(d):
    blob = (d.get("title") or "") + " " + (d.get("abstract") or "")
    if _FR_NOISE.search(blob):
        return False
    ag = " ".join(a.get("slug", "") for a in (d.get("agencies") or []))
    if "environmental-protection-agency" in ag and "national-highway" not in ag:
        return bool(_EPA_TRANS.search(blob)) and not _EPA_STAT.search(blob)
    return bool(_FR_AUTO_KW.search(blob)) or "national-highway" in ag

def fetch_federal_register(date_str):
    docs, page = [], 1
    while True:
        q = [("per_page", "100"), ("page", str(page)), ("order", "newest"),
             ("conditions[publication_date][gte]", date_str),
             ("conditions[publication_date][lte]", date_str)]
        for a in FR_AGENCIES:
            q.append(("conditions[agencies][]", a))
        for f in ("document_number", "title", "type", "abstract", "publication_date",
                  "effective_on", "html_url", "pdf_url", "agencies", "citation"):
            q.append(("fields[]", f))
        try:
            text = http_get(FR_API + "?" + urllib.parse.urlencode(q),
                            headers={"Accept": "application/json"})
            data = json.loads(text) if text else {}
        except Exception:
            break
        res = data.get("results") or []
        docs += [d for d in res if _fr_is_auto(d)]
        if not res or page >= (data.get("total_pages") or 1) or page >= 15:
            break
        page += 1
        time.sleep(0.3)

    results = []
    for d in docs:
        blob = (d.get("title") or "") + " " + (d.get("abstract") or "")
        ag   = " ".join(a.get("slug", "") for a in (d.get("agencies") or []))
        lab  = ("NHTSA" if "national-highway" in ag
                else "EPA" if "environmental-protection-agency" in ag else "")
        docnum = d.get("document_number", "")
        results.append({
            "region":       "北美",
            "country":      "美国",
            "agency":       f"{lab}(美国联邦公报)",
            "title":        f"[{lab}] {(d.get('title') or '')[:220]}",
            "summary":      re.sub(r'\s+', ' ', d.get("abstract") or "").strip()[:1500],
            "stage":        _FR_STAGE.get(d.get("type"), d.get("type") or ""),
            "topics":       [d.get("type") or "", lab, "联邦公报"],
            "dims":         infer_dims(blob),
            "source_url":   d.get("pdf_url") or d.get("html_url"),
            "source_name":  f"美国联邦公报 Federal Register · {d.get('citation') or docnum}",
            "pub_date":     d.get("publication_date"),
            "effective_date": d.get("effective_on"),
            "search_kw":    f"Federal Register {docnum} {lab}",
            "note":         f"auto:fr:{docnum}",
        })
    return results


# ── 数据源 B: EUR-Lex SPARQL ──────────────────────────────────────────────────

EURLEX_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"

_EU_AUTO_KW = re.compile(
    r'\b(vehicle|motor|automotive|tyre|emission|type[- ]approv|WVTA|IWVTA|'
    r'electric|battery|charg|cybersecur|automated driv|ADAS|roadworthiness|'
    r'exhaust|fuel|CO2|carbon dioxide|truck|coach|moped|motorcycle|trailer)', re.I)
_EU_NOISE   = re.compile(
    r'(state aid|competition|merger|financial|banking|food safety|'
    r'pharmaceutical|medical device|fishery|agriculture|pesticide|biocide|'
    r'cosmetic|tobacco)', re.I)
_EU_DOCTYPE = {
    "regulation": "已发布(法规)", "directive": "已发布(指令)",
    "decision": "已发布(决定)", "proposal": "拟议(提案)",
    "delegated_regulation": "已发布(委托法规)",
    "implementing_regulation": "已发布(实施法规)",
    "recommendation": "建议", "opinion": "意见",
}

def fetch_eurlex(date_str):
    sparql = (
        "PREFIX eli: <http://data.europa.eu/eli/ontology#>\n"
        "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
        "SELECT DISTINCT ?celex ?title ?doctype WHERE {\n"
        f'  ?work eli:date_publication "{date_str}"^^xsd:date ;\n'
        "        eli:id_local ?celex ;\n"
        "        dcterms:title ?title ;\n"
        "        eli:type_document ?doctype .\n"
        "  FILTER(LANG(?title) = \"en\")\n"
        "}\nLIMIT 300"
    )
    text = http_post(
        EURLEX_SPARQL + "?format=application%2Fsparql-results%2Bjson",
        sparql.encode("utf-8"),
        headers={
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json",
        },
        timeout=120,
    )
    if not text:
        return []
    try:
        data = json.loads(text)
    except Exception:
        return []

    results = []
    for b in (data.get("results") or {}).get("bindings") or []:
        celex   = (b.get("celex") or {}).get("value", "")
        title   = (b.get("title") or {}).get("value", "")
        doctype = (b.get("doctype") or {}).get("value", "").split("/")[-1].split("#")[-1].lower()

        if not _EU_AUTO_KW.search(title):
            continue
        if _EU_NOISE.search(title):
            continue

        stage   = _EU_DOCTYPE.get(doctype, doctype or "已发布")
        oj_url  = (f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}"
                   if celex else None)
        results.append({
            "region":       "欧洲",
            "country":      "欧盟",
            "agency":       "欧盟委员会 European Commission (EUR-Lex)",
            "title":        title[:280],
            "summary":      f"EU官方公报 · CELEX {celex} · {doctype}",
            "stage":        stage,
            "topics":       ["EUR-Lex", "Official Journal", doctype],
            "dims":         infer_dims(title),
            "source_url":   oj_url,
            "source_name":  f"EUR-Lex · CELEX {celex}",
            "pub_date":     date_str,
            "effective_date": None,
            "search_kw":    f"EUR-Lex {celex} {title[:80]}",
            "note":         f"auto:eurlex:{celex}",
        })
    return results


# ── 数据源 C: 英国 legislation.gov.uk Atom ────────────────────────────────────

UK_FEED = "https://www.legislation.gov.uk/new/data.feed"

_UK_AUTO_KW = re.compile(
    r'\b(motor vehicle|road vehicle|type[- ]approv|roadworthiness|MOT test|'
    r'tyre|driving licen|electric vehicle|EV charg|charging point|'
    r'vehicle emission|exhaust|fuel econom|battery|automated vehicle|'
    r'autonomous|vehicle lighting|vehicle brake|speed limit|'
    r'construction and use|whole vehicle|vehicle standard|highway code)', re.I)
_UK_NOISE   = re.compile(
    r'(prohibit.*traffic|temporary.*prohibit|trunk road|'
    r'environmental permit|waste.*transport|transport.*waste|'
    r'finance|tax credit|council|election|school|health care|welfare|pension|'
    r'immigration|planning|housing|benefit|food hygiene|veterinary)', re.I)

def _xml_text(s):
    return re.sub(r'<[^>]+>|<!\[CDATA\[|\]\]>', '', s).strip()

def fetch_uk_legislation(date_str):
    params = urllib.parse.urlencode({
        "type": "uksi", "start-date": date_str, "end-date": date_str,
    })
    text = http_get(UK_FEED + "?" + params, headers={"Accept": "application/atom+xml"})
    if not text:
        return []

    results = []
    for entry in re.findall(r'<entry>(.*?)</entry>', text, re.S):
        title_m   = re.search(r'<title[^>]*>(.*?)</title>', entry, re.S)
        link_m    = re.search(r'<link[^>]+href="([^"]+)"', entry)
        id_m      = re.search(r'<id>(.*?)</id>', entry, re.S)
        summary_m = re.search(r'<summary[^>]*>(.*?)</summary>', entry, re.S)

        title   = _xml_text(title_m.group(1) if title_m else "")
        link    = (link_m.group(1) if link_m else "").strip()
        uid     = _xml_text(id_m.group(1) if id_m else link)
        summary = _xml_text(summary_m.group(1) if summary_m else "")

        if not title:
            continue
        blob = title + " " + summary
        if not _UK_AUTO_KW.search(blob) or _UK_NOISE.search(blob):
            continue

        si_m   = re.search(r'/uksi/(\d{4}/\d+)', link)
        si_num = "UK SI " + si_m.group(1) if si_m else ""
        safe_uid = re.sub(r'https?://[^/]+', '', uid).strip("/")[:80]

        results.append({
            "region":       "欧洲",
            "country":      "英国",
            "agency":       "英国 legislation.gov.uk",
            "title":        title[:280],
            "summary":      (summary or f"UK SI · {si_num}")[:800],
            "stage":        "已发布(SI/法律)",
            "topics":       ["UK SI", "英国立法"],
            "dims":         infer_dims(blob),
            "source_url":   link or f"https://www.legislation.gov.uk/{safe_uid}",
            "source_name":  f"UK legislation.gov.uk · {si_num or title[:60]}",
            "pub_date":     date_str,
            "effective_date": None,
            "search_kw":    f"UK SI {si_num} {title[:80]}",
            "note":         f"auto:uk:{safe_uid}",
        })
    return results


# ── 数据源 D: UNECE 新闻 RSS ──────────────────────────────────────────────────

UNECE_RSS = "https://unece.org/SASSFiles/rss.xml"

_UNECE_AUTO_KW = re.compile(
    r'\b(WP\.?29|vehicle|motor|road transport|type[- ]approv|emission|'
    r'automated|ADAS|cybersecur|\bEV\b|electric|battery|brake|lighting|'
    r'UN\s*R\s*\d|GTR\s*\d|GRVA|GRSP|GRPE|GRBP|GRSG|GRRF|GRE\b)', re.I)

def fetch_unece(date_str):
    text = http_get(UNECE_RSS, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
    if not text:
        return []

    results = []
    for item in re.findall(r'<item>(.*?)</item>', text, re.S):
        title_m  = re.search(r'<title[^>]*>(.*?)</title>', item, re.S)
        link_m   = re.search(r'<link>(.*?)</link>', item, re.S)
        date_m   = re.search(r'<pubDate>(.*?)</pubDate>', item, re.S)
        desc_m   = re.search(r'<description[^>]*>(.*?)</description>', item, re.S)
        guid_m   = re.search(r'<guid[^>]*>(.*?)</guid>', item, re.S)

        title   = _xml_text(title_m.group(1) if title_m else "")
        link    = _xml_text(link_m.group(1) if link_m else "")
        pub_raw = (date_m.group(1) if date_m else "").strip()
        desc    = _xml_text(desc_m.group(1) if desc_m else "")
        guid    = _xml_text(guid_m.group(1) if guid_m else link)

        # Parse RFC 822 pubDate
        pub_date = date_str  # fallback
        try:
            import email.utils as eu
            t = eu.parsedate_to_datetime(pub_raw)
            pub_date = t.strftime("%Y-%m-%d")
        except Exception:
            pass

        if pub_date != date_str:
            continue
        if not title or not _UNECE_AUTO_KW.search(title + " " + desc):
            continue

        safe_guid = re.sub(r'[^a-zA-Z0-9/\-_]', '', guid)[-60:]
        results.append({
            "region":       "国际",
            "country":      "UNECE/WP.29",
            "agency":       "UNECE 联合国欧洲经济委员会",
            "title":        title[:280],
            "summary":      desc[:800],
            "stage":        "国际法规/文件",
            "topics":       ["UNECE", "WP.29", "国际协调"],
            "dims":         infer_dims(title + " " + desc),
            "source_url":   link or None,
            "source_name":  f"UNECE · {title[:80]}",
            "pub_date":     pub_date,
            "effective_date": None,
            "search_kw":    f"UNECE WP.29 {title[:80]}",
            "note":         f"auto:unece:{safe_guid}",
        })
    return results


# ── Supabase 操作 ─────────────────────────────────────────────────────────────

def _sb_req(base, key, method, table, body=None, params=""):
    url = f"{base}/rest/v1/{table}"
    if params:
        url += "?" + params
    hdrs = {
        "apikey": key, "Authorization": "Bearer " + key,
        "Content-Type": "application/json", "Prefer": "return=minimal",
    }
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, r.read().decode()


def _sb_get(base, key, table, params=""):
    url = f"{base}/rest/v1/{table}" + (("?" + params) if params else "")
    hdrs = {"apikey": key, "Authorization": "Bearer " + key,
            "Accept": "application/json"}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def get_existing_notes(base, key):
    rows = _sb_get(base, key, "reg_radar",
                   "select=note&note=like.auto:*&order=created_at.desc&limit=10000")
    return {r["note"] for r in rows if r.get("note")}


def insert_radar_batch(base, key, rows):
    clean = [{k: v for k, v in r.items()} for r in rows]
    for i in range(0, len(clean), 25):
        _sb_req(base, key, "POST", "reg_radar", clean[i:i+25])


def update_scan_matrix(base, key, country_dims, date_str):
    updated = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for country, dims in country_dims.items():
        try:
            rows = _sb_get(base, key, "scan_matrix",
                           f"country=eq.{urllib.parse.quote(country)}&select=cells")
        except Exception:
            continue
        if not rows:
            continue  # country not in scan_matrix — skip

        merged = dict(rows[0].get("cells") or {})
        for d in dims:
            merged[str(d - 1)] = {"s": 1, "note": f"自动扫集 {date_str}"}
        try:
            _sb_req(base, key, "PATCH", "scan_matrix",
                    {"cells": merged, "updated_at": now_iso},
                    f"country=eq.{urllib.parse.quote(country)}")
            updated += 1
        except Exception as e:
            print(f"  [WARN] scan_matrix 更新失败 {country}: {e}", file=sys.stderr)
    return updated


def insert_scan_run(base, key, date_str, new_count, country_dims, src_notes):
    row = {
        "run_date":      date_str,
        "covered_count": len(country_dims),
        "cells_count":   new_count,
        "note":          ("自动扫集 | " + " | ".join(src_notes))[:2000],
        "countries":     ", ".join(sorted(country_dims.keys()))[:2000],
    }
    _sb_req(base, key, "POST", "scan_runs", [row])


# ── 主程序 ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="法规雷达每日自动扫集")
    ap.add_argument("--date",    help="目标日期 YYYY-MM-DD (默认昨天)")
    ap.add_argument("--dry-run", action="store_true", help="不写库,仅打印")
    args = ap.parse_args()

    today    = datetime.now(timezone.utc).date()
    date_str = args.date or str(today - timedelta(days=1))
    print(f"═══ 法规雷达日扫集  目标日期: {date_str}  运行: {today} UTC ═══\n")

    base, key = cfg()

    # ── 各源抓取 ──
    all_items  = []
    src_notes  = []

    for label, fetch_fn, src_tag in [
        ("[1/4] 美国联邦公报 Federal Register",   fetch_federal_register, "FR"),
        ("[2/4] 欧盟 EUR-Lex SPARQL",             fetch_eurlex,            "EU"),
        ("[3/4] 英国 legislation.gov.uk",          fetch_uk_legislation,   "UK"),
        ("[4/4] UNECE 新闻 RSS",                   fetch_unece,            "UNECE"),
    ]:
        print(label + " …")
        try:
            items = fetch_fn(date_str)
        except Exception as e:
            print(f"  [ERROR] {e}", file=sys.stderr)
            items = []
        print(f"      → {len(items)} 条")
        all_items.extend(items)
        src_notes.append(f"{src_tag}{len(items)}条")

    print(f"\n汇总: {len(all_items)} 条原始")

    # ── 去重 ──
    if not args.dry_run:
        existing = get_existing_notes(base, key)
        all_items = [r for r in all_items if r.get("note") not in existing]

    seen, deduped = set(), []
    for r in all_items:
        k = r.get("note", "")
        if k and k in seen:
            continue
        seen.add(k)
        deduped.append(r)
    new_items = deduped

    # 补全默认字段
    for r in new_items:
        r.setdefault("collected_date", date_str)
        r.setdefault("confidence", "待核实")
        r.setdefault("status", "待确认")

    print(f"净新增: {len(new_items)} 条\n")

    if args.dry_run:
        for r in new_items:
            print(f"  [{r.get('country','?')}] {r.get('stage','?')} | {r.get('title','')[:75]}")
        print("\n[dry-run] 不写库。")
        return

    # ── 写入 reg_radar ──
    if new_items:
        print("写入 reg_radar …")
        insert_radar_batch(base, key, new_items)
        print(f"  ✓ {len(new_items)} 条已写入")

    # ── 更新 scan_matrix ──
    country_dims = {}
    for r in new_items:
        c = r.get("country") or ""
        if not c:
            continue
        if c not in country_dims:
            country_dims[c] = set()
        country_dims[c].update(r.get("dims") or [])

    if country_dims:
        print(f"更新 scan_matrix ({len(country_dims)} 个条目) …")
        updated = update_scan_matrix(base, key, country_dims, date_str)
        print(f"  ✓ {updated} 行已更新")

    # ── 写入 scan_runs ──
    print("写入 scan_runs …")
    insert_scan_run(base, key, date_str, len(new_items), country_dims, src_notes)
    print(f"  ✓ scan_runs 日志已写入")

    print(f"\n═══ 完成  日期:{date_str}  新增:{len(new_items)}条  覆盖:{len(country_dims)}个地区 ═══")


if __name__ == "__main__":
    main()
