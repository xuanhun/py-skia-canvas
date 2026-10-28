"""Initial synchronous bindings to the original skia-canvas 3.0.8 core.

Canvas/native operations require their creating thread and raise RuntimeError on
foreign access. Coordinates are canvas units, readbacks are RGBA pixels. This
initial binding accepts finite numeric geometry, CSS colors/shared gradients and original
CSS font/FontLibrary typography; remaining API/JS coercion audit is in docs/TASKS.md.
No renderer or drawing state is implemented in Python.
"""
from __future__ import annotations

import json
import math
import weakref
from types import MappingProxyType
from . import _native

__version__ = "0.1.0a18"
__all__ = ["Canvas", "CanvasRenderingContext2D", "TextMetrics", "Path2D", "CanvasGradient", "DOMMatrix", "DOMPoint", "DOMRect"]
class _Undefined:
    """JS undefined value for absent arguments/distinct results; Python-owned, no units.

    Source: geometry.js:invertSelf fallthrough and JS default arguments. None remains null.
    """
    __slots__ = ()
    def __repr__(self):
        """Return unitless JS label, any thread, no side effects/errors."""
        return "undefined"
    def __bool__(self):
        """Return original false truth value, any thread, no units/errors."""
        return False

undefined = _MISSING = _Undefined()
__all__.append("undefined")
__all__.append("FontLibrary")


