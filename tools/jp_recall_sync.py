#!/usr/bin/env python3
"""
日本国土交通省(MLIT)机动车リコール(召回)/改善対策/キャンペーン → recalls 同步器
抓取「リコール等情報検索」系统(renrakuda.mlit.go.jp)背后的 Estraier 搜索 CGI 官方接口,
按届出番号(notification_no)去重后写入 Supabase recalls 表。16 召回案例页会自动显示新记录。

工作原理:
- 该系统前端(ris-search-result-car.html)本身不含数据,实际由 JS 调用
  GET https://renrakuda.mlit.go.jp/mt/mt-estraier.cgi?blog_id=4&class=recalldatacar
      &notification_date=<自YYYY/MM/DD> <至YYYY/MM/DD>&offset=&limit=&order_by=...&order_condition=STRD
  该 CGI 要求带 Referer 头(否则返回空 data),返回体是「模板拼接的 JSON」,
  末尾在 `]}` 前多一个逗号,需先用正则去掉再 json.loads。
- 单条记录字段完整,无需下载/解析 PDF:届出番号、届出日、不具合装置、状況説明(缺陷描述)、
  改善措置説明(处理方式)、対象台数、typeList(厂商 car_name_code + 通称名 + 型式,可多条);
  campaign_flag:1=リコール(安全召回) 2=改善対策 3=キャンペーン;country_flag:2=进口车。
  file_name 字段内含 PDF 相对链接,解析后拼为
  https://renrakuda.mlit.go.jp/renrakuda/recallpdf/{届出番号}.pdf(已验证 200)。
- 纯静态站 + Supabase 无后端,本脚本由 GitHub Actions 定时(每周)运行;仅用标准库。
- Supabase url + anonKey 从仓库根 config.js 解析(anonKey 公开,RLS 全放行)。

用法:
  python tools/jp_recall_sync.py                  # 同步近 --days-back 天内的届出(默认45天,含重叠去重)
  python tools/jp_recall_sync.py --dry-run
  python tools/jp_recall_sync.py --days-back 400   # 首次播种,拉近13个月
"""
import re, sys, json, time, argparse, os, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

API = "https://renrakuda.mlit.go.jp/mt/mt-estraier.cgi"
REFERER = "https://renrakuda.mlit.go.jp/renrakuda/ris-search-result-car.html"
UA = "Mozilla/5.0 (AutoRegMonitor MLITRecallSync)"

CAMPAIGN_TEXT = {"1": "安全召回", "2": "改善对策", "3": "服务活动通知"}

def cfg():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt = open(os.path.join(root, "config.js"), encoding="utf-8").read()
    url = re.search(r'url:\s*"([^"]+)"', txt).group(1).rstrip("/")
    key = re.search(r'anonKey:\s*"([^"]+)"', txt).group(1)
    return url, key

