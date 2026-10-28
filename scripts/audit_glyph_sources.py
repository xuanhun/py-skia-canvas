"""Observe original measurement glyphs and match selected SFNT table SHA to pinned files.

Diagnostic only. All raw table/font bytes stay in memory; only hashes/metadata persist.
"""
import argparse,hashlib,json,os,struct,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capture_core_probe import verify_environment,encode_numbers,descriptor
from compare_runs import json_differences

TAGS=('head','name','cmap','OS/2')

def font_tables(path):
    """Read original SFNT/TTC directory and hash selected table bytes, not copy fonts.

    Offsets/lengths bytes, returns per-face table identities. Reject malformed bounds;
    pure file metadata inspection, no font matching/shaping policy or native ownership.
    Source: observed Typeface.copy_table_data tags and OpenType SFNT directory layout.
    """
    data=path.read_bytes()
    def u16(pos):return struct.unpack_from('>H',data,pos)[0]
    def u32(pos):return struct.unpack_from('>I',data,pos)[0]
    if len(data)<12:raise ValueError('Truncated SFNT')
    if data[:4]==b'ttcf':
        count=u32(8)
        if 12+count*4>len(data):raise ValueError('Truncated TTC directory')
        offsets=[u32(12+i*4) for i in range(count)]
    else:offsets=[0]
    faces=[]
    for face,offset in enumerate(offsets):
        if offset+12>len(data):raise ValueError('Invalid SFNT face offset')
        count=u16(offset+4)
        if offset+12+count*16>len(data):raise ValueError('Truncated table directory')
        tables={}
        for i in range(count):
            p=offset+12+i*16;tag=data[p:p+4].decode('ascii');start,length=u32(p+8),u32(p+12)
            if start+length>len(data):raise ValueError('Invalid SFNT table bounds')
            if tag in TAGS:tables[tag]={'bytes':length,'sha256':hashlib.sha256(data[start:start+length]).hexdigest()}
        faces.append({'faceIndex':face,'tables':{tag:tables.get(tag) for tag in TAGS}})
    return faces

def python_observations(fixture):
    """Run the same explicit fallback fixture on installed wheel, owner thread only.

    Text/width units original Canvas API; returns owned diagnostic values. It does not
    replace any rendering or selection rule. Temporary table bytes are consumed by caller.
    """
    import py_skia_canvas as api
    cases=[]
    for item in fixture['cases']:
        canvas=api.Canvas(item['width'],item['height']);ctx=canvas.getContext('2d');objects={'canvas':canvas,'ctx':ctx,'fontLibrary':api.FontLibrary};observed=None
        for op in item['ops']:
            if op['op']=='set':setattr(objects[op['target']],op['name'],op['value'])
            elif op['op']=='call':
                args=op.get('args',[]);result=getattr(objects[op['target']],op['name'])(*args)
                if op['name']=='measureText' and op.get('save')=='metrics':
                    text=args[0];width=api._native._text_width(args[1] if len(args)>1 else api.undefined)
                    observed={'id':item['id'],'metrics':dict(result._values),'glyphs':json.loads(ctx._native.audit_glyphs(text,width))}
            else:raise ValueError('Unsupported audit fixture operation')
        if observed is None:raise ValueError('No declared metrics observation')
        cases.append(encode_numbers(observed))
    return cases

