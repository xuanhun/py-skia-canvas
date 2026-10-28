// Development observer only. Raw selected table bytes go directly to parent memory
// for hashing; this process never writes font/table bytes to disk.
import fs from 'node:fs';import{createRequire}from'node:module';
const require=createRequire(import.meta.url),api=require(process.argv[2]);
const fixture=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const encode=v=>typeof v==='number'?(Number.isNaN(v)?{$number:'NaN'}:!Number.isFinite(v)?{$number:String(v)}:Object.is(v,-0)?{$number:'-0'}:v):Array.isArray(v)?v.map(encode):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,encode(x)])):v;
const cases=[];
for(const item of fixture.cases){
 const canvas=new api.Canvas(item.width,item.height),ctx=canvas.getContext('2d');
 const objects={canvas,ctx,fontLibrary:api.FontLibrary};let observation;
 for(const op of item.ops){
  if(op.op==='set')objects[op.target][op.name]=op.value;
  else if(op.op==='call'){
   const result=objects[op.target][op.name](...(op.args||[]));
   if(op.name==='measureText'&&op.save==='metrics')observation={id:item.id,metrics:result,glyphs:JSON.parse(ctx.ƒ('debugGlyphs',...(op.args||[])))};
  }else throw Error('Unsupported audit fixture operation: '+op.op);
 }
 if(!observation)throw Error('No declared metrics observation');cases.push(observation);
}
process.stdout.write('GLYPH_AUDIT_JSON='+JSON.stringify(encode(cases))+'\n');
