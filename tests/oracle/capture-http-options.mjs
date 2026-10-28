// Only owned loopback URLs; standard public Image loading, exact explicit request options.
import fs from'node:fs';import{createRequire}from'node:module';let[modulePath,input,out]=process.argv.slice(2),{loadImage,ImageData}=createRequire(import.meta.url)(modulePath),cfg=JSON.parse(fs.readFileSync(input)),records=[];
for(let c of cfg.cases){let src=cfg.base+c.path;if(c.urlObject)src=new URL(src);try{let image=await loadImage(src,c.options);records.push({id:c.id,width:image.width,height:image.height,pixels:[...new ImageData(image).data]});}catch(e){records.push({id:c.id,error:{type:e.name,message:e.message}});}}
fs.writeFileSync(out,JSON.stringify(records)+'\n');
