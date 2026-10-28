# G8 多页与完整导出

兼容目标仍为固定官方 Node skia-canvas 3.0.8 A；本轮没有重编开发 Node B，没有 commit、push 或发布。Canvas 是通用绘图库。

## 已迁移范围

`newPage()`、`pages` 与当前页选择；旧页独立状态、顺序、尺寸和 head-only reset。PNG、JPG/JPEG、WebP、raw、PDF、SVG 的同步/异步 buffer、文件、文件序列、MIME/base64 URL、同步 `toDataURL`、六个 Promise 属性与三个 deprecated alias。保留 quality、density、matte、msaa、outline、downsample、colorType、page、filename format override、@Nx 和 {N} 原行为。PDF 默认导出所有页，位图/SVG 默认最新页，显式 page 为 1-based/负索引；负数字符串的原 JS 拼接特例也保留。

原 PageRecorder、PageSequence、PageCache、JPEG/WebP/PNG 编码、PDF/SVG、Vulkan 选择和绘制算法继续由唯一 Rust core 执行。原 canvas.rs 两个编码/文件分支与 utils.rs ExportOptions 字段打包只作语言分离；机械生成器、来源片段与哈希见 `scripts/export_extraction.py`、`crates/source-map.json`。

Python fixed-page handle 只持 metadata lease，Context 留在创建线程 TLS；页可独立回收，旧页可在 Python Canvas 回收后继续保留原 native 资源。async 在调用时立即 snapshot，并在创建线程执行原 `materialize`，再交给原 Rayon worker；task 仅持结果 channel。编译器验证原 PageSequence/ExportOptions 可 Send，没有新增 unsafe Send/Sync，没有 Python executor 搬动 GPU context。await 可重复；取消一个 waiter 不取消原 native 工作，丢弃 awaitable 不使后台任务假成功。源码函数注释记录单位、异常、来源和线程边界。

## 并发初始化修复

压力测试发现**官方 A 与最初 Python 候选均会原生崩溃**：`test-runs/20261028-export-race-diagnosis` 中，官方第 4 个进程、Python 第 2 个进程退出 11；GDB 保存了 Vulkan loader → vulkano DeviceFunctions::load → 原 VulkanContext::new 的崩溃栈。不能把这称为通过，也没有用 CPU 或减少默认线程掩盖。

共享 core 新增极窄的初始化 mutex，仅把原 status/with_context 中两处 `VulkanContext::new()` 调用转发至初始化锁。**原 new 函数完整保留**，设备枚举/打分/选择、队列、Skia 初始化、默认 GPU、Rayon 并发绘制与 5 秒 idle 生命周期均保留；锁在构造返回后立即释放。该变化同时供 Node/Python 消费。source-map 保留 236 个完整原函数体，另外两处调用点单列 initializationGuardFragments；不是把改过的函数冒称原封不动。修复后 100 个新进程（每个 12 个并发异步导出加同步导出）的压力检查通过；最终同一 wheel 另作 100 进程复验，记录于 `20261028-export-final-stress-1`。

## 验收入口

最终候选为本地 Linux x86_64 / CPython 3.13 `0.1.0a15`；最终 wheel、SHA 和同一字节的干净安装记录见 `test-runs/20261028-export-final-1/run.json`、`wheel-candidate.json`、`verification.json`。构建只复用已核对的 Skia C++ 缓存，重编 Rust/PyO3；不依赖 Node、Neon/N-API、skia-python 或 .local 运行时 fallback。

本轮验收范围为：原有 670 加 15 个多页场景，累计 **685** 个普通场景；G6/G7/G8 **384** 场景另验 STRICT，不重复算功能覆盖。独立 **206** 个导出用例另验普通/STRICT，各 **224** 个文件；六种格式、选页/多页 PDF、序列命名、参数错误、URL、异步 eager snapshot。JSON、RGBA 和解码 PNG 无容差，alpha=0 的 RGB 仍比较。

PDF 使用只作开发审计的 pypdf 6.1.1 检查页/资源/字体/解码流结构，并以同一 Poppler 26.01.0、72 DPI 对全部页比较 RGBA。结构只排除 Info 的 CreationDate/ModDate 和 trailer ID；文件原字节不改。SVG 比较 XML 和原核心解码后的 RGBA；PNG/JPEG/WebP 比较解码 RGBA 与元数据；raw 逐字节。只检查 PNG 字节相同不能替代这些检查。Poppler 提取在 .local，未作为 wheel 依赖。

92 项生命周期、66 项 bootstrap、100 个最终 wheel 并发压力进程、原生 surface/submit trace 和视觉审阅均为独立证据。原生 trace 的 readback 为 1 surface/6 submit，包含 worker 的 PNG 导出阶段为 2 surface/5 submit，fresh CPU 控制为 0/0。缺少任何一项不应从启动资料检查或 oracle 采集推断通过；最终数字以 run.json 的实际结果为准。此前失败、异常文案修正与比较工具对分数尺寸的修正原样保留在 export-before / export-audits-1 / export-audits-2，未覆盖旧证据。

## 保留项

本轮完成普通输入的多页/完整格式/awaitable，不称全 API 或发布验收。JS host/proxy/valueOf/原型、Node URL/Sharp/流、极端分数 page 导致的原生 panic 等留 G0；分数 page 以 NotImplementedError 明示，未伪造输出。完整 App/Window 留 G9；G5 emoji/music 缺字、安全 cluster 与实际绘制字体来源、G6 全量 EventEmitter/请求选项、Windows/Metal/硬件 GPU、manylinux/static-fontconfig、完整许可及发布仍待验收。当前 GPU 证据仅 Linux Mesa 软件 Vulkan。
