# 分批任务清单

2026-10-28 新增纯 CPU 验收已完成：双平台 3,561 普通/3,175 STRICT 场景、23 项 CPU 生命周期、真实无 Vulkan/无 GPU 容器和原生 Raster 调用验证，见 [CPU 报告](CPU_RENDER_REPORT.md)。这是独立门禁，不替代 GPU 证据。用户已确认窗口保留原版 GPU 限制；Windows 并行矢量序列继承限制保留。

> 2026-10-28 本批最新状态：G0–G9 在用户确认的 Python 宿主范围内已迁移并完成 Windows/Linux 本地 alpha 验收。先读 [本批交付报告](COMPLETION_REPORT.md) 和 [发行流程](RELEASE_WORKFLOW.md)；下面保留早期方案/记录，其中“尚待迁移”不覆盖最新报告。外部同步、Actions 实际执行、Release/TestPyPI/PyPI 仍需单独授权与验证。不要重装已可用工具链、重编 Node 或换掉已验收 wheel。


截至2026-10-28，G0/G1已部分推进，G2已迁移paint/image、Page/缓存/导出、GPU、Canvas/Context/State、字体及布局；独立Rust绘制已验证，Path扩展与语言边界仍待完成，G3首批限定输入的真实Python绑定与Linux CPython3.13 wheel已实现，G4当前路径/数值变换/clip/描边、独立Path2D/路径特效与roundRect、三类CanvasGradient及共享样式引用、DOM数值对象/矩阵重载、原DOMMatrix运算/CSS parser及createProjection已实现；FontLibrary注册/查询/reset及ctx.font CSS解析/实际字体选择已绑定，9个文本状态属性已绑定，G6的Image/ImageData/图像绘制/像素读写、pattern/texture和加载事件普通入口已迁移；textDecoration和完整TextMetrics数据/浅只读构造、measureText普通输入转换已绑定，所选测量布局glyph/字体四表已核对，music/emoji仍缺字，安全cluster与完整字形/布局验收与DOM/JS契约、后续批次及完整参数契约仍待完成。证据和限制见 [进度交接](PROGRESS_2026-10-27.md)、[效果与混色批次](G7_EFFECTS_REPORT.md)。每批都要有小范围回归、实际结果与交接；没有证据不打勾。

| 批次 | 任务 | 本批产物 | 进入下一批的门禁 |
| --- | --- | --- | --- |
| G0 | 固定上游/工具链/包名；补全JS+native公共API、feature和coercion盘点 | upstream lock、API ledger、构建provenance schema | 资料校验通过；所有顶层export都有归属；明确原npm与源码构建差异 |
| G1 | 建立A原发布物oracle及Windows/Linux原默认GPU/字体基线 | fixture run、metrics、raw、PNG、engine/fonts manifest | 实际GPU和资源可用，结果可复跑；不是CPU标签或纯白图 |
| G2 | 原源码先构建Node B，再机械分离唯一core和Neon adapter | Rust workspace、source-map、每批patch | Python↔官方A相关场景精确一致；Python/core feature图无Neon依赖 |
| G3 | PyO3最小真实Canvas、context、状态栈、GPU surface和同步PNG/raw | native module、最小wheel、生命周期测试 | Python默认GPU真实渲染，与A/B的矩形/彩字/黑字精确一致 |
| G4 | 基础路径、变换、clip、stroke、gradient与DOM几何 | 绑定、签名/默认值表、差分cases | 分数坐标、嵌套clip、规则/重载/异常全部相关差分通过 |
| G5 | 字体库、文本、全部测量与排版/装饰契约 | font fixtures/许可、metrics差分、文本图 | regular/bold/italic/CJK/RTL/组合字/variable/emoji及作用域/reset分别通过 |
| G6 | Image/ImageData、Canvas源、采样、pattern/texture、像素 | 图片资源与绑定、raw/PNG比较 | crop/alpha/越界/加载失败/资源释放不偏差 |
| G7 | 剩余path扩展、filter、shadow、composite等 | 完整效果绑定与场景 | 无临时近似；原调用顺序、参数与像素一致 |
| G8 | Promise对应awaitable、PageCache、导出格式/序列、取消与回收 | async bridge、导出文件、并发资源报告 | 不搬动GPU context；异步/同步像素和元数据对齐，无GC/取消崩溃 |
| G9 | 补全App/Window与其余公共项，或明确alpha尚未完成的列表 | GUI feature/事件契约、API ledger | 完整兼容版不能有无归属/未处理公开项，headless和GUI分层验收 |
| G10 | wheel矩阵、干净安装、TestPyPI/GitHub/PyPI发布 | 已验收wheel、SHA、来源、许可证、安装证据 | 无Node/skia-python/工作区依赖；发布字节就是验收字节；各目标真实测试 |
| G11 | 原PPT项目消费独立包的单独集成批次 | 调用点改造和实际P1/P3回归 | 不混用两套Skia对象；新库自身不携带PPT模型；旧差异重新验证 |

