"""Trace real installed standalone Path2D snapshots/operations through default Vulkan."""
from py_skia_canvas import Canvas, Path2D

canvas=Canvas(300,150)
ctx=canvas.getContext("2d")
assert canvas.gpu and canvas.engine["renderer"]=="GPU",canvas.engine
print("TRACE_ENGINE",canvas.engine,flush=True)
path=Path2D("M10 10L220 20Q260 100 100 130L20 80Z")
other=Path2D()
other.ellipse(150,75,80,40,0.2,0,7)
combined=path.xor(other)
ctx.translate(10.25,3.5)
ctx.clip(path)
ctx.fillStyle="#2878d9"
ctx.fill(combined,"evenodd")
ctx.strokeStyle="#cf3277"
ctx.lineWidth=3.25
ctx.stroke(combined.round(5.25))
print("TRACE_REAL_READBACK_BEGIN requested=300x150",flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data)
assert len(raw)==180000 and len(set(raw))>4
print("TRACE_REAL_READBACK_END bytes=180000",flush=True)
print("TRACE_REAL_PNG_BEGIN",flush=True)
assert canvas.toBufferSync().startswith(b"\x89PNG")
print("TRACE_REAL_PNG_END",flush=True)
control=Canvas(300,150)
control.gpu=False
print("TRACE_FRESH_CPU_CONTROL_BEGIN",flush=True)
c=control.getContext("2d")
c.fill(path)
assert len(c.getImageData(0,0,300,150).data)==180000
print("TRACE_FRESH_CPU_CONTROL_END",flush=True)
