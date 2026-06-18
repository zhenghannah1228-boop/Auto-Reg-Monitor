#!/usr/bin/env python3
"""
build_kanban.py — 从 insights.json 生成看板与反向链接清单

输出：
  output/kanban.html       — 可交互的解读看板（按类型分列，可筛选维度/地区/搜索）
  output/reverse_links.json — 法规编号 → 解读列表（用于写回法规库 Excel 的"解读链接"列）
  output/reverse_links.csv  — 同上，CSV 便于人工查看
"""
import json, os, sys, html, csv

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'data', 'insights.json')
OUT = os.path.join(ROOT, 'output')
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
from matcher import build_library_index, annotate_matches

TYPE_LABEL = {"compare": "对比解读", "interpret": "文本解读", "revision": "修订解读", "system": "体系科普"}
TYPE_COLOR = {"compare": "#6366f1", "interpret": "#0891b2", "revision": "#d97706", "system": "#16a34a"}

def build():
    db = json.load(open(DATA, encoding='utf-8'))
    insights = db['insights']
    dim_map = db['dimension_map']
    lib_index = build_library_index()
    annotate_matches(insights, lib_index)

    # ---------- 反向链接：法规编号 -> [解读] ----------
    reverse = {}
    for it in insights:
        for reg in it['regulations']:
            key = reg['reg_no']
            reverse.setdefault(key, {
                "reg_no": reg['reg_no'], "match_key": reg['match_key'],
                "region": reg['region'], "country": reg['country'],
                "in_library": reg.get('_matched_count', 0) > 0,
                "library_hits": reg.get('_matched', []),
                "insights": []
            })
            reverse[key]["insights"].append({
                "id": it['id'], "title": it['title'],
                "type": it['type'], "url": it.get('url', '')
            })

    json.dump(reverse, open(os.path.join(OUT, 'reverse_links.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    with open(os.path.join(OUT, 'reverse_links.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['法规编号', '区域', '国家', '是否在法规库', '解读条数', '解读ID', '解读标题', '解读类型', '链接'])
        for key, v in reverse.items():
            for ins in v['insights']:
                w.writerow([v['reg_no'], v['region'], v['country'],
                            '是' if v['in_library'] else '否（待补充）',
                            len(v['insights']), ins['id'], ins['title'],
                            TYPE_LABEL.get(ins['type'], ins['type']), ins['url']])

    # ---------- 看板 HTML ----------
    cards_json = json.dumps(insights, ensure_ascii=False)
    dim_json = json.dumps(dim_map, ensure_ascii=False)
    page = HTML_TEMPLATE.replace('__CARDS__', cards_json).replace('__DIMS__', dim_json)
    open(os.path.join(OUT, 'kanban.html'), 'w', encoding='utf-8').write(page)

    # ---------- 控制台小结 ----------
    print(f"解读总数：{len(insights)}")
    by_type = {}
    for it in insights:
        by_type[it['type']] = by_type.get(it['type'], 0) + 1
    print("按类型：", {TYPE_LABEL[k]: v for k, v in by_type.items()})
    linked = sum(1 for v in reverse.values() if v['in_library'])
    print(f"涉及法规编号：{len(reverse)}，其中 {linked} 条已在法规库中（可直接反向挂链），"
          f"{len(reverse)-linked} 条待法规库补充")
    print(f"输出 → {OUT}/kanban.html, reverse_links.json, reverse_links.csv")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>法规解读看板</title>
<style>
:root{--bg:#0f1115;--card:#1a1d24;--line:#2a2e38;--txt:#e6e8ec;--mut:#9aa0ac;
--compare:#6366f1;--interpret:#0891b2;--revision:#d97706;--system:#16a34a;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:24px}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:20px}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;align-items:center}
input,select{background:var(--card);border:1px solid var(--line);color:var(--txt);
padding:8px 12px;border-radius:8px;font-size:13px}
input{flex:1;min-width:200px}
#qbtn{flex:0 0 auto;cursor:pointer;background:var(--compare,#3a6b8a);color:#fff;border-color:transparent;font-size:13px;padding:8px 16px}
#qbtn:hover{opacity:.9}
.board{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;align-items:start}
.col{background:rgba(255,255,255,.02);border:1px solid var(--line);border-radius:12px;padding:12px;min-height:120px}
.col h2{font-size:14px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.dot{width:10px;height:10px;border-radius:50%}
.count{margin-left:auto;color:var(--mut);font-weight:400;font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:12px;cursor:pointer;transition:.15s}
.card:hover{border-color:#444a58;transform:translateY(-1px)}
.card .t{font-weight:600;font-size:14px;margin-bottom:6px;line-height:1.4}
.card .s{color:var(--mut);font-size:12.5px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.tag{font-size:11px;padding:2px 8px;border-radius:20px;background:rgba(255,255,255,.06);color:var(--mut)}
.tag.reg{background:rgba(99,102,241,.18);color:#a5b4fc}
.tag.lib{background:rgba(16,185,129,.18);color:#6ee7b7}
.tag.nolib{background:rgba(239,68,68,.15);color:#fca5a5}
.meta{font-size:11px;color:var(--mut);margin-top:8px}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;padding:24px;z-index:10}
.modal.on{display:flex}
.box{background:var(--card);border:1px solid var(--line);border-radius:14px;max-width:680px;width:100%;max-height:85vh;overflow:auto;padding:26px}
.box h2{font-size:19px;margin-bottom:8px}
.box .kp{margin:14px 0}
.box .kp li{margin:6px 0 6px 18px}
.kpimg{display:block;max-width:96%;max-height:420px;margin:8px 0 4px;border:1px solid #3a4150;border-radius:6px;cursor:zoom-in}
.box .reglist a,.box .reglist span{display:inline-block;margin:4px 6px 4px 0;padding:4px 10px;border-radius:8px;background:rgba(255,255,255,.06);color:#a5b4fc;text-decoration:none;font-size:12.5px}
.close{float:right;cursor:pointer;color:var(--mut);font-size:22px;line-height:1}
@media(max-width:760px){.board{grid-template-columns:1fr}}
</style></head><body>
<h1>法规解读看板</h1>
<div class="sub">推文解读数据库 · 三类承载（对比 / 文本 / 修订）· 自动关联法规库</div>
<div class="controls">
  <input id="q" placeholder="搜索标题 / 法规编号 / 主题…">
  <button id="qbtn" onclick="render()">🔍 检索</button>
  <select id="dim"><option value="">全部维度</option></select>
  <select id="region"><option value="">全部地区</option></select>
</div>
<div class="board">
  <div class="col" data-type="compare"><h2><span class="dot" style="background:var(--compare)"></span>对比解读<span class="count" id="c-compare"></span></h2><div id="col-compare"></div></div>
  <div class="col" data-type="interpret"><h2><span class="dot" style="background:var(--interpret)"></span>文本解读<span class="count" id="c-interpret"></span></h2><div id="col-interpret"></div></div>
  <div class="col" data-type="revision"><h2><span class="dot" style="background:var(--revision)"></span>修订解读<span class="count" id="c-revision"></span></h2><div id="col-revision"></div></div>
  <div class="col" data-type="system"><h2><span class="dot" style="background:var(--system)"></span>体系科普<span class="count" id="c-system"></span></h2><div id="col-system"></div></div>
</div>
<div class="modal" id="modal"><div class="box" id="box"></div></div>
<script>
const DATA = __CARDS__;
const DIMS = __DIMS__;
const TYPE_LABEL={compare:"对比解读",interpret:"文本解读",revision:"修订解读",system:"体系科普"};
const dimSel=document.getElementById('dim');
Object.entries(DIMS).forEach(([k,v])=>{let o=document.createElement('option');o.value=k;o.textContent=k+" "+v;dimSel.appendChild(o);});
const regions=[...new Set(DATA.flatMap(d=>d.region_focus||[]))];
const regSel=document.getElementById('region');
regions.forEach(r=>{let o=document.createElement('option');o.value=r;o.textContent=r;regSel.appendChild(o);});

function card(d){
  const regTags=(d.regulations||[]).map(r=>{
    const inLib=(r._matched_count||0)>0;
    return `<span class="tag reg">${r.reg_no}</span>`+
      (inLib?`<span class="tag lib">库✓</span>`:`<span class="tag nolib">待补充</span>`);
  }).join('');
  const dimTags=(d.dimensions||[]).map(x=>`<span class="tag">${x} ${DIMS[x]||''}</span>`).join('');
  return `<div class="card" data-id="${d.id}">
    <div class="t">${d.title}</div>
    <div class="s">${d.summary||''}</div>
    <div class="tags">${regTags}${dimTags}</div>
    <div class="meta">${d.publish_date||''} · ${d.author||''}</div>
  </div>`;
}
function render(){
  const q=document.getElementById('q').value.trim().toLowerCase();
  const dim=dimSel.value, reg=regSel.value;
  ['compare','interpret','revision','system'].forEach(t=>{
    const items=DATA.filter(d=>d.type===t)
      .filter(d=>!dim||(d.dimensions||[]).includes(dim))
      .filter(d=>!reg||(d.region_focus||[]).includes(reg))
      .filter(d=>{if(!q)return true;const blob=(d.title+JSON.stringify(d.regulations)+(d.topics||[]).join()+(d.summary||'')+(d.key_points||[]).join()).toLowerCase();return q.split(' ').filter(Boolean).every(t=>blob.includes(t));});
    document.getElementById('col-'+t).innerHTML=items.map(card).join('')||'<div style="color:#666;font-size:12px;padding:8px">无</div>';
    document.getElementById('c-'+t).textContent=items.length;
  });
}
function openModal(d){
  const regs=(d.regulations||[]).map(r=>{
    const inLib=(r._matched_count||0)>0;
    const label=r.reg_no+(inLib?` · 法规库${r._matched_count}条`:' · 待补充');
    return r.url?`<a href="${r.url}" target="_blank">${label}</a>`:`<span>${label}</span>`;
  }).join('');
  const kp=(d.key_points||[]).map(p=>`<li>${p.replace(/\[img\](\S+)/g,'<a href="$1" target="_blank"><img class="kpimg" src="$1" loading="lazy"></a>')}</li>`).join('');
  document.getElementById('box').innerHTML=`<span class="close" onclick="document.getElementById('modal').classList.remove('on')">×</span>
    <h2>${d.title}</h2>
    <div class="meta">${TYPE_LABEL[d.type]} · ${d.publish_date||''} · ${d.author||''} · ${(d.region_focus||[]).join(' / ')}</div>
    <p style="margin-top:12px;color:#c8ccd4">${d.summary||''}</p>
    ${kp?`<div class="kp"><b>要点</b><ul>${kp}</ul></div>`:''}
    <div style="margin-top:14px"><b>关联法规</b><div class="reglist" style="margin-top:8px">${regs||'<span>无</span>'}</div></div>
    ${d.url?`<div style="margin-top:16px"><a href="${d.url}" target="_blank" style="color:#a5b4fc">阅读原文 →</a></div>`:''}`;
  document.getElementById('modal').classList.add('on');
}
document.addEventListener('click',e=>{
  const c=e.target.closest('.card');
  if(c){const d=DATA.find(x=>x.id===c.dataset.id);openModal(d);}
  if(e.target.id==='modal')e.target.classList.remove('on');
});
['q','dim','region'].forEach(id=>document.getElementById(id).addEventListener('input',render));
render();
</script></body></html>"""

if __name__ == '__main__':
    build()
