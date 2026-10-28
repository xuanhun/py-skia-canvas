"""Installed-wheel public export capture, matching independent fixed official A driver."""
import asyncio,importlib.metadata,json,sys
from pathlib import Path
from py_skia_canvas import Canvas,Image,_native

async def resolve(value):
    """Await public Promise equivalent, owned result; no GPU context movement/test adjustment."""
    import inspect
    return await value if inspect.isawaitable(value) else value

def paint(x,i):
    """Same original fixture drawing commands; canvas units, no output compensation."""
    x.fillStyle=['#d34b7180','#339972ad','#3158bbaa'][i];x.fillRect(.25,.5,51.25,31.75);x.strokeStyle='#122e49';x.lineWidth=1.25;x.beginPath();x.moveTo(2,3);x.bezierCurveTo(5,40,45,0,68,35);x.stroke();x.font='11px sans-serif';x.fillStyle='#102030';x.fillText('Canvas '+str(i+1),4,43)

def main():
    """Capture clean installed public API, fresh output, no fallback/skip/tolerance."""
    input,out=map(Path,sys.argv[1:3]);backend=sys.argv[3] if len(sys.argv)>3 else 'gpu';assert backend in ('gpu','cpu');out.mkdir(exist_ok=False)
    c=Canvas(72,48);first=c.getContext('2d');paint(first,0);second=c.newPage(80,52);paint(second,1);third=c.newPage(96,60);paint(third,2);first.fillStyle='#ffaa22';first.fillRect(55,6,6,9)
    pages=dict(count=len(c.pages),current=c.getContext('2d') is third,order=[[first,second,third].index(x) for x in c.pages],width=c.width,height=c.height)
    report=dict(status='PYTHON_IMPLEMENTATION_CAPTURED',version=importlib.metadata.version('py-skia-canvas'),pages=pages,cases=[])
    assert (c.gpu and c.engine['renderer']=='GPU') if backend=='gpu' else (not c.gpu and c.engine['renderer']=='CPU')
    if backend=='cpu':first._native.audit_surface_capture(True)
    for cfg in json.loads(input.read_text())['cases']:
        directory=out/cfg['id'];directory.mkdir();entry=dict(id=cfg['id'],observations={},files=[]);report['cases'].append(entry)
        try:
            method=cfg['method'];ext=cfg['extension'];opts=cfg['opts']
            if method=='property':result=asyncio.run(resolve(getattr(c,ext)))
            elif method=='toDataURL':result=c.toDataURL(ext,cfg.get('quality'))
            elif 'File' in method:
                result=asyncio.run(resolve(getattr(c,method)(str(directory/cfg['filename']),opts)));entry['observations']['returned']='undefined' if result is None else result
            else:result=asyncio.run(resolve(getattr(c,method)(ext,opts)))
            if isinstance(result,str):
                import base64
                entry['observations']['prefix']=result.split(',')[0];result=base64.b64decode(result.split(',')[1])
            if isinstance(result,bytes):(directory/('buffer.'+('pdf' if 'pdf' in ext else 'svg' if 'svg' in ext else 'raw' if ext=='raw' else 'bin'))).write_bytes(result)
            entry['observations']['threw']=False
        except Exception as e:entry['observations']=dict(threw=True,type=type(e).__name__,message=str(e).replace(str(directory),'<case>'))
        entry['files']=sorted(p.name for p in directory.iterdir())
        for f in [f for f in entry['files'] if f.endswith('.svg')]:
            image=Image((directory/f).read_bytes());r=Canvas(image.width,image.height);r.getContext('2d').drawImage(image,0,0);(directory/(f+'.png')).write_bytes(r.toBufferSync('png'))
    s=Canvas(16,12);x=s.getContext('2d');x.fillStyle='red';x.fillRect(0,0,16,12);promise=s.toBuffer('raw');x.fillStyle='blue';x.fillRect(0,0,16,12);data=asyncio.run(resolve(promise));(out/'snapshot.raw').write_bytes(data);report['snapshot']=list(data[:4]);report['asyncAudit']=promise._audit
    report['backendRequirement']=backend
    if backend=='cpu':
        report['nativeSurfaceAudit']=json.loads(first._native.audit_surface_capture(False));assert not report['nativeSurfaceAudit']['surfaces']
    (out/'run.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(report['cases']),pages=pages)))

if __name__=='__main__':main()
