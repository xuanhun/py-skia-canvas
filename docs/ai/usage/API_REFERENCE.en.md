# Public API reference

[中文](API_REFERENCE.md) | English

Install (CPython 3.13): `python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18`. See the [installation guide](../INSTALL.en.md).

For `py-skia-canvas==0.1.0a18`, targeting official Node `skia-canvas@3.0.8`. Use this page to select common signatures and understand data/lifetimes. Consult the [public API ledger](../../public-api-ledger.json), [alpha status](../../alpha-api-status.json), and [Python host profile](../../PYTHON_HOST_PROFILE.md) for special overloads and individual compatibility records. Do not infer this library's API from browser Canvas or other Python drawing libraries.

## 1. Imports and host conventions

```python
from py_skia_canvas import (
    Canvas, CanvasRenderingContext2D, TextMetrics, Path2D,
    CanvasGradient, CanvasPattern, CanvasTexture, FontLibrary,
    DOMMatrix, DOMPoint, DOMRect, Image, ImageData,
    loadImage, loadImageData, App, Window, undefined,
)
```

Upstream has 17 runtime exports. Python supplies their counterparts and additionally exports the `undefined` singleton. Usually obtain related objects through `Canvas.getContext()`, `ctx.create*()`, and `ctx.measureText()`.

| Node concept | Python counterpart | Notes |
| --- | --- | --- |
| Buffer / Uint8ClampedArray | `bytes` / `ImageData.data` pixel view | Distinguish encoded bytes from raw pixels |
| Promise | Awaitable export objects; loaders can also be awaited | Wrap async programs in `async def main()` |
| undefined / null | `undefined` / `None` | Omitted arguments and explicit null can behave differently |
| Plain objects/arrays | `dict` / `list` and corresponding values | Access line fields as `metrics.lines[0]["x"]` |
| File paths | Usually `str`; exports also accept `os.PathLike` | Pass string paths for font registration |
| Sharp | Same-name entry raises missing Node Sharp dependency | Obtain bytes and use the application's Python tool |

Numeric conversion/validation follows the original implementation. Some invalid inputs leave state unchanged or suppress drawing; others raise. Common Python catch types include `TypeError`, `ValueError`, `RuntimeError`, and file/network exceptions; unsupported host special cases may raise `NotImplementedError`. Do not expect one exception for every invalid input. Set `SKIA_CANVAS_STRICT=1` before process startup/import to use upstream strict invalid-argument behavior for diagnostics/compatibility tests.

“Owner” means the thread that created a native object. Native access to Canvas, Context, Path, Image, Gradient, Pattern, and Texture stays on that thread; foreign-thread access raises. DOM values, TextMetrics, obtained bytes, and ImageData pixel storage carry no GPU context. Applications still synchronize shared mutable data.

## 2. Canvas and pages

| Entry point | Parameters and result | Semantics |
| --- | --- | --- |
| `Canvas(width=300, height=150, options=undefined)` | Dimensions in canvas units; returns Canvas | options include `textContrast`, `textGamma`, `gpu`; preserves default GPU policy |
| `getContext("2d")` | Current page's Context | Other context types return `None` |
| `newPage()` / `newPage(width, height)` | New page's Context | New page becomes current; previous pages remain |
| `pages` | Context list in creation order | Getting the list does not duplicate native pictures |
| `width` / `height` | Read/write logical dimensions | Assignment resets the current page; size before drawing |
| `engine` | Copied backend/device/text-settings dict | `renderer` is `GPU` or `CPU`; not a per-call native trace |
| `gpu` | Read/write switch | For explicit CPU, set `canvas.gpu = False` before drawing |

Default text settings: `textContrast=0`, `textGamma=1.4`. Preserve the 3.0.8 constructor behavior: `{"gpu": False}` does not reliably force CPU; use the setter. Without GPU support, offscreen work automatically falls back to CPU.

Context `.canvas` is weak parent access. Keep the Canvas alive until drawing/export calls finish. Pages may have different dimensions; avoid resizing Canvas after drawing a page.

