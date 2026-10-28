# 纯 CPU 与无 GPU 环境验收

2026-10-28，使用已经完成 GPU 验收的 **0.1.0a18 同一 wheel 字节**。本轮没有重编 Node/Skia，没有修改 Python 库、原 Rust 绘图算法或默认 GPU 策略。Windows/Linux 无可用 GPU 时，原核心会自动选择 CPU；调用者不需要额外安装 Vulkan。

| 环境 | 普通场景 | STRICT 场景 | 实际结果 |
| --- | ---: | ---: | --- |
| Windows，无可用 Vulkan 驱动 | 3,561 | 3,175 | 83 组，JSON、raw RGBA、PNG 解码像素对官方 Node CPU 精确一致 |
| Linux，无可用 Vulkan 驱动 | 3,561 | 3,175 | 同上，所有场景 Vulkan surface 数为零 |
| Linux 隔离容器，无 GPU 设备、无 Vulkan 库 | 3,561 | 3,175 | 全部成功；与官方 CPU 基线的 6,736 份 raw/PNG 像素逐字节相同 |

这些数字包括有效绘图及预期的非法参数/异常契约。没有把 CPU 结果拿来替代 GPU 验收，也没有要求 CPU/GPU 两种后端之间像素相同。

## 覆盖范围与证据

路径/布尔运算/特效、变换/矩阵/投影、clip、渐变、pattern/texture、filter/shadow/混色、文本/FontLibrary/TextMetrics、CJK/RTL/组合字/variable/emoji、图像加载/裁剪/像素、Canvas 互绘、多页和导出均使用既有全部 58 组绘图 fixture；STRICT 另有 25 组。系统字体资源固定，与对应 Node 对照相同；未捆绑字体。

每端另外通过 **23 项 CPU 生命周期测试**，包括同步/异步六格式导出、像素快照、取消/多等待者、文件序列、异常恢复、owner 退出、跨线程误用、并行 CPU owner 和 GC。图像加载 18 项、HTTP options 16 项也在无驱动的 CPU 环境对照通过。

每端 12 组实际 Paragraph 字形观测覆盖文本绘制和 stroke，字体四表来源、glyph 与安全 UTF16 range 检查无缺项；启用观测后的 raw/PNG 也与 CPU 官方对照逐字节一致。没有只看 engine 标签：Linux GDB 实际命中 **5 次 `C_SkSurfaces_Raster`**，Vulkan surface 和 queue submit 均为 **0**。后端负控制还确认：GPU 存在时，CPU 验收工具会拒绝 GPU 绘图；GPU 不可用时，原 GPU 验收工具仍会失败。

隔离容器关闭网络，没有 Node、生产 Python/Rust 源码或 GPU 设备，也没有 `libvulkan.so.1`。只装同一发行 wheel，挂载合成测试数据和已固定的系统/Noto 字体。完整 6,736 个绘图场景、普通/STRICT 各 206 个导出输入均可执行；每组 228 个导出文件的像素、PDF 全页/结构、SVG 和元数据也与官方 CPU 基线精确一致。另一个最小环境独立通过 23 项生命周期和六格式导出。

主要记录位于 `test-runs/`：

- `20261028-cpu-matrix-linux-1`、`20261028-cpu-matrix-windows-1`：双平台原 Node CPU 差分；每个 Python case 单独记录真实 Vulkan surface 数为零。
- `20261028-cpu-native-trace-1`：原生 Raster 调用栈及 GPU 零命中。
- `20261028-cpu-no-loader-container-1`、`20261028-cpu-no-loader-full-2`：无 Vulkan/无设备的真实运行。
- `20261028-cpu-no-loader-pixels-1`：隔离环境全部 6,736 场景像素核对，差异为零。
- `20261028-cpu-no-loader-exports-1`、`20261028-cpu-no-loader-exports-strict-1`：隔离环境普通/STRICT 各 206 项、228 文件精确一致。
- `20261028-cpu-lifecycle-1`、`20261028-cpu-loading-1`：资源、线程、导出和真实加载。
- `20261028-cpu-visual-review-1`：双平台粗斜体、RTL、CJK 和 emoji 的人工视觉审阅，另于像素差分记录。
- `20261028-cpu-review-3`：独立汇总复核；早期 controller 的 wheelSha256 空字段不作为来源依据，逐一核对实际 83 组 capture 的 wheel/native SHA；Windows 默认并发导出的差异仅限既有四项。

固定 wheel SHA：

- Windows：`9efce11f1340a9bfbb69387f0757abe1635b3ff45528ce07e69dc30771049b74`
- Linux：`2e641429ceedaca260037abba217e13189a16a1168571fa430857e06b2734071`

本轮本地补充包为 `dist/cpu-validation-0.1.0a18.zip`：包含差分记录、日志、测试输入/工具、视觉审阅和全部渲染输出的 SHA 索引；完整 raw/导出文件保留在上述独立目录。补充包不改写此前已验收的 GPU 发布候选包，也不表示已对外发布。

## 导出与边界

Linux 在默认并发下，普通/STRICT 各 **206 项、228 个文件**对照通过，包含 PNG/JPG/WebP/raw/PDF/SVG、density/matte/MSAA/outline/downsample、文件序列、元数据和所有 PDF 页。CPU 对某些 MSAA 输入的原行为与 GPU 不同，所以文件数以 CPU 的实际记录为准。

Windows 默认并发的 PDF/SVG 文件序列仍有此前已确认、用户已同意保留的原版非确定性漏字/字体子集问题；它在 CPU 下同样复现。这些失败原样保留，没有静默跳过。相同 `RAYON_NUM_THREADS=1` 诊断下，两端普通/STRICT 各 206 项、228 文件全部精确一致；库的默认线程数没有改为 1。需要稳定的 Windows 多文件矢量导出时，可在启动进程前显式设置该环境变量。

默认并发差异限定于 `export-125/126` 的 PDF 结构及 `export-146/147` 的 SVG XML/像素，复核没有豁免其他导出项。上述串行设置是已验证的规避方式，保留原实现的非确定性限制仍适用。

**App/Window 屏幕呈现依旧需要 GPU。** 原版与 Python 在无 GPU 时均明确报 `No windowing support: Could not create Vulkan instance`，见 `20261028-cpu-window-boundary-2`。用户已确认“完整验收离屏渲染与导出，窗口保留原版限制”；本轮不新增 CPU 窗口呈现后端。

## 运行方式

无可用 GPU 时，`Canvas(width, height)` 自动回退 CPU。若机器有 GPU 但需要显式选择 CPU，请创建后使用 `canvas.gpu = False`；原 3.0.8 构造 options 中的 `gpu:false` 不能当作真正禁用 GPU 的开关。手动 setter 不等同于证明整个进程没有做过 GPU 可用性探测，本轮无设备/无库环境补足了这个验证。

开发复测工具：`scripts/run_cpu_matrix.py --config <明确的测试路径配置> --out <新的证据目录>`；后端断言为 `scripts/capture_python.py --backend cpu` 与官方采集的 `--require-cpu`；`tests/cpu/test_cpu_lifecycle.py` 可用安装环境的 `python -I -m unittest discover -s <绝对 tests/cpu 路径> -v` 运行。`tests/cpu/probe_cpu_runtime.py --no-loader --out <新目录>` 可独立验证最小部署。

驱动屏蔽只设置子进程的 `VK_DRIVER_FILES` / `VK_ICD_FILENAMES`，未修改系统驱动或注册表；其行为依据 [Khronos Vulkan Loader 驱动接口](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderDriverInterface.md)。默认 GPU 门禁和此前 GPU 证据继续保留。外部同步和发布仍未执行。
