/** Widget embutível: <script src="https://SEU-APP/widget.js" data-key="WIDGET_KEY" async></script> */
export const WIDGET_JS = String.raw`(function(){
  var s=document.currentScript; if(!s) return;
  var key=s.getAttribute('data-key'); var base=new URL(s.src).origin; var color=s.getAttribute('data-color')||'#4f46e5';
  if(!key) return;
  function store(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}
  var sid=store('sbai_sid_'+key);
  if(!sid){var a=new Uint8Array(18);crypto.getRandomValues(a);sid=Array.from(a,function(b){return('0'+b.toString(16)).slice(-2)}).join('');store('sbai_sid_'+key,sid)}
  var lang=(navigator.language||'pt').slice(0,2);
  var T={pt:['Fale conosco','Digite sua mensagem…','Enviar','Assistente virtual com IA'],fr:['Contactez-nous','Écrivez votre message…','Envoyer','Assistant virtuel IA'],en:['Chat with us','Type your message…','Send','AI virtual assistant'],es:['Hable con nosotros','Escriba su mensaje…','Enviar','Asistente virtual con IA']}[lang]||['Fale conosco','Digite sua mensagem…','Enviar','Assistente virtual com IA'];
  var host=document.createElement('div'); host.style.cssText='position:fixed;right:16px;bottom:16px;z-index:2147483000'; document.body.appendChild(host);
  var root=host.attachShadow({mode:'open'});
  root.innerHTML='<style>*{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}'+
  '.b{width:60px;height:60px;border-radius:50%;border:0;background:'+color+';color:#fff;font-size:26px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25)}'+
  '.p{display:none;position:fixed;right:16px;bottom:88px;width:min(370px,calc(100vw - 32px));height:min(540px,calc(100vh - 120px));background:#fff;border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,.25);flex-direction:column;overflow:hidden}'+
  '.p.o{display:flex}.h{background:'+color+';color:#fff;padding:14px 16px}.h b{display:block;font-size:15px}.h small{opacity:.85;font-size:12px}'+
  '.m{flex:1;overflow-y:auto;padding:12px;background:#f6f7fb}.x{max-width:82%;padding:9px 12px;border-radius:14px;margin:6px 0;font-size:14px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word}'+
  '.c{background:'+color+';color:#fff;margin-left:auto;border-bottom-right-radius:4px}.a{background:#fff;color:#111;border:1px solid #e5e7eb;border-bottom-left-radius:4px}'+
  'form{display:flex;gap:8px;padding:10px;border-top:1px solid #e5e7eb}input{flex:1;padding:10px 12px;border:1px solid #d1d5db;border-radius:10px;font-size:16px}'+
  'button.s{background:'+color+';color:#fff;border:0;border-radius:10px;padding:0 14px;font-weight:600;cursor:pointer}.t{font-size:12px;color:#6b7280;padding:4px}</style>'+
  '<div class="p" role="dialog" aria-label="Chat"><div class="h"><b class="n">…</b><small>'+T[3]+'</small></div><div class="m" aria-live="polite"></div>'+
  '<form><input name="q" autocomplete="off" maxlength="2000" placeholder="'+T[1]+'" aria-label="'+T[1]+'"><button class="s" type="submit">'+T[2]+'</button></form></div>'+
  '<button class="b" aria-label="'+T[0]+'" title="'+T[0]+'">💬</button>';
  var panel=root.querySelector('.p'), msgs=root.querySelector('.m'), form=root.querySelector('form'), input=root.querySelector('input');
  var seen={}, last=null, timer=null;
  function add(role,text,id){ if(id){if(seen[id])return;seen[id]=1}
    var d=document.createElement('div'); d.className='x '+(role==='customer'?'c':'a'); d.textContent=text; msgs.appendChild(d); msgs.scrollTop=msgs.scrollHeight; }
  function poll(){ fetch(base+'/api/widget/'+key+'/messages?sessionId='+sid+(last?'&after='+encodeURIComponent(last):'')).then(function(r){return r.json()}).then(function(list){
    (list||[]).forEach(function(m){ add(m.role,m.content,m.id); last=m.createdAt; }); }).catch(function(){}); }
  fetch(base+'/api/widget/'+key+'/info').then(function(r){return r.json()}).then(function(i){ root.querySelector('.n').textContent=i.name||''; }).catch(function(){});
  root.querySelector('.b').addEventListener('click',function(){ panel.classList.toggle('o');
    if(panel.classList.contains('o')){ poll(); timer=setInterval(poll,4000); input.focus(); } else clearInterval(timer); });
  form.addEventListener('submit',function(e){ e.preventDefault(); var q=input.value.trim(); if(!q) return; input.value='';
    var tmp=document.createElement('div'); tmp.className='t'; tmp.textContent='…';
    var pend=document.createElement('div'); pend.className='x c'; pend.textContent=q; msgs.appendChild(pend); msgs.appendChild(tmp); msgs.scrollTop=msgs.scrollHeight;
    fetch(base+'/api/widget/'+key+'/messages',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({sessionId:sid,text:q})})
      .then(function(r){return r.json()}).then(function(){ pend.remove(); tmp.remove(); poll(); }).catch(function(){ tmp.textContent='⚠'; });
  });
})();`;