Sources: [Canvas facade](../../../python/py_skia_canvas/_canvas_api.py), [public entry points](../../../python/py_skia_canvas/__init__.py), [shared Canvas core](../../../crates/canvas-core/src/canvas.rs).

## 3. Context: paths, drawing, and transforms

Positions/lengths use canvas units; angles use radians. Drawing methods generally return `None`; queries return the values below. Argument counts, radii, valid numbers, and owner errors follow the original implementation.

| Category | Common signatures | Purpose |
| --- | --- | --- |
| Rectangles | `fillRect(x,y,w,h)`, `strokeRect(...)`, `clearRect(...)` | Fill, stroke, or clear a region |
| Current path | `beginPath()`, `closePath()`, `moveTo(x,y)`, `lineTo(x,y)` | Build the current path; beginPath clears that path |
| Curves | `bezierCurveTo(c1x,c1y,c2x,c2y,x,y)`, `quadraticCurveTo(cx,cy,x,y)` | Cubic/quadratic Bézier curves |
| Arcs | `arc(x,y,r,start,end,ccw=False)`, `arcTo(x1,y1,x2,y2,r)` | Circular arcs and rounded joins |
| Ellipses | `ellipse(x,y,rx,ry,rotation,start,end,ccw=False)` | Rotation and start/end angles all use radians |
| Rectangle paths | `rect(x,y,w,h)`, `roundRect(x,y,w,h,radii)` | Add geometry without automatically filling it |
| Paint/clip | `fill()`, `fill(path)`, `stroke()`, `stroke(path)`, `clip()`, `clip(path)` | fill/clip have `"nonzero"` / `"evenodd"` rule overloads |
| Hit testing | `isPointInPath(x,y)`, `isPointInPath(path,x,y)`, `isPointInStroke(...)` | Returns `bool`; optional explicit path |
| State | `save()`, `restore()`, `reset()` | Save/restore state or reset Context using original semantics |
| Transforms | `translate(x,y)`, `scale(x,y)`, `rotate(radians)` | Update the current transform |
| Matrices | `transform(a,b,c,d,e,f)`, `setTransform(...)`, `resetTransform()`, `getTransform()` | get returns DOMMatrix; corresponding object overloads are available |

Use `save/restore` to scope styles, clips, and transforms. They are not a pixel undo history. Set each component's required state explicitly.

| Style property | Common values/meaning |
| --- | --- |
| `fillStyle` / `strokeStyle` | CSS color, CanvasGradient, CanvasPattern, CanvasTexture; default black |
| `lineWidth` / `lineCap` / `lineJoin` / `miterLimit` | Defaults: `1` / `"butt"` / `"miter"` / `10` |
| `setLineDash(list)` / `getLineDash()` / `lineDashOffset` | Canvas-unit lengths; get returns an owned list; odd-length patterns follow upstream duplication |
| `lineDashMarker` / `lineDashFit` | Path2D marker and original dash-fitting extension |
| `globalAlpha` | 0–1; default 1 |
| `globalCompositeOperation` | Default `"source-over"`; original modes such as `"multiply"`, `"screen"` |
| `filter` | CSS filter string, e.g. `"blur(2px)"`; default `"none"` |
| `shadowColor` / `shadowBlur` / `shadowOffsetX/Y` | CSS color, blur, and offsets; offsets in canvas units |
| `imageSmoothingEnabled` / `imageSmoothingQuality` | Image scaling/sampling controls |

Sources: [Context public API](../../../python/py_skia_canvas/__init__.py), [argument specifications](../../../python/py_skia_canvas/_argument_specs.py), [effects bindings](../../../python/py_skia_canvas/_effects.py), [shared Context](../../../crates/canvas-core/src/context).

## 4. Path2D, gradients, patterns, and textures

