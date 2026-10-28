"""Compare actual installed CSS font parser to separately captured original JS descriptors."""
import argparse,hashlib,json,os,sys
from pathlib import Path

def main():
    """Read fixture inputs/oracle and write fresh evidence; no font files or GPU work.

    Unitless parser metadata, CSS px f64 numbers exact. Empty PATH and outside-workspace
    cwd required. Source css.js:parseFont/Size/Weight, tokenizer references/css. No skip.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--node',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    if os.environ.get('PATH') or Path.cwd().is_relative_to(root):p.error('Run outside workspace with empty PATH')
    from py_skia_canvas import _native,undefined
    from py_skia_canvas._font_css import parse_font
    native=Path(_native.__file__).resolve()
    if not native.is_relative_to(Path(sys.prefix).resolve()):p.error('Requires installed wheel')
    a.out.mkdir(exist_ok=False)
    values=json.loads(a.inputs.read_text(encoding='utf-8'));expected=json.loads(a.node.read_text(encoding='utf-8'))
    def decode(v):
        if isinstance(v,list):return [decode(x) for x in v]
        return undefined if isinstance(v,dict) and v.get('$undefined') else v
    actual=[]
    for v in values:
        item=parse_font(decode(v))
        actual.append({k:x for k,x in item.items() if not(k=='lineHeight' and x is None)} if item is not None else None)
    differences=[{'index':i,'input':values[i],'expected':e,'actual':x} for i,(e,x) in enumerate(zip(expected,actual)) if e!=x]
    assert len(actual)==len(expected)
    for name,data in [('python.json',actual),('run.json',{'status':'MATCHED_PARSER_RECORDS' if not differences else 'INCOMPLETE','cases':len(values),'differences':differences,'nativeSha256':hashlib.sha256(native.read_bytes()).hexdigest(),'inputsSha256':hashlib.sha256(a.inputs.read_bytes()).hexdigest(),'oracleSha256':hashlib.sha256(a.node.read_bytes()).hexdigest(),'scope':'Exact private parser descriptors, separate from rendered font selection and host/prototype contracts'})]:
        with (a.out/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'cases':len(values),'differences':len(differences)}));raise SystemExit(bool(differences))

if __name__=='__main__':main()
