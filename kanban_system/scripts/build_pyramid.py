#!/usr/bin/env python3
"""
build_pyramid.py — 把 pyramids.json 渲染成「09 认证金字塔」tab 模块

输出 output/pyramid_view.html：与监控台 09 tab 同款的阶梯金字塔视图，
可切换国家、点击层看详情、显示主管机构与核心法规、链接回来源推文。

设计与现有 09 tab 对齐：紫色阶梯(L1最宽顶端→L4最窄)，右侧详情面板，
底部主管机构 + 核心法规分组。code 可直接把此渲染逻辑搬进监控台。
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYRAMIDS = os.path.join(ROOT, 'data', 'pyramids.json')
INSIGHTS = os.path.join(ROOT, 'data', 'insights.json')
OUT = os.path.join(ROOT, 'output')
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
from matcher import build_library_index, match_key_to_library

def build():
    pyr = json.load(open(PYRAMIDS, encoding='utf-8'))
    insights = {i['id']: i for i in json.load(open(INSIGHTS, encoding='utf-8'))['insights']}
    lib_index = build_library_index()

    # 给每条金字塔法规算库命中
    for cname, p in pyr['pyramids'].items():
        for layer in p['layers']:
            for r in layer.get('regulations', []):
                r['_lib'] = len(match_key_to_library(r['match_key'], lib_index))
        # 把来源推文标题补进去，便于链接
        p['_source_titles'] = {sid: insights[sid]['title'] for sid in p.get('sources', []) if sid in insights}

    data_json = json.dumps(pyr['pyramids'], ensure_ascii=False)
    page = TEMPLATE.replace('__PYRAMIDS__', data_json)
    open(os.path.join(OUT, 'pyramid_view.html'), 'w', encoding='utf-8').write(page)

    print(f"金字塔国家数：{len(pyr['pyramids'])}")
    for cname, p in pyr['pyramids'].items():
        src = '解码自'+','.join(p.get('sources',[])) if p.get('decoded_from_tweet') else '手工录入'
        print(f"  【{cname}】{p['country_type']} · {len(p['layers'])}层 · {src}")
    print(f"输出 → {OUT}/pyramid_view.html")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>09 认证金字塔</title>
<style>
:root{--bg:#f4f1ec;--panel:#fff;--ink:#2a2438;--mut:#8a8398;--line:#e4ded5;
--p1:#3d2f5c;--p2:#5b4789;--p3:#7e6bb0;--p4:#a99bd4;--accent:#c4453f;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:14px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:24px}
.head{display:flex;align-items:center;gap:14px;margin-bottom:18px}
select{background:var(--panel);border:1px solid var(--line);color:var(--ink);padding:9px 14px;border-radius:8px;font-size:14px;min-width:160px}
.hint{color:var(--mut);font-size:13px}
.cname{font-size:24px;font-weight:700;margin:6px 0 2px;display:flex;align-items:center;gap:10px}
.badge{font-size:12px;padding:3px 10px;border-radius:20px;font-weight:500}
.badge.type{background:#efe9f7;color:#5b4789}
.badge.grade{background:#e6f4ea;color:#2e7d46}
.badge.src{background:#fdecec;color:#c4453f}
.tagline{color:#6b6478;font-size:13.5px;margin-bottom:20px;max-width:780px}
.main{display:grid;grid-template-columns:1.1fr 1fr;gap:20px;align-items:start}
.pyramid{display:flex;flex-direction:column;gap:8px}
.layer{border-radius:10px;padding:16px 18px;color:#fff;cursor:pointer;transition:.15s;position:relative}
.layer:hover{transform:translateX(3px);filter:brightness(1.08)}
.layer.sel{outline:3px solid var(--accent);outline-offset:2px}
.layer .lv{font-size:11px;opacity:.7;letter-spacing:1px}
.layer .role{font-size:11px;opacity:.75;float:right}
.layer .ncn{font-size:15px;font-weight:600;margin-top:3px}
.layer .nen{font-size:11.5px;opacity:.8}
.l1{background:linear-gradient(135deg,var(--p1),var(--p2));margin-right:0}
.l2{background:linear-gradient(135deg,var(--p2),var(--p3));margin-right:8%}
.l3{background:linear-gradient(135deg,var(--p3),var(--p4));margin-right:18%}
.l4{background:linear-gradient(135deg,var(--p4),#c3b8e3);margin-right:30%}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;min-height:200px}
.panel .pl{font-size:11px;color:var(--mut);letter-spacing:1px}
.panel h3{font-size:17px;margin:4px 0 2px}
.panel .en{color:var(--mut);font-size:12.5px;margin-bottom:12px}
.panel .dt{font-size:13.5px;color:#4a4458;margin-bottom:14px}
.reg{display:flex;align-items:center;gap:8px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;margin-bottom:6px;font-size:13px}
.reg .no{font-weight:600;color:#5b4789}
.reg .lib{margin-left:auto;font-size:11px;padding:2px 8px;border-radius:12px}
.reg .lib.y{background:#e6f4ea;color:#2e7d46}
.reg .lib.n{background:#fdecec;color:#c4453f}
.sect{margin-top:22px}
.sect h4{font-size:13px;color:var(--mut);margin-bottom:10px;letter-spacing:.5px}
.auth{border-left:3px solid var(--p3);padding:4px 0 4px 12px;margin-bottom:12px}
.auth .an{font-weight:600;font-size:13.5px}
.auth .aa{font-size:11px;color:#fff;background:var(--p3);padding:1px 7px;border-radius:4px;margin-left:6px}
.auth .ad{font-size:12.5px;color:#6b6478;margin-top:2px}
.core .grp{margin-bottom:10px}
.core .gn{font-weight:600;font-size:13px;color:#3d2f5c}
.core .gi{font-size:12.5px;color:#555;margin-top:2px}
.src-link{font-size:12px;color:var(--accent);cursor:pointer;text-decoration:underline;margin-top:4px;display:inline-block}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:8px}
@media(max-width:820px){.main,.two{grid-template-columns:1fr}}
</style></head><body>
<div class="head">
  <select id="country"></select>
  <select id="filter"><option value="">全部体系类型</option><option>自有型</option><option>采纳型</option><option>混合型</option></select>
  <span class="hint">选国家看其汽车型式认证体系金字塔（顶=母法/框架 → 底=最终证书）</span>
</div>
<div id="view"></div>
<script>
const PYR = __PYRAMIDS__;
const sel = document.getElementById('country');
Object.keys(PYR).forEach(c=>{let o=document.createElement('option');o.value=c;o.textContent=c;sel.appendChild(o);});
let curLayer = 0;

function libBadge(n){return n>0?`<span class="lib y">库${n}</span>`:`<span class="lib n">待补充</span>`;}

function render(){
  const c = sel.value; const p = PYR[c]; if(!p)return;
  const srcBadge = p.decoded_from_tweet?`<span class="badge src">解码自推文</span>`:'';
  const layers = p.layers.map((L,i)=>`
    <div class="layer l${i+1} ${i===curLayer?'sel':''}" onclick="pick('${c}',${i})">
      <span class="lv">${L.level}</span><span class="role">${L.role}</span>
      <div class="ncn">${L.name_cn}</div><div class="nen">${L.name_en||''}</div>
    </div>`).join('');
  const L = p.layers[curLayer];
  const regs = (L.regulations||[]).map(r=>`
    <div class="reg"><span class="no">${r.reg_no}</span>${r.name?'<span style="color:#888">'+r.name+'</span>':''}${libBadge(r._lib||0)}</div>`).join('') || '<div style="color:#aaa;font-size:12px">本层无具体法规编号</div>';
  const auths = (p.authorities||[]).map(a=>`
    <div class="auth"><span class="an">${a.name}</span><span class="aa">${a.abbr}</span><div class="ad">${a.desc||''}</div></div>`).join('');
  let core='';
  for(const [cat,groups] of Object.entries(p.core_regulations||{})){
    core+=`<div class="core" style="margin-bottom:14px"><div class="gn" style="font-size:13.5px;border-bottom:1px solid #eee;padding-bottom:4px;margin-bottom:8px">${cat}</div>`;
    core+=groups.map(g=>`<div class="grp"><span class="gn">${g.group}：</span><span class="gi">${g.items}</span></div>`).join('');
    core+='</div>';
  }
  const srcs=(p.sources||[]).map(sid=>`<span class="src-link" title="来源推文">📄 ${sid}${p._source_titles&&p._source_titles[sid]?'：'+p._source_titles[sid]:''}</span>`).join('<br>');

  document.getElementById('view').innerHTML=`
    <div class="cname">${c} <span class="badge type">${p.country_type}</span><span class="badge grade">资料${p.data_grade}</span>${srcBadge}</div>
    <div class="tagline">${p.tagline||''}</div>
    <div class="main">
      <div class="pyramid">${layers}</div>
      <div class="panel">
        <div class="pl">${L.role} · 第 ${curLayer+1} 层</div>
        <h3>${L.name_cn}</h3><div class="en">${L.name_en||''}</div>
        <div class="dt">${L.detail||''}</div>
        ${regs}
      </div>
    </div>
    <div class="two">
      <div class="panel"><div class="sect"><h4>主管机构</h4>${auths||'<span style="color:#aaa">—</span>'}</div></div>
      <div class="panel"><div class="sect"><h4>核心法规</h4>${core||'<span style="color:#aaa">—</span>'}</div>
        ${srcs?'<div class="sect"><h4>来源推文</h4>'+srcs+'</div>':''}</div>
    </div>`;
}
function pick(c,i){curLayer=i;render();}
sel.addEventListener('change',()=>{curLayer=0;render();});
render();
</script></body></html>"""

if __name__ == '__main__':
    build()
