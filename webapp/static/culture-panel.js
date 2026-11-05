function renderCulturePanel(){
 if(window.renderBookReferences){window.renderBookReferences();return;}
 const box=document.getElementById('cultureBox');
 if(box.dataset.ready && box.childElementCount)return;
 box.dataset.ready='true';
 box.innerHTML=`<div class="culture-box"><div class="culture-title">传统居住文化参考 · v1.2</div><p class="culture-text">主动查询后启用。结果不计入空间评分，也不会自动移动家具。资料仅用于本次查询，不发送给智谱。</p><form id="cultureForm"><label>省份 / 大区（选填）<input name="region" placeholder="例如：浙江" maxlength="30"></label><label>出生年份（命卦选填）<input name="birth_year" type="number" min="1900" max="2100" placeholder="例如：1998"></label><label>传统命卦计算选项<select name="gender"><option value="">不计算命卦</option><option value="male">传统男命算法</option><option value="female">传统女命算法</option></select></label><label>门净宽 / 物件尺寸（毫米，选填）<input name="width_mm" type="number" min="1" max="10000" placeholder="例如：810"></label><button class="btn" type="submit">查看文化参考</button></form><div id="cultureOutput" aria-live="polite"></div><p class="culture-limits">命卦需要出生年份、计算选项和标明入户门的户型；地域与鲁班尺可单独查询。尺寸仍以规范和实际使用为准，不承诺吉凶或功效。</p></div>`;
 const form=box.querySelector('form');form.style.cssText='display:grid;gap:12px;margin:16px 0';
 form.querySelectorAll('input,select').forEach(e=>e.style.cssText='display:block;width:100%;box-sizing:border-box;padding:9px;border:1px solid #ddd;border-radius:8px;margin-top:5px');
 form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('button'),out=box.querySelector('#cultureOutput');button.disabled=true;out.textContent='正在查询…';
 try{const data=Object.fromEntries(new FormData(form));data.scene=typeof sceneData!=='undefined'?sceneData:null;const r=await fetch('/api/culture-reference',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw new Error(result.error);out.replaceChildren();
 const add=(title,text)=>{const h=document.createElement('h4'),p=document.createElement('p');h.textContent=title;p.textContent=text;p.style.cssText='line-height:1.8;white-space:pre-wrap;font-size:13px';out.append(h,p)};
 add('地域色彩与意象',result.region.available?result.region.text:result.region.reason);
 const m=result.minggua;add('命卦与方位',m.available?m.text:m.reason);
 if(m.available){add('流派与证据边界',(m.limits||[]).join('\n'))}
 if(result.ruler){add('鲁班尺文化查询',result.ruler.width_mm+' 毫米，在门光尺通行算法中落于“'+result.ruler.cell+'”格。此为文化记号，不代表尺寸合规或实际吉凶。');add('尺寸依据边界',result.ruler_limits.join('\n'))}
 if(result.region.available)add('地域参考边界',result.region.limits.join('\n'));
 }catch(error){out.textContent=error.message}finally{button.disabled=false}};
}
renderCulturePanel();
