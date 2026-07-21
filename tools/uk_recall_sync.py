#!/usr/bin/env python3
"""
英国 DVSA(驾驶与车辆标准局)机动车安全召回 → recalls 同步器
抓取 GOV.UK「Check if a vehicle has been recalled」服务(服务端渲染,纯 stdlib 可解析),
遍历 品牌 → 车型 → /recalls(年份可跳过),按召回编号 R/YYYY/NNN 去重后写入 Supabase recalls 表。
16 召回案例页会自动显示新记录。

- 该服务无批量/最近视图、无公开 API,但页面是渐进增强(带 cookie 即返回完整 HTML),
  且 /make/{品牌}/model/{车型}/recalls 一次给出该车型全部召回(内联:编号/日期/类型/原因/
  处理方式/影响车辆数)。故用「品牌×车型」遍历实现同步。
- 默认只收近两年(--min-year,默认当前年-1)以聚焦"新召回"、控制请求量与礼貌度;
  默认精选主流 OEM + 中国品牌(约60家),--full 遍历全部 396 个品牌。
- 纯静态站+Supabase 无后端,本脚本由 GitHub Actions 定时(每周)运行;仅用 Python 标准库。
- Supabase url + anonKey 从 config.js 解析(anonKey 公开,RLS 全放行)。

用法:
  python tools/uk_recall_sync.py                 # 精选品牌、近两年
  python tools/uk_recall_sync.py --dry-run
  python tools/uk_recall_sync.py --full          # 全部品牌
  python tools/uk_recall_sync.py --min-year 1990 # 含历史
"""
import re, sys, json, time, argparse, os, html, http.cookiejar
import urllib.request, urllib.parse
from datetime import datetime, timezone

BASE = "https://www.check-vehicle-recalls.service.gov.uk"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
# 精选品牌关键词(主流乘用/商用 OEM + 中国品牌);实际以 make 列表中匹配到的确切名为准
CURATED = re.compile(r'\b(FORD|VAUXHALL|VOLKSWAGEN|AUDI|BMW|MERCEDES|TOYOTA|LEXUS|NISSAN|HONDA|'
    r'HYUNDAI|\bKIA\b|PEUGEOT|CITROEN|RENAULT|DACIA|SKODA|SEAT|CUPRA|VOLVO|POLESTAR|JAGUAR|LAND ROVER|'
    r'MINI|FIAT|ALFA ROMEO|ABARTH|JEEP|MAZDA|SUZUKI|MITSUBISHI|SUBARU|TESLA|PORSCHE|SMART|\bDS\b|'
    r'BYD|GREAT WALL|\bMG \b|MG MOTOR|MAXUS|\bLDV\b|OMODA|JAECOO|CHERY|GENESIS|INEOS|'
    r'BENTLEY|ASTON MARTIN|MASERATI|FERRARI|LAMBORGHINI|ROLLS-ROYCE|MCLAREN|'
    r'IVECO|SCANIA|\bMAN\b|\bDAF\b)', re.I)

def cfg():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = open(os.path.join(root, "config.js"), encoding="utf-8").read()
    url = re.search(r'url:\s*"([^"]+)"', txt).group(1).rstrip("/")
    key = re.search(r'anonKey:\s*"([^"]+)"', txt).group(1)
    return url, key

def make_opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept", "text/html")]
    return op

def get(op, url, tries=4, timeout=45):
    last = None
    for i in range(tries):
        try:
            with op.open(url, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e; time.sleep(1.2 * (i + 1))
    raise RuntimeError(f"GET failed: {url} :: {last}")

def q(seg):
    return urllib.parse.quote(seg, safe="")

def options(h):
    return [o for o in re.findall(r'<option[^>]*value="([^"]+)"', h) if o and o != "_unused"]

RECALL_RE = re.compile(
    r'@@(?P<concern>(?:(?!@@).)*?)@@\s*'
    r'@@Recall number@@\s*(?P<num>R/\d{4}/\d+)\s*'
    r'@@Recall date@@\s*(?P<date>\d{2}-\d{2}-\d{4})\s*'
    r'@@Recall type@@\s*(?P<rtype>(?:(?!@@).)*?)\s*'
    r'@@Reason for recall@@\s*(?P<reason>(?:(?!@@).)*?)\s*'
    r'@@How to check(?:(?!@@).)*?@@\s*(?:(?!@@).)*?\s*'
    r'@@How the manufacturer will repair@@\s*(?P<remedy>(?:(?!@@).)*?)\s*'
    r'@@Number of(?:\s+)affected vehicles@@\s*(?P<units>[\d,]+)', re.S)

def parse_recalls(h):
    h = re.sub(r'<script.*?</script>', ' ', h, flags=re.S)
    h = re.sub(r'<(h2|h3)[^>]*>(.*?)</\1>', lambda m: "@@" + re.sub(r'\s+', ' ',
        html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))).strip() + "@@", h, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', h)
    t = re.sub(r'[ \t\r\n]+', ' ', html.unescape(t))
    out = []
    for m in RECALL_RE.finditer(t):
        d = m.groupdict()
        out.append({k: re.sub(r'\s+', ' ', (v or "").strip()) for k, v in d.items()})
    return out

