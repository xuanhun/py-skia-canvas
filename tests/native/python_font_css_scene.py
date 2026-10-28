"""Trace original custom alias selection, FontSpec state and Vulkan text export.

System font path only, no font bytes bundled; owner thread throughout.
"""
from py_skia_canvas import Canvas,FontLibrary
FontLibrary.reset();FontLibrary.use('Trace CSS','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='white';ctx.fillRect(0,0,300,150)
ctx.font='small-caps 28px/1.5 "Trace CSS"'
assert 'Trace CSS' in ctx.font and ctx.measureText('AV fj ffi').width>50
print('TRACE_SELECTED_FONT',ctx.font,flush=True)
ramp=ctx.createLinearGradient(0,0,300,150);ramp.addColorStop(0,'#2060ff');ramp.addColorStop(1,'#ff2450')
ctx.fillStyle=ramp;ctx.fillText('AV fj ffi Canvas',10.25,55.75)
ctx.save();ctx.font='bold 32px serif';ctx.strokeText('Font CSS',10.25,110.5);ctx.restore()
assert 'Trace CSS' in ctx.font
FontLibrary.reset()
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.font='24px serif';c.fillText('CPU',10,40)
assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
