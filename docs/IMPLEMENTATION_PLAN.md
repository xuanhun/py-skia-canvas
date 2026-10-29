# py-skia-canvas 详细实施方案

> 2026-10-29 最新发行状态：0.1.0a18 已发布至正式 PyPI、TestPyPI 和 GitHub Release，同一 wheel 的双平台独立安装/GPU/CPU 回验已通过。以 [RELEASE_STATUS.md](RELEASE_STATUS.md) 为准；下方未发布/待授权表述为历史记录。

> 2026-10-28 本批最新状态：G0–G9 在用户确认的 Python 宿主范围内已迁移并完成 Windows/Linux 本地 alpha 验收。先读 [本批交付报告](COMPLETION_REPORT.md) 和 [发行流程](RELEASE_WORKFLOW.md)；下面保留早期方案/记录，其中“尚待迁移”不覆盖最新报告。外部同步、Actions 实际执行、Release/TestPyPI/PyPI 仍需单独授权与验证。不要重装已可用工具链、重编 Node 或换掉已验收 wheel。


日期：2026-10-27。目标仓库：`xuanhun/py-skia-canvas`。发行名暂定 `py-skia-canvas`，Python 导入名 `py_skia_canvas`；发行前重新核对 PyPI 名称和发布权限。

执行状态以 [2026-10-27进度交接](PROGRESS_2026-10-27.md) 为准；本文保留原方案和各阶段门禁。现已有共享Canvas/Context/字体/paint/Page/GPU核心及独立Rust绘制验证，已有初始PyO3绑定与本地Linux CPython3.13 wheel，完整API与发布尚未完成；见[最新效果与混色报告](G7_EFFECTS_REPORT.md)。

## 1 目标与不变项

把固定版本 Node `skia-canvas` 的公开能力开放给 Python，复用它已有的 Rust、Skia、字体、Canvas、GPU 与导出实现，发布独立 wheel。用户选择的是**保留原默认 GPU 效果的 1:1 目标**，不是通过统一 CPU 降低验收标准。

首个兼容基线为 v3.0.8，源码 commit `042312a3f40b660b1d7dc0beba541486171bc5cc`。后续上游升级是单独的兼容版本任务；不能在绑定迁移时顺手升级到 v4、M148 fork、不同色彩模型或新版 Skia。

四个交付目标分别验收：

1. 公共 API 和可观测行为对齐，包括 JS 包装层定义的默认值、参数、异常和状态。
2. 同一环境、同一字体、同一实际后端下，指标与 RGBA 精确一致；默认 GPU 单独认证。
3. Python wheel 安装和运行不需要 Node/npm、Neon/N-API、skia-python 或本仓库资料快照。
4. Windows/Linux 从公开发行物全新安装可用，来源、构建、wheel 哈希和实际测试可追溯。

不把 Rust 代码重写为 Python，不重建 shaping、混色或 Vulkan 算法，不实现第二份绘图模型。PPT 只是未来使用方，库内不出现 slide/proto/母版等业务概念。

## 2 当前资料与尚未实现的部分

仓库已有上游源码快照、来源指纹生成器、原生导出索引、测试输入、Node oracle、精确比较器、文档校验与启动资料单测。它们不构成可用的 Python 渲染库；目前已有初始 Python native module 与本地 wheel，尚无 PyPI 发布。

历史实验确认：3.0.8 的构造 `gpu:false` 只写 disabled 状态标记，实际 `engine` 仍按默认初始化；Linux 原生断点捕获了 GPU 调用。公开 `canvas.gpu=false` setter 才真正选择 CPU。同 CPU 的 Office 八行在两 OS 精确一致，但旧 Python renderer 对原默认 GPU 仍有 Windows 2,471 / Linux 3,719 像素差异；Windows emoji 438 与透明色 80 在真 CPU 也未关闭。见 [历史记录](../references/history/README.md)。

这些结果属于旧 `skia-python` 路线，不是新库的通过记录。新路线停止优先补 `skia-python` Vulkan BackendContext，不把它作为新库依赖。

## 3 来源锁定和双重 Node 对照

### 3.1 锁定内容

冻结 npm `skia-canvas@3.0.8`、上游源码 commit、JS 包装、类型声明、Cargo.lock、features、目标平台、Skia revision、编译器和 GN 参数。Rust 顶层依赖为 `skia-safe 0.88.0`，不能仅凭 crate 号推断已安装 npm 二进制的全部构建参数。

Linux 上游构建有 static-fontconfig patch；Windows 字体后端也必须按原版核对。不要复制旧 `skia-python` 的 FreeType/Skia 编译参数当作 Node 版配置。上游预编译缓存若无法完整重现，先记录差异，不把新编译 Node 当唯一标准。

