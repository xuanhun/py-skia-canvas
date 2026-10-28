"""Compare original CSS filter f64 descriptors/errors against the actual installed wheel."""
import argparse,hashlib,json,math,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from compare_runs import json_differences
from capture_core_probe import encode_numbers

def main():
    """Write fresh exact parser evidence, owned plain values; no drawing or native policy.
    Source css.js:parseFilter/Percentage/Angle/Size, units CSS px/degrees/f64 amounts.
    Outside cwd/empty PATH/installed wheel required; I/O/malformed input errors propagate.
    """
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','node','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    if os.environ.get('PATH') or Path.cwd().is_relative_to(root):p.error('Run outside workspace with empty PATH')
    from py_skia_canvas import _native,undefined
    from py_skia_canvas._effects import parse_filter
    native=Path(_native.__file__).resolve()
    if not native.is_relative_to(Path(sys.prefix).resolve()):p.error('Requires installed wheel')
    a.out.mkdir(exist_ok=False);inputs=json.loads(a.inputs.read_text(encoding='utf-8'));expected=json.loads(a.node.read_text(encoding='utf-8'))
    def decode(v):
        """Fixture-only nonfinite/undefined tags ->owned values, no units/native refs."""
        if isinstance(v,list):return[decode(x) for x in v]
        if isinstance(v,dict) and '$undefined'in v:return undefined
        if isinstance(v,dict) and '$number'in v:return{'NaN':math.nan,'Infinity':math.inf,'-Infinity':-math.inf,'-0':-0.}[v['$number']]
        return v
    actual=[]
    for item in inputs:
        try:actual.append(dict(value=encode_numbers(parse_filter(decode(item['value'])))))
        except Exception as e:actual.append(dict(error=dict(type=type(e).__name__,message=str(e))))
    differences=json_differences(expected,actual)
    report=dict(status='MATCHED_EFFECT_PARSER_RECORDS' if not differences else 'INCOMPLETE',cases=len(inputs),differences=differences,nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest(),inputsSha256=hashlib.sha256(a.inputs.read_bytes()).hexdigest(),oracleSha256=hashlib.sha256(a.node.read_bytes()).hexdigest(),scope='Exact original CSS filter descriptors/errors; pixel/native checks separate')
    for name,data in [('python.json',actual),('run.json',report)]:
        with (a.out/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,ensure_ascii=True);f.write('\n')
    print(json.dumps(dict(cases=len(inputs),differences=len(differences))));raise SystemExit(bool(differences))

if __name__=='__main__':main()
