# Documentation and demo validation record

[中文](VALIDATION.md) | English

Date: 2026-10-29. Scope: AI usage/development docs, runnable demos, minimal comparison tutorial, and embedded images. Production Python/Rust and published wheels were unchanged; this documentation batch rebuilt neither Node nor Skia and created no new release.

## Implementations used

Tests used independently installed production-PyPI **0.1.0a18**, outside the repository with empty PATH and Python `-I`. No source-package or alternative-renderer fallback was used.

| Platform | Wheel SHA-256 | GPU environment |
| --- | --- | --- |
| Windows AMD64 / CPython 3.13 | `9efce11f1340a9bfbb69387f0757abe1635b3ff45528ce07e69dc30771049b74` | NVIDIA RTX 5080 / Vulkan |
| Linux x86_64 / CPython 3.13 | `2e641429ceedaca260037abba217e13189a16a1168571fa430857e06b2734071` | WSLg llvmpipe / Vulkan with actual GPU surface; distinct from CPU Raster |

See [RELEASE_STATUS](../RELEASE_STATUS.md) and [CPU_RENDER_REPORT](../CPU_RENDER_REPORT.md) for full release provenance, GPU/CPU acceptance, and index installation checks.

## Application demos

Four configurations per platform produced **40 final demo executions**:

| Configuration | Demos per platform | Result |
| --- | --- | --- |
| `all --backend gpu` | 9 | Actual GPU; assertions/exports succeeded |
| `all --backend auto` with drivers blocked | 9 | Automatic CPU fallback; assertions/exports succeeded |
| `hello --backend cpu` | 1 | Explicit CPU setter succeeded |
| `window --hidden --backend gpu` | 1 | Actual event loop, drawing, frame output, automatic close |

Each platform additionally ran `text --font-file`: **2 font-registration demos**, verifying DemoFace registration, measurement, and output. They read local Windows Arial and Linux DejaVu Sans files without copying them into docs/evidence. The later ring-demo revision did not change text registration behavior.

Final local ignored evidence: `test-runs/20261029-ai-docs-examples-2/{windows,linux}/`; font evidence: `test-runs/20261029-ai-docs-font-1/{windows,linux}/`. Runs retain commands, exit status, actual engines, PNG/other formats, dimensions, hashes, and metrics.

Visual review covered the nine final offscreen demos on both platforms and the embedded window frame. Initial review found a solid disc under the default fill rule. The demo was corrected to explicit evenodd filling, gained a center-background RGBA assertion, and reran all 40 final executions. Earlier runs/reviews and the failed Linux path-conversion harness record were retained without overwriting.

## Development tutorial comparisons

The two [parity-smoke.json](../../examples/development/parity-smoke.json) scenes ran across:

- Windows and Linux.
- Default GPU and automatic CPU after driver blocking.
- Normal and `SKIA_CANVAS_STRICT=1`.
- Identical fixture/platform font/config manifest; official Node **22.23.2 / skia-canvas 3.0.8** and installed Python wheel.

All **8 comparison reports / 16 scene pairs** were `MATCHED_RECORDS`, with zero JSON, full-RGBA, or decoded-PNG pixel differences. Evidence: `test-runs/20261029-ai-docs-parity-1/{windows,linux}/`. This validates the tutorial scenes/workflow, not a new full compatibility run.

## Documentation and embedded images

```shell
python scripts/validate_ai_docs.py
```

The tool checks recursive local Markdown links, Python code-block syntax, version/18 Python exports, facts paths, tutorial fixture structure, and **15 PNGs** for dimensions, sizes, hashes, script provenance, and gallery references. Source CI includes it. Its status is only `AI_DOCS_STRUCTURALLY_VALIDATED`; it loads no native module and certifies no rendering behavior.

Images come directly from final Windows GPU outputs into [assets](assets/README.en.md); see [manifest.json](assets/manifest.json). The three pages, two snapshots, and three batch jobs retain separate images. Guides/gallery use repository assets, so readers do not need local `test-runs` data to see them.

The batch also passed **74 bootstrap assertions, 6 Node API ledger assertions**, and bootstrap/core/license source checks. Production dependencies and controlled source bytes remained unchanged. No new wheel build or external package publication occurred; full release acceptance remains a separate record.

## Chinese and English documentation update

On the same date, 12 English counterparts were added: repository/AI entry points, usage/API/troubleshooting/gallery, development workflow/acceptance, examples, image provenance, and this record. Chinese retains existing filenames; English uses `.en.md`. Every page links to its counterpart. `facts.json` adds `zh-CN` / `en` routes.

Bilingual validation covers 24 Markdown pages, 12 translation pairs, local links/language entries, matching heading levels, and executable code/image references. Python blocks are compared by AST (allowing translated comments); shell/PowerShell/Bash blocks are compared directly. The 15 original image hashes remain checked. English retains all version, CPU/GPU, host, thread, and publication limitations. Historical source reports retain their original language.

Only documentation and its checker changed. Demos, images, fixtures, production code, and wheel bytes are unchanged. Rendering results above are completed evidence from the preceding batch; translation checks are not a new rendering acceptance run. Fresh Windows/Linux documentation evidence is under `test-runs/20261029-bilingual-docs-1/`.
