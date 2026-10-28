"""Actual Winit Vulkan window presentation, main-thread callbacks, native swapchain trace."""
import asyncio
from py_skia_canvas import App,Window,Canvas
w=Window(160,100,{'title':'py-skia-canvas G9 native trace','left':200,'top':200,'borderless':True})
assert w.canvas.gpu and w.canvas.engine['renderer']=='GPU'
print('TRACE_GUI_PRESENT_BEGIN',flush=True)
def draw(e):
    """Original Canvas operations through original window renderer; source fixture units px."""
    x=w.ctx;x.fillStyle='white';x.fillRect(0,0,160,100);x.fillStyle='#d02880';x.fillRect(5.25,10.5,60.5,30.25);x.font='13px sans-serif';x.fillStyle='#102030';x.fillText('Canvas GUI',3,55)
    if e.frame==5:w.close()
w.on('draw',draw);asyncio.run(App.launch());assert w.closed and not App.windows
print('TRACE_GUI_PRESENT_END',flush=True)
print('TRACE_GUI_CPU_CONTROL_BEGIN',flush=True)
c=Canvas(160,100);c.gpu=False;x=c.getContext('2d');x.fillRect(5,10,60,30);assert c.toBufferSync().startswith(b'\x89PNG')
print('TRACE_GUI_CPU_CONTROL_END',flush=True)
