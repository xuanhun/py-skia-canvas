"""Thin Path2D facade; original geometry/effects are executed only in canvas-core."""
import json
from . import _native, _number, _text, _MISSING, _matrix_args, _round_rect_args


def _values(value):
    """Decode original Number tokens from Rust JSON; no units/rounding/native ownership.

    Non-finite values retain IEEE semantics; source: original path.rs JsNumber allocation.
    """
    if isinstance(value, dict):
        if set(value) == {"$number"}:
            return {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": -float("inf")}[value["$number"]]
        return {k: _values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_values(v) for v in value]
    return value


class Path2D:
    """Original owner-thread path with SVG/COW copy, primitives, operations and effects.

    Geometry uses finite numeric canvas units/radians; returned data is Python-owned.
    Foreign access raises RuntimeError; native paths remain in owner TLS. Source: path.js/path.rs.
    Full coercion/CSS string matrix parsing remain tracked separately.
    """
    __slots__ = ("_native", "__weakref__")

    def __init__(self, source=_MISSING, *extra):
        """Create default/SVG/copied original path; source unitless, no return.

        Non-string/non-Path source and invalid constructor SVG retain original empty
        construction behavior. Owner/ID errors propagate; copied data uses original COW.
        """
        if isinstance(source, Path2D):
            self._native = _native.NativePath(source=source._native)
        elif isinstance(source, str):
            self._native = _native.NativePath(svg=_text(source))
        else:
            self._native = _native.NativePath()

    @classmethod
    def _from_native(cls, native):
        """Own a real returned native ID handle; no units/Skia transfer or reconstruction.

        Owner was established by Rust operation. Source: JS neon.wrap(Path2D, native).
        """
        value = object.__new__(cls)
        value._native = native
        return value

    @property
    def d(self):
        """Return original owned SVG text; unitless, owner-only. Source: path.rs:get_d."""
        return self._native.svg()

    @d.setter
    def d(self, svg):
        """Set original SVG; invalid string ->TypeError, previous path retained; owner-only.

        No units/return. Source: path.rs:set_d; uses original parser/rewind/add sequence.
        """
        self._native.check_owner()
        if not isinstance(svg,str):raise TypeError('Expected a string for `svgPath`')
        self._native.svg(_text(svg))

    @property
    def bounds(self):
        """Return original tight bounds dict in canvas units; owner-only, no recomputation.

        Keys left/top/right/bottom/width/height; source: path.rs:bounds.
        """
        return _values(json.loads(self._native.data("bounds")))

    @property
    def edges(self):
        """Return original verb/coordinate rows; canvas units, conic weight unitless.

        Python-owned data, owner-only call; source: path.rs:edges original iterator/index order.
        """
        return _values(json.loads(self._native.data("edges")))

    def contains(self, *args):
        """Original staged x then y numeric reads and original containment; bool/errors.
        Canvas units, owner only; source path.rs:contains, no geometry duplication."""
        from ._arguments import contains
        return contains(self,args)



    def closePath(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:closePath."""
        from ._arguments import command
        return command(self,"path","closePath",args)


    def moveTo(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:moveTo."""
        from ._arguments import command
        return command(self,"path","moveTo",args)


    def lineTo(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:lineTo."""
        from ._arguments import command
        return command(self,"path","lineTo",args)


    def bezierCurveTo(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:bezierCurveTo."""
        from ._arguments import command
        return command(self,"path","bezierCurveTo",args)


    def quadraticCurveTo(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:quadraticCurveTo."""
        from ._arguments import command
        return command(self,"path","quadraticCurveTo",args)


    def conicCurveTo(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:conicCurveTo."""
        from ._arguments import command
        return command(self,"path","conicCurveTo",args)


    def arc(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:arc."""
        from ._arguments import command
        return command(self,"path","arc",args)


    def ellipse(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:ellipse."""
        from ._arguments import command
        return command(self,"path","ellipse",args)


    def arcTo(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:arcTo."""
        from ._arguments import command
        return command(self,"path","arcTo",args)


    def rect(self, *args):
        """Original primitive argument stages, canvas units/radians/weights.
        None/original count/type/STRICT/radius errors, owner only. Source path.js/path.rs:rect."""
        from ._arguments import command
        return command(self,"path","rect",args)


    def roundRect(self, *args):
        """Original JS argc/radii and numeric boundary, omitted radius ignored.
        Canvas units, None/RangeError/TypeError, owner only; source path.js:roundRect."""
        from ._arguments import round_rect
        return round_rect(self,"path",args)


    def addPath(self,*args):
        """Original path/matrix overload order; canvas units, None/original errors, owner.
        Source path.js:addPath/path.rs:addPath, actual append remains unique core."""
        from ._path_args import add
        return add(self,args)

    @staticmethod
    def op(operation=_MISSING,path=_MISSING,*args):
        """Original static boolean overload; real Path2D/original errors, owner only.
        Geometry canvas units; source path.js:op/path.rs:op, no geometry duplication."""
        if not isinstance(path,Path2D):
            if path is _MISSING or path is None:raise TypeError("Cannot read properties of "+('undefined' if path is _MISSING else 'null')+" (reading 'ƒ')")
            raise TypeError('path.ƒ is not a function')
        from ._path_args import combine
        return combine(path,args,operation)

    def difference(self,*args):
        """Original boolean difference overload; real Path2D/original errors, owner only.
        Geometry canvas units; path.js:difference, unique core path operation retained."""
        return Path2D.op("difference",self,*args)

    def intersect(self,*args):
        """Original boolean intersect overload; real Path2D/original errors, owner only.
        Geometry canvas units; path.js:intersect, unique core path operation retained."""
        return Path2D.op("intersect",self,*args)

    def union(self,*args):
        """Original boolean union overload; real Path2D/original errors, owner only.
        Geometry canvas units; path.js:union, unique core path operation retained."""
        return Path2D.op("union",self,*args)

    def xor(self,*args):
        """Original boolean xor overload; real Path2D/original errors, owner only.
        Geometry canvas units; path.js:xor, unique core path operation retained."""
        return Path2D.op("xor",self,*args)

    def complement(self,*args):
        """Original boolean complement overload; real Path2D/original errors, owner only.
        Geometry canvas units; path.js:complement, unique core path operation retained."""
        return Path2D.op("complement",self,*args)

    def interpolate(self,*args):
        """Original instance/class-style interpolation arguments, unitless weight.
        Real Path2D/original errors, owner only; path.js/path.rs:interpolate."""
        from ._path_args import combine
        return combine(self,args,'interpolate')

    def _effect(self, name, coords=(), flag=False, rule="nonzero"):
        """Forward original effect, returning real owner-local path; canvas units/fractions.

        Original errors propagate; no Python geometry. Source: path.rs effect functions.
        """
        return Path2D._from_native(self._native.effect(name, [_number(v, name) for v in coords], flag, rule))

    @staticmethod
    def effect(name=_MISSING, path=_MISSING, *args):
        """Dispatch supported original effect to same implementation; returns path, owner-only.

        Unit/error rules belong to target method. Unknown effect ->TypeError; source: path.js:effect.
        Full dynamic native-method dispatch audit remains pending.
        """
        from ._arguments import guard,double
        from ._text_api import string
        from ._path_args import effect
        if not isinstance(path,Path2D):
            if path is _MISSING or path is None:raise TypeError("Cannot read properties of "+('undefined' if path is _MISSING else 'null')+" (reading 'ƒ')")
            raise TypeError('path.ƒ is not a function')
        guard(path,'path');name=string(name)
        if name in {"round","trim","jitter","offset","simplify","unwind"}:return effect(path,name,args)
        if name=='transform':
            values=[n for n in (double(v) for v in args[0]) if n is not None] if args and isinstance(args[0],(list,tuple)) else []
            return Path2D._from_native(path._native.effect(name,values,False,'nonzero'))
        raise TypeError('this.native[fn] is not a function')

    def simplify(self, *args):
        """Original effect argument stages/defaults, canvas units/fractions/seed unitless.
        Real Path2D/undefined or original count/type/STRICT errors; owner-only.
        Source path.js/path.rs:simplify; no geometry duplicated in facade."""
        from ._path_args import effect
        return effect(self,"simplify",args)

    def unwind(self, *args):
        """Original effect argument stages/defaults, canvas units/fractions/seed unitless.
        Real Path2D/undefined or original count/type/STRICT errors; owner-only.
        Source path.js/path.rs:unwind; no geometry duplicated in facade."""
        from ._path_args import effect
        return effect(self,"unwind",args)

    def offset(self, *args):
        """Original effect argument stages/defaults, canvas units/fractions/seed unitless.
        Real Path2D/undefined or original count/type/STRICT errors; owner-only.
        Source path.js/path.rs:offset; no geometry duplicated in facade."""
        from ._path_args import effect
        return effect(self,"offset",args)

    def transform(self, *matrix):
        """Return original transformed path from DOM/object/6/16 scalars/array; owner-only.

        Canvas units/coefficients, typed/CSS parsing errors. Source: path.js:transform/toSkMatrix.
        """
        return Path2D._from_native(self._native.effect("transform", _matrix_args(matrix), False, "nonzero"))

    def round(self, *args):
        """Original effect argument stages/defaults, canvas units/fractions/seed unitless.
        Real Path2D/undefined or original count/type/STRICT errors; owner-only.
        Source path.js/path.rs:round; no geometry duplicated in facade."""
        from ._path_args import effect
        return effect(self,"round",args)

    def trim(self, *args):
        """Original effect argument stages/defaults, canvas units/fractions/seed unitless.
        Real Path2D/undefined or original count/type/STRICT errors; owner-only.
        Source path.js/path.rs:trim; no geometry duplicated in facade."""
        from ._path_args import trim
        return trim(self,args)

    def jitter(self, *args):
        """Original effect argument stages/defaults, canvas units/fractions/seed unitless.
        Real Path2D/undefined or original count/type/STRICT errors; owner-only.
        Source path.js/path.rs:jitter; no geometry duplicated in facade."""
        from ._path_args import effect
        return effect(self,"jitter",args)

    def points(self, step=1, *extra):
        """Return original sampled x/y lists at canvas-unit step; owner-only/typed errors.

        Uses original jitter(step,0) and edges, with original JS row projection. Source: path.js:points.
        """
        step=1 if step is _MISSING else step
        path=self.jitter(step,0)
        if path is _MISSING:raise TypeError("Cannot read properties of undefined (reading 'edges')")
        return [row[1:][-2:] for row in path.edges if row[1:]]
