# py-skia-canvas

[中文](README.md) | English

A standalone Python Canvas library using the original Rust/Skia core from `skia-canvas@3.0.8`, with its default GPU policy preserved. Python wheels require no Node, npm, Neon/N-API, or skia-python.

## Install from production PyPI

Version `0.1.0a18` is published on [production PyPI](https://pypi.org/project/py-skia-canvas/0.1.0a18/) as an alpha prerelease. Requires **CPython 3.13**; supported wheels target Windows AMD64 and Linux glibc 2.28+ x86_64.

```shell
python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
python -c "import py_skia_canvas as c; print(c.__version__, c.__file__)"
```

See [English installation](docs/ai/INSTALL.en.md) / [中文安装说明](docs/ai/INSTALL.md). AI can read [llms.txt](llms.txt) directly. Using the wheel needs no Node/npm or Rust toolchain.

## Capabilities and example

Migrated capabilities include Canvas/Context, Path2D and its extensions, DOM geometry/matrices/CSS transforms, gradients, fonts and text shaping/layout/measurement/decoration, images/pixels/patterns/textures, filters/compositing, multiple pages, synchronous/asynchronous exports, and App/Window. Public names and defaults follow Node; language-specific values use the accepted [Python host profile](docs/PYTHON_HOST_PROFILE.md).

Current version: **0.1.0a18**. Accepted wheels target **CPython 3.13 / Windows AMD64 / Linux glibc 2.28+ x86_64**. [PyPI](https://pypi.org/project/py-skia-canvas/0.1.0a18/), [TestPyPI](https://test.pypi.org/project/py-skia-canvas/0.1.0a18/), and the [GitHub alpha Release](https://github.com/xuanhun/py-skia-canvas/releases/tag/v0.1.0a18) have been published and independently installed and checked on both platforms. Windows Vulkan and Linux Vulkan were accepted separately. macOS Metal source/features remain available, but no macOS release artifact has been accepted. See the [completion report](docs/COMPLETION_REPORT.md) for wheel hashes and scope, and [release status](docs/RELEASE_STATUS.md) for publication records.

```python
from py_skia_canvas import Canvas

canvas = Canvas(300, 150)
ctx = canvas.getContext("2d")
ctx.fillStyle = "#2878d9"
ctx.fillRect(10.25, 11.75, 113.5, 63.25)
ctx.font = "24px sans-serif"
ctx.fillStyle = "black"
ctx.fillText("Canvas AV fj", 10.25, 110)
with open("example.png", "wb") as output:
    output.write(canvas.toBufferSync("png"))
```

Synchronous Buffers map to bytes, Promises to actual awaitables, and the `undefined` singleton and `None` to undefined and null respectively. Sharp is a Node host dependency: same-name entry points raise the original missing-Sharp error. Use `toBuffer/toFile` for image output. The library does not start Node or return placeholder Sharp/Stream objects.

Use Canvas, Context, fonts, and GPU resources on their creating thread; foreign-thread drawing raises an error. Asynchronous exports first materialize an original-core snapshot on that thread; background work receives only transferable data. On Windows, thread-local resources and the original GPU context are released before a Python worker exits. GPU contexts are never handed to a Python thread pool.

System fonts and drivers affect output. The project records font provenance/fingerprints without bundling system fonts. Validation compares JSON numbers, full RGBA, and decoded pixels exactly, including RGB differences where alpha is zero. Default GPU acceptance and CPU diagnostics are separate.

Without a usable GPU, offscreen rendering automatically uses CPU. Offscreen drawing and every export format passed CPU acceptance on both platforms, including a container with no Vulkan library. See the [CPU report](docs/CPU_RENDER_REPORT.md). App/Window presentation retains the original GPU requirement; the report also records the inherited Windows parallel PDF/SVG sequence limitation.

## AI usage and development documentation

Choose a task at the [AI documentation entry](docs/ai/README.en.md). [Using the library](docs/ai/usage/README.en.md) covers installation, drawing workflows, fonts, images, pages, async work, CPU, and windows. [Developing the library](docs/ai/development/README.en.md) covers architecture, source constraints, candidate builds, exact comparisons, and release acceptance.

Also available: [API reference](docs/ai/usage/API_REFERENCE.en.md), [10 runnable demos](examples/README.en.md), [troubleshooting](docs/ai/usage/TROUBLESHOOTING.en.md), and [machine-readable facts](docs/ai/facts.json). See the [documentation validation record](docs/ai/VALIDATION.en.md) for the checks actually performed.

## Local wheels and source builds

Or install an accepted local wheel:

```shell
python -m pip install /path/to/py_skia_canvas-0.1.0a18-cp313-cp313-win_amd64.whl
```

On Linux, use the corresponding `manylinux_2_28_x86_64.whl`. Releases must upload the exact accepted bytes. GitHub Actions builds, GitHub Release downloads, TestPyPI installations, and PyPI installations each have their own verification status.

Download matching wheels from the GitHub Release above. On Windows without system long-path support, use a short virtual-environment path to avoid `MAX_PATH` failures in license files.

Rust is pinned to 1.90.0 and rust-skia to 0.88.0. Windows builds require CPython 3.13 and the MSVC x64 toolchain:

```powershell
./scripts/build_windows.ps1
```

Portable Linux builds use the pinned manylinux image; see the [release workflow](docs/RELEASE_WORKFLOW.md), [build script](scripts/build_manylinux.sh), and [container definition](tools/manylinux.Dockerfile). Fontconfig 2.17.1 is statically linked against the same embedded FreeType used by Skia. Ordinary development builds may use system libraries; that alone does not establish release acceptance.

`crates/canvas-core` is the only drawing core, consumed by Python and the development Node adapter. Official Node 3.0.8 is a development oracle; daily work does not require rebuilding Node. Its source snapshot is read-only reference material, never a Python runtime fallback.

## Development references

A new session must first read [AGENTS.md](AGENTS.md), [NEW_SESSION](docs/NEW_SESSION.md), the [implementation plan](docs/IMPLEMENTATION_PLAN.md), [API rules](docs/API_COMPATIBILITY.md), and the [task list](docs/TASKS.md). These authoritative project records and historical reports are currently in Chinese; the English development guides summarize the current workflow and constraints. Consult the latest completion/release reports when historical text disagrees with current status.

```shell
python -m unittest discover -s tests/bootstrap -v
python scripts/validate_bootstrap.py
python scripts/validate_core.py
python scripts/validate_licenses.py
```

Source checks do not replace GPU, font, lifecycle, or release checks on the actual wheel. Tool details are in [tests/README](tests/README.md). The repository retains its [MIT license](LICENSE); pinned dependency notices are in [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md).
