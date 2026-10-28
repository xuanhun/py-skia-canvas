"""Real installed-wheel image/data/shader ownership and owner-loop I/O checks."""
import unittest
import test_lifecycle as existing

class ImageryLifecycleTests(unittest.TestCase):
    def run_case(self,body):
        """Run isolated installed-wheel child, assert exit/errors; no units/native transfer.
        Reuses existing subprocess harness, not inherited tests or a rendering mock.
        """
        existing.LifecycleTests.run_case(self,'''from py_skia_canvas import Image,ImageData,CanvasPattern,CanvasTexture,loadImage,loadImageData
from pathlib import Path
import asyncio,base64
assets=Path(os.environ['PY_SKIA_CANVAS_TEST_ASSETS'])
'''+body)

    def test_encoded_buffer_copy_and_image_pixels_owned(self):
        self.run_case('''
source=bytearray((assets/"rgba-grid.png").read_bytes()); image=Image(source)
source[:]=b"x"*len(source); assert image.complete and image.width==8
data=ImageData(image); expected=bytes(data.data); assert len(expected)==256
c,x=rendered();x.drawImage(image,0,0,48,32); png=c.toBufferSync()
data.data.set([255,0,0,255]); assert bytes(ImageData(image).data)==expected
assert c.toBufferSync()==png
del c,x,image;gc.collect();assert _native._debug_drain()==(0,0)
assert bytes(data.data)!=expected
''')

    def test_image_foreign_access_and_gc_deferred(self):
        self.run_case('''
image=Image((assets/"rgba-grid.png").read_bytes()); q=queue.Queue()
def foreign():
    actions=(lambda:image.width,lambda:image.complete,lambda:ImageData(image),lambda:setattr(image,"src",b"x"))
    errors=[]
    for action in actions:
        try:action()
        except RuntimeError as e:errors.append("creating thread" in str(e))
        else:errors.append(False)
    q.put(errors)
t=threading.Thread(target=foreign);t.start();t.join();assert q.get()==[True]*4
holder=[image];del image
def release():holder.clear();gc.collect()
t=threading.Thread(target=release);t.start();t.join()
assert _native._debug_drain()==(0,0)
''')

    def test_image_owner_exit_live_foreign_handle(self):
        self.run_case('''
q=queue.Queue()
def owner():q.put(Image((assets/"checker.svg").read_bytes()))
t=threading.Thread(target=owner);t.start();t.join();image=q.get()
assert _native._debug_drain()==(0,0)
try:image.width
except RuntimeError:pass
else:raise AssertionError("Ended image owner accepted")
del image;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_image_data_mutable_after_canvas_gc_and_thread_exit(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered();q.put(x.getImageData(0,0,64,32))
t=threading.Thread(target=owner);t.start();t.join();data=q.get()
assert _native._debug_drain()==(0,0)
copy=ImageData(data);assert copy.data is data.data
data.data.set([-2,1.5,2.5,300]);assert list(copy.data[:4])==[0,2,2,255]
c,x=rendered();x.putImageData(data,0,0);assert c.toBufferSync().startswith(b"\\x89PNG")
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_data_fixed_size_and_readonly_metadata(self):
        self.run_case('''
d=ImageData(2,2);before=bytes(d.data)
for op in (lambda:setattr(d,"data",None),lambda:setattr(d,"width",9),lambda:d.data.append(0),lambda:d.data.__setitem__(slice(0,1),[1,2])):
    try:op()
    except (TypeError,ValueError):pass
    else:raise AssertionError("Invalid data mutation accepted")
assert bytes(d.data)==before and d.width==2
assert _native._debug_drain()==(0,0)
''')

    def test_canvas_source_self_draw_and_source_gc(self):
        self.run_case('''
c,x=rendered();source,s=rendered();x.drawImage(source,0,0,32,16);x.drawCanvas(source,32,0,32,16)
before=bytes(x.getImageData(0,0,64,32).data);ref=weakref.ref(source)
del source,s;gc.collect();assert ref() is None
x.drawImage(c,0,0,32,16,32,16,32,16);x.drawCanvas(c,0,0,32,16,0,16,32,16)
assert len(before)==8192 and c.toBufferSync().startswith(b"\\x89PNG")
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_put_errors_and_source_mutation_preserve_state(self):
        self.run_case('''
c,x=rendered();d=ImageData((assets/"rgba-grid.raw").read_bytes(),8,8)
x.translate(2.25,3.5);before=x.getTransform().toJSON();png=c.toBufferSync()
try:x.putImageData(d,0,0,1)
except TypeError:pass
else:raise AssertionError("Incomplete dirty args accepted")
assert c.toBufferSync()==png and x.getTransform().toJSON()==before
x.putImageData(d,0,0);d.data.set([255,0,0,255]);assert x.getTransform().toJSON()==before
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_pattern_shared_state_after_source_and_canvas_gc(self):
        self.run_case('''
c,x=rendered();image=Image((assets/"checker.svg").read_bytes());p=x.createPattern(image,"repeat")
x.fillStyle=p;x.save();x.fillRect(0,0,64,32);before=c.toBufferSync()
del image;gc.collect();p.setTransform(2,0,0,2,4,3);x.restore()
assert x.fillStyle is p;x.clearRect(0,0,64,32);x.fillRect(0,0,64,32);assert c.toBufferSync()!=before
ref=weakref.ref(c);del c;gc.collect();assert ref() is None
x.fillRect(0,0,64,32)
del x,p;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_pattern_canvas_snapshot_and_source_gc(self):
        self.run_case('''
c,x=rendered();src,s=rendered();p=x.createPattern(src,"repeat")
x.clearRect(0,0,64,32);x.fillStyle=p;x.fillRect(0,0,64,32);before=c.toBufferSync()
s.fillStyle="red";s.fillRect(0,0,64,32);del src,s;gc.collect()
x.clearRect(0,0,64,32);x.fillRect(0,0,64,32);assert c.toBufferSync()==before
del c,x,p;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_shader_foreign_assignment_rejected_before_state_change(self):
        self.run_case('''
q=queue.Queue();release=threading.Event()
def owner():
    c,x=rendered();image=Image((assets/"rgba-grid.png").read_bytes())
    q.put((x.createPattern(image,"repeat"),x.createTexture(8)));release.wait()
t=threading.Thread(target=owner);t.start();p,texture=q.get();c,x=rendered();before=x.fillStyle;png=c.toBufferSync()
try:
    for shader in (p,texture):
        try:x.fillStyle=shader
        except RuntimeError:pass
        else:raise AssertionError("Foreign shader accepted")
        assert x.fillStyle==before and c.toBufferSync()==png
finally:release.set();t.join()
del p,texture,c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_texture_holds_path_after_path_gc(self):
        self.run_case('''
c,x=rendered();path=Path2D("M0 0L6 2L2 6Z");texture=x.createTexture(12,{"path":path,"color":"#e02880"})
del path;gc.collect();x.fillStyle=texture;x.save();x.fillStyle="red";x.restore()
# Original restore resets native Dye but does not restore the JS shader reference cache.
assert x.fillStyle is None;x.fillRect(0,0,64,32);assert c.toBufferSync().startswith(b"\\x89PNG")
del texture,c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_shader_owner_exit_live_handles(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered();image=Image((assets/"checker.svg").read_bytes());p=x.createPattern(image,"repeat");texture=x.createTexture([12,8]);x.fillStyle=p;x.strokeStyle=texture;x.save();x.fillRect(0,0,64,32);c.toBufferSync();q.put((c,x,image,p,texture))
t=threading.Thread(target=owner);t.start();t.join();values=q.get()
assert _native._debug_drain()==(0,0)
del values;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_async_file_load_decode_and_raw_data(self):
        self.run_case('''
async def check():
    image=await loadImage(assets/"rgba-grid.png");assert image.complete and image.width==8
    assert await image.decode() is image
    data=await loadImageData(assets/"rgba-grid.raw",8,8);assert len(data.data)==256
    c,x=rendered();x.drawImage(image,0,0,64,32);x.putImageData(data,0,0);assert c.toBufferSync().startswith(b"\\x89PNG")
asyncio.run(check());gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_src_events_latest_request_and_waiter_cancel(self):
        self.run_case('''
async def check():
    image=Image();events=[];image.onload=lambda i:events.append((i.width,i.height))
    image.src=assets/"checker.svg";image.src=assets/"rgba-grid.png"
    assert await image.decode() is image and events==[(8,8)]
    image.src=assets/"checker.svg";waiter=asyncio.create_task(image.decode());await asyncio.sleep(0)
    waiter.cancel()
    try:await waiter
    except asyncio.CancelledError:pass
    assert await image.decode() is image and image.width==32
asyncio.run(check());gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_immediate_events_errors_and_duplicate_once(self):
        self.run_case('''
image=Image();events=[]
def cb(value):events.append(value.width)
image.once("load",cb);image.on("load",cb);image.src=(assets/"rgba-grid.png").read_bytes()
image.src=(assets/"checker.svg").read_bytes();assert events==[8,8,32]
errors=[];image.onerror=lambda e:errors.append(str(e));image.src=b"invalid"
assert image.complete and image.width==0 and errors==["Could not decode image data"]
async def check():
    try:await image.decode()
    except RuntimeError as e:assert str(e)==errors[0]
    else:raise AssertionError("Broken decode accepted")
asyncio.run(check());del image;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_async_errors_owner_and_interpreter_exit(self):
        self.run_case('''
async def check():
    for src in (b"broken",assets/"missing-not-an-image.png"):
        try:await loadImage(src)
        except RuntimeError:pass
        else:raise AssertionError("Invalid load accepted")
asyncio.run(check());gc.collect();assert _native._debug_drain()==(0,0)
image=Image((assets/"checker.svg").read_bytes());c,x=rendered();x.fillStyle=x.createPattern(image,"repeat");x.fillRect(0,0,64,32);c.toBufferSync()
''')

if __name__=='__main__':unittest.main()
