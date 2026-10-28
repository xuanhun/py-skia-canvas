"""Installed-wheel one-process public App/Window contract capture, ordinary inputs."""
import asyncio,json,sys
from pathlib import Path
from py_skia_canvas import Canvas,App,Window,undefined

def encode(v):
    """Serialize undefined ordinary GUI observations without native coercion/tolerance."""
    if v is undefined:return {'$undefined':True}
    if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [encode(x) for x in v]
    return v

def main():
    """Fresh App singleton case, output JSON and real GUI cleanup; no fallback or skip."""
    input,ident,out=sys.argv[1:];cfg=next(c for c in json.loads(Path(input).read_text())['cases'] if c['id']==ident);observations=[]
    try:
        opts=cfg['options'].copy()
        if cfg.get('multipage'):
            c=Canvas(96,64);c.newPage();c.newPage(128,72);opts['canvas']=c
        w=Window(*cfg['constructor']) if 'constructor'in cfg else Window(cfg['width'],cfg['height'],opts)
        for op in cfg['ops']:
            try:
                if op['op']=='set':setattr(w,op['name'],op['value'])
                if op['op']=='setApp':setattr(App,op['name'],op['value'])
                if op['op']=='replaceCanvas':
                    c=Canvas(64,48);c.newPage();w.canvas=c
                if op['op']=='closeOpen':
                    events=[];w.on('close',lambda e:events.append([e.type,e.target is w]));w.close();w.close();w.open();w.open();observations.append(dict(closeEvents=events,closed=w.closed,windows=len(App.windows)))
                if op['op']=='events':
                    calls=[]
                    def a(e):calls.append('a:'+str(e.n))
                    def b(e):calls.append('b:'+str(e.n))
                    def c(e):calls.append('c:'+str(e.n))
                    w.on('test',a);w.once('test',b);w.prependOnceListener('test',c);w.on('test',a);raw=w.rawListeners('test');before=['a' if x is a else 'b' if x is b else 'c' for x in w.listeners('test')]
                    w.emit('test',dict(n=1));w.removeListener('test',a);w.emit('test',dict(n=2));observations.append(dict(calls=calls,before=before,rawOnce=raw[0].listener is c,names=w.eventNames(),count=w.listenerCount('test'),same=w.listeners('test')[0] is a,max=w.getMaxListeners()));w.removeAllListeners()
                observations.append(dict(threw=False))
            except Exception as e:observations.append(dict(threw=True,type=type(e).__name__,message=str(e)))
        observations.append(dict(**w.state,canvas=[w.canvas.width,w.canvas.height],pages=len(w.canvas.pages),ctxIndex=w.canvas.pages.index(w.ctx),running=App.running,mode=App.eventLoop,fps=App.fps,windows=len(App.windows)))
    except Exception as e:observations.append(dict(threw=True,type=type(e).__name__,message=str(e)))
    Path(out).write_text(json.dumps(encode(dict(id=ident,observations=observations)))+'\n')
    for win in App.windows:win.close()
    App.quit();asyncio.run(App.launch())

if __name__=='__main__':main()
