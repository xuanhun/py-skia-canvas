"""Trace original colored decoration, wrapped/stroked text and GPU export, owner only."""
from py_skia_canvas import Canvas,FontLibrary
FontLibrary.reset();FontLibrary.use('Trace Decoration','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='white';ctx.fillRect(0,0,300,150)
ctx.font='24px "Trace Decoration"';ctx.fillStyle='#286bc5'
ctx.textDecoration='wavy underline 2px #d02060';ctx.textWrap=True
assert ctx.textDecoration=='wavy underline 2px #d02060'
assert ctx.measureText('AV ffi decorated text',230.5).width>0
print('TRACE_DECORATION',ctx.textDecoration,flush=True)
ctx.fillText('AV ffi decorated text',10.25,35.75,230.5)
ctx.save();ctx.textWrap=False;ctx.textDecoration='double overline 1px #10b060';ctx.strokeText('Decoration',10.25,125.5);ctx.restore()
assert ctx.textDecoration=='wavy underline 2px #d02060'
FontLibrary.reset()
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.font='24px serif';c.textDecoration='underline red';c.fillText('CPU decoration',10,40)
assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
