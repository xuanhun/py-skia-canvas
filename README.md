# py-skia-canvas

独立 Python Canvas 库，复用 `skia-canvas@3.0.8` 的原 Rust/Skia 核心，保留默认 GPU 策略。Python wheel 不需要 Node、npm、Neon/N-API 或 skia-python。

已迁移 Canvas/Context、Path2D 与扩展、DOM 几何/矩阵/CSS 变换、渐变、字体与文本排版/测量/装饰、图像/像素/pattern/texture、滤镜/混色、多页、同步/异步导出和 App/Window。公共名称与默认值沿用 Node；语言宿主采用已确认的 [Python 对应方案](docs/PYTHON_HOST_PROFILE.md)。

当前版本 **0.1.0a18**，首批支持 **CPython 3.13 / Windows AMD64 / Linux glibc 2.28+ x86_64**。[PyPI](https://pypi.org/project/py-skia-canvas/0.1.0a18/)、[TestPyPI](https://test.pypi.org/project/py-skia-canvas/0.1.0a18/) 和 [GitHub alpha Release](https://github.com/xuanhun/py-skia-canvas/releases/tag/v0.1.0a18) 均已发布并完成双平台独立安装回验。Windows Vulkan 与 Linux Vulkan 分别验收；macOS Metal 保留源代码和 feature，尚无验收过的发行物。实际 wheel SHA 和检查范围见 [本批交付报告](docs/COMPLETION_REPORT.md)，后续发行进度见 [发布状态](docs/RELEASE_STATUS.md)。

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

同步 Buffer 对应 bytes，Promise 对应实际 awaitable，undefined 单例与 None 分别对应 undefined/null。Sharp 是 Node 宿主依赖；同名入口明确抛缺少 Sharp 的原错误，图像字节可由 `toBuffer/toFile` 获取。库不启动 Node 或返回占位 Sharp/Stream 对象。

Canvas、Context、字体与 GPU 资源在创建线程使用；跨线程绘图会报错。异步导出在创建线程先形成原核心快照，后台只处理可安全转移的数据。Windows 在 Python 工作线程退出前释放其本地资源和原 GPU context，不把 GPU context 送入 Python 线程池。

系统字体和驱动会影响结果；项目只记录字体来源/指纹，不捆绑系统字体。验证逐项比较 JSON 数字、RGBA 和解码像素，不使用容差；透明像素的 RGB 差异也计数。原默认 GPU 验收与 CPU 诊断分开。

无可用 GPU 时自动使用 CPU，离屏绘制和全部导出格式已通过双平台 CPU 验收；完全没有 Vulkan 库的容器也已验证。详见 [纯 CPU 报告](docs/CPU_RENDER_REPORT.md)。App/Window 屏幕呈现仍受原版 GPU 后端限制；Windows 并行 PDF/SVG 序列的继承限制也在报告中明确列出。

## AI 使用与开发文档

从 [AI 文档入口](docs/ai/README.md)选择任务类型：[使用库](docs/ai/usage/README.md)介绍安装、绘图流程、字体、图像、多页、异步、CPU 和窗口；[开发库](docs/ai/development/README.md)介绍架构、来源约束、候选构建、精确差分和发布验收。

常用 [API 参考](docs/ai/usage/API_REFERENCE.md)、[10 类可运行 demo](examples/README.md)、[排错](docs/ai/usage/TROUBLESHOOTING.md)和[机器可读事实](docs/ai/facts.json)可单独查阅。示例与文档的实际验证范围见 [文档验证记录](docs/ai/VALIDATION.md)。

## 安装与构建

从正式 PyPI 安装已验收的同一 alpha wheel：

```shell
python -m pip install --only-binary=:all: py-skia-canvas==0.1.0a18
```

安装已验收的本地 wheel：

```shell
python -m pip install /path/to/py_skia_canvas-0.1.0a18-cp313-cp313-win_amd64.whl
```

Linux 使用对应 `manylinux_2_28_x86_64.whl`。发布必须上传同一批验收过的字节；GitHub Actions 构建、GitHub Release、TestPyPI 和 PyPI 安装各自记录状态。

可从上方 GitHub Release 下载对应 wheel。Windows 未启用系统长路径支持时，请使用较短的虚拟环境目录，避免许可证文件路径触及 `MAX_PATH`。

Rust 固定 1.90.0，Skia/rust-skia 固定 0.88.0。Windows 构建需要 CPython 3.13、MSVC x64 工具链：

```powershell
./scripts/build_windows.ps1
```

Linux 可移植构建使用固定 manylinux 镜像，流程见 [发行流程](docs/RELEASE_WORKFLOW.md)、[构建脚本](scripts/build_manylinux.sh) 和 [容器定义](tools/manylinux.Dockerfile)。Fontconfig 2.17.1 静态链接到同一 Skia 内嵌 FreeType；普通开发构建可使用系统库，但不因此获得发行验收。

`crates/canvas-core` 是唯一绘图核心，Python 和开发用 Node adapter 共同消费。官方 Node 3.0.8 仅用于开发差分，日常不重编 Node；其来源快照为只读资料，不能作为 Python 运行时 fallback。

## 开发资料

新会话先读 [AGENTS.md](AGENTS.md)、[NEW_SESSION](docs/NEW_SESSION.md)、[实施方案](docs/IMPLEMENTATION_PLAN.md)、[API 规则](docs/API_COMPATIBILITY.md) 和 [任务清单](docs/TASKS.md)。历史批次的结果保留在各报告；最新状态以本批交付报告为准。

```shell
python -m unittest discover -s tests/bootstrap -v
python scripts/validate_bootstrap.py
python scripts/validate_core.py
python scripts/validate_licenses.py
```

这些源码检查不代替实际 wheel 的 GPU、字体、生命周期或发布检查。工具用法见 [tests/README](tests/README.md)。仓库既有 [MIT 许可](LICENSE) 保持不变；固定依赖的版权和许可见 [第三方说明](THIRD_PARTY_NOTICES.md)。
