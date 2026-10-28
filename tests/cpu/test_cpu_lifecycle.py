"""Installed-wheel CPU fallback ownership/export contracts; unavailable GPU is required."""
import asyncio,gc,hashlib,json,os,queue,sys,tempfile,threading,unittest,weakref
from pathlib import Path
from py_skia_canvas import Canvas,CanvasRenderingContext2D,Path2D,Image,ImageData,FontLibrary,DOMMatrix,undefined,_native

class CpuLifecycleTests(unittest.TestCase):
    def setUp(self):
        """Require a real installed CPU-fallback wheel; arm owner-only surface observation."""
        self.assertTrue(Path(_native.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()))
        self.c=Canvas(128,96);self.x=self.c.getContext('2d');self.assertFalse(self.c.gpu);self.assertEqual(self.c.engine['renderer'],'CPU');self.x._native.audit_surface_capture(True)
    def tearDown(self):
        """Prove no successful Vulkan render target was allocated by any owner operation."""
        self.assertEqual(json.loads(self.x._native.audit_surface_capture(False))['surfaces'],0)
        self.c=self.x=None;gc.collect();_native._debug_drain()
    def test_automatic_fallback_and_requested_gpu_unavailable(self):
        self.assertIn('error',self.c.engine);self.c.gpu=True;self.assertFalse(self.c.gpu)
        self.c.gpu=False;self.assertFalse(self.c.gpu)
    def test_constructor_flag_does_not_require_a_device(self):
        c=Canvas(24,16,{'gpu':False});self.assertFalse(c.gpu);self.assertEqual(c.engine['renderer'],'CPU');self.assertEqual(len(c.toBufferSync('raw')),24*16*4)
    def test_exact_opaque_pixel_and_resize_reset(self):
        self.x.fillStyle='#3168bf';self.x.fillRect(0,0,128,96);self.assertEqual(self.c.toBufferSync('raw')[:4],bytes([49,104,191,255]));self.c.width=64;self.assertEqual(self.x.fillStyle,'#000000')
    def test_alpha_and_compositing(self):
        self.x.fillStyle='red';self.x.fillRect(0,0,128,96);self.x.globalCompositeOperation='destination-out';self.x.fillRect(0,0,20,20);self.assertEqual(bytes(self.x.getImageData(0,0,1,1).data),bytes(4))
    def test_clip_gradient_and_path(self):
        p=Path2D('M4 4 L100 4 L60 80 Z');self.x.clip(p);g=self.x.createLinearGradient(0,0,128,0);g.addColorStop(0,'red');g.addColorStop(1,'blue');self.x.fillStyle=g;self.x.fillRect(0,0,128,96);self.assertTrue(any(self.c.toBufferSync('raw')))
    def test_effects_filters_and_dash_marker(self):
        p=Path2D();p.rect(0,0,6,6);self.x.lineDashMarker=p;self.x.lineDashFit='rotate';self.x.setLineDash([5,3]);self.x.filter='blur(1px) contrast(1.2)';self.x.shadowColor='#0008';self.x.shadowBlur=2;self.x.strokeRect(10,10,90,70);self.assertTrue(self.c.toBufferSync().startswith(b'\x89PNG'))
    def test_path_boolean_transform_and_effects(self):
        a=Path2D();a.rect(0,0,80,80);b=Path2D();b.rect(40,20,80,60);p=a.union(b).round(2).offset(2,3).transform(DOMMatrix().translate(1,1));self.x.fill(p);self.assertTrue(any(self.c.toBufferSync('raw')))
    def test_font_unicode_wrap_and_metrics(self):
        self.x.font='italic bold 20px sans-serif';self.x.textWrap=True;text='AV ffi cafe\u0301 中文 مرحبا \U0001f600';m=self.x.measureText(text,100);self.assertGreater(m.width,0);self.x.fillText(text,2,25,100);self.x.strokeText('CPU',2,80);self.assertTrue(any(self.c.toBufferSync('raw')))
    def test_font_registration_reset(self):
        path=Path(os.environ['WINDIR'])/'Fonts/arial.ttf' if os.name=='nt' else Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf');FontLibrary.use('CPU test alias',str(path));self.x.font='20px "CPU test alias"';self.assertGreater(self.x.measureText('Canvas').width,0);FontLibrary.reset()
    def test_image_decode_and_crop(self):
        self.x.fillStyle='green';self.x.fillRect(0,0,128,96);im=Image(self.c.toBufferSync('png'));target=Canvas(24,16);target.getContext('2d').drawImage(im,0,0,50,40,0,0,24,16);self.assertEqual(target.toBufferSync('raw')[:4],bytes([0,128,0,255]))
    def test_image_data_write_and_dirty_rect(self):
        im=ImageData(bytes([255,0,0,255]*16),4,4);self.x.putImageData(im,2,2,0,0,2,2);self.assertEqual(bytes(self.x.getImageData(2,2,1,1).data),bytes([255,0,0,255]));self.assertEqual(bytes(self.x.getImageData(5,5,1,1).data),bytes(4))
    def test_pattern_and_canvas_source(self):
        tile=Canvas(8,8);t=tile.getContext('2d');t.fillStyle='#aa4422';t.fillRect(0,0,8,8);self.x.fillStyle=self.x.createPattern(tile,'repeat');self.x.fillRect(0,0,128,96);self.assertEqual(self.c.toBufferSync('raw')[:4],bytes([170,68,34,255]))
    def test_all_sync_formats(self):
        self.x.fillText('CPU export',3,20)
        for fmt in ('png','jpg','webp','raw','pdf','svg'):
            with self.subTest(fmt=fmt):self.assertGreater(len(self.c.toBufferSync(fmt)),10)
    def test_all_async_formats_and_pixel_snapshot(self):
        async def run():
            self.x.fillStyle='red';self.x.fillRect(0,0,128,96);p=self.c.toBuffer('raw');self.x.fillStyle='blue';self.x.fillRect(0,0,128,96);self.assertEqual((await p)[:4],bytes([255,0,0,255]))
            for fmt in ('png','jpg','webp','raw','pdf','svg'):self.assertGreater(len(await self.c.toBuffer(fmt)),10)
        asyncio.run(run())
    def test_multi_page_files_and_async_sequences(self):
        self.x.fillRect(0,0,8,8);self.c.newPage(80,60).fillRect(2,2,20,20);self.assertEqual(len(self.c.pages),2)
        with tempfile.TemporaryDirectory() as tmp:
            self.c.toFileSync(str(Path(tmp)/'page-{}.png'));self.assertEqual(len(list(Path(tmp).glob('*.png'))),2)
            async def run():await self.c.toFile(str(Path(tmp)/'page-{}.svg'))
            asyncio.run(run());self.assertEqual(len(list(Path(tmp).glob('*.svg'))),2)
    def test_cancel_waiter_retains_export(self):
        self.x.fillText('cancel',1,20)
        async def run():
            p=self.c.toBuffer('png')
            async def wait():return await p
            task=asyncio.create_task(wait());task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertTrue((await p).startswith(b'\x89PNG'))
        asyncio.run(run())
    def test_shared_waiters_and_repeat_await(self):
        async def run():
            p=self.c.toBuffer('png');a,b=await asyncio.gather(p,p);self.assertEqual(a,b);self.assertEqual(a,await p)
        asyncio.run(run())
    def test_foreign_thread_access_rejected(self):
        errors=[]
        def run():
            try:self.c.toBufferSync()
            except RuntimeError:errors.append(True)
        t=threading.Thread(target=run);t.start();t.join(10);self.assertFalse(t.is_alive());self.assertEqual(errors,[True])
    def test_parallel_cpu_owners_and_thread_exit(self):
        results=queue.Queue()
        def run():
            try:
                c=Canvas(64,32);x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,64,32);x.fillText('owner',1,20);results.put((not c.gpu,c.toBufferSync('raw')[:4]))
            except BaseException as e:results.put(e)
        ts=[threading.Thread(target=run) for _ in range(6)]
        for t in ts:t.start()
        for t in ts:t.join(15);self.assertFalse(t.is_alive())
        values=[results.get_nowait() for _ in ts];self.assertTrue(all(v==(True,bytes([255,0,0,255])) for v in values),values)
    def test_owner_exit_before_export_await(self):
        results=queue.Queue()
        def run():
            c=Canvas(32,24);c.getContext('2d').fillRect(0,0,32,24);results.put(c.toBuffer('png'))
        t=threading.Thread(target=run);t.start();t.join(15);self.assertFalse(t.is_alive());p=results.get_nowait()
        async def wait():return await p
        self.assertTrue(asyncio.run(wait()).startswith(b'\x89PNG'))
    def test_foreign_finalizer_and_native_resource_gc(self):
        c=Canvas(16,16);x=c.getContext('2d');holder=[c,x];del c,x;t=threading.Thread(target=holder.clear);t.start();t.join(10);gc.collect();_native._debug_drain();self.assertEqual(len(self.c.toBufferSync('raw')),128*96*4)
    def test_direct_context_and_dead_parent(self):
        c=Canvas(32,24);x=CanvasRenderingContext2D(c);ref=weakref.ref(c);del c;gc.collect();self.assertIsNone(ref());self.assertIs(x.canvas,undefined);x.fillText('alive',1,15);self.assertGreater(x.measureText('alive').width,0);self.assertTrue(x._native.encode('png').startswith(b'\x89PNG'))
    def test_error_recovery(self):
        g=self.x.createLinearGradient(0,0,1,1)
        with self.assertRaises(ValueError):g.addColorStop(2,'red')
        self.x.fillRect(0,0,20,20);self.assertEqual(self.c.toBufferSync('raw')[:4],bytes([0,0,0,255]))

if __name__=='__main__':unittest.main()
