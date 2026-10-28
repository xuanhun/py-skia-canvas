// Fixed-official loading/event oracle. Local synthetic bytes/loopback server only.
import fs from 'node:fs';import {createRequire}from'node:module';
const api=createRequire(import.meta.url)(process.argv[2]),cfg=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const bytes=fs.readFileSync(cfg.png),raw=fs.readFileSync(cfg.raw),records=[];
const info=i=>({width:i.width,height:i.height,complete:i.complete});
const err=e=>({type:e.name,message:e.message});
const pixels=i=>Array.from(new api.ImageData(i).data);
let image=await api.loadImage(bytes);records.push({case:'buffer',...info(image),src:image.src,pixels:pixels(image)});
image=await api.loadImage(cfg.png);records.push({case:'file',...info(image),src:image.src});
image=await api.loadImage('data:image/png;base64,'+bytes.toString('base64'));records.push({case:'dataurl',...info(image),pixels:pixels(image)});
for(const endpoint of ['/image','/redirect']){image=await api.loadImage(cfg.base+endpoint,{headers:{'X-Canvas-Probe':'owner'}});records.push({case:endpoint,...info(image),src:image.src,pixels:pixels(image)});}
for(const source of [Buffer.from('broken'),cfg.missing,cfg.base+'/missing']){
 try{await api.loadImage(source);records.push({case:'failure',threw:false});}catch(e){records.push({case:'failure',threw:true,...err(e)});}
}
const data=await api.loadImageData(raw,8,8);records.push({case:'raw',width:data.width,height:data.height,data:Array.from(data.data)});
const fromFile=await api.loadImageData(cfg.raw,8,8,{colorType:'rgba'});records.push({case:'raw-file',width:fromFile.width,height:fromFile.height,data:Array.from(fromFile.data)});
image=new api.Image();records.push({case:'empty',...info(image),src:image.src,onload:typeof image.onload,onerror:typeof image.onerror});
try{await image.decode();}catch(e){records.push({case:'unset-decode',...err(e)});}
let events=[];const cb=i=>events.push(i.width);image.once('load',cb);image.on('load',cb);image.src=bytes;image.src=fs.readFileSync(cfg.svg);records.push({case:'once-on',events});
events=[];image.onload=i=>events.push('property:'+i.width);image.onload=false;image.src=bytes;records.push({case:'onload-clear',events,cleared:image.onload===null});
events=[];image.onerror=e=>events.push(err(e));image.src=Buffer.from('broken');try{await image.decode();}catch(e){records.push({case:'broken-src',...info(image),events,decode:err(e)});}
events=[];image=new api.Image();image.onload=i=>events.push(info(i));image.src=cfg.base+'/slow';image.src=cfg.base+'/image';const decoded=await image.decode();await new Promise(resolve=>setTimeout(resolve,250));records.push({case:'latest',...info(image),same:decoded===image,events});
records.push({case:'complete-decode',same:await image.decode()===image});
image=new api.Image();events=[];image.onerror=e=>events.push(err(e));image.src=cfg.base+'/missing';try{await image.decode();}catch(e){records.push({case:'http-src-error',...info(image),src:image.src,events,decode:err(e)});}
process.stdout.write('IMAGERY_LOADING_JSON='+JSON.stringify(records)+'\n');
