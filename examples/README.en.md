# Runnable examples

[中文](README.md) | English

Use the published `py-skia-canvas==0.1.0a18`, CPython 3.13, and the wheel for your platform. Application examples depend only on the standard library and this package; Node/Rust are unnecessary.

```shell
python -m pip install --only-binary=:all: py-skia-canvas==0.1.0a18
python examples/ai_demos.py --help
python examples/ai_demos.py all --out test-runs/my-demos-001
```

`--out` must name a new directory. The default `--backend auto` preserves the original GPU/CPU policy. Explicit `--backend cpu` uses the CPU setter; `--backend gpu` requires an actual GPU backend. Window presentation requires a usable GPU and desktop.

| Demo | Content |
| --- | --- |
| `hello` | Complete first image, PNG output, pixel assertion |
| `paths` | Path2D Boolean operations, gradients, DOMMatrix and Context transforms |
| `text` | Languages, wrapping, RTL, decoration, TextMetrics; optional `--font-file` |
| `images` | Load bytes, scale/crop, patterns, raw pixels |
| `effects` | Shadows, filters, compositing, textures |
| `exports` | PNG/JPG/WebP/raw/PDF/SVG, density, data URLs |
| `pages` | Multipage PDF, page selection, file sequences |
| `async` | Call-time snapshots, concurrent waiting, async files |
| `batch` | Each worker creates its own Canvas and returns bytes |
| `window` | Main-thread GPU window, closing automatically after a few frames |

`all` runs the first nine demos. Run the window separately, or add `--include-window`. `window --hidden` still needs a GUI backend. Each demo writes outputs and `result.json`; the top-level `summary.json` records version, actual engines, dimensions, hashes, and other results.

See the [demo guide](../docs/ai/usage/DEMOS.en.md) for explanations and recipes, and the [API reference](../docs/ai/usage/API_REFERENCE.en.md) for signatures. Documentation separates [using the library](../docs/ai/usage/README.en.md) from [developing the library](../docs/ai/development/README.en.md).

The [gallery](../docs/ai/usage/DEMOS.en.md#actual-output-gallery) embeds actual outputs, including three pages, two async snapshots, three parallel jobs, and a window frame.

`development/parity-smoke.json` contains two shared Node/Python tutorial scenes. It requires the pinned official oracle and an installed wheel; follow the [development workflow](../docs/ai/development/WORKFLOW.en.md). This test fixture is not an application drawing API.
