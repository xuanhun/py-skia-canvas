# CPU 验收

此目录为独立的 CPU/无 GPU 测试，不改变生产默认 GPU 策略。使用已安装的同一 wheel，在仓库外工作目录、`PATH` 为空、Python `-I` 下执行。`Canvas()` 必须自动选择 CPU；不能把 llvmpipe Vulkan 当作这里的 Skia Raster。

`suites.json` 固定 58 组普通、25 组 STRICT 绘图输入，共 3,561/3,175 场景。`scripts/run_cpu_matrix.py` 根据显式配置启动固定官方 A 和安装环境，并逐项精确比较；配置字段包含 `transport`（native 或 wsl）、目标 `root/cwd/python/node/module/wheel/environment` 路径、`blockedDriver`、`ordinary/strict` 名称数组、可选 `mappedFixtures`。字体和测试资产的路径映射必须在两端一致并保留指纹。

CPU 捕获要求 `scripts/capture_python.py --backend cpu` 与 oracle 的 `--require-cpu`。默认参数仍要求 GPU，禁止 CPU 静默通过 GPU 门禁。Vulkan 驱动屏蔽变量只传给子进程；不得改系统驱动、注册表或系统库。真正的无库验收另在没有 Vulkan/设备/Node 的隔离运行时完成。

安装环境运行 `python -I -m unittest discover -s <本目录绝对路径> -v`，覆盖 23 个 CPU 资源/导出/线程/GC 契约。测试以像素/字节为单位，所有绘图仍在创建线程；线程测试只在其 owner 创建和使用 Canvas，错误或断言失败不得 skip。`probe_cpu_runtime.py --no-loader --out <新目录>` 是无 Node 依赖的部署探针。

导出输入为 `tests/fixtures/exports.json`。普通和 STRICT 各 206 项均须保留原文件、像素、PDF 所有页/结构、SVG 和元数据比较。Windows 原并行 PDF/SVG 序列非确定性与串行诊断分别记录；不把串行诊断写成默认并发完全通过。

具体环境、同一 wheel SHA、独立复核、原生 Raster 调用栈和限制见 [CPU 渲染报告](../../docs/CPU_RENDER_REPORT.md)。App/Window 按用户确认保留原版 GPU 呈现限制。
