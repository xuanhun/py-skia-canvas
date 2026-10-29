# Documentation example images

[中文](README.md) | English

These 15 PNGs are the original bytes produced by [ai_demos.py](../../../examples/ai_demos.py) using the published **0.1.0a18 Windows AMD64 wheel**. They appear in the [usage guide](../usage/README.en.md) and [gallery](../usage/DEMOS.en.md). Rendering used the original Vulkan GPU backend; text depended on the system fonts then available.

All graphics/input images were created by the project demos. No user pictures, system font files, or local node_modules were copied. PNGs received no resizing, recoloring, or postprocessing; Markdown display may scale them to fit.

[manifest.json](manifest.json) records script/wheel hashes, backend, and each image's original run path, dimensions, size, and SHA. The demo writes `result.json` / `summary.json` during execution. Reproduce the scenes with:

```shell
python examples/ai_demos.py all --backend gpu --out test-runs/NEW_DOC_ASSETS/gpu
python examples/ai_demos.py window --hidden --backend gpu --out test-runs/NEW_DOC_ASSETS/window
```

When regenerating, succeed in the required environment and inspect outputs before updating images/manifest. Different platforms/fonts/drivers need not produce identical encoded bytes. Library compatibility acceptance still uses exact comparisons with official Node A in the same environment. These images do not replace complete pixel, font, window, or release evidence.