def main():
    """Create fresh selected glyph/table evidence or exact cross-binding comparison.

    Font/table hashes are identities, glyph0 remains a missing-coverage finding; neither
    missing resources nor equality with tofu is silently promoted to font acceptance.
    """
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--role',choices=('node','python'));p.add_argument('--module',type=Path);p.add_argument('--fixtures',type=Path);p.add_argument('--environment',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--compare',type=Path);p.add_argument('--oracle',type=Path)
    a=p.parse_args();a.out.mkdir(exist_ok=False);root=Path(__file__).resolve().parents[1]
    if a.compare:
        left=json.loads((a.compare/'run.json').read_text(encoding='utf-8'));right=json.loads((a.fixtures/'run.json').read_text(encoding='utf-8'))
        differences=json_differences(left['cases'],right['cases'])
        if left['fontResourcesSha256']!=right['fontResourcesSha256']:differences.append('Font environment changed')
        if left['fixtureSha256']!=right['fixtureSha256']:differences.append('Fixture changed')
        if a.oracle:
            oracle=json.loads((a.oracle/'run.json').read_text(encoding='utf-8'))
            if oracle['role']!='node-oracle' or oracle['status']!='ORACLE_CAPTURED':raise ValueError('Require original A capture')
            if oracle['fixtureSha256']!=left['fixtureSha256'] or oracle['environment']['fontResourcesSha256']!=left['fontResourcesSha256']:raise ValueError('Original A environment/fixture changed')
            original=[{'id':c['id'],'metrics':c['observations']['metrics']} for c in oracle['cases']]
            measured=[{'id':c['id'],'metrics':c['metrics']} for c in left['cases']]
            differences.extend(json_differences(original,measured))
        d={'status':'MATCHED_GLYPH_RECORDS' if not differences else 'INCOMPLETE','differences':differences,'cases':len(left['cases']),'officialAMetricsCompared':a.oracle is not None,'unresolvedCoverage':left['unresolvedCoverage'],'scope':'Selected original measurement-layout glyph/font identities; official A public metrics compared when supplied, separate from official-A private glyph introspection and full font acceptance'}
        (a.out/'run.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(d));raise SystemExit(bool(differences))
    if not all((a.role,a.fixtures,a.environment)):p.error('Require role/fixtures/environment')
    _,environment=verify_environment(a.environment)
    pinned=[]
    for item in environment['fontFiles']:
        for face in font_tables(Path(item['path'])):pinned.append({**item,**face})
    fixture=json.loads(a.fixtures.read_text(encoding='utf-8'))
    if a.role=='node':
        if a.module is None:p.error('Node role requires explicit development module')
        args=['/usr/local/bin/node',str(root/'tests/oracle/audit-glyphs.mjs'),str(a.module),str(a.fixtures)]
        result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=60)
        (a.out/'stderr.log').write_text(result.stderr,encoding='utf-8');result.check_returncode()
        marker='GLYPH_AUDIT_JSON=';raw=result.stdout.split(marker,1)
        if len(raw)!=2:raise ValueError('Missing diagnostic output')
        cases=json.loads(raw[1]);native=a.module/'lib/skia.node'
    else:
        if os.environ.get('PATH') or Path.cwd().is_relative_to(root):p.error('Python role requires empty PATH and outside-workspace cwd')
        from py_skia_canvas import _native
        native=Path(_native.__file__).resolve()
        if not native.is_relative_to(Path(sys.prefix).resolve()):p.error('Python role requires installed wheel')
        args=[sys.executable,'-I',str(Path(__file__).resolve()),*sys.argv[1:]];cases=python_observations(fixture)
    unresolved=[]
    for case in cases:
        missing=0;unmapped=0
        for run in case['glyphs']['runs']:
            missing+=sum(g==0 for g in run['glyphs'])
            tables={}
            for table in run['font'].pop('tables'):
                values=table.pop('data');tables[table['tag']]=None if values is None else {'bytes':len(values),'sha256':hashlib.sha256(bytes(values)).hexdigest()}
            run['font']['tableFingerprints']=tables
            matches=[{'path':f['path'],'fileSha256':f['sha256'],'faceIndex':f['faceIndex']} for f in pinned if f['tables']==tables]
            run['font']['sourceMatches']=matches
            if len(matches)!=1:unmapped+=1
        case['coverage']={'zeroGlyphs':missing,'nonuniqueSourceRuns':unmapped,'status':'MISSING_GLYPHS' if missing else 'UNMAPPED_SOURCE' if unmapped else 'SELECTED_GLYPHS_COVERED'}
        if missing or unmapped:unresolved.append({'id':case['id'],**case['coverage']})
    d={'status':'SELECTED_GLYPH_SOURCES_OBSERVED','role':a.role,'fontResourcesSha256':environment['fontResourcesSha256'],'nativeSha256':hashlib.sha256(native.read_bytes()).hexdigest(),'fixtureSha256':hashlib.sha256(a.fixtures.read_bytes()).hexdigest(),'argv':args,'cases':cases,'unresolvedCoverage':unresolved,'rawFontOrTableBytesPersisted':False,'limits':['Measurement-layout visitor of shared core B/Python, not official A private Typeface introspection','Selected SFNT table identity matches pinned files, not complete glyph-source/font-license/platform audit','Glyph0 or unmapped fonts are missing coverage, not silently skipped/passed']}
    (a.out/'run.json').write_text(json.dumps(d,indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':d['status'],'cases':len(cases),'unresolvedCoverage':unresolved,'rawFontOrTableBytesPersisted':False}))

if __name__=='__main__':main()
