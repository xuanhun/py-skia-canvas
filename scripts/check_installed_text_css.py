"""Compare actual installed text CSS parser/value results/errors to original JS records."""
import argparse,hashlib,json,math,os,sys
from pathlib import Path

def main():
    """Write fresh exact parser evidence, no font files/rendering or numeric tolerance.

    Units are original raw/px f64 or unitless flags/tags. Requires outside-workspace
    cwd, empty PATH and installed wheel; Source css.js spacing/stretch/variant/decoration, context.js !!.
    """
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','node','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    if os.environ.get('PATH') or Path.cwd().is_relative_to(root):p.error('Run outside workspace with empty PATH')
    from py_skia_canvas import _native,undefined
    from py_skia_canvas import _text_css as css
    native=Path(_native.__file__).resolve()
    if not native.is_relative_to(Path(sys.prefix).resolve()):p.error('Requires installed wheel')
    a.out.mkdir(exist_ok=False);inputs=json.loads(a.inputs.read_text(encoding='utf-8'));expected=json.loads(a.node.read_text(encoding='utf-8'))
    def decode(v):
        if isinstance(v,list):return [decode(x) for x in v]
        if isinstance(v,dict) and '$undefined' in v:return undefined
        if isinstance(v,dict) and '$number' in v:return {'NaN':math.nan,'Infinity':math.inf,'-Infinity':-math.inf,'-0':-0.}[v['$number']]
        return v
    def encode(v):
        if v is undefined:return {'$undefined':True}
        if isinstance(v,css._Inherited):return {'$function':True} if v.function else {'$prototype':'Object'}
        if isinstance(v,float):
            if not math.isfinite(v):return {'$number':'NaN' if math.isnan(v) else 'Infinity' if v>0 else '-Infinity'}
            if v==0 and math.copysign(1,v)<0:return {'$number':'-0'}
        if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
        if isinstance(v,list):return [encode(x) for x in v]
        return v
    actual=[]
    for item in inputs:
        try:actual.append({'value':encode(getattr(css,item['kind'])(decode(item['value'])))})
        except Exception as e:actual.append({'error':{'type':type(e).__name__,'message':str(e)}})
    assert len(actual)==len(expected)
    differences=[{'index':i,'input':inputs[i],'expected':e,'actual':v} for i,(e,v) in enumerate(zip(expected,actual)) if e!=v]
    for name,data in [('python.json',actual),('run.json',{'status':'MATCHED_TEXT_PARSER_RECORDS' if not differences else 'INCOMPLETE','cases':len(inputs),'differences':differences,'nativeSha256':hashlib.sha256(native.read_bytes()).hexdigest(),'inputsSha256':hashlib.sha256(a.inputs.read_bytes()).hexdigest(),'oracleSha256':hashlib.sha256(a.node.read_bytes()).hexdigest(),'scope':'Exact language parser/error records; native parameter and font/GPU behavior are separate checks'})]:
        with (a.out/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'cases':len(inputs),'differences':len(differences)}));raise SystemExit(bool(differences))

if __name__=='__main__':main()
