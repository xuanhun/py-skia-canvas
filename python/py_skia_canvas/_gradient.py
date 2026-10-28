"""CanvasGradient facade; original geometry, stops and shader are shared core values."""
from . import _native, _number, _text, _MISSING
from ._arguments import read
from ._text_css import truth
from ._text_api import string


class CanvasGradient:
    """Original shared owner-thread ramp; supports linear, radial and conic constructors.

    Python holds an ID only. Context State clones the original Rc ramp, not stops.
    No native/GPU values move between threads. Source: canvas.js:CanvasGradient/gradient.rs.
    """
    __slots__ = ("_native", "__weakref__")

    def __init__(self, style=_MISSING, *coords):
        """Create original gradient: coordinates/radii in canvas units, conic angle radians.

        Valid style strings are case-insensitive. Missing/unknown style ->original Error
        (RuntimeError subclass); typed geometry errors ->TypeError. No radial validation
        is invented. Source: canvas.js:constructor and gradient.rs three factories.
        """
        if not truth(style):
            style = ""
        if not isinstance(style, str):
            raise TypeError('(style || "").toLowerCase is not a function')
        style = style.lower()
        names = {"linear": ("x1", "y1", "x2", "y2"), "radial": ("x1", "y1", "r1", "x2", "y2", "r2"), "conic": ("theta", "x", "y")}
        if style not in names:
            raise _native.Error('Function is not a constructor (use CanvasRenderingContext2D\'s "createConicGradient", "createLinearGradient", and "createRadialGradient" methods instead)')
        self._native = _native.NativeGradient(style,read('gradient',style,coords))

    def addColorStop(self, *args):
        """Mutate original shared ramp; offset normalized/f32, color CSS string, returns None.

        Owner-only. Offset range checked after original f32 conversion and before color
        parse; RangeError(ValueError)/TypeError messages retained. Missing/null color and
        invalid CSS follow original errors. Full JS object color coercion remains pending.
        Source: gradient.rs:addColorStop/add_color_stop/add_stop.
        """
        self._native.kind()
        offset=read('gradient','addColorStop',args)[0]
        color=args[1] if len(args)>1 else _MISSING
        value=string(color) if isinstance(color,(str,list,tuple,dict)) else None
        try:self._native.stop(offset,value,len(args)>1)
        except TypeError as e:
            if str(e)=='Could not be parsed as a color' and len(args)!=2:raise TypeError('not enough arguments') from None
            raise

    def __repr__(self):
        """Return original CanvasGradient style label; owner-only, RuntimeError if foreign.

        Unitless string, no ramp snapshot. Source: canvas.js custom REPR/gradient.rs:repr.
        """
        return "CanvasGradient (" + self._native.kind() + ")"