G3可以发布真实但范围明确的alpha；不能据此称“完整Node对齐”。G9和全部方法级状态闭环后才讨论完整兼容版本。发布alpha也要有wheel安装、GPU图、版本说明和发布授权，不发占位包。

## 每轮交接

在 `test-runs/<new-id>/run.json` 记录源码/依赖/环境指纹、命令、选择的cases、状态、错误、产物SHA；视觉结论另存review。更新本表的对应项时只引用实际存在的结果。失败原样保留，不改oracle参数获得零差异。

后续继续完成G0人工语义审计与G1原生surface trace，并从G2首批结果继续提取其余核心。启动资料单测不表示这些门禁通过；首批滤镜完成也不表示整个核心已去Node。

用户最新要求：每次完成一个大目标；日常只以Python↔官方A作兼容验收，开发Node B不再每批重编。G6普通图像/像素/pattern/texture目标已完成；全量host/Sharp/网络选项留G0，G7滤镜/阴影/混色/marker fit已完成迁移，G8多页与完整导出/异步资源边界已迁移，下一功能大目标为G9 App/Window与剩余公共项。

G7完成普通效果属性8项/16个共享操作和原CSS FilterSpec边界；670个普通场景对官方A、369个G6/G7 STRICT场景另验，76项生命周期。完整宿主对象/子类/coercion等G0状态不据此全部完成。


G8 多页与完整导出普通输入已迁移；范围、并发 Vulkan 初始化锁的来源和限制见 [G8 报告](G8_EXPORT_REPORT.md)。下一大目标为 G9 App/Window 与剩余公开项。G0 host/Sharp/极端输入及跨平台/字体/发布门禁继续保留；最终可用 wheel 字节与检查结果以 G8 最终记录为准。


G9 App/Window 与普通事件/会话已迁移；范围、真实 GUI GPU/像素证据和原版危险输入见 [G9 报告](G9_GUI_REPORT.md)。全部 408 条清单的归属和剩余项见 alpha-api-status.json（docs 下）。完整兼容、Node Sharp 互操作、G0/G4/G5 与平台/发布门禁仍保留。


2026-10-28 构造与参数大目标：Canvas options/尺寸重置、独立 CanvasRenderingContext2D(Canvas)、当前路径/Path2D 数值参数、rect/基础变换、描边数字、dash、命中与 gradient 的普通 primitive/array 参数计数、转换、异常与 STRICT 读取已迁移。新增 1429 个不同场景，连同旧场景共 2114 普通/1813 STRICT；11 种 STRICT 环境值另验；117 项 wheel 生命周期、70 项 bootstrap。实际最终 wheel 与检查以 [构造与参数报告](G0_G4_ARGUMENT_REPORT.md) 和 `test-runs/20261028-contracts-final-1` 为准。文本绘制等其余参数、完整 host/subclass/proxy/valueOf/EventEmitter/Sharp、G5 字形/emoji 与平台/发布仍待完成。
