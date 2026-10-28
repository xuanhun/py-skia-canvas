"""Trace default text/export while registering/resetting original caller-thread FontLibrary.

Alias selection via ctx.font remains a separate pending contract; no font bytes copied.
"""
from py_skia_canvas import Canvas, FontLibrary
FontLibrary.reset()
fonts=FontLibrary.use('Trace family','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
assert fonts[0]['family']=='Trace family' and FontLibrary.has('Trace family')
assert FontLibrary.family('Trace family')['weights']==[400]
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='#fff';ctx.fillRect(0,0,300,150)
ctx.fillStyle='#2060ff';ctx.fillText('AV fj FontLibrary',12.25,45.75)
assert ctx.measureText('AV fj FontLibrary').width>0
ctx.beginPath();ctx.roundRect(10.25,65.5,270.75,60.25,12.5)
ctx.strokeStyle='#ff2450';ctx.lineWidth=3.25;ctx.stroke()
FontLibrary.reset();assert not FontLibrary.has('Trace family')
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.fillText('CPU control',10,40)
assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
