"""Real installed original-core multipage/async ownership tests; no GPU skip or fallback."""
import unittest
import test_lifecycle as legacy

class ExportLifecycleTests(unittest.TestCase):
    run_case=legacy.LifecycleTests.run_case

    def test_page_identity_and_reset(self):
        self.run_case('''
c=Canvas(16,12); assert c.pages==[]
a=c.newPage();a.fillStyle='red';a.fillRect(0,0,16,12)
b=c.newPage(20,18);b.fillStyle='blue';b.fillRect(0,0,20,18)
assert c.pages==[a,b] and c.getContext('2d') is b
copy=c.pages;copy.clear();assert len(c.pages)==2
c.width=22;assert b.fillStyle=='#000000' and a.fillStyle=='#ff0000'
assert bytes(a.getImageData(0,0,1,1).data)==bytes([255,0,0,255])
assert bytes(b.getImageData(0,0,1,1).data)==bytes(4)
c.newPage(99);assert c.width==22 and c.height==18
c.newPage(99,99,99);assert c.width==22 and c.height==18
del c,a,b,copy;gc.collect();assert _native._debug_drain()==(0,0);assert _native._debug_pages()==0
''')

    def test_old_page_survives_parent(self):
        self.run_case('''
c=Canvas(16,12);a=c.newPage();b=c.newPage();ref=weakref.ref(c)
assert _native._debug_pages()==2
del c,b;gc.collect();assert ref() is None;assert _native._debug_pages()==1
a.fillStyle='red';a.fillRect(0,0,4,4);assert a._native.encode('raw')[:4]==bytes([255,0,0,255])
del a;gc.collect();assert _native._debug_drain()==(0,0);assert _native._debug_pages()==0
''')

    def test_foreign_page_finalizers(self):
        self.run_case('''
c=Canvas(16,12);a=c.newPage();c.newPage();holder=[c,a];del c,a
t=threading.Thread(target=lambda:holder.clear());t.start();t.join()
gc.collect();assert _native._debug_drain()==(0,0);assert _native._debug_pages()==0
''')

    def test_async_snapshot_and_repeat(self):
        self.run_case('''
import asyncio
c=Canvas(16,12);x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,16,12);p=c.toBuffer('raw')
x.fillStyle='blue';x.fillRect(0,0,16,12)
async def wait():
    a=await p;b=await p;assert a==b and a[:4]==bytes([255,0,0,255])
asyncio.run(wait());assert p._audit['owner']!=p._audit['worker']
''')

    def test_gpu_page_cache_materialized_on_owner(self):
        self.run_case('''
import asyncio
c=Canvas(16,12);x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,16,12);expected=c.toBufferSync('raw');p=c.toBuffer('raw')
async def wait():assert await p==expected
asyncio.run(wait());a=p._audit
assert a['cachedImagesBefore']==1 and a['cachedTexturesBefore']==1,a
assert a['cachedImagesAfter']==1 and a['cachedTexturesAfter']==0,a
assert a['owner']!=a['worker'] and a['materializedOnOwner'],a
''')

    def test_async_parent_collected_before_await(self):
        self.run_case('''
import asyncio
c=Canvas(64,32);x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,64,32);p=c.toBuffer('png');ref=weakref.ref(c)
del c,x;gc.collect();assert ref() is None;assert _native._debug_drain()==(0,0)
async def wait():assert (await p).startswith(b'\\x89PNG')
asyncio.run(wait())
''')

    def test_owner_exits_before_await(self):
        self.run_case('''
import asyncio
q=queue.Queue()
def owner():
 c=Canvas(64,32);x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,64,32);c.toBufferSync('png');q.put(c.toBuffer('raw'))
t=threading.Thread(target=owner);t.start();t.join();p=q.get_nowait()
assert not thread_failures and _native._debug_drain()==(0,0)
async def wait():assert (await p)[:4]==bytes([255,0,0,255])
asyncio.run(wait())
''')

    def test_await_on_foreign_thread(self):
        self.run_case('''
import asyncio
c=Canvas(16,12);p=c.toBuffer('png');q=queue.Queue()
async def wait():q.put(await p)
t=threading.Thread(target=lambda:asyncio.run(wait()));t.start();t.join();assert not thread_failures;assert q.get_nowait().startswith(b'\\x89PNG')
''')

    def test_waiter_cancel_does_not_cancel_job(self):
        self.run_case('''
import asyncio
c=Canvas(256,128);x=c.getContext('2d');x.fillRect(0,0,256,128);p=c.toBuffer('png')
async def wait():
 async def one():return await p
 task=asyncio.create_task(one());task.cancel()
 try:await task
 except asyncio.CancelledError:pass
 assert (await p).startswith(b'\\x89PNG')
asyncio.run(wait())
''')

    def test_multiple_waiters(self):
        self.run_case('''
import asyncio
c=Canvas(64,32);p=c.toBuffer('raw')
async def wait():
 async def one():return await p
 values=await asyncio.gather(*[one() for _ in range(8)]);assert all(v==values[0] for v in values)
asyncio.run(wait())
''')

    def test_abandoned_tasks_release_jobs(self):
        self.run_case('''
import time
c=Canvas(32,16);x=c.getContext('2d');x.fillRect(0,0,32,16)
for _ in range(20):c.toBuffer('png')
del c,x;gc.collect()
deadline=time.monotonic()+10
while _native._debug_export_jobs() and time.monotonic()<deadline:time.sleep(.005)
assert _native._debug_export_jobs()==0 and _native._debug_drain()==(0,0)
''')

    def test_concurrent_exports_and_sync(self):
        self.run_case('''
import asyncio
c=Canvas(32,16);x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,32,16);expected=c.toBufferSync('raw')
jobs=[c.toBuffer('raw') for _ in range(12)];assert c.toBufferSync('raw')==expected
async def wait():
 for p in jobs:assert await p==expected
asyncio.run(wait())
''')

    def test_all_export_properties(self):
        self.run_case('''
import asyncio
c=Canvas(32,16)
async def wait():
 for fmt in ['png','jpg','webp','pdf','svg','raw']:
  value=await getattr(c,fmt);assert len(value)>0
asyncio.run(wait())
''')

    def test_foreign_start_rejected(self):
        self.run_case('''
c=Canvas(16,12);c.newPage();q=queue.Queue()
def other():
 for fn in [c.newPage,c.toBuffer,c.toBufferSync]:
  try:fn()
  except RuntimeError:q.put(True)
  else:q.put(False)
t=threading.Thread(target=other);t.start();t.join();assert [q.get_nowait() for _ in range(3)]==[True]*3
''')

    def test_async_errors_repeat(self):
        self.run_case('''
import asyncio
c=Canvas(32,16);p=c.toFile('/nonexistent/export.png')
async def wait():
 for _ in range(2):
  try:await p
  except _native.Error as e:assert str(e).startswith('I/O Error: ')
  else:raise AssertionError('missing I/O failure')
asyncio.run(wait())
''')

    def test_original_alias_return_and_warning(self):
        self.run_case('''
import contextlib,io
c=Canvas(16,12);log=io.StringIO()
with contextlib.redirect_stderr(log):
 assert c.toDataURLSync() is None;assert c.toDataURLSync() is None
assert log.getvalue().count('Deprecation warning:')==1
''')

if __name__=='__main__':unittest.main()
