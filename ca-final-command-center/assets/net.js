/* Shared student transport: bounded requests, coalesced reads, no write retries or raw server HTML. */
(() => {
 'use strict';
 const waiting=[],reads=new Map();let active=0;
 const safeMessage=(data,status)=>{
  if(status===401||status===403)return 'Your session or access needs checking. Sign in again before retrying.';
  const message=data?.message;
  return typeof message==='string'&&message.length<=220&&!/[<>]|SQLSTATE|mysqli|password|Error establishing|SELECT\s|UPDATE\s/i.test(message)?message:'The study service is temporarily unavailable. Your saved work is unchanged. Please retry.';
 };
 function pump(){while(active<2&&waiting.length){active++;const task=waiting.shift();task().finally(()=>{active--;pump();});}}
 function request(url,{method='GET',body,nonce,signal}={}){
  const key=method==='GET'?String(url)+'|'+String(nonce||''):null;if(key&&reads.has(key))return reads.get(key);
  const pending=new Promise((resolve,reject)=>{waiting.push(async()=>{
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});
   try{
    if(signal?.aborted)controller.abort();
    const response=await fetch(url,{method,cache:'no-store',credentials:'same-origin',signal:controller.signal,headers:{'X-WP-Nonce':nonce||'','Content-Type':'application/json',Accept:'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    const type=response.headers.get('content-type')||'';let data;
    if(!/application\/(?:[a-z.+-]*\+)?json/i.test(type))throw Object.assign(Error('The study service is temporarily unavailable. Your saved work is unchanged. Please retry.'),{code:'non_json_response',status:response.status});
    try{data=await response.json();}catch(_){throw Object.assign(Error('The study service returned an incomplete response. Your saved work is unchanged. Please retry.'),{code:'invalid_json',status:response.status});}
    if(data===null||typeof data!=='object')throw Object.assign(Error('The study service returned an invalid response. Your saved work is unchanged. Please retry.'),{code:'invalid_json',status:response.status});
    if(!response.ok)throw Object.assign(Error(safeMessage(data,response.status)),{status:response.status,code:'service_response'});
    resolve(data);
   }catch(error){const e=error.code?error:Object.assign(Error('Connection unavailable. Your saved work is unchanged. Please retry when online.'),{code:'connection',status:0});document.dispatchEvent(new CustomEvent('cafcc:service-error',{detail:{code:e.code,status:e.status||0,path:new URL(url,location.href).pathname.replace(/\/[0-9]+(?=\/|$)/g,'/:id')}}));reject(e);}
   finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
  });pump();});
  if(key){reads.set(key,pending);pending.finally(()=>reads.delete(key)).catch(()=>{});}return pending;
 }
 window.CAFCCNet={request};
})();
