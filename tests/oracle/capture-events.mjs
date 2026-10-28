// Real official Image EventEmitter contract, no synthetic emitter implementation.
import fs from 'node:fs';import{createRequire}from'node:module';let[modulePath,input,out]=process.argv.slice(2),{Image}=createRequire(import.meta.url)(modulePath),cases=[];
for(let cfg of JSON.parse(fs.readFileSync(input)).cases){let e=new Image(),calls=[],callbacks={},warnings=[],observations=[];
 for(let name of ['f0','f1','f2','meta'])callbacks[name]=function(...args){calls.push([name,args]);};
 const enc=v=>{if(v===e)return{$self:true};if(v===undefined)return{$undefined:true};if(typeof v==='number'&&(!Number.isFinite(v)||Object.is(v,-0)))return{$number:Object.is(v,-0)?'-0':String(v)};if(typeof v==='function'){for(let[k,f]of Object.entries(callbacks))if(v===f)return{$callback:k};return{$once:Object.entries(callbacks).find(([k,f])=>v.listener===f)?.[0]};}if(Array.isArray(v))return v.map(enc);if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).map(([k,x])=>[k,enc(x)]));return v;};
 const dec=v=>v&&typeof v==='object'?(v.$undefined?undefined:v.$number?Number(v.$number):v.$callback?callbacks[v.$callback]:Array.isArray(v)?v.map(dec):Object.fromEntries(Object.entries(v).map(([k,x])=>[k,dec(x)]))):v;
 const warned=w=>warnings.push({name:w.name,message:w.message,count:w.count,type:w.type});process.on('warning',warned);
 for(let op of cfg.ops){try{observations.push({value:enc(e[op.name](...(op.args||[]).map(dec)))});}catch(x){observations.push({error:{type:x.name,message:x.message}});}}
 await new Promise(r=>setImmediate(r));process.off('warning',warned);cases.push({id:cfg.id,observations,calls:enc(calls),warnings:enc(warnings)});
}
fs.writeFileSync(out,JSON.stringify({cases})+'\n');
