#!/usr/bin/env node
/* 认证体系世界地图 · 设计交付导出
 * 复用 index.html 里的同一套分类(STD_FAMILY/GROUP_STYLE/CN2GEO/EU_MEMBERS),
 * 与 data/cert_pyramid.json + data/world_geo.json,产出给设计做 PPT 的资产:
 *   cert_map_clean.svg     纯地图矢量(透明底,只有上色国家轮廓,最适合拖进 PPT/AI 改配色)
 *   cert_map_composed.svg  含标题+图例的成稿矢量(纸面底色,直接当一页视觉)
 *   cert_map_colors.csv     国家→标准体系→配色 对照表(设计可据此换品牌色)
 * 运行:node export/build_cert_map_export.js
 */
const fs=require("fs"),path=require("path");
const ROOT=path.join(__dirname,"..");
const echarts=require(path.join(ROOT,"echarts.min.js"));

// —— 从 index.html 抽取分类常量,保证与线上地图同源,不重复维护 ——
const html=fs.readFileSync(path.join(ROOT,"index.html"),"utf8");
function grab(name){const m=html.match(new RegExp("const "+name+"=(\\{[\\s\\S]*?\\}|\\[[\\s\\S]*?\\]);"));if(!m)throw new Error("missing "+name);return eval("("+m[1]+")");}
const STD_FAMILY=grab("STD_FAMILY"),GROUP_STYLE=grab("GROUP_STYLE"),CN2GEO=grab("CN2GEO"),EU_MEMBERS=grab("EU_MEMBERS");
const GROUP_ORDER=["EU","FMVSS","CMVSS","KMVSS","ADR","JAPAN","GB","AIS","EAEU","NAT","hybrid","recognition"];
const certGroupOf=rec=>rec.system_type==="own_full"?(STD_FAMILY[rec.country]||"NAT"):rec.system_type;

const CERT=JSON.parse(fs.readFileSync(path.join(ROOT,"data/cert_pyramid.json"))).cert_systems;
const GEO=JSON.parse(fs.readFileSync(path.join(ROOT,"data/world_geo.json")));
echarts.registerMap("world",GEO);

// —— 装配 地图要素→认证记录(与 buildCertMap 一致:直接条目优先,欧盟成员兜底) ——
const fill={};
for(const cn in CERT){const g=CN2GEO[cn];if(g)fill[g]={cn,rec:CERT[cn]};}
if(CERT["欧盟"])EU_MEMBERS.forEach(g=>{if(!fill[g])fill[g]={cn:"欧盟",rec:CERT["欧盟"],viaEU:true};});
const cnt={};
const seriesData=Object.entries(fill).map(([g,o])=>{const grp=certGroupOf(o.rec);cnt[grp]=(cnt[grp]||0)+1;
  return {name:g,itemStyle:{areaColor:GROUP_STYLE[grp].color}};});

function renderSVG(opt,w,h){
  const c=echarts.init(null,null,{renderer:"svg",ssr:true,width:w,height:h});
  c.setOption(opt);const s=c.renderToSVGString();c.dispose();return s;
}
const mapSeries=extra=>Object.assign({type:"map",map:"world",roam:false,nameProperty:"name",
  itemStyle:{areaColor:"#efece1",borderColor:"#cfc9b8",borderWidth:.4},
  emphasis:{disabled:true},label:{show:false},data:seriesData},extra);

// 1) 纯地图(透明底)——给设计自由摆放/改色
fs.writeFileSync(path.join(__dirname,"cert_map_clean.svg"),
  renderSVG({backgroundColor:"transparent",series:[mapSeries({left:10,right:10,top:10,bottom:10})]},2400,1240));