### 3.2 两个 oracle

- **A 原发布物**：固定 npm 3.0.8 的原生包及文件哈希，是外部行为基线。
- **B 同核 Node**：迁移后同一份 `canvas-core` 由保留的 Node 绑定调用，用于判断核心拆分是否改变逻辑。

用户在2026-10-28调整日常验收为Python↔固定官方A。已有A/B历史证据保留，后续不要求每批重编开发Node B或以B作主门禁；同核Node adapter继续维护，核心唯一性和机械拆分源码检查仍保留。官方A只作开发对照，不进入Python运行时或fallback。

## 4 目标架构

```text
Python 公共 API → PyO3 绑定 ─┐
                           ├→ 同一份 canvas-core
开发用 Node JS → Neon 绑定 ─┘    → skia-safe → 原 Skia C++
                                → Vulkan Windows/Linux
                                → 原字体、图片与编码依赖
```

唯一核心保存 State、路径、文本、字体管理、绘图记录、图片、过滤器、GPU host、缓存和导出逻辑。两个绑定只做语言参数/对象/异常/异步入口适配。不能把独立 Rust fork 的新渲染算法混入这一核心。

当前工作结构（core/Node/Python均已建立，完整API继续实现）：

```text
crates/canvas-core/src/      唯一生产核心，由上游机械拆分而来
crates/python/src/           PyO3 类、转换和模块入口
crates/node/src/             开发用 Neon adapter，不编入 wheel
python/py_skia_canvas/       薄公共入口、类型声明、必要资源
tests/fixtures/             跨语言场景输入和资源声明
tests/parity/               共用的差分测试与结果格式
scripts/                   校验、采集、对比、构建和发行脚本
references/upstream/        原始只读来源，不是 runtime
test-runs/                 忽略的大型证据目录，每轮独立
```

初期选 PyO3 + Maturin；在 G0 固定实际验证的稳定版本和 Rust MSRV。先建立 CPython 3.13 Windows AMD64 / Linux glibc x86_64 的可重复 wheel，再验证其他 Python/ABI/架构。ABI3 是后续减少 wheel 数量的候选，不在首次构建时未经验证宣称多版本可用。

## 5 机械拆分方法

### 5.1 原文件职责

| 来源 | 保留的核心 | 需要隔离的入口 |
| --- | --- | --- |
| `src/context/mod.rs` | State、栈、变换、路径、paint、文本绘制 | JsBox/Finalize、Neon 相关类型引用 |
| `src/context/api.rs` | 每个 API 的原参数处理规则与调用顺序 | FunctionContext/JsValue 读取和 JS 返回值构造 |
| `src/context/page.rs` | PageRecorder、RecordingSurface、PageCache、编码和导出 | pages_arg 等 JS 对象解析 |
| `src/gpu/` | 原设备选择、context、MSAA、surface、线程缓存和清理 | 与 Node/gui 外层事件循环耦合的入口 |
| `src/font_library.rs` / `typography.rs` | FontMgr、variable 实例、缓存、Paragraph、字体指标 | JS 数组、Neon 参数和字体元数据对象构造 |
| image/path/filter/gradient/pattern/texture | 原几何、shader、image 与效果行为 | 每类对象的 Boxed 类型、语言值转换 |
| `src/utils.rs` | 原数学、字符串及解析规则 | 混在同文件中的 Neon 参数助手 |
| `lib/classes/*.js` / `lib/index.d.ts` | 公共 API、重载、默认值、几何和 CSS 规范化契约 | Node 模块装载、Promise/Buffer/WeakRef 包装 |

原生导出清单不是全部 API：`loadImage`、DOM 几何、公共重载、getter/setter、FontLibrary.use、Canvas pages 等还有 JS 逻辑。G0 必须给全部 JS export/类型声明建立条目和源位置。

### 5.2 每批规则

先原样搬移、保持符号和函数体；只调整模块可见性、依赖方向及语言值边界。每批标明旧位置→新位置、调用者、保留的默认值和测试。先维持原名，稳定后再做语义命名，不把改名、算法优化和 API 扩展混成一批。

JsBox 包装不能进入 core 的字段或函数签名。遇到 `BoxedGradient` 一类混合类型，提取它实际拥有的 Rust 资源引用，不做全局文本替换或伪造 JS runtime。原来由 JS 包装执行的 radii/CSS/几何转换也必须迁移，不能假设 Rust 代码已涵盖。

生产 Python 构建的 Cargo feature 图不得包含 Neon/N-API。需要保留的 Node adapter 放在独立 crate/feature；不要只关闭 `#[neon::main]` 却把 Neon 类型继续带入 Python 核心。

