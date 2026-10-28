(() => {'use strict';
 document.querySelectorAll('.cc-portal').forEach(root=>{
  if(!root.querySelector('[data-experience-explorer],[data-cafcc-library],[data-cafcc-dashboard]'))return;
  const label=document.createElement('label');label.className='cc-design-preference';label.append(document.createTextNode('Appearance '));
  const select=document.createElement('select');select.setAttribute('aria-label','Workspace appearance preference');
  for(const [value,title]of [['current','Current'],['modern','Modern Light preview']]){const option=document.createElement('option');option.value=value;option.textContent=title;select.append(option);}
  function apply(value){root.dataset.ccDesign=value;select.value=value;}
  let initial='current';try{initial=localStorage.getItem('cafcc_design_preference')||'current';}catch(e){}apply(initial==='modern'?'modern':'current');
  select.onchange=()=>{apply(select.value);try{localStorage.setItem('cafcc_design_preference',select.value);}catch(e){}};label.append(select);(root.querySelector('.cc-portal-top')||root).append(label);
 });
})();
