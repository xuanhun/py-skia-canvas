"""Actual installed Image EventEmitter contracts, Python callable/warning host mapping."""
import json,sys,warnings
from pathlib import Path
from py_skia_canvas import Image,undefined
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capture_core_probe import encode_numbers
def main():
    """Run shared callback/metadata/error cases, owned values only; no graphics fallback."""
    input,out=map(Path,sys.argv[1:]);cases=[]
    for cfg in json.loads(input.read_text(encoding='utf-8'))['cases']:
        e=Image();calls=[];callbacks={};observations=[]
        def callback(name):
            """Bind explicit undefined return and original event argument recording."""
            def f(*args):calls.append([name,list(args)]);return undefined
            return f
        for name in ('f0','f1','f2','meta'):callbacks[name]=callback(name)
        def enc(v):
            """Encode language identities/callback wrappers before native-free JSON write."""
            if v is e:return {'$self':True}
            if v is undefined:return {'$undefined':True}
            if callable(v):
                for name,f in callbacks.items():
                    if v is f:return {'$callback':name}
                return {'$once':next((name for name,f in callbacks.items() if getattr(v,'listener',None) is f),None)}
            if isinstance(v,(list,tuple)):return [enc(x) for x in v]
            if isinstance(v,dict):return {k:enc(x) for k,x in v.items()}
            return encode_numbers(v)
        def dec(v):
            """Decode explicit ordinary values/callback handles, no renderer changes."""
            if isinstance(v,dict):
                if '$undefined'in v:return undefined
                if '$number'in v:return float(v['$number'])
                if '$callback'in v:return callbacks[v['$callback']]
                return {k:dec(x) for k,x in v.items()}
            if isinstance(v,list):return [dec(x) for x in v]
            return v
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            for op in cfg['ops']:
                try:observations.append(dict(value=enc(getattr(e,op['name'])(*[dec(x) for x in op.get('args',[])]))))
                except Exception as x:observations.append(dict(error=dict(type=type(x).__name__,message=str(x))))
        cases.append(dict(id=cfg['id'],observations=observations,calls=enc(calls),warnings=[dict(name=type(w.message).__name__,message=str(w.message),count=w.message.count,type=w.message.type) for w in caught]))
    out.write_text(json.dumps(dict(cases=cases),ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')
if __name__=='__main__':main()