def iso(d):
    m = re.match(r'(\d{2})-(\d{2})-(\d{4})', d or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None

def dims_for(text):
    t = (text or "").lower(); d = [0]
    if re.search(r'high[- ]voltage|traction battery|lithium|\bbattery\b', t): d.append(3)
    if re.search(r'camera|automatic emergency|advanced driver|lane|stability control|\bads\b', t): d.append(6)
    return sorted(set(d))

def map_recall(make, model, rec, url):
    concern = rec["concern"]
    reason = (concern + " — " + rec["reason"]).strip(" —")
    rtype = rec["rtype"]
    status = "安全召回" if re.search(r'safety', rtype, re.I) else (rtype or "召回")
    return {
        "country": "英国", "agency": "英国DVSA(驾驶与车辆标准局)· 车辆安全处VSB",
        "oems": make[:200], "models": model[:300],
        "recall_date": iso(rec["date"]), "mandatory": False, "status": status,
        "reason": reason[:1200], "reg_ref": None, "refs": [],
        "dims": dims_for(concern + " " + rec["reason"]),
        "units": (rec["units"] or "").replace(",", "")[:40],
        "remedy": rec["remedy"][:400], "source_url": url,
        "note": (f"英国DVSA召回数据库 · 编号 {rec['num']} · {rtype} · DVSA每周自动同步")[:900],
        "_ref": rec["num"],
    }

def sb_existing_refs(base, key):
    url = base + "/rest/v1/recalls?country=eq." + q("英国") + "&select=note,source_url,reason,models"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    refs = set()
    for x in rows:
        for f in (x.get("note") or "", x.get("source_url") or "", x.get("reason") or "", x.get("models") or ""):
            for m in re.findall(r'R/\d{4}/\d+', f):
                refs.add(m)
    return refs

def sb_insert(base, key, rows):
    body = json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]).encode()
    req = urllib.request.Request(base + "/rest/v1/recalls", data=body, method="POST",
        headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="遍历全部品牌(默认仅精选)")
    ap.add_argument("--min-year", type=int, default=datetime.now(timezone.utc).year - 1,
                    help="仅收召回编号年份≥此值(默认当前年-1)")
    ap.add_argument("--years-back", type=int, default=8,
                    help="遍历的车辆生产年份回溯窗口(默认8,即近8个年份;召回按覆盖的生产年份归档)")
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base, key = cfg()
    op = make_opener()
    get(op, BASE + "/")  # 建立会话 cookie
    makes = options(get(op, BASE + "/recall-type/vehicle/make"))
    if not args.full:
        makes = [m for m in makes if CURATED.search(m)]
    cur = datetime.now(timezone.utc).year
    years = list(range(cur, cur - args.years_back, -1))   # 近 N 个生产年份
    print(f"品牌 {len(makes)} 个{'(全量)' if args.full else '(精选)'};min-year={args.min_year};"
          f"遍历生产年份 {years[-1]}-{years[0]}")
    existing = set() if args.dry_run else sb_existing_refs(base, key)

    new_rows, seen = [], set()
    for mk in makes:
        try:
            mh = get(op, BASE + f"/recall-type/vehicle/make/{q(mk)}/model")
        except Exception as e:
            print(f"[warn] make {mk}: {e}", file=sys.stderr); continue
        for md in options(mh):
            for yr in years:
                url = BASE + f"/recall-type/vehicle/make/{q(mk)}/model/{q(md)}/year/{yr}/recalls"
                try:
                    rh = get(op, url)
                except Exception as e:
                    print(f"[warn] {mk}/{md}/{yr}: {e}", file=sys.stderr); continue
                for rec in parse_recalls(rh):
                    ref = rec["num"]
                    ryr = int(ref.split("/")[1])
                    if ryr < args.min_year or ref in seen or ref in existing:
                        continue
                    seen.add(ref); new_rows.append(map_recall(mk, md, rec, url))
                time.sleep(args.sleep)
    print(f"新增 {len(new_rows)} 条(去重后,编号年份≥{args.min_year})")
    if args.dry_run:
        for r in new_rows[:20]:
            print("  ", r["_ref"], r["recall_date"], "|", r["oems"], r["models"], "|", r["reason"][:50])
        return
    for i in range(0, len(new_rows), 25):
        sb_insert(base, key, new_rows[i:i+25])
    print(f"已写入 recalls 表 {len(new_rows)} 条。")

if __name__ == "__main__":
    main()
