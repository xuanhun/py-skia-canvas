# G3 首批真实 Python 绑定

日期：2026-10-27。基线仍是 skia-canvas 3.0.8。已构建本地 CPython 3.13 / Linux x86_64 alpha wheel；未上传或发布。G3 当前是限定输入范围的真实实现，不代表完整 Node API/语言契约或跨平台发行验收。

## 实现

`crates/python` 使用 PyO3 0.27.2，调用唯一 `canvas-core`；`python/py_skia_canvas` 只提供薄包装和返回容器。原 317 个第三方 Cargo package 条目保留不变，新增 10 个 PyO3 相关 package。CSS 颜色解析和颜色 getter 字符串格式也机械提取到 core，Node/Python 共用原 css-color 和原通道/alpha 舍入。

当前公共名称保持 Node 命名：Canvas 的 width/height、getContext、gpu/engine、toBufferSync；Context 的 save/restore/reset、fillStyle/strokeStyle 纯色、globalAlpha、fillRect/strokeRect/clearRect、fillText/strokeText/measureText、getImageData；TextMetrics 保留原字段。构造默认 300×150、contrast=0/gamma=1.4，以及 gpu:false 只改状态标记的原版差异均保留。

几何目前支持有限数值；文字采用原默认字体，maxWidth 及 UTF-16/孤立 surrogate 行为有专项对照。没有另写 shaping、字体选择、混色、绘图或 Vulkan 策略。颜色非法字符串保留原忽略行为；完整 JS coercion、STRICT/non-STRICT 非法值契约尚未绑定。getImageData 返回拥有 bytearray 的内部读回容器，不冒充完整 ImageData 构造器。

平台 Cargo 依赖自动选择原 Linux Vulkan/FreeType、Windows Vulkan、macOS Metal，防止不传 build feature 就静默构成 CPU-only 包。只有 Linux 构建实际验证；不宣称另两个平台已通过。

## 线程和生命周期

PyO3 类只持资源 ID 和创建线程 ID，可按 Rust 类型规则自动满足 Send/Sync；未使用 unsafe Send/Sync。Core Canvas/Context 及 GPU 引用始终在创建线程 TLS registry 中。所有原生操作先检查线程，再借用 registry；不在借用期间调用 Python 回调，不在 Python 线程池移动 GPU context。

同线程最终引用释放会直接销毁原生资源；异线程 GC 只入队 ID，创建线程下一次原生入口或线程退出时回收。创建线程闲置时回收会延后。在线程原 GPU TLS 初始化之后注册 cleanup，使 core 对象先于该 GPU context 销毁。创建线程退出即使 Python handle 仍存活，也会释放原生对象；外线程 handle 继续禁止原生访问。

该策略与 [PyO3 线程安全约束](https://pyo3.rs/v0.27.2/class/thread-safety.html) 一致，生命周期必须由实际测试支持。当前仅验证 Linux CPython 3.13；free-threaded Python、fork 后继续使用对象、多解释器和异步取消均未验收。

## 验证

独立 CPython 3.13.18 放在 `/tmp/py-skia-canvas-g3-20261027-1`，不是项目 `.local` 的 Python；在仓库外新 venv 安装实际 wheel，空 PATH 且不可发现 Node。采集器检查安装的 Python/native 文件与指定 wheel 字节一致，ldd 无 libnode/Neon/项目路径依赖，验证同一系统字体/config 内容。

8 个 Python 场景（core-smoke 1 + python-core 7）对固定官方 Node A 与最新共享核心 Node B：JSON 指标、RGBA、解码 PNG 精确比较，alpha=0 的 RGB 不例外。覆盖状态/resize/reset、CSS alpha/非法颜色、默认字体/maxWidth/描边、孤立 surrogate/UTF-16、原构造 gpu:false 差异及独立 CPU 诊断。CPU 结果不替代默认 GPU。比较状态仅为 `MATCHED_RECORDS`。

6 项真实 wheel 生命周期测试：同线程回收、异线程访问拒绝与 GC、异线程循环 GC、owner 线程退出时仍有 Python 引用、读回异常后退出、解释器带活动 GPU 对象退出。子线程异常会传播为测试失败，不做缺 GPU skip。

`scripts/trace_python_gpu.py` 用同一已安装 wheel 采集原生断点：实际 300×150 请求读回命中 1 次 Vulkan surface、6 次 Skia Vulkan submit；PNG 命中 1/2 次；全新显式 CPU 对照为 0/0。断点位于 `VulkanContext::surface` 和 `GrVkPrimaryCommandBuffer::submitToQueue`，调用栈包括 PyO3 入口和原 GPU 读回。它不是驱动 vkQueueSubmit 入口 trace，优化符号没有直接暴露 surface 尺寸字段；请求尺寸与返回 180000 字节单独记录。Linux 仍是 Mesa llvmpipe 软件 Vulkan。

已有 GPU 缓存的 Canvas 切到 CPU 后仍可能为旧 GPU image 读回提交队列；首轮 trace 原样保留。全新 CPU 对照与上述场景分开，未改造原缓存行为以消除命中。

最终证据入口是 `test-runs/20261027-g3-python-final/run.json`；最终构建在 `20261027-python-wheel-final-build-linux-2/run.json`，安装/生命周期在 `20261027-python-final-install-linux`，原生路径在 `20261027-python-native-trace-accepted-linux`。早期 wheel 与失败采集保留在各自目录，不覆盖。

## 仍待完成

- G4 路径、变换、clip、gradient 与 DOM 几何；G5 CSS font/FontLibrary/完整排版；G6 图像/像素完整绑定；其余效果、异步、多页、文件/格式、App/Window 继续在 TASKS 中。
- 完整 JS coercion/默认值/异常映射及 STRICT 两模式、公开 ImageData 构造器和全部公共 ledger 条目。
- Windows 硬件 Vulkan 与源码 wheel，Metal、原生驱动入口/尺寸 trace、glyph fallback/字体许可。
- Linux 上游 static-fontconfig patch/完整原生构建 provenance、manylinux、全部第三方许可、CI 与发布流程。当前 wheel 使用系统 Fontconfig，标签明确为 linux_x86_64。
- 只有实际验收的同一 wheel 字节可以用于将来的发行；当前没有 commit/push、TestPyPI 或 PyPI 操作。

下一批先推进 G4 的基础路径/变换/clip，同时补 G0 参数契约；不升级兼容基线或改默认 GPU 策略。
