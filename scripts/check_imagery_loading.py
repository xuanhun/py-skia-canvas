"""Exact installed-Python vs official Node image loading/events on owned loopback inputs."""
import argparse,asyncio,base64,hashlib,http.server,json,os,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from compare_runs import json_differences

async def python_records(cfg):
    """Execute original public load/Image/Data/event cases on this installed wheel.

    Paths/HTTP/bytes are explicit owned synthetic fixtures, dimensions pixels. Returns
    owned records, original errors are observed. Native decode stays on this owner loop.
    Source imagery.js/urls.js; independent Node oracle script executes same operations.
    """
    import py_skia_canvas as api
    encoded=Path(cfg['png']).read_bytes();raw=Path(cfg['raw']).read_bytes();records=[]
    def info(i):
        """Snapshot owned public dimensions/complete, pixels/unitless; owner errors propagate."""
        return dict(width=i.width,height=i.height,complete=i.complete)
    def err(e):
        """Retain exact error category/message as data; no tolerance or normalization."""
        return dict(type=type(e).__name__,message=str(e))
    def pixels(i):
        """Copy original decoded RGBA bytes into owned list, pixel units; owner only."""
        return list(api.ImageData(i).data)
    image=await api.loadImage(encoded);records.append(dict(case='buffer',**info(image),src=image.src,pixels=pixels(image)))
    image=await api.loadImage(cfg['png']);records.append(dict(case='file',**info(image),src=image.src))
    image=await api.loadImage('data:image/png;base64,'+base64.b64encode(encoded).decode());records.append(dict(case='dataurl',**info(image),pixels=pixels(image)))
    for endpoint in ('/image','/redirect'):
        image=await api.loadImage(cfg['base']+endpoint,{'headers':{'X-Canvas-Probe':'owner'}});records.append(dict(case=endpoint,**info(image),src=image.src,pixels=pixels(image)))
    for source in (b'broken',cfg['missing'],cfg['base']+'/missing'):
        try:await api.loadImage(source);records.append(dict(case='failure',threw=False))
        except Exception as e:records.append(dict(case='failure',threw=True,**err(e)))
    data=await api.loadImageData(raw,8,8);records.append(dict(case='raw',width=data.width,height=data.height,data=list(data.data)))
    data=await api.loadImageData(cfg['raw'],8,8,{'colorType':'rgba'});records.append(dict(case='raw-file',width=data.width,height=data.height,data=list(data.data)))
    image=api.Image();records.append(dict(case='empty',**info(image),src=image.src,onload='undefined' if image.onload is api.undefined else 'object',onerror='undefined' if image.onerror is api.undefined else 'object'))
    try:await image.decode()
    except Exception as e:records.append(dict(case='unset-decode',**err(e)))
    events=[]
    def cb(i):
        """Observe load width, pixels; owner callback, no native objects retained."""
        events.append(i.width)
    image.once('load',cb);image.on('load',cb);image.src=encoded;image.src=Path(cfg['svg']).read_bytes();records.append(dict(case='once-on',events=events))
    events=[];image.onload=lambda i:events.append('property:'+str(int(i.width)));image.onload=False;image.src=encoded;records.append(dict(case='onload-clear',events=events,cleared=image.onload is None))
    events=[];image.onerror=lambda e:events.append(err(e));image.src=b'broken'
    try:await image.decode()
    except Exception as e:records.append(dict(case='broken-src',**info(image),events=events,decode=err(e)))
    events=[];image=api.Image();image.onload=lambda i:events.append(info(i));image.src=cfg['base']+'/slow';image.src=cfg['base']+'/image';decoded=await image.decode();await asyncio.sleep(.25);records.append(dict(case='latest',**info(image),same=decoded is image,events=events))
    records.append(dict(case='complete-decode',same=await image.decode() is image))
    image=api.Image();events=[];image.onerror=lambda e:events.append(err(e));image.src=cfg['base']+'/missing'
    try:await image.decode()
    except Exception as e:records.append(dict(case='http-src-error',**info(image),src=image.src,events=events,decode=err(e)))
    return records

