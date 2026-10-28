"""Audit the actual original draw Paragraph: fonts/glyphs and safe UTF16 grapheme ranges."""
import argparse,hashlib,json,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_glyph_sources import font_tables,TAGS
from capture_core_probe import verify_environment,encode_numbers
def main():
    """Execute shared fixture through real public API, capture same-Paragraph diagnostics.
    Pixel/canvas units, owned JSON hashes only; no raw font/table bytes persist. Owner
    thread only; requires installed native wheel and real default GPU with CPU control.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--backend',choices=('gpu','cpu'),default='gpu');a=p.parse_args();a.out.mkdir(exist_ok=False)
    from py_skia_canvas import Canvas,FontLibrary,_native
    native=Path(_native.__file__).resolve();assert native.is_relative_to(Path(sys.prefix).resolve())
    _,env=verify_environment(a.environment);pinned=[]
    for item in env['fontFiles']:
        for face in font_tables(Path(item['path'])):pinned.append({**item,**face})
    cases=[];unresolved=[];invalid=[]
    for item in json.loads(a.fixtures.read_text(encoding='utf-8'))['cases']:
        c=Canvas(item['width'],item['height']);x=c.getContext('2d');objects={'canvas':c,'ctx':x,'fontLibrary':FontLibrary};assert (c.gpu and c.engine['renderer']=='GPU') if a.backend=='gpu' else (not c.gpu and c.engine['renderer']=='CPU')
        x._native.audit_draw_capture(True);x._native.audit_surface_capture(True)
        for op in item['ops']:
            if op['op']=='set':setattr(objects[op['target']],op['name'],op['value'])
            elif op['op']=='call':getattr(objects[op['target']],op['name'])(*op.get('args',[]))
            else:raise ValueError('Unsupported explicit audit operation')
        raw=c.toBufferSync('raw');png=c.toBufferSync('png');(a.out/(item['id']+'.rgba')).write_bytes(raw);(a.out/(item['id']+'.png')).write_bytes(png)
        records=json.loads(x._native.audit_draw_capture(False));surfaces=json.loads(x._native.audit_surface_capture(False));assert surfaces['surfaces']>0 if a.backend=='gpu' else surfaces['surfaces']==0
        actual=[v for v in records if v['operation'] in ('fillText','strokeText','outlineText')];assert actual
        for record in actual:
            length=len(record['layoutText'].encode('utf-16-le'))//2
            for cluster in record['clusters']:
                if cluster['info'] is not None:
                    start,end=cluster['info']['range']
                    if not 0<=start<=end<=length:invalid.append(dict(case=item['id'],cluster=cluster,length=length))
            for run in record['runs']:
                tables={}
                for table in run['font'].pop('tables'):
                    data=table.pop('data');tables[table['tag']]=None if data is None else dict(bytes=len(data),sha256=hashlib.sha256(bytes(data)).hexdigest())
                matches=[dict(path=f['path'],fileSha256=f['sha256'],faceIndex=f['faceIndex']) for f in pinned if f['tables']==tables]
                run['font'].update(tableFingerprints=tables,sourceMatches=matches)
                if len(matches)!=1 or 0 in run['glyphs']:unresolved.append(dict(case=item['id'],operation=record['operation'],font=run['font']['family'],zeroGlyphs=run['glyphs'].count(0),sourceCount=len(matches)))
        cases.append(dict(id=item['id'],engine=c.engine,drawRecords=actual,surfaces=surfaces,rawSha256=hashlib.sha256(raw).hexdigest(),pngSha256=hashlib.sha256(png).hexdigest()))
    control=Canvas(64,48);control.gpu=False;z=control.getContext('2d');z._native.audit_surface_capture(True);z.fillText('CPU',2,20);control.toBufferSync();cpu=json.loads(z._native.audit_surface_capture(False));assert cpu['surfaces']==0
    d=dict(status='ACTUAL_DRAW_GLYPHS_AND_SAFE_RANGES_OBSERVED' if not unresolved and not invalid else 'INCOMPLETE',cases=cases,unresolvedCoverage=unresolved,invalidRanges=invalid,freshCpuControl=cpu,nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest(),fixtureSha256=hashlib.sha256(a.fixtures.read_bytes()).hexdigest(),fontResourcesSha256=env['fontResourcesSha256'],rawFontOrTableBytesPersisted=False,limits=['Actual Python same-Paragraph observation; official A public metrics/RGBA compared separately','UTF16 public grapheme ranges are not fabricated per-glyph UTF8 visitor offsets','System fonts fingerprinted, not redistributed'])
    (a.out/'run.json').write_text(json.dumps(encode_numbers(d),indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8');print(json.dumps(dict(status=d['status'],cases=len(cases),unresolved=unresolved,invalidRanges=len(invalid))));raise SystemExit(bool(unresolved or invalid))
if __name__=='__main__':main()
