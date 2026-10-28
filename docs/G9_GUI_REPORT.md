# G9 App/Window 与剩余公共项

固定官方 Node skia-canvas 3.0.8 A 为日常 oracle。原默认 GPU 和平台选择保留；未重编开发 Node B，未 commit/push/上传或发布。

## 已实现

原 `gui/window.rs`、`window_mgr.rs`、`event.rs`、App 事件循环和 Cadence 已分离到唯一 `canvas-core::gui`。Node adapter 保留 Neon Root/Channel/Promise 与语言返回读取；Python adapter 只读写普通配置/页 handle/事件 JSON。窗口、fit 矩阵、输入坐标、事件筛选、Vulkan/Metal renderer、swapchain、帧调度和设备选择均保留原算法。`scripts/gui_extraction.py` 和 source-map 检查 294 个原函数体及分离片段，不以重写 GUI renderer 代替原实现。

Python 新增真实 `App` singleton 和 `Window`：构造重载、Canvas/页引用与选择、尺寸/位置/标题/背景、fit/cursor、可见性/fullscreen/resizable/borderless、close/open、窗口列表、FPS、native/node 模式、frame/draw/idle 和实际 UI 事件。普通 EventEmitter listener 顺序、once、prepend、移除、identity、事件清单等共用单一 facade。新增 `DOMMatrix.dump()` 的原四列数值诊断和已移除的 textTracking setter：发 PropertyRemoved 警告，不改变 letterSpacing；不把移除属性误实现为别名。

GUI 始终在 OS 主线程。原 Canvas/Context/GPU 仍在 owner TLS，无新 unsafe Send/Sync。native event loop 执行期间只释放 GIL，仍在同一 OS 线程；进入 Python callback 时重新持有 GIL。页快照交给原 WindowManager，不搬动原 GPU context。headless import 不创建事件循环或要求显示器。默认 wheel 编译 window；不启用 window 的构建明确报原 support 错误。

Python 没有 Node 的内置 setImmediate 循环：在已有 asyncio loop 中创建 Window 会自动安排 launch；普通同步程序使用 `asyncio.run(App.launch())`。App.launch 立即设置原 running/started 标记并返回同一会话 awaitable；native 模式维持原阻塞 OS loop，node 模式按原 pump/cadence 与 asyncio 协作。取消单个 waiter 不取消会话；asyncio loop 关闭时在 owner 清理真实窗口。frame/draw callback 为同步接口。单位、异常、来源和所有权写于函数注释。

## 原行为与显式限制

保留原版 running 在 idle 后仍为 true、初始 frame 从 1 开始而 setup 不触发、readonly ID 和负页选择规则。WSLg Wayland 的 node 模式配显式 top/left 会因首次空 state 提前关闭；官方与 Python 均已单独复现，未修改原事件排序或强制选择 X11。默认 native 模式验收 Wayland，cooperative node/输入与客户区像素验收 X11；不称所有 compositor/启动时序一致。

官方原版对零尺寸初始 viewport 会在 Winit Wayland 原生 panic。输入保持在 fixture 与失败记录中；Python 对非正窗口尺寸明确抛 NotImplementedError，未返回占位窗口。原 App.quit 在 callback 内会重入 RefCell；Python 提前拒绝该危险 profile，应在 callback 调用 Window.close，外部仍可正常 App.quit。两项保留 G0，不称原版崩溃为验收通过。

Node Sharp/stream 返回对象不适用于无 Node 的 Python wheel，Canvas.toSharp 与 ImageData.toSharp 仍明确待定。全部 17 runtime export 已提供；408 条源码/声明清单逐项状态和归属见 [alpha API 状态](alpha-api-status.json)，包含实际原版没有的 toSharpSync、私有字段/readonly setter 和 singleton constructor 条目，没有从清单删除。成员存在只证明入口形状，不等于完整重载/异常/host 兼容。直接 Context constructor、完整 EventEmitter host/meta/最大监听警告、console.inspect/警告调度、G5 字形/emoji、G6 请求参数等仍待完成。

## 实际验收与来源

最终本地候选 alpha16 / Linux CPython 3.13，实际 wheel 字节/SHA、干净 venv、空 PATH 和仓库外 cwd 记录于 `test-runs/20261028-gui-final-1`。默认 GPU 全量旧场景/导出检查继续执行；本轮 98 项 GUI 状态输入中 97 项限定行为精确对齐，1 项零尺寸原版 panic 列为明确未支持。普通/STRICT 分进程采集。七个真实 X11 窗口用例比较客户区原始 RGBA、页面 raw/解码 PNG，包含原 fit、多页、resize、鼠标/滚轮/键盘、preventDefault 和默认关闭；所有通道无容差。OS 启动 focus/move 次序与 wall time 原样记录，不冒充确定序列。

原生 GDB trace 独立记录原 WindowRenderer::draw、Skia WrapBackendRenderTarget 与 Vulkano queue present 调用栈，fresh CPU 控制必须为零。窗口内容另作视觉核查。105 项实际 wheel 生命周期断言覆盖原 92 加 GUI 13；68 项 bootstrap 包括 GUI fit/cadence 不得改写的负控制。G9_REMAINDERS_EXACT 独立验证 dump 数值/return/no mutation 与两次 removed warning。最终通过数字以 run.json、verification.json 为准，不能从 oracle/启动校验推断。

WSLg 已有 Wayland，本轮安装发行版原生 libxkbcommon-x11-0/libxcb-xkb1 以验证原 X11 后端（日志 `20261028-gui-x11-environment`）。这是明确 OS GUI 前提，wheel 没有 .local fallback 或捆绑这些系统库。测试 Xlib/XTest 工具仅截取精确标题的本项目客户区，不截取其他窗口；首次输入注入受 WSLg 窗口移出屏幕影响，失败记录在 gui-render-1。修复测试控制器的可见屏幕位置与同步后，用同一公开参数重新采集两方，未改 Canvas 坐标/像素或 renderer。

本轮只验收 Linux Mesa 软件 Vulkan/WSLg。Windows/Metal/硬件 GPU、完整 IME/系统窗口管理器、打包矩阵、manylinux/static-fontconfig、许可证与发布仍未验收。下一大目标优先闭合 G0/G4 其余公共契约与 G5 字形来源/emoji，再推进 Windows wheel；G9 并不代表已经完整兼容或可以发布稳定版。
