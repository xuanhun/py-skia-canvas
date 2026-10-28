# API 对齐规则

> 2026-10-28 本批最新状态：G0–G9 在用户确认的 Python 宿主范围内已迁移并完成 Windows/Linux 本地 alpha 验收。先读 [本批交付报告](COMPLETION_REPORT.md) 和 [发行流程](RELEASE_WORKFLOW.md)；下面保留早期方案/记录，其中“尚待迁移”不覆盖最新报告。外部同步、Actions 实际执行、Release/TestPyPI/PyPI 仍需单独授权与验证。不要重装已可用工具链、重编 Node 或换掉已验收 wheel。


初始逐项清单见 [公共API ledger](public-api-ledger.json)：17个runtime export、408个重载/accessor条目，含JS来源、直接native路由与默认表达式。它是源码盘点，`contractAudit`仍为pending；声明/运行时差异、动态实例字段、宿主事件继承与单位/所有权审计不能据此视为完成。

## 对齐对象

对象是Node版v3.0.8的整个公共API，而不是仅Rust导出或PPT所用少数方法。盘点源为 `references/upstream/skia-canvas-3.0.8/lib/index.js`、`lib/index.d.ts`、`lib/classes/*.js` 和 `src/lib.rs`。自动原生索引只提供起点，JS侧重载和派生方法须逐项补齐。

| 族 | 首批能力 | 完整兼容仍须覆盖 |
| --- | --- | --- |
| Canvas/Context | 创建、尺寸、getContext、状态栈、默认GPU、同步PNG/raw | 多页、reset、缓存、全部导出选项及异步属性 |
| 路径与几何 | Path2D、基础path、transform、clip、fill/stroke、hit test | roundRect规范化、conic、SVG path、op/interpolate/trim/jitter等扩展、DOMMatrix/Point/Rect |
| Paint与效果 | fillStyle/strokeStyle、线型、gradient、alpha/composite | pattern、texture、shadow、filter、dashFit/marker、采样质量 |
| 文本与字体 | CSS font、fillText/strokeText/measureText、baseline、字距 | CJK/RTL/组合字/emoji、variable、FontLibrary全部重载、wrap、decoration、outline、metadata与reset |
| 图像与像素 | Image/ImageData、drawImage、get/putImageData | Canvas源、多参数裁剪、加载/解码错误、loadImageData、色彩与alpha语义 |
| 导出与并发 | 同步bytes、PNG/raw、生命周期 | Promise对应awaitable、文件/序列、PDF/SVG/JPEG/WebP、density/matte/MSAA/EXIF等 |
| App/Window | 源码完整保留，headless里不冒充已绑定 | 事件循环、窗口/回调、关闭、帧速率与平台feature；不能在“完全对齐”分母中消失 |

## 语言边界

- Node 特有的 Buffer/Promise、Sharp stream 及浏览器/窗口事件对象需要逐项登记语言对应。`toSharp/toSharpSync` 不能在无 Node 的 Python wheel 返回一个真正的 Node Sharp 对象；G0 明确这类宿主互操作的等价输入输出/替代接口及验证边界，需用户确认后再宣称完整兼容，不能悄悄删项或重新依赖 Node。
- 主名称、属性与重载保留Node写法；snake_case可选别名不另存状态、不复制算法。
- 同步 `toBufferSync` → bytes；异步 `toBuffer` → awaitable[bytes]。Python阻塞便利方法不能冒充Node异步方法。
- 源支持的JS缺省、undefined、null、false、0、空串不同；fixture用显式标记区分。不要统一成None/空dict。
- JS Number到Rust f32/f64的转换点、NaN/Infinity/-0、超界/负尺寸依原行为。测试数据中的特殊数值使用tag，不生成非标准JSON。
- JS字符串到Rust的转换、UTF-16偏移、孤立surrogate与Python编码异常需要显式审计。不要按Pythonlen截断glyph范围。
- Python异常类型允许采用明确的对应类，但原错误类别/条件/消息必须可追踪；建立映射表并测试，不把所有错误变成RuntimeError。
- Node包装对非法setter可能忽略而非throw，且受 `SKIA_CANVAS_STRICT` 模式影响；两个模式分进程采集，不能假定Python天然行为正确。
- 时间/路径/网络加载是单独契约：测试不用任意外网数据，实际下载失败不能转换成空Image。

