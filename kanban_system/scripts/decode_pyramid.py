#!/usr/bin/env python3
"""
decode_pyramid.py — 把 type=system 的体系科普推文解码成「认证金字塔」并 merge 进 pyramids.json

设计：一国一塔。system 推文是数据来源，被解码后合并到对应国家的塔。

用法：
  # 把 insights.json 里所有 type=system 且还没进塔的，跑一遍解码（半自动：给出骨架待人工精修）
  python decode_pyramid.py --scan

  # 解码指定 insight
  python decode_pyramid.py --id INS-2026-019

  # 校验现有塔的法规编号与法规库的挂链情况
  python decode_pyramid.py --check

合并规则：
  - 国家不存在 → 新建塔（4层骨架，需人工精修 layers 内容）
  - 国家已存在 → 把该 insight 加进 sources[]，并把推文新识别的法规编号补进对应层的 regulations（去重），不覆盖已有 detail/name。

注意：体系层级(谁是母法、谁是技术基准)需要语义理解，纯规则只能给骨架。
脚本负责：抽取国家、机构、编号、四层候选词；人工/LLM 负责：定 detail 与层级归属。
"""
import json, os, sys, re, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INSIGHTS = os.path.join(ROOT, 'data', 'insights.json')
PYRAMIDS = os.path.join(ROOT, 'data', 'pyramids.json')

sys.path.insert(0, HERE)
from matcher import build_library_index, match_key_to_library

# 国家中文名（region_focus 不够精确时从标题/正文找）
COUNTRY_HINTS = ['巴西','马来西亚','印度','泰国','越南','印尼','印度尼西亚','沙特','阿联酋',
                 '土耳其','墨西哥','南非','尼日利亚','埃及','俄罗斯','日本','韩国','美国',
                 '加拿大','澳大利亚','新西兰','英国','欧盟']

# 机构 abbr → 角色提示（用于层级归属的弱提示）
ROLE_HINTS = {
    'L1': ['母法','法令','Act','法律','框架','决议','CONTRAN','强制'],
    'L2': ['技术基准','标准','UN R','ECE','FMVSS','MS','NBR','参考'],
    'L3': ['测试','实验室','技术服务','审查','TS','Lab'],
    'L4': ['批准','证书','认证','VTA','CTA','CAT','COC','型式'],
}

def find_country(insight):
    # 优先级：标题(主角最强信号) > region_focus首个具体国 > 摘要
    # 摘要常含对照国(如马来西亚/泰国),不能压过标题主体
    title = insight['title']
    for c in COUNTRY_HINTS:
        if c in title:
            return c
    rf = insight.get('region_focus', [])
    skip = ('通用','欧洲','美国','南美','东盟','中东','非洲','大洋洲')
    for r in rf:
        if r not in skip:
            return r
    summary = insight.get('summary','')
    for c in COUNTRY_HINTS:
        if c in summary:
            return c
    return rf[0] if rf else '未知'

def extract_authorities(insight):
    """从要点里抓 机构名(ABBR) 模式"""
    blob = ' '.join(insight.get('key_points',[])) + ' ' + insight.get('summary','')
    auths = []
    # 抓大写缩写
    for m in re.finditer(r'([A-Z]{3,10})(?:（|\()?([\u4e00-\u9fa5]{2,20}(?:委员会|局|部|机构|秘书处))?', blob):
        abbr = m.group(1)
        if abbr in ('ECE','FMVSS','WP29','UN','VTA','CTA','OBD','REESS') or len(abbr) < 3:
            continue
        auths.append(abbr)
    return sorted(set(auths))

