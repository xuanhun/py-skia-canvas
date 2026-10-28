"""Observe real Skia Raster calls and prohibit Vulkan surface/queue calls in CPU profile."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path

def main():
    """Run installed Linux wheel under GDB, fresh output; return success or raise.
    Pixel dimensions belong to the fixed witness. Native resources stay on the
    calling owner thread. No rendering algorithm or availability policy is changed.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1]
    if os.environ.get('PATH') or Path.cwd().is_relative_to(root):p.error('Require outside working directory and empty PATH')
    from py_skia_canvas import _native
    native=Path(_native.__file__).resolve();assert native.is_relative_to(Path(sys.prefix).resolve());a.out.mkdir(exist_ok=False)
    for source,name in [('tests/native/cpu.gdb','commands.gdb'),('tests/native/python_cpu_scene.py','scene.py')]:shutil.copyfile(root/source,a.out/name)
    args=['/usr/bin/gdb','-nx','-batch','-x',str(a.out/'commands.gdb'),'--args',sys.executable,'-I',str(a.out/'scene.py')]
    with (a.out/'trace.log').open('xb') as f:result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=60)
    raw=(a.out/'trace.log').read_bytes();log=raw.decode(errors='replace');counts={name:log.count(marker) for name,marker in [('raster','NATIVE_CPU_RASTER_HIT'),('gpuSurfaces','UNEXPECTED_GPU_SURFACE_HIT'),('gpuQueues','UNEXPECTED_GPU_QUEUE_HIT')]};okay=result.returncode==0 and 'exited normally' in log and counts['raster']>0 and not counts['gpuSurfaces'] and not counts['gpuQueues']
    (a.out/'run.json').write_text(json.dumps(dict(status='NATIVE_CPU_RASTER_OBSERVED' if okay else 'INCOMPLETE',argv=args,exitCode=result.returncode,counts=counts,nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest(),traceSha256=hashlib.sha256(raw).hexdigest()),indent=2)+'\n');print(counts);raise SystemExit(not okay)
if __name__=='__main__':main()