## 6 Python API 和语义

详见 [API 对齐规则](API_COMPATIBILITY.md)。首先保留 Canvas、CanvasRenderingContext2D、Path2D、Image、ImageData、FontLibrary、CanvasGradient、CanvasPattern、CanvasTexture、TextMetrics、DOM 几何、App/Window 等原公共名称。

主方法先用 Node 的 camelCase：例如 `getContext`、`fillText`、`measureText`、`toBufferSync`。可选 snake_case 只作为同一实现的别名。支持阶段可以不同，但不能把不支持的方法实现成假成功；alpha 版本列明能力，完整 1.0 对齐要求盘点内所有公共项都已解决。

同步方法 `toBufferSync` 返回 bytes；异步 `toBuffer` 返回可 await 的 bytes，`.png` 等 Promise 属性在 Python 对应 awaitable。先做同步 PoC，再恢复原 Rayon 异步导出，不能直接用 `asyncio.to_thread` 搬动 GPU context。类型重载、忽略非法 setter、STRICT 环境模式、非有限数值、缺参数和 `null`/缺省区别都进入契约测试。

Python 与 JS 必须有必要的语言值适配，但它不是第二套绘图/文档转换模型。f64→f32 在原转换点执行，不先四舍五入；字符串、UTF-16 索引和孤立代理项的行为逐项对照 Node，不以 Python 默认语义猜测。

### 6.1 默认 GPU 与已知原行为

兼容 profile 默认保持 3.0.8 的可观测行为，包括构造 gpu:false 与 setter 的已知区别。不得为了清理这个 bug 顺便改变默认输出；若以后提供修正行为，须明确的不同 profile/版本和专门测试。

Vulkan设备、graphics queue、surface与MSAA沿用源规则：离散→集成→虚拟→CPU→其他；N32Premul+sRGB、Budgeted Yes、BottomLeft；支持4则默认4，否则取源有效样本列表的最大值；contrast0/gamma1.4/unknown geometry。不得改成 F32、GL 或 shader workaround。

原引擎在 GPU 不可用时按原策略选择 CPU，可以保留该行为，但测试必须区分“原自动策略的 CPU 结果”和“GPU 已验收”；GPU-required 作业不能用 CPU 或 skip 冒充成功。

## 7 生命周期与线程

Canvas/context/path/image/font 等 wrapper 拥有正确的 Rust 引用，不能向 Python 暴露由另一套 skia-python wheel 管理的裸 Skia 指针，也不能让 m140/m144 对象互传。core 与 Python 绑定必须链接同一份受控 Skia。

原 Canvas/Context 的 WeakRef、页面列表及失效时机需要审计：不能为防崩溃静默把弱引用全部变强引用，再称生命周期完全对齐。允许语言层实现不同，但可观察行为和资源安全必须有记录及测试。

原 VK_CONTEXT 与字体库是线程局部。初期线程亲和的 Python 类可显式拒绝跨线程访问；`unsendable` 只解决访问约束，不自动解决跨线程 GC/析构。禁止未经证明的 unsafe Send/Sync、全局 mutex 强行搬迁 context 或每个 fillText 重建设备。

同步重绘可在安全边界释放 GIL，但闭包内不得碰 Python 对象。异步导出沿原 Page snapshot/materialize/非纹理位图传递规则，只把可发送的数据交给 Rayon；future 完成时再安全回到 Python event loop。验证主对象先释放、future取消、重入、异常、解释器结束和 worker 回收。

FontLibrary 的注册、alias、variable clone、reset 与缓存失效保持源命名空间。字体文件/内存数据的持有时间、FontMgr/Typeface/Paragraph 依赖关系单独验证；不在 wheel 中复制系统字体。

## 8 测试体系

测试以统一 fixture 操作序列分别驱动 Node 和未来 Python；此 JSON 是**测试协议**，不是产品运行的绘图指令解释器。

验证分为：公共 API 输入/返回/错误；实际绘制 trace和字形指标；原始像素；PNG/PDF/SVG 等编码语义；资源生命周期；部署/平台。相同 PNG 只能证明该图，不能推断完整 API 或系统兼容。

逐像素比较解码后相同格式、相同尺寸的RGBA，不做缩放、色彩空间转换、边缘裁剪或隐藏alpha=0 RGB。PNG 压缩字节可不同，但像素、DPI/色彩/alpha等元数据语义仍需对照；PDF/SVG以结构与同一明确栅格器的视图分开测试，不用文件大小当成功。

