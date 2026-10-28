"""Original geometry.js matrix operation order, defaults, sharing and return values.

Value-only JS facade adaptation, independent of renderer/GPU ownership. Trigonometry
uses the pinned original V8 IEEE functions rather than platform libm approximations.
"""
import math
from . import _MISSING, _native
from ._transform import string_number, fixed_string, number_string

class Float64Values(list):
    """Mark original Float64Array storage vs singular inverse's plain Array.

    Owned f64 list marker only; original map/slice output types differ. No native data.
    """
    __slots__ = ()

_RAD = math.pi / 180
_DEG = 180 / math.pi

def _matrix():
    """Resolve original concrete DOMMatrix factory after module initialization; no units."""
    from ._geometry import DOMMatrix
    return DOMMatrix

def _number(value):
    """Original typeof number test, excluding Python bool; bool result, any thread."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def _zero(value):
    """Original strict numeric zero comparison; bool, no coercion/ownership or units."""
    return _number(value) and value == 0

def _coerce(value):
    """JS arithmetic primitive coercion; f64, no units, any thread.

    Source: geometry.js numeric operators. Missing/null/bool/numeric strings supported;
    host/valueOf/array object coercion remains explicit TypeError outside this profile.
    """
    if value is _MISSING: return math.nan
    if value is None: return 0.
    if isinstance(value, (int, float)): return float(value)
    if isinstance(value, str): return string_number(value)
    raise TypeError("Object numeric coercion is not bound yet")

def _instance(values):
    """Original newInstance: share array and reset is2D=true, without revalidation.

    Returns DOMMatrix with original alias behavior, no native resources/affinity.
    Source: geometry.js:newInstance. Normal operations replace array with owned product.
    """
    value = object.__new__(_matrix()); value._items = values; value._is2d = True
    return value

def _multiply(first, second):
    """Original 4x4 f64 nested loop i/j/k and sequential +=; owned 16-value product.

    Coefficients unitless, translations canvas units; primitive coercion errors only.
    Source: geometry.js:multiply. No fsum/FMA/reassociation or library substitution.
    """
    dest = Float64Values([0.] * 16)
    for i in range(4):
        for j in range(4):
            total = 0.
            for k in range(4): total += _coerce(first[i*4+k]) * _coerce(second[k*4+j])
            dest[i*4+j] = total
    return dest

def _div(x, y):
    """JS IEEE f64 division, including zero/NaN/Infinity; no units/affinity/errors.

    Source: geometry.js:invertSelf/rotateAxisAngleSelf numeric division.
    """
    if y != 0: return x / y
    if x == 0 or math.isnan(x): return math.nan
    return math.copysign(math.inf, math.copysign(1., x) * math.copysign(1., y))

class MatrixOperations:
    """Original operations mixed into the sole DOMMatrix facade; no separate state.

    All data is Python-owned, any thread. Units: translations/origins canvas units,
    scales unitless, operation angles degrees, vector/axis components unitless.
    Source for every method: skia-canvas 3.0.8 lib/classes/geometry.js, same symbol.
    """
    __slots__ = ()

    def multiply(self, other):
        """Original non-self product; return DOMMatrix, sharing only until allocation.

        Matrix units as class, DOMMatrix input required, attribute/type errors propagate.
        Source: geometry.js:multiply/newInstance/multiplySelf; is2D resets as original.
        """
        return _instance(self._items).multiplySelf(other)

    def multiplySelf(self, other):
        """Original other*this stored-order product; mutate/return self, units as class.

        Source: geometry.js:multiplySelf; other.is2D=false makes flag sticky false.
        """
        self._items = _multiply(other._items, self._items)
        if not other.is2D: self._is2d = False
        return self

    def preMultiplySelf(self, other):
        """Original reversed stored-order product; mutate/return self, units as class.

        Source: geometry.js:preMultiplySelf; DOMMatrix errors/flag policy as multiplySelf.
        """
        self._items = _multiply(self._items, other._items)
        if not other.is2D: self._is2d = False
        return self

    def translate(self, tx=_MISSING, ty=_MISSING, tz=_MISSING, *extra):
        """Original non-self canvas-unit translation; returns DOMMatrix, primitive errors.

        Source: geometry.js:translate; extra JS arguments ignored, any thread.
        """
        return _instance(self._items).translateSelf(tx, ty, tz)

    def translateSelf(self, tx=_MISSING, ty=_MISSING, tz=_MISSING, *extra):
        """Original missing-zero translation; mutate/return self, canvas units.

        Source: geometry.js:translateSelf; strict tz!==0 flag precedes no normalization.
        """
        tx, ty, tz = (0 if x is _MISSING else x for x in (tx, ty, tz))
        self._items = _multiply([1,0,0,0,0,1,0,0,0,0,1,0,tx,ty,tz,1], self._items)
        if not _zero(tz): self._is2d = False
        return self

    def scale(self, scaleX=_MISSING, scaleY=_MISSING, scaleZ=_MISSING, originX=_MISSING, originY=_MISSING, originZ=_MISSING, *extra):
        """Original non-self unitless scale at canvas-unit origin; returns DOMMatrix.

        Source: geometry.js:scale; defaults/error/ownership as scaleSelf.
        """
        return _instance(self._items).scaleSelf(scaleX, scaleY, scaleZ, originX, originY, originZ)

    def scale3d(self, scale=_MISSING, originX=_MISSING, originY=_MISSING, originZ=_MISSING, *extra):
        """Original uniform three-axis scale; independent result except original no-op cases.

        Unitless scale/canvas-unit origin; source: geometry.js:scale3d/scale3dSelf.
        """
        return _instance(self._items).scale3dSelf(scale, originX, originY, originZ)

    def scale3dSelf(self, scale=_MISSING, originX=_MISSING, originY=_MISSING, originZ=_MISSING, *extra):
        """Forward original uniform scale to scaleSelf; mutate/return self, same units.

        Source: geometry.js:scale3dSelf; no second scaling implementation or policy.
        """
        return self.scaleSelf(scale, scale, scale, originX, originY, originZ)

    def scaleSelf(self, scaleX=_MISSING, scaleY=_MISSING, scaleZ=_MISSING, originX=_MISSING, originY=_MISSING, originZ=_MISSING, *extra):
        """Original origin translate/scale/inverse-translate order; mutate/return self.

        Unitless factors, canvas-unit origins; non-number factors use original defaults.
        Source: geometry.js:scaleSelf; IEEE values retained, no native ownership.
        """
        originX, originY, originZ = (x if _number(x) else 0 for x in (originX, originY, originZ))
        self.translateSelf(originX, originY, originZ)
        if not _number(scaleX): scaleX = 1
        if not _number(scaleY): scaleY = scaleX
        if not _number(scaleZ): scaleZ = 1
        self._items = _multiply([scaleX,0,0,0,0,scaleY,0,0,0,0,scaleZ,0,0,0,0,1], self._items)
        self.translateSelf(-originX, -originY, -originZ)
        if scaleZ != 1 or originZ != 0: self._is2d = False
        return self

    def rotateFromVector(self, x=_MISSING, y=_MISSING, *extra):
        """Original non-self vector-angle rotation; return DOMMatrix, atan2 in V8 math.

        Vector components unitless; source: geometry.js:rotateFromVector.
        """
        return _instance(self._items).rotateFromVectorSelf(x, y)

    def rotateFromVectorSelf(self, x=_MISSING, y=_MISSING, *extra):
        """Original atan2*degrees then rotateSelf; mutate/return self, zero defaults.

        Source: geometry.js:rotateFromVectorSelf; primitive coercion profile as _coerce.
        """
        x, y = (0 if v is _MISSING else v for v in (x, y))
        theta = 0 if _zero(x) and _zero(y) else _native._dom_math("atan2", _coerce(y), _coerce(x)) * _DEG
        return self.rotateSelf(theta)

    def rotate(self, rotX=_MISSING, rotY=_MISSING, rotZ=_MISSING, *extra):
        """Original non-self degree rotation; return DOMMatrix, same defaults as rotateSelf.

        Source: geometry.js:rotate; no Skia transform substitution.
        """
        return _instance(self._items).rotateSelf(rotX, rotY, rotZ)

    def rotateSelf(self, rotX=_MISSING, rotY=_MISSING, rotZ=_MISSING, *extra):
        """Original Z/Y/X rotation products and one-angle overload; mutate/return self.

        Angles degrees; original V8 trig f64 results, IEEE retained. Source: rotateSelf.
        """
        if rotY is _MISSING and rotZ is _MISSING: rotZ, rotX, rotY = rotX, 0, 0
        if not _number(rotY): rotY = 0
        if not _number(rotZ): rotZ = 0
        if not _zero(rotX) or not _zero(rotY): self._is2d = False
        rotX, rotY, rotZ = (_coerce(v) * _RAD for v in (rotX, rotY, rotZ))
        c, s = _native._dom_math("cos", rotZ), _native._dom_math("sin", rotZ)
        self._items = _multiply([c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1], self._items)
        c, s = _native._dom_math("cos", rotY), _native._dom_math("sin", rotY)
        self._items = _multiply([c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1], self._items)
        c, s = _native._dom_math("cos", rotX), _native._dom_math("sin", rotX)
        self._items = _multiply([1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1], self._items)
        return self

    def rotateAxisAngle(self, x=_MISSING, y=_MISSING, z=_MISSING, angle=_MISSING, *extra):
        """Original non-self unit-axis/degree rotation; return DOMMatrix, zero-axis shares array.

        Source: geometry.js:rotateAxisAngle; defaults/IEEE semantics as rotateAxisAngleSelf.
        """
        return _instance(self._items).rotateAxisAngleSelf(x, y, z, angle)

    def rotateAxisAngleSelf(self, x=_MISSING, y=_MISSING, z=_MISSING, angle=_MISSING, *extra):
        """Original normalize/axis-angle formula order; mutate/return self, degree angle.

        Source: geometry.js:rotateAxisAngleSelf; zero axis returns without allocation.
        Numeric primitive profile; no GPU state/thread affinity.
        """
        x, y, z, angle = (0 if v is _MISSING else v for v in (x, y, z, angle))
        cx, cy, cz = map(_coerce, (x, y, z))
        length = math.sqrt(cx*cx + cy*cy + cz*cz)
        if length == 0: return self
        if length != 1: x, y, z = _div(cx, length), _div(cy, length), _div(cz, length)
        flag = not _zero(x) or not _zero(y)
        x, y, z = map(_coerce, (x, y, z)); angle = _coerce(angle) * _RAD
        c, s = _native._dom_math("cos", angle), _native._dom_math("sin", angle)
        t = 1 - c; tx, ty = t*x, t*y
        self._items = _multiply([tx*x+c,tx*y+s*z,tx*z-s*y,0,tx*y-s*z,ty*y+c,ty*z+s*x,0,tx*z+s*y,ty*z-s*x,t*z*z+c,0,0,0,0,1], self._items)
        if flag: self._is2d = False
        return self

    def skew(self, sx=_MISSING, sy=_MISSING, *extra):
        """Original non-self two-angle skew in degrees; result may share on no-op.

        Source: geometry.js:skew; no native state/affinity, errors as skewSelf.
        """
        return _instance(self._items).skewSelf(sx, sy)

    def skewSelf(self, sx=_MISSING, sy=_MISSING, *extra):
        """Original two-angle skew and typeof/isNaN defaults; mutate/return self.

        Degrees; original V8 tangent, no native ownership. Source: geometry.js:skewSelf.
        """
        if not _number(sx) and not _number(sy): return self
        x, y = map(_coerce, (sx, sy))
        x = 0 if math.isnan(x) else _native._dom_math("tan", x*_RAD)
        y = 0 if math.isnan(y) else _native._dom_math("tan", y*_RAD)
        self._items = _multiply([1,y,0,0,x,1,0,0,0,0,1,0,0,0,0,1], self._items)
        return self

    def skewX(self, sx=_MISSING, *extra):
        """Original non-self X degree skew; possible no-op shared array. Source: skewX."""
        return _instance(self._items).skewXSelf(sx)

    def skewXSelf(self, sx=_MISSING, *extra):
        """Original numeric-only X degree skew; mutate/return self, V8 tangent/IEEE.

        Non-number returns before allocation; source: geometry.js:skewXSelf.
        """
        if not _number(sx): return self
        t = _native._dom_math("tan", sx*_RAD)
        self._items = _multiply([1,0,0,0,t,1,0,0,0,0,1,0,0,0,0,1], self._items)
        return self

    def skewY(self, sy=_MISSING, *extra):
        """Original non-self Y degree skew; possible no-op shared array. Source: skewY."""
        return _instance(self._items).skewYSelf(sy)

    def skewYSelf(self, sy=_MISSING, *extra):
        """Original numeric-only Y degree skew; mutate/return self, V8 tangent/IEEE.

        Non-number returns before allocation; source: geometry.js:skewYSelf.
        """
        if not _number(sy): return self
        t = _native._dom_math("tan", sy*_RAD)
        self._items = _multiply([1,t,0,0,0,1,0,0,0,0,1,0,0,0,0,1], self._items)
        return self

    def flipX(self):
        """Original X flip product with newInstance flag reset; return DOMMatrix.

        Coefficients unitless/translation canvas units; source: geometry.js:flipX.
        """
        return _instance(_multiply([-1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1], self._items))

    def flipY(self):
        """Original Y flip product with newInstance flag reset; return DOMMatrix.

        Coefficients unitless/translation canvas units; source: geometry.js:flipY.
        """
        return _instance(_multiply([1,0,0,0,0,-1,0,0,0,0,1,0,0,0,0,1], self._items))

    def inverse(self):
        """Original newInstance then invertSelf, including is2D reset; DOMMatrix/undefined.

        Matrix units as fields, any thread; source: geometry.js:inverse/invertSelf.
        """
        return _instance(self._items).invertSelf()

    def invertSelf(self):
        """Original 2D inverse: nonsingular returns a new object without changing self.

        Singular replaces self with 16 NaNs and returns undefined; 3D raises original
        Error. No alternative inversion algorithm. Source: geometry.js:invertSelf.
        """
        if self._is2d:
            v = self._items; det = v[0]*v[5] - v[1]*v[4]
            if det != 0:
                result = _matrix()()
                result.a = _div(v[5], det); result.b = _div(-v[1], det)
                result.c = _div(-v[4], det); result.d = _div(v[0], det)
                result.e = _div(v[4]*v[13] - v[5]*v[12], det)
                result.f = _div(v[1]*v[12] - v[0]*v[13], det)
                return result
            self._is2d = False; self._items = [math.nan]*16
        else:
            raise _native.Error("3D matrix inversion is not implemented.")
        return _MISSING

    def setMatrixValue(self, transformList):
        """Original constructor then replace values/flag atomically; return self.

        Numeric/CSS inputs and units as DOMMatrix; constructor errors leave self intact.
        Source: geometry.js:setMatrixValue, any thread, no native references.
        """
        temp = _matrix()(transformList)
        self._items, self._is2d = temp._items, temp._is2d
        return self

    def toString(self):
        """Original matrix/matrix3d text from flag and toFixed(12)/regex; owned string.

        Source: geometry.js:toString; no units conversion/native access, any thread.
        """
        values = [self.a,self.b,self.c,self.d,self.e,self.f] if self.is2D else self._items
        strings = list(map(fixed_string, values))
        # Original Float64Array.map converts simplify's strings back to numbers.
        if not self.is2D and isinstance(values, Float64Values):
            strings = [number_string(string_number(s)) for s in strings]
        return ("matrix" if self.is2D else "matrix3d") + "(" + ", ".join(strings) + ")"
