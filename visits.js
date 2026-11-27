(async()=>{
 const status=document.getElementById('visitsStatus');
 try{
  const response=await fetch('/api/visit-history',{cache:'no-store'});
  if(!response.ok)throw Error();
  const {days,today}=await response.json();
  if(!days.length){status.textContent='Ainda não há visitas registradas.';return;}
  const counts=new Map(days.map(d=>[d.date,d.count]));
  const points=[];
  for(let t=Date.parse(days[0].date);t<=Date.parse(today);t+=86400000){
   const day=new Date(t).toISOString().slice(0,10);
   points.push({day,count:counts.get(day)||0});
  }
  const label=day=>day.split('-').reverse().join('/');
  const rows=document.getElementById('visitRows');
  for(const {day,count} of [...points].reverse()){
   const tr=rows.insertRow();tr.insertCell().textContent=label(day);tr.insertCell().textContent=count.toLocaleString('pt-BR');
  }
  const max=points.reduce((n,p)=>Math.max(n,p.count),1);
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 680 245');svg.setAttribute('role','img');svg.setAttribute('aria-label','Visitas por dia. Valores exatos na tabela abaixo.');
  function draw(name,attrs,text){
   const e=document.createElementNS(svg.namespaceURI,name);
   for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);
   if(text!==undefined)e.textContent=text;svg.append(e);return e;
  }
  const x=i=>points.length===1?345:55+i*585/(points.length-1);
  const y=v=>200-v*165/max;
  for(const n of new Set([0,Math.ceil(max/2),max])){
   draw('line',{x1:55,x2:640,y1:y(n),y2:y(n),stroke:'#494358'});
   draw('text',{x:45,y:y(n)+4,fill:'#d8d5df','text-anchor':'end'},n);
  }
  draw('polyline',{points:points.map((p,i)=>x(i)+','+y(p.count)).join(' '),fill:'none',stroke:'#c4a5ff','stroke-width':3});
  if(points.length<=120)points.forEach((p,i)=>draw('circle',{cx:x(i),cy:y(p.count),r:4,fill:'#c4a5ff'}));
  draw('text',{x:x(0),y:232,fill:'#ddd','text-anchor':points.length===1?'middle':'start'},label(points[0].day));
  if(points.length>1)draw('text',{x:640,y:232,fill:'#ddd','text-anchor':'end'},label(points.at(-1).day));
  document.getElementById('visitsGraph').append(svg);
  status.textContent='Total de visitas no período: '+points.reduce((n,p)=>n+p.count,0).toLocaleString('pt-BR');
 }catch{status.textContent='Não foi possível carregar o histórico. Atualize a página para tentar novamente.';}
})();