// 2) 成稿(标题 + 图例)——可直接当一页 PPT 视觉
const present=GROUP_ORDER.filter(g=>cnt[g]);
const own=present.filter(g=>!["hybrid","recognition"].includes(g));
const others=present.filter(g=>["hybrid","recognition"].includes(g));
const graphic=[];
let gx=70,gy=1090;const sw=26,rowH=46,colW=470;
function legendBlock(title,keys,x0,y0){
  const els=[{type:"text",left:x0,top:y0-34,style:{text:title,font:"700 26px sans-serif",fill:"#1a2420"}}];
  keys.forEach((k,i)=>{const col=Math.floor(i/4),row=i%4;const x=x0+col*colW,y=y0+row*rowH;
    els.push({type:"rect",left:x,top:y,shape:{width:sw,height:sw,r:4},style:{fill:GROUP_STYLE[k].color}});
    els.push({type:"text",left:x+sw+12,top:y+3,style:{text:GROUP_STYLE[k].label+"  ("+cnt[k]+")",font:"22px sans-serif",fill:"#3a4a44"}});
  });
  return els;
}
graphic.push(...legendBlock("自有完整型式批准 · 按标准体系",own,70,gy));
graphic.push(...legendBlock("其他体系",others,70+3*colW+30,gy));
function composedOpt(font){
  const ff=font||"sans-serif",serif=font||"serif";
  const g=JSON.parse(JSON.stringify(graphic));
  g.forEach(e=>{if(e.type==="text"&&e.style&&e.style.font)e.style.font=e.style.font.replace(/(sans-serif|serif)$/,ff);});
  return {backgroundColor:"#f4f1e8",
    title:{text:"全球汽车型式认证体系分布",subtext:"同一认证标准体系同色 · 自有完整型式按 EU-WVTA / FMVSS / KMVSS / ADR / CMVSS / GB / AIS / EAEU 等细分",
      left:70,top:48,textStyle:{color:"#1a2420",fontSize:46,fontWeight:900,fontFamily:serif},
      subtextStyle:{color:"#6a675c",fontSize:22,fontFamily:ff}},
    graphic:g, series:[mapSeries({left:40,right:40,top:170,bottom:330})]};
}
// 设计用矢量(通用字体,设计机上用其品牌字渲染)
fs.writeFileSync(path.join(__dirname,"cert_map_composed.svg"),renderSVG(composedOpt(null),2400,1350));
// 直接可用的高清 PNG:用本机 CJK 字体渲染中文,经 SVG→PNG
if(process.env.EMIT_PNG){
  fs.writeFileSync("/tmp/_cjk.svg",renderSVG(composedOpt("WenQuanYi Zen Hei"),2400,1350));
}

