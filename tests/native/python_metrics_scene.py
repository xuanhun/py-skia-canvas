"""Observe owned metrics then draw original multilingual text on the owner GPU thread."""
from py_skia_canvas import Canvas
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='white';ctx.fillRect(0,0,300,150)
ctx.font='24px DejaVu Sans';ctx.fillStyle='#286bc5';ctx.textWrap=True
text='AV ffi 中文\nمرحبا world';m=ctx.measureText(text,250.5)
assert m.width>0 and len(m.lines)>=2 and m.lines[0]['runs']
width=m.width;m.lines[0]['runs'][0]['auditNote']='owned'
ctx.fillText(text,10.25,35.75,250.5)
ctx.save();ctx.direction='rtl';ctx.fillText('שלום العربية',280,125.5);ctx.restore()
assert m.width==width
print('TRACE_METRICS',width,len(m.lines),flush=True)
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.font='24px serif';assert c.measureText('CPU metrics').width>0
c.fillText('CPU metrics',10,40);assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
