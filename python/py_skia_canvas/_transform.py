"""Original geometry.js CSS parser and JS numeric formatting adaptations; no drawing.

Python-owned values only, any thread. Expressions/order/errors follow the fixed JS
facade, including permissive parseFloat suffixes and matrix3d's original error text.
"""
import math
import re
from . import _MISSING

_SPACE = " \t\n\r\v\f\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_DECIMAL = r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"

def parse_float(value):
    """Original JS parseFloat numeric prefix, returning f64/NaN; no units or affinity.

    Source: geometry.js:parseAngle/Length/Scalar/Numeric built-in parseFloat calls.
    Only string inputs used by parser; numeric overflow retains Infinity.
    """
    match = re.match(r"[+-]?Infinity|" + _DECIMAL, value.lstrip(_SPACE))
    return float(match[0]) if match else math.nan

def string_number(value):
    """Original Number(string) needed by global isNaN checks; f64, no units/errors.

    Source: geometry.js parse helpers; JS empty/hex/bin/oct/Infinity syntax, ASCII digits.
    Host object/valueOf coercion is outside this helper's string-only scope.
    """
    value = value.strip(_SPACE)
    if not value:
        return 0.
    if re.fullmatch(_DECIMAL + r"|[+-]?Infinity", value):
        return float(value)
    if re.fullmatch(r"0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+", value):
        try:
            return float(int(value, 0))
        except OverflowError:
            return math.inf
    return math.nan

def parse_angle(value):
    """Original CSS angle to degrees, f64, any thread; TypeError on unsupported units.

    Source: geometry.js:parseAngle, retaining parseFloat/pi*180 order for radians.
    """
    if value.endswith("deg"): return parse_float(value)
    if value.endswith("rad"): return parse_float(value) / math.pi * 180
    if value.endswith("turn"): return parse_float(value) * 360
    raise TypeError(f'Angles must be in \'deg\', \'rad\', or \'turn\' units (got: "{value}")')

def _parse(value, suffix, label, units):
    """Original length/scale/matrix branch, returning f64; TypeError, no ownership.

    Source: geometry.js:parseLength/parseScalar/parseNumeric. Suffix parses even NaN.
    """
    if suffix and value.endswith(suffix):
        result = parse_float(value)
        return result / 100 if suffix == "%" else result
    result = parse_float(value)
    if not math.isnan(string_number(value)) and not math.isnan(result): return result
    raise TypeError(f'{label} must be in {units} units (got: "{value}")')

def parse_transform_string(text):
    """Return original sequential CSS op/degree/scalar lists; no matrix arithmetic.

    Units parsed as original; SyntaxError/TypeError messages retained, any thread.
    Source: geometry.js:parseTransformString/parseTransformName and parse helpers.
    """
    result = []
    for transform in text.split(")"):
        if not transform.strip(_SPACE): continue
        parts = [s.strip(_SPACE) for s in transform.split("(")]
        name, raw = parts[0], parts[1] if len(parts) > 1 else ""
        if not raw:
            if re.fullmatch(r"inherit|initial|revert(?:-layer)?|unset|none", name):
                result.append(("matrix", [1, 0, 0, 1, 0, 0])); continue
            raise SyntaxError("The string did not match the expected pattern")
        if not text.strip(_SPACE).endswith(")"):
            raise SyntaxError("Expected a closing ')'")
        if not re.fullmatch(r"matrix(?:3d)?|(?:rotate|translate|scale)(?:3d|X|Y|Z)?|skew(?:X|Y)?", name):
            raise SyntaxError(f"Unknown transform operation: {name}")
        if name == "rotate3d": name = "rotateAxisAngle"
        raw_vals = [s.strip(_SPACE) for s in raw.split(",")]
        if name.startswith("rotate"):
            values = [_parse(s, "px", "Lengths", "'px' or numeric") for s in raw_vals[:-1]] + [parse_angle(raw_vals[-1])]
        elif name.startswith("skew"):
            values = [parse_angle(s) for s in raw_vals]
        elif name.startswith("scale"):
            values = [_parse(s, "%", "Scales", "'%' or numeric") for s in raw_vals]
        elif name.startswith("matrix"):
            values = [_parse(s, "", "Matrix values", "plain, numeric") for s in raw_vals]
        else:
            values = [_parse(s, "px", "Lengths", "'px' or numeric") for s in raw_vals]
        if name in ("matrix", "matrix3d") and len(values) != (6 if name == "matrix" else 16):
            raise TypeError(f"{name}() requires 6 numeric values (got {len(values)})")
        parts = re.fullmatch(r"(rotate|translate|scale)(3d|X|Y|Z)", name)
        if parts:
            op, dim = parts.groups(); fill = 1 if op == "scale" else 0
            values = [values[0], fill, fill] if dim == "X" else [fill, values[0], fill] if dim == "Y" else [fill, fill, values[0]] if dim == "Z" else values
            name = op
        result.append((name, values))
    return result

def number_string(value):
    """Original V8 Number::toString for all f64; owned ASCII, no units/affinity/errors.
    Reuses pinned Node dtoa/format source; no Python repr approximation or Node runtime.
    Source Node22.23.2 deps/v8 conversions.cc:DoubleToCString and base/numbers/dtoa.cc.
    """
    from . import _native
    return _native._number_string(value)


def fixed_string(value):
    """Original Number.toFixed(12) then original regex simplification, unitless string.

    Exact rational rounding with ties away from zero, retaining original unusual zero
    stripping. Source: geometry.js:toString simplify; any thread, IEEE values supported.
    """
    if not math.isfinite(value) or abs(value) >= 1e21: return number_string(value)
    numerator, denominator = abs(value).as_integer_ratio()
    whole, remainder = divmod(numerator * 10**12, denominator)
    if remainder * 2 >= denominator: whole += 1
    digits = str(whole).rjust(13, "0")
    text = ("-" if value < 0 else "") + digits[:-12] + "." + digits[-12:]
    text = re.sub(r"\.([^0])?0*$", lambda m: "." + (m[1] or ""), text).removesuffix(".")
    return "0" if text == "-0" else text
