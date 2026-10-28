// Original fixed css.js parser, independent of candidate facade/native state.
import fs from 'node:fs';import{createRequire}from'node:module';
const require=createRequire(import.meta.url),css=require(process.argv[2]+'/lib/classes/css.js');
const decode=v=>Array.isArray(v)?v.map(decode):v&&typeof v==='object'&&'$undefined'in v?undefined:v&&typeof v==='object'&&'$number'in v?Number(v.$number):v;
const encode=v=>typeof v==='number'?Number.isNaN(v)?{$number:'NaN'}:!Number.isFinite(v)?{$number:String(v)}:Object.is(v,-0)?{$number:'-0'}:v:Array.isArray(v)?v.map(encode):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,encode(x)])):v;
const inputs=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const results=inputs.map(({value})=>{try{return{value:encode(css.filter(decode(value)))}}catch(e){return{error:{type:e.name,message:e.message}}}});
fs.writeFileSync(process.argv[4],JSON.stringify(results,null,2)+'\n');
