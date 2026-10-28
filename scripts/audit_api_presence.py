"""Installed Python runtime presence for every frozen ledger entry; never promotes semantic parity."""
import inspect,json,sys
from pathlib import Path
import py_skia_canvas as api

def main():
    """Inspect real resources and class descriptors, record absent methods/constructor profiles.
    No empty stubs or drawing fallback; actual shape only, not full overload/host verification.
    """
    source,out=map(Path,sys.argv[1:]);ledger=json.loads(source.read_text());c=api.Canvas(16,12);x=c.getContext('2d')
    objects=dict(Canvas=c,CanvasRenderingContext2D=x,CanvasGradient=x.createLinearGradient(0,0,1,1),CanvasPattern=x.createPattern(c,'repeat'),CanvasTexture=x.createTexture(8),Path2D=api.Path2D(),DOMMatrix=api.DOMMatrix(),DOMPoint=api.DOMPoint(),DOMRect=api.DOMRect(),Image=api.Image(),ImageData=api.ImageData(1,1),TextMetrics=x.measureText('x'),App=api.App,Window=api.Window,FontLibrary=api.FontLibrary)
    rows=[]
    for entry in ledger['entries']:
        owner,name,kind,scope=[entry[k] for k in ('owner','name','kind','scope')];obj=getattr(api,owner) if scope=='static' else objects.get(owner,getattr(api,owner,None))
        row=dict(id=entry['id'],owner=owner,name=name,kind=kind,scope=scope,present=False)
        if kind=='construct':
            row.update(present=inspect.isclass(getattr(api,owner,None)),profile='singleton has no public constructor' if owner in ('App','FontLibrary') else 'direct Context(Canvas) tested against official A' if owner=='CanvasRenderingContext2D' else 'constructor overload semantics require scoped evidence')
        elif kind=='function' or scope=='module':row['present']=callable(getattr(api,name,None))
        else:
            try:value=inspect.getattr_static(obj,name)
            except AttributeError:
                try:value=getattr(obj,name)
                except AttributeError:value=None
                else:row['present']=True
            else:
                row['present']=True
                if isinstance(value,property) and kind in ('get','set'):row['present']=getattr(value,'fget' if kind=='get' else 'fset') is not None
        rows.append(row)
    d=dict(status='PYTHON_API_PRESENCE_CAPTURED',exports={e['name']:hasattr(api,e['name']) for e in ledger['exports']},entries=rows,limits=['Presence is not signature/default/exception/coercion/ownership/overload compatibility','Singleton constructors require explicit source interpretation','Window inspected as class, actual live behavior tested separately'])
    out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(entries=len(rows),present=sum(v['present'] for v in rows),exports=d['exports'])))

if __name__=='__main__':main()
