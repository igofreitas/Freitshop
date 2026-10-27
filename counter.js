// Totais do servidor; relógio em Brasília, sincronizado com a hora da API.
(()=>{
 const counter=document.getElementById('accessCounter');
 const status=document.getElementById('accessCounterStatus');
 const clock=document.getElementById('accessClock');
 const cacheKey='freitshop.counter.v1';
 let inFlight=false,registered=false,last=null,offset=0,displayDay=null;
 const valid=n=>n&&Number.isSafeInteger(n.total)&&n.total>=0&&Number.isSafeInteger(n.today)&&n.today>=0&&n.today<=n.total&&/^\d{4}-\d{2}-\d{2}$/.test(n.date);
 const localISO=()=>new Date(Date.now()+offset-3*3600000).toISOString();
 function paint(){
  if(!last)return;
  const today=last.date===localISO().slice(0,10)?last.today:0;
  counter.textContent=`${last.total.toLocaleString('pt-BR')} no total • ${today.toLocaleString('pt-BR')} hoje`;
 }
 function accept(n,live=false){
  if(live&&Number.isFinite(n.serverTime))offset=n.serverTime-Date.now();
  last=n;paint();
 }
 try{
  const initial=JSON.parse(counter.dataset.stats||'null');
  if(valid(initial))accept(initial,true);
  else{const cached=JSON.parse(localStorage.getItem(cacheKey));if(valid(cached)){accept(cached);status.textContent='Último valor salvo • sincronizando…';}}
 }catch{}
 async function request(register){
  const abort=new AbortController();const timeout=setTimeout(()=>abort.abort(),8000);
  try{
   const response=await fetch(register?'/api/visit':'/api/stats',{method:register?'POST':'GET',credentials:'same-origin',cache:'no-store',signal:abort.signal});
   if(!response.ok)throw Error('Contador indisponível');
   const data=await response.json();if(!valid(data))throw Error('Contagem inválida');
   return data;
  }finally{clearTimeout(timeout);}
 }
 async function sync(){
  if(inFlight||document.hidden)return;
  inFlight=true;
  try{
   // Só a entrada na página registra visita. Polling e virada do dia apenas consultam.
   const data=await request(!registered);registered=true;
   accept(data,true);
   try{localStorage.setItem(cacheKey,JSON.stringify(data));}catch{}
   status.textContent='Atualização automática a cada 5 s';
  }catch{
   status.textContent=(last||counter.dataset.serverValue)?'Último total salvo • diário aguardando sincronização':'Sem conexão com o contador • tentando novamente…';
  }finally{inFlight=false;}
 }
 function tick(){
  const iso=localISO(),day=iso.slice(0,10);
  clock.textContent=`${day.slice(8,10)}/${day.slice(5,7)}/${day.slice(0,4)} • ${iso.slice(11,19)}`;
  clock.dateTime=iso.slice(0,19)+'-03:00';
  if(displayDay!==day){
   const changed=displayDay!==null;displayDay=day;paint();
   if(changed){status.textContent='Novo dia • sincronizando visitas…';sync();}
  }
 }
 tick();sync();
 setInterval(tick,1000);setInterval(sync,5000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden){tick();sync();}});
 window.addEventListener('online',()=>{tick();sync();});
 window.addEventListener('pageshow',()=>{tick();sync();});
})();