| Object/entry | Result and use |
| --- | --- |
| `Path2D()` / `Path2D(svg_string)` / `Path2D(path)` | Empty path, SVG path, or original COW copy; native access is owner-only |
| Path `moveTo/lineTo/arc/ellipse/rect/roundRect/...` | Build geometry, usually returning `None`; units match corresponding Context methods |
| `path.d` | Read/write SVG path string; invalid constructor SVG differs from assigning invalid SVG to an existing path |
| `path.bounds` / `path.edges` | Owned Python bounds dict / verb data; these do not transfer a drawable native Path |
| `path.contains(x,y)` | Returns containment `bool` |
| `path.addPath(other, matrix)` | Adds another path to this one; matrix has an omitted-argument overload |
| `path.transform(matrix)` | Returns a new transformed Path2D |
| `difference/intersect/union/xor/complement(other)` | Returns a new Boolean-operation Path2D; do not assume in-place mutation |
| `simplify/unwind/offset/round/trim/jitter/points` | Original extensions; check source signatures/ledger for special parameters rather than importing another library's algorithms |
| `ctx.createLinearGradient(x0,y0,x1,y1)` | Returns CanvasGradient |
| `ctx.createRadialGradient(x0,y0,r0,x1,y1,r1)` | Returns CanvasGradient; radii in canvas units |
| `ctx.createConicGradient(angle,x,y)` | Angle in radians; returns CanvasGradient |
| `gradient.addColorStop(offset, color)` | Offset 0–1, CSS color string; original f32 range validation; returns `None` |
| `ctx.createPattern(source, repetition)` | Image/Canvas and other supported sources; explicitly pass `"repeat"`, `"repeat-x"`, `"repeat-y"`, or `"no-repeat"` |
| `pattern.setTransform(matrix)` | Updates pattern transform, preserving original shared-style semantics |
| `ctx.createTexture(spacing, options)` | Scalar or two-element spacing; returns CanvasTexture |

Common texture options: `path`, `color`, `line`, `cap`, `angle`, `offset`, `outline`. Spacing, stroke width, and offsets use canvas units; angle uses radians. Prefer Context factories instead of guessing low-level public-class constructor parameters.

Sources: [Path](../../../python/py_skia_canvas/_path.py), [Gradient](../../../python/py_skia_canvas/_gradient.py), [Pattern/Texture](../../../python/py_skia_canvas/_shaders.py). See `paths`, `images`, and `effects` [demos](DEMOS.en.md).

## 5. Text, TextMetrics, and FontLibrary

| Entry | Result/units/notes |
| --- | --- |
| `ctx.font` | CSS font string, e.g. `"24px sans-serif"`; default `"10px sans-serif"` |
| `fillText(text,x,y[,maxWidth])` / `strokeText(...)` | Draws text; positions and maxWidth in canvas units; y follows textBaseline |
| `measureText(text[,maxWidth])` | Returns TextMetrics; use the same font/layout state/width as drawing |
| `outlineText(text[,maxWidth])` | Returns outline Path2D; position with later path/Context transforms |
| `textAlign` / `textBaseline` / `direction` | Common values: `left/center/right/start/end`, `alphabetic/top/middle/...`, `ltr/rtl/inherit` |
| `textWrap` | `True` with maxWidth enables original multiline layout |
| `fontStretch` / `fontVariant` / `fontHinting` | Original text extension state |
| `letterSpacing` / `wordSpacing` / `textDecoration` | CSS spacing and decoration; check accepted string forms |
| `textTracking` | Retained legacy extension; prefer explicit spacing properties for new code |

TextMetrics `width`, `actualBoundingBoxLeft/Right/Ascent/Descent`, `fontBoundingBoxAscent/Descent`, `emHeightAscent/Descent`, and baselines use canvas units. `lines` is a list of mapping data with UTF-16 code-unit offsets. Initial top-level fields are read-only; nested lists/dicts retain ordinary mutable-data semantics, not deep immutability.

| FontLibrary entry | Purpose |
| --- | --- |
| `FontLibrary.use(file_or_list)` | Registers one or more string file paths; returns font metadata |
| `FontLibrary.use(alias, file_or_list)` | Registers under a family alias |
| `FontLibrary.use({alias: file_or_list})` | Registers multiple alias groups |
| `FontLibrary.families` | Snapshot of visible family names |
| `FontLibrary.has(name)` | Original family-name membership; not glyph coverage |
| `FontLibrary.family(name)` | Family metadata, or `undefined` if absent |
| `FontLibrary.reset()` | Clears the calling thread's custom fonts and associated caches |

