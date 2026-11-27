(()=>{
 const el=id=>document.getElementById(id);
 let csrf=null,editing=null,items=[],busy=false;
 const status=message=>el('adminStatus').textContent=message;
 function authenticated(value){csrf=value.csrf;el('adminLogin').hidden=value.authenticated;el('adminPanel').hidden=!value.authenticated;
  if(value.authenticated) loadManagement().catch(e=>status(e.message));
  else {el('generalSettings').reset();el('moderationList').replaceChildren();}}
 async function api(path,data){
  const response=await fetch(path,{method:data?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||''},...(data?{body:JSON.stringify(data)}:{})});
  let result;try{result=await response.json();}catch{throw Error('Abra o site pelo servidor Python atualizado.');}
  if(!response.ok){if(response.status===401)authenticated({authenticated:false,csrf:null});throw Error(result.error||'Não foi possível concluir.');}
  return result;
 }
 let nextPage=null;
 async function comments(before=null){
  const page=await api('/api/feedback'+(before?'?before='+before:''));
  if(!csrf)return;
  const list=el('moderationList');
  if(!before) list.replaceChildren();
  if(!before && !page.items.length) list.textContent='Nenhum comentário publicado.';
  for(const item of page.items){
   const row=document.createElement('p');
   const remove=document.createElement('button');
   remove.type='button';remove.className='underline ml-4';remove.textContent='Remover';
   remove.onclick=()=>{if(confirm('Remover este comentário do site?'))run(async()=>{
    await api('/api/admin/comments/delete',{id:item.id});await comments();status('Comentário removido.');location.reload();
   });};
   row.append(document.createTextNode(item.rating+' ★ — '+item.comment),remove);list.append(row);
  }
  nextPage=page.nextBefore;el('moreModeration').hidden=!nextPage;
 }
 async function loadManagement(){
  const cfg=await api('/api/admin/settings');
  if(!csrf)return;
  const fields=el('generalSettings').elements;
  for(const key of ['title','intro','client','slot','privacyUrl'])fields.namedItem(key).value=cfg[key];
  fields.namedItem('enabled').checked=cfg.enabled==='true';
  await comments();
 }
 el('moreModeration').onclick=()=>run(()=>comments(nextPage));
 el('generalSettings').onsubmit=e=>{
  e.preventDefault();
  run(async()=>{
   const data=Object.fromEntries(new FormData(e.target));
   data.enabled=e.target.elements.namedItem('enabled').checked?'true':'false';
   await api('/api/admin/settings',data);location.reload();
  });
 };
 el('downloadBackup').onclick=()=>run(async()=>{
  const backup=await api('/api/admin/backup',{});
  const url=URL.createObjectURL(new Blob([JSON.stringify(backup,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='FreitShop-'+new Date().toISOString().slice(0,10)+'.json';
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
  status('Backup de conteúdo pronto para download.');
 });
 function reset(){editing=null;el('sponsorForm').reset();el('sponsorSave').textContent='Adicionar patrocinador';el('sponsorCancel').hidden=true;}
 function render(){
  el('sponsorsList').replaceChildren();el('sponsorManagement').replaceChildren();el('sponsorsSection').hidden=!items.length;
  for(const item of items){
   const link=document.createElement('a');link.textContent=item.name;link.href=item.url;link.target='_blank';link.rel='sponsored noopener noreferrer';link.className='bg-dark-card border border-purple-900/40 rounded-xl px-5 py-3 text-purple-300 underline';el('sponsorsList').append(link);
   const row=document.createElement('div');row.className='flex flex-wrap gap-4 items-center border border-purple-900/40 rounded-xl p-3';
   const name=document.createElement('span');name.textContent=item.name+' — '+item.url;name.style.overflowWrap='anywhere';
   const edit=document.createElement('button');edit.type='button';edit.textContent='Editar';edit.className='text-purple-300 underline';edit.onclick=()=>{editing=item.id;el('sponsorName').value=item.name;el('sponsorUrl').value=item.url;el('sponsorSave').textContent='Salvar alterações';el('sponsorCancel').hidden=false;el('sponsorName').focus();};
   const remove=document.createElement('button');remove.type='button';remove.textContent='Remover';remove.className='text-red-400 underline';remove.onclick=()=>{if(confirm('Remover o patrocinador '+item.name+'?'))run(async()=>{await api('/api/admin/sponsors/delete',{id:item.id});if(editing===item.id)reset();await load();status('Patrocinador removido.');});};
   row.append(name,edit,remove);el('sponsorManagement').append(row);
  }
 }
 async function load(){items=(await api('/api/sponsors')).items;render();}
 async function run(action){if(busy)return;busy=true;const buttons=[...document.querySelectorAll('#adminLogin button,#adminPanel button')];buttons.forEach(b=>b.disabled=true);try{await action();}catch(e){status(e.message);}finally{busy=false;buttons.forEach(b=>b.disabled=false);}}
 el('adminLogin').addEventListener('submit',event=>{event.preventDefault();run(async()=>{const result=await api('/api/admin/login',{username:el('adminUsername').value,password:el('adminPassword').value});el('adminPassword').value='';authenticated(result);status('Admin master conectado.');await load();});});
 el('adminLogout').onclick=()=>run(async()=>{await api('/api/admin/logout',{});authenticated({authenticated:false,csrf:null});reset();status('Sessão encerrada.');});
 el('sponsorCancel').onclick=reset;
 el('sponsorForm').addEventListener('submit',event=>{event.preventDefault();run(async()=>{await api('/api/admin/sponsors',{id:editing,name:el('sponsorName').value.trim(),url:el('sponsorUrl').value.trim()});reset();await load();status('Patrocinadores atualizados no site.');});});
 load().catch(()=>{});
 api('/api/admin/session').then(authenticated).catch(e=>status(e.message));
})();
