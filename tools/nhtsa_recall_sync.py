#!/usr/bin/env python3
"""
美国 NHTSA(国家公路交通安全管理局)机动车安全召回 → recalls 同步器
抓取 NHTSA 官方召回 API,映射为召回记录,按召回号(YYV###)去重后写入 Supabase recalls 表。
16 召回案例页会自动显示新记录。

工作原理:
- NHTSA 没有「列最近召回」的公开接口,但车辆(V)类召回号 `YYV001, YYV002, …` 连续递增。
- 脚本读库里已有的最大车辆召回号,从其附近开始逐号探测
  `https://api.nhtsa.gov/recalls/campaignNumber?campaignNumber=<YYV###>`;
  命中即映射入库,连续空号达阈值(且已越过当前最大号)即停;同时回填中间缺号。
- 年初(1–3 月)额外扫上一年前缀,兜住跨年发布的滞后召回。

- 纯静态站 + Supabase 无后端,本脚本由 GitHub Actions 定时(每周)运行。
- 仅用 Python 标准库;Supabase url + anonKey 从 config.js 解析(anonKey 公开,RLS 全放行)。
- 与人工粘贴 NHTSA 列表互补:自动同步给英文原文摘要+官方数量/处理措施(够用、可归类);
  需要中文精译时仍可让 Claude 逐条深抓。

用法:
  python tools/nhtsa_recall_sync.py                # 同步当前年份新增车辆召回
  python tools/nhtsa_recall_sync.py --dry-run      # 只打印映射结果,不写库
  python tools/nhtsa_recall_sync.py --year 26      # 指定年份前缀(两位)
  python tools/nhtsa_recall_sync.py --miss-stop 20 # 连续空号停止阈值(默认15)
"""
import re, sys, json, time, argparse, urllib.request, urllib.error, os
from datetime import datetime, timezone

API = "https://api.nhtsa.gov/recalls/campaignNumber?campaignNumber="
UA = "Mozilla/5.0 (AutoRegMonitor NHTSARecallSync)"

def http_get_json(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e; time.sleep(1.5 * (i + 1))
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url} :: {last}")

def cfg():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = open(os.path.join(root, "config.js"), encoding="utf-8").read()
    url = re.search(r'url:\s*"([^"]+)"', txt).group(1).rstrip("/")
    key = re.search(r'anonKey:\s*"([^"]+)"', txt).group(1)
    return url, key

def iso_date(s):
    # NHTSA ReportReceivedDate 格式为 DD/MM/YYYY(经核实:出现日>12 的值)
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', s or "")
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if d > 12 and mo <= 12:            # 明确 DD/MM
        pass
    elif mo > 12 and d <= 12:          # 实为 MM/DD,交换
        d, mo = mo, d
    # 否则(两者≤12)按 NHTSA 既定 DD/MM 解释
    try:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    except Exception:
        return None

FMVSS_PAT = re.compile(r'FMVSS\s*(?:No\.?\s*)?(\d+[A-Za-z]?)', re.I)
def extract_fmvss(*texts):
    seen = []
    for t in texts:
        for n in FMVSS_PAT.findall(t or ""):
            v = "FMVSS " + n.upper()
            if v not in seen: seen.append(v)
    return " & ".join(seen) if seen else None

def dims_for(text):
    t = (text or "").lower()
    dims = [0]
    if re.search(r'high[\s-]?voltage|traction battery|lithium[\s-]?ion|\bev battery\b|battery pack', t):
        dims.append(3)
    if re.search(r'rearview camera|backup camera|back[\s-]?up camera|lane depart|stability control|\bESC\b|automatic emergency|forward collision|\bADAS\b|driver assist', t, re.I):
        dims.append(6)
    if re.search(r'\blabel\b|labeling|placard|tire information', t):
        dims.append(7)
    return sorted(set(dims))

