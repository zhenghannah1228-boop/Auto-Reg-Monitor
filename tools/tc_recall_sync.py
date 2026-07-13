#!/usr/bin/env python3
"""
加拿大交通部(Transport Canada)机动车安全召回 → recalls 同步器
抓取 TC 召回数据库 Atom RSS(最近 ~30 条),映射为召回记录,按召回号 rn 去重后写入
Supabase recalls 表。16 召回案例页会自动显示新记录。

- 纯静态站+Supabase 无后端,本脚本由 GitHub Actions 定时运行(每周两次)。
- 仅用 Python 标准库;Supabase url+anonKey 从 config.js 解析(anonKey 公开,RLS 全放行)。
- 与人工「📋 复制抓取指令」流程互补:自动同步给出英文原文摘要(够用、可归类);
  需要中文精译 + 数量/处理措施补全时,仍可用复制指令让 Claude 逐条深抓。

用法:
  python tools/tc_recall_sync.py            # 同步 RSS 当前 ~30 条新召回
  python tools/tc_recall_sync.py --dry-run  # 只打印映射结果,不写库
"""
import re, sys, json, time, argparse, urllib.request, os

RSS_URL = "https://wwwapps.tc.gc.ca/Saf-Sec-Sur/7/VRDB-BDRV/search-recherche/rss.aspx?lang=eng"
UA = "Mozilla/5.0 (AutoRegMonitor TCRecallSync)"

def http_get(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
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

def unescape(s):
    return (s or "").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')

def tag(t, block):
    m = re.search(rf'<{t}[^>]*>(.*?)</{t}>', block, re.S)
    return unescape(m.group(1).strip()) if m else ""

def map_entry(e):
    link = re.search(r'<link[^>]*href="([^"]*)"', e)
    url = unescape(link.group(1)) if link else tag("id", e)
    rn = (re.search(r'rn=(\d+)', url) or [None, ""])[1] if re.search(r'rn=(\d+)', url) else ""
    rn = re.search(r'rn=(\d+)', url).group(1) if re.search(r'rn=(\d+)', url) else ""
    title = re.sub(r'\s+', ' ', tag("title", e))
    m = re.match(r'^(.*?)\s+issued a recall on the\s+(.*?)\s+models?\.?$', title, re.I)
    brand = (m.group(1).strip() if m else title.split(" issued")[0].strip()) or "(未标注)"
    models = (m.group(2).strip() if m else "")
    summary = re.sub(r'\s+', ' ', tag("summary", e)).strip()
    summary = re.sub(r'^Issue:\s*', '', summary)
    cats = re.findall(r'<category[^>]*term="([^"]*)"', e)
    upd = tag("updated", e)[:10]  # YYYY-MM-DD
    note = ("加拿大交通部召回数据库 VRDB · rn=" + rn +
            (" · 车型类别 " + "/".join(cats) if cats else "") + " · TC 每周自动同步")
    return {
        "country": "加拿大", "agency": "加拿大交通部(Transport Canada)",
        "oems": brand, "models": models[:300], "recall_date": upd,
        "mandatory": False, "status": "自愿召回",
        "reason": summary[:1200], "reg_ref": None, "refs": [],
        "dims": [0], "units": "", "remedy": "", "source_url": url,
        "note": note[:900], "_rn": rn,
    }

def sb_existing_rns(base, key):
    url = base + "/rest/v1/recalls?or=(source_url.like.*VRDB-BDRV*,note.like.*rn=*)&select=source_url,note"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    rns = set()
    for x in rows:
        for f in (x.get("note") or "", x.get("source_url") or ""):
            m = re.search(r'rn=(\d+)', f)
            if m: rns.add(m.group(1))
    return rns

def sb_insert(base, key, rows):
    body = json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]).encode()
    req = urllib.request.Request(base + "/rest/v1/recalls", data=body, method="POST",
        headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base, key = cfg()
    xml = http_get(RSS_URL)
    entries = re.findall(r'<entry>(.*?)</entry>', xml, re.S)
    print(f"RSS 条目 {len(entries)}")
    existing = set() if args.dry_run else sb_existing_rns(base, key)
    new_rows, seen = [], set()
    for e in entries:
        row = map_entry(e)
        rn = row["_rn"]
        if not rn or rn in existing or rn in seen:
            continue
        seen.add(rn); new_rows.append(row)
    print(f"新增 {len(new_rows)} 条(去重后)")
    if args.dry_run:
        for r in new_rows[:12]:
            print(json.dumps({k: r[k] for k in ("oems", "models", "recall_date", "reason")}, ensure_ascii=False)[:200])
        return
    for i in range(0, len(new_rows), 25):
        sb_insert(base, key, new_rows[i:i+25])
    print(f"已写入 recalls 表 {len(new_rows)} 条。")

if __name__ == "__main__":
    main()
