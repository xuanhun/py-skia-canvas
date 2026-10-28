"""Installed original-core constructor/argument ownership, default GPU required."""
import unittest
import test_lifecycle as legacy

class ContractLifecycleTests(unittest.TestCase):
    run_case=legacy.LifecycleTests.run_case

    def test_direct_context_is_real_and_not_a_page(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(32,24);a=CanvasRenderingContext2D(c);b=CanvasRenderingContext2D(c)
assert a.canvas is c and b.canvas is c and a is not b and c.pages==[]
a.fillStyle='red';a.fillRect(0,0,32,24);assert bytes(a.getImageData(0,0,1,1).data)==bytes([255,0,0,255])
x=c.getContext(['2d']);assert x is c.getContext('2d') and x not in (a,b) and len(c.pages)==1
assert bytes(x.getImageData(0,0,1,1).data)==bytes(4);assert c.gpu and c.engine['renderer']=='GPU'
del c,a,b,x;gc.collect();assert _native._debug_pages()==0 and _native._debug_drain()==(0,0)
''')

    def test_head_reset_does_not_reset_independent_context(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(32,24);a=CanvasRenderingContext2D(c);a.fillStyle='red';a.fillRect(0,0,32,24)
x=c.getContext('2d');x.fillStyle='blue';x.fillRect(0,0,32,24);c.width='48'
assert c.width==48 and a.fillStyle=='#ff0000' and x.fillStyle=='#000000'
assert a._native.context_size()==(32,24) and x._native.context_size()==(48,24)
assert bytes(a.getImageData(0,0,1,1).data)==bytes([255,0,0,255])
''')

    def test_context_without_public_page_survives_dimension_update(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(32,24);a=CanvasRenderingContext2D(c);a.fillStyle='red';c.width=48
assert c.pages==[] and a.fillStyle=='#ff0000' and a._native.context_size()==(32,24)
b=CanvasRenderingContext2D(c);assert b._native.context_size()==(48,24)
assert c.pages==[]
''')

    def test_independent_contexts_release_after_parent_gc(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(32,24);a=CanvasRenderingContext2D(c);b=c.getContext('2d');r=weakref.ref(c)
del c,b;gc.collect();assert r() is None and a.canvas is undefined and _native._debug_pages()==1
a.fillStyle='red';a.fillRect(0,0,10,10);assert a._native.encode('raw')[:4]==bytes([255,0,0,255])
del a;gc.collect();assert _native._debug_drain()==(0,0) and _native._debug_pages()==0
''')

    def test_foreign_constructor_access_rejected(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(32,24);q=queue.Queue()
def other():
 try:CanvasRenderingContext2D(c)
 except RuntimeError:q.put(True)
 else:q.put(False)
t=threading.Thread(target=other);t.start();t.join();assert q.get_nowait() and not c.pages
''')

    def test_foreign_direct_context_gc_queues_only_metadata(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(32,24);a=CanvasRenderingContext2D(c);x=c.getContext('2d');holder=[a];del a
t=threading.Thread(target=holder.clear);t.start();t.join();gc.collect();_native._debug_drain()
assert _native._debug_pages()==1 and c.getContext('2d') is x
del c,x;gc.collect();assert _native._debug_drain()==(0,0) and _native._debug_pages()==0
''')

    def test_direct_context_owner_exit_releases_native_state(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
q=queue.Queue()
def owner():
 c=Canvas(32,24);a=CanvasRenderingContext2D(c);a.fillRect(0,0,10,10);a.getImageData(0,0,1,1);q.put(a)
t=threading.Thread(target=owner);t.start();t.join();a=q.get_nowait();assert _native._debug_drain()==(0,0) and _native._debug_pages()==0
try:a.fillRect(0,0,1,1)
except RuntimeError:pass
else:raise AssertionError('ended direct owner accepted')
''')

    def test_canvas_source_ignores_detached_drawing_and_creates_public_page(self):
        self.run_case('''
from py_skia_canvas import CanvasRenderingContext2D
c=Canvas(16,12);a=CanvasRenderingContext2D(c);a.fillStyle='red';a.fillRect(0,0,16,12)
t=Canvas(16,12);x=t.getContext('2d');x.drawCanvas(c,0,0)
assert len(c.pages)==1 and c.pages[0] is not a and bytes(x.getImageData(0,0,1,1).data)==bytes(4)
p=x.createPattern(c,'repeat');x.fillStyle=p;x.fillRect(0,0,16,12);assert bytes(x.getImageData(0,0,1,1).data)==bytes(4)
''')

    def test_constructor_and_gpu_setter_keep_original_truth_and_gpu_policy(self):
        self.run_case('''
c=Canvas('32',[24],{'gpu':[],'unknown':True});assert c.width==32 and c.height==24 and c.gpu and c.engine['renderer']=='GPU'
c.gpu=False;assert not c.gpu;c.gpu={};assert c.gpu
broken=Canvas(32,24,{'gpu':False});assert broken.gpu and broken.engine['renderer']=='CPU'
''')

    def test_cyclic_singleton_argument_is_not_forwarded_to_stack_overflow(self):
        self.run_case('''
c=Canvas(32,24);x=c.getContext('2d');a=[];a.append(a)
try:x.moveTo(a,0)
except NotImplementedError:pass
else:raise AssertionError('cyclic native numeric recursion accepted')
''')

    def test_extra_and_missing_args_use_native_contract(self):
        self.run_case('''
c=Canvas(32,24);x=c.getContext('2d');x.fillRect('0','0',16,12,'ignored')
assert bytes(x.getImageData(0,0,1,1).data)==bytes([0,0,0,255])
try:x.arcTo(1,2,3,4)
except TypeError as e:assert str(e)=='not enough arguments (missing: radius)'
else:raise AssertionError('missing argument accepted')
''')

    def test_canvas_option_factory_preserves_original_gamma_boundary_and_error_order(self):
        self.run_case('''
c=Canvas(32,24,{'textGamma':4});assert c.engine['textGamma']==4-2**-23
c=Canvas(32,24,{'textGamma':10});assert c.engine['textGamma']==10
try:Canvas(32,24,{'textContrast':-1,'textGamma':-1})
except _native.RangeError as e:assert 'textContrast' in str(e)
else:raise AssertionError('range validation skipped')
''')

    def test_dead_weak_parent_matches_original_readback_failure(self):
        self.run_case('''
c=Canvas(32,24);x=c.getContext('2d');del c;gc.collect();assert x.canvas is undefined
x.fillText('A',1,20);assert x.measureText('A').width>0
try:x.getImageData(0,0,1,1)
except TypeError as e:assert 'failed to downcast any to neon::types_impl::boxed::JsBox' in str(e)
else:raise AssertionError('dead parent public readback accepted')
''')

if __name__=='__main__':unittest.main()
