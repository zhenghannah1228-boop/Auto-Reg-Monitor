#!/usr/bin/env python3
"""
compile_tweet.py — 投喂新推文，编译进 insights.json

用法：
  # 处理一个 PDF
  python compile_tweet.py --pdf "推文——XXX.pdf"

  # 处理纯文字（从文件或直接传字符串）
  python compile_tweet.py --text tweet.txt
  python compile_tweet.py --text - < tweet.txt

  # 批量处理一个目录里所有 PDF
  python compile_tweet.py --dir inbox/

脚本做三件事：
  1. 抽取文本 → 解析标题/日期/作者/法规编号/类型
  2. 自动分类（type / dimensions）并匹配法规库
  3. 追加到 data/insights.json（去重，按 source_file 判断）

注意：自动解析是「初稿」。脚本会把低置信度字段标记 needs_review=true，
你（或下一轮 code）只需校对而非从零录入。
"""
import json, re, os, sys, argparse, glob, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'data', 'insights.json')

sys.path.insert(0, HERE)
from matcher import build_library_index, match_key_to_library

# ---------- 法规编号识别 ----------
# 注意：reg_no 保留用户写的完整版本（含系列号），match_key 用基础编号供匹配回退
REG_PATTERNS = [
    (r'UN\s*R(?:egulation\s*No\.?)?\s*(\d+)([A-Z]?)(?:[.\-]\s?(\d{2}))?', lambda m: ('欧洲','UN ECE',
        f"UN Regulation No. {m.group(1)}{m.group(2)}" + (f".{m.group(3)}" if m.group(3) else ''),
        f"UN R{m.group(1)}{m.group(2)}")),
    (r'ECE\s*R\.?\s*(\d+)([A-Z]?)', lambda m: ('欧洲','UN ECE',f"UN Regulation No. {m.group(1)}{m.group(2)}", f"UN R{m.group(1)}{m.group(2)}")),
    (r'GB[/\s]?T?\s?(\d{3,5}(?:[-—]\d{2,4})?)', lambda m: ('中国','中国',f"GB {m.group(1)}", f"GB {m.group(1).split('-')[0].split('—')[0]}")),
    (r'\(?EU\)?\s*(\d{4}/\d{2,4})', lambda m: ('欧盟','欧盟',f"EU {m.group(1)}", f"EU {m.group(1)}")),
    (r'FMVSS\s*(\d+)', lambda m: ('美国','美国',f"FMVSS {m.group(1)}", f"FMVSS {m.group(1)}")),
    (r'ADR\s*(\d+)', lambda m: ('澳洲','澳大利亚',f"ADR {m.group(1)}", f"ADR {m.group(1)}")),
    (r'(?:CONTRAN|Resolu[çc][ãa]o\s*CONTRAN|RES)\s*(?:n[ºo°]?\s*)?(\d{2,4})(?:/(\d{2,4}))?',
        lambda m: ('南美','巴西', f"CONTRAN {m.group(1)}" + (f"/{m.group(2)}" if m.group(2) else ''),
                   f"CONTRAN {m.group(1)}")),
    (r'INMETRO\s*(?:Ordinance|Portaria)?\s*(\d+)', lambda m: ('南美','巴西',f"INMETRO {m.group(1)}", f"INMETRO {m.group(1)}")),
    (r'AIS[\s\-]?(\d{2,3})', lambda m: ('南亚','印度',f"AIS {m.group(1)}", f"AIS {m.group(1)}")),
    (r'\bCMVR\b', lambda m: ('南亚','印度','CMVR','CMVR')),
    (r'\bKMVSS\s*(\d+)?', lambda m: ('东亚','韩国',f"KMVSS {m.group(1) or ''}".strip(), f"KMVSS {m.group(1) or ''}".strip())),
    (r'\bTIS\s*(\d+)', lambda m: ('东南亚','泰国',f"TIS {m.group(1)}", f"TIS {m.group(1)}")),
    (r'\bSNI\s*(\d{3,4})', lambda m: ('东南亚','印尼',f"SNI {m.group(1)}", f"SNI {m.group(1)}")),
    (r'\bSASO\s*(\d+)?', lambda m: ('中东','沙特',f"SASO {m.group(1) or ''}".strip(), f"SASO {m.group(1) or ''}".strip())),
    (r'\bGSO\s*(\d+)', lambda m: ('中东','海湾',f"GSO {m.group(1)}", f"GSO {m.group(1)}")),
]

# ---------- 类型判定 ----------
def guess_type(title, text):
    t = title + ' ' + text[:600]
    # 体系/制度科普：讲认证体系、机构层级、编号区别，而非单一法规条文
    system_kw = ['认证体系', '法规体系', '区别', '层级关系', '准入流程', '认证流程',
                 '机构', '体系解析', '一文看懂', '一文带你', '入门', '科普', '关系与层级']
    has_system = sum(1 for w in system_kw if w in t) >= 2
    has_compare_word = any(w in t for w in ['比较','差异','对比','vs','VS','与 ','中欧','对比学习'])
    has_revision_word = any(w in t for w in ['修订','升级','变化点','新旧','改版','新增','修改','修订版'])
    regs = extract_regs(t)
    distinct = len(set(r['match_key'] for r in regs))
    if has_system:
        return 'system'
    # 多条同体系法规并列对比（如 R79/R171/R157）
    if has_compare_word and distinct >= 2:
        return 'compare'
    if has_revision_word:
        return 'revision'
    if distinct >= 3:  # 3+法规并列基本是对比
        return 'compare'
    return 'interpret'

