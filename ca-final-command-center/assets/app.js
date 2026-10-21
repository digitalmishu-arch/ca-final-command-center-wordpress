(function(){
 'use strict';
 const root=document.querySelector('.cafcc-app');if(!root||typeof CAFCC_CONFIG==='undefined')return;
 const select=root.querySelector('#cafcc-subject'),list=root.querySelector('#cafcc-list'),feedback=root.querySelector('#cafcc-feedback');
 const statuses=['not_started','attempted','revision','mastered'];
 const labels={not_started:'Not started',attempted:'Attempted',revision:'Needs revision',mastered:'Mastered'};
 const api=(path,options={})=>fetch(CAFCC_CONFIG.url+path,{credentials:'same-origin',headers:{'X-WP-Nonce':CAFCC_CONFIG.nonce,'Content-Type':'application/json'},...options}).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.message||'Request failed');return data;});
 function element(tag,cls,text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
 async function load(){
  list.replaceChildren(element('p','','Loading questions…'));feedback.textContent='';
  try{
   const items=await api('questions'+(select.value?'?subject='+encodeURIComponent(select.value):''));
   list.replaceChildren();
   if(!items.length){list.append(element('p','','No questions have been added yet.'));return;}
   const counts=element('p','cafcc-summary',items.length+' questions · '+items.filter(q=>q.status==='mastered').length+' mastered');
   list.append(counts);
   items.forEach(q=>{
    const article=element('article','cafcc-question');
    article.append(element('div','cafcc-meta',[q.subject,q.chapter,q.topic,q.source_type,q.exam_term].filter(Boolean).join(' · ')));
    article.append(element('p','cafcc-question-text',q.question_text));
    if(q.source_reference)article.append(element('p','cafcc-ref','Reference: '+q.source_reference));
    const label=element('label','','Practice status');
    const status=document.createElement('select');status.setAttribute('aria-label','Practice status for question '+q.id);
    statuses.forEach(value=>{const o=document.createElement('option');o.value=value;o.textContent=labels[value];o.selected=q.status===value;status.append(o);});
    label.append(status);article.append(label);
    const notes=element('textarea','');notes.placeholder='Private revision notes';notes.value=q.notes||'';notes.rows=2;notes.setAttribute('aria-label','Private notes for question '+q.id);
    article.append(notes);
    const save=element('button','','Save progress');save.type='button';
    save.addEventListener('click',async()=>{
     save.disabled=true;feedback.textContent='Saving…';
     try{await api('progress/'+q.id,{method:'POST',body:JSON.stringify({status:status.value,notes:notes.value})});feedback.textContent='Progress saved.';}
     catch(err){feedback.textContent=err.message;}
     finally{save.disabled=false;}
    });
    article.append(save);list.append(article);
   });
  }catch(err){list.replaceChildren(element('p','cafcc-error',err.message));}
 }
 select.addEventListener('change',load);load();
})();