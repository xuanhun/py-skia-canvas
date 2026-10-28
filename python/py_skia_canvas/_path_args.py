"""Original Path2D extension argument boundary only; unique core owns all geometry."""
from . import undefined
from ._arguments import guard,required,double
def effect(path,name,args):
    """Read original effect stages/default seed and return real Path2D/undefined/errors.
    Lengths canvas units, trim fractions/seed unitless; owner only. Source path.rs
    offset/round/jitter/trim and path.js trim. No effect/geometry algorithms here.
    """
    from . import Path2D
    guard(path,'path');values=[];flag=False;rule='nonzero'
    if name=='unwind':pass
    elif name=='simplify':
        rule=args[0] if args else 'nonzero'
        if not isinstance(rule,str) or rule not in ('nonzero','evenodd'):raise TypeError('Expected `fillRule` to be "nonzero" or "evenodd" for 1st arg')
    elif name=='round':values=required(args,('radius',))
    elif name=='offset':
        first=required(args,('dx',));second=required(args,('dy',),2);values=first+second
    elif name=='jitter':
        first=required(args,('segmentLength',),bail=True)
        if first is None:return undefined
        second=required(args,('variance',),2,True)
        if second is None:return undefined
        seed=double(args[2]) if len(args)>2 else None;values=first+second+[0 if seed is None else seed]
    elif name=='trim':
        first=required(args,('begin',),bail=True)
        if first is None:return undefined
        second=required(args,('end',),2,True)
        if second is None:return undefined
        values=first+second;flag=args[2] if len(args)>2 and isinstance(args[2],bool) else False
    return Path2D._from_native(path._native.effect(name,values,flag,rule))

def trim(path,args):
    """Original JS trim overload normalization before native finite-f32 reads.
    Fractions, actual bool invert, Path2D/undefined/original errors; owner-only.
    Source path.js:trim, native path.rs:trim. No clipping/effect implementation.
    """
    from ._imagery import number
    values=list(args);first=number(values[0]) if values else float('nan')
    if len(values)<2 or isinstance(values[1],bool) or not isinstance(values[1],(int,float)):
        if first>0:values.insert(0,0)
        elif first<0:values.insert(1,1)
    for i in range(min(2,len(values))):
        value=number(values[i])
        if value<0:values[i]=max(-1,value)+1
    return effect(path,'trim',values)

def combine(path,args,operation):
    """Original op/interpolate optional-other JS truth gate then native Path/weight reads.
    Weight unitless, geometry canvas units; real Path2D/original TypeError/Error. Owner
    only; source path.js static op/interpolate and path.rs corresponding native functions.
    """
    from . import Path2D
    from ._text_css import truth
    guard(path,'path')
    if not args or not truth(args[0]):raise TypeError('not enough arguments (missing: Path2D as 1st arg)')
    other=args[0]
    if not isinstance(other,Path2D):raise TypeError('Expected a Path2D for 1st arg')
    weight=0
    if operation=='interpolate':weight=required((other,args[1] if len(args)>1 else undefined),('weight',),2)[0]
    elif not isinstance(operation,str):raise TypeError('Expected a string for `pathOp`')
    return Path2D._from_native(path._native.combine(other._native,operation,weight))

def add(path,args):
    """Original addPath path filtering and truthy matrix parsing before native Path read.
    Matrix coefficients unitless/translation canvas units; None/original errors, owner.
    Source path.js:addPath ->toSkMatrix, path.rs:addPath. No geometry copied into Python.
    """
    from . import Path2D,_matrix_args
    from ._text_css import truth
    guard(path,'path');other=args[0] if args else undefined;matrix=args[1] if len(args)>1 else undefined
    values=_matrix_args((matrix,)) if truth(matrix) else [1,0,0,0,1,0,0,0,1]
    if not isinstance(other,Path2D):raise TypeError('Expected a Path2D for 1st arg' if truth(matrix) else 'not enough arguments (missing: Path2D as 1st arg)')
    path._native.add(other._native,values)
