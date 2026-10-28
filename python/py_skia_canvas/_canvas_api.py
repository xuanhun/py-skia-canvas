"""Original Canvas construction/dimension facade, one core option factory, no rendering."""
from . import _native,undefined
from ._arguments import double,STRICT
from ._imagery import field,number
from ._text_css import truth

def initialize(canvas,width,height,options):
    """Original option destructuring -> native construction -> width then height setters.
    Canvas-unit sizes, f64 contrast/gamma, GPU truthy flag; None/original range/type errors.
    New owner TLS Canvas, no context until requested. Source canvas.js:constructor.
    """
    contrast=field(options,'textContrast',0);gamma=field(options,'textGamma',1.4);gpu=field(options,'gpu',True)
    canvas._native=_native.NativeCanvas(300,150,contrast,gamma,not truth(gpu));canvas._contexts=[]
    dimension(canvas,'width',width);dimension(canvas,'height',height)

def dimension(canvas,name,value):
    """Original JS Number gate then native finite-number/f32 boundary, reset head only.
    Canvas units, negative/NaN defaults 300/150; invalid native value default bail still
    resets head, STRICT throws before reset. Other pages/direct Contexts remain unchanged.
    Owner only; source canvas.js setters/canvas.rs:set_width/set_height.
    """
    width,height=canvas._native.size();js=number(value);value=300 if name=='width' and (js!=js or js<0) else 150 if name=='height' and (js!=js or js<0) else value
    parsed=double(value)
    if parsed is None:
        if STRICT:raise TypeError('\ufe0fExpected a number for `size` as 1st arg')
    elif name=='width':width=parsed
    else:height=parsed
    canvas._native.set_size(width,height)

def context(canvas,kind):
    """Original loose == '2d' for ordinary strings/array primitives; Context/None/owner error.
    No units/native movement; object host coercion remains G0. Source canvas.js:getContext.
    """
    from ._text_api import string
    matches=kind=='2d' if isinstance(kind,str) else string(kind)=='2d' if isinstance(kind,(list,tuple)) else False
    if not matches:return None
    canvas._native.size();return canvas._contexts[0] if canvas._contexts else canvas.newPage()