// 3) 配色清单 CSV
const rows=[["国家_中文","地图要素_英文","体系类别","标准体系","配色HEX","数据来源"]];
Object.entries(fill).sort((a,b)=>a[1].rec.system_type.localeCompare(b[1].rec.system_type)).forEach(([g,o])=>{
  const grp=certGroupOf(o.rec);
  rows.push([o.rec.country||o.cn,g,o.rec.system_type,GROUP_STYLE[grp].label,GROUP_STYLE[grp].color,o.viaEU?"欧盟成员兜底":"cert_pyramid.json"]);
});
fs.writeFileSync(path.join(__dirname,"cert_map_colors.csv"),"﻿"+rows.map(r=>r.map(c=>'"'+String(c).replace(/"/g,'""')+'"').join(",")).join("\r\n"));

// 4) 自包含交互 HTML —— 设计可本地打开、缩放、用工具栏「保存为图片」导出高清 PNG
const ECHARTS=fs.readFileSync(path.join(ROOT,"echarts.min.js"),"utf8");
const DATA={geo:GEO,seriesData,cnt,GROUP_STYLE,GROUP_ORDER,
  meta:Object.fromEntries(Object.entries(fill).map(([g,o])=>[g,{country:o.rec.country||o.cn,viaEU:!!o.viaEU,
    grp:certGroupOf(o.rec),system_type:o.rec.system_type,confidence:o.rec.confidence||"",
    summary:o.rec.summary||"",auth:(o.rec.sections&&o.rec.sections.authorities&&o.rec.sections.authorities[0]&&o.rec.sections.authorities[0].name)||""}]))};
const SYS_LABEL={own_full:"自有完整型式批准",hybrid:"混合型",recognition:"采信外部型"};
const CONF_LABEL={A:"资料充分 A",B:"B",C:"资料有限 C"};
const standalone=`<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>全球汽车型式认证体系分布 · 设计交付</title>
<style>
:root{--ink:#1a2420;--paper:#f4f1e8;--panel:#fcfbf6;--muted:#8d8674;--line:#d8d2c0}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1480px;margin:0 auto;padding:22px}
h1{font-family:Georgia,serif;font-size:30px;margin:0 0 2px}
.sub{color:var(--muted);font-size:13px;margin-bottom:14px}
#chart{width:100%;height:760px;background:var(--panel);border:1px solid var(--line);border-radius:10px}
.legend{display:flex;flex-wrap:wrap;gap:7px 18px;margin-top:14px;font-size:12.5px}
.legend .hd{width:100%;font-weight:700;margin-top:6px}
.legend .li{display:flex;gap:7px;align-items:center;color:#3a4a44}
.legend .sw{width:13px;height:13px;border-radius:3px}
.tip{font-size:11px;color:var(--muted);margin-top:8px}
</style></head><body><div class="wrap">
<h1>全球汽车型式认证体系分布</h1>
<div class="sub">同一认证标准体系同色 · 自有完整型式按 EU-WVTA / FMVSS / CMVSS / KMVSS / ADR / 日本 / GB / AIS / EAEU 等细分。右上角工具栏可缩放、「保存为图片」导出高清 PNG。</div>
<div id="chart"></div>
<div class="legend" id="legend"></div>
<div class="tip">数据来源:汽车法规库监控台 · 认证金字塔(09)。中国台湾/香港在底图并入中国;UNECE/GSO/东盟等组织不单独着色;欧盟成员按 EU-WVTA 统一着色。</div>
</div>
<script>${ECHARTS}</script>
<script>
const D=${JSON.stringify(DATA)},SYS_LABEL=${JSON.stringify(SYS_LABEL)},CONF_LABEL=${JSON.stringify(CONF_LABEL)};
const E=s=>String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
echarts.registerMap("world",D.geo);
const ch=echarts.init(document.getElementById("chart"));
ch.setOption({backgroundColor:"transparent",
 toolbox:{right:16,top:10,feature:{saveAsImage:{name:"全球认证体系分布",pixelRatio:3,title:"保存为图片",backgroundColor:"#f4f1e8"},restore:{title:"复位"}}},
 tooltip:{trigger:"item",confine:true,backgroundColor:"#fcfbf6",borderColor:"#d8d2c0",textStyle:{color:"#1a2420",fontSize:12},
  extraCssText:"max-width:330px;white-space:normal;box-shadow:0 6px 24px rgba(26,36,32,.18)",
  formatter:p=>{const m=D.meta[p.name];if(!m)return "<b>"+E(p.name)+"</b><br><span style='color:#8d8674'>暂无认证体系数据</span>";
   const gs=D.GROUP_STYLE[m.grp]||{label:m.system_type,color:"#d8d2c0"};
   return "<div style='font-weight:800;font-size:13px;margin-bottom:3px'>"+E(m.country)+(m.viaEU?" <span style='color:#8d8674'>("+E(p.name)+" · 欧盟成员)</span>":"")+"</div>"
    +"<div style='margin:3px 0'><span style='display:inline-block;width:9px;height:9px;border-radius:50%;background:"+gs.color+";margin-right:5px'></span><b style='color:"+gs.color+"'>"+E(gs.label)+"</b>"+(m.confidence?" · 资料 "+E(CONF_LABEL[m.confidence]||m.confidence):"")+"</div>"
    +(m.system_type==="own_full"?"<div style='color:#8d8674;font-size:11px;margin-top:-1px'>类别:自有完整型式批准</div>":"")
    +(m.summary?"<div style='color:#3a4a44;line-height:1.55;margin-top:4px'>"+E(m.summary)+"</div>":"")
    +(m.auth?"<div style='color:#8d8674;margin-top:5px;font-size:11px'>主管机构:"+E(m.auth)+"</div>":"");}},
 series:[{type:"map",map:"world",roam:true,zoom:1.2,scaleLimit:{min:1,max:8},nameProperty:"name",selectedMode:false,
  itemStyle:{areaColor:"#efece1",borderColor:"#cfc9b8",borderWidth:.5},
  emphasis:{itemStyle:{areaColor:"#c6502a"},label:{show:false}},label:{show:false},data:D.seriesData}]});
window.addEventListener("resize",()=>ch.resize());
const ownG=["EU","FMVSS","CMVSS","KMVSS","ADR","JAPAN","GB","AIS","EAEU","NAT"];
const li=g=>D.cnt[g]?"<div class='li'><span class='sw' style='background:"+D.GROUP_STYLE[g].color+"'></span>"+E(D.GROUP_STYLE[g].label)+" <b style='color:#8d8674'>"+D.cnt[g]+"</b></div>":"";
document.getElementById("legend").innerHTML="<div class='hd'>自有完整型式批准 · 按标准体系</div>"+ownG.map(li).join("")
 +"<div class='hd'>其他体系</div>"+["hybrid","recognition"].map(li).join("")
 +"<div class='li' style='color:#8d8674'><span class='sw' style='background:#efece1;border:1px solid #cfc9b8'></span>暂无数据</div>";
</script></body></html>`;
fs.writeFileSync(path.join(__dirname,"cert_map_interactive.html"),standalone);

console.log("已着色国家/地区:",Object.keys(fill).length);
console.log("体系分布:",GROUP_ORDER.filter(g=>cnt[g]).map(g=>GROUP_STYLE[g].label+"="+cnt[g]).join(" / "));
console.log("输出:export/cert_map_clean.svg / cert_map_composed.svg / cert_map_colors.csv");
