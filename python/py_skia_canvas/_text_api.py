"""Original ordinary context.js toString boundary for text measurement; no layout."""
import math
from . import _text,undefined
from ._transform import number_string

def string(value):
    """Original new String(value).toString for ordinary primitive/array/object inputs.

    Returns owned Rust-compatible string; no units/native handles. Numbers use f64,
    arrays join with comma and null/undefined empty items. Custom host/valueOf/Proxy
    contracts and extreme shortest-string audit remain pending. Source context.js:14.
    """
    active=set()
    def convert(v):
        """Stringify ordinary language values only, before native borrow."""
        if isinstance(v,str):return v
        if v is undefined:return 'undefined'
        if v is None:return 'null'
        if isinstance(v,bool):return 'true' if v else 'false'
        if isinstance(v,(int,float)):
            try:n=float(v)
            except OverflowError:n=-math.inf if v<0 else math.inf
            return number_string(n)
        if isinstance(v,(list,tuple)):
            if id(v) in active:return ''
            active.add(id(v))
            try:return ','.join('' if x is None or x is undefined else convert(x) for x in v)
            finally:active.remove(id(v))
        missing=object();method=v.get('toString',missing) if isinstance(v,dict) else getattr(v,'toString',missing)
        if method is missing:return '[object Object]'
        for name in ('toString','valueOf'):
            method=v.get(name,missing) if isinstance(v,dict) else getattr(v,name,missing)
            if callable(method):
                result=method()
                if result is None or result is undefined or isinstance(result,(str,bool,int,float)):return convert(result)
        raise TypeError('Cannot convert object to primitive value')
    return _text(convert(value))

def draw(target,args,stroke=False):
    """Original fillText/strokeText String ->x ->y ->optional-width reads, then core.
    Positions/maxWidth canvas units; None or original count/type/STRICT errors. An invalid
    width suppresses the whole draw in ordinary mode; null width is numeric zero.
    Owner only; source context.js:246/250 and context/api.rs:_draw_text. No layout policy.
    """
    from ._arguments import guard,required,double,STRICT
    text=string(args[0] if args else undefined);guard(target)
    x=required(args,('x',),2,True)
    if x is None:return
    y=required(args,('y',),3,True)
    if y is None:return
    width=double(args[3]) if len(args)>3 else None
    if len(args)>3 and args[3] is not undefined and width is None:
        if STRICT:raise TypeError('\ufe0fExpected a number for `width` as 4th arg')
        return
    target._native.text(text,x[0],y[0],stroke,width)

def color(value):
    """Original color_in object .toString only, returns str/None or callback exception.
    CSS unitless, no valueOf fallback/stringifying non-string callback result. Runs before
    native borrow; owner checked by caller. Source original utils.rs:color_in.
    """
    if isinstance(value,(list,tuple)):return string(value)
    method=value.get('toString') if isinstance(value,dict) else getattr(value,'toString',None)
    result=method() if callable(method) else None
    return _text(result) if isinstance(result,str) else None

def outline(target,args):
    """Original outlineText String and exactly-two-argument width overload, core Path.
    Width canvas units; Path2D/undefined or original STRICT/count/owner errors. Extra
    geometry arguments make original native width absent. Owner-only original layout.
    Source context.js:254 and context/api.rs:outlineText, no font/shaping duplication.
    """
    from . import Path2D
    from ._arguments import guard,required
    text=string(args[0] if args else undefined);guard(target);width=None
    if len(args)==2:
        values=required(args,('width',),2,True)
        if values is None:return undefined
        width=values[0]
    return Path2D._from_native(target._native.outline(text,width))
