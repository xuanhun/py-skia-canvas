"""Standalone CPU deployment witness; no test-runner or Node dependency."""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,shutil,sys
from py_skia_canvas import Canvas,Window,_native

def main():
    """Write CPU backend/actual surface/format evidence into a fresh directory.
    Width/height are pixels, exports are bytes; owner thread only. Any GPU use or
    missing format fails. Window support is recorded as its actual API outcome.
    Optional --no-loader additionally forbids loader/devices/Node discovery.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--no-loader',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=False)
    c=Canvas(160,80);x=c.getContext('2d');x._native.audit_surface_capture(True);assert not c.gpu and c.engine['renderer']=='CPU'
    x.fillStyle='white';x.fillRect(0,0,160,80);x.fillStyle='#3168bf';x.font='20px sans-serif';x.fillText('CPU Canvas',4,35);x.filter='blur(1px)';x.fillRect(20,40,60,20);raw=c.toBufferSync('raw');(a.out/'image.png').write_bytes(c.toBufferSync());formats={fmt:len(c.toBufferSync(fmt)) for fmt in ('png','jpg','webp','raw','pdf','svg')};audit=json.loads(x._native.audit_surface_capture(False));assert not audit['surfaces'] and all(formats.values())
    try:ctypes.CDLL('vulkan-1.dll' if sys.platform=='win32' else 'libvulkan.so.1');loader=True
    except OSError:loader=False
    devices={p:Path(p).exists() for p in ('/dev/dri','/dev/dxg','/dev/nvidia0')}
    if a.no_loader:assert not loader and not any(devices.values()) and shutil.which('node') is None
    try:w=Window(16,16,{'visible':False});window=dict(opened=True);w.close()
    except Exception as e:window=dict(type=type(e).__name__,message=str(e))
    d=dict(status='CPU_RUNTIME_CHECKED',gpu=c.gpu,engine=c.engine,nativeVulkanSurfaces=audit,formats=formats,loaderPresent=loader,deviceNodes=devices,window=window,nativeSha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),rawSha256=hashlib.sha256(raw).hexdigest(),prefix=sys.prefix,cwd=str(Path.cwd()))
    (a.out/'run.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(d))
if __name__=='__main__':main()
