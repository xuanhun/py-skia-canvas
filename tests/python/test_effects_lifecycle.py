"""Real installed-wheel effect State/cache/marker ownership and GPU cleanup assertions."""
import unittest
import test_lifecycle as existing

class EffectsLifecycleTests(unittest.TestCase):
    def run_case(self,body):
        """Run isolated installed-wheel assertion; original units/owner and subprocess errors.
        Uses existing harness, no copied renderer, no skips, no inherited test duplication.
        """
        existing.LifecycleTests.run_case(self,'''from py_skia_canvas import Image,ImageData
from pathlib import Path
import json
assets=Path(os.environ['PY_SKIA_CANVAS_TEST_ASSETS'])
'''+body)

    def test_effects_survive_canvas_wrapper_gc(self):
        self.run_case('''
c,x=rendered();x.filter="blur(1px) contrast(1.2)";x.shadowColor="#d02880";x.shadowBlur=3.5;x.shadowOffsetX=4.25;x.globalCompositeOperation="multiply"
x.fillRect(1,2,30,20);c.toBufferSync();snapshot=(x.filter,x.shadowColor,x.shadowBlur,x.globalCompositeOperation)
ref=weakref.ref(c);del c;gc.collect();assert ref() is None and x.canvas is undefined
x.fillRect(3,4,25,18);assert x._native.encode("png").startswith(b"\\x89PNG")
assert (x.filter,x.shadowColor,x.shadowBlur,x.globalCompositeOperation)==snapshot
del x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_effects_foreign_get_set_rejected(self):
        self.run_case('''
c,x=rendered();x.filter="blur(1px)";before=c.toBufferSync();q=queue.Queue()
names=["filter","shadowColor","shadowBlur","shadowOffsetX","shadowOffsetY","globalCompositeOperation","globalAlpha","lineDashFit"]
def foreign():
    errors=[]
    for name in names:
        for action in (lambda n=name:getattr(x,n),lambda n=name:setattr(x,n,None)):
            try:action()
            except RuntimeError as e:errors.append("creating thread" in str(e))
            else:errors.append(False)
    q.put(errors)
t=threading.Thread(target=foreign);t.start();t.join();assert q.get()==[True]*16
assert x.filter=="blur(1px)" and c.toBufferSync()==before
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_cached_effect_state_owner_exit_live_handles(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered();x.filter="drop-shadow(2px 3px 2px red) blur(1px)";x.shadowColor="blue";x.shadowBlur=2;x.globalCompositeOperation="source-in"
    x.save();x.fillRect(1,1,40,25);c.toBufferSync();q.put((c,x))
t=threading.Thread(target=owner);t.start();t.join();c,x=q.get()
assert _native._debug_drain()==(0,0)
try:x.filter
except RuntimeError:pass
else:raise AssertionError("Ended effect owner accepted")
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_filter_save_restore_cached_scale_and_rotation(self):
        self.run_case('''
c,x=rendered();x.filter="blur(1px) brightness(.7)";x.shadowColor="red";x.shadowBlur=3
x.fillRect(2,2,25,15);c.toBufferSync();x.save();x.filter="sepia(1)";x.shadowColor="blue";x.scale(1.25,.75);x.fillRect(10,10,30,20);c.toBufferSync();x.restore()
assert x.filter=="blur(1px) brightness(.7)" and x.shadowColor=="#ff0000" and x.shadowBlur==3
x.rotate(.25);x.fillRect(1,1,30,20);assert c.toBufferSync().startswith(b"\\x89PNG")
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_invalid_effects_leave_render_and_state(self):
        self.run_case('''
c,x=rendered();x.filter="sepia(.5)";x.shadowColor="red";x.shadowBlur=3;x.globalAlpha=.75;x.globalCompositeOperation="multiply";before=c.toBufferSync()
x.filter="not-a-filter";x.shadowColor="not-a-color";x.shadowBlur=-1;x.shadowOffsetX={};x.globalAlpha=float("nan");x.globalCompositeOperation="bogus"
assert x.filter=="sepia(.5)" and x.shadowBlur==3 and x.shadowColor=="#ff0000" and x.globalAlpha==.75 and x.globalCompositeOperation=="multiply"
for action in (lambda:setattr(x,"filter",None),lambda:setattr(x,"filter",True),lambda:setattr(x,"globalCompositeOperation",False)):
    try:action()
    except (TypeError,RuntimeError):pass
    else:raise AssertionError("Invalid effect accepted")
assert c.toBufferSync()==before
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_filter_spec_transport_owned_and_errors_before_borrow(self):
        self.run_case('''
c,x=rendered();desc={"canonical":"blur(1px) brightness(.7)","filters":{"blur":1,"brightness":.7},"order":["blur","brightness"]}
x._native.effects_filter(json.dumps(desc));x.fillRect(1,1,30,20);before=c.toBufferSync();desc["filters"]["blur"]=99
assert x.filter=="blur(1px) brightness(.7)" and c.toBufferSync()==before
for bad in ({"canonical":"bad","filters":{},"order":["missing"]},{"canonical":"bad","filters":{"drop-shadow":[1,"red"]},"order":["drop-shadow"]}):
    try:x._native.effects_filter(json.dumps(bad))
    except TypeError:pass
    else:raise AssertionError("Malformed private descriptor accepted")
assert x.filter=="blur(1px) brightness(.7)" and c.toBufferSync()==before
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_image_and_path_drop_after_recorded_effects(self):
        self.run_case('''
c,x=rendered();image=Image((assets/"rgba-grid.png").read_bytes());path=Path2D("M1 1L45 4L20 28Z")
x.filter="hue-rotate(30deg) blur(.5px)";x.shadowColor="red";x.shadowBlur=3;x.shadowOffsetX=4
x.drawImage(image,0,0,40,30);x.fill(path);before=c.toBufferSync()
del image,path;gc.collect();assert c.toBufferSync()==before
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_put_image_data_ignores_effects_and_preserves_state(self):
        self.run_case('''
data=ImageData((assets/"rgba-grid.raw").read_bytes(),8,8);c0=Canvas(8,8);x0=c0.getContext("2d");x0.putImageData(data,0,0);expected=bytes(x0.getImageData(0,0,8,8).data)
c,x=rendered();x.filter="invert(1)";x.shadowColor="red";x.shadowBlur=5;x.shadowOffsetX=12;x.globalAlpha=.3;x.globalCompositeOperation="copy";x.translate(30,20)
x.beginPath();x.rect(50,50,1,1);x.clip();x.putImageData(data,0,0)
assert bytes(x.getImageData(0,0,8,8).data)==expected and x.filter=="invert(1)" and x.globalCompositeOperation=="copy" and x.getTransform().e==30
del c,x,c0,x0;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_marker_fit_snapshot_survives_source_gc(self):
        self.run_case('''
c,x=rendered();p=Path2D("M-2 -2L4 0L-2 2Z");x.lineDashMarker=p;x.lineDashFit="follow";x.setLineDash([10,5]);x.filter="blur(.5px)";x.shadowColor="red";x.shadowBlur=2
del p;gc.collect();x.save();x.lineDashFit="move";x.restore();assert x.lineDashFit=="follow"
marker=x.lineDashMarker;x.beginPath();x.moveTo(2,5);x.bezierCurveTo(20,0,40,30,60,20);x.stroke();c.toBufferSync()
del c,x;gc.collect();assert marker.bounds["width"]==6
del marker;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_effect_reset_resize_defaults_and_snapshot_values(self):
        self.run_case('''
c,x=rendered();x.filter="blur(1px)";x.shadowColor="red";x.shadowBlur=3;x.globalCompositeOperation="copy";x.globalAlpha=.5;x.lineDashFit="move"
snapshot=(x.filter,x.shadowColor,x.globalCompositeOperation);c.width=80
assert x.filter=="none" and x.shadowBlur==0 and x.shadowOffsetX==0 and x.globalCompositeOperation=="source-over" and x.globalAlpha==1 and x.lineDashFit=="turn"
x.filter="invert(1)";x.reset();assert x.filter=="none"
del c,x;gc.collect();assert _native._debug_drain()==(0,0) and snapshot==("blur(1px)","#ff0000","copy")
''')

    def test_pattern_texture_with_filter_owner_cleanup(self):
        self.run_case('''
from py_skia_canvas import CanvasPattern,CanvasTexture
c,x=rendered();image=Image((assets/"checker.svg").read_bytes());pattern=x.createPattern(image,"repeat");texture=x.createTexture(6,{"color":"#d02880"})
x.filter="blur(.5px) saturate(1.2)";x.shadowColor="blue";x.shadowBlur=2;x.fillStyle=pattern;x.strokeStyle=texture;x.save();x.fillRect(0,0,64,32);x.strokeRect(2,2,50,20);c.toBufferSync()
del c,x,image,pattern,texture;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_interpreter_exit_cached_filters_and_intermediate_blend(self):
        self.run_case('''
c,x=rendered();x.filter="blur(1px) drop-shadow(2px 3px 1px red) brightness(.7)";x.shadowColor="blue";x.shadowBlur=2;x.globalCompositeOperation="source-in";x.save();x.fillRect(0,0,50,30);c.toBufferSync()
assert _native._debug_drain()==(1,1)
''')

if __name__=='__main__':unittest.main()