## GPU 与原行为

3.0.8构造gpu:false与setter的差异须保留在兼容profile。原`.engine`状态标签不是实际backend证明；至少记录`.gpu` getter、设备/driver、实际surface路径与源构建配置。声明GPU验收必须有GPU-required作业。

不以“修bug”为名改变surface格式、MSAA、字体选择或gamma。未来改善行为要有显式版本/兼容profile、差异文档和用户决定。

## 资源与对象

不对外交换来自skia-python的C++对象、指针或capsule。全库共享自身的唯一Skia构建。Page/context/font/image持有和释放顺序要验证，不能假设GIL等于GPU线程安全。跨线程访问、future取消、GC和解释器关闭都是API能力的一部分。

## 方法级登记格式

G0给每个公共方法/属性/重载登记：`id`、JS来源/原生来源、默认值、输入/输出/异常、所属core方法、Python入口、场景ID、feature、状态、证据。getter/setter和重载分开计数。返回类型转换直接在语言绑定处理，不另建可变图形模型。

状态按项推进：inventoried → core_extracted → python_bound → contract_tested → gpu_verified → released。这些状态不是同一含义。未实现项只能在清单中标planned，不返回占位成功。

本轮 TextMetrics/measureText 普通输入、浅只读字段和所选测量布局字体身份的限定状态见 [G5测量与字形报告](G5_METRICS_REPORT.md) 与 [逐项API状态](metrics-api-status.json)。子对象用原键名的Python list/dict，保留引用身份；JS host/coercion和实际绘制字形/emoji验收仍待完成。

G6普通Image/ImageData/图像绘制与像素读写/pattern/texture及加载事件已迁移，限定状态见 [图像与像素报告](G6_IMAGING_REPORT.md) 和 [逐项图像API状态](imaging-api-status.json)。用户于2026-10-28明确日常验收直接Python↔固定官方Node A，开发Node B不再每批重编。

G7普通filter/shadow/globalCompositeOperation/lineDashFit与globalAlpha边界已迁移，限定状态见 [效果与混色报告](G7_EFFECTS_REPORT.md) 和 [效果API状态](effects-api-status.json)。原算法/重复filter顺序/无效setter/STRICT消息与缓存规则保留，完整JS宿主契约仍为G0。


G8 多页与完整导出普通输入已迁移；范围、并发 Vulkan 初始化锁的来源和限制见 [G8 报告](G8_EXPORT_REPORT.md)。下一大目标为 G9 App/Window 与剩余公开项。G0 host/Sharp/极端输入及跨平台/字体/发布门禁继续保留；最终可用 wheel 字节与检查结果以 G8 最终记录为准。


G9 App/Window 与普通事件/会话已迁移；范围、真实 GUI GPU/像素证据和原版危险输入见 [G9 报告](G9_GUI_REPORT.md)。全部 408 条清单的归属和剩余项见 alpha-api-status.json（docs 下）。完整兼容、Node Sharp 互操作、G0/G4/G5 与平台/发布门禁仍保留。


2026-10-28 构造与参数大目标：Canvas options/尺寸重置、独立 CanvasRenderingContext2D(Canvas)、当前路径/Path2D 数值参数、rect/基础变换、描边数字、dash、命中与 gradient 的普通 primitive/array 参数计数、转换、异常与 STRICT 读取已迁移。新增 1429 个不同场景，连同旧场景共 2114 普通/1813 STRICT；11 种 STRICT 环境值另验；117 项 wheel 生命周期、70 项 bootstrap。实际最终 wheel 与检查以 [构造与参数报告](G0_G4_ARGUMENT_REPORT.md) 和 `test-runs/20261028-contracts-final-1` 为准。文本绘制等其余参数、完整 host/subclass/proxy/valueOf/EventEmitter/Sharp、G5 字形/emoji 与平台/发布仍待完成。