def _number(value, name):
    """Convert finite Python numbers to f64, no units/ownership; TypeError otherwise.

    Typed subset of upstream utils.rs:_as_double; JS object coercion is pending.
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"Expected a number for `{name}`")
    result = float(value)
    if not math.isfinite(result):
        raise TypeError(f"Expected a finite number for `{name}`")
    return result


def _text(value):
    """Return a Rust-compatible string with Neon-equivalent lone-surrogate replacement.

    No units/ownership; TypeError for non-string initial inputs. Source: Neon JsString.value.
    Full JS toString coercion remains pending; Python conversion runs outside core borrow.
    """
    if not isinstance(value, str):
        raise TypeError("Expected a string for `text`")
    return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _matrix_args(values):
    """Forward shared DOM-to-Skia facade adaptation; no matrix arithmetic.

    Coefficients unitless, translation canvas units; owned numeric list. Typed errors
    ->TypeError, CSS string overloads ->NotImplementedError. Objects/6/16 arrays supported.
    Source: geometry.js:toSkMatrix/DOMMatrix constructor; shared by Context and Path2D.
    """
    return to_sk_matrix(values)


def _round_rect_args(x, y, width, height, radius, reader=None):
    """Adapt original CSS corner radii and signed-corner order; owned f64 canvas-unit list.

    None means original silent abort for invalid radii; negative radius ->RangeError.
    Numeric/dict x/y and list/tuple inputs follow css.js:parseCornerRadii, including
    truncate-before-validation and 1/2/3/4 expansion. Skia constructs geometry in core.
    """
    radii = list(radius) if isinstance(radius, (list, tuple)) else [radius]
    points = [(v["x"], v["y"]) if isinstance(v, dict) and "x" in v and "y" in v else (v, v) for v in radii[:4]]
    for point in points:
        for value in point:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None
            try:
                if not math.isfinite(value):
                    return None
            except OverflowError:
                return None
    if any(a < 0 or b < 0 for a, b in points):
        raise _native.RangeError("Corner radius cannot be negative")
    if len(points) == 1:
        points *= 4
    elif len(points) == 2:
        points *= 2
    elif len(points) == 3:
        points = [points[0], points[1], points[2], points[1]]
    elif not points:
        points = [(0, 0)] * 4
    x, y, width, height = reader() if reader is not None else [_number(v, "roundRect") for v in (x, y, width, height)]
    if width < 0:
        points = [points[1], points[0], points[3], points[2]]
    if height < 0:
        points = [points[3], points[2], points[1], points[0]]
    return [x, y, width, height, *[v for point in points for v in point]]


from ._metrics import TextMetrics


class Canvas:
    """Original Canvas/default GPU, independent pages and original sync/async exports.

    Native objects live exclusively on the creator thread. Python handles may be
    collected elsewhere; native destruction is deferred to owner entry or exit.
    Source: lib/classes/canvas.js. Host object coercion/toSharp remain G0 pending.
    """
    __slots__ = ("_native", "_contexts", "__weakref__")

    def __init__(self, width=_MISSING, height=_MISSING, options=_MISSING, *extra):
        """Create original Canvas with JS ordinary dimensions/options, 300x150 defaults.
        Contrast/gamma f64, geometry canvas units; original range/type errors. Owner TLS,
        retains GPU constructor flag discrepancy. Source canvas.js:constructor/canvas.rs:new."""
        from ._thread_lifetime import ensure_owner
        ensure_owner()
        from ._canvas_api import initialize
        initialize(self,width,height,options)


    @property
    def width(self):
        """Original f32 canvas-unit width; owner-only, RuntimeError on foreign access."""
        return self._native.size()[0]

    @width.setter
    def width(self, value):
        """Original JS Number gate/native f32 setter and head-only reset; canvas units.
        Default/nonfinite bail/STRICT errors retained, owner only. Source canvas.js setter."""
        from ._canvas_api import dimension
        dimension(self,"width",value)


    @property
    def height(self):
        """Original f32 canvas-unit height; owner-only, RuntimeError on foreign access."""
        return self._native.size()[1]

    @height.setter
    def height(self, value):
        """Original JS Number gate/native f32 setter and head-only reset; canvas units.
        Default/nonfinite bail/STRICT errors retained, owner only. Source canvas.js setter."""
        from ._canvas_api import dimension
        dimension(self,"height",value)


    @property
    def gpu(self):
        """Original selected-engine bool, not a queue trace; owner-only, RuntimeError if foreign."""
        return self._native.engine()[0]

    @gpu.setter
    def gpu(self, value):
        """Original JS !!value GPU/CPU setter, None/owner errors; no GPU transfer.
        Source canvas.js:gpu setter, core engine selection unchanged."""
        from ._text_css import truth
        self._native.set_gpu(truth(value))


    @property
    def engine(self):
        """Return original owned status dict; owner-only, backend/device errors remain upstream.

        Source: canvas.rs:get_engine_status; no units or native ownership transfer.
        """
        return json.loads(self._native.engine()[1])

    def getContext(self, kind=_MISSING, *extra):
        """Original ordinary loose kind == 2d, return head Context/None. Owner access
        for supported kind, extra args ignored; source canvas.js:getContext, no units."""
        from ._canvas_api import context
        return context(self,kind)


    def newPage(self, *args):
        """Create original page at current canvas-unit bounds, newest head. Exactly
        two args assign width then height; all others ignored. Returns real Context or
        owner/argument errors, source canvas.js:newPage; no native objects transferred."""
        ctx=object.__new__(CanvasRenderingContext2D)
        ctx._bind(self,self._native.page_handle())
        self._contexts.insert(0,ctx)
        if len(args)==2:self.width,self.height=args
        return ctx


    @property
    def pages(self):
        """Copied contexts oldest→newest, no units/errors; no native objects move.
        Context handles remain owner-thread-only. Source canvas.js:pages.
        """
        return self._contexts[::-1]

    def toSharp(self, options=undefined, *extra):
        """Node Sharp host entry: original missing dependency Error in Python profile.
        Options page/matte/density/MSAA unitless/pixel scales; no Node runtime or fake
        stream. User-approved host mapping; source canvas.js:toSharp/getSharp.
        """
        from ._host import sharp
        return sharp(options,canvas=True)

    def toBufferSync(self, extension="png", opts=undefined):
        """Encode selected original pages as owned bytes; quality fraction/density scale.
        Supports original PNG/JPG/WebP/raw/PDF/SVG/options. Owner-only; original validation,
        codec Error and typed exceptions. Source canvas.js:toBufferSync/exportOptions.
        """
        from ._exports import export
        return export(self,extension,opts)

    def toBuffer(self, extension="png", opts=undefined):
        """Start original export immediately, return repeatedly awaitable owned bytes.
        Same options/errors as sync, owner at call; worker owns materialized snapshot.
        Source canvas.js:toBuffer/canvas.rs:toBuffer, original Rayon policy retained.
        """
        from ._exports import export
        return export(self,extension,opts,asynchronous=True)

    def toFileSync(self, filename=undefined, opts=undefined):
        """Write selected pages, None on success; filename string/PathLike, sequence {N}
        pads page digits. Owner-only; original Error/validation exceptions. Source toFileSync.
        """
        from ._exports import export
        return export(self,'',opts,filename=filename)

    def toFile(self, filename=undefined, opts=undefined):
        """Start original file/sequence job now, await None; same path/units as sync.
        Owner at call; original async 'I/O Error:' prefix, no live owner context transfer.
        Source canvas.js:toFile/canvas.rs:save.
        """
        from ._exports import export
        return export(self,'',opts,filename=filename,asynchronous=True)

    def toURLSync(self, extension="png", opts=undefined):
        """Original MIME/base64 data URL; export units/options/errors as toBufferSync.
        Owner-only. Source canvas.js:toURLSync, no network operation.
        """
        from ._exports import export
        return export(self,extension,opts,url=True)

    def toURL(self, extension="png", opts=undefined):
        """Immediately start export, await MIME/base64 URL; original options/errors.
        Owner at call, channel-only waiter. Source canvas.js:toURL, no network operation.
        """
        from ._exports import export
        return export(self,extension,opts,url=True,asynchronous=True)

    def toDataURL(self, extension="png", quality=undefined):
        """Original synchronous browser-style URL, numeric quality fraction 0–1 only.
        Owner-only, TypeError for invalid quality. Source canvas.js:toDataURL.
        """
        if quality is not undefined and (isinstance(quality,bool) or not isinstance(quality,(int,float))):
            raise TypeError("Expected a number in the range 0–1 for `quality` (use toURL() for additional rendering options)")
        return self.toURLSync(extension,{'quality':quality})

    def saveAs(self,*args):
        """Deprecated once/process warning + eagerly start toFile, return None as Node.
        Paths/units/errors as toFile; source canvas.js:saveAs. No new render policy.
        """
        from ._exports import deprecated
        deprecated('saveAs','toFile()');self.toFile(*args)

    def saveAsSync(self,*args):
        """Deprecated warning + toFileSync, None; owner/path/errors as original method.
        Source canvas.js:saveAsSync. No new render policy.
        """
        from ._exports import deprecated
        deprecated('saveAsSync','toFileSync()');self.toFileSync(*args)

    def toDataURLSync(self,*args):
        """Deprecated warning + toURLSync, returns None as original alias (not URL).
        Owner/options/errors as toURLSync. Source canvas.js:toDataURLSync.
        """
        from ._exports import deprecated
        deprecated('toDataURLSync','toURLSync() (see also Canvas.toDataURL() which is now synchronous)');self.toURLSync(*args)

    @property
    def raw(self):
        """Start original raw export, await bytes; owner call/options/errors as toBuffer.
        Source canvas.js:raw getter. No units or additional native ownership.
        """
        return self.toBuffer("raw")

    @property
    def png(self):
        """Start original png export, await bytes; owner call/options/errors as toBuffer.
        Source canvas.js:png getter. No units or additional native ownership.
        """
        return self.toBuffer("png")

    @property
    def jpg(self):
        """Start original jpg export, await bytes; owner call/options/errors as toBuffer.
        Source canvas.js:jpg getter. No units or additional native ownership.
        """
        return self.toBuffer("jpg")

    @property
    def pdf(self):
        """Start original pdf export, await bytes; owner call/options/errors as toBuffer.
        Source canvas.js:pdf getter. No units or additional native ownership.
        """
        return self.toBuffer("pdf")

    @property
    def svg(self):
        """Start original svg export, await bytes; owner call/options/errors as toBuffer.
        Source canvas.js:svg getter. No units or additional native ownership.
        """
        return self.toBuffer("svg")

    @property
    def webp(self):
        """Start original webp export, await bytes; owner call/options/errors as toBuffer.
        Source canvas.js:webp getter. No units or additional native ownership.
        """
        return self.toBuffer("webp")



class CanvasRenderingContext2D:
    """Owner-thread context; state/drawing use only original core implementation.

    Geometry uses finite numbers in canvas units. Foreign access raises RuntimeError;
    unsupported numeric inputs raise TypeError in this initial binding. Source: context.js.
    """
    __slots__ = ("_native", "_canvas", "_fill_ref", "_stroke_ref")

    def __init__(self, canvas=_MISSING, *extra):
        """Construct original independent Context for Canvas, without joining pages or
        replacing its head. Canvas-unit bounds, weak Python parent; invalid parent ->original
        TypeError, foreign owner ->RuntimeError. Source context.js constructor/API new."""
        if not isinstance(canvas,Canvas):raise TypeError('Function is not a constructor (use Canvas\'s "getContext" method instead)')
        self._bind(canvas,canvas._native.context_handle())


    def _bind(self,canvas,native):
        """Bind one real owner Context ID and weak parent, initialize shader refs once.
        No units/return/native transfer. Shared public constructor/newPage plumbing;
        source context.js:constructor and Canvas.newPage, not a second drawing policy.
        """
        self._native=native;self._canvas=weakref.ref(canvas);self._fill_ref=None;self._stroke_ref=None

    @property
    def canvas(self):
        """Return weak Canvas parent or original undefined after GC, no units/native transfer.
        Source context.js:canvas WeakRef.deref; keeps parent weak and native owner TLS.
        """
        value=self._canvas()
        return undefined if value is None else value

    def save(self,*extra):
        """Push original state, returns None; owner-only, RuntimeError if foreign. Source: API save."""
        self._native.state("save")

    def restore(self,*extra):
        """Pop original state, returns None; owner-only, RuntimeError if foreign. Source: API restore."""
        self._native.state("restore")

    def reset(self,*extra):
        """Reset original context at current canvas-unit size; None, owner-only. Source: API reset."""
        self._native.state("reset")

    @property
    def fillStyle(self):
        """Return original CSS value or JS-compatible cached shader ref; owner-only.

        Native errors propagate. Reference cache intentionally differs from restored State
        after save/restore, as upstream context.js does. Source: Dye::value/context.js:fillStyle.
        """
        value = self._native.color(False)
        return self._fill_ref if value is None else value

    @fillStyle.setter
    def fillStyle(self, value):
        """Set CSS color/shared CanvasGradient; None, owner-only, original string ignore policy.

        Unsupported object color coercion ->TypeError; source: context.js setter/Dye::new.
        """
        self._set_style(False, value)

    @property
    def strokeStyle(self):
        """Return original CSS value or cached shader ref; owner-only/errors as fillStyle.

        Source: context.js:strokeStyle and Dye::value; does not infer wrapper from native State.
        """
        value = self._native.color(True)
        return self._stroke_ref if value is None else value

    @strokeStyle.setter
    def strokeStyle(self, value):
        """Set original CSS/shared gradient stroke; None, owner-only/errors as fillStyle.

        Source: context.js setter/Dye::new; shared ramp is cloned by reference in core.
        """
        self._set_style(True, value)

    def _set_style(self, stroke, value):
        """Adapt original cached shader ref and native dye assignment; no geometry/units.

        Owner checked first; gradient owners checked before State/cache change. String or
        primitive invalid color keeps original ignore behavior; object coercion pending.
        Source: context.js fillStyle/strokeStyle setters and native Dye::new.
        """
        self._native.ensure_context()
        name = "_stroke_ref" if stroke else "_fill_ref"
        if isinstance(value, CanvasGradient):
            self._native.gradient_style(stroke, value._native)
            setattr(self, name, value)
        elif isinstance(value,(CanvasPattern,CanvasTexture)):
            value._native.apply(self._native,stroke)
            setattr(self,name,value)
        else:
            setattr(self, name, None)
            if isinstance(value, str):
                self._native.color(stroke, _text(value))
            elif value is None or isinstance(value, (bool, int, float)):
                self._native.color(stroke)  # Original primitive non-string color is ignored.
            else:
                from ._text_api import color
                css=color(value)
                if css is not None:self._native.color(stroke,css)

    def createLinearGradient(self, *args):
        """Create original shared ramp from primitive numeric args; canvas-unit
        coordinates/radii, angle radians. Owner only, original count/type errors; context.js factory."""
        self._native.ensure_context()
        return CanvasGradient("linear",*args)


    def createRadialGradient(self, *args):
        """Create original shared ramp from primitive numeric args; canvas-unit
        coordinates/radii, angle radians. Owner only, original count/type errors; context.js factory."""
        self._native.ensure_context()
        return CanvasGradient("radial",*args)


    def createConicGradient(self, *args):
        """Create original shared ramp from primitive numeric args; canvas-unit
        coordinates/radii, angle radians. Owner only, original count/type errors; context.js factory."""
        self._native.ensure_context()
        return CanvasGradient("conic",*args)


    def fillRect(self, *args):
        """Original finite-f64/f32 argument stages and shared native operation; units
        canvas coordinates/scales/radians as named. None/original count/STRICT/type errors.
        Owner only; source context/api.rs:fillRect, no geometry or math duplicated."""
        from ._arguments import rectangle
        return rectangle(self,"fillRect",args)


    def strokeRect(self, *args):
        """Original finite-f64/f32 argument stages and shared native operation; units
        canvas coordinates/scales/radians as named. None/original count/STRICT/type errors.
        Owner only; source context/api.rs:strokeRect, no geometry or math duplicated."""
        from ._arguments import rectangle
        return rectangle(self,"strokeRect",args)


    def clearRect(self, *args):
        """Original finite-f64/f32 argument stages and shared native operation; units
        canvas coordinates/scales/radians as named. None/original count/STRICT/type errors.
        Owner only; source context/api.rs:clearRect, no geometry or math duplicated."""
        from ._arguments import rectangle
        return rectangle(self,"clearRect",args)


    @property
    def font(self):
        """Original canonical font string; no units/errors except owner RuntimeError.

        Owner Context state snapshot; source context.js:font / API get_font.
        """
        return self._native.font()

    @font.setter
    def font(self, value):
        """Apply original CSS font parser/FontSpec; invalid strings retain current state.

        Size/leading CSS px, original canonical string stored by core. Parsing uses
        Python values before native borrow; native fonts/GPU stay owner TLS. Source:
        css.js:parseFont/parseSize/parseWeight, typography.rs:font_arg, API set_font.
        """
        from ._font_css import parse_font
        descriptor=parse_font(value)
        def strings(item):
            """Adapt descriptor strings to original Neon UTF-16 decoding, no native state."""
            if isinstance(item,str):return _text(item)
            if isinstance(item,list):return [strings(v) for v in item]
            if isinstance(item,dict):return {k:strings(v) for k,v in item.items()}
            return item
        self._native.font(None if descriptor is None else json.dumps(strings(descriptor),allow_nan=False))

    def fillText(self, *args):
        """Original text String/geometry boundary, canvas units, owner only; original errors.
        Source context.js/fillText and context/api.rs; font/layout/drawing stay unique core."""
        from ._text_api import draw
        return draw(self,args)

    def strokeText(self, *args):
        """Original text String/geometry boundary, canvas units, owner only; original errors.
        Source context.js/strokeText and context/api.rs; font/layout/drawing stay unique core."""
        from ._text_api import draw
        return draw(self,args,True)

    def measureText(self, text=_MISSING, maxWidth=_MISSING, *extra):
        """Return original TextMetrics (canvas units/UTF-16 offsets); owner-only/typed errors.

        Ordinary text values follow original toString; optional width follows original
        primitive/string/array finite-f64 conversion then f32 cast, null is zero and
        invalid/undefined ignored. Extra args ignored. Context2D::measure_text unchanged.
        """
        from ._text_api import string
        return TextMetrics(json.loads(self._native.measure(string(text), _native._text_width(maxWidth))))


    def beginPath(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:beginPath."""
        from ._arguments import command
        return command(self,"context","beginPath",args)


    def closePath(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:closePath."""
        from ._arguments import command
        return command(self,"context","closePath",args)


    def moveTo(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:moveTo."""
        from ._arguments import command
        return command(self,"context","moveTo",args)


    def lineTo(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:lineTo."""
        from ._arguments import command
        return command(self,"context","lineTo",args)


    def rect(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:rect."""
        from ._arguments import command
        return command(self,"context","rect",args)


    def roundRect(self, *args):
        """Original argc/CSS radius-before-coordinate order; canvas units, None or
        original RangeError/TypeError, owner native call only. Source context.js:roundRect."""
        from ._arguments import round_rect
        return round_rect(self,"context",args)


    def arc(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:arc."""
        from ._arguments import command
        return command(self,"context","arc",args)


    def ellipse(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:ellipse."""
        from ._arguments import command
        return command(self,"context","ellipse",args)


    def arcTo(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:arcTo."""
        from ._arguments import command
        return command(self,"context","arcTo",args)


    def bezierCurveTo(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:bezierCurveTo."""
        from ._arguments import command
        return command(self,"context","bezierCurveTo",args)


    def quadraticCurveTo(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:quadraticCurveTo."""
        from ._arguments import command
        return command(self,"context","quadraticCurveTo",args)


    def conicCurveTo(self, *args):
        """Original primitive, canvas-unit coordinates/radii, radians and unitless weights.
        Missing args throw; ordinary invalid values bail/STRICT throw, extra args ignored.
        Owner only, original native radius errors retained; source context/api.rs:conicCurveTo."""
        from ._arguments import command
        return command(self,"context","conicCurveTo",args)


    def _rule(self, rule, ordinal="1st"):
        """Check language string type, return unchanged fill-rule string; no units/native state.

        TypeError retains original argument message. Actual rule selection is shared core
        utils::fill_rule; owner access is checked by the following native operation.
        """
        if not isinstance(rule, str):
            raise TypeError(f'Expected `fillRule` to be "nonzero" or "evenodd" for {ordinal} arg')
        return rule


    def fill(self, *args):
        """Original positional Path/rule overload, owner-only, None/original TypeError.
        Rule unitless, actual geometry shared core. Source context.js/api.rs:fill."""
        from ._arguments import paint
        return paint(self,"fill",args)

    def stroke(self, *args):
        """Original positional Path/rule overload, owner-only, None/original TypeError.
        Rule unitless, actual geometry shared core. Source context.js/api.rs:stroke."""
        from ._arguments import paint
        return paint(self,"stroke",args)

    def clip(self, *args):
        """Original positional Path/rule overload, owner-only, None/original TypeError.
        Rule unitless, actual geometry shared core. Source context.js/api.rs:clip."""
        from ._arguments import paint
        return paint(self,"clip",args)

    def isPointInPath(self, *args):
        """Original rule-first/optional path/numeric filtering and hit operation.
        Canvas-unit coordinates, bool or original argument/owner errors. Extra/count ambiguity
        retained; source context/api.rs:_is_in. Actual geometry remains shared core."""
        from ._arguments import hit
        return hit(self,args,False)


    def isPointInStroke(self, *args):
        """Original rule-first/optional path/numeric filtering and hit operation.
        Canvas-unit coordinates, bool or original argument/owner errors. Extra/count ambiguity
        retained; source context/api.rs:_is_in. Actual geometry remains shared core."""
        from ._arguments import hit
        return hit(self,args,True)


    def _matrix(self, kind, values):
        """Adapt original DOM-to-Skia element order; no matrix arithmetic in Python.

        Values are canvas-unit translation/unitless coefficients; None, owner-only/typed
        errors. Original CSS parser is shared with DOMMatrix. Source: geometry.js:toSkMatrix.
        """
        self._native.matrix(kind, _matrix_args(values))

    def setTransform(self, *values):
        """Set original matrix from DOM value/object or 6/16 scalar/sequence terms; None, owner-only.

        Coefficients unitless, translation canvas units; typed/overload errors per _matrix.
        Source: context.js:setTransform, geometry.js:toSkMatrix, API set_currentTransform.
        """
        self._matrix("set", values)

    def transform(self, *values):
        """Pre-concatenate original DOM/object/6/16 matrix; units/returns/errors as setTransform.

        Owner-only. Source: context.js:transform, geometry.js:toSkMatrix, API transform.
        """
        self._matrix("transform", values)

    @property
    def currentTransform(self):
        """Return original independent DOMMatrix snapshot; coefficients unitless/translation canvas units.

        Owner-only native read, RuntimeError if foreign; snapshot itself is Python-owned.
        Source: context.js:get currentTransform and geometry.js:fromSkMatrix.
        """
        return from_sk_matrix(self._native.current_matrix())

    @currentTransform.setter
    def currentTransform(self, matrix):
        """Set original matrix via same setTransform implementation; None, owner-only.

        Units/errors as setTransform; source: context.js:set currentTransform.
        """
        self.setTransform(matrix)

    def getTransform(self):
        """Return same independent snapshot as currentTransform; units/errors/ownership identical.

        Source: context.js:getTransform; no cached live matrix or second state.
        """
        return self.currentTransform

    def createProjection(self, quad=_MISSING, basis=_MISSING, *extra):
        """Return original DOMMatrix mapping basis to quad; coordinates in canvas units.

        Flat 2/4/6/8 numbers use original size/rect/3-point/quad rules. Omitted/filtered
        empty basis uses current Context bounds; primitive/string/array coercion, finite
        filtering and f32 cast are original native rules. No CTM/state mutation.
        Owner-only; original odd-count/solver TypeError and ownership RuntimeError.
        Result is independent Python-owned data usable after owner exit. Extra args
        ignored as original. Source: context.js:50 and context/api.rs:createProjection.
        """
        self._native.ensure_context()
        dst = list(quad) if isinstance(quad, (list, tuple)) else [quad]
        src = list(basis) if isinstance(basis, (list, tuple)) else [basis]
        return from_sk_matrix(self._native.projection(dst, src))

    def resetTransform(self,*extra):
        """Reset original matrix to identity; no units/return, owner-only. Source: API resetTransform."""
        self._native.matrix("reset", [])

    def translate(self, *args):
        """Original finite-f64/f32 argument stages and shared native operation; units
        canvas coordinates/scales/radians as named. None/original count/STRICT/type errors.
        Owner only; source context/api.rs:translate, no geometry or math duplicated."""
        from ._arguments import transform
        return transform(self,"translate",args)


    def scale(self, *args):
        """Original finite-f64/f32 argument stages and shared native operation; units
        canvas coordinates/scales/radians as named. None/original count/STRICT/type errors.
        Owner only; source context/api.rs:scale, no geometry or math duplicated."""
        from ._arguments import transform
        return transform(self,"scale",args)


    def rotate(self, *args):
        """Original finite-f64/f32 argument stages and shared native operation; units
        canvas coordinates/scales/radians as named. None/original count/STRICT/type errors.
        Owner only; source context/api.rs:rotate, no geometry or math duplicated."""
        from ._arguments import transform
        return transform(self,"rotate",args)


    def getLineDash(self):
        """Return owned original canvas-unit dash list; owner-only/RuntimeError. Source: API getLineDash."""
        return self._native.line_dash()

    def setLineDash(self, *args):
        """Original array primitive conversion, complete finite/nonnegative guard.
        Canvas units, None/TypeError, owner only; original core duplicates odd lists. API setLineDash."""
        from ._arguments import line_dash
        return line_dash(self,args)


    @property
    def lineWidth(self):
        """Return original f32 canvas-unit width; owner-only/RuntimeError. Source: API get_lineWidth."""
        return self._native.stroke_number("lineWidth")

    @lineWidth.setter
    def lineWidth(self, value):
        """Original optional/bail numeric setter, native range guard unchanged.
        Width/offset canvas units, miter unitless; None/STRICT/owner errors. Source context API."""
        from ._arguments import stroke_number
        stroke_number(self,"lineWidth",value)


    @property
    def miterLimit(self):
        """Return original unitless miter limit; owner-only/RuntimeError. Source: API get_miterLimit."""
        return self._native.stroke_number("miterLimit")

    @miterLimit.setter
    def miterLimit(self, value):
        """Original optional/bail numeric setter, native range guard unchanged.
        Width/offset canvas units, miter unitless; None/STRICT/owner errors. Source context API."""
        from ._arguments import stroke_number
        stroke_number(self,"miterLimit",value)


    @property
    def lineDashOffset(self):
        """Return original canvas-unit dash offset; owner-only/RuntimeError. Source: API get_lineDashOffset."""
        return self._native.stroke_number("lineDashOffset")

    @lineDashOffset.setter
    def lineDashOffset(self, value):
        """Original optional/bail numeric setter, native range guard unchanged.
        Width/offset canvas units, miter unitless; None/STRICT/owner errors. Source context API."""
        from ._arguments import stroke_number
        stroke_number(self,"lineDashOffset",value)


    @property
    def lineCap(self):
        """Return original canonical cap name; unitless, owner-only/RuntimeError. Source: API get_lineCap."""
        return self._native.stroke_name("lineCap")

    @lineCap.setter
    def lineCap(self, value):
        """Set original cap (case normalized); bad name ignored, None, owner-only, TypeError if non-string."""
        if not isinstance(value, str):
            raise TypeError("Expected a string for `lineCap`")
        self._native.stroke_name("lineCap", value)

    @property
    def lineJoin(self):
        """Return original canonical join name; unitless, owner-only/RuntimeError. Source: API get_lineJoin."""
        return self._native.stroke_name("lineJoin")

    @lineJoin.setter
    def lineJoin(self, value):
        """Set original join (case normalized); bad name ignored, None, owner-only, TypeError if non-string."""
        if not isinstance(value, str):
            raise TypeError("Expected a string for `lineJoin`")
        self._native.stroke_name("lineJoin", value)

    def outlineText(self, *args):
        """Original text String/geometry boundary, canvas units, owner only; original errors.
        Source context.js/outlineText and context/api.rs; font/layout/drawing stay unique core."""
        from ._text_api import outline
        return outline(self,args)

    @property
    def lineDashMarker(self):
        """Return copied original marker Path2D/None; canvas-unit geometry, owner-only.

        Source: API get_lineDashMarker and context.js wrapper; no shared mutable Python state.
        """
        value = self._native.marker()
        return None if value is None else Path2D._from_native(value)

    @lineDashMarker.setter
    def lineDashMarker(self, path):
        """Set original path snapshot or null clear; invalid value TypeError, owner only.

        Source: API set_lineDashMarker; supplied Path2D must belong to this thread.
        """
        self._native.ensure_context()
        if path is not None and not isinstance(path,Path2D):raise TypeError('Expected a Path2D object (or null)')
        self._native.marker(True, path._native if isinstance(path, Path2D) else None)


from ._path import Path2D
from ._gradient import CanvasGradient
from ._geometry import DOMMatrix, DOMPoint, DOMRect, to_sk_matrix, from_sk_matrix
from ._fonts import FontLibrary
from ._text_state import install as _install_text_state
_install_text_state(CanvasRenderingContext2D)

from ._imagery import Image,ImageData,loadImage,loadImageData,install as _install_imagery
_install_imagery(CanvasRenderingContext2D)
__all__ += ["Image","ImageData","loadImage","loadImageData"]
from ._shaders import CanvasPattern,CanvasTexture,install as _install_shaders
_install_shaders(CanvasRenderingContext2D)
__all__ += ["CanvasPattern","CanvasTexture"]

from ._effects import install as _install_effects
_install_effects(CanvasRenderingContext2D)

from ._gui import App,Window
__all__ += ["App","Window"]
