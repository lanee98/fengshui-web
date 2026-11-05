/* Enhancements shared by the original editor, audit view and Three.js viewer. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const path = location.pathname;
  const isPlan = path.startsWith('/plan'), is3D = path.startsWith('/3d'), isRefresh = path.startsWith('/refresh');
  const create = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; };
  const notify = text => { if(typeof toast === 'function') toast(text); else if(typeof showToast === 'function') showToast(text); else { const e=create('div','living-message',text); e.style.cssText='position:fixed;bottom:20px;left:20px;z-index:300;max-width:80vw'; document.body.append(e);setTimeout(()=>e.remove(),3500); } };
  let account = null, accountMode='register';
  const nav = create('nav','living-nav'); nav.setAttribute('aria-label','空间导航');
  [['/design','一键布置'],['/plan','二维布置'],['/refresh','日常微调'],['/','空间诊断']].forEach(([url,name]) => {const a=create('a',path===url?'current':'',name);a.href=url;nav.append(a)});
  const galleryButton=create('button','','灵感图库');galleryButton.type='button';nav.append(galleryButton);
  const accountButton=create('button','','注册 / 登录');accountButton.type='button';nav.append(accountButton);
  if(is3D)document.body.append(nav);else if(isPlan)$('.top .brand').after(nav);else if(isRefresh||path.startsWith('/design'))$('.refresh-header').append(nav);else $('.topbar .brand').after(nav);
  function modal(title,eyebrow){const d=create('dialog','living-modal');const close=create('button','living-close','×');close.setAttribute('aria-label','关闭');close.type='button';close.onclick=()=>d.close();d.append(close,create('div','living-eyebrow',eyebrow),create('h2','',title));document.body.append(d);d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close()}});return d}
  const profile=modal('从你的生活开始','YOUR LIVING PROFILE'); profile.style.maxWidth='500px';
  profile.insertAdjacentHTML('beforeend',`<p class="living-help">创建本站账号，保存生日与房屋所在地区。无需门牌号。</p><form id="livingAccountForm"><div id="accountCredentials" class="living-form-grid"><label>账号<input name="username" autocomplete="username" minlength="3" maxlength="40" required></label><label>密码<input name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required></label></div><div id="accountProfile"><label>称呼<input name="nickname" required maxlength="40"></label><label>生日（选填）<input name="birthday" type="date"></label><div class="living-form-grid"><label>国家<input name="country" placeholder="中国" required maxlength="60"></label><label>省份 / 州<input name="province" placeholder="浙江省" required maxlength="60"></label><label>城市<input name="city" placeholder="杭州市" required maxlength="60"></label><label>区 / 县<input name="district" placeholder="西湖区" required maxlength="60"></label></div><label>生活目标<select name="goal"><option>舒适生活</option><option>求职与专注</option><option>睡眠与放松</option><option>绿植与自然</option><option>传统招财寓意</option></select></label></div><p class="living-form-error" role="status" id="accountError"></p><button class="living-button primary" type="submit" id="accountSubmit">创建账号 →</button> <button class="living-button" type="button" id="accountSwitch">已有账号，去登录</button><p class="living-footer-note">账号与档案存储在本机运行的本站数据库中；布局方案继续沿用原工程的浏览器保存机制。</p></form>`);
  const form=$('#livingAccountForm');
  function mode(m){accountMode=m;$('#accountError').textContent='';$('#accountCredentials').hidden=m==='profile';$('#accountProfile').hidden=m==='login';$('#accountCredentials').querySelectorAll('input').forEach(i=>i.disabled=m==='profile');$('#accountProfile').querySelectorAll('input,select').forEach(i=>i.disabled=m==='login');$('#accountSubmit').textContent={profile:'保存档案 →',login:'登录 →',register:'创建账号 →'}[m];$('#accountSwitch').textContent=m==='profile'?'退出登录':m==='login'?'没有账号，去注册':'已有账号，去登录';form.elements.password.autocomplete=m==='login'?'current-password':'new-password';if(m==='profile'&&account)Object.entries(account.profile).forEach(([k,v])=>{if(form.elements[k])form.elements[k].value=v})}
  async function api(url,method,data){const r=await fetch(url,{method,headers:{'Content-Type':'application/json','X-Requested-With':'ImmerseHome'},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw new Error(result.error||'请求失败，请稍后重试');return result}
  function updateAccount(){accountButton.textContent=account?account.profile.nickname+' · 档案':'注册 / 登录'}
  accountButton.onclick=()=>{mode(account?'profile':'register');profile.showModal()};
  $('#accountSwitch').onclick=async()=>{if(accountMode==='profile'){try{await api('/api/account/logout','POST',{});account=null;updateAccount();mode('login');form.reset()}catch(e){$('#accountError').textContent=e.message}}else mode(accountMode==='login'?'register':'login')};
  form.onsubmit=async e=>{e.preventDefault();$('#accountError').textContent='';$('#accountSubmit').disabled=true;try{const data=Object.fromEntries(new FormData(form));const result=await api(accountMode==='profile'?'/api/account':'/api/account/'+accountMode,accountMode==='profile'?'PUT':'POST',data);account=result.user;form.elements.password.value='';updateAccount();profile.close();notify(accountMode==='register'?'账号已创建，居住档案已保存':'已保存，欢迎回来')}catch(error){$('#accountError').textContent=error.message}finally{$('#accountSubmit').disabled=false}};
  fetch('/api/account').then(r=>r.json()).then(data=>{account=data.user;updateAccount();if(data.publicDemo){accountButton.textContent='共享演示';accountButton.onclick=()=>notify('共享演示不收集账号与生日资料，方案保存在你当前使用的设备中。')}}).catch(()=>{});
  const gallery=modal('把喜欢，带进生活','SIX WAYS TO FEEL AT HOME');gallery.append(create('p','living-help','取自你的参考图片。应用色调会同步到当前布局的家具，并保留已有户型与诊断能力。'));
  const cards=create('div','living-gallery');gallery.append(cards);
  const themes=[['复古原木','胡桃木 · 暖光 · 生活气息','#ad8867','#9b8b6b'],['自然原木','浅木色 · 棉麻 · 鼠尾草绿','#c4ad89','#a5b297'],['温柔法式','奶油白 · 细线条 · 柔和粉','#d8c9b5','#c5a498'],['现代简约','暖灰 · 留白 · 间接照明','#b4aca1','#a4a69f'],['中古暖棕','皮革 · 深木色 · 沉静','#a67e59','#a58971'],['日式自然','原木 · 藤编 · 陶土色','#c7aa79','#bd8d72']];
  function themeColor(f,t){const spec=FurnitureMaterials.resolve(f);return spec.fixed?spec.color:/sofa|bed|chair/.test(f.type)?t[3]:t[2]}
  function applyTheme(n){const t=themes[n];localStorage.setItem('immersehome.palette',String(n));if(isPlan&&window.__plan){window.__plan.furn.forEach(f=>f.color=themeColor(f,t));draw();saveEditorDraft();publishPlanDraft()}else if(is3D&&typeof sceneData!=='undefined'&&sceneData){const before=SceneStore.clone(sceneData);sceneData.furniture.forEach(f=>f.color=themeColor(f,t));rebuildFurniture();saveAdjustedScene(before)}else{const doc=SceneStore.restore();if(doc){const data=doc.updated;data.furniture.forEach(f=>f.color=themeColor(f,t));SceneStore.commit(data);if(typeof restoreCurrentPlan==='function')restoreCurrentPlan()}}gallery.close();notify('已应用「'+t[0]+'」色调。云端模型保留自带 PBR 纹理。')}
  themes.forEach((t,n)=>{const figure=create('figure'),b=create('button');b.type='button';const img=create('img');img.src='/inspiration/room-'+n+'.jpg';img.alt=t[0]+'室内搭配参考';img.loading='lazy';const caption=create('figcaption');caption.append(create('strong','',t[0]),create('p','',t[1]),create('span','living-help','应用到我的空间 ↗'));b.append(img,caption);b.onclick=()=>applyTheme(n);figure.append(b);cards.append(figure)});galleryButton.onclick=()=>gallery.showModal();
  const chatToggle=create('button','living-chat-toggle','✧ 空间小助手');chatToggle.type='button';document.body.append(chatToggle);
  const chat=create('section','living-chat-box');chat.hidden=true;chat.setAttribute('aria-label','空间建议对话');chat.insertAdjacentHTML('beforeend','<div class="living-chat-head"><b>和空间聊一聊</b><button type="button" aria-label="关闭对话">×</button></div><p class="living-help">空间智能体 · 正在检查智谱连接</p><div class="living-chat-messages" aria-live="polite"></div><form class="living-chat-form"><input placeholder="窗台适合放什么绿植？" required maxlength="500" aria-label="输入空间问题"><button type="submit">↑</button></form><p class="living-footer-note">提问会将文字及布局摘要发送给智谱，不自动上传照片或生日。AI 建议仅供参考，勿作为决策依据。</p>');document.body.append(chat);
  const messages=chat.querySelector('.living-chat-messages');
  function say(text,mine){messages.append(create('div','living-message'+(mine?' mine':''),text));messages.scrollTop=messages.scrollHeight}
  say('你好，想改善采光、整理求职准备区，或给窗台添一点绿意？告诉我你想调整的地方。');
  chatToggle.onclick=()=>{chat.hidden=!chat.hidden;if(!chat.hidden)chat.querySelector('input').focus()};chat.querySelector('.living-chat-head button').onclick=()=>chat.hidden=true;
  chat.addEventListener('wheel',e=>e.stopPropagation());chat.addEventListener('pointerdown',e=>e.stopPropagation());chat.addEventListener('keydown',e=>e.stopPropagation());
  const history=[];
  const chatStatus=chat.querySelector('.living-help');
  fetch('/api/space-agent/status').then(r=>{if(!r.ok)throw new Error();return r.json()}).then(s=>chatStatus.textContent=s.configured?'智谱空间智能体 · 结合当前布局，可连续追问':'智谱空间智能体 · 等待管理员配置密钥').catch(()=>chatStatus.textContent='空间智能体 · 暂时无法检查连接');
  function spaceContext(){
    let current;
    try {current=isPlan&&typeof window.__scene==='function'?window.__scene():is3D&&typeof sceneData!=='undefined'?sceneData:SceneStore.restore()?.updated;}catch(e){current=null}
    const furniture=current?.furniture||(isPlan?window.__plan?.furn:[])||[];
    const keys=['type','name','x','y','w','h','width','depth','rotation','material','color','rect'];
    return {page:path,goal:account?.profile?.goal||document.querySelector('#refreshGoal')?.value||'舒适生活',furniture:furniture.slice(0,80).map(f=>Object.fromEntries(keys.filter(k=>f[k]!==undefined).map(k=>[k,f[k]]))),rooms:current?.rooms?.slice(0,12)||[],note:'用户浏览器中的布局数据，尺寸单位以原方案为准，未提供照片'};
  }
  chat.querySelector('form').onsubmit=async e=>{
    e.preventDefault();const input=chat.querySelector('input'),button=chat.querySelector('form button'),q=input.value.trim();if(!q||button.disabled)return;
    say(q,true);input.value='';button.disabled=true;input.disabled=true;
    const pending=create('div','living-message','正在结合你的空间思考…');messages.append(pending);messages.scrollTop=messages.scrollHeight;
    try {
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),55000);let r;
      try {r=await fetch('/api/space-agent/chat',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'ImmerseHome'},body:JSON.stringify({question:q,history:history.slice(-8),context:spaceContext()}),signal:controller.signal});}finally{clearTimeout(timer)}
      const data=await r.json();if(!r.ok)throw new Error(data.error||'空间智能体暂时不可用');
      pending.textContent=data.answer;history.push({role:'user',content:q},{role:'assistant',content:data.answer});if(history.length>8)history.splice(0,history.length-8);
      chatStatus.textContent='智谱空间智能体 · 可继续追问';
    }catch(error){pending.textContent=error.name==='AbortError'?'回答超时，请稍后重试。':error.message;input.value=q;}
    finally{button.disabled=false;input.disabled=false;messages.scrollTop=messages.scrollHeight;input.focus()}
  };
  if(isPlan){const palette=$('#palette');const filter=create('select','living-furn-filter');filter.setAttribute('aria-label','家具分类');['全部家具','卧室','客厅','餐厨','卫浴','书房','其他'].forEach(t=>filter.append(new Option(t,t)));palette.before(filter);filter.onchange=()=>{let category='';[...palette.children].forEach(e=>{if(e.classList.contains('pal-cat'))category=e.textContent.trim();e.hidden=filter.value!=='全部家具'&&filter.value!==category})};
    const prop=$('#propBody');new MutationObserver(()=>{
      if($('#livingMaterial')||$('#livingFixedMaterial')||!window.__plan?.furn.includes(window.__plan.sel))return;
      const f=window.__plan.sel;FurnitureMaterials.normalizeItem(f);const spec=FurnitureMaterials.resolve(f);
      if(spec.fixed){const note=create('div','living-material-note','已自动匹配：'+spec.label+'。此类物件不提供不适用的材质选项。');note.id='livingFixedMaterial';prop.append(note);return;}
      const label=create('label','','材质 '),select=create('select');select.id='livingMaterial';spec.options.forEach(key=>select.append(new Option(FurnitureMaterials.materials[key].label,key)));select.value=spec.key;label.append(select);
      const colorLabel=create('label','','颜色 '),color=create('input','living-swatch');color.type='color';color.value=spec.color;colorLabel.append(color);prop.append(label,colorLabel);
      select.onchange=()=>{f.material=select.value;f.color=FurnitureMaterials.materials[select.value].color;color.value=f.color;draw();publishPlanDraft()};color.oninput=()=>{f.color=color.value;draw();publishPlanDraft()};
    }).observe(prop,{childList:true});
  }
  if(is3D){const quality=create('button','gbtn','材质与画质');quality.type='button';quality.onclick=()=>LivingRender.openInspector();$('.top-right').append(quality);}
  const useTemplate=create('a','living-button primary','不想画图？一键套用完整方案 →');useTemplate.href='/design';gallery.insertBefore(useTemplate,cards);
  window.LivingHome={applyTheme,account:()=>account};
})();