同 host 的A/B/Python共享同一字体和设备/driver。Windows与Linux各自对齐本机Node，不要求不同字体/驱动的两OS图片相同。共享的可再分发字体另建版本/哈希/许可清单；系统fallback、CJK、emoji、variable字体作为独立场景，缺资源要报告，不静默替换请求字体。

当前 [场景集](../tests/fixtures/scenarios.json) 是可执行 starter，不是完整方法覆盖。完整覆盖以API清单的每项状态、断言、原始结果路径为准：`inventoried / core_extracted / python_bound / contract_tested / gpu_verified / released` 不可混为一个百分比。

## 9 分批实施

按 [任务清单](TASKS.md) 的G0–G11执行。每批先固定输入、选最小相关集，再修改唯一核心或绑定；保留差分与失败。日常直接验证官方A↔Python；开发Node B按用户最新要求不再每批重编；每完成一批就更新状态、证据和下一步，不反复跑无关全量。

第一轮必须取得一个真实Vulkan表面：白底、分数坐标矩形、一行彩字/黑字、raw/PNG、实际GPU信息。不以模块能import、能写纯白PNG或CPU全零结束PoC。若A↔同源码重建B已有差异，先解决构建provenance，不能靠Python补偿。

## 10 构建与发布

Maturin负责PyO3 wheel；运行期需要的Skia/Rust代码编入native扩展。目标机器仍需匹配的Vulkan loader/driver和字体环境，所谓独立pip包不等于无操作系统依赖。用户安装wheel时不编译Skia、不安装Node，不在import阶段联网下载native包。

优先矩阵：Windows AMD64 CPython3.13、Linux glibc x86_64 CPython3.13；Linux发布wheel必须在合规manylinux构建环境生成或经真实auditwheel检查修复，不把WSL的linux标签文件改名成manylinux。随后验证CPython3.10–3.14/ABI3；macOS Metal和ARM64各立任务，不默认受支持。

CI分为资料/结构、Rust/core、wheel构建、全新安装、GPU差分、发布六类。普通hosted runner不保证有可用Vulkan；用明确配置的Mesa llvmpipe作软件Vulkan GPU语义基线，并以真实Windows GPU作另一个目标。GPU runner采用专用标签，不能运行不受信任PR的任意代码；保留driver/device/ICD/样本数。

正式发布步骤和门禁见 [测试与发布规则](TEST_AND_RELEASE.md)。GitHub仓库存在不等于PyPI项目可用；先核对名字和Trusted Publisher。初次发行只能发布声明清楚的真实alpha能力，不能发空wheel占名；完整兼容版本要求全表闭环。

## 11 外部集成边界

PPT项目只有在新wheel完成指定子集验证后才接入。其调用点应消费新Canvas API，不把skia-python Canvas/Paint/Typeface对象直接塞进新Rust核心。调用点改造、字体指标返回、P1/P3共享基础能力在原PPT仓库另开批次，不在本通用库引入PPT adapter或复制OpenXML代码。

现有旧renderer和历史测试不删除，避免新会话把未完成的独立库误当已接管生产。旧仓库的Windows emoji/透明色证据只作回归输入，新库必须重新测量。

## 12 首轮执行清单

1. 检查Git远端、现有修改、README/AGENTS和来源哈希，不覆盖用户文件。
2. 运行启动资料单测与校验；记录为BOOTSTRAP_VALIDATED，不写渲染PASS。
3. 完成G0公共API/JS规范化盘点，固定工具链和依赖，建立A原发布物环境。
4. 在Windows/Linux采集同host A的默认GPU基线、实际backend信息及字体资源manifest。
5. 原源码构建B并对A；先证明构建可对齐，再实施核心分离。
6. 每批生成不可变证据和审图记录；只有真实通过的目标才更新状态。

资料阶段不需要仓库发布权限；push、CI运行、GitHub Release、TestPyPI、PyPI授权分别处理。不复制浏览器登录态或访问令牌，不把凭据写进仓库。


G8 多页与完整导出普通输入已迁移；范围、并发 Vulkan 初始化锁的来源和限制见 [G8 报告](G8_EXPORT_REPORT.md)。下一大目标为 G9 App/Window 与剩余公开项。G0 host/Sharp/极端输入及跨平台/字体/发布门禁继续保留；最终可用 wheel 字节与检查结果以 G8 最终记录为准。


G9 App/Window 与普通事件/会话已迁移；范围、真实 GUI GPU/像素证据和原版危险输入见 [G9 报告](G9_GUI_REPORT.md)。全部 408 条清单的归属和剩余项见 alpha-api-status.json（docs 下）。完整兼容、Node Sharp 互操作、G0/G4/G5 与平台/发布门禁仍保留。
