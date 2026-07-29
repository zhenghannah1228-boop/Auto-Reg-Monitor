// 2026-07-28 数据核实回归测试。用法:
//   node tools/verify_reg_data.mjs
// 依赖 playwright(全局或本地安装均可);Chromium 路径可用 PW_CHROMIUM 覆盖。
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
import fs from 'fs';
const REPO=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const cert=JSON.parse(fs.readFileSync(REPO+'/data/cert_pyramid.json','utf8')).cert_systems;
const browser=await chromium.launch({executablePath: process.env.PW_CHROMIUM || undefined});
let fail=0;
const ok=(c,m)=>{ console.log((c?'  PASS  ':'  FAIL  ')+m); if(!c)fail++; };
const IGNORE=/fetch|supabase|config|net::|Failed to load resource|CORS|ERR_FILE/i;

async function open(rel){
  const page=await browser.newPage();
  const errs=[];
  page.on('pageerror',e=>errs.push('pageerror: '+e.message));
  page.on('console',m=>{ if(m.type()==='error') errs.push('console: '+m.text()); });
  await page.goto('file://'+REPO+'/'+rel,{waitUntil:'load'});
  await page.waitForTimeout(900);
  return {page,errs:errs.filter(e=>!IGNORE.test(e))};
}

console.log('\n=== emark_assessment.html ===');
{
  const {page,errs}=await open('emark/emark_assessment.html');
  ok(errs.length===0,'无无关外的 JS 报错'+(errs.length?': '+errs.join(' | '):''));
  const d=await page.evaluate(()=>({
    accepts:EMARK_ACCEPT.accepts.map(x=>x[0]),
    refs:EMARK_ACCEPT.refs.map(x=>x[0]),
    own:EMARK_ACCEPT.own.map(x=>x[0]),
    src:EMARK_SRC,
    vn:(EMARK_ACCEPT.accepts.find(x=>x[0]==='越南')||[])[1]||''
  }));
  ok(d.accepts.length===4 && !d.accepts.includes('埃及'),`采信档 4 国且不含埃及 → ${d.accepts.join('/')}`);
  ok(d.refs.length===16 && d.refs.includes('埃及'),`参照档 16 国且含埃及 (实际 ${d.refs.length})`);
  ok(!d.refs.includes('印度尼西亚') && !d.refs.includes('伊拉克'),'印尼/伊拉克已移出参照档');
  ok(d.own.length===4 && d.own.includes('印度尼西亚') && d.own.includes('伊拉克'),`own 档 4 项 → ${d.own.join('/')}`);
  ok(d.refs.includes('乌拉圭'),'乌拉圭保留在参照档');
  ok(/中国产车/.test(d.vn) && /<b>/.test(d.vn),'越南行含中国产车警示且带 <b> 标记');
  ok(!/GSO 42/.test(d.src) && !/IMR 2025/.test(d.src),'EMARK_SRC 已清除 GSO 42 / IMR 2025');
  ok(/截至 2026-07/.test(d.src),'EMARK_SRC 含时点声明');
  // v2 断言：措辞更新（档位不变）
  const v2=await page.evaluate(()=>{
    const get=(list,cn)=>((EMARK_ACCEPT[list].find(x=>x[0]===cn)||[])[1]||'');
    return {iraq:get('own','伊拉克'), kg:get('refs','吉尔吉斯斯坦'), ar:get('refs','阿根廷'),
            il:get('accepts','以色列'), inn:get('refs','印度'), gh:get('refs','加纳'),
            allText:JSON.stringify(EMARK_ACCEPT)+EMARK_SRC};
  });
  ok(/2026-01-01/.test(v2.iraq) && !/拟实施/.test(v2.iraq),'伊拉克整车条款已更新为已实施');
  ok(!/勿假定/.test(v2.kg) && /无权威依据表明影响/.test(v2.kg),'吉尔吉斯 OTTS 警示已改为中性表述');
  ok(/Gestión de Política Industrial/.test(v2.ar),'阿根廷主管机关已更新为 Res.18/2026 后机构');
  ok(/אישור דגם/.test(v2.il) && /非批准制度/.test(v2.il),'以色列 IMR 已改述为声明表、型批正名 אישור דגם');
  ok(/Safety Critical Components/.test(v2.inn) && !/pretest inspection 且国内生产/.test(v2.inn),'印度标题补全且错误括注已移除');
  ok(/Act 1078/.test(v2.gh) && /版本自相矛盾/.test(v2.gh),'加纳母法更正为 Act 1078 且已记版本冲突');
  ok(!/OTTC/.test(v2.allText) && /OTTS/.test(v2.allText),'OTTC 已全库统一为 OTTS');
  ok(!/Dirección Nacional de Industria/.test(v2.allText),'已废止的阿根廷机关名不再出现');
  // 渲染：越南 <b> 是否真的加粗（note 未转义）
  const bold=await page.evaluate(()=>{
    if(typeof reachData!=='function') return null;
    if(typeof sel==='object'&&sel) sel.role='OEM';
    const r=reachData().rows.find(x=>x.cn==='越南');
    if(!r) return null;
    const d=document.createElement('div'); d.innerHTML=`<span>${r.note}</span>`;
    return d.querySelector('b')?d.querySelector('b').textContent.slice(0,12):'NO_B';
  });
  ok(bold && bold!=='NO_B', `越南 note 中 <b> 可正常渲染为粗体 (取到: ${bold})`);
  const ghost=await page.evaluate(()=>{
    if(typeof sel==='object'&&sel) sel.role='OEM';
    const rows=reachData().rows.map(r=>r.cn);
    return ['印度尼西亚','伊拉克','中国','巴西'].filter(c=>rows.includes(c));
  });
  ok(ghost.length===0,`own 档国家不进可通行名单 (泄漏: ${ghost.join(',')||'无'})`);
  await page.close();
}

