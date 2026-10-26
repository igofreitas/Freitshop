const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),requests=[];
function make(){return {value:'',children:[],dataset:{},style:{},textContent:'',hidden:false,disabled:false,listeners:{},addEventListener(type,fn){this.listeners[type]=fn},setAttribute(){},setCustomValidity(v){this.validationMessage=v},reportValidity(){return !this.validationMessage},reset(){},appendChild(c){this.children.push(c)},append(...c){this.children.push(...c)},replaceChildren(){this.children=[]}};}
const get=id=>{if(!nodes.has(id))nodes.set(id,make());return nodes.get(id)};
const context=vm.createContext({document:{getElementById:get,createElement:make,querySelectorAll:()=>[get('feedbackSave')],querySelector:()=>({value:'5'})},location:{origin:'https://example.com'},fetch:async(path,options)=>{requests.push({path,options});return {ok:true,json:async()=>path==='/api/feedback-config'?{enabled:true,siteOrigin:'https://example.com'}:options.method==='POST'?{message:'Obrigado!'}:{items:[],nextBefore:null}};}});
vm.runInContext(fs.readFileSync(__dirname+'/feedback.js','utf8').replace('export function initializeFeedback','function initializeFeedback'),context);
(async()=>{
 await vm.runInContext('initializeFeedback()',context);assert.equal(get('feedbackSave').disabled,false);
 get('feedbackComment').value='Comentário sem login';await get('feedbackForm').listeners.submit({preventDefault(){}});
 const posted=requests.find(r=>r.options.method==='POST');assert(posted);assert.equal(posted.options.headers.Authorization,undefined);assert.equal(JSON.parse(posted.options.body).rating,5);assert.equal(JSON.parse(posted.options.body).comment,'Comentário sem login');
 get('feedbackComment').value='🙂'.repeat(501);vm.runInContext('countCharacters()',context);assert(get('feedbackComment').validationMessage);
 vm.runInContext(`appendReviews([{rating:5,comment:'<script>alert(1)</script>',updatedAt:'2026-10-25'}])`,context);
 const last=get('feedbackList').children.at(-1);assert.equal(last.children[0].textContent,'Visitante');assert.equal(last.children[2].textContent,'<script>alert(1)</script>');
 console.log('PASS: anonymous form sends no token, ratings/character limit retained, comment rendered as text.');
})().catch(e=>{console.error(e);process.exit(1)});
