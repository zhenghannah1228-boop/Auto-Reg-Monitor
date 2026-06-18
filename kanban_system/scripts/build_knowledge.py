#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_knowledge.py — 把 insights.json 编译成「知识体系」视图(knowledge.html)

组织轴:维度 → 知识主题 → 法规节点 → (合并要点 / 版本演变 / 跨国对照 / 知识缺口)
与 kanban.html(按推文类型分列)并存:看板回答"最近读了什么",知识树回答"体系长什么样、还缺什么"。

主题映射 THEME_MAP 是可扩展常量:新主题/新关键词只改这里,无需动渲染逻辑。
推文按 topics 关键词 或 法规 match_key 归入主题(可多归属);两边都不命中的进「未归类」桶(诚实可见)。
"""
import json, os, re, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "insights.json")
RLINK = os.path.join(HERE, "..", "output", "reverse_links.json")
OUT = os.path.join(HERE, "..", "output", "knowledge.html")

# ============ 可扩展常量:知识主题映射 ============
# dims: 主要维度编号;topic_kw: topics/title 命中即归入;reg_kw: 法规 match_key 命中即归入
THEME_MAP = [
    {"id":"seat",    "name":"座椅与头枕",        "dims":["1"], "topic_kw":["座椅","头枕","鞭打","零重力"],            "reg_kw":["GB 15083","UN R17","UN R25"]},
    {"id":"light",   "name":"灯光与信号",        "dims":["1"], "topic_kw":["近光灯","自动大灯","灯光","信号灯"],       "reg_kw":["UN R48","UN R148","UN R149"]},
    {"id":"vision",  "name":"视野与HUD",         "dims":["1"], "topic_kw":["视野","HUD","FVA","A柱"],                 "reg_kw":["GB 11562","GB/T 46926","UN R125","UN R176"]},
    {"id":"steer",   "name":"转向系统",          "dims":["1","7"], "topic_kw":["转向","线控"],                        "reg_kw":["GB 11557","UN R12","UN R79"]},
    {"id":"control", "name":"车内操控与标识",     "dims":["1","8"], "topic_kw":["车内开关","信号标志","背光","标志颜色"],"reg_kw":["GB 4094","UN R121"]},
    {"id":"door",    "name":"车门与逃生",        "dims":["1"], "topic_kw":["车门把手","门把手","断电逃生","机械释放"],  "reg_kw":["GB 48001"]},
    {"id":"dim",     "name":"外廓尺寸与凸出物",   "dims":["1"], "topic_kw":["外廓","凸出物","圆角","质量限值"],         "reg_kw":["GB 1589","UN R26"]},
    {"id":"speedo",  "name":"车速与里程表",      "dims":["1","6"], "topic_kw":["车速表","里程表"],                    "reg_kw":["GB 15082","UN R39"]},
    {"id":"tyre",    "name":"应急轮胎与TPMS",    "dims":["1","3"], "topic_kw":["备胎","防爆胎","TPMS","RFWS","EMT"],  "reg_kw":["UN R64","UN R141"]},
    {"id":"brake",   "name":"制动系统",          "dims":["1"], "topic_kw":["制动","ABS","衬垫"],                      "reg_kw":["UN R13","GB 12676","GB 21670"]},
    {"id":"battery", "name":"动力电池安全",      "dims":["4"], "topic_kw":["电池热扩散","REESS","刮底","热失控"],      "reg_kw":["GB 38031","UN R100"]},
    {"id":"passport","name":"电池护照与标识",     "dims":["4","8"], "topic_kw":["电池护照","电池标签","电子标识","标牌"],"reg_kw":["EU 2023/1542"]},
    {"id":"substance","name":"禁限用物质与化学品",  "dims":["2"],     "topic_kw":["RoHS","REACH","POPs","禁限用物质","有害物质","化学品","邻苯二甲酸酯","斯德哥尔摩"],"reg_kw":["EU 2023/1542"]},
    {"id":"adas",    "name":"智能驾驶分级(ADAS→L3)","dims":["7","6"], "topic_kw":["ADAS","DCAS","ALKS","ISA","DMS","自动驾驶","智能速度"],"reg_kw":["UN R79","UN R157","UN R171","UN R130","EU 2021/1958","EU 2019/2144"]},
    {"id":"icv",     "name":"智能网联测评·座舱·隐私",  "dims":["7","6"], "topic_kw":["C-ICAP","智能网联","行车辅助","泊车辅助","智慧座舱","隐私保护","网络安全","座舱","V2X"],"reg_kw":["UN R155","UN R156"]},
    {"id":"cert",    "name":"认证制度与体系",     "dims":["1","9"], "topic_kw":["认证体系","认证制度","型式认证","准入管理","CCC","CMVR","ARAI","CONTRAN","INMETRO","等效认可"],"reg_kw":["EU 2018/858","CMVR","AIS","CONTRAN","UN R95","FMVSS 305","工信部"]},
    {"id":"policy",  "name":"产业与贸易政策",     "dims":["2","5"], "topic_kw":["工业加速","本地化","低碳","原产地","补贴"],"reg_kw":["工业加速法案"]},
]
DIM_NAMES = {"1":"整车准入","2":"环保全链条","3":"射频认证","4":"充电电池","5":"EV补贴",
             "6":"网络安全","7":"ADAS","8":"标签标识","9":"注册监管","10":"随车工具"}
TYPE_CN = {"compare":"对比","interpret":"解读","revision":"修订","system":"体系"}
REGION_ORDER = ["中国","欧盟","欧洲","UN ECE","美国","印度","巴西","通用"]

def esc(s): return html.escape(str(s or ""))

IMG_TOKEN = re.compile(r"\[img\](\S+)")
def kp_html(p):
    """要点渲染:文本转义,[img]路径 标记转 <img>(点击新窗口看原图)"""
    out, last = [], 0
    for m in IMG_TOKEN.finditer(p):
        if p[last:m.start()].strip(): out.append(esc(p[last:m.start()].strip()))
        u = esc(m.group(1))
        out.append(f'<a href="{u}" target="_blank"><img class="kpimg" src="{u}" loading="lazy"></a>')
        last = m.end()
    if p[last:].strip(): out.append(esc(p[last:].strip()))
    return " ".join(out)

def load():
    with open(DATA, encoding="utf-8") as f: ins = json.load(f)["insights"]
    rl = {}
    if os.path.exists(RLINK):
        with open(RLINK, encoding="utf-8") as f: rl = json.load(f)
    return ins, rl

def kw_hit_reg(kw, regs_text):
    """法规关键词匹配,带数字边界:UN R17 不命中 UN R176"""
    return bool(re.search(re.escape(kw) + r"(?!\d)", regs_text))

def assign(ins):
    """每篇推文 → 命中的主题 id 列表(可多归属);未命中 → unassigned"""
    themed = {t["id"]: [] for t in THEME_MAP}
    unassigned = []
    for it in ins:
        text = " ".join(it.get("topics", [])) + " " + it.get("title", "")
        regs = " ".join(r.get("match_key", "") for r in it.get("regulations", []))
        hits = set()
        for t in THEME_MAP:
            if any(k in text for k in t["topic_kw"]) or any(k and kw_hit_reg(k, regs) for k in t["reg_kw"]):
                hits.add(t["id"])
        if hits:
            for h in hits: themed[h].append(it)
        else:
            unassigned.append(it)
    return themed, unassigned

ALL_REG_KW = [k for t in THEME_MAP for k in t["reg_kw"]]
def theme_regs(items, theme):
    """主题下的法规节点:只保留 ①命中本主题 reg_kw 的,或 ②不属于任何主题的散件
    (防止多主题文章把无关法规带进本主题矩阵)"""
    by_region = {}
    for it in items:
        for r in it.get("regulations", []):
            reg = r.get("reg_no") or r.get("match_key")
            mk = r.get("match_key", "") or str(reg)
            if not reg: continue
            mine = any(kw_hit_reg(k, mk) for k in theme["reg_kw"])
            claimed_elsewhere = any(kw_hit_reg(k, mk) for k in ALL_REG_KW)
            if not mine and claimed_elsewhere:
                continue  # 属于别的主题,不进本矩阵
            region = r.get("country") or r.get("region") or "其他"
            by_region.setdefault(region, {})
            by_region[region].setdefault(reg, {"match_key": mk, "ins": []})
            if it["id"] not in [x["id"] for x in by_region[region][reg]["ins"]]:
                by_region[region][reg]["ins"].append(it)
    return by_region

def render_theme(t, items, rlinks):
    if not items: return ""
    by_region = theme_regs(items, t)
    regions = [r for r in REGION_ORDER if r in by_region] + [r for r in by_region if r not in REGION_ORDER]
    # —— 法规对照矩阵(国家 → 法规节点 + 在库/解读徽标)
    reg_html = ""
    for region in regions:
        chips = ""
        for reg, info in by_region[region].items():
            in_lib = rlinks.get(reg, rlinks.get(info["match_key"], {})).get("in_library")
            badge = '<i class="lib y" title="已在法规库,反向链接已挂">库</i>' if in_lib else '<i class="lib n" title="法规库暂无此条(待补充)">缺</i>'
            n = len(info["ins"])
            chips += f'<span class="regchip">{esc(reg)} {badge}<u>{n}篇</u></span>'
        reg_html += f'<div class="regrow"><b>{esc(region)}</b><div class="chips">{chips}</div></div>'
    # —— 合并要点:按 (推文类型) 分三段拍平,标注出处
    pts = {"revision": [], "compare": [], "interpret": [], "system": []}
    for it in items:
        for p in it.get("key_points", []):
            pts.setdefault(it.get("type","interpret"), pts["interpret"]).append((p, it))
    pt_html = ""
    sec_names = [("compare","跨国对照要点"),("revision","版本演变要点"),("interpret","条文解读要点"),("system","体系背景")]
    for k, nm in sec_names:
        if not pts.get(k): continue
        lis = "".join(f'<li>{kp_html(p)} <a class="src" href="{esc(it.get("url") or "kanban.html")}" target="_blank" title="{esc(it["title"])}">[{esc(it["id"].split("-")[-1])}]</a></li>'
                      for p, it in pts[k])
        pt_html += f'<div class="ptsec"><h4>{nm}<i>{len(pts[k])}条</i></h4><ul>{lis}</ul></div>'
    # —— 知识缺口:库缺的编号 + 区域对照缺口
    miss = sorted({reg for region in by_region for reg, info in by_region[region].items()
                   if not rlinks.get(reg, rlinks.get(info["match_key"], {})).get("in_library")})
    covered = {("中国" if region=="中国" else "国际") for region in regions}
    gap_lines = []
    if miss: gap_lines.append("法规库待补充:" + "、".join(esc(m) for m in miss))
    if "中国" not in covered: gap_lines.append("暂无中国侧解读/对照")
    if "国际" not in covered: gap_lines.append("暂无国际侧(UNECE/欧盟/美标)对照")
    gap_html = f'<div class="gap">⚠ 知识缺口:{"; ".join(gap_lines)}</div>' if gap_lines else \
               '<div class="gap ok">✓ 本主题中外对照齐备,相关法规均在库</div>'
    dims = " · ".join(DIM_NAMES.get(d, d) for d in t["dims"])
    arts = "".join(f'<span class="art t-{esc(it.get("type","interpret"))}" title="{esc(it.get("summary",""))}">'
                   f'{TYPE_CN.get(it.get("type"),"")}|{esc(it["title"][:34])}</span>' for it in items)
    return f'''<section class="theme" id="t-{t["id"]}">
  <h2>{esc(t["name"])} <span class="dims">{esc(dims)}</span><span class="cnt">{len(items)} 篇</span></h2>
  <div class="regmatrix">{reg_html}</div>
  {pt_html}
  <div class="arts"><b>来源推文:</b>{arts}</div>
  {gap_html}
</section>'''

SEARCH_BAR = ('<div class="kwbar">'
  '<input id="kw" placeholder="关键词检索:法规编号 / 主题 / 要点 / 国家…(回车或点检索)" autocomplete="off">'
  '<button class="kwbtn" onclick="kwSearch()">🔍 检索</button>'
  '<button class="kwbtn ghost" onclick="kwClear()">清除</button>'
  '<span id="kwstat" class="kwstat"></span></div>')

SEARCH_JS = r"""<script>
var TYPECN={compare:'对比',interpret:'解读',revision:'修订',system:'体系'};
function _esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function _imgify(s){return s.replace(/\[img\](\S+)/g,'<a href="$1" target="_blank"><img class="kpimg" src="$1" loading="lazy"></a>');}
function _hay(it){return [it.title,it.summary,(it.topics||[]).join(' '),(it.key_points||[]).join(' '),
  (it.regulations||[]).map(function(r){return (r.reg_no||'')+' '+(r.match_key||'');}).join(' ')].join(' ').toLowerCase();}