FontLibrary is a singleton facade, but **registration and caches belong to the calling thread**. Each drawing worker registers its fonts. Invalid/unreadable files and invalid arguments retain original input/file errors. Local rendering rights do not automatically grant font redistribution rights.

Sources: [text entries](../../../python/py_skia_canvas/_text_api.py), [text state](../../../python/py_skia_canvas/_text_state.py), [metrics](../../../python/py_skia_canvas/_metrics.py), [fonts](../../../python/py_skia_canvas/_fonts.py).

## 6. Image, ImageData, and pixels

| Entry | Parameters and result |
| --- | --- |
| `await loadImage(source[, options])` | Encoded bytes, local file, data URL, HTTP URL → loaded Image |
| `Image(encoded_bytes)` | Synchronously decodes obtained encoded bytes; native access is owner-only |
| `image.src = source` / `await image.decode()` | Load/wait; decode returns Image; original onload/onerror lifecycle |
| `image.width` / `height` / `complete` | Decoded dimensions/load state; finish loading before drawing |
| `ImageData(width,height[,settings])` | Allocates pixel storage; default `rgba/srgb` |
| `ImageData(raw_bytes,width,height[,settings])` | Creates from raw pixels; length/layout must match |
| `ImageData(image)` / `ImageData(other_data)` | Reads pixels from an Image or copies pixel data |
| `image_data.data` | Fixed-length writable clamped byte view; not PNG/JPG data |
| `await loadImageData(source,width,height[,settings])` | Fetches raw pixels and constructs ImageData; does not decode PNG |
| `ctx.createImageData(width,height[,settings])` | Creates empty pixel storage by size; copy storage with `ImageData(other_data)` |
| `ctx.getImageData(x,y,w,h[,settings])` | Independent ImageData readback; default rgba is four bytes per pixel |
| `ctx.putImageData(data,dx,dy[,dirtyX,dirtyY,dirtyW,dirtyH])` | Direct pixel write; do not apply drawImage transform/compositing assumptions |
| `ctx.drawImage(source,...)` | Original 3/5/9-argument forms, described in the usage guide |
| `ctx.drawCanvas(...)` | Original Canvas-drawing extension; check ledger/source before using its overload |

ImageData `width/height/colorSpace/colorType` metadata is read-only. Format names in settings are case-sensitive. For ordinary RGBA, explicit `{"colorType":"rgba"}` makes the layout clear. Other formats have their own byte/channel layouts and must not all be treated as RGBA.

Propagate image/network failures rather than substituting an empty successful image. Python network host options do not reproduce Node Agent/Stream object identities; see the host profile.

Sources: [images and pixels](../../../python/py_skia_canvas/_imagery.py), [Python HTTP host](../../../python/py_skia_canvas/_http.py).

## 7. Exports

| Synchronous entry | Async counterpart | Result |
| --- | --- | --- |
| `toBufferSync(extension="png", opts=undefined)` | `toBuffer(...)` | bytes / await bytes |
| `toFileSync(filename, opts=undefined)` | `toFile(...)` | None / await None |
| `toURLSync(extension="png", opts=undefined)` | `toURL(...)` | data URL str / await str |
| `toDataURL(extension="png", quality=undefined)` | — | Synchronous data URL; legacy browser-style second argument is quality |

`canvas.png/jpg/webp/pdf/svg/raw` are awaitable properties, e.g. `png = await canvas.png`. Prefer canonical entries with explicit format/options. `toSharp()` requires Node Sharp and raises the missing-dependency error in standalone Python.

| Option | Default/range | Meaning |
| --- | --- | --- |
| `quality` | `0.92`, 0–1 | Original codec's lossy quality option; not used by every format |
| `density` | `1`, positive integer | Raster scale; 2× doubles width and height |
| `matte` | Unspecified | CSS background for compositing/opaque output |
| `page` | Unspecified | 1-based; negative from the end; omitted means multipage PDF or latest page for other single files |
| `outline` | False | PDF/SVG text outlines |
| `downsample` | False | Original image processing option for vector exports |
| `colorType` | Original format default | Raw pixel layout; same format names as ImageData |
| `msaa` | Original device default | Original GPU sampling option, device-dependent; not a CPU rendering switch |
| `format` | Inferred from filename | Explicit format for file entries |