def main():
    """Start bounded byte-only loopback server, collect A and installed Python, exact compare.

    Fresh output only; propagates process/I/O/protocol errors. No font files or native
    GPU resources enter server threads; Node is an explicit separate test oracle only.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--module',type=Path,required=True);p.add_argument('--node',default='/usr/local/bin/node');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.out.resolve()
    if out.exists() or not out.is_relative_to(root/'test-runs'):p.error('Use fresh test-runs directory')
    if os.environ.get('PATH') or Path.cwd().is_relative_to(root):p.error('Installed role requires outside cwd/empty PATH')
    lock=json.loads((root/'docs/upstream-lock.json').read_text(encoding='utf-8'))
    pkg=json.loads((a.module/'package.json').read_text(encoding='utf-8'))
    target='win32-x64' if sys.platform=='win32' else 'linux-x64'
    if pkg['name']!='skia-canvas' or pkg['version']!='3.0.8' or hashlib.sha256((a.module/'lib/skia.node').read_bytes()).hexdigest()!=lock['originalNativeSha256'][target]:p.error('Require fixed official A native bytes')
    import py_skia_canvas as api
    native=Path(api._native.__file__).resolve()
    if not native.is_relative_to(Path(sys.prefix).resolve()):p.error('Requires actual installed wheel')
    out.mkdir();encoded=(root/'tests/assets/rgba-grid.png').read_bytes();svg=(root/'tests/assets/checker.svg').read_bytes()
    requests=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        """Owned byte fixture responder only; no renderer/font/native references."""
        def do_GET(self):
            """Record requested path/header and reply/redirect/error, no external network."""
            requests.append(dict(path=self.path,header=self.headers.get('X-Canvas-Probe')))
            if self.path=='/redirect':self.send_response(302);self.send_header('Location','/image');self.end_headers();return
            if self.path not in ('/image','/slow'):self.send_response(404);self.end_headers();return
            body=svg if self.path=='/slow' else encoded
            if self.path=='/slow':time.sleep(.1)
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):
            """Suppress HTTP console noise; explicit requests list is evidence, returns None."""
            pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    cfg=dict(png=str(root/'tests/assets/rgba-grid.png'),raw=str(root/'tests/assets/rgba-grid.raw'),svg=str(root/'tests/assets/checker.svg'),missing=str(root/'tests/assets/missing-not-an-image.png'),base='http://127.0.0.1:'+str(server.server_port))
    (out/'inputs.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
    args=[a.node,str(root/'tests/oracle/capture-imagery-loading.mjs'),str(a.module),str(out/'inputs.json')]
    try:
        result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=30);(out/'node-stderr.log').write_text(result.stderr,encoding='utf-8');result.check_returncode()
        original=json.loads(result.stdout.split('IMAGERY_LOADING_JSON=',1)[1]);(out/'official.json').write_text(json.dumps(original,indent=2)+'\n',encoding='utf-8')
        official_requests=list(requests)
        current=asyncio.run(python_records(cfg));(out/'python.json').write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
        differences=json_differences(original,current)
        python_requests=requests[len(official_requests):]
        original_headers=sum(item['header']=='owner' for item in official_requests);python_headers=sum(item['header']=='owner' for item in python_requests)
        if original_headers<2 or original_headers!=python_headers:differences.append('Custom header/redirect transport differs from official A')
        report=dict(status='MATCHED_OFFICIAL_LOADING_RECORDS' if not differences else 'INCOMPLETE',cases=len(original),differences=differences,nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest(),officialNativeSha256=hashlib.sha256((a.module/'lib/skia.node').read_bytes()).hexdigest(),argv=args,requests=requests,limits=['Explicit loopback/file/data URL transport and selected load/error events only','Node-specific Sharp/agent/proxy/complete EventEmitter interoperability remains G0','No Node in installed package dependency graph; Node invoked separately as test oracle'])
        (out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=report['status'],cases=len(original),differences=differences)));raise SystemExit(bool(differences))
    finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':main()
