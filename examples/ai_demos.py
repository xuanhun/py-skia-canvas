"""Executable application examples for py-skia-canvas 0.1.0a18.

Run --help. Coordinates are canvas units; image dimensions are pixels. Output is
written to a NEW directory. All native objects stay on their creator thread.
These examples call the public API; they implement no renderer or font engine.
"""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import struct

from py_skia_canvas import (
    App, Canvas, DOMMatrix, DOMPoint, FontLibrary, ImageData, Path2D,
    Window, __version__, loadImage,
)


def make_canvas(width, height, backend):
    """Create an owner-local Canvas; dimensions in canvas units, backend is a name.

    Return Canvas or raise if a requested backend is unavailable. 'auto' retains
    the library default; 'cpu' uses its public setter. Source: Canvas.gpu/getContext.
    """
    canvas = Canvas(width, height)
    if backend == 'cpu':
        canvas.gpu = False
    expected = {'cpu': 'CPU', 'gpu': 'GPU'}.get(backend)
    if expected and canvas.engine['renderer'] != expected:
        raise RuntimeError(f'Required {expected}, got {canvas.engine}')
    return canvas


def write_bytes(path, data):
    """Write owned bytes, return JSON-safe size/SHA metadata; propagate I/O errors.

    No native resources or thread restriction. Source: stdlib application I/O.
    """
    assert isinstance(data, bytes) and len(data) > 8
    path.write_bytes(data)
    result = {'name': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        result['pixels'] = list(struct.unpack('>II', data[16:24]))
    return result


def preview(canvas, out, name='preview.png'):
    """Export owner Canvas to PNG; return file metadata, propagate export/I/O errors.

    Source: Canvas.toBufferSync; no object crosses a thread boundary.
    """
    return write_bytes(out / name, canvas.toBufferSync('png'))


def label(ctx, text, x, y, size=24):
    """Draw Latin label at a baseline in canvas units on the owner thread.

    Returns None; original font/draw errors propagate. Source: Context font/fillText.
    """
    ctx.font = f'{size}px sans-serif'
    ctx.fillStyle = '#16243a'
    ctx.fillText(text, x, y)


def hello(out, backend, font_file=None, hidden=False):
    """Render a 360x180 starter card; return output/backend metadata, owner only.

    Source: Context fillRect/fillText/getImageData and Canvas.toBufferSync.
    """
    c = make_canvas(360, 180, backend)
    x = c.getContext('2d')
    x.fillStyle = 'white'
    x.fillRect(0, 0, 360, 180)
    x.fillStyle = '#2878d9'
    x.fillRect(20, 20, 320, 80)
    label(x, 'Hello Canvas', 20, 145)
    assert bytes(x.getImageData(30, 30, 1, 1).data) == bytes([40, 120, 217, 255])
    return {'engines': [c.engine], 'files': [preview(c, out)]}


def paths(out, backend, font_file=None, hidden=False):
    """Show boolean paths, gradient, transforms and a degree-based DOMMatrix.

    Canvas lengths in units; Context.rotate uses radians. Native paths remain
    owner-local. Returns file/geometry metadata; original errors propagate.
    Source: Path2D.difference/transform, Context gradients/save/restore, DOM values.
    """
    c = make_canvas(520, 280, backend)
    x = c.getContext('2d')
    x.fillStyle = '#f1f5fb'
    x.fillRect(0, 0, 520, 280)
    outer = Path2D()
    outer.arc(130, 135, 85, 0, math.tau)
    inner = Path2D()
    inner.arc(130, 135, 42, 0, math.tau)
    ring = outer.difference(inner)
    gradient = x.createLinearGradient(40, 40, 220, 220)
    gradient.addColorStop(0, '#2878d9')
    gradient.addColorStop(1, '#8d4bc7')
    x.fillStyle = gradient
    x.fill(ring, 'evenodd')
    shape = Path2D('M0 0 L110 0 L55 95 Z')
    matrix = DOMMatrix().translate(320, 80).rotate(15)
    transformed = shape.transform(matrix)
    x.fillStyle = '#f0ad32'
    x.fill(transformed)
    x.save()
    x.translate(325, 230)
    x.rotate(-math.pi / 12)
    x.strokeStyle = '#24364b'
    x.lineWidth = 3
    x.strokeRect(-40, -20, 140, 35)
    x.restore()
    point = DOMPoint(0, 0).matrixTransform(matrix)
    assert ring.contains(190, 135) and not ring.contains(130, 135)
    assert list(x.getImageData(130, 135, 1, 1).data) == [241, 245, 251, 255]
    return {'engines': [c.engine], 'files': [preview(c, out)], 'mappedOrigin': [point.x, point.y]}


def text(out, backend, font_file=None, hidden=False):
    """Draw wrapped/RTL text and optional caller-supplied font; return metrics.

    Font sizes/coordinates are canvas units, line offsets use UTF-16. Font file
    is read but never copied to outputs. Owner-thread registration and drawing.
    Source: FontLibrary.use/has, Context text state/measureText/fillText.
    """
    family = 'sans-serif'
    if font_file:
        FontLibrary.use('DemoFace', str(font_file.resolve(strict=True)))
        assert FontLibrary.has('DemoFace')
        family = 'DemoFace'
    c = make_canvas(560, 300, backend)
    x = c.getContext('2d')
    x.fillStyle = 'white'
    x.fillRect(0, 0, 560, 300)
    x.font = f'28px "{family}"' if font_file else '28px sans-serif'
    x.fillStyle = '#263d62'
    x.textBaseline = 'alphabetic'
    x.textWrap = True
    content = 'Canvas text: AV ffi cafe\u0301 / 中文 / مرحبا / emoji 😀'
    metrics = x.measureText(content, 500)
    x.fillText(content, 25, 55, 500)
    x.textDecoration = 'underline #2878d9'
    x.fillText('Wrapped text uses the installed fonts.', 25, 180, 500)
    x.textDecoration = 'none'
    x.direction = 'rtl'
    x.textAlign = 'right'
    x.fillText('مرحبا بالعالم', 530, 265)
    assert metrics.width > 0
    return {'engines': [c.engine], 'files': [preview(c, out)], 'metrics': {
        'width': metrics.width, 'ascent': metrics.actualBoundingBoxAscent,
        'descent': metrics.actualBoundingBoxDescent, 'lineCount': len(metrics.lines),
    }, 'fontRegistration': family}


def images(out, backend, font_file=None, hidden=False):
    """Generate/load a local PNG, crop it, repeat a pattern and edit RGBA pixels.

    Dimensions are pixels; drawing is on one asyncio/owner thread. Returns plain
    output metadata, propagates load/decode/export errors. Source: loadImage,
    Context drawImage/createPattern/putImageData/getImageData.
    """
    async def render():
        """Await encoded-image loading on its owner loop; no native objects move."""
        tile = make_canvas(48, 48, backend)
        tx = tile.getContext('2d')
        tx.fillStyle = '#2878d9'
        tx.fillRect(0, 0, 48, 48)
        tx.fillStyle = '#ffd662'
        tx.fillRect(0, 0, 24, 24)
        tx.fillRect(24, 24, 24, 24)
        image = await loadImage(tile.toBufferSync('png'))
        c = make_canvas(560, 280, backend)
        x = c.getContext('2d')
        x.fillStyle = 'white'
        x.fillRect(0, 0, 560, 280)
        x.drawImage(image, 20, 20, 160, 160)
        x.drawImage(image, 0, 0, 24, 24, 205, 20, 135, 135)
        pattern = x.createPattern(image, 'repeat')
        pattern.setTransform(DOMMatrix().scale(0.5))
        x.fillStyle = pattern
        x.fillRect(370, 20, 170, 170)
        pixels = ImageData(bytes([255, 0, 0, 255] * 64), 8, 8)
        x.putImageData(pixels, 30, 220)
        assert bytes(x.getImageData(30, 220, 1, 1).data) == bytes([255, 0, 0, 255])
        label(x, 'scaled / cropped / repeated', 65, 240, 20)
        return {'engines': [tile.engine, c.engine], 'files': [preview(c, out)], 'sourcePixels': [image.width, image.height]}
    return asyncio.run(render())


def effects(out, backend, font_file=None, hidden=False):
    """Draw shadows, filters, alpha/compositing and native line texture.

    Coordinates/blur are canvas units, texture angle radians. Owner thread only;
    returns file metadata and propagates original API errors. Source: Context
    effects/createTexture and the single shared Rust paint/filter implementation.
    """
    c = make_canvas(560, 260, backend)
    x = c.getContext('2d')
    x.fillStyle = 'white'
    x.fillRect(0, 0, 560, 260)
    x.save()
    x.shadowColor = '#435d8b'
    x.shadowBlur = 12
    x.shadowOffsetX = 6
    x.shadowOffsetY = 8
    x.fillStyle = '#2878d9'
    x.fillRect(25, 40, 120, 130)
    x.restore()
    x.save()
    x.filter = 'blur(2px)'
    x.fillStyle = '#f0ad32'
    x.fillRect(195, 40, 115, 100)
    x.filter = 'none'
    x.globalCompositeOperation = 'multiply'
    x.globalAlpha = 0.7
    x.fillStyle = '#2878d9'
    x.fillRect(235, 85, 110, 95)
    x.restore()
    texture = x.createTexture(12, {'color': '#596c8a', 'line': 2, 'angle': math.pi / 4})
    x.fillStyle = texture
    x.fillRect(385, 40, 145, 145)
    label(x, 'shadow / blend / texture', 25, 235, 23)
    return {'engines': [c.engine], 'files': [preview(c, out)]}


def exports(out, backend, font_file=None, hidden=False):
    """Export six formats, 2x raster and data URL; owner thread, output bytes.

    Density is a positive integer scale; quality 0..1. Source: Canvas sync export
    methods. Assertions inspect signatures/sizes, not codec implementation details.
    """
    c = make_canvas(360, 180, backend)
    x = c.getContext('2d')
    x.fillStyle = '#e9f1fc'
    x.fillRect(0, 0, 360, 180)
    label(x, 'One scene, six formats', 20, 95, 24)
    files = []
    for fmt in ('png', 'jpg', 'webp', 'raw', 'pdf', 'svg'):
        opts = {'quality': 0.9, 'matte': 'white'}
        if fmt == 'raw':
            opts['colorType'] = 'rgba'
        data = c.toBufferSync(fmt, opts)
        if fmt == 'raw':
            assert len(data) == 360 * 180 * 4
        if fmt == 'pdf':
            assert data.startswith(b'%PDF-')
        files.append(write_bytes(out / ('scene.' + fmt), data))
    files.append(write_bytes(out / 'scene@2x.png', c.toBufferSync('png', {'density': 2})))
    assert files[-1]['pixels'] == [720, 360]
    url = c.toURLSync('png')
    assert url.startswith('data:image/png;base64,')
    return {'engines': [c.engine], 'files': files, 'dataUrlPrefix': url[:22]}


def pages(out, backend, font_file=None, hidden=False):
    """Export a three-page PDF and PNG sequence; pages use 1-based export indexes.

    Native pages remain owned by this thread. Returns plain metadata; file/range
    errors propagate. Source: Canvas.newPage/pages/toFileSync/exportOptions.
    """
    c = make_canvas(480, 240, backend)
    for index, color in enumerate(('#e1edff', '#ffefcf', '#e0f5ee'), 1):
        x = c.getContext('2d') if index == 1 else c.newPage()
        x.fillStyle = color
        x.fillRect(0, 0, 480, 240)
        label(x, f'Page {index}', 30, 125, 40)
    assert len(c.pages) == 3
    c.toFileSync(out / 'pages.pdf')
    c.toFileSync(out / 'page-{2}.png')
    c.toFileSync(out / 'first.png', {'page': 1})
    c.toFileSync(out / 'last.png', {'page': -1})
    files = [write_bytes(p, p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()]
    assert len(list(out.glob('page-*.png'))) == 3
    return {'engines': [c.engine], 'files': files, 'pageCount': len(c.pages)}


def asynchronous(out, backend, font_file=None, hidden=False):
    """Show awaitable export snapshots and concurrent waiting on one owner loop.

    The call to toBuffer occurs on owner; only export bytes leave it. Returns file
    metadata, propagates validation/encoding/async errors. Source: Canvas.toBuffer/toFile.
    """
    async def render():
        """Create/start tasks and draw on the same loop; await original export jobs."""
        c = make_canvas(240, 120, backend)
        x = c.getContext('2d')
        x.fillStyle = 'red'
        x.fillRect(0, 0, 240, 120)
        first = c.toBuffer('png')
        x.fillStyle = 'green'
        x.fillRect(0, 0, 240, 120)
        second = c.toBuffer('png')
        before, after = await asyncio.gather(first, second)
        assert before != after
        await c.toFile(out / 'async.pdf')
        files = [write_bytes(out / 'before.png', before), write_bytes(out / 'after.png', after)]
        files.append(write_bytes(out / 'async.pdf', (out / 'async.pdf').read_bytes()))
        return {'engines': [c.engine], 'files': files, 'snapshotChanged': before != after}
    return asyncio.run(render())


def batch(out, backend, font_file=None, hidden=False):
    """Create independent canvases inside workers and return bytes, never contexts.

    Workload is three 160x100 images. Each worker owns all its native resources;
    failures propagate through Future.result. Source: Canvas thread ownership contract.
    """
    def worker(color):
        """Own one Canvas for its whole lifetime; return only bytes and copied status."""
        c = make_canvas(160, 100, backend)
        x = c.getContext('2d')
        x.fillStyle = color
        x.fillRect(0, 0, 160, 100)
        return c.toBufferSync('png'), c.engine
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(worker, ('#2878d9', '#f0ad32', '#3aa885')))
    files = [write_bytes(out / f'job-{i}.png', data) for i, (data, _) in enumerate(results, 1)]
    return {'engines': [engine for _, engine in results], 'files': files, 'independentWorkers': True}


def window(out, backend, font_file=None, hidden=False):
    """Run a main-thread native GPU window for five frames, save PNG then close.

    Window dimensions are logical pixels; frame is an integer. --hidden is for
    automated verification. Requires display/GPU, never a CPU substitute.
    Source: App.launch/fps, Window.ctx/on/close and original GUI callbacks.
    """
    if backend == 'cpu':
        raise RuntimeError('The original Window presentation backend requires GPU')
    win = Window(480, 300, {'title': 'py-skia-canvas example', 'visible': not hidden})
    if win.canvas.engine['renderer'] != 'GPU':
        raise RuntimeError('Window requires a working GPU backend')
    files = []
    frames = []
    App.fps = 30

    def draw(event):
        """Draw on main/owner thread; export at frame 4 and queue native close."""
        frames.append(event.frame)
        x = win.ctx
        x.fillStyle = 'white'
        x.fillRect(0, 0, 480, 300)
        x.fillStyle = '#2878d9'
        x.fillRect(25 + event.frame * 8, 45, 140, 140)
        label(x, f'Frame {event.frame}', 25, 245, 30)
        if event.frame >= 4:
            files.append(preview(win.canvas, out))
            win.close()
    win.on('draw', draw)
    asyncio.run(App.launch())
    assert files and max(frames) >= 4
    return {'engines': [win.canvas.engine], 'files': files, 'frames': frames}


DEMOS = {'hello': hello, 'paths': paths, 'text': text, 'images': images, 'effects': effects,
         'exports': exports, 'pages': pages, 'async': asynchronous, 'batch': batch, 'window': window}


def main():
    """Parse CLI, run requested public-API demos, write JSON evidence or raise.

    --out is a fresh directory, --font-file optional user-owned resource. All
    scenes run on main thread except explicit batch owners. No hidden fallback.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('demo', choices=[*DEMOS, 'all'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--backend', choices=['auto', 'gpu', 'cpu'], default='auto')
    parser.add_argument('--font-file', type=Path)
    parser.add_argument('--include-window', action='store_true')
    parser.add_argument('--hidden', action='store_true')
    args = parser.parse_args()
    if args.backend == 'cpu' and (args.demo == 'window' or args.include_window):
        parser.error('Window requires GPU; CPU examples cover offscreen rendering and exports')
    args.out.mkdir(parents=True, exist_ok=False)
    names = [name for name in DEMOS if name != 'window' or args.include_window] if args.demo == 'all' else [args.demo]
    results = []
    for name in names:
        target = args.out / name
        target.mkdir()
        result = DEMOS[name](target, args.backend, args.font_file, args.hidden)
        result.update(demo=name, version=__version__, backendRequested=args.backend)
        (target / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        results.append(result)
        print(name, 'completed', flush=True)
    (args.out / 'summary.json').write_text(json.dumps({'status': 'EXAMPLES_COMPLETED', 'results': results,
        'windowRequested': args.demo == 'window' or args.include_window,
        'scope': 'Application examples and output assertions; not an upstream parity or release acceptance verdict.'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
