// One fresh official A process per App singleton/immutable loop mode contract.
import fs from 'node:fs';import {createRequire} from 'node:module';
let [modulePath,input,id,out]=process.argv.slice(2),{Canvas,App,Window}=createRequire(import.meta.url)(modulePath),cfg=JSON.parse(fs.readFileSync(input)).cases.find(x=>x.id===id),observations=[];
function state(w){return {...w.state,canvas:[w.canvas.width,w.canvas.height],pages:w.canvas.pages.length,ctxIndex:w.canvas.pages.indexOf(w.ctx),running:App.running,mode:App.eventLoop,fps:App.fps,windows:App.windows.length};}
function encode(v){if(v===undefined)return {$undefined:true};if(v&&typeof v==='object')return Array.isArray(v)?v.map(encode):Object.fromEntries(Object.entries(v).map(([k,v])=>[k,encode(v)]));return v;}
let w;
try{
 let opts={...cfg.options};if(cfg.multipage){let c=new Canvas(96,64);c.newPage();c.newPage(128,72);opts.canvas=c;}
 w=Object.hasOwn(cfg,'constructor')?new Window(...cfg.constructor):new Window(cfg.width,cfg.height,opts);
 for(let op of cfg.ops){try{
   if(op.op==='set')w[op.name]=op.value;
   if(op.op==='setApp')App[op.name]=op.value;
   if(op.op==='replaceCanvas'){let c=new Canvas(64,48);c.newPage();w.canvas=c;}
   if(op.op==='closeOpen'){let e=[];w.on('close',v=>e.push([v.type,v.target===w]));w.close();w.close();w.open();w.open();observations.push({closeEvents:e,closed:w.closed,windows:App.windows.length});}
   if(op.op==='events'){
    let calls=[],a=e=>calls.push('a:'+e.n),b=e=>calls.push('b:'+e.n),c=e=>calls.push('c:'+e.n);
    w.on('test',a);w.once('test',b);w.prependOnceListener('test',c);w.on('test',a);
    let raw=w.rawListeners('test'),before=w.listeners('test').map(x=>x===a?'a':x===b?'b':'c');
    w.emit('test',{n:1});w.removeListener('test',a);w.emit('test',{n:2});
    observations.push({calls,before,rawOnce:raw[0].listener===c,names:w.eventNames(),count:w.listenerCount('test'),same:w.listeners('test')[0]===a,max:w.getMaxListeners()});w.removeAllListeners();
   }
   observations.push({threw:false});
  }catch(e){observations.push({threw:true,type:e.name,message:e.message});}}
 observations.push(state(w));
}catch(e){observations.push({threw:true,type:e.name,message:e.message});}
fs.writeFileSync(out,JSON.stringify(encode({id,observations}))+'\n');
for(let win of App.windows)win.close();App.quit();await App.launch();
