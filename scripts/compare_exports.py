"""Exact public export/structure/RGBA comparison; external PDF rasterizer is audit-only."""
import argparse,hashlib,io,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

def digest(p):
    """Owned test file fingerprint; bytes/SHA only, no renderer tolerance."""
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def main():
    """Compare fresh captures; PDF uses pypdf structure and same Poppler all-page RGBA.
    No PNG-byte shortcut, no alpha-zero mask, no epsilon. Original files stay immutable.
    """
    p=argparse.ArgumentParser();p.add_argument('original',type=Path);p.add_argument('python',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--pdf-tools',type=Path,required=True);p.add_argument('--audit-modules',type=Path,required=True);args=p.parse_args()
    sys.path.insert(0,str(args.audit_modules.resolve()));from pypdf import PdfReader
    args.out.mkdir(exist_ok=False);errors=[];checks=[];a,b=args.original,args.python
    x=json.loads((a/'run.json').read_text(encoding='utf-8'));y=json.loads((b/'run.json').read_text(encoding='utf-8'))
    assert [v['id'] for v in x['cases']]==[v['id'] for v in y['cases']]
    assert len({v['id'] for v in x['cases']})==len(x['cases'])
    assert x['pages']==y['pages'] and x['snapshot']==y['snapshot'];assert (a/'snapshot.raw').read_bytes()==(b/'snapshot.raw').read_bytes()
    def pixels(pa,pb,label):
        """All decoded RGBA channels including RGB at zero alpha, exact dimensions/bytes."""
        ia,ib=Image.open(pa),Image.open(pb);ra,rb=ia.convert('RGBA'),ib.convert('RGBA');okay=ra.size==rb.size and ra.tobytes()==rb.tobytes()
        if not okay:errors.append(label+' RGBA')
        return dict(size=list(ra.size),exactRGBA=okay,originalMode=ia.mode,pythonMode=ib.mode,originalInfo=repr(ia.info),pythonInfo=repr(ib.info))
    def pdf_structure(p):
        """Page boxes/resources/operators/fonts/images, raw decoded streams and all keys.
        Indirect IDs are resolved, cycles labeled; volatile Info CreationDate/ModDate and
        trailer ID excluded explicitly. This is test structure, never rewrites PDF bytes.
        """
        from pypdf.generic import IndirectObject,StreamObject,DictionaryObject,ArrayObject
        def value(v,stack=()):
            if isinstance(v,IndirectObject):
                key=(v.idnum,v.generation)
                if key in stack:return {'cycle':True}
                return value(v.get_object(),stack+(key,))
            if isinstance(v,StreamObject):return {'dict':{str(k):value(w,stack) for k,w in v.items() if k not in ['/Length','/Filter','/DecodeParms']},'decodedSHA256':hashlib.sha256(v.get_data()).hexdigest()}
            if isinstance(v,DictionaryObject):return {str(k):value(w,stack) for k,w in v.items() if k not in ['/Parent','/CreationDate','/ModDate']}
            if isinstance(v,ArrayObject):return [value(w,stack) for w in v]
            if isinstance(v,bytes):return {'bytes':v.hex()}
            return str(v)
        r=PdfReader(p);return dict(pages=[value(page) for page in r.pages],info=value(r.metadata or {}))
    for left,right in zip(x['cases'],y['cases']):
        label=left['id']
        if left!=right:errors.append(dict(case=label,original=left,python=right));continue
        assert {p.name for p in (a/label).iterdir()}=={p.name for p in (b/label).iterdir()}
        for pa in sorted((a/label).iterdir()):
            pb=b/label/pa.name;raw=pa.read_bytes();row=dict(case=label,file=pa.name,original=digest(pa),python=digest(pb),exactBytes=raw==pb.read_bytes());checks.append(row)
            if raw.startswith(b'%PDF'):
                sa,sb=pdf_structure(pa),pdf_structure(pb);row['exactStructure']=sa==sb;row['pages']=len(sa['pages'])
                if sa!=sb:errors.append(label+' PDF structure')
                (args.out/(label+'-'+pa.name+'-structure.json')).write_text(json.dumps(dict(original=sa,python=sb),indent=2)+'\n',encoding='utf-8')
                outputs=[]
                for side,file in [('original',pa),('python',pb)]:
                    prefix=args.out/(label+'-'+pa.name+'-'+side)
                    def linux(p):return '/mnt/'+p.resolve().drive[0].lower()+p.resolve().as_posix()[2:]
                    cmd=['wsl','-e','env','LD_LIBRARY_PATH='+linux(args.pdf_tools/'usr/lib/x86_64-linux-gnu'),linux(args.pdf_tools/'usr/bin/pdftoppm'),'-r','72','-png',linux(file),linux(prefix)]
                    r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert r.returncode==0,r.stdout
                    outputs.append(sorted(args.out.glob(prefix.name+'-*.png')))
                assert len(outputs[0])==len(outputs[1])==len(sa['pages'])
                row['raster']=[pixels(ra,rb,label) for ra,rb in zip(*outputs)]
            elif pa.suffix=='.svg':
                row['exactXML']=ET.canonicalize(raw.decode())==ET.canonicalize(pb.read_text(encoding='utf-8'))
                if not row['exactXML']:errors.append(label+' SVG XML')
            elif raw.startswith((b'\x89PNG',b'\xff\xd8',b'RIFF')):
                row['decoded']=pixels(pa,pb,label)
                if row['decoded']['originalInfo']!=row['decoded']['pythonInfo']:errors.append(label+' image metadata')
            elif not row['exactBytes']:errors.append(label+' raw bytes')
    result=dict(status='EXPORTS_EXACT' if not errors else 'INCOMPLETE',cases=len(x['cases']),files=len(checks),checks=checks,errors=errors,pdfTool=digest(args.pdf_tools/'usr/bin/pdftoppm'),pdfStructurePolicy='Resolved page/resources/decoded stream SHA; exclude volatile Info dates and trailer IDs only',pixelPolicy='Every decoded RGBA byte, including RGB at alpha=0, exact; PDFs all pages Poppler 26.01.0 at 72 DPI',asyncAudit=y.get('asyncAudit'))
    (args.out/'run.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['checks']}));sys.exit(bool(errors))

if __name__=='__main__':main()
