"""Differential public loadImage explicit options on a byte-only loopback server."""
import argparse,asyncio,hashlib,http.server,json,os,subprocess,sys,threading,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from compare_runs import json_differences
def main():
    """Save request/results from actual official A and installed wheel; no external URLs.
    Headers/auth use synthetic test literals. I/O server threads own bytes only, no Skia.
    """
    p=argparse.ArgumentParser();p.add_argument('--module',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--node',default='/usr/local/bin/node');a=p.parse_args();a.out.mkdir(exist_ok=False);r=Path(__file__).resolve().parents[1];body=(r/'tests/assets/rgba-grid.png').read_bytes();requests=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        """Receive explicit fixture traffic only and return PNG/redirect/status bytes."""
        def do_GET(self):self.respond()
        def do_POST(self):self.respond()
        def do_PUT(self):self.respond()
        def do_HEAD(self):self.respond()
        def respond(self):
            """Record explicit semantic fields, including chunked or length payloads."""
            data=b''
            if self.headers.get('Transfer-Encoding','').lower()=='chunked':
                while True:
                    size=int(self.rfile.readline().strip(),16)
                    if not size:self.rfile.readline();break
                    data+=self.rfile.read(size);self.rfile.read(2)
            else:data=self.rfile.read(int(self.headers.get('Content-Length',0)))
            requests.append(dict(method=self.command,path=self.path,case=self.headers.get('X-Canvas-Case'),userAgent=self.headers.get('User-Agent'),auth=self.headers.get('Authorization'),body=data.decode()))
            if self.path.startswith('/redirect'):
                code=int(self.path.rsplit('/',1)[1]);self.send_response(code);self.send_header('Location','/image');self.end_headers();return
            if self.path!='/image':self.send_response(404);self.end_headers();return
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers()
            if self.command!='HEAD':self.wfile.write(body)
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port);cases=[]
    for ident,path,options in [('default','/image',{}),('null','/image',None),('header','/image',{'headers':{'User-Agent':'Canvas explicit'}}),('post','/image',{'method':'POST','body':'canvas-body'}),('put','/image',{'method':'PUT','body':'canvas-body'}),('get-body','/image',{'body':'canvas-body','headers':{'Content-Length':'11'}}),('auth','/image',{'auth':'canvas:probe'}),('override','/wrong',{'path':'/image'}),('missing','/missing',{}),('head','/image',{'method':'HEAD'})]:cases.append(dict(id=ident,path=path,options=options))
    for code in (301,302,303,307,308):cases.append(dict(id='post-'+str(code),path='/redirect/'+str(code),options={'method':'POST','body':'canvas-body'}))
    cases.append(dict(id='url-object',path='/image',options={},urlObject=True))
    for case in cases:
        if case['options'] is not None:case['options'].setdefault('headers',{})['X-Canvas-Case']=case['id']
    cfg=dict(base=base,cases=cases);(a.out/'inputs.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8');args=[a.node,str(r/'tests/oracle/capture-http-options.mjs'),str(a.module),str(a.out/'inputs.json'),str(a.out/'original.json')]
    env=os.environ.copy()
    for key in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy','ALL_PROXY','all_proxy'):env.pop(key,None)
    try:
        with (a.out/'node.log').open('xb') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=60,env=env)
        original_requests=requests[:]
        async def run():
            """Load/decode solely on current owner thread; byte transport may use a worker."""
            from py_skia_canvas import loadImage,ImageData
            records=[]
            for case in cases:
                src=base+case['path'];src=urllib.parse.urlparse(src) if case.get('urlObject') else src
                try:
                    image=await loadImage(src,case['options']);records.append(dict(id=case['id'],width=image.width,height=image.height,pixels=list(ImageData(image).data)))
                except Exception as e:records.append(dict(id=case['id'],error=dict(type=type(e).__name__,message=str(e))))
            return records
        current=asyncio.run(run());original=json.loads((a.out/'original.json').read_text(encoding='utf-8'));diff=json_differences(original,current);diff+=json_differences(original_requests,requests[len(original_requests):]);(a.out/'python.json').write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
        from py_skia_canvas import _native
        d=dict(status='HTTP_OPTIONS_EXACT' if not diff else 'INCOMPLETE',cases=len(cases),differences=diff,requests=requests,nativeSha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest());(a.out/'run.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=d['status'],cases=len(cases),differences=diff)));raise SystemExit(bool(diff))
    finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':main()
