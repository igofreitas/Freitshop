// O servidor é a única fonte dos totais. O cache apenas evita apagar o número ao recarregar.
(()=>{
 const counter=document.getElementById('accessCounter');
 const status=document.getElementById('accessCounterStatus');
 const cacheKey='freitshop.counter.v1';
 let inFlight=false,registeredDay=null,last=null;
 const valid=n=>n&&Number.isSafeInteger(n.total)&&n.total>=0&&Number.isSafeInteger(n.today)&&n.today>=0&&n.today<=n.total&&/^\d{4}-\d{2}-\d{2}$/.test(n.date);
 function render(n){
  last=n;
  counter.textContent=`${n.total.toLocaleString('pt-BR')} no total • ${n.today.toLocaleString('pt-BR')} hoje`;
 }
 // O HTML servido já contém um total atual; não o substituir por um cache antigo.
 try{const cached=JSON.parse(localStorage.getItem(cacheKey));if(valid(cached)&&!counter.dataset.serverValue){render(cached);status.textContent='Último valor salvo • sincronizando…';}}catch{}
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
   let data=await request(!registeredDay);
   if(registeredDay&&data.date!==registeredDay)data=await request(true);
   registeredDay=data.date;
   render(data);
   try{localStorage.setItem(cacheKey,JSON.stringify(data));}catch{}
   status.textContent='Atualização automática a cada 5 s';
  }catch{
   // Nunca substituir o total conhecido por zero ou apagar o número por falha de rede.
   status.textContent=(last||counter.dataset.serverValue)?'Último valor disponível • reconectando…':'Sem conexão com o contador • tentando novamente…';
  }finally{inFlight=false;}
 }
 sync();
 setInterval(sync,5000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
 window.addEventListener('online',sync);
 window.addEventListener('pageshow',sync);
})();
