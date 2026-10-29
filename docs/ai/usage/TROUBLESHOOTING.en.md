# Usage troubleshooting

[中文](TROUBLESHOOTING.md) | English

Record `python --version`, package version/path, OS/architecture, `canvas.engine`, input dimensions/format, and the full exception. Start a minimal reproduction with one opaque rectangle, then add text, images, effects, and pages.

| Symptom | Investigation and action |
| --- | --- |
| pip finds no matching distribution | Confirm CPython 3.13, Windows AMD64 or Linux glibc 2.28+ x86_64, and fixed `==0.1.0a18`. This initial release has no other ABI wheels or PyPI sdist. |
| Windows license installation reports a missing/long path | Use a shorter virtual-environment prefix; respect the MAX_PATH deployment boundary. Rebuilding the renderer is unnecessary. |
| Imported version/path is unexpected | Check the interpreter running your script and `py_skia_canvas.__version__` / `__file__`. Look for a shadowing file or old package in the current directory. |
| engine reports CPU | Offscreen apps can use the original CPU fallback. If GPU/window support is required, inspect drivers, Vulkan, and desktop availability; report missing requirements accurately. |
| Constructor `gpu=False` still shows GPU behavior | Set `canvas.gpu = False` after construction. The constructor flag preserves upstream 3.0.8 behavior. |
| Window reports No windowing support | The original presentation backend requires GPU/desktop support. Create it on the main thread; use offscreen Canvas for server jobs. |
| Missing CJK/emoji or different wrapping on another machine | Check the exact font file, face/alias, registration thread, and actual glyph coverage. `FontLibrary.has` checks families only. Do not compensate shaping character by character. |
| Zero image dimensions or missing image | Finish `await loadImage(...)` / `await image.decode()` before drawing. Check encoded-versus-raw data and path readability. |
| Wrong pixel colors/length | Default ImageData is rgba/srgb, four bytes per pixel. Explicit colorType changes the layout. Account for alpha, matte, and color space; raw is not PNG. |
| Misplaced text | `fillText` y follows the selected baseline. Set font/textBaseline/textAlign and measure consistently. DOMMatrix uses degrees; Context uses radians. |
| Output contains only the last page | Non-PDF single-file exports default to the latest page. Select `page=1` or use a PNG sequence; PDF can include all pages. |
| Changing dimensions removes drawing/state | Dimension setters reset the current page. Set dimensions before drawing or redraw explicitly. |
| `opts=None` raises an error | None maps to JS null. Omit the argument or pass a dict rather than treating None as default options. |
| asyncio.run rejects the awaitable | Await `canvas.toBuffer(...)` inside `async def main()`, then call `asyncio.run(main())`. |
| Foreign-thread RuntimeError | Use native objects on their creating thread. Each worker creates its own Canvas and returns bytes; do not transfer Context/Path/Image/style resources. |
| ctx.canvas becomes undefined | Retain a strong Canvas reference; Context's parent access is weak. |
| Intermittent missing glyphs in Windows PDF/SVG file sequences | Inherited upstream parallel-sequence limitation. Set `RAYON_NUM_THREADS=1` before process startup and verify the required output. |
| toSharp reports a missing dependency | This Python host profile retains the same-name missing-dependency error. Obtain bytes and use the Python image tool needed by your application. |
| Invalid arguments seem not to raise | Some setters/methods ignore invalid inputs as upstream does. Inspect current values/state. Set STRICT before process startup; do not assume uniform exceptions. |

## Report a reproducible issue

Provide a minimal script using public APIs, pinned version, input provenance/license, backend/fonts, and expected versus actual output. Start from the [hello example](../../../examples/ai_demos.py). Preserve original outputs; compare complete RGBA, including RGB under zero alpha.

Maintainers additionally build a candidate wheel, compare with pinned official Node A, and preserve independent evidence; see the [development guide](../development/README.en.md). Application code should not depend on `_native`, `_debug_*`, or other internal diagnostic APIs.
