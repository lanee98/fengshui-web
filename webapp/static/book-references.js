window.renderBookReferences=async function(){
 const box=document.getElementById('cultureBox');
 const revision=(box._bookRevision||0)+1;box._bookRevision=revision;
 box.textContent='正在加载书籍参考…';
 try{const response=await fetch('/api/book-references');if(!response.ok)throw new Error('书籍目录暂时无法加载');const data=await response.json();if(box._bookRevision!==revision)return;box.replaceChildren();
 const add=(tag,text,parent=box)=>{const e=document.createElement(tag);e.textContent=text;parent.append(e);return e};
 add('h3','书籍与依据参考');add('p','传统文化、住宅设计与现代规范分开展示。以下关联是阅读线索，不表示每条规则已从原书逐页核实。').style.cssText='font-size:12px;line-height:1.8;color:#777';
 const issues=typeof auditResult!=='undefined'&&auditResult?auditResult.violations:[];
 if(issues.length)add('p','当前户型有 '+issues.length+' 条问题提示，可结合以下主题阅读。');else add('p','选择户型并诊断后，这里会显示相关问题的阅读线索。');
 for(const book of data.books){const card=add('article','');card.style.cssText='padding:16px 8px;border-bottom:1px solid #e4e7dd';add('h4','《'+book.title+'》',card);add('p',book.topic,card).style.cssText='font-size:13px;line-height:1.7';
 let related=issues.filter(v=>book.id==='housing'?/BED|LIV|GEN/.test(v.rule_id):book.id==='classic'?/BED|KIT|ENT/.test(v.rule_id):book.id==='theory'?/BED|LIV|ENT|GEN/.test(v.rule_id):book.id==='standard'?/GEN-003|BED-006/.test(v.rule_id):book.id==='interior'?/BED|KIT|LIV/.test(v.rule_id):false);
 if(related.length)add('p','相关问题：'+related.map(v=>v.name).join('、'),card).style.cssText='font-size:12px;line-height:1.7;color:#526e48';
 add('p',book.status,card).style.cssText='font-size:11px;color:#888';if(book.available){const link=add('a','打开本地原书 ↗',card);link.href=book.url;link.target='_blank';link.rel='noopener';}else add('p','未找到本地文件',card);
 }
 }catch(error){box.textContent=error.message}
};