def api_get(offset, limit, date_from, date_to, tries=4, timeout=60):
    params = {
        "blog_id": "4", "class": "recalldatacar",
        "notification_date": f"{date_from} {date_to}",
        "offset": str(offset), "limit": str(limit),
        "order_by": "recall_data_car_mlit_notification_date",
        "order_condition": "STRD",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/json", "Referer": REFERER})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
            text = re.sub(r',(\s*\]\s*\}\s*)$', r'\1', raw.strip())
            return json.loads(text)
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed: offset={offset} :: {last}")

def iso(d):
    m = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', d or "")
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None

def dims_for(text):
    t = text or ""
    d = [0]
    if re.search(r'high[- ]voltage|traction battery|lithium|battery pack|バッテリー|電池|高電圧|リチウム', t, re.I):
        d.append(3)
    if re.search(r'camera|automatic emergency|lane depart|stability control|driver assist|\bADAS\b|'
                 r'カメラ|自動ブレーキ|衝突被害軽減|車線逸脱|安定性制御|運転支援', t, re.I):
        d.append(6)
    return sorted(set(d))

def map_recall(rec):
    notif_no = rec.get("recall_data_car_mlit_notification_no") or ""
    type_list = []
    for k, v in rec.items():
        if k == "typeList" or re.match(r'typeList\d+$', k):
            type_list += (v or [])
    makers, models = [], []
    for t in type_list:
        mk = (t.get("recall_type_data_car_mlit_car_name_code") or "").strip()
        common = (t.get("recall_type_data_car_mlit_common_name") or "").strip()
        model_code = (t.get("recall_type_data_car_mlit_model_name") or "").strip()
        if mk and mk not in makers:
            makers.append(mk)
        label = " ".join(x for x in (mk, common or model_code) if x)
        if label and label not in models:
            models.append(label)
    device = (rec.get("recall_data_car_mlit_defective_device") or "").strip()
    situation = re.sub(r'\s+', ' ', (rec.get("recall_data_car_mlit_situation_explanatory_text") or "")).strip()
    remedy = re.sub(r'\s+', ' ', (rec.get("recall_data_car_mlit_measures_explanatory_text") or "")).strip()
    units = (rec.get("recall_data_car_mlit_recall_car_count") or "").strip()
    campaign_flag = str(rec.get("recall_data_car_mlit_recall_campaign_flag") or "1")
    country_flag = str(rec.get("recall_data_car_mlit_home_foreign_country_flag") or "1")
    status = CAMPAIGN_TEXT.get(campaign_flag, "召回")
    reason = (f"{device} — {situation}" if device else situation).strip(" —")
    note = (f"日本国土交通省(MLIT)リコール等情報検索 · 届出番号 {notif_no} · {status}"
            + (" · 进口车" if country_flag == "2" else "")
            + " · MLIT每周自动同步")
    return {
        "country": "日本", "agency": "日本国土交通省(MLIT)· リコール等情報検索",
        "oems": (" / ".join(makers))[:200], "models": (" / ".join(models))[:300],
        "recall_date": iso(rec.get("recall_data_car_mlit_notification_date")),
        "mandatory": False, "status": status,
        "reason": reason[:1200], "reg_ref": device[:120] or None, "refs": [],
        "dims": dims_for(device + " " + situation),
        "units": units[:40], "remedy": remedy[:400],
        "source_url": f"https://renrakuda.mlit.go.jp/renrakuda/recallpdf/{notif_no}.pdf",
        "note": note[:900], "_ref": notif_no,
    }

def sb_existing_refs(base, key):
    url = base + "/rest/v1/recalls?country=eq." + urllib.parse.quote("日本") + "&select=note"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    refs = set()
    for x in rows:
        for m in re.findall(r'届出番号\s*(\d{6,8})', x.get("note") or ""):
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
    ap.add_argument("--days-back", type=int, default=45, help="拉取近多少天内届出(默认45,含重叠去重)")
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base, key = cfg()

    to_d = datetime.now(timezone.utc)
    from_d = to_d - timedelta(days=args.days_back)
    date_from, date_to = from_d.strftime("%Y/%m/%d"), to_d.strftime("%Y/%m/%d")
    print(f"抓取区间 {date_from} ~ {date_to}")

    existing = set() if args.dry_run else sb_existing_refs(base, key)
    print(f"库中已有日本召回 {len(existing)} 条")

    all_recs, offset, total = [], 1, None
    while total is None or offset <= total:
        d = api_get(offset, args.page_size, date_from, date_to)
        page = d.get("data") or []
        if not page:
            break
        total = int(page[0].get("count") or len(page))
        all_recs += page
        offset += args.page_size
        time.sleep(0.3)
    print(f"接口返回 {len(all_recs)} 条(区间内总数 {total})")

    new_rows, seen = [], set()
    for rec in all_recs:
        if (rec.get("recall_data_car_mlit_delete_flag") or "") == "オン":
            continue
        row = map_recall(rec)
        ref = row["_ref"]
        if not ref or ref in seen or ref in existing:
            continue
        seen.add(ref); new_rows.append(row)
    print(f"新增 {len(new_rows)} 条(去重后)")
    if args.dry_run:
        for r in new_rows[:20]:
            print("  ", r["_ref"], r["recall_date"], "|", r["oems"], r["models"], "|", r["reason"][:50])
        return
    for i in range(0, len(new_rows), 25):
        sb_insert(base, key, new_rows[i:i+25])
    print(f"已写入 recalls 表 {len(new_rows)} 条。")

if __name__ == "__main__":
    main()
