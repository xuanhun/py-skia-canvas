"""Real installed-wheel path/curve/clip/stroke GPU trace; no product rendering code."""
from py_skia_canvas import Canvas

canvas = Canvas(300, 150)
context = canvas.getContext("2d")
assert canvas.gpu and canvas.engine["renderer"] == "GPU", canvas.engine
print("TRACE_ENGINE", canvas.engine, flush=True)
context.save()
context.translate(15.25, 10.75)
context.beginPath()
context.ellipse(105.25, 60.5, 90.75, 45.25, 0.2, 0, 7)
context.clip()
context.setTransform(1.1, 0.15, -0.2, 0.85, 20.25, 10.75)
context.beginPath()
context.moveTo(0.25, 50.75)
context.bezierCurveTo(40.5, -20.25, 140.25, 150.75, 220.5, 30.25)
context.lineTo(200.5, 120.25)
context.closePath()
context.fillStyle = "#2878d9"
context.fill("evenodd")
context.setLineDash([4.25, 2.75, 1.25])
context.lineWidth = 3.25
context.lineCap = "round"
context.strokeStyle = "#cf3277"
context.stroke()
context.restore()
print("TRACE_REAL_READBACK_BEGIN requested=300x150", flush=True)
raw = bytes(context.getImageData(0, 0, 300, 150).data)
assert len(raw) == 180000 and len(set(raw)) > 4
print("TRACE_REAL_READBACK_END bytes=180000", flush=True)
print("TRACE_REAL_PNG_BEGIN", flush=True)
assert canvas.toBufferSync("png").startswith(b"\x89PNG")
print("TRACE_REAL_PNG_END", flush=True)

control = Canvas(300, 150)
control.gpu = False
print("TRACE_FRESH_CPU_CONTROL_BEGIN", flush=True)
ctx = control.getContext("2d")
ctx.beginPath()
ctx.rect(5.25, 7.5, 160.5, 90.25)
ctx.clip()
ctx.fillRect(0, 0, 300, 150)
assert len(ctx.getImageData(0, 0, 300, 150).data) == 180000
print("TRACE_FRESH_CPU_CONTROL_END", flush=True)
