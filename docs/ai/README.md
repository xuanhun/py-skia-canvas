# AI 文档入口

中文 | [English](README.en.md)

本文档针对 **py-skia-canvas 0.1.0a18 / 官方 Node skia-canvas 3.0.8**。发行状态见 [RELEASE_STATUS](../RELEASE_STATUS.md)。这是通用 Canvas 库，适用于图形、图片、文档页面和窗口应用。

## 先选择任务类型

| 你的任务 | 读取顺序 | 交付物 |
| --- | --- | --- |
| 使用已发布包编写应用、生成图片/PDF、处理像素 | [使用指南](usage/README.md) → [API 参考](usage/API_REFERENCE.md) → [示例与配方](usage/DEMOS.md) → [排错](usage/TROUBLESHOOTING.md) | 应用代码、渲染文件、实际 backend/字体/尺寸说明 |
| 修改本库的 Python/Rust 代码、修复兼容问题、构建发行物 | 根 [AGENTS](../../AGENTS.md) 指定资料 → [开发指南](development/README.md) → [开发流程](development/WORKFLOW.md) → [测试与发行](development/TESTING_AND_RELEASE.md) | 有来源映射的补丁、新候选 wheel、独立断言/Node 差分证据 |

“开发”在本目录中特指修改库本身。使用本库开发业务应用，走“使用”路线即可。

机器可读事实见 [facts.json](facts.json)，可运行代码见 [examples/ai_demos.py](../../examples/ai_demos.py)，15 张实际输出见[示例图册](usage/DEMOS.md#实际输出图册)。事实文件只帮助 AI 选择 API，不参与库的渲染或运行。本批实际检查范围见[验证记录](VALIDATION.md)。

## 两条路线共用的事实

- 安装名 `py-skia-canvas`，导入名 `py_skia_canvas`；首发支持 CPython 3.13、Windows AMD64、Linux glibc 2.28+ x86_64。
- 使用者只需发行 wheel；Python 运行不依赖 Node/npm、Rust、Neon/N-API 或 skia-python。
- 公共名称沿用 Node 的 camelCase：`getContext`、`fillText`、`toBufferSync`。根据参考选择准确名称，不自行推测 snake_case 别名。
- 无可用 GPU 时，离屏 Canvas 按原策略自动使用 CPU。有 GPU 时保留原默认 GPU 策略。
- Canvas、Context、Path2D、图像和样式资源在创建线程使用；异步任务在调用时形成原实现的快照。并行任务在各自线程内创建和使用 Canvas，只传递 bytes/普通数据。
- App/Window 屏幕呈现仍要求 GPU 和可用桌面。Windows 默认并发 PDF/SVG 文件序列保留原版非确定性限制，详见使用指南。
- 系统字体由运行环境提供；中文、emoji、RTL 的具体外观与可用字体有关。固定布局验收时记录字体文件和指纹。

## 给 AI 的最小任务说明模板

使用任务：

```text
使用 py-skia-canvas==0.1.0a18 实现以下绘图任务：……
环境：CPython 3.13，操作系统/架构：……，可用字体：……。
先读 docs/ai/usage/README.md 和对应 API/示例。
使用公开 API，在创建线程绘制，说明画布单位、输出像素尺寸、格式和实际 backend。
提供可运行代码与输出文件；对字体、窗口和导出限制按实说明。
```

库开发任务：

```text
在 py-skia-canvas 仓库修改/修复：……。
先遵循 AGENTS.md 的必读要求，再读 docs/ai/development/README.md。
兼容目标固定官方 skia-canvas 3.0.8，共享唯一 Rust/Skia 核心；日常对照官方 A。
先重现问题、定位原实现和绑定边界，再修改并构建新候选 wheel。
用新 wheel 做相关断言/精确差分，保留新的 test-runs 证据；记录实际通过与未验收项。
外部操作按当前任务授权执行；不要把旧发行物测试当新补丁的验证。
```

## 阅读资料的优先级

当前发行事实以发布报告、实际安装的固定版本和该版本源码为依据。根目录的实施计划、任务清单、部分函数 docstring 和旧测试说明保留了迁移过程中的历史文字。遇到 `pending`、`initial binding` 或“尚未发布”等旧描述时，交叉核对 [发布状态](../RELEASE_STATUS.md)、[迁移报告](../COMPLETION_REPORT.md)、[宿主对应](../PYTHON_HOST_PROFILE.md) 和 [API 状态清单](../alpha-api-status.json)，再决定是否需要开发。

中文页保留原路径，英文对应页使用 `.en.md`。两种语言共用同一套可运行 demo、图片和机器事实；历史项目报告保留原语言。
