"""Trace real installed shared gradient State and shader materialization through default Vulkan."""
from py_skia_canvas import Canvas

canvas=Canvas(300,150)
ctx=canvas.getContext("2d")
assert canvas.gpu and canvas.engine["renderer"]=="GPU",canvas.engine
print("TRACE_ENGINE",canvas.engine,flush=True)
gradient=ctx.createConicGradient(0.27,150.25,75.5)
gradient.addColorStop(0,"#2060ff")
gradient.addColorStop(0.5,"rgba(40,220,70,0.6)")
gradient.addColorStop(1,"#ff2450")
ctx.fillStyle=gradient
ctx.fillRect(2.25,3.5,295.5,143.25)
gradient.addColorStop(0.25,"#ffe020")
ctx.strokeStyle=gradient
ctx.lineWidth=8.25
ctx.beginPath(); ctx.ellipse(150,75,100,40,0.2,0,7); ctx.stroke()
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
c=control.getContext("2d"); c.fillStyle=gradient; c.fillRect(0,0,300,150)
assert len(c.getImageData(0,0,300,150).data)==180000
print("TRACE_FRESH_CPU_CONTROL_END",flush=True)
