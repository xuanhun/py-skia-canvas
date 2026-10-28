"""Default GPU multipage, owner materialization and native Rayon worker GPU trace."""
import asyncio,json
from py_skia_canvas import Canvas
c=Canvas(300,150);x=c.getContext('2d');x.fillStyle='#d02880';x.fillRect(.25,.5,180.5,100.25);x.font='24px sans-serif';x.fillStyle='black';x.fillText('Canvas export',20,130)
assert c.gpu and c.engine['renderer']=='GPU'
print('TRACE_ENGINE',c.engine,flush=True)
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(x.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
y=c.newPage(300,150);y.fillStyle='#2070d0';y.fillRect(0,0,200,100);y.font='24px sans-serif';y.fillStyle='black';y.fillText('Async page',20,130)
print('TRACE_REAL_PNG_BEGIN',flush=True)
c.toBufferSync('raw')
p=c.toBuffer('png')
async def wait():assert (await p).startswith(b'\x89PNG')
asyncio.run(wait());assert p._audit['cachedTexturesBefore']==1 and p._audit['cachedTexturesAfter']==0,p._audit
assert p._audit['owner']!=p._audit['worker'];print('TRACE_ASYNC_AUDIT',json.dumps(p._audit),flush=True)
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
z=control.newPage();z.fillRect(10,10,100,100);assert len(z.getImageData(0,0,300,150).data)==180000;assert control.toBufferSync().startswith(b'\x89PNG')
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
