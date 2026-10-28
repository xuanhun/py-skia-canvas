"""Real owner-thread decoded images, pixel blit, bitmap/vector sources and shared shaders."""
from pathlib import Path
from py_skia_canvas import Canvas,Image,ImageData
root=Path('/mnt/c/code/py-skia-canvas/tests/assets')
image=Image((root/'rgba-grid.png').read_bytes());svg=Image((root/'checker.svg').read_bytes())
canvas=Canvas(300,150);ctx=canvas.getContext('2d')
assert canvas.gpu and canvas.engine['renderer']=='GPU',canvas.engine
print('TRACE_ENGINE',canvas.engine,flush=True)
ctx.fillStyle='white';ctx.fillRect(0,0,300,150)
ctx.drawImage(image,8.25,9.75,110.5,110.5);ctx.drawImage(svg,1,2,26,27,120,10,75,75)
data=ImageData(image);data.data.set([255,0,80,255]);ctx.putImageData(data,12,130)
source=Canvas(16,16);s=source.getContext('2d');s.fillStyle='#e03080';s.fillRect(2,2,10,10)
ctx.drawImage(source,220,10,64,64);ctx.drawCanvas(source,225,80,64,64)
pattern=ctx.createPattern(image,'repeat');pattern.setTransform(2,0,0,2,0,0)
ctx.fillStyle=pattern;ctx.fillRect(125,92,80,40)
ctx.fillStyle=ctx.createTexture(5,{'color':'#2460c0','line':1.25});ctx.fillRect(120,100,85,35)
print('TRACE_REAL_READBACK_BEGIN requested=300x150',flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print('TRACE_REAL_READBACK_END bytes=180000',flush=True)
print('TRACE_REAL_PNG_BEGIN',flush=True)
assert canvas.toBufferSync().startswith(b'\x89PNG')
print('TRACE_REAL_PNG_END',flush=True)
control=Canvas(300,150);control.gpu=False
print('TRACE_FRESH_CPU_CONTROL_BEGIN',flush=True)
c=control.getContext('2d');c.drawImage(image,10,10,100,100);c.putImageData(data,150,10)
assert len(c.getImageData(0,0,300,150).data)==180000
print('TRACE_FRESH_CPU_CONTROL_END',flush=True)
