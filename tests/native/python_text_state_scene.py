"""Trace original text state, selected alias, wrapping and styled GPU export.

Owner thread only; font bytes remain system resources. Not a complete glyph audit.
"""
from py_skia_canvas import Canvas,FontLibrary
FontLibrary.reset();FontLibrary.use('Trace Text State','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='white';ctx.fillRect(0,0,300,150)
ctx.font='24px "Trace Text State"';ctx.textAlign='center';ctx.textBaseline='middle';ctx.direction='rtl'
ctx.letterSpacing='.5px';ctx.wordSpacing='2px';ctx.fontStretch='condensed';ctx.fontVariant='small-caps';ctx.fontHinting=True;ctx.textWrap=True
assert ctx.textAlign=='center' and ctx.textBaseline=='middle' and ctx.direction=='rtl'
assert ctx.measureText('AV ffi text wraps here',180.25).width>0
print('TRACE_TEXT_STATE',ctx.font,ctx.textAlign,ctx.direction,ctx.letterSpacing,ctx.fontVariant,ctx.textWrap,flush=True)
ramp=ctx.createLinearGradient(0,0,300,150);ramp.addColorStop(0,'#2060ff');ramp.addColorStop(1,'#ff2450')
ctx.fillStyle=ramp;ctx.fillText('AV ffi text wraps here',150.25,45.75,220.5)
ctx.save();ctx.textWrap=False;ctx.textBaseline='alphabetic';ctx.strokeText('State AV ffi',150.25,125.5);ctx.restore()
assert ctx.textWrap and ctx.textBaseline=='middle'
FontLibrary.reset()
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.font='24px serif';c.textAlign='center';c.textWrap=True;c.letterSpacing='1px';c.fillText('CPU text state',150,40,200)
assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
