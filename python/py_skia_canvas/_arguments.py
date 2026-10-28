"""Original primitive argument/coercion boundary, no geometry, rendering or font strategy."""
import os,math
from . import _native,undefined
from ._argument_specs import SPECS
from ._transform import _SPACE
STRICT=(os.environ.get('SKIA_CANVAS_STRICT') or '0').strip(_SPACE).lower() not in ('0','false','off')

def double(value):
    """Original finite-f64 primitive/array reader, None for invalid; no native ownership.
    Source utils.rs:_as_double; singleton cycles explicitly unsupported instead of stack overflow.
    """
    visited=set();current=value
    while isinstance(current,(list,tuple)) and len(current)==1:
        if id(current) in visited:raise NotImplementedError('Cyclic singleton numeric arrays are an unsafe upstream profile')
        visited.add(id(current));current=current[0]
    return _native._argument_double(value)

def ordinal(index):
    """Original positive argument ordinal string, no units/ownership/errors; utils.rs:arg_num."""
    return str(index)+('st' if index==1 else 'nd' if index==2 else 'rd' if index==3 else 'th')

def required(args,names,start=1,bail=False):
    """Original _float_args_at count-first/finite-f64-to-f32 reads; names/positions source data.
    Returns owned f64 list (native casts f32 at boundary), None for default bail, TypeError
    for missing/non-bail or STRICT invalid. No context/native values transferred.
    """
    available=max(0,len(args)-(start-1))
    if available<len(names):raise TypeError('not enough arguments (missing: '+', '.join(names[available:])+')')
    values=[]
    for offset,name in enumerate(names):
        value=double(args[start-1+offset])
        if value is None:
            if bail and not STRICT:return None
            raise TypeError(('\ufe0f' if bail else '')+'Expected a number for `'+name+'` as '+ordinal(start+offset)+' arg')
        values.append(value)
    return values

def read(group,name,args):
    """Execute generated original staged argument declarations, list/None/original TypeError.
    Canvas units/radians/weights per original names; no native state or math policy.
    """
    result=[]
    for start,names,bail in SPECS[group][name]['stages']:
        values=required(args,names,start,bail)
        if values is None:return None
        result+=values
    return result

def guard(target,group='context'):
    """Check metadata owner before reading arguments; no units/return or GPU transfer.
    Foreign/ended access ->RuntimeError; original required native this before argument reads.
    """
    target._native.check_owner() if group=='path' else target._native.ensure_context()

def command(target,group,name,args):
    """Dispatch original primitive with validated owned values; None/original native errors.
    Geometry canvas units, angles radians, conic weight unitless. Boolean CCW accepts only
    actual bool as original bool_arg_or. Source context/api.rs/path.rs listed in SPECS.
    """
    guard(target,group)
    values=[] if name in ('beginPath','closePath') else read(group,name,args)
    if values is None:return
    index=5 if name=='arc' else 7 if name=='ellipse' else len(args)
    ccw=args[index] if index<len(args) and isinstance(args[index],bool) else False
    method=target._native.command if group=='path' else target._native.path_command
    method(name,values,ccw)

def rectangle(target,name,args):
    """Original fill/stroke/clear rect argument policy, then unique core drawing; None/errors.
    Canvas units, owner only; source context/api.rs:fillRect/strokeRect/clearRect.
    """
    guard(target);values=read('context',name,args)
    if values is not None:target._native.rect({'fillRect':'fill','strokeRect':'stroke','clearRect':'clear'}[name],*values)

def transform(target,name,args):
    """Original translate/scale/rotate read policy, core retains matrix arithmetic.
    Canvas units/unitless/radians respectively, None/errors, owner only. Source context API.
    """
    guard(target);values=read('context',name,args)
    if values is not None:target._native.matrix(name,values)

