// Fixed official A public exports, never imports development B. Output files are evidence.
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';
let [modulePath,input,directory,backend='gpu']=process.argv.slice(2),out=path.resolve(directory);if(!['gpu','cpu'].includes(backend))throw Error('Unknown backend profile');fs.mkdirSync(out,{recursive:false});
let api=createRequire(import.meta.url)(modulePath),{Canvas,Image}=api;
function paint(x,i){x.fillStyle=['#d34b7180','#339972ad','#3158bbaa'][i];x.fillRect(.25,.5,51.25,31.75);x.strokeStyle='#122e49';x.lineWidth=1.25;x.beginPath();x.moveTo(2,3);x.bezierCurveTo(5,40,45,0,68,35);x.stroke();x.font='11px sans-serif';x.fillStyle='#102030';x.fillText('Canvas '+(i+1),4,43);}
let c=new Canvas(72,48),first=c.getContext('2d');paint(first,0);let second=c.newPage(80,52);paint(second,1);let third=c.newPage(96,60);paint(third,2);first.fillStyle='#ffaa22';first.fillRect(55,6,6,9);
if(backend==='cpu'&&(c.gpu||c.engine.renderer!=='CPU'))throw Error('CPU required');
let pages={count:c.pages.length,current:c.getContext('2d')===third,order:c.pages.map(x=>[first,second,third].indexOf(x)),width:c.width,height:c.height};let report={status:'ORACLE_CAPTURED',version:'3.0.8',pages,cases:[]};
let configs=JSON.parse(fs.readFileSync(input)).cases;
for(let cfg of configs){let dir=path.join(out,cfg.id);fs.mkdirSync(dir);let entry={id:cfg.id,observations:{},files:[]};report.cases.push(entry);
 try{let result,ext=cfg.extension,opts=cfg.opts;
  if(cfg.method==='property')result=await c[ext];
  else if(cfg.method==='toDataURL')result=c.toDataURL(ext,cfg.quality);
  else if(cfg.method.includes('File')){let dest=path.join(dir,cfg.filename);result=await c[cfg.method](dest,opts);entry.observations.returned=result===undefined?'undefined':result;}
  else result=await c[cfg.method](ext,opts);
  if(typeof result==='string'){entry.observations.prefix=result.split(',')[0];result=Buffer.from(result.split(',')[1],'base64');}
  if(Buffer.isBuffer(result))fs.writeFileSync(path.join(dir,'buffer.'+(ext.includes('pdf')?'pdf':ext.includes('svg')?'svg':ext==='raw'?'raw':'bin')),result);
  entry.observations.threw=false;
 }catch(e){entry.observations={threw:true,type:e.name,message:e.message.replaceAll(dir,'<case>')};}
 entry.files=fs.readdirSync(dir).sort();
 for(let f of entry.files.filter(f=>f.endsWith('.svg'))){let img=new Image(fs.readFileSync(path.join(dir,f))),r=new Canvas(img.width,img.height);r.getContext('2d').drawImage(img,0,0);fs.writeFileSync(path.join(dir,f+'.png'),r.toBufferSync('png'));}
}
// Original Promise starts before mutation; async snapshot must retain the first paint.
let s=new Canvas(16,12),x=s.getContext('2d');x.fillStyle='red';x.fillRect(0,0,16,12);let promise=s.toBuffer('raw');x.fillStyle='blue';x.fillRect(0,0,16,12);fs.writeFileSync(path.join(out,'snapshot.raw'),await promise);report.snapshot=[...fs.readFileSync(path.join(out,'snapshot.raw')).subarray(0,4)];
fs.writeFileSync(path.join(out,'run.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({cases:report.cases.length,pages}));
