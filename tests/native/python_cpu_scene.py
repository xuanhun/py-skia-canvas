"""Original CPU Raster call-path witness; run with unavailable Vulkan drivers."""
from py_skia_canvas import Canvas,ImageData
import asyncio,json
c=Canvas(160,96);x=c.getContext('2d');assert not c.gpu and c.engine['renderer']=='CPU';x._native.audit_surface_capture(True)
g=x.createLinearGradient(0,0,160,0);g.addColorStop(0,'red');g.addColorStop(1,'blue');x.fillStyle=g;x.fillRect(0,0,160,96);x.filter='blur(1px)';x.font='22px sans-serif';x.fillText('CPU Raster',3,30);x.putImageData(ImageData(bytes([0,255,0,255]*16),4,4),2,40)
print('CPU_NATIVE_RENDER_BEGIN',flush=True)
for fmt in ('raw','png','jpg','webp','pdf','svg'):assert len(c.toBufferSync(fmt))>10
async def run():assert (await c.toBuffer('png')).startswith(b'\x89PNG')
asyncio.run(run());assert json.loads(x._native.audit_surface_capture(False))['surfaces']==0
print('CPU_NATIVE_RENDER_END',flush=True)
