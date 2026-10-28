"""Real installed Python Winit/Skia render, driven by external exact-window X11 audit."""
import asyncio,json,sys
from pathlib import Path
from py_skia_canvas import App,Window,Canvas
input,out,stop=map(Path,sys.argv[1:]);cfg=json.loads(input.read_text());out.mkdir(exist_ok=False);App.eventLoop=cfg.get('mode','native')
opts=dict(left=200,top=200,title='py-skia-canvas-G9-'+cfg['id'],borderless=True,background='white',fit=cfg.get('fit','contain'))
if cfg.get('page'):
    c=Canvas(100,60);c.newPage();c.newPage(80,50);opts.update(canvas=c,page=1)
w=Window(160,100,opts);events=[];frames=0;setup=0;ticks=0;timer_at_ready=0;timer_advanced=False
def event(e):
    """Record real owned UI payload, invoke original preventDefault when requested."""
    if e.type=='keydown' and e.key=='c' and cfg.get('prevent'):e.preventDefault()
    events.append({k:v for k,v in e.items() if k!='target' and not callable(v)})
for kind in ['move','resize','keydown','keyup','mousedown','mouseup','wheel','input','fullscreen','focus','blur','close']:w.on(kind,event)
def setup_event(e):
    """Count original setup dispatch (3.0.8 never emits it at initial frame1)."""
    global setup
    setup+=1
w.on('setup',setup_event)
def draw(e):
    """Original fixture commands in canvas units, real GUI core paints presented swapchain."""
    global frames,timer_at_ready,timer_advanced
    frames+=1;x=w.ctx;x.fillStyle='white';x.fillRect(0,0,w.canvas.width,w.canvas.height);x.fillStyle='#d02880';x.fillRect(5.25,10.5,60.5,30.25);x.strokeStyle='#123456';x.lineWidth=1.25;x.beginPath();x.moveTo(2,2);x.bezierCurveTo(12,60,80,0,95,40);x.stroke();x.font='13px sans-serif';x.fillStyle='#102030';x.fillText('Canvas GUI',3,55)
    if e.frame==5:timer_at_ready=ticks;print('READY',flush=True)
    if e.frame==10:timer_advanced=ticks>timer_at_ready
    if (stop.exists() and e.frame>=12) or e.frame>=300:w.close()
w.on('draw',draw)
async def main():
    """Schedule cooperative timer and original launch; native mode retains blocked loop semantics."""
    global ticks
    async def ticker():
        """Test-only asyncio scheduling observation, no native/context access."""
        global ticks
        while True:ticks+=1;await asyncio.sleep(.001)
    task=asyncio.create_task(ticker());session=App.launch();before=dict(running=App.running,same=session is App.launch());await session;task.cancel()
    try:await task
    except asyncio.CancelledError:pass
    error=None
    try:App.eventLoop='node'
    except Exception as e:error=dict(type=type(e).__name__,message=str(e))
    (out/'page.rgba').write_bytes(bytes(w.ctx.getImageData(0,0,w.canvas.width,w.canvas.height).data));(out/'page.png').write_bytes(w.canvas.toBufferSync('png'))
    (out/'run.json').write_text(json.dumps(dict(id=cfg['id'],before=before,after=dict(running=App.running,windows=len(App.windows),closed=w.closed),modeError=error,setup=setup,timerAdvanced=timer_advanced,events=events,frames=frames,state=w.state,canvas=[w.canvas.width,w.canvas.height],gpu=w.canvas.gpu,engine=w.canvas.engine))+'\n');print('DONE',flush=True)
asyncio.run(main())
