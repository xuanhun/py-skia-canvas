"""Real default-GPU argument conversion, independent Context and original path rendering."""
from py_skia_canvas import Canvas,CanvasRenderingContext2D,Path2D
c=Canvas('300',[150],{'textGamma':'1.4'})
detached=CanvasRenderingContext2D(c);assert c.pages==[] and detached.canvas is c
detached.fillStyle='#e09030';detached.fillRect('1','2',[30],20)
x=c.getContext(['2d']);assert x is not detached and c.pages==[x]
x.fillStyle='white';x.fillRect(0,0,300,150)
g=x.createLinearGradient('0',[],['300'],0);g.addColorStop('0','#d02880');g.addColorStop([1],'#2070d0');x.fillStyle=g
x.fillRect(['.25'],'.5','180.5',[100.25])
p=Path2D();p.moveTo('20',110);p.bezierCurveTo(80,'30',150,140,'270',105)
x.strokeStyle='#202020';x.lineWidth='3';x.setLineDash(['7',2]);x.stroke(p)
assert c.gpu and c.engine['renderer']=='GPU'
print('TRACE_ENGINE',c.engine,flush=True)
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(x.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
other=bytes(detached.getImageData(0,0,300,150).data);assert raw!=other
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert c.toBufferSync('png').startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
z=control.newPage();z.fillRect(10,10,100,100);assert len(z.getImageData(0,0,300,150).data)==180000
assert control.toBufferSync().startswith(b'\x89PNG')
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