console.log('\n=== index.html · 13 合规路径 ===');
{
  const {page,errs}=await open('index.html');
  ok(errs.length===0,'无无关外的 JS 报错'+(errs.length?': '+errs.join(' | '):''));
  const d=await page.evaluate((cert)=>{
    CERT=cert;
    const gcc=['沙特','阿联酋','科威特','卡塔尔','阿曼','巴林'];
    const res={blocKeys:Object.keys(PATH_BLOCS), tokensGCC:PATH_TOKENS.GCC};
    res.saudi=anchorConfers('沙特');
    res.eu=anchorConfers('欧盟');
    res.gso=anchorConfers('GSO');
    // 以沙特为锚点时，一证通行集合
    const set=new Set(); (res.saudi.blocs||[]).forEach(bn=>PATH_BLOCS[bn].forEach(c=>set.add(c)));
    res.saudiBlocSet=[...set];
    const set2=new Set(); (res.eu.blocs||[]).forEach(bn=>PATH_BLOCS[bn].forEach(c=>set2.add(c)));
    res.euBlocSet=[...set2];
    res.gccInCert=gcc.filter(c=>cert[c]);
    return res;
  },cert);
  ok(!d.blocKeys.includes('GCC') && d.blocKeys.length===2,`PATH_BLOCS 仅剩 ${d.blocKeys.join('/')}`);
  ok(Array.isArray(d.tokensGCC) && d.tokensGCC.length===3,'PATH_TOKENS.GCC 保留未动');
  ok(d.saudi.blocs.length===0,'锚点=沙特 时无一证通行区块');
  ok(d.saudiBlocSet.length===0,`锚点=沙特 时其余 GCC 国不再落入一证通行 (集合: ${d.saudiBlocSet.join(',')||'空'})`);
  ok(d.gso.blocs.length===0,'锚点=GSO 时无一证通行区块');
  ok(d.eu.blocs.includes('EU-WVTA') && d.euBlocSet.length===9,`锚点=欧盟 时 EU-WVTA 区块 9 国不变`);
  ok(d.gccInCert.length===6,'6 个 GCC 国仍在 cert_systems 中（仅改档位，未丢数据）');
  await page.close();
}

console.log('\n=== 关税字段 ===');
{
  const t=k=>cert[k].tariff;
  ok(/50%/.test(t('墨西哥').cbu_passenger) && /2026-01-01/.test(t('墨西哥').cbu_passenger),'墨西哥 50% + 生效日');
  ok(/İGV/.test(t('土耳其').cbu_passenger) && /7,000/.test(t('土耳其').cbu_passenger),'土耳其 İGV + 中国产附加税');
  ok(/≤1600cc 30%/.test(t('埃及').cbu_passenger) && /勿再沿用/.test(t('埃及').cbu_passenger),'埃及 30%/100%，旧三档已标注作废');
  ok(/2026-07-01/.test(t('巴西').cbu_ev||''),'巴西 EV 说明已补');
  ok(/2025-12-31/.test(t('印度尼西亚').cbu_ev||''),'印尼 EV 优惠到期说明已补');
}

console.log('\n=== ad / ev / cyber 页 ===');
for(const f of ['emark/ad_assessment.html','emark/ev_assessment.html','emark/cyber_assessment.html']){
  const {page,errs}=await open(f);
  ok(errs.length===0,`${f} 无 JS 报错`+(errs.length?': '+errs.join(' | '):''));
  await page.close();
}

await browser.close();
console.log('\n'+(fail?`✗ ${fail} 项未通过`:'✓ 全部通过'));
process.exit(fail?1:0);
