const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/counter.js','utf8');
let total=0,today=0,date='2026-10-26',offline=false;
const seen=new Set();
function client(identity,cache=new Map()){
 const nodes={accessCounter:{textContent:'Carregando…',dataset:{}},accessCounterStatus:{textContent:''}};
 const events={};let interval;
 const context={document:{hidden:false,getElementById:id=>nodes[id],addEventListener:(event,fn)=>events[event]=fn},window:{addEventListener:(event,fn)=>events[event]=fn},localStorage:{getItem:key=>cache.get(key)||null,setItem:(key,v)=>cache.set(key,v)},AbortController,setTimeout,clearTimeout,setInterval:fn=>interval=fn,fetch:async(path,options)=>{
  if(offline)throw Error('offline');
  assert.equal(options.cache,'no-store');
  if(path==='/api/visit'){
   assert.equal(options.method,'POST');const key=identity+date;
   if(!seen.has(key)){seen.add(key);total++;today++;}
  }else{assert.equal(path,'/api/stats');assert.equal(options.method,'GET');}
  return {ok:true,json:async()=>({total,today,date})};
 }};
 vm.runInNewContext(source,context);
 return {nodes,cache,poll:()=>interval(),events,context};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 const pc=client('pc');await flush();assert.equal(total,1);
 const phone=client('phone');await flush();assert.equal(total,2);
 await pc.poll();assert.equal(pc.nodes.accessCounter.textContent,phone.nodes.accessCounter.textContent);
 for(let i=0;i<5;i++)await pc.poll();assert.equal(total,2);
 offline=true;const before=pc.nodes.accessCounter.textContent;await pc.poll();assert.equal(pc.nodes.accessCounter.textContent,before);
 const refreshed=client('pc',pc.cache);assert.equal(refreshed.nodes.accessCounter.textContent,before);await flush();
 offline=false;await refreshed.poll();assert.equal(total,2);
 date='2026-10-27';today=0;await pc.poll();assert.equal(total,3);assert.equal(today,1);
 await phone.poll();await pc.poll();assert.equal(total,4);assert.equal(pc.nodes.accessCounter.textContent,phone.nodes.accessCounter.textContent);
 console.log('PASS: PC e celular sincronizam; polling/refresh não duplicam; cache e falha de rede preservam valor; virada do dia correta.');
})().catch(e=>{console.error(e);process.exit(1)});
