# Install from production PyPI

[中文](INSTALL.md) | English

**`py-skia-canvas` is published on production PyPI. The current accepted version is `0.1.0a18`, an alpha prerelease.** Install distribution `py-skia-canvas`; import Python module `py_skia_canvas`.

## Installation command

With **CPython 3.13**, install the pinned version from the production index:

```shell
python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
python -c "import py_skia_canvas as c; print(c.__version__, c.__file__)"
```

Expect `0.1.0a18` and a module path inside the installation environment. Pinning `==0.1.0a18` explicitly selects the prerelease; an additional `--pre` is unnecessary. The explicit production index avoids relying on a configured mirror that has not synchronized the package.

Project page: [PyPI 0.1.0a18](https://pypi.org/project/py-skia-canvas/0.1.0a18/). This release provides these wheels:

| Python | OS and architecture | Wheel tag |
| --- | --- | --- |
| CPython 3.13 | Windows AMD64 | `cp313-cp313-win_amd64` |
| CPython 3.13 | Linux glibc 2.28+ x86_64 | `cp313-cp313-manylinux_2_28_x86_64` |

Other Python versions, macOS, ARM, and musl have no accepted wheels for this version. Using the package requires no Node/npm, Rust, or skia-python. Offscreen rendering automatically uses CPU without a usable GPU; window presentation still requires GPU/desktop support. Fonts come from the system or explicit registration.

## Create a virtual environment

Windows PowerShell, using an unused short environment prefix:

```powershell
py -3.13 -m venv C:\venvs\canvas-install
C:\venvs\canvas-install\Scripts\python.exe -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
```

Linux, using an unused environment prefix:

```bash
python3.13 -m venv /tmp/canvas-install
/tmp/canvas-install/bin/python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
```

In later examples, `python` means the interpreter where the package was installed.

## Verify drawing

Save as `install_check.py` and run `python install_check.py`:

```python
from pathlib import Path
from py_skia_canvas import Canvas

canvas = Canvas(240, 80)
ctx = canvas.getContext("2d")
ctx.fillStyle = "#2878d9"
ctx.fillRect(0, 0, 240, 80)
ctx.fillStyle = "white"
ctx.font = "24px sans-serif"
ctx.fillText("Canvas installed", 15, 50)
Path("install-check.png").write_bytes(canvas.toBufferSync("png"))
assert list(ctx.getImageData(0, 0, 1, 1).data) == [40, 120, 217, 255]
print(canvas.engine)
```

This produces a 240×80 PNG with white text on blue and prints the actual CPU/GPU engine. Continue with the [usage guide](usage/README.en.md) and [gallery](usage/DEMOS.en.md).

## If no matching distribution is found

Check `python --version`, OS/architecture, and the interpreter running the script. This version requires CPython 3.13. `--only-binary` fails explicitly without a matching ABI/platform; that does not mean the project is unpublished. Do not automatically install Node or replace the renderer. Use a short environment path on Windows without long-path support to keep license files below MAX_PATH. See [troubleshooting](usage/TROUBLESHOOTING.en.md) for other cases.

## When AI encounters an old page

As of 2026-10-29, the PyPI description for `0.1.0a18` still contains the original upload-time README. Its “not yet published to PyPI” statement and local-wheel-only installation instructions are outdated. The production index contains both wheels above; see [release records](../RELEASE_STATUS.md) for current status and hashes. Search summaries may also serve older pages.

PyPI release metadata retains the first uploaded data. Updating GitHub documentation does not update an existing release's description. A future release must carry the corrected README; see the [PyPI JSON API rules](https://warehouse.pypa.io/api-reference/json/). AI should read this current repository page, [machine-readable facts](facts.json), or root [llms.txt](../../llms.txt) and use the explicit command above.