Formats: `png/jpg/webp/raw/pdf/svg`. PNG/JPG/WebP are encoded images; raw contains no dimensions or other metadata. File names support padded sequences such as `page-{2}.png` and density inference such as `@2x`. Prefer explicit options in AI-generated code.

Start async exports on the owner thread. The core materializes a transferable picture snapshot at call time; later drawing does not change it. Results can be awaited repeatedly; cancelling one waiter does not guarantee cancellation of encoding. ExportPromise is awaitable, not necessarily accepted directly by `asyncio.run/create_task`; wrap it in a coroutine.

Handle missing/unsupported formats, invalid options, out-of-range pages, unwritable files, and encoding errors. Windows default parallel PDF/SVG file sequences retain the upstream glyph-loss limitation; explicit `RAYON_NUM_THREADS=1` is documented in [troubleshooting](TROUBLESHOOTING.en.md).

Sources: [normalization and async facade](../../../python/py_skia_canvas/_exports.py), [shared Page core](../../../crates/canvas-core/src/context/page.rs).

## 8. DOM value objects

| Object | Common entries and units |
| --- | --- |
| `DOMPoint(x=0,y=0,z=0,w=1)` | Point values; `matrixTransform(matrix)` returns the transformed point; `toJSON()` returns plain data |
| `DOMRect(x=0,y=0,width=0,height=0)` | Rectangle values; derived left/top/right/bottom; fromRect/toJSON |
| `DOMMatrix()` | Identity by default; accepts 6/16-element sequences or CSS transform strings |
| Matrix properties | `a,b,c,d,e,f`, `m11...m44`, `is2D`, `isIdentity` |
| Matrix operations | `translate/scale/rotate/skewX/skewY/multiply/...` and Self forms; non-Self methods usually return a new matrix |
| Conversion | `transformPoint(point)`, `toFloat32Array()`, `toFloat64Array()`, `toJSON()`, `toString()` |

Matrix rotation/skew uses **degrees**; translation uses the surrounding coordinate units. Preserve upstream's special inversion behavior: for invertible 2D input, `invertSelf()` returns a new matrix without changing the original; a singular matrix receives NaNs and returns `undefined`; 3D inversion raises an unimplemented error. Do not infer browser-standard behavior merely from Self method names.

Sources: [DOM data](../../../python/py_skia_canvas/_geometry.py), [original matrix-operation mapping](../../../python/py_skia_canvas/_matrix_ops.py).

## 9. App / Window

App is a singleton; Window is a main-thread GPU/desktop object. CPU offscreen support does not include software window presentation.

| Entry | Behavior |
| --- | --- |
| `Window(width,height,options)` / `Window(options)` | Default 512×512; options include title, visible, resizable, background, canvas, and others |
| `window.canvas` / `window.ctx` / `window.page` | Associated Canvas, selected-page Context, 1-based page |
| `window.on(event,callback)` / `once` / `off` | Original drawing, window, pointer, keyboard, and other events |
| `window.on("draw", callback)` | Callback receives an event with `event.frame`; reapply needed drawing state each frame |
| `window.close()` / `open()` | Closes/opens; affects App session continuation |
| `App.fps` | Drawing frame rate |
| `App.windows` / `App.running` / `App.eventLoop` | Active window list, started-once flag, original event-loop mode name |
| `App.launch()` | Awaitable session; supports `asyncio.run(App.launch())` |
| `App.quit()` | Requests exit |

Dimensions are logical window/canvas units; desktop scaling affects physical pixels. Missing native backend support fails explicitly, e.g. `No windowing support`. See the complete automatically terminating [example](../../../examples/ai_demos.py); constructing a Window without running its loop is not a successful window execution.

`App.running` retains the original started-once flag and can remain True after idle; do not use it alone to decide whether a window remains active.

Sources: [GUI](../../../python/py_skia_canvas/_gui.py), [event mapping](../../../python/py_skia_canvas/_events.py).