# ---------- 维度判定（关键词 → 10维度）----------
DIM_KW = {
    '1': ['整车','座椅','头枕','门把手','转向','凸出物','视野','HUD','认证','型式','碰撞','制动','灯','车速表','尺寸','外廓'],
    '2': ['排放','环保','油耗','REACH','CBAM','噪声','低碳','空气质量','ELV','碳足迹'],
    '3': ['射频','EMC','RED','电波','TPMS','蓝牙','RFID','天线'],
    '4': ['电池','充电','REESS','电池护照','UN38.3','电芯'],
    '5': ['补贴','IRA','ZEV','原产地','本地化','税收','工业加速'],
    '6': ['网络安全','CSMS','SUMS','OTA','R155','R156','数据','防篡改'],
    '7': ['ADAS','自动驾驶','ALKS','AEB','ISA','车道','智能网联','雷达','摄像头'],
    '8': ['标签','标牌','VIN','铭牌','e-mark','能效','标志','电子标识','信号装置'],
    '9': ['注册','清关','COC','年检','召回','监管','上牌','入关'],
    '10': ['警告三角','灭火器','急救包','备胎','随车工具'],
}
def guess_dimensions(title, text):
    t = title + ' ' + text
    dims = [d for d, kws in DIM_KW.items() if any(k in t for k in kws)]
    return dims or ['1']

def extract_regs(text):
    found = {}
    for pat, fn in REG_PATTERNS:
        for m in re.finditer(pat, text):
            region, country, reg_no, key = fn(m)
            found[key] = {"region": region, "country": country,
                          "reg_no": reg_no, "match_key": key}
    return list(found.values())

def extract_meta(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    title = lines[0] if lines else ''
    author, date = '', ''
    for l in lines[:5]:
        m = re.search(r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', l)
        if m:
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        m2 = re.search(r'原创\s+(\S+)\s+(\S+)', l)
        if m2:
            author = m2.group(2)
    return title, author, date

def read_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return '\n'.join((p.extract_text() or '') for p in pdf.pages)

def next_id(insights, year):
    nums = [int(re.search(r'-(\d+)$', i['id']).group(1))
            for i in insights if i['id'].startswith(f'INS-{year}')]
    return f"INS-{year}-{(max(nums)+1 if nums else 1):03d}"

def compile_one(text, source_file, insights, lib_index):
    title, author, date = extract_meta(text)
    year = (date or str(datetime.date.today()))[:4]
    regs = extract_regs(title + '\n' + text)
    typ = guess_type(title, text)
    dims = guess_dimensions(title, text)
    # 匹配法规库
    for r in regs:
        hits = match_key_to_library(r['match_key'], lib_index)
        r['_matched_count'] = len(hits)
    # 摘要：取标题后第一段实质内容
    body = [l.strip() for l in text.split('\n')
            if l.strip() and not re.search(r'原创|点击|关注|喜欢作者|（end）|收录于', l)]
    summary = body[1] if len(body) > 1 else title
    record = {
        "id": next_id(insights, year),
        "title": title,
        "type": typ,
        "summary": summary[:200],
        "regulations": [{k: v for k, v in r.items() if not k.startswith('_')} for r in regs],
        "topics": [],
        "dimensions": dims,
        "key_points": [],
        "author": author or "未知",
        "publish_date": date,
        "region_focus": sorted(set(r['region'] for r in regs)) or ["通用"],
        "source_file": os.path.basename(source_file),
        "url": "",
        "needs_review": True,
        "_auto_match": {r['match_key']: r.get('_matched_count', 0) for r in regs}
    }
    return record

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf')
    ap.add_argument('--text')
    ap.add_argument('--dir')
    ap.add_argument('--source', default='', help='纯文字输入时手动指定 source 名')
    args = ap.parse_args()

    insights_db = json.load(open(DATA, encoding='utf-8'))
    insights = insights_db['insights']
    existing = {i['source_file'] for i in insights}
    lib_index = build_library_index()
    print(f"[法规库] 索引 {len(lib_index)} 个编号")

    todo = []  # (text, source)
    if args.pdf:
        todo.append((read_pdf(args.pdf), args.pdf))
    if args.dir:
        for f in sorted(glob.glob(os.path.join(args.dir, '*.pdf'))):
            todo.append((read_pdf(f), f))
    if args.text:
        raw = sys.stdin.read() if args.text == '-' else open(args.text, encoding='utf-8').read()
        todo.append((raw, args.source or 'manual-text-' + datetime.date.today().isoformat()))

    added = 0
    for text, src in todo:
        if os.path.basename(src) in existing:
            print(f"[跳过] 已存在: {os.path.basename(src)}")
            continue
        rec = compile_one(text, src, insights, lib_index)
        insights.append(rec)
        existing.add(rec['source_file'])
        added += 1
        nmatch = sum(rec['_auto_match'].values())
        print(f"[新增] {rec['id']} | {rec['title'][:40]} | type={rec['type']} "
              f"| dims={rec['dimensions']} | 法规库命中={nmatch}")

    json.dump(insights_db, open(DATA, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f"\n完成：新增 {added} 条，共 {len(insights)} 条 → {DATA}")
    if added:
        print("提示：新增条目 needs_review=true，建议补全 topics / key_points / url 后置为 false")

if __name__ == '__main__':
    main()
