# 本批文档与示例验证

中文 | [English](VALIDATION.en.md)

日期：2026-10-29。范围是 AI 使用/开发文档、可运行 demo、最小差分教程和嵌入图片。生产 Python/Rust 实现与已发布 wheel 未修改；本批没有重新编译 Node/Skia，也没有创建新发行版。

## 使用的实现

使用正式 PyPI 独立安装的 **0.1.0a18**，从仓库外目录、空 PATH、Python `-I` 执行。没有从当前源码包或其他绘图库 fallback。

| 平台 | wheel SHA-256 | GPU 环境 |
| --- | --- | --- |
| Windows AMD64 / CPython 3.13 | `9efce11f1340a9bfbb69387f0757abe1635b3ff45528ce07e69dc30771049b74` | NVIDIA RTX 5080 / Vulkan |
| Linux x86_64 / CPython 3.13 | `2e641429ceedaca260037abba217e13189a16a1168571fa430857e06b2734071` | WSLg llvmpipe / Vulkan，实际 GPU surface；与 CPU Raster 区分 |

详细发行来源、全量 GPU/CPU 验收与索引安装回验仍以 [RELEASE_STATUS](../RELEASE_STATUS.md) 和 [CPU_RENDER_REPORT](../CPU_RENDER_REPORT.md) 为准。

## 应用示例

每个平台执行以下四组，最终共 **40 次 demo 执行**：

| 配置 | 每平台示例数 | 结果 |
| --- | --- | --- |
| `all --backend gpu` | 9 | 全部实际 GPU，断言与导出成功 |
| 屏蔽驱动后的 `all --backend auto` | 9 | 全部自动回退 CPU，断言与导出成功 |
| `hello --backend cpu` | 1 | 显式 setter 选择 CPU 成功 |
| `window --hidden --backend gpu` | 1 | 真实事件循环、绘制、保存画面并自动关闭 |

另在两平台各运行一次 `text --font-file`，共 **2 次字体注册示例**，验证 DemoFace 注册、测量和输出。读取 Windows Arial 与 Linux DejaVu Sans 本机文件，不复制字体到文档或证据。字体注册文本功能未因后续圆环示例修订改变。

最终示例证据位于本机忽略目录 `test-runs/20261029-ai-docs-examples-2/{windows,linux}/`；字体证据位于 `test-runs/20261029-ai-docs-font-1/{windows,linux}/`。每组保留命令、退出状态、实际 engine、PNG/其他格式、尺寸、SHA 及指标。

视觉审阅覆盖两平台最终九个离屏示例，以及嵌入的窗口帧。初次审图发现圆环使用默认填充规则时呈实心；示例改为显式 evenodd，并新增圆心 RGBA 背景断言后重新执行上述 40 项。初次运行/审图和 Linux 路径转换工具的失败记录保留在原 run，未覆盖。

## 开发教程差分

[parity-smoke.json](../../examples/development/parity-smoke.json) 的两个场景在以下矩阵运行：

- Windows、Linux。
- 默认 GPU、屏蔽驱动后的自动 CPU。
- 普通、`SKIA_CANVAS_STRICT=1`。
- 同一 fixture、平台字体/config manifest；官方 Node **22.23.2 / skia-canvas 3.0.8** 与已安装 Python wheel。

共 **8 份比较报告、16 个场景对**，全部为 `MATCHED_RECORDS`，JSON、完整 RGBA 和解码 PNG 像素差异均为零。证据在 `test-runs/20261029-ai-docs-parity-1/{windows,linux}/`。这验证教程用例和流程，不能扩大解释为本批重新跑了全部兼容测试。

## 文档及嵌入图片

```shell
python scripts/validate_ai_docs.py
```

该工具检查递归 Markdown 本地链接、Python 代码块语法、版本/18 个 Python 导出、机器事实路径、教程 fixture 结构，以及 **15 张 PNG** 的尺寸、大小、SHA、脚本来源和图册引用。源码 CI 已加入此检查。它只输出 `AI_DOCS_STRUCTURALLY_VALIDATED`，不加载 native 模块或声明渲染验收。

图片直接取自最终 Windows GPU 结果，保存到 [assets](assets/README.md)，见 [manifest.json](assets/manifest.json)。三页文档、两次快照和三个 batch 任务分别保留各自图像。图册与指南引用固定仓库资源，其他用户无需拿到本机 `test-runs` 就能看到图片。

还运行既有 **74 项 bootstrap 断言、6 项 Node API ledger 断言**及 bootstrap/core/许可证来源检查，全部通过，确认新增文档没有改变受控来源和生产依赖。未执行新的 wheel 构建或外部发布；已发布发行物的全面验收记录独立保留。

## 中英文文档更新

同日新增 12 份英文对应文档，覆盖仓库入口、AI 入口、使用/API/排错/图册、开发流程/验收、示例、图片来源及本记录。中文保留原文件名，英文使用 `.en.md`，每页互相链接；`facts.json` 增加 `zh-CN` / `en` 路由。

双语校验覆盖 24 份 Markdown、12 对译文、全部本地链接与语言入口、相同章节层级，以及两种语言的可执行代码和图片引用。Python 代码按 AST 比较（允许注释翻译），shell/PowerShell/Bash 命令逐块比较，15 张图片继续验证原 SHA。英文文档完整保留版本、CPU/GPU、宿主、线程和发布限制；历史来源报告保留原语言。

本次只改文档与文档校验工具，demo、图片、fixture、生产代码和 wheel 字节未变；上面的渲染结果是已完成的上一批证据，本次不将翻译检查写成新一轮渲染验收。双平台文档检查的新证据保存在 `test-runs/20261029-bilingual-docs-1/`。