def round_rect(target,group,args):
    """Original JS argc/radius parsing precedes original non-bail coordinate reads.
    Canvas units, None/RangeError/TypeError, owner operation only after radius validation.
    Source context.js/path.js:roundRect and css.js:radii; geometry stays original core.
    """
    from . import _round_rect_args
    from ._imagery import argc
    argc(args,4,5)
    radius=(0 if group=='context' else undefined) if len(args)<5 or args[4] is undefined else args[4]
    values=_round_rect_args(*args[:4],radius,reader=lambda:required(args,('x','y','width','height')))
    if values is not None:
        guard(target,group)
        method=target._native.command if group=='path' else target._native.path_command
        method('roundRect',values,False)

def stroke_number(target,name,value):
    """Original optional numeric width/miter and bail dash offset setters; None/errors.
    Width/offset canvas units, miter unitless, native range/State policy retained. Owner only.
    """
    guard(target)
    values=required((value,),(name,),bail=True) if name=='lineDashOffset' else [double(value)]
    if values is not None and values[0] is not None:target._native.stroke_number(name,values[0])

def line_dash(target,args):
    """Original complete-array numeric conversion/finite/nonnegative guard; None/errors.
    Canvas-unit segments, original core handles odd duplication. Source API setLineDash.
    """
    guard(target)
    if not args:raise TypeError('not enough arguments')
    if not isinstance(args[0],(list,tuple)):raise TypeError('Value is not a sequence')
    values=[]
    for value in args[0]:
        number=double(value)
        if number is None:return
        f32=_native._text_width(value)
        if not math.isfinite(f32) or f32<0:return
        values.append(number)
    target._native.line_dash(values)

def contains(target,args):
    """Original staged non-bail Path.contains x then y reads, bool/original errors.
    Canvas units, owner only, no geometry duplication. Source path.rs:contains.
    """
    guard(target,'path');x=required(args,('x',));y=required(args,('y',),2)
    return target._native.contains(x[0],y[0])

def hit(target,args,stroke=False):
    """Original _is_in path/count/rule-first and opt_float_args filtering; bool/errors.
    Coordinates canvas units, owner only; unique core still performs actual hit geometry.
    Source context/api.rs:_is_in, including original four-argument ambiguity and false result.
    """
    from . import Path2D
    guard(target);path=args[0] if args and isinstance(args[0],Path2D) else None
    if path is not None:guard(path,'path')
    elif len(args)==4:raise TypeError('Expected a Path2D for 1st arg')
    rule='nonzero';index=3 if path is not None else 2
    if not stroke and index<len(args):
        rule=args[index]
        if not isinstance(rule,str) or rule not in ('nonzero','evenodd'):raise TypeError('Expected `fillRule` to be "nonzero" or "evenodd" for '+ordinal(index+1)+' arg')
    values=[v for v in (double(v) for v in args[:3]) if v is not None]
    if len(values)!=2:
        if len(args)<2:raise TypeError('not enough arguments')
        return False
    return target._native.hit_path(*values,stroke,rule,None if path is None else path._native)

def paint(target,kind,args):
    """Original fill/clip/stroke positional overloads including explicit undefined.
    Optional Path2D/rule unitless; None or original TypeError, owner before reads.
    Geometry/clip stays original core. Source context/api.rs:fill/clip/stroke.
    """
    from . import Path2D
    guard(target);path=args[0] if args and isinstance(args[0],Path2D) else None
    if kind=='stroke':
        if args and path is None:raise TypeError('Expected a Path2D for 1st arg')
        rule='nonzero'
    else:
        if path is None and len(args)>1:raise TypeError('Expected a Path2D for 1st arg')
        index=1 if path is not None else 0;rule=args[index] if len(args)>index else 'nonzero'
        if not isinstance(rule,str) or rule not in ('nonzero','evenodd'):raise TypeError('Expected `fillRule` to be "nonzero" or "evenodd" for '+ordinal(index+1)+' arg')
    target._native.use_path(kind,rule,None if path is None else path._native)
