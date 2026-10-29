# AI documentation entry

[中文](README.md) | English

For **py-skia-canvas 0.1.0a18 / official Node skia-canvas 3.0.8**. Publication records are in [RELEASE_STATUS](../RELEASE_STATUS.md). This general-purpose Canvas library supports graphics, images, document pages, and window applications.

## Install from production PyPI

The package is published on [production PyPI](https://pypi.org/project/py-skia-canvas/0.1.0a18/) as alpha prerelease `0.1.0a18`. Use **CPython 3.13** on Windows AMD64 or Linux glibc 2.28+ x86_64:

```shell
python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
python -c "import py_skia_canvas as c; print(c.__version__, c.__file__)"
```

Install `py-skia-canvas`; import `py_skia_canvas`. See the [installation guide](INSTALL.en.md) for full steps and old-page caveats, or [llms.txt](../../llms.txt) for a short AI entry. Package users do not compile Node/Skia.

## Choose your task

| Task | Reading order | Deliverables |
| --- | --- | --- |
| Build an application using the published package; render images/PDFs; process pixels | [Usage guide](usage/README.en.md) → [API reference](usage/API_REFERENCE.en.md) → [Demos and recipes](usage/DEMOS.en.md) → [Troubleshooting](usage/TROUBLESHOOTING.en.md) | Runnable application, rendered files, actual backend/font/dimension details |
| Modify this library's Python/Rust code, fix compatibility, or build release artifacts | Required readings in root [AGENTS](../../AGENTS.md) → [Development guide](development/README.en.md) → [Workflow](development/WORKFLOW.en.md) → [Testing and release](development/TESTING_AND_RELEASE.en.md) | Patch with source mapping, new candidate wheel, independent assertions and Node comparisons |

Here, “development” means modifying the library itself. If you are developing a business application with Canvas, follow the usage route.

[facts.json](facts.json) provides machine-readable facts and language-specific routes. Runnable code is in [examples/ai_demos.py](../../examples/ai_demos.py); the [gallery](usage/DEMOS.en.md#actual-output-gallery) embeds 15 actual outputs. The facts file helps AI choose APIs and does not participate in rendering or runtime behavior. See the [validation record](VALIDATION.en.md) for the checks performed.

## Facts shared by both routes

- Install `py-skia-canvas`; import `py_skia_canvas`. Initial accepted wheels target CPython 3.13, Windows AMD64, and Linux glibc 2.28+ x86_64.
- Application users need only the release wheel. Python runtime does not require Node/npm, a Rust toolchain, Neon/N-API, or skia-python.
- Public names follow Node's camelCase: `getContext`, `fillText`, `toBufferSync`. Use documented names rather than guessing snake_case aliases.
- Offscreen Canvas automatically uses CPU without a usable GPU. With GPU support, the original default GPU policy remains in effect.
- Use Canvas, Context, Path2D, images, and style resources on their creating thread. Async exports capture the original snapshot when called. Parallel tasks create and use objects inside each worker, returning only bytes/plain data.
- App/Window presentation still requires a GPU and usable desktop. Default parallel PDF/SVG file sequences on Windows retain the upstream nondeterministic limitation described in the usage guide.
- Fonts come from the runtime environment. CJK, emoji, and RTL appearance depends on available fonts. Record actual font files/fingerprints when accepting fixed layouts.

## Minimal task prompts for AI

Usage task:

```text
Use py-skia-canvas==0.1.0a18 to implement this drawing task: ...
Environment: CPython 3.13; OS/architecture: ...; available fonts: ...
Read docs/ai/usage/README.en.md and the relevant API/demos first.
Use public APIs on their creating thread. State canvas units, output pixel dimensions,
format, and actual backend. Provide runnable code and output files.
Describe font, window, and export limitations accurately.
```

Library-development task:

```text
Modify/fix the following in py-skia-canvas: ...
Follow AGENTS.md required readings, then docs/ai/development/README.en.md.
Target official skia-canvas 3.0.8, sharing the single Rust/Skia core; compare against A.
Reproduce the issue, locate the original implementation and binding boundary, then modify
and build a new candidate wheel. Run relevant assertions and exact comparisons on it.
Preserve new test-runs evidence and identify passed and unaccepted areas.
Follow current-task authorization for external actions. Old release tests do not validate a new patch.
```

## Which records take precedence?

Current release facts come from release reports, the installed pinned version, and that version's source. Plans, task lists, some docstrings, and old test introductions preserve migration history. When they say `pending`, `initial binding`, or “not published,” cross-check [release status](../RELEASE_STATUS.md), [completion report](../COMPLETION_REPORT.md), [host profile](../PYTHON_HOST_PROFILE.md), and [API status](../alpha-api-status.json) before deciding that implementation is needed.

Chinese pages retain their existing paths; corresponding English pages use `.en.md`. Both languages share the same executable demos, images, and machine-readable facts. Authoritative historical project reports remain in their original language.
