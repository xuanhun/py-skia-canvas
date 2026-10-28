"""Installed-wheel native GPU trace scene, not product rendering code or an oracle."""
from py_skia_canvas import Canvas

canvas = Canvas(300, 150)
context = canvas.getContext("2d")
assert canvas.gpu and canvas.engine["renderer"] == "GPU", canvas.engine
print("TRACE_ENGINE", canvas.engine, flush=True)
context.fillStyle = "#ffffff"
context.fillRect(0, 0, 300, 150)
context.fillStyle = "#2878d9"
context.fillRect(10.25, 11.75, 113.5, 63.25)
context.fillStyle = "black"
context.fillText("Canvas AV fj", 10.25, 100.5)
print("TRACE_REAL_READBACK_BEGIN requested=300x150", flush=True)
raw = bytes(context.getImageData(0, 0, 300, 150).data)
assert len(raw) == 180000 and len(set(raw)) > 4
print("TRACE_REAL_READBACK_END bytes=180000", flush=True)
print("TRACE_REAL_PNG_BEGIN", flush=True)
assert canvas.toBufferSync("png").startswith(b"\x89PNG")
print("TRACE_REAL_PNG_END", flush=True)

# Use a fresh canvas so no earlier GPU-backed cached image needs CPU readback.
control = Canvas(300, 150)
control.gpu = False
print("TRACE_FRESH_CPU_CONTROL_BEGIN", flush=True)
control_context = control.getContext("2d")
control_context.fillStyle = "#2878d9"
control_context.fillRect(0, 0, 160, 100)
assert len(control_context.getImageData(0, 0, 300, 150).data) == 180000
print("TRACE_FRESH_CPU_CONTROL_END", flush=True)
