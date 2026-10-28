"""Original CanvasPattern/CanvasTexture facade; rendering and shared stamps live in core."""
import math
from . import _native,undefined
from ._imagery import Image,ImageData,argc,field
from ._text_css import truth
from ._geometry import to_sk_matrix

class CanvasPattern:
    """Original shared owner-local pattern; image/data/vector content snapshot, ID only.
    Dimensions canvas/pixel units as source, setTransform shared by State aliases.
    Source canvas.js:CanvasPattern; errors original repetition/source and owner errors.
    """
    __slots__=('_native','__weakref__')
    def __init__(self,canvas=undefined,src=undefined,repeat=undefined,*extra):
        """Create original source pattern; repeat string/null (absent is original error).
        Returns pattern; no callbacks under native borrow. Source canvas.js constructor.
        """
        from . import Canvas
        if not isinstance(src,(Image,ImageData,Canvas)):raise _native.Error('CanvasPatterns require a source Image or a Canvas')
        idx=4 if isinstance(src,Image) else 2
        if repeat is undefined:raise TypeError('not enough arguments: expected a string for `repetition` as '+str(idx)+('th' if idx==4 else 'nd')+' arg')
        if repeat is None:repeat=''
        elif not isinstance(repeat,str):raise TypeError('Expected a string for `repetition`')
        if isinstance(src,Image):self._native=_native.NativePattern.image(src._native,canvas.width,canvas.height,repeat)
        elif isinstance(src,Canvas):src.getContext('2d');self._native=_native.NativePattern.canvas(src._native,repeat)
        else:self._native=_native.NativePattern.pixels(bytes(src.data),src.width,src.height,src.colorType,src.colorSpace,repeat)
    def setTransform(self,*values):
        """Set original shared matrix, coefficients unitless/translation canvas units.
        Owner-only ->None/original DOM/type/owner errors. Source pattern.js/canvas.js method.
        """
        self._native.transform(to_sk_matrix(values))
    def __repr__(self):
        """Return original pattern representation; owned text/owner error, source canvas.js REPR."""
        return 'CanvasPattern ('+self._native.kind()+')'

class CanvasTexture:
    """Original shared pattern of lines/path, ID-only owner handle; no shader math here.
    Source canvas.js:CanvasTexture and shared texture.rs:new/mix_into.
    """
    __slots__=('_native','__weakref__')
    def __init__(self,*args):
        """Create original spacing/options overload. Lengths canvas units, angle radians.
        Defaults depend on optional Path2D, outline JS truth; returns object or original
        argc/type/number/owner errors. Parsing happens before native owner borrow.
        """
        from . import Path2D
        argc(args,1);spacing=args[0];options=args[1] if len(args)>1 else undefined
        path=field(options,'path');color=field(options,'color');angle=field(options,'angle');line=field(options,'line');cap=field(options,'cap','butt');outline=field(options,'outline',False);offset=field(options,'offset',0)
        if path is not undefined and not isinstance(path,Path2D):raise TypeError('Expected a Path2D object for `path`')
        native_path=path._native if isinstance(path,Path2D) else None
        if line is undefined or line is None:line=0 if native_path else 1
        if angle is undefined or angle is None:angle=0 if native_path else -math.pi/4
        def num(v,name):
            """Original optional-float validation, f64->f32, unit inherited; TypeError."""
            n=_native._text_width(v)
            if n is None:raise TypeError('Expected a number for `'+name+'`')
            return n
        def pair(v,name):
            """Original array concat/slice or scalar duplication, canvas units; TypeError."""
            values=(list(v)+list(v))[:2] if isinstance(v,(list,tuple)) else [v,v]
            vals=[_native._text_width(x) for x in values]
            if len(vals)!=2 or any(x is None for x in vals):raise TypeError('Expected a number or array with 2 numbers for `'+name+'`')
            return tuple(vals)
        line=num(line,'line')
        if not isinstance(cap,str):raise TypeError('Expected a string for `cap`')
        if cap.lower() not in ('butt','square','round'):raise TypeError('Expected "butt", "square", or "round" for `cap`')
        angle=num(angle,'angle')
        self._native=_native.NativeTexture(native_path,color if isinstance(color,str) else None,line,cap,angle,truth(outline),pair(spacing,'spacing'),pair(offset,'offset'))
    def __repr__(self):
        """Original texture representation, owned text/owner error; source canvas.js REPR."""
        return 'CanvasTexture ('+self._native.kind()+')'

def install(cls):
    """Install original createPattern/createTexture wrappers, owner thread checked, no drawing.
    Return native shared resources, source context.js and canvas.js constructors.
    """
    def createPattern(self,src=undefined,repetition=undefined,*extra):
        """Original CanvasPattern(this.canvas,...) factory, unitless repeat/canvas source units.
        Returns pattern or source/repeat/owner error; no renderer or ownership transfer.
        """
        self._native.ensure_context();return CanvasPattern(self.canvas,src,repetition,*extra)
    def createTexture(self,*args):
        """Original texture factory, canvas units/radians; object or original errors.
        Context checked, texture retains no Canvas reference. Source context.js:createTexture.
        """
        self._native.ensure_context();return CanvasTexture(*args)
    cls.createPattern=createPattern;cls.createTexture=createTexture
