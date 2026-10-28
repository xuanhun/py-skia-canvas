"""Real installed-wheel ownership tests. Missing GPU/extension is a failure, never a skip."""
import os
import subprocess
import sys
import textwrap
import unittest


class LifecycleTests(unittest.TestCase):
    def run_case(self, body):
        """Run isolated owner/GC exercise; no PATH tools, output preserved by unittest on failure."""
        prelude = '''
from py_skia_canvas import Canvas, Path2D, CanvasGradient, DOMMatrix, DOMPoint, DOMRect, FontLibrary, undefined
from py_skia_canvas import _native
import gc, queue, threading, weakref, os
from pathlib import Path
TEST_FONT = str(Path(os.environ['WINDIR'])/'Fonts/arial.ttf') if os.name=='nt' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
TEST_MONO = str(Path(os.environ['WINDIR'])/'Fonts/consola.ttf') if os.name=='nt' else '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
TEST_MONO_FAMILY = 'Consolas' if os.name=='nt' else 'DejaVu Sans Mono'
thread_failures = []
threading.excepthook = lambda args: thread_failures.append(repr(args.exc_value))
def rendered():
    c = Canvas(64, 32)
    x = c.getContext("2d")
    assert c.gpu and c.engine["renderer"] == "GPU", c.engine
    x.fillStyle = "#2878d9"
    x.fillRect(0.25, 0.5, 32.5, 20.25)
    assert len(x.getImageData(0, 0, 64, 32).data) == 64*32*4
    assert c.toBufferSync().startswith(b"\\x89PNG")
    return c, x
assert _native._debug_drain() == (0, 0)
'''
        from pathlib import Path
        env = dict(os.environ, PATH="", PYTHONFAULTHANDLER="1", PY_SKIA_CANVAS_TEST_ASSETS=str(Path(__file__).resolve().parents[1]/'assets'))
        result = subprocess.run([sys.executable, "-I", "-c", textwrap.dedent(prelude) + textwrap.dedent(body) + "\nassert not thread_failures, thread_failures\n"],
                                capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_decoration_survives_canvas_gc_and_owns_snapshot(self):
        self.run_case('''
c,x=rendered();x.font='24px serif';x.textDecoration='wavy underline 2px #d02060'
style=x.textDecoration;width=x.measureText('AV fj ffi').width
x.fillText('AV fj ffi',1,25);assert c.toBufferSync().startswith(b'\\x89PNG')
del c;gc.collect();assert x.canvas is undefined
assert x.textDecoration==style and x.measureText('AV fj ffi').width==width
x.textDecoration='double overline 1px green';x.fillText('AV ffi',1,25)
del x;gc.collect();assert style=='wavy underline 2px #d02060'
assert _native._debug_drain()==(0,0)
''')

    def test_decoration_foreign_access_rejected(self):
        self.run_case('''
c,x=rendered();x.textDecoration='underline red';before=x.textDecoration;errors=[]
def worker():
    for operation in (lambda:x.textDecoration,lambda:setattr(x,'textDecoration','wavy underline 2px blue'),lambda:setattr(x,'textDecoration','underline 2em red'),lambda:setattr(x,'textDecoration',None)):
        try:operation()
        except RuntimeError:errors.append(True)
        else:raise AssertionError('foreign decoration access accepted')
t=threading.Thread(target=worker);t.start();t.join();assert len(errors)==4
assert x.textDecoration==before and c.toBufferSync().startswith(b'\\x89PNG')
''')

    def test_decoration_errors_restore_resize_and_reset(self):
        self.run_case('''
c,x=rendered();x.textDecoration='underline 2px red';style=x.textDecoration
x.textDecoration='overline';assert x.textDecoration==style
try:x.textDecoration='underline 2em red'
except TypeError as e:assert str(e)=='Exptected a numerical value for "px"'
else:raise AssertionError('original invalid thickness error suppressed')
assert x.textDecoration==style
x.save();x.textDecoration='double overline 1px blue';x.restore();assert x.textDecoration==style
x.textDecoration='underline 2em from-font red';assert x.textDecoration=='underline 2em from-font red'
x.textDecoration=None;assert x.textDecoration=='none'
x.textDecoration='wavy line-through 2px green';c.width=64;assert x.textDecoration=='none'
''')

    def test_decoration_owner_exit_with_live_handles(self):
        self.run_case('''
q=queue.Queue()
def worker():
    c,x=rendered();x.font='24px serif';x.textDecoration='double underline 1px red'
    x.fillText('AV ffi',1,25);assert c.toBufferSync().startswith(b'\\x89PNG')
    q.put((c,x,x.textDecoration))
t=threading.Thread(target=worker);t.start();t.join();c,x,style=q.get();assert style=='double underline 1px red'
try:_=x.textDecoration
except RuntimeError:pass
else:raise AssertionError('dead owner decoration access accepted')
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_text_state_snapshots_survive_canvas_gc(self):
        self.run_case('''
c,x=rendered();x.font='24px serif';x.textAlign='center';x.textBaseline='middle';x.direction='rtl'
x.letterSpacing='1.25px';x.wordSpacing='2.5px';x.fontStretch='condensed';x.fontVariant='small-caps';x.fontHinting=True;x.textWrap=True
fields=('textAlign','textBaseline','direction','letterSpacing','wordSpacing','fontStretch','fontVariant','fontHinting','textWrap')
snapshot={k:getattr(x,k) for k in fields};before=x.measureText('AV ffi words',120.5).width
x.fillText('AV ffi',30,16,60);assert c.toBufferSync().startswith(b'\\x89PNG')
del c;gc.collect();assert x.canvas is undefined
assert snapshot=={k:getattr(x,k) for k in fields}
assert before==x.measureText('AV ffi words',120.5).width
x.letterSpacing='0.5px';x.textWrap=False;x.fillText('AV ffi',30,16)
del x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_text_state_foreign_access_is_rejected(self):
        self.run_case('''
c,x=rendered();fields={'textAlign':'right','textBaseline':'top','direction':'rtl','letterSpacing':'1px','wordSpacing':'2px','fontStretch':'condensed','fontVariant':'small-caps','fontHinting':True,'textWrap':True}
snapshot={k:getattr(x,k) for k in fields};errors=[]
def worker():
    for key,value in fields.items():
        for operation in (lambda:getattr(x,key),lambda:setattr(x,key,value)):
            try:operation()
            except RuntimeError:errors.append(True)
            else:raise AssertionError('foreign text property accepted')
t=threading.Thread(target=worker);t.start();t.join();assert len(errors)==18
assert snapshot=={k:getattr(x,k) for k in fields}
assert c.toBufferSync().startswith(b'\\x89PNG')
''')

    def test_text_state_restore_resize_and_original_errors(self):
        self.run_case('''
c,x=rendered();fields=('textAlign','textBaseline','direction','letterSpacing','wordSpacing','fontStretch','fontVariant','fontHinting','textWrap')
initial={k:getattr(x,k) for k in fields};x.save()
x.textAlign='right';x.textBaseline='top';x.direction='rtl';x.letterSpacing='1px';x.wordSpacing='2px';x.fontStretch='condensed';x.fontVariant='small-caps';x.fontHinting=True;x.textWrap=True
changed={k:getattr(x,k) for k in fields}
for key,value in [('fontVariant','normal'),('letterSpacing','2em'),('wordSpacing','3rem')]:
    try:setattr(x,key,value)
    except TypeError:pass
    else:raise AssertionError('original error suppressed')
assert changed=={k:getattr(x,k) for k in fields}
x.restore();assert initial=={k:getattr(x,k) for k in fields}
x.textWrap=True;x.letterSpacing='2px';c.width=64
assert initial=={k:getattr(x,k) for k in fields}
''')

    def test_text_state_owner_exit_with_live_handles(self):
        self.run_case('''
q=queue.Queue()
def worker():
    c,x=rendered();x.font='24px serif';x.textAlign='center';x.textBaseline='middle';x.direction='rtl';x.letterSpacing='1px';x.fontVariant='small-caps';x.fontHinting=True;x.textWrap=True
    x.fillText('AV ffi words',30,16,60);assert c.toBufferSync().startswith(b'\\x89PNG')
    q.put((c,x,x.measureText('AV ffi words',60).width))
t=threading.Thread(target=worker);t.start();t.join();c,x,width=q.get();assert width>0
try:_=x.textWrap
except RuntimeError:pass
else:raise AssertionError('dead owner text property accepted')
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_selected_font_metadata_and_context_survive_canvas_gc(self):
        self.run_case('''
FontLibrary.reset();FontLibrary.use('Selected lifecycle',TEST_MONO)
c,x=rendered();x.font='28px "Selected lifecycle"'
canonical=x.font;metric=x.measureText('AV fj ffi').width
assert metric>40
reference=Canvas(64,32).getContext('2d');reference.font='28px "'+TEST_MONO_FAMILY+'"'
assert metric==reference.measureText('AV fj ffi').width
x.fillText('AV',1,25);assert c.toBufferSync().startswith(b'\\x89PNG')
del c;gc.collect();assert x.canvas is undefined
assert x.font==canonical and x.measureText('AV fj ffi').width==metric
x.fillText('AV',1,25)  # Parentless context retains drawing/state; public readback requires parent.
FontLibrary.reset();assert x.font==canonical
x.font='24px serif';x.fillText('reset',1,25)
del x,reference;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_font_properties_reject_foreign_thread_and_recover(self):
        self.run_case('''
c,x=rendered();x.font='bold 28px serif';canonical=x.font;errors=[]
def worker():
    for operation in (lambda:x.font,lambda:setattr(x,'font','22px monospace'),lambda:setattr(x,'font',None)):
        try:operation()
        except RuntimeError:errors.append(True)
        else:raise AssertionError('foreign font access accepted')
t=threading.Thread(target=worker);t.start();t.join();assert len(errors)==3
assert x.font==canonical;x.font='italic 23px serif'
assert c.toBufferSync().startswith(b'\\x89PNG')
''')

    def test_font_save_restore_resize_and_invalid_retention(self):
        self.run_case('''
c,x=rendered();default=x.font
x.font='small-caps bold 26px serif';selected=x.font
x.save();x.font='31px monospace';x.restore();assert x.font==selected
x.font='invalid';assert x.font==selected
c.width=64;assert x.font==default
x.font='27px monospace';x.fillText('AV ffi',1,25)
assert c.toBufferSync().startswith(b'\\x89PNG')
''')

    def test_selected_font_owner_exit_leaves_safe_foreign_handles(self):
        self.run_case('''
q=queue.Queue()
def worker():
    FontLibrary.use('Selected exit',TEST_MONO)
    c,x=rendered();x.font='29px "Selected exit"';x.fillText('AV ffi',1,25)
    assert c.toBufferSync().startswith(b'\\x89PNG')
    q.put((c,x,x.font))
t=threading.Thread(target=worker);t.start();t.join()
c,x,font=q.get();assert 'Selected exit' in font
try:_=x.font
except RuntimeError:pass
else:raise AssertionError('dead owner font access accepted')
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
assert not FontLibrary.has('Selected exit')
''')

    def test_font_library_is_calling_thread_local(self):
        self.run_case('''
path=TEST_FONT
FontLibrary.reset();FontLibrary.use('Main TLS',path)
ready=threading.Event();release=threading.Event()
def worker():
    assert not FontLibrary.has('Main TLS')
    FontLibrary.use('Worker TLS',path)
    q.put(FontLibrary.family('Worker TLS'))
    ready.set();assert release.wait(10)
    FontLibrary.reset();assert not FontLibrary.has('Worker TLS')
q=queue.Queue();t=threading.Thread(target=worker);t.start()
assert ready.wait(10)
assert FontLibrary.has('Main TLS') and not FontLibrary.has('Worker TLS')
snapshot=q.get();assert snapshot['family']=='Worker TLS'
release.set();t.join();assert FontLibrary.has('Main TLS')
assert snapshot['weights']==[400]
FontLibrary.reset()
''')

    def test_font_partial_failure_and_reset_with_recorded_text(self):
        self.run_case('''
path=TEST_FONT
FontLibrary.reset();c,x=rendered()
# Opaque replay background makes repeated snapshots stable under original rendering.
x.fillStyle='white';x.fillRect(0,0,64,32)
x.fillStyle='#2878d9';x.fillText('AV fj',1,20)
before=bytes(x.getImageData(0,0,64,32).data)
try: FontLibrary.use('Partial lifecycle',[path,path+'.missing'])
except _native.Error: pass
else: raise AssertionError('file failure was suppressed')
assert FontLibrary.has('Partial lifecycle')
assert FontLibrary.reset() is undefined
assert not FontLibrary.has('Partial lifecycle')
assert before==bytes(x.getImageData(0,0,64,32).data)
assert c.toBufferSync().startswith(b'\\x89PNG')
del c,x;gc.collect();assert _native._debug_drain()==(0,0)
''')

    def test_font_snapshots_and_canvas_gc_are_independent(self):
        self.run_case('''
FontLibrary.reset()
metadata=FontLibrary.use('Snapshot lifecycle',TEST_FONT)
families=FontLibrary.families;details=FontLibrary.family('Snapshot lifecycle')
c,x=rendered();del c,x;gc.collect();assert _native._debug_drain()==(0,0)
metadata[0]['family']='changed';families.clear();details['weights'].clear()
assert FontLibrary.has('Snapshot lifecycle')
assert FontLibrary.family('Snapshot lifecycle')['weights']==[400]
FontLibrary.reset();assert FontLibrary.family('Snapshot lifecycle') is undefined
''')

    def test_font_owner_thread_exit_and_interpreter_exit(self):
        self.run_case('''
path=TEST_FONT
def worker():
    FontLibrary.use('Thread exit lifecycle',path)
    c,x=rendered();x.fillText('AV',1,20)
    assert c.toBufferSync().startswith(b'\\x89PNG')
t=threading.Thread(target=worker);t.start();t.join()
assert not FontLibrary.has('Thread exit lifecycle')
FontLibrary.use('Interpreter exit lifecycle',path)
live_canvas,live_context=rendered()
live_context.fillText('exit',1,20)
# Registered fonts and GPU resources intentionally remain live at interpreter exit.
''')

    def test_owner_gc_releases_context_and_canvas(self):
        self.run_case('''
for _ in range(8):
    c, x = rendered()
    assert _native._debug_drain() == (1, 1)
    ref = weakref.ref(c)
    del c
    gc.collect()
    assert ref() is None and x.canvas is undefined
    # Original context remains usable after weak parent disappears.
    x.fillText("AV fj", 1, 20)
    del x
    gc.collect()
    assert _native._debug_drain() == (0, 0)
''')

    def test_foreign_access_is_rejected_and_foreign_gc_is_deferred(self):
        self.run_case('''
q = queue.Queue()
c, x = rendered()
q.put((c, x))
del c, x
errors = []
def foreign():
    c, x = q.get()
    for operation in (lambda: c.width, lambda: c.toBufferSync(), lambda: x.fillRect(0,0,2,2)):
        try:
            operation()
        except RuntimeError as error:
            errors.append(str(error))
        else:
            raise AssertionError("Foreign access accepted")
    del operation, c, x
    gc.collect()
t = threading.Thread(target=foreign)
t.start(); t.join()
assert len(errors) == 3 and all("creating thread" in e for e in errors), errors
assert _native._debug_drain() == (0, 0)
''')

    def test_owner_thread_exit_releases_live_handles(self):
        self.run_case('''
q = queue.Queue()
def owner():
    c, x = rendered()
    # Font TLS initialized after GPU/readback cleanup registration.
    assert x.measureText("Canvas AV fj").width > 0
    x.fillText("late font", 1, 20)
    c.toBufferSync()
    q.put((c, x))
for _ in range(4):
    t = threading.Thread(target=owner)
    t.start(); t.join()
    c, x = q.get()
    assert _native._debug_drain() == (0, 0), "owner exit leaked native objects"
    try:
        c.width
    except RuntimeError:
        pass
    else:
        raise AssertionError("Ended owner accepted")
    del c, x
    gc.collect()
    assert _native._debug_drain() == (0, 0)
''')

    def test_foreign_cycle_collection(self):
        self.run_case('''
c, x = rendered()
class Holder: pass
h = Holder(); h.canvas = c; h.context = x; h.loop = h
q = queue.Queue(); q.put(h)
del c, x, h
def foreign_gc():
    h = q.get()
    del h
    gc.collect()
t = threading.Thread(target=foreign_gc)
t.start(); t.join()
assert _native._debug_drain() == (0, 0)
''')

    def test_readback_errors_then_thread_exit(self):
        self.run_case('''
errors = []
def owner():
    c, x = rendered()
    try:
        x.getImageData(0, 0, 0, 0)
    except (RuntimeError, ValueError, TypeError) as error:
        errors.append(str(error))
    else:
        raise AssertionError("Zero-size accepted")
    x.fillText("after error", 1, 20)
    assert c.toBufferSync().startswith(b"\\x89PNG")
t = threading.Thread(target=owner)
t.start(); t.join()
assert len(errors) == 1
assert _native._debug_drain() == (0, 0)
''')

    def test_interpreter_exit_with_live_gpu_objects(self):
        self.run_case('''
c, x = rendered()
x.fillText("exit", 1, 20)
png = c.toBufferSync()
assert _native._debug_drain() == (1, 1)
# Intentionally leave globals alive through CPython shutdown.
''')

    def test_clipped_paths_foreign_gc_and_range_error_recovery(self):
        self.run_case('''
c, x = rendered()
x.save(); x.translate(4.25, 3.5); x.rotate(0.17)
x.beginPath(); x.ellipse(20.5, 10.25, 17.5, 8.25, 0.3, 0, 7)
x.clip("evenodd"); x.setLineDash([2.5, 1.25, 0.75]); x.lineWidth = 2.25
x.beginPath(); x.moveTo(0,0); x.bezierCurveTo(10,30,20,-10,40,15); x.stroke()
try:
    x.arcTo(1,2,3,4,-1)
except ValueError as error:
    assert type(error).__name__ == "RangeError"
else:
    raise AssertionError("Missing original radius error")
x.restore(); x.fillRect(1.25, 2.5, 8.75, 9.25)
assert c.toBufferSync().startswith(b"\\x89PNG")
q = queue.Queue(); q.put((c,x)); del c,x
def foreign():
    c,x = q.get()
    try:
        x.translate(1,2)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Foreign transform accepted")
    del c,x
    gc.collect()
t = threading.Thread(target=foreign); t.start(); t.join()
assert _native._debug_drain() == (0,0)
''')

    def test_owner_exit_drops_path_state_stack(self):
        self.run_case('''
q = queue.Queue()
def owner():
    c,x = rendered()
    for n in range(5):
        x.save(); x.translate(0.25,0.75)
        x.beginPath(); x.arc(20,15,12,0,7); x.clip()
    x.setTransform(1,0.2,-0.1,1,2,3)
    x.beginPath(); x.rect(0,0,40,20); x.fill("evenodd")
    assert c.toBufferSync().startswith(b"\\x89PNG")
    q.put((c,x))
t = threading.Thread(target=owner); t.start(); t.join()
c,x=q.get()
assert _native._debug_drain() == (0,0)
del c,x; gc.collect()
assert _native._debug_drain() == (0,0)
''')

    def test_standalone_path_owner_gc(self):
        self.run_case('''
p = Path2D("M1 1L20 1L20 20Z")
q = Path2D(p)
r = p.offset(3.25,4.5).round(2.5)
assert _native._debug_drain() == (3,3)
assert q.edges and r.bounds["width"] > 0
assert p.points(3.5)
assert _native._debug_drain() == (3,3), "temporary effect handle leaked"
ref = weakref.ref(p)
del p,q,r
gc.collect()
assert ref() is None and _native._debug_drain() == (0,0)
''')

    def test_path_foreign_gc_retained_marker_snapshot(self):
        self.run_case('''
c,x = rendered()
p = Path2D("M0 0L3 0L1 3Z")
x.lineDashMarker = p
x.setLineDash([4,3]); x.lineWidth = 2
q = queue.Queue(); q.put(p); del p
errors = []
def foreign():
    p=q.get()
    try:
        p.rect(0,0,10,10)
    except RuntimeError as error:
        errors.append(str(error))
    del p
    gc.collect()
t=threading.Thread(target=foreign); t.start(); t.join()
assert len(errors)==1 and "creating thread" in errors[0]
assert _native._debug_drain()==(1,1)
x.beginPath(); x.moveTo(1,1); x.lineTo(55,25); x.stroke()
assert c.toBufferSync().startswith(b"\\x89PNG")
marker=x.lineDashMarker
assert isinstance(marker,Path2D) and marker.edges
del marker,c,x
gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_owner_exit_with_live_path_handles(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered()
    p=Path2D("M2 2L50 2L25 25Z")
    r=p.round(2.5)
    x.fill(p); x.clip(r); x.lineDashMarker=p
    assert c.toBufferSync().startswith(b"\\x89PNG")
    q.put((c,x,p,r))
t=threading.Thread(target=owner); t.start(); t.join()
c,x,p,r=q.get()
assert _native._debug_drain()==(0,0)
for value in (p,r):
    try:
        value.d
    except RuntimeError:
        pass
    else:
        raise AssertionError("Ended path owner accepted")
del value,c,x,p,r
gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_cross_owner_path_rejected_before_canvas_mutation(self):
        self.run_case('''
q=queue.Queue(); release=threading.Event()
def owner():
    p=Path2D("M1 1L20 1L20 20Z")
    q.put(p)
    assert release.wait(10)
    assert p.contains(10,5)
t=threading.Thread(target=owner); t.start()
p=q.get(); c,x=rendered()
before=c.toBufferSync()
try:
    try:
        x.fill(p)
    except RuntimeError as error:
        assert "creating thread" in str(error)
    else:
        raise AssertionError("Cross-owner path accepted")
    assert c.toBufferSync()==before
finally:
    release.set(); t.join()
del p,c,x
gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_foreign_cycle_collection_with_path_and_canvas(self):
        self.run_case('''
c,x=rendered(); p=Path2D("M1 1L20 1L20 20Z"); x.fill(p)
class Holder: pass
h=Holder(); h.c=c; h.x=x; h.p=p; h.loop=h
q=queue.Queue(); q.put(h); del c,x,p,h
def foreign():
    h=q.get(); del h; gc.collect()
t=threading.Thread(target=foreign); t.start(); t.join()
assert _native._debug_drain()==(0,0)
''')

    def test_interpreter_exit_with_live_standalone_paths(self):
        self.run_case('''
c,x=rendered()
p=Path2D("M2 2L50 2L25 25Z")
r=p.round(3.25)
x.clip(r); x.fill(p); x.lineDashMarker=p
assert c.toBufferSync().startswith(b"\\x89PNG")
assert _native._debug_drain()==(3,3)
''')

    def test_gradient_foreign_gc_keeps_native_state_ramp(self):
        self.run_case('''
c,x=rendered()
g=x.createLinearGradient(0,0,64,32)
g.addColorStop(0,"blue"); g.addColorStop(1,"red")
x.fillStyle=g
x.fillStyle="invalid CSS color"
assert x.fillStyle is None
ref=weakref.ref(g); q=queue.Queue(); q.put(g); del g
errors=[]
def foreign():
    g=q.get()
    for action in (lambda:g.addColorStop(0.5,"green"), lambda:repr(g)):
        try:
            action()
        except RuntimeError as error:
            errors.append(str(error))
        else:
            raise AssertionError("Foreign gradient accepted")
    del action,g; gc.collect()
t=threading.Thread(target=foreign); t.start(); t.join()
assert len(errors)==2 and ref() is None
assert _native._debug_drain()==(1,1)
x.fillRect(0,0,64,32)
assert c.toBufferSync().startswith(b"\\x89PNG")
del c,x; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_gradient_cache_restore_and_reset_retention(self):
        self.run_case('''
c,x=rendered()
g1=x.createLinearGradient(0,0,64,32); g1.addColorStop(0,"blue"); g1.addColorStop(1,"red")
g2=x.createLinearGradient(0,0,64,32); g2.addColorStop(0,"green"); g2.addColorStop(1,"yellow")
r1,r2=weakref.ref(g1),weakref.ref(g2)
x.fillStyle=g1; x.save(); x.fillStyle=g2; x.restore()
assert x.fillStyle is g2
del g1; gc.collect()
assert r1() is None and _native._debug_drain()==(2,2)
x.fillRect(0,0,64,32); assert c.toBufferSync().startswith(b"\\x89PNG")
x.reset(); del g2; gc.collect()
assert x.fillStyle=="#000000" and r2() is not None
x.fillStyle="red"; gc.collect()
assert r2() is None and _native._debug_drain()==(1,1)
del c,x; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_owner_exit_with_shared_gradient_path_and_canvas(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered(); g=x.createConicGradient(0.3,30,15)
    g.addColorStop(0,"blue"); g.addColorStop(1,"red")
    p=Path2D("M1 1L60 1L30 30Z")
    x.fillStyle=g; x.strokeStyle=g; x.save(); x.fill(p)
    assert c.toBufferSync().startswith(b"\\x89PNG")
    q.put((c,x,g,p))
t=threading.Thread(target=owner); t.start(); t.join()
c,x,g,p=q.get()
assert _native._debug_drain()==(0,0)
try:
    g.addColorStop(0.5,"green")
except RuntimeError:
    pass
else:
    raise AssertionError("Ended gradient owner accepted")
del c,x,g,p; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_cross_owner_gradient_rejected_before_style_change(self):
        self.run_case('''
q=queue.Queue(); release=threading.Event()
def owner():
    g=CanvasGradient("linear",0,0,64,32); g.addColorStop(0,"blue"); g.addColorStop(1,"red")
    q.put(g); assert release.wait(10); g.addColorStop(0.5,"green")
t=threading.Thread(target=owner); t.start()
g=q.get(); c,x=rendered(); before=x.fillStyle; png=c.toBufferSync()
try:
    try:
        x.fillStyle=g
    except RuntimeError:
        pass
    else:
        raise AssertionError("Cross-owner gradient accepted")
    assert x.fillStyle==before and c.toBufferSync()==png
finally:
    release.set(); t.join()
del g,c,x; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_gradient_shared_after_creator_canvas_gc(self):
        self.run_case('''
c1,x1=rendered(); c2,x2=rendered()
g=x1.createLinearGradient(0,0,64,32); g.addColorStop(0,"blue"); g.addColorStop(1,"red")
x1.fillStyle=g; x2.fillStyle=g
ref=weakref.ref(c1); del c1,x1; gc.collect()
assert ref() is None
x2.fillRect(0,0,64,32); before=bytes(x2.getImageData(0,0,64,32).data)
g.addColorStop(0.5,"green"); x2.fillRect(0,0,64,32)
assert bytes(x2.getImageData(0,0,64,32).data)!=before
del g,c2,x2; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_interpreter_exit_with_gradient_reference_cache(self):
        self.run_case('''
c,x=rendered()
g=x.createRadialGradient(20,10,1,30,15,30)
g.addColorStop(0,"#2060ff"); g.addColorStop(1,"#ff2450")
x.fillStyle=g; x.strokeStyle=g; x.save(); x.fillRect(0,0,64,32)
assert c.toBufferSync().startswith(b"\\x89PNG")
assert _native._debug_drain()==(2,2)
''')

    def test_dom_snapshot_outlives_owner_thread(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered(); x.setTransform(1.25,0.125,0.25,0.875,10.25,8.75)
    q.put((x.getTransform(),DOMPoint(2.25,3.5),DOMRect(10,20,-5,-8)))
t=threading.Thread(target=owner); t.start(); t.join()
m,p,r=q.get()
assert _native._debug_drain()==(0,0)
c,x=rendered(); x.currentTransform=m
assert x.getTransform().toJSON()==m.toJSON()
assert p.matrixTransform(m).toJSON()==m.transformPoint(p).toJSON()
assert r.right==5 and r.bottom==12
path=Path2D("M0 0L20 0L10 20Z"); transformed=path.transform(m)
x.fill(transformed); assert c.toBufferSync().startswith(b"\\x89PNG")
del c,x,path,transformed; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_dom_getter_foreign_access_rejected_snapshot_allowed(self):
        self.run_case('''
c,x=rendered(); x.translate(10.25,8.75); snapshot=x.getTransform()
before=x.currentTransform.toJSON(); q=queue.Queue()
def foreign():
    for action in (lambda:x.getTransform(),lambda:x.currentTransform):
        try:
            action()
        except RuntimeError as error:
            assert "creating thread" in str(error)
        else:
            raise AssertionError("Foreign context getter accepted")
    copy=snapshot.clone(); copy.e=99
    q.put(copy)
t=threading.Thread(target=foreign); t.start(); t.join()
copy=q.get(); assert copy.e==99 and snapshot.e==10.25
assert x.getTransform().toJSON()==before
del c,x; gc.collect()
assert _native._debug_drain()==(0,0)
''')

    def test_dom_snapshots_survive_resize_and_canvas_gc(self):
        self.run_case('''
c,x=rendered(); m=DOMMatrix([1.25,0.125,0.25,0.875,10.25,8.75])
x.setTransform(m); snapshot=x.getTransform(); values=snapshot.toFloat64Array()
m.e=99; c.width=80
assert x.currentTransform.isIdentity and snapshot.e==10.25
ref=weakref.ref(c); del c,x; gc.collect()
assert ref() is None and _native._debug_drain()==(0,0)
assert snapshot.toFloat64Array()==values
copy=DOMMatrix.fromFloat64Array(values); copy.f=70
assert snapshot.f==8.75
''')

    def test_matrix_operations_after_owner_exit(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered(); x.setTransform("translate(10.25px,8.75px) rotate(17.125deg)")
    q.put(x.getTransform())
t=threading.Thread(target=owner); t.start(); t.join()
m=q.get(); assert _native._debug_drain()==(0,0)
r=m.rotateFromVector(.375,-.8125).scale(1.25,.875).skew(17.125,-23.75)
c,x=rendered(); x.setTransform(r); x.fillRect(0,0,30,20)
assert c.toBufferSync().startswith(b"\\x89PNG")
del c,x; gc.collect(); assert _native._debug_drain()==(0,0)
''')

    def test_matrix_noop_shared_storage_and_detachment(self):
        self.run_case('''
m=DOMMatrix([1.25,.125,.25,.875,10.25,8.75]); copy=m.skewX()
assert copy is not m
copy.e=77; assert m.e==77
copy.translateSelf(1,2); copy.e=88; assert m.e==77
singular=DOMMatrix([1,2,2,4,5,6]); assert singular.invertSelf() is undefined
assert not singular.is2D
assert _native._debug_drain()==(0,0)
''')

    def test_projection_snapshot_outlives_owner_thread(self):
        self.run_case('''
q=queue.Queue()
def owner():
    c,x=rendered(); p=x.createProjection([2.25,1.75,60.5,3.25,57.75,29.5,5.5,28.25])
    q.put(p)
t=threading.Thread(target=owner); t.start(); t.join()
p=q.get(); assert _native._debug_drain()==(0,0)
c,x=rendered(); x.setTransform(p); x.fillRect(0,0,64,32)
assert c.toBufferSync().startswith(b"\\x89PNG")
del c,x; gc.collect(); assert _native._debug_drain()==(0,0)
assert len(p.toFloat64Array())==16
''')

    def test_projection_owner_rejection_and_error_leave_state(self):
        self.run_case('''
c,x=rendered(); x.translate(10.25,8.75); before=x.getTransform().toJSON(); png=c.toBufferSync()
def foreign():
    try:
        x.createProjection([32,16])
    except RuntimeError as error:
        assert "creating thread" in str(error)
    else:
        raise AssertionError("Foreign projection accepted")
t=threading.Thread(target=foreign); t.start(); t.join()
for quad,basis in (([1],undefined),([0,0,1,1,2,2],[0,0])):
    try:
        x.createProjection(quad,basis)
    except TypeError:
        pass
    else:
        raise AssertionError("Invalid projection accepted")
assert x.getTransform().toJSON()==before and c.toBufferSync()==png
del c,x; gc.collect(); assert _native._debug_drain()==(0,0)
''')

    def test_projection_size_snapshot_and_gc(self):
        self.run_case('''
c,x=rendered(); p=x.createProjection([32,16]); assert p.a==.5 and p.d==.5
c.width=128; c.height=64; q=x.createProjection([32,16]); assert q.a==.25 and q.d==.25
assert p.a==.5 and p.d==.5
ref=weakref.ref(c); del c,x; gc.collect()
assert ref() is None and _native._debug_drain()==(0,0)
r=DOMMatrix(p); r.e=77; assert p.e==0
''')


    def test_metrics_owned_after_thread_exit(self):
        self.run_case('''
from py_skia_canvas import TextMetrics
q=queue.Queue()
def owner():
    c,x=rendered(); x.font="20px DejaVu Sans"
    q.put(x.measureText("AV ffi 中文"))
t=threading.Thread(target=owner); t.start(); t.join()
m=q.get(); assert _native._debug_drain()==(0,0)
assert m.width>0 and m.lines[0]["runs"]
copy=TextMetrics(m); assert copy.lines is m.lines
m.lines[0]["runs"][0]["probe"]=17
assert copy.lines[0]["runs"][0]["probe"]==17
try:
    m.width=0
except TypeError:
    pass
else:
    raise AssertionError("Readonly metric accepted")
m.note="owned"; del m.note
assert m.width>0
''')

    def test_metrics_snapshot_foreign_access_context_rejected(self):
        self.run_case('''
c,x=rendered(); m=x.measureText("ffi"); q=queue.Queue()
def foreign():
    assert m.width>0; m.note="foreign"
    try:
        x.measureText("ffi")
    except RuntimeError as error:
        assert "creating thread" in str(error)
    else:
        raise AssertionError("Foreign measurement accepted")
    q.put(m.width)
t=threading.Thread(target=foreign); t.start(); t.join()
assert q.get()==m.width and m.note=="foreign"
ref=weakref.ref(c); del c,x; gc.collect()
assert ref() is None and _native._debug_drain()==(0,0)
assert m.width>0
''')

    def test_metrics_ordinary_inputs_resize_and_error_retention(self):
        self.run_case('''
from py_skia_canvas import TextMetrics
c,x=rendered(); x.font="16px DejaVu Sans"
m=x.measureText(["A",None,"B"]); assert m.width==x.measureText("A,,B").width
assert x.measureText().width==x.measureText("undefined").width
assert x.measureText(None).width==x.measureText("null").width
assert x.measureText("AV",undefined).width==x.measureText("AV",{}).width
child={"runs":[]}; source={"width":4,"lines":[child]}; v=TextMetrics(source)
source["width"]=99; assert v.width==4 and v.lines[0] is child
try:
    del v.width
except TypeError:
    pass
else:
    raise AssertionError("Nonconfigurable metric accepted")
before=m.width; c.width=80; assert m.width==before
del c,x; gc.collect(); assert _native._debug_drain()==(0,0)
''')

    def test_glyph_observer_owned_empty_and_foreign_rejection(self):
        self.run_case('''
import json
c,x=rendered(); x.font="16px DejaVu Sans"; before=x.measureText("AV ffi").width
record=json.loads(x._native.audit_glyphs("AV ffi",None))
assert record["runs"] and record["runs"][0]["glyphs"]
assert isinstance(json.loads(x._native.audit_glyphs("",None))["runs"],list)
q=queue.Queue()
def foreign():
    try:
        x._native.audit_glyphs("AV",None)
    except RuntimeError as error:
        q.put("creating thread" in str(error))
    else:
        q.put(False)
t=threading.Thread(target=foreign); t.start(); t.join()
assert q.get_nowait(),"Foreign glyph observer accepted"
assert x.measureText("AV ffi").width==before
del c,x; gc.collect(); assert _native._debug_drain()==(0,0)
assert record["runs"][0]["font"]["family"]
''')


if __name__ == "__main__":
    unittest.main()
