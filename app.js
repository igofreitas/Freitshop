'use strict';
const $ = id => document.getElementById(id);
const money = n => n.toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = s => { try { const u=new URL(s); return ['http:','https:'].includes(u.protocol) ? u.href : ''; } catch {return '';} };
let offers=[], chosen=new Set(), controller, sequence=0, focusBefore;
let blackFridayOpen=false, bfSelected=null, historySequence=0, historyController;
function filterProducts(){
 let visible=[...offers];
 const sort=$('sortSelect').value;
 if(sort==='price-asc') visible.sort((a,b)=>a.price-b.price);
 if(sort==='price-desc') visible.sort((a,b)=>b.price-a.price);
 if(sort==='rating') visible.sort((a,b)=>(b.rating ?? -1)-(a.rating ?? -1));
 $('productCount').textContent=visible.length;
 $('compareCount').textContent=chosen.size;
 const min=visible.length ? Math.min(...visible.map(p=>p.price)) : 0;
 $('productGrid').innerHTML=visible.map(p=>`<article class="bg-dark-card border border-purple-900/40 rounded-2xl overflow-hidden flex flex-col">
 <div class="h-44 bg-white p-4 flex items-center justify-center">${safeUrl(p.image)?`<img src="${esc(safeUrl(p.image))}" alt="${esc(p.name)}" loading="lazy" referrerpolicy="no-referrer" class="h-full w-full object-contain">`:'<span class="text-gray-500">Sem imagem</span>'}</div>
 <div class="p-4 flex flex-col flex-1 gap-3"><p class="text-xs text-purple-300">${esc(p.store)}</p><h2 class="font-bold text-sm">${esc(p.name)}</h2>
 <p class="text-2xl font-extrabold text-red-400">${money(p.price)}</p>
 ${p.price===min?'<p class="text-xs text-green-400">Menor preço dos resultados</p>':''}
 <p class="text-xs text-gray-400">${esc(p.delivery || 'Frete não informado — confira na oferta')}</p>
 <p class="text-xs text-gray-400">Estado: ${esc(p.condition || 'não informado')} • Avaliação: ${p.rating==null?'não informada':esc(p.rating)}</p>
 <a class="mt-auto bg-purple-700 hover:bg-purple-600 p-3 rounded-xl text-center text-sm" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener noreferrer">Ver oferta ↗</a>
 <label class="text-sm cursor-pointer"><input type="checkbox" data-compare="${esc(p.id)}" ${chosen.has(p.id)?'checked':''} class="accent-red-500"> Comparar esta oferta</label></div></article>`).join('');
 renderBlackFridayOffers(visible);
 if(!visible.length) $('productGrid').innerHTML='<p class="col-span-full text-gray-400 p-6">Nenhuma oferta para exibir. Faça uma busca.</p>';
}
async function searchOnline(){
 const q=$('searchInput').value.trim();
 if(q.length<2){$('status').textContent='Digite pelo menos 2 caracteres.'; return;}
 controller?.abort(); controller=new AbortController(); const serial=++sequence;
 const timer=setTimeout(()=>controller.abort(),35000);
 offers=[]; chosen.clear(); closeComparisonModal(); filterProducts(); $('updated').textContent='';
 $('status').textContent='Consultando ofertas online…'; $('productGrid').setAttribute('aria-busy','true');
 try {
  if(location.protocol==='file:') throw Error('Abra pelo servidor: execute python server.py e acesse http://127.0.0.1:8000.');
  const response=await fetch('/api/search?q='+encodeURIComponent(q),{signal:controller.signal});
  const data=await response.json();
  if(!response.ok) throw Error(data.error || 'Não foi possível consultar as ofertas.');
  if(serial!==sequence)return;
  offers=data.offers.map(p=>({...p,fetchedAt:data.fetchedAt,historySaved:data.historySaved}));
  $('status').textContent=offers.length ? `Consulta concluída: ${offers.length} ofertas. Os resultados podem incluir modelos e variantes diferentes.` : 'Nenhuma oferta com preço em reais encontrada. Tente informar marca e modelo.';
  $('updated').textContent='Consulta ao provedor: '+new Date(data.fetchedAt).toLocaleString('pt-BR')+(data.cached?' • Cache de até 5 minutos.':'');
  filterProducts();
 }catch(e){if(serial===sequence)$('status').textContent=e.name==='AbortError'?'Consulta interrompida ou tempo limite excedido. Tente novamente.':e.message;}
 finally {clearTimeout(timer); if(serial===sequence)$('productGrid').removeAttribute('aria-busy');}
}
function openComparisonModal(){
 const selected=offers.filter(p=>chosen.has(p.id));
 if(!selected.length){$('status').textContent='Selecione de 2 a 4 ofertas para comparar.'; return;}
 const min=Math.min(...selected.map(p=>p.price));
 const row=(title,fn)=>`<tr class="border-b border-purple-900/40"><th class="p-3 text-purple-300">${title}</th>${selected.map(p=>`<td class="p-3 min-w-48">${fn(p)}</td>`).join('')}</tr>`;
 $('comparisonContent').innerHTML='<p class="text-sm text-gray-400 mb-4">Confira se modelo, capacidade e estado são iguais. A diferença abaixo compara apenas o preço anunciado, sem frete.</p><table class="w-full text-sm text-left"><tbody>'+row('Produto',p=>esc(p.name))+row('Loja',p=>esc(p.store))+row('Preço anunciado',p=>money(p.price))+row('Diferença para o menor selecionado',p=>money(p.price-min))+row('Entrega',p=>esc(p.delivery||'Não informada'))+row('Estado',p=>esc(p.condition||'Não informado'))+row('Oferta',p=>`<a class="text-purple-300 underline" target="_blank" rel="noopener noreferrer" href="${esc(safeUrl(p.url))}">Abrir oferta ↗</a>`)+'</tbody></table>';
 focusBefore=document.activeElement;
 $('comparisonModal').classList.replace('hidden','flex'); $('comparisonModal').querySelector('button').focus();
}
function closeComparisonModal(){ $('comparisonModal').classList.remove('flex'); $('comparisonModal').classList.add('hidden'); focusBefore?.focus(); }
$('searchInput').addEventListener('keydown',e=>{if(e.key==='Enter')searchOnline();});
$('sortSelect').addEventListener('change',filterProducts);
$('productGrid').addEventListener('change',e=>{const id=e.target.dataset.compare;if(!id)return;if(e.target.checked){if(chosen.size===4){e.target.checked=false;$('status').textContent='Compare até 4 ofertas por vez.';return;}chosen.add(id);}else chosen.delete(id);$('compareCount').textContent=chosen.size;});
$('comparisonModal').addEventListener('click',e=>{if(e.target===$('comparisonModal'))closeComparisonModal();});
document.addEventListener('keydown',e=>{
 if($('comparisonModal').classList.contains('hidden'))return;
 if(e.key==='Escape')closeComparisonModal();
 if(e.key==='Tab'){const nodes=$('comparisonModal').querySelectorAll('button,a[href]');const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
});

async function setupAdvertising(){
 try{
  const r=await fetch('/api/site-config'); if(!r.ok)return;
  const cfg=await r.json();
  if(safeUrl(cfg.privacyUrl)){ $('privacyLink').href=safeUrl(cfg.privacyUrl); $('privacyLink').hidden=false; }
  // Só habilitar após aprovação, política publicada e configuração de consentimento.
  // CMP: use a integração oficial da solução escolhida, não um banner fictício.
  if(!cfg.enabled || !/^ca-pub-\d{16}$/.test(cfg.client) || !/^\d+$/.test(cfg.slot))return;
  $('adContainer').hidden=false;
  const ad=document.createElement('ins');
  ad.className='adsbygoogle';ad.style.display='block';
  ad.dataset.adClient=cfg.client;ad.dataset.adSlot=cfg.slot;
  ad.dataset.adFormat='auto';ad.dataset.fullWidthResponsive='true';
  $('adSlot').appendChild(ad);
  const script=document.createElement('script');
  script.async=true;script.crossOrigin='anonymous';
  script.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+encodeURIComponent(cfg.client);
  script.onload=()=>{try{(window.adsbygoogle=window.adsbygoogle||[]).push({});}catch{$('adContainer').hidden=true;}};
  script.onerror=()=>{$('adContainer').hidden=true;};
  document.head.appendChild(script);
 }catch{ /* Falha de anúncio não interfere na comparação de preços. */ }
}
setupAdvertising();

function renderBlackFridayOffers(items){
 $('bfOffers').innerHTML=items.length ? items.map(p=>`<button type="button" class="bf-choice" data-history-id="${esc(p.historyId)}" aria-pressed="${bfSelected?.historyId===p.historyId}"><span class="block font-semibold">${esc(p.name)}</span><span class="block text-sm text-purple-300 mt-2">${esc(p.store)}</span><span class="block text-lg text-lime-300 font-bold mt-2">${money(p.price)}</span><span class="block text-xs text-gray-400 mt-2">Selecionar e ver histórico →</span></button>`).join('') : '<p class="text-gray-400 p-4 col-span-full">Busque um produto para listar ofertas e lojas.</p>';
 if(bfSelected && !items.some(p=>p.historyId===bfSelected.historyId)){
  bfSelected=null;historySequence++;historyController?.abort();$('bfDetail').hidden=true;
 }
}
function toggleBlackFriday(){
 blackFridayOpen=!blackFridayOpen;
 $('blackFridayPanel').hidden=!blackFridayOpen;
 $('productGrid').hidden=blackFridayOpen;
 $('blackFridayButton').setAttribute('aria-expanded',String(blackFridayOpen));
 if(blackFridayOpen){$('bfHeading').focus(); if(!offers.length)$('searchInput').focus();}
}
function selectBlackFridayOffer(identity){
 const p=offers.find(o=>o.historyId===identity);if(!p)return;
 bfSelected=p;
 document.querySelectorAll('[data-history-id]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.historyId===identity)));
 $('bfDetail').hidden=false;
 $('bfName').textContent=p.name;$('bfStore').textContent='Loja: '+p.store;$('bfPrice').textContent=money(p.price);
 $('bfFetched').textContent='Consultado em '+new Date(p.fetchedAt).toLocaleString('pt-BR')+'. Preço sujeito a alteração.';
 $('bfOfferLink').href=safeUrl(p.url);
 loadPriceHistory();
 $('bfDetail').scrollIntoView({behavior:'smooth',block:'nearest'});
}
const dateLabel = value => value.split('-').reverse().join('/');
function drawPriceHistory(data){
 const points=data.points;
 $('bfTableDetails').hidden=!points.length;
 $('bfTable').innerHTML='<table class="w-full text-sm text-left"><thead><tr><th class="p-2">Data (UTC−3)</th><th class="p-2">Preço anunciado</th></tr></thead><tbody>'+points.map(p=>`<tr class="border-t border-purple-900/40"><td class="p-2">${esc(dateLabel(p.date))}</td><td class="p-2">${money(p.price)}</td></tr>`).join('')+'</tbody></table>';
 if(!points.length){$('bfHistoryStatus').textContent='Nenhum preço registrado neste período. O primeiro registro disponível é de '+dateLabel(data.firstRecorded)+'.';return;}
 const warning=bfSelected?.historySaved===false?' A consulta atual não pôde ser salva no histórico.':'';
 $('bfHistoryStatus').textContent=points.length===1 ? 'Há apenas 1 dia registrado. O gráfico ganhará novos pontos conforme houver consultas em outros dias.'+warning : `${points.length} dias com registros no período. Primeiro registro disponível: ${dateLabel(data.firstRecorded)}. As linhas apenas conectam observações; não representam preços nos dias sem dados.`+warning;
 const values=points.map(p=>p.price),min=Math.min(...values),max=Math.max(...values);
 $('bfSummary').textContent='Menor preço registrado no período: '+money(min)+' • Maior: '+money(max);
 const start=Date.parse(data.start+'T00:00:00Z'),end=Date.parse(data.end+'T00:00:00Z');
 const pad=Math.max((max-min)*0.15,max*0.03,1),low=Math.max(0,min-pad),high=max+pad;
 const x=day=>100+((Date.parse(day+'T00:00:00Z')-start)/(end-start||1))*580;
 const y=price=>225-((price-low)/(high-low))*185;
 let svg=`<svg viewBox="0 0 720 290" role="img" aria-label="Histórico de preços da oferta selecionada"><title>Histórico: ${esc(data.name)} em ${esc(data.store)}</title><desc>${points.length} dias registrados, entre ${esc(data.start)} e ${esc(data.end)}. Valores disponíveis na tabela abaixo.</desc><rect width="720" height="290" fill="#111118" rx="12"/>`;
 for(let i=0;i<4;i++){const v=low+(high-low)*i/3,py=y(v);svg+=`<line x1="100" x2="680" y1="${py}" y2="${py}" stroke="#343044"/><text x="90" y="${py+4}" text-anchor="end" fill="#aaa5ba" font-size="11">${esc(money(v))}</text>`;}
 [0,0.5,1].forEach((v,i)=>{const day=new Date(start+(end-start)*v).toISOString().slice(0,10);svg+=`<text x="${100+580*v}" y="255" text-anchor="${i===0?'start':i===2?'end':'middle'}" fill="#aaa5ba" font-size="12">${esc(dateLabel(day))}</text>`;});
 if(points.length>1)svg+=`<polyline points="${points.map(p=>`${x(p.date)},${y(p.price)}`).join(' ')}" fill="none" stroke="#a3e635" stroke-width="2" stroke-dasharray="5 4"/>`;
 svg+=points.map(p=>`<circle cx="${x(p.date)}" cy="${y(p.price)}" r="4" fill="#a3e635"><title>${esc(dateLabel(p.date))}: ${esc(money(p.price))}</title></circle>`).join('');
 $('bfChart').innerHTML=svg+'</svg>';
}
async function loadPriceHistory(){
 if(!bfSelected)return;
 historyController?.abort();historyController=new AbortController();
 const request=historyController,version=++historySequence,identity=bfSelected.historyId;
 $('bfChart').innerHTML='';$('bfTable').innerHTML='';$('bfSummary').textContent='';$('bfTableDetails').hidden=true;
 $('bfHistoryStatus').textContent='Carregando histórico…';
 const timer=setTimeout(()=>request.abort(),15000);
 try{
  const r=await fetch('/api/price-history?offer='+encodeURIComponent(identity)+'&months='+$('bfMonths').value,{signal:request.signal});
  const data=await r.json();if(version!==historySequence)return;
  if(!r.ok)throw Error(data.error||'Histórico indisponível.');
  drawPriceHistory(data);
 }catch(e){if(version===historySequence)$('bfHistoryStatus').textContent=e.name==='AbortError'?'A consulta ao histórico demorou demais. Troque o período para tentar novamente.':e.message;}
 finally{clearTimeout(timer);}
}
$('blackFridayButton').addEventListener('click',toggleBlackFriday);
$('bfOffers').addEventListener('click',e=>{const button=e.target.closest('[data-history-id]');if(button)selectBlackFridayOffer(button.dataset.historyId);});
$('bfMonths').addEventListener('change',loadPriceHistory);
filterProducts();


// Formulário público de avaliação, sem dependência de Firebase.
import('/feedback.js')
 .then(module=>module.initializeFeedback())
 .catch(()=>{const message=document.getElementById('feedbackStatus');if(message)message.textContent='Não foi possível carregar o formulário. Atualize a página.';});
