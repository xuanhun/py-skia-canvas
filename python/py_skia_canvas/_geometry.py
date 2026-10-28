"""Value-only adaptation of skia-canvas 3.0.8 lib/classes/geometry.js.

DOM values own Python f64 data and have no GPU/thread affinity. Rendering and path
transforms remain in the shared Rust core. Original JS matrix operations/parser
are value-only facade code; original V8 trig is statically bound without a JS runtime.
"""
from array import array
import math
from . import _MISSING
from ._matrix_ops import MatrixOperations, Float64Values
from ._transform import parse_transform_string

_NAMES = tuple(f"m{i}{j}" for i in range(1, 5) for j in range(1, 5))
_ALIASES = dict(zip("abcdef", (0, 1, 4, 5, 12, 13)))
_TWO_D = {0, 1, 4, 5, 12, 13}
_IDENTITY = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)


def _numeric(value):
    """Adapt JS number-only matrix fields to f64, retaining non-finite/-0 values.

    Unitless conversion; TypeError for non-numbers/bools, no native ownership.
    Source: geometry.js:setNumber2D/setNumber3D. Huge Python integer coercion pending.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("Expected number")
    try:return float(value)
    except OverflowError:return -math.inf if value<0 else math.inf


def _field(value, key, default=_MISSING):
    """Read a DOM dictionary/attribute with JS undefined-default semantics; no units.

    Returns the value/default; user attribute errors propagate outside native borrows.
    Source: geometry.js:fromPoint/fromRect/fromMatrix property access/destructuring.
    """
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _record(value):
    """Recognize the supported plain matrix-object facade inputs; bool, no ownership.

    Source: geometry.js:isPlainObject. JS host/proxy/boxed-object coercion audit pending.
    """
    return value is not None and value is not _MISSING and not isinstance(value, (str, int, float, bool, list, tuple, array, bytes, bytearray, memoryview, DOMMatrix))


class DOMPoint:
    """Mutable f64 x/y/z/w value; canvas units for x/y/z, homogeneous w unitless.

    Numeric input profile (including non-finite/-0); owned Python data, any thread.
    Source: geometry.js:DOMPoint, lines 30-84; complete JS coercion remains pending.
    """
    __slots__ = ("x", "y", "z", "w")

    def __init__(self, x=0, y=0, z=0, w=1):
        """Store original defaults; returns None, numeric TypeError; no native resources."""
        self.x, self.y, self.z, self.w = map(_numeric, (x, y, z, w))

    @staticmethod
    def fromPoint(otherPoint):
        """Copy x/y/z/w with original constructor defaults; returns independent DOMPoint.

        Numeric canvas-unit/homogeneous fields; TypeError outside profile, any thread.
        Source: geometry.js:DOMPoint.fromPoint; missing fields become constructor defaults.
        """
        if otherPoint is None:
            raise TypeError("Cannot read properties of null (reading 'x')")
        return DOMPoint(*(_field(otherPoint, k, default) for k, default in zip(("x", "y", "z", "w"), (0, 0, 0, 1))))

    def matrixTransform(self, matrix):
        """Return original f64 transformed point, including the original 2D fast path.

        Canvas-unit geometry/homogeneous w; attribute/type errors propagate, no divide
        by w, no mutation or native ownership. Source: geometry.js:DOMPoint.matrixTransform.
        """
        if matrix.is2D and self.z == 0 and self.w == 1:
            return DOMPoint(self.x * matrix.a + self.y * matrix.c + matrix.e,
                            self.x * matrix.b + self.y * matrix.d + matrix.f, 0, 1)
        return DOMPoint(
            self.x * matrix.m11 + self.y * matrix.m21 + self.z * matrix.m31 + self.w * matrix.m41,
            self.x * matrix.m12 + self.y * matrix.m22 + self.z * matrix.m32 + self.w * matrix.m42,
            self.x * matrix.m13 + self.y * matrix.m23 + self.z * matrix.m33 + self.w * matrix.m43,
            self.x * matrix.m14 + self.y * matrix.m24 + self.z * matrix.m34 + self.w * matrix.m44)

    def toJSON(self):
        """Return owned original x/y/z/w dict; units as fields, any thread, no conversion.

        Source: geometry.js:DOMPoint.toJSON; non-finite tokens belong to test serializers.
        """
        return {k: getattr(self, k) for k in ("x", "y", "z", "w")}


class DOMRect:
    """Mutable numeric rect value, original signed width/height, no normalization.

    All fields/edges in canvas units, Python-owned and thread-independent.
    Source: geometry.js:DOMRect, lines 95-142; JS nonnumeric field coercion pending.
    """
    __slots__ = ("x", "y", "width", "height")

    def __init__(self, x=0, y=0, width=0, height=0):
        """Store original zero defaults; None return, numeric TypeError; any thread."""
        self.x, self.y, self.width, self.height = map(_numeric, (x, y, width, height))

    @staticmethod
    def fromRect(otherRect):
        """Copy numeric dict/rect fields with original zero defaults; return DOMRect.

        Canvas units, independent Python data, any thread; profile TypeError.
        Source: geometry.js:DOMRect.fromRect/constructor.
        """
        if otherRect is None:
            raise TypeError("Cannot read properties of null (reading 'x')")
        return DOMRect(*(_field(otherRect, k, 0) for k in ("x", "y", "width", "height")))

    @property
    def top(self):
        """Original y edge in canvas units; owned scalar, any thread. geometry.js:get top."""
        return self.y

    @property
    def left(self):
        """Original x edge in canvas units; owned scalar, any thread. geometry.js:get left."""
        return self.x

    @property
    def right(self):
        """Original x+width, even if width negative; canvas units. geometry.js:get right."""
        return self.x + self.width

    @property
    def bottom(self):
        """Original y+height, even if height negative; canvas units. geometry.js:get bottom."""
        return self.y + self.height

    def toJSON(self):
        """Return original fields and unnormalized edges as owned dict; no errors/affinity.

        All values canvas units. Source: geometry.js:DOMRect.toJSON.
        """
        return {k: getattr(self, k) for k in ("x", "y", "width", "height", "top", "left", "right", "bottom")}


class DOMMatrix(MatrixOperations):
    """Original column-ordered 4x4 f64 DOM value and sticky is2D flag.

    Unitless coefficients, canvas-unit translations, no native/GPU resources or affinity.
    Supports 6/16 numeric scalars/sequences, same-type copies and matrix-like objects.
    Source: geometry.js:DOMMatrix; operations/parser follow original facade and V8 math.
    """
    __slots__ = ("_items", "_is2d")

    def dump(self):
        """Print original four copied Float64Array columns, return None (JS undefined).
        Unitless matrix coefficients/canvas-unit translation, any thread, no native refs.
        Source geometry.js:dump; Python array repr substitutes Node console.inspect styling.
        Numeric content/order and original matrix remain unchanged.
        """
        print([array('d',self._items[i:i+4]) for i in (0,4,8,12)])

    def __init__(self, init=_MISSING, *extra):
        """Construct independent original storage; returns None, original type/arity errors.

        6-value a/b/c/d/e/f or 16-value column order; all values f64. CSS strings
        use original sequential parser/operations and errors. Any thread.
        Source: geometry.js:constructor/fromMatrix/setNumber2D/setNumber3D.
        """
        self._items, self._is2d = Float64Values(_IDENTITY), True
        if isinstance(init, DOMMatrix) or _record(init):
            result = DOMMatrix.fromMatrix(init)
            self._items, self._is2d = result._items, result._is2d
            return
        if extra:
            init = (init, *extra)
        if init is _MISSING or (isinstance(init, str) and init == ""):
            return
        if isinstance(init, str):
            acc = DOMMatrix()
            for op, values in parse_transform_string(init):
                acc = acc.multiply(DOMMatrix(values)) if op.startswith("matrix") else getattr(acc, op)(*values) if hasattr(acc, op) else acc
            init = acc._items
        if not isinstance(init, (list, tuple, array)) or len(init) not in (6, 16):
            raise TypeError("Expected string, array, or matrix object.")
        indices = (0, 1, 4, 5, 12, 13) if len(init) == 6 else range(16)
        for index, value in zip(indices, init):
            self._set(index, value)

    def _set(self, index, value):
        """Original number-only setter and sticky 3D test; None, TypeError, no affinity.

        Units follow matrix field. Source: geometry.js:setNumber2D/setNumber3D.
        Resetting a 3D field to its identity value does not restore is2D.
        """
        value = _numeric(value)
        if index not in _TWO_D and value != (1 if index in (10, 15) else 0):
            self._is2d = False
        self._items[index] = value

    @property
    def is2D(self):
        """Return original sticky flag; bool, any thread. Source: geometry.js:get is2D."""
        return self._is2d

    @property
    def isIdentity(self):
        """Check all 16 original values, independently of is2D; bool, any thread.

        Exact equality including JS NaN semantics; source: geometry.js:get isIdentity.
        """
        return all(v == i for v, i in zip(self._items, _IDENTITY))

    @staticmethod
    def isMatrix3(matrix):
        """Test original six numeric aliases or DOMMatrix; bool, no units/affinity.

        Source: geometry.js:isMatrix3. Host/proxy/null error details remain unaudited.
        """
        if matrix is None:
            raise TypeError("Cannot read properties of null (reading 'a')")
        return isinstance(matrix, DOMMatrix) or all(isinstance(_field(matrix, k), (int, float)) and not isinstance(_field(matrix, k), bool) for k in _ALIASES)

    @staticmethod
    def isMatrix4(matrix):
        """Test all 16 original numeric fields or DOMMatrix; bool, no units/affinity.

        Source: geometry.js:isMatrix4. Host/proxy/null error details remain unaudited.
        """
        if matrix is None:
            raise TypeError("Cannot read properties of null (reading 'm11')")
        return isinstance(matrix, DOMMatrix) or all(isinstance(_field(matrix, k), (int, float)) and not isinstance(_field(matrix, k), bool) for k in _NAMES)

    @staticmethod
    def fromMatrix(init):
        """Copy original matrix/complete 4x4/partial alias object; returns DOMMatrix.

        Recomputes is2D from values, no shared storage; units as fields, any thread.
        Source: geometry.js:fromMatrix. Invalid primitive ->TypeError; object coercion pending.
        """
        if isinstance(init, DOMMatrix):
            return DOMMatrix(init._items)
        if DOMMatrix.isMatrix4(init):
            return DOMMatrix([_field(init, k) for k in _NAMES])
        if DOMMatrix.isMatrix3(init) or _record(init):
            return DOMMatrix([_field(init, k, default) for k, default in zip(_ALIASES, (1, 0, 0, 1, 0, 0))])
        raise TypeError(f"Expected DOMMatrix, got: '{init}'")

    @staticmethod
    def fromFloat32Array(init):
        """Copy original f32 typed array (Python array('f')); return independent DOMMatrix.

        Units/order as constructor, any thread; wrong type ->original TypeError.
        Source: geometry.js:fromFloat32Array.
        """
        if not isinstance(init, array) or init.typecode != "f":
            raise TypeError("Expected Float32Array")
        return DOMMatrix(init)

    @staticmethod
    def fromFloat64Array(init):
        """Copy original f64 typed array (Python array('d')); return independent DOMMatrix.

        Units/order as constructor, any thread; wrong type ->original TypeError.
        Source: geometry.js:fromFloat64Array.
        """
        if not isinstance(init, array) or init.typecode != "d":
            raise TypeError("Expected Float64Array")
        return DOMMatrix(init)

    def transformPoint(self, point):
        """Return original full f64 point product, preserving operation order/no w divide.

        Canvas units and homogeneous w; input numeric DOMPoint/dict fields required;
        attribute/arithmetic errors propagate, any thread. Source: geometry.js:transformPoint.
        """
        x, y, z, w = (_field(point, k) for k in ("x", "y", "z", "w"))
        v = self._items
        return DOMPoint(v[0]*x + v[4]*y + v[8]*z + v[12]*w,
                        v[1]*x + v[5]*y + v[9]*z + v[13]*w,
                        v[2]*x + v[6]*y + v[10]*z + v[14]*w,
                        v[3]*x + v[7]*y + v[11]*z + v[15]*w)

    def toFloat32Array(self):
        """Return original independent f32 snapshot as array('f'); units/order as fields.

        Retains IEEE rounding/non-finite/-0; any thread. Source: geometry.js:toFloat32Array.
        """
        return array("f", self._items)

    def toFloat64Array(self):
        """Return original independent f64 snapshot: array('d'), or list after singular inverse.

        No units conversion/affinity/errors; original typed/plain slice type retained.
        Source: geometry.js:toFloat64Array/invertSelf.
        """
        return array("d", self._items) if isinstance(self._items, Float64Values) else list(self._items)

    def toJSON(self):
        """Return all original aliases/16 fields/flags as owned dict, no affinity/errors.

        Coefficients unitless, translations canvas units. Source: geometry.js:toJSON.
        """
        return {k: getattr(self, k) for k in (*_ALIASES, *_NAMES, "is2D", "isIdentity")}

    def clone(self):
        """Return original independent copy with is2D recomputed; no units conversion.

        Any thread; source: geometry.js:clone/constructor/fromMatrix.
        """
        return DOMMatrix(self)


def _matrix_property(index):
    """Create equivalent field/alias accessors, units as field; Python data only.

    Setter TypeError delegated to _set. Source: geometry.js:DOMMatrix m11..f accessors.
    """
    def get(self):
        """Return original field scalar, no units conversion/affinity/errors."""
        return self._items[index]
    def set_(self, value):
        """Store original field scalar with sticky flag; see DOMMatrix._set contract."""
        self._set(index, value)
    return property(get, set_)


for _name, _index in (*((name, index) for index, name in enumerate(_NAMES)), *_ALIASES.items()):
    setattr(DOMMatrix, _name, _matrix_property(_index))


def to_sk_matrix(values):
    """Original DOM-to-Skia order and native finite-f64 filtering; owned scalar list.

    Coefficients unitless, translation canvas units. Context ignores invalid filtered
    arity; Path2D.transform rejects it, addPath uses identity. Source: geometry.js:toSkMatrix,
    utils.rs:opt_matrix_arg/floats_in/_as_double. No native data or drawing policy.
    """
    if len(values) != 1 and len(values) < 6:
        raise TypeError("not enough arguments")
    try:
        m = DOMMatrix(*values)
    except (TypeError, SyntaxError) as error:
        raise TypeError("Invalid transform matrix argument(s): " + type(error).__name__ + ": " + str(error)) from None
    return [v for v in (m.a, m.c, m.e, m.b, m.d, m.f, m.m14, m.m24, m.m44) if math.isfinite(v)]


def from_sk_matrix(sk_matrix):
    """Original 9-element Skia-to-16-element DOM mapping; independent DOMMatrix.

    Units as matrix, no native reference/affinity. Source: geometry.js:fromSkMatrix.
    """
    a, b, c, d, e, f, p0, p1, p2 = sk_matrix
    return DOMMatrix([a, d, 0, p0, b, e, 0, p1, 0, 0, 1, 0, c, f, 0, p2])
