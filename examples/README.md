# 可运行示例

使用已发布的 `py-skia-canvas==0.1.0a18`，需要 CPython 3.13 和对应平台 wheel。应用示例只依赖标准库与该包，不需要 Node/Rust。

```shell
python -m pip install --only-binary=:all: py-skia-canvas==0.1.0a18
python examples/ai_demos.py --help
python examples/ai_demos.py all --out test-runs/my-demos-001
```

`--out` 必须为新目录。默认 `--backend auto` 保留原 GPU/CPU 策略；显式 `--backend cpu` 使用 CPU setter，`--backend gpu` 则要求真实 GPU。窗口需要可用 GPU/桌面。

| 示例 | 内容 |
| --- | --- |
| `hello` | 完整首图、PNG、像素断言 |
| `paths` | Path2D 布尔运算、渐变、DOMMatrix 和 Context 变换 |
| `text` | 多语言、换行、RTL、装饰、TextMetrics；可选 `--font-file` |
| `images` | 从 bytes 加载、缩放裁剪、pattern、raw 像素 |
| `effects` | 阴影、filter、混色、texture |
| `exports` | PNG/JPG/WebP/raw/PDF/SVG、density、data URL |
| `pages` | 多页 PDF、页面索引、文件序列 |
| `async` | 调用时快照、并发等待、异步文件 |
| `batch` | 每个 worker 内自建 Canvas，返回 bytes |
| `window` | 主线程 GPU 窗口，数帧后自动关闭 |

`all` 包含前九项；窗口单独运行，或加 `--include-window`。`window --hidden` 仍需要 GUI 后端。每项写出文件、`result.json`；顶层 `summary.json` 保存版本、实际 engine、尺寸、SHA 等结果。

详细说明与组合配方见 [AI 示例指南](../docs/ai/usage/DEMOS.md)，API 见 [使用参考](../docs/ai/usage/API_REFERENCE.md)。完整文档分为[使用库](../docs/ai/usage/README.md)与[开发库](../docs/ai/development/README.md)。

实际绘图结果已嵌入[示例图册](../docs/ai/usage/DEMOS.md#实际输出图册)，包含三页文档、前后异步快照、三个并行任务和窗口画面。

`development/parity-smoke.json` 是开发教程的两个 Node/Python 共用场景，需固定官方 oracle 和已安装 wheel，运行方式见[开发流程](../docs/ai/development/WORKFLOW.md)。测试 fixture 不是应用绘图 API。