def build_skeleton(insight, lib_index):
    """生成4层骨架 + 把推文里的法规编号按角色提示分配到层"""
    regs = insight.get('regulations', [])
    # 给每条 reg 计算库命中
    for r in regs:
        r['_lib'] = len(match_key_to_library(r['match_key'], lib_index))

    # 按角色提示把 reg 粗分到层（CONTRAN/Act→L1, UN R/ECE/FMVSS→L2）
    layer_regs = {'L1':[], 'L2':[], 'L3':[], 'L4':[]}
    for r in regs:
        rn = r['reg_no'].upper()
        if any(k.upper() in rn for k in ['CONTRAN','ACT','SENATRAN','法令','RESOLU']):
            layer_regs['L1'].append(r)
        elif any(k in rn for k in ['UN R','ECE','FMVSS','NBR','MS ']):
            layer_regs['L2'].append(r)
        else:
            layer_regs['L2'].append(r)  # 默认归技术基准

    palette = {'L1':'母法 / 顶端','L2':'技术基准','L3':'审查 / 测试','L4':'批准 / 证书'}
    layers = []
    for lv in ['L1','L2','L3','L4']:
        layers.append({
            "level": lv, "role": palette[lv],
            "name_cn": "【待精修】", "name_en": "",
            "detail": "【待精修：根据推文要点填写本层定位】",
            "regulations": [{k:v for k,v in r.items() if not k.startswith('_')} for r in layer_regs[lv]]
        })
    return layers

def decode_one(insight, pyramids, lib_index):
    country = find_country(insight)
    layers = build_skeleton(insight, lib_index)
    auths = extract_authorities(insight)

    if country in pyramids['pyramids']:
        # 已存在 → 补来源 + 合并法规编号（不覆盖）
        p = pyramids['pyramids'][country]
        if insight['id'] not in p.get('sources', []):
            p.setdefault('sources', []).append(insight['id'])
        # 合并各层新法规
        for new_layer in layers:
            for exist_layer in p['layers']:
                if exist_layer['level'] == new_layer['level']:
                    have = {r['reg_no'] for r in exist_layer.get('regulations',[])}
                    for r in new_layer['regulations']:
                        if r['reg_no'] not in have:
                            exist_layer.setdefault('regulations',[]).append(r)
        p['decoded_from_tweet'] = True
        action = 'merged'
    else:
        # 新建塔骨架
        pyramids['pyramids'][country] = {
            "country": country, "country_type": "【待定:自有型/采纳型/混合型】",
            "data_grade": "C", "tagline": insight.get('summary','【待精修一句话定位】'),
            "layers": layers,
            "authorities": [{"name": "【待精修】", "abbr": a, "desc": ""} for a in auths],
            "core_regulations": {},
            "sources": [insight['id']],
            "decoded_from_tweet": True,
            "last_updated": "auto"
        }
        action = 'created'
    return country, action

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--id')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    insights_db = json.load(open(INSIGHTS, encoding='utf-8'))
    pyramids = json.load(open(PYRAMIDS, encoding='utf-8'))
    lib_index = build_library_index()

    if args.check:
        print("=== 金字塔法规挂链校验 ===")
        for cname, p in pyramids['pyramids'].items():
            print(f"\n【{cname}】 来源:{p.get('sources',[])}  解码:{p.get('decoded_from_tweet')}")
            for layer in p['layers']:
                for r in layer.get('regulations', []):
                    n = len(match_key_to_library(r['match_key'], lib_index))
                    flag = '✓库'+str(n) if n else '✗待补充'
                    print(f"  {layer['level']} {r['reg_no']:24s} [{flag}]")
        return

    insights = insights_db['insights']
    targets = []
    if args.id:
        targets = [i for i in insights if i['id'] == args.id]
    elif args.scan:
        done = set()
        for p in pyramids['pyramids'].values():
            done.update(p.get('sources', []))
        targets = [i for i in insights if i['type'] == 'system' and i['id'] not in done]

    if not targets:
        print("没有待解码的 system 推文（都已进塔）。用 --check 查看现有塔。")
        return

    for ins in targets:
        country, action = decode_one(ins, pyramids, lib_index)
        print(f"[{action}] {ins['id']} → 「{country}」金字塔")

    json.dump(pyramids, open(PYRAMIDS, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"\n已写入 {PYRAMIDS}")
    print("提示：新建/合并的塔含【待精修】占位，需人工或 LLM 根据推文要点补全层级定位与机构描述。")

if __name__ == '__main__':
    main()
