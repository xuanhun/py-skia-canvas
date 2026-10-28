"""Owner-thread original filter/shadow/composite/marker rendering with real GPU export."""
from pathlib import Path
from py_skia_canvas import Canvas,Image,Path2D
image=Image(Path('/mnt/c/code/py-skia-canvas/tests/assets/rgba-grid.png').read_bytes())
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='white';ctx.fillRect(0,0,300,150)
ctx.filter='blur(1px) hue-rotate(37deg)';ctx.shadowColor='rgba(20,120,80,.7)';ctx.shadowBlur=3.5;ctx.shadowOffsetX=5.25;ctx.shadowOffsetY=4.5
ctx.drawImage(image,8.25,9.75,100.5,100.5)
ctx.save();ctx.globalCompositeOperation='source-in';ctx.globalAlpha=.75;ctx.fillStyle='#d02880';ctx.fillRect(70,20,100,80);ctx.restore()
marker=Path2D('M-2 -2L4 0L-2 2Z');ctx.lineDashMarker=marker;ctx.lineDashFit='follow';ctx.setLineDash([12,6]);ctx.strokeStyle='#2060c0';ctx.lineWidth=2
ctx.beginPath();ctx.moveTo(160,20);ctx.bezierCurveTo(220,0,180,140,285,120);ctx.stroke()
ctx.font='24px DejaVu Sans';ctx.fillStyle='#d02880';ctx.fillText('Skia effects',20,135)
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.filter='blur(1px) invert(.5)';c.shadowColor='red';c.shadowBlur=2;c.drawImage(image,10,10,100,100)
assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
