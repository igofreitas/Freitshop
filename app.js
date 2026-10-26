'use strict';
const $ = id => document.getElementById(id);
const money = n => n.toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = s => { try { const u=new URL(s); return ['http:','https:'].includes(u.protocol) ? u.href : ''; } catch {return '';} };
let offers=[], chosen=new Set(), controller, sequence=0, focusBefore;
function filterProducts(){
 const store=$('storeFilter').value, max=Number($('priceRange').value);
 let visible=offers.filter(p=>(!store || p.store===store) && p.price<=max);
 const sort=$('sortSelect').value;
 if(sort==='price-asc') visible.sort((a,b)=>a.price-b.price);
 if(sort==='price-desc') visible.sort((a,b)=>b.price-a.price);
 if(sort==='rating') visible.sort((a,b)=>(b.rating ?? -1)-(a.rating ?? -1));
 $('productCount').textContent=visible.length;
 $('compareCount').textContent=chosen.size;
 $('priceLabel').textContent=money(max);
 const min=visible.length ? Math.min(...visible.map(p=>p.price)) : 0;
 $('productGrid').innerHTML=visible.map(p=>`<article class="bg-dark-card border border-purple-900/40 rounded-2xl overflow-hidden flex flex-col">
 <div class="h-44 bg-white p-4 flex items-center justify-center">${safeUrl(p.image)?`<img src="${esc(safeUrl(p.image))}" alt="${esc(p.name)}" loading="lazy" referrerpolicy="no-referrer" class="h-full w-full object-contain">`:'<span class="text-gray-500">Sem imagem</span>'}</div>
 <div class="p-4 flex flex-col flex-1 gap-3"><p class="text-xs text-purple-300">${esc(p.store)}</p><h2 class="font-bold text-sm">${esc(p.name)}</h2>
 <p class="text-2xl font-extrabold text-red-400">${money(p.price)}</p>
 ${p.price===min?'<p class="text-xs text-green-400">Menor preço dos resultados filtrados</p>':''}
 <p class="text-xs text-gray-400">${esc(p.delivery || 'Frete não informado — confira na oferta')}</p>
 <p class="text-xs text-gray-400">Estado: ${esc(p.condition || 'não informado')} • Avaliação: ${p.rating==null?'não informada':esc(p.rating)}</p>
 <a class="mt-auto bg-purple-700 hover:bg-purple-600 p-3 rounded-xl text-center text-sm" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener noreferrer">Ver oferta ↗</a>
 <label class="text-sm cursor-pointer"><input type="checkbox" data-compare="${esc(p.id)}" ${chosen.has(p.id)?'checked':''} class="accent-red-500"> Comparar esta oferta</label></div></article>`).join('');
 if(!visible.length) $('productGrid').innerHTML='<p class="col-span-full text-gray-400 p-6">Nenhuma oferta para exibir. Faça uma busca ou ajuste os filtros.</p>';
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
  offers=data.offers;
  $('storeFilter').innerHTML='<option value="">Todas as lojas</option>'+[...new Set(offers.map(p=>p.store))].sort().map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');
  const ceiling=Math.max(10000,...offers.map(p=>Math.ceil(p.price/100)*100));
  $('priceRange').max=ceiling; $('priceRange').value=ceiling;
  $('status').textContent=offers.length ? `Consulta concluída: ${offers.length} ofertas. Os resultados podem incluir modelos e variantes diferentes.` : 'Nenhuma oferta com preço em reais encontrada. Tente informar marca e modelo.';
  $('updated').textContent='Consulta ao provedor: '+new Date(data.fetchedAt).toLocaleString('pt-BR')+(data.cached?' • Cache de até 5 minutos.':'');
  filterProducts();
 }catch(e){if(serial===sequence)$('status').textContent=e.name==='AbortError'?'Consulta interrompida ou tempo limite excedido. Tente novamente.':e.message;}
 finally {clearTimeout(timer); if(serial===sequence)$('productGrid').removeAttribute('aria-busy');}
}
function resetFilters(){ $('storeFilter').value=''; $('priceRange').value=$('priceRange').max; $('sortSelect').value='relevance'; filterProducts(); }
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
['storeFilter','sortSelect'].forEach(id=>$(id).addEventListener('change',filterProducts));
$('priceRange').addEventListener('input',filterProducts);
$('productGrid').addEventListener('change',e=>{const id=e.target.dataset.compare;if(!id)return;if(e.target.checked){if(chosen.size===4){e.target.checked=false;$('status').textContent='Compare até 4 ofertas por vez.';return;}chosen.add(id);}else chosen.delete(id);$('compareCount').textContent=chosen.size;});
$('comparisonModal').addEventListener('click',e=>{if(e.target===$('comparisonModal'))closeComparisonModal();});
document.addEventListener('keydown',e=>{
 if($('comparisonModal').classList.contains('hidden'))return;
 if(e.key==='Escape')closeComparisonModal();
 if(e.key==='Tab'){const nodes=$('comparisonModal').querySelectorAll('button,a[href]');const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
});
filterProducts();

// Estatística pública agregada; ler esta rota não aumenta a contagem.
async function loadAccessCounter(){
 try{
  const r=await fetch('/api/stats'); if(!r.ok)throw Error();
  const n=await r.json();
  $('accessCounter').textContent=`Visualizações: ${Number(n.total).toLocaleString('pt-BR')} no total • ${Number(n.today).toLocaleString('pt-BR')} hoje`;
 }catch{$('accessCounter').textContent='Contador temporariamente indisponível.';}
}
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
loadAccessCounter();
setupAdvertising();
