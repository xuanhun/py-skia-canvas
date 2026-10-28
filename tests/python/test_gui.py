"""Real default-GPU WSLg GUI ownership/session tests; no display/GPU skip or fake window."""
import unittest
import test_lifecycle as legacy

class GuiLifecycleTests(unittest.TestCase):
    run_case=legacy.LifecycleTests.run_case

    def test_gui_rejects_foreign_threads_before_native(self):
        self.run_case('''
from py_skia_canvas import App,Window
q=queue.Queue()
def other():
 for fn in [lambda:Window(32,24),App.launch,lambda:setattr(App,'fps',30)]:
  try:fn()
  except RuntimeError:q.put(True)
  else:q.put(False)
t=threading.Thread(target=other);t.start();t.join();assert [q.get_nowait() for _ in range(3)]==[True]*3
assert not App.windows and not App.running
''')

    def test_native_callbacks_stay_owner_and_release_gil(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio,time
w=Window(64,48,{'visible':False,'left':200,'top':200});owner=threading.get_ident();checked=threading.Event();trigger=threading.Event()
def other():
 trigger.wait(5)
 try:w.width=80
 except RuntimeError:checked.set()
t=threading.Thread(target=other);t.start()
def draw(e):
 assert threading.get_ident()==owner
 trigger.set()
 if e.frame==8:assert checked.is_set(),'GIL held across native event loop';w.close()
w.on('draw',draw);asyncio.run(App.launch());t.join();assert checked.is_set()
''')

    def test_closed_window_releases_python_and_native_pages(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
w=Window(64,48,{'visible':False,'left':200,'top':200});ref=weakref.ref(w)
def draw(e):
 e.target.ctx.fillRect(0,0,20,20)
 if e.frame==3:e.target.close()
w.on('draw',draw);del w;gc.collect();assert ref() is not None
asyncio.run(App.launch());assert App.running and not App.windows;gc.collect();assert ref() is None
assert _native._debug_drain()==(0,0) and _native._debug_pages()==0
''')

    def test_context_survives_closed_window(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
w=Window(64,48,{'visible':False,'left':200,'top':200});x=w.ctx;canvas=w.canvas
jobs=[]
def draw(e):
 e.target.ctx.fillStyle='red';e.target.ctx.fillRect(0,0,20,20)
 if e.frame==1:jobs.append(e.target.canvas.toBuffer('raw'))
 if e.frame==3:e.target.close()
w.on('draw',draw);asyncio.run(App.launch());del w;gc.collect();assert bytes(x.getImageData(0,0,1,1).data)==bytes([255,0,0,255])
async def exported():assert (await jobs[0])[:4]==bytes([255,0,0,255])
asyncio.run(exported())
del x,canvas;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_reopen_preserves_id_and_restarts_frame_counter(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
w=Window(64,48,{'visible':False,'left':200,'top':200});ident=w.id;frames=[]
def draw(e):
 frames.append(e.frame)
 if e.frame==2:e.target.close()
w.on('draw',draw)
async def run():
 a=App.launch();await a;assert frames==[1,2] and w.closed
 w.open();b=App.launch();assert a is not b;await b
asyncio.run(run());assert frames==[1,2,1,2] and w.id==ident and w.closed
''')

    def test_cancel_waiter_preserves_node_mode_session(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio,os
os.environ.pop('WAYLAND_DISPLAY',None);os.environ.pop('WAYLAND_SOCKET',None)
App.eventLoop='node';w=Window(64,48,{'visible':False})
# Original Windows node-pump closes positioned hidden windows before first Open;
# use an unpositioned real window to exercise waiter cancellation independently.
allow_close=[False]
def draw(e):
 if allow_close[0] and e.frame>=12:e.target.close()
w.on('draw',draw)
async def run():
 session=App.launch()
 async def waiter():return await session
 task=asyncio.create_task(waiter());await asyncio.sleep(.01);task.cancel()
 try:await task
 except asyncio.CancelledError:pass
 assert not w.closed
 allow_close[0]=True
 await session;assert w.closed and not App.windows
asyncio.run(run())
''')

    def test_loop_shutdown_closes_actual_windows(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
App.eventLoop='node';w=Window(64,48,{'visible':False,'left':200,'top':200})
async def run():App.launch();await asyncio.sleep(.05)
asyncio.run(run());assert w.closed and not App.windows and App._session is None
''')

    def test_multiple_waiters_and_repeat_await(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
App.eventLoop='node';w=Window(64,48,{'visible':False,'left':200,'top':200})
def draw(e):
 if e.frame==3:e.target.close()
w.on('draw',draw)
async def run():
 session=App.launch()
 async def waiter():return await session
 assert await asyncio.gather(waiter(),waiter(),waiter())==[None,None,None]
 assert await session is None
asyncio.run(run())
''')

    def test_draw_handler_error_is_reported_then_next_frame_runs(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio,io,contextlib
w=Window(64,48,{'visible':False,'left':200,'top':200});log=io.StringIO()
def draw(e):
 if e.frame==1:raise ValueError('fixture handler error')
 if e.frame==3:e.target.close()
w.on('draw',draw)
with contextlib.redirect_stderr(log):asyncio.run(App.launch())
assert w.closed and 'fixture handler error' in log.getvalue()
''')

    def test_direct_gui_access_rejects_foreign_thread(self):
        self.run_case('''
from py_skia_canvas import App,Window
w=Window(64,48,{'visible':False,'left':200,'top':200});q=queue.Queue()
def other():
 try:_native._gui_close(w.id)
 except RuntimeError:q.put(True)
 else:q.put(False)
t=threading.Thread(target=other);t.start();t.join();assert q.get_nowait()
w.close();App.quit()
import asyncio
asyncio.run(App.launch())
''')

    def test_nonpositive_viewport_rejected_before_window_open(self):
        self.run_case('''
from py_skia_canvas import App,Window
for args in [(0,16),(16,0),(-1,16),({'width':0,'height':0},)]:
 try:Window(*args)
 except NotImplementedError:pass
 else:raise AssertionError('unsafe native viewport accepted')
assert not App.windows
''')

    def test_reentrant_quit_rejected_without_native_refcell_panic(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
w=Window(64,48,{'visible':False,'left':200,'top':200});seen=[]
def draw(e):
 try:App.quit()
 except RuntimeError:seen.append(True)
 e.target.close()
w.on('draw',draw);asyncio.run(App.launch());assert seen and w.closed
''')

    def test_window_keeps_replaced_canvas_ownership_correct(self):
        self.run_case('''
from py_skia_canvas import App,Window
import asyncio
w=Window(64,48,{'visible':False,'left':200,'top':200});old=weakref.ref(w.canvas)
c=Canvas(32,24);w.canvas=c;gc.collect();assert old() is None
def draw(e):
 e.target.ctx.fillStyle='red';e.target.ctx.fillRect(0,0,32,24)
 if e.frame==3:e.target.close()
w.on('draw',draw);asyncio.run(App.launch());assert len(c.toBufferSync('raw'))==32*24*4
del c,w;gc.collect();assert _native._debug_drain()==(0,0)
''')

if __name__=='__main__':unittest.main()
