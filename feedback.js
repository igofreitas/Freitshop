const el=id=>document.getElementById(id);
let ready=false,busy=false,nextBefore=null,initializing=null;
const status=message=>{el('feedbackStatus').textContent=message;};
function setBusy(value){busy=value;document.querySelectorAll('#feedbackSection button').forEach(button=>button.disabled=value||!ready);}
async function request(path,options={}){
 const response=await fetch(path,{...options,headers:{'Content-Type':'application/json'},credentials:'same-origin'});
 let data;try{data=await response.json();}catch{throw Error('Servidor indisponível. Abra o site pelo servidor Python, não apenas o arquivo HTML.');}
 if(!response.ok)throw Error(data.error||'Não foi possível concluir.');
 return data;
}
function countCharacters(){
 const count=Array.from(el('feedbackComment').value).length;
 el('feedbackCharacters').textContent=count+'/500 caracteres';
 el('feedbackComment').setCustomValidity(count>500?'Limite de 500 caracteres.':'');
}
function appendReviews(items){
 if(!items.length&&!el('feedbackList').children.length){const p=document.createElement('p');p.textContent='Ainda não há avaliações. Compartilhe sua experiência.';p.className='text-sm text-gray-400';el('feedbackList').appendChild(p);}
 for(const item of items){
  const card=document.createElement('article');card.className='border border-purple-900/40 rounded-xl p-4';
  const head=document.createElement('p');head.className='text-sm text-purple-300';head.textContent='Visitante';
  const stars=document.createElement('p');stars.className='text-amber-300 mt-1';stars.textContent='★'.repeat(item.rating)+'☆'.repeat(5-item.rating);stars.setAttribute('aria-label',item.rating+' de 5 estrelas');
  const text=document.createElement('p');text.className='text-sm text-gray-200 mt-3';text.style.whiteSpace='pre-wrap';text.style.overflowWrap='anywhere';text.textContent=item.comment;
  const date=document.createElement('p');date.className='text-xs text-gray-400 mt-2';date.textContent=new Date(item.updatedAt).toLocaleDateString('pt-BR');
  card.append(head,stars,text,date);el('feedbackList').appendChild(card);
 }
}
async function loadReviews(reset=false){
 const cursor=reset?null:nextBefore;
 const data=await request('/api/feedback'+(cursor?'?before='+cursor:''));
 if(reset)el('feedbackList').replaceChildren();appendReviews(data.items);nextBefore=data.nextBefore;el('feedbackMore').hidden=!nextBefore;
}
export function initializeFeedback(){
 if(initializing)return initializing;
 initializing=(async()=>{
  setBusy(true);
  try{
   const config=await request('/api/feedback-config');
   if(!config.enabled){status(config.message||'Formulário em preparação.');return;}
   if(config.siteOrigin&&location.origin!==config.siteOrigin){status('Para avaliar, acesse o endereço oficial: '+config.siteOrigin);return;}
   ready=true;status('Deixe sua avaliação. Não é necessário cadastro.');
   try{await loadReviews(true);}catch{status('Você pode avaliar, mas não foi possível carregar os comentários anteriores.');}
  }catch(e){status(e.message);}
  finally{setBusy(false);}
 })().finally(()=>{initializing=null;});return initializing;
}
el('feedbackComment').addEventListener('input',countCharacters);
el('feedbackForm').addEventListener('submit',async event=>{
 event.preventDefault();if(busy)return;if(!ready){status('O formulário ainda não está disponível. Tente recarregar a página.');return;}
 countCharacters();if(!el('feedbackForm').reportValidity())return;
 const rating=Number(document.querySelector('input[name="feedbackRating"]:checked')?.value);
 setBusy(true);
 try{
  const data=await request('/api/feedback',{method:'POST',body:JSON.stringify({rating,comment:el('feedbackComment').value})});
  el('feedbackForm').reset();countCharacters();status(data.message);
  try{await loadReviews(true);}catch{status('Avaliação publicada. Atualize a página para ver a lista.');}
 }catch(e){status(e.message);}finally{setBusy(false);}
});
el('feedbackMore').addEventListener('click',async()=>{if(busy)return;setBusy(true);try{await loadReviews(false);}catch(e){status(e.message);}finally{setBusy(false);}});