function kwSearch(){
  var raw=(document.getElementById('kw').value||'').trim().toLowerCase();
  var toks=raw.split(/\s+/).filter(Boolean);
  var res=document.getElementById('kwresults'), br=document.getElementById('browse'), stat=document.getElementById('kwstat');
  if(!toks.length){res.style.display='none';br.style.display='';stat.textContent='';return;}
  var hits=(window.INS||[]).filter(function(it){var h=_hay(it);return toks.every(function(t){return h.indexOf(t)>=0;});});
  br.style.display='none';res.style.display='';
  stat.textContent=hits.length+' 篇推文匹配「'+raw+'」';
  if(!hits.length){res.innerHTML='<div class="kwempty">没有匹配的推文。多个词用空格分隔(需都命中)。</div>';return;}
  res.innerHTML='<div class="kwrhd">检索结果 '+hits.length+' 篇 · 点标题看正文</div>'+hits.map(function(it){
    return '<div class="kwhit" onclick="openIns(\''+it.id+'\')">'
      +'<div class="kwhd1"><span class="kwtag t-'+_esc(it.type)+'">'+(TYPECN[it.type]||'')+'</span>'
      +'<span class="kwttl">'+_esc(it.title)+'</span></div>'
      +(it.summary?'<div class="kwsum">'+_esc(it.summary.slice(0,120))+(it.summary.length>120?'…':'')+'</div>':'')
      +'<div class="kwmeta">'+_esc((it.region_focus||[]).join(' / '))+(it.publish_date?' · '+_esc(it.publish_date):'')+(it.author?' · '+_esc(it.author):'')
      +' · '+(it.key_points||[]).length+' 个要点</div></div>';
  }).join('');
}
function openIns(id){
  var it=(window.INS||[]).filter(function(x){return x.id===id;})[0]; if(!it)return;
  var kp=(it.key_points||[]).map(function(p){return '<li>'+_imgify(_esc(p))+'</li>';}).join('');
  var regs=(it.regulations||[]).map(function(r){return '<span class="ireg">'+_esc(r.reg_no||r.match_key||'')+'</span>';}).join('');
  document.getElementById('insbox').innerHTML='<span class="insx" onclick="closeIns()">×</span>'
    +'<h3>'+_esc(it.title)+'</h3>'
    +'<div class="imeta">'+(TYPECN[it.type]||'')+(it.publish_date?' · '+_esc(it.publish_date):'')+(it.author?' · '+_esc(it.author):'')
      +(((it.region_focus||[]).length)?' · '+_esc(it.region_focus.join(' / ')):'')+'</div>'
    +(it.summary?'<p class="isum">'+_esc(it.summary)+'</p>':'')
    +(kp?'<div class="ikp"><b>要点</b><ul>'+kp+'</ul></div>':'')
    +(regs?'<div class="iregs"><b>关联法规</b><div>'+regs+'</div></div>':'')
    +(it.url?'<div style="margin-top:14px"><a class="ilink" href="'+_esc(it.url)+'" target="_blank">阅读原文 →</a></div>':'');
  document.getElementById('insmodal').style.display='flex';
}
function closeIns(){document.getElementById('insmodal').style.display='none';}
function kwClear(){var k=document.getElementById('kw');k.value='';kwSearch();k.focus();}
(function(){var k=document.getElementById('kw');if(k){k.addEventListener('keydown',function(e){if(e.key==='Enter')kwSearch();});k.addEventListener('input',kwSearch);}
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeIns();});})();
</script>"""

def main():
    ins, rl = load()
    themed, unassigned = assign(ins)
    # 按维度组织导航
    nav_by_dim = {}
    for t in THEME_MAP:
        if not themed[t["id"]]: continue
        nav_by_dim.setdefault(t["dims"][0], []).append(t)
    nav = ""
    for d in sorted(nav_by_dim, key=lambda x: int(x)):
        items = "".join(f'<a href="#t-{t["id"]}">{esc(t["name"])}<i>{len(themed[t["id"]])}</i></a>'
                        for t in nav_by_dim[d])
        nav += f'<div class="navdim"><b>{d}. {DIM_NAMES.get(d,d)}</b>{items}</div>'
    body = "".join(render_theme(t, themed[t["id"]], rl) for t in THEME_MAP)
    if unassigned:
        lis = "".join(f'<li>{esc(it["title"])} <i>({TYPE_CN.get(it.get("type"),"")})</i></li>' for it in unassigned)
        body += f'<section class="theme" id="t-none"><h2>未归类 <span class="cnt">{len(unassigned)} 篇</span></h2>' \
                f'<p style="color:#8d8674;font-size:13px">以下推文未命中任何主题关键词——在 build_knowledge.py 的 THEME_MAP 增加主题或关键词后重跑即可归位:</p><ul>{lis}</ul></section>'
        nav += f'<div class="navdim"><b>—</b><a href="#t-none">未归类<i>{len(unassigned)}</i></a></div>'
    n_theme = sum(1 for t in THEME_MAP if themed[t["id"]])
    _slim=[{k:it.get(k) for k in ('id','title','type','summary','key_points','regulations','topics','author','publish_date','region_focus','url')} for it in ins]
    INS_EMBED='<script>window.INS='+json.dumps(_slim,ensure_ascii=False)+';</script>'
    page = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>法规知识体系 · 主题树</title><style>
.kpimg{{display:block;max-width:min(640px,96%);max-height:420px;margin:8px 0 4px;border:1px solid #d8d2c0;border-radius:6px;cursor:zoom-in}}
:root{{--ink:#1a2420;--paper:#f4efe7;--panel:#fcfbf6;--line:#ddd6c6;--accent:#b8754a;--blue:#3a6b8a;
--good:#5a8a4a;--warn:#d98a3a;--muted:#8d8674;--mono:'SF Mono',ui-monospace,Menlo,monospace;
--sans:'Inter','Segoe UI',-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--paper);color:var(--ink);font-family:var(--sans);display:flex;min-height:100vh}}
nav{{width:240px;flex-shrink:0;border-right:1px solid var(--line);padding:18px 14px;position:sticky;top:0;
height:100vh;overflow-y:auto;background:var(--panel)}}
nav h1{{font-size:15px;font-weight:800;margin-bottom:4px}}
nav .sub{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-bottom:14px}}
.navdim{{margin-bottom:12px}}
.navdim b{{display:block;font-family:var(--mono);font-size:10px;color:var(--accent);letter-spacing:.06em;margin-bottom:4px}}
.navdim a{{display:flex;justify-content:space-between;font-size:12.5px;color:var(--ink);text-decoration:none;
padding:4px 8px;border-radius:5px}}
.navdim a:hover{{background:var(--paper)}}
.navdim a i{{font-style:normal;font-family:var(--mono);font-size:10px;color:var(--muted)}}
main{{flex:1;padding:22px 28px;max-width:1060px}}
.theme{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px 24px;margin-bottom:20px}}
.theme h2{{font-size:17px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}
.theme h2 .dims{{font-family:var(--mono);font-size:10px;color:var(--blue)}}
.theme h2 .cnt{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-left:auto}}
.regmatrix{{margin:12px 0 4px}}
.regrow{{display:flex;gap:10px;align-items:baseline;padding:5px 0;border-bottom:1px dashed var(--line)}}
.regrow b{{font-size:12px;min-width:64px;color:var(--ink)}}
.chips{{display:flex;gap:6px;flex-wrap:wrap}}
.regchip{{font-family:var(--mono);font-size:11px;background:var(--paper);border:1px solid var(--line);
border-radius:12px;padding:2px 10px;display:inline-flex;gap:5px;align-items:center}}
.regchip u{{text-decoration:none;color:var(--muted);font-size:9.5px}}
.lib{{font-style:normal;font-size:9px;border-radius:8px;padding:0 5px}}
.lib.y{{background:#deead5;color:#3d6630}}.lib.n{{background:#f5ded4;color:#a8401f}}
.ptsec{{margin-top:14px}}
.ptsec h4{{font-size:12.5px;color:var(--accent)}}
.ptsec h4 i{{font-style:normal;font-family:var(--mono);font-size:9.5px;color:var(--muted);margin-left:6px}}
.ptsec ul{{margin:6px 0 0 18px}}
.ptsec li{{font-size:12.8px;line-height:1.75;margin-bottom:4px}}
.src{{font-family:var(--mono);font-size:9.5px;color:var(--blue);text-decoration:none}}
.arts{{margin-top:14px;display:flex;gap:6px;flex-wrap:wrap;align-items:baseline}}
.arts b{{font-size:11px;color:var(--muted)}}
.art{{font-size:10.5px;border:1px solid var(--line);border-radius:4px;padding:2px 8px;background:var(--paper)}}
.art.t-compare{{border-left:3px solid var(--blue)}}.art.t-revision{{border-left:3px solid var(--warn)}}
.art.t-interpret{{border-left:3px solid var(--good)}}.art.t-system{{border-left:3px solid #7a5ba0}}
.gap{{margin-top:12px;font-size:12px;background:#fdf3e7;border:1px solid #ecd9bb;border-radius:7px;
padding:8px 12px;color:#8a5a14;line-height:1.7}}
.gap.ok{{background:#eef4e9;border-color:#cfdfc2;color:#3d6630}}
.kwbar{{position:sticky;top:0;z-index:6;display:flex;gap:9px;align-items:center;flex-wrap:wrap;
background:var(--paper);padding:10px 0 12px;margin:-6px 0 10px;border-bottom:1px solid var(--line)}}
.kwbar input{{flex:1;min-width:200px;max-width:460px;font-family:var(--sans);font-size:13.5px;
padding:9px 13px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);outline:none}}
.kwbar input:focus{{border-color:var(--accent)}}
.kwbtn{{font-family:var(--sans);font-size:12.5px;padding:9px 16px;border:1px solid var(--accent);
background:var(--accent);color:#fff;border-radius:8px;cursor:pointer}}
.kwbtn.ghost{{background:var(--panel);color:var(--ink);border-color:var(--line)}}
.kwbtn:hover{{opacity:.9}}
.kwstat{{font-family:var(--mono);font-size:11px;color:var(--muted)}}
mark{{background:#ffe9a8;color:inherit;padding:0 1px;border-radius:2px}}
.kwresults{{margin-top:2px}}
.kwrhd{{font-family:var(--mono);font-size:11px;color:var(--muted);margin:2px 0 12px}}
.kwhit{{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--blue);border-radius:9px;padding:12px 16px;margin-bottom:11px;cursor:pointer;transition:.12s}}
.kwhit:hover{{background:var(--paper);border-left-color:var(--accent);transform:translateX(2px)}}
.kwhd1{{display:flex;gap:9px;align-items:baseline}}
.kwtag{{font-size:10px;border-radius:5px;padding:1px 8px;color:#fff;background:var(--blue);flex-shrink:0}}
.kwtag.t-compare{{background:var(--blue)}}.kwtag.t-revision{{background:var(--warn)}}.kwtag.t-interpret{{background:var(--good)}}.kwtag.t-system{{background:#7a5ba0}}
.kwttl{{font-weight:800;font-size:14.5px;color:var(--ink);line-height:1.5}}
.kwsum{{font-size:12.5px;color:var(--ink);opacity:.82;margin-top:6px;line-height:1.65}}
.kwmeta{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:6px}}
.kwempty{{color:var(--muted);font-size:13px;padding:30px;text-align:center}}
.insmodal{{display:none;position:fixed;inset:0;background:rgba(20,24,20,.5);z-index:50;align-items:center;justify-content:center;padding:20px}}
.insbox{{background:var(--panel);border:1px solid var(--line);border-radius:12px;max-width:760px;width:100%;max-height:86vh;overflow-y:auto;padding:24px 28px;position:relative;box-shadow:0 12px 44px rgba(0,0,0,.22)}}
.insx{{position:absolute;top:10px;right:16px;font-size:25px;color:var(--muted);cursor:pointer;line-height:1}}
.insx:hover{{color:var(--accent)}}
.insbox h3{{font-size:18px;font-weight:800;margin:0 24px 6px 0;line-height:1.4}}
.imeta{{font-family:var(--mono);font-size:11px;color:var(--muted);margin-bottom:13px}}
.isum{{font-size:14px;line-height:1.85;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:12px 15px}}
.ikp{{margin-top:16px}}.ikp>b,.iregs>b{{font-size:12.5px;color:var(--accent)}}
.ikp ul{{margin:8px 0 0 18px}}.ikp li{{font-size:13px;line-height:1.85;margin-bottom:8px}}
.iregs{{margin-top:16px}}.ireg{{display:inline-block;font-family:var(--mono);font-size:11px;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:2px 10px;margin:5px 6px 0 0}}
.ilink{{color:var(--blue);font-size:13px;text-decoration:none}}
@media(max-width:760px){{body{{flex-direction:column}}nav{{width:100%;height:auto;position:static}}}}
</style></head><body>
<nav><h1>法规知识体系</h1>
<div class="sub">维度 → 主题 → 法规 · {n_theme} 主题 / {len(ins)} 篇 · {datetime.date.today()}</div>
{nav}
<div class="sub" style="margin-top:14px"><a href="kanban.html" style="color:var(--blue)">→ 推文流看板(按类型)</a></div>
</nav>
<main>{SEARCH_BAR}<div id="kwresults" class="kwresults" style="display:none"></div><div id="browse">{body}</div></main><div id="insmodal" class="insmodal" onclick="if(event.target===this)closeIns()"><div class="insbox" id="insbox"></div></div>{INS_EMBED}{SEARCH_JS}</body></html>'''
    with open(OUT, "w", encoding="utf-8") as f: f.write(page)
    n_un = len(unassigned)
    print(f"主题 {n_theme} 个(共配置 {len(THEME_MAP)}),覆盖推文 {len(ins)-n_un}/{len(ins)} 篇,未归类 {n_un}")
    print(f"输出 → {os.path.abspath(OUT)}")

if __name__ == "__main__":
    main()
