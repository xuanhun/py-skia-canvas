"""Trace original CSS/rotate/skew matrix facade into the unchanged default GPU core."""
from py_skia_canvas import Canvas, DOMMatrix, Path2D
canvas=Canvas(300,150);ctx=canvas.getContext("2d")
assert canvas.gpu and canvas.engine["renderer"]=="GPU",canvas.engine
print("TRACE_ENGINE",canvas.engine,flush=True)
matrix=DOMMatrix("translate(30.25px,20.75px) rotate(-17.125deg) scale(110%,90%) skewX(13.125deg)")
ctx.setTransform(matrix)
gradient=ctx.createLinearGradient(0,0,250,120);gradient.addColorStop(0,"#2060ff");gradient.addColorStop(1,"#ff2450")
ctx.fillStyle=gradient;ctx.fillRect(.25,.75,240.5,120.25)
path=Path2D("M10 10L180 10L90 90Z").transform(matrix.rotateFromVector(.375,-.8125))
ctx.resetTransform();ctx.strokeStyle="#ffe020";ctx.lineWidth=4.25;ctx.stroke(path)
print("TRACE_REAL_READBACK_BEGIN requested=300x150",flush=True)
raw=bytes(ctx.getImageData(0,0,300,150).data);assert len(raw)==180000 and len(set(raw))>4
print("TRACE_REAL_READBACK_END bytes=180000",flush=True)
print("TRACE_REAL_PNG_BEGIN",flush=True)
assert canvas.toBufferSync().startswith(b"\x89PNG")
print("TRACE_REAL_PNG_END",flush=True)
control=Canvas(300,150);control.gpu=False
print("TRACE_FRESH_CPU_CONTROL_BEGIN",flush=True)
c=control.getContext("2d");c.setTransform(matrix);c.fillStyle=gradient;c.fillRect(0,0,260,120)
assert len(c.getImageData(0,0,300,150).data)==180000
print("TRACE_FRESH_CPU_CONTROL_END",flush=True)