def map_campaign(cid, results):
    r0 = results[0]
    # 车型聚合:MAKE MODEL (minYr-maxYr)
    grp = {}
    makes = []
    for r in results:
        mk = (r.get("Make") or "").strip()
        md = (r.get("Model") or "").strip()
        yr = str(r.get("ModelYear") or "").strip()
        if mk and mk not in makes: makes.append(mk)
        key = (mk, md)
        grp.setdefault(key, set())
        if yr.isdigit(): grp[key].add(int(yr))
    parts = []
    for (mk, md), yrs in grp.items():
        label = f"{mk} {md}".strip()
        if yrs:
            lo, hi = min(yrs), max(yrs)
            label += f" ({lo})" if lo == hi else f" ({lo}-{hi})"
        parts.append(label)
    models = " / ".join(parts)
    summary = re.sub(r'\s+', ' ', (r0.get("Summary") or "")).strip()
    remedy = re.sub(r'\s+', ' ', (r0.get("Remedy") or "")).strip()
    consequence = re.sub(r'\s+', ' ', (r0.get("Consequence") or "")).strip()
    component = (r0.get("Component") or "").strip()
    park_out = str(r0.get("parkOutSide")).lower() in ("true", "1", "yes")
    park_it = str(r0.get("parkIt")).lower() in ("true", "1", "yes")
    ota = str(r0.get("overTheAirUpdate")).lower() in ("true", "1", "yes")
    units = str(r0.get("PotentialNumberofUnitsAffected") or "").strip()
    reason = (summary or consequence or component)[:1200]
    note = ("美国NHTSA召回数据库 · Recall ID " + cid +
            (" · ⚠停室外" if park_out else "") + (" · ⚠立即停驶" if park_it else "") +
            (" · OTA可更新" if ota else "") + " · NHTSA每周自动同步")
    return {
        "country": "美国", "agency": "美国NHTSA(国家公路交通安全管理局)",
        "oems": (" / ".join(makes) or (r0.get("Manufacturer") or ""))[:200],
        "models": models[:300], "recall_date": iso_date(r0.get("ReportReceivedDate")),
        "mandatory": False, "status": "安全召回",
        "reason": reason, "reg_ref": extract_fmvss(summary, component),
        "refs": [], "dims": dims_for(summary + " " + component),
        "units": units[:40], "remedy": remedy[:400],
        "source_url": "https://www.nhtsa.gov/recalls?nhtsaId=" + cid,
        "note": note[:900], "_cid": cid,
    }

def sb_existing_cids(base, key):
    url = base + "/rest/v1/recalls?or=(source_url.like.*nhtsaId*,note.like.*NHTSA*)&select=source_url,note"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    cids = set()
    for x in rows:
        for f in (x.get("note") or "", x.get("source_url") or ""):
            for m in re.findall(r'(\d{2}[VvEeTt]\d{3,4})', f):
                cids.add(m.upper())
    return cids

def sb_insert(base, key, rows):
    body = json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]).encode()
    req = urllib.request.Request(base + "/rest/v1/recalls", data=body, method="POST",
        headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status

def prefixes(year_arg):
    if year_arg:
        return [f"{int(year_arg):02d}V"]
    now = datetime.now(timezone.utc)
    yy = now.year % 100
    pref = [f"{yy:02d}V"]
    if now.month <= 3:                 # 年初兜住上一年滞后发布
        pref.append(f"{(yy - 1) % 100:02d}V")
    return pref

def probe_prefix(pref, existing, miss_stop, back, cap_ahead):
    nums = sorted(int(c[3:]) for c in existing if c.startswith(pref) and c[3:].isdigit())
    max_existing = nums[-1] if nums else 0
    start = max(1, max_existing - back)
    end = max_existing + cap_ahead
    new_rows, miss = [], 0
    n = start
    while n <= end:
        cid = f"{pref}{n:03d}"
        if cid in existing:
            miss = 0; n += 1; continue
        data = http_get_json(API + cid)
        results = (data or {}).get("results") or []
        results = [r for r in results if str(r.get("NHTSACampaignNumber", "")).startswith(cid)]
        if results:
            new_rows.append(map_campaign(cid, results)); miss = 0
            print(f"  + {cid}: {results[0].get('Make','')} — {(results[0].get('Component') or '')[:40]}")
        else:
            miss += 1
            if n > max_existing and miss >= miss_stop:
                break
        time.sleep(0.2)
        n += 1
    return new_rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", help="年份前缀两位(如 26);默认按当前 UTC 年份")
    ap.add_argument("--miss-stop", type=int, default=15, help="越过当前最大号后连续空号停止阈值")
    ap.add_argument("--back", type=int, default=30, help="向下回填缺号的窗口")
    ap.add_argument("--cap-ahead", type=int, default=120, help="向上探测的最大跨度上限")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base, key = cfg()
    existing = set() if args.dry_run else sb_existing_cids(base, key)
    print(f"库中已有 NHTSA 召回号 {len(existing)} 个")
    all_new = []
    for pref in prefixes(args.year):
        print(f"探测前缀 {pref} …")
        all_new += probe_prefix(pref, existing, args.miss_stop, args.back, args.cap_ahead)
    # 去重(防同号在多前缀/多结果重复)
    seen, rows = set(), []
    for r in all_new:
        if r["_cid"] in seen: continue
        seen.add(r["_cid"]); rows.append(r)
    print(f"\n新增 {len(rows)} 条(去重后)")
    if args.dry_run:
        for r in rows[:20]:
            print(json.dumps({k: r[k] for k in ("_cid", "oems", "recall_date", "units", "reason")},
                             ensure_ascii=False)[:200])
        return
    for i in range(0, len(rows), 25):
        sb_insert(base, key, rows[i:i+25])
    print(f"已写入 recalls 表 {len(rows)} 条。")

if __name__ == "__main__":
    main()
