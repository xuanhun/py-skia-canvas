# 启动测试与后续差分入口

当前已有真实 Python Canvas 本地 alpha wheel，尚未发布。下文区分资料检查、原 Node 采集和真实 wheel 验证；29 个 starter case 不是完整公共 API 测试集。最新投影批次见第15节。

## 1 不依赖 Node/GPU 的资料检查

在项目根目录使用 Python 3.10+：

```shell
python -m unittest discover -s tests/bootstrap -v
python scripts/validate_bootstrap.py
```

包括来源指纹、原生入口位置、文档链接、场景/资源引用、精确比较算法、alpha=0 RGB、uint8 差值、缺失指标和篡改证据的负例。成功状态仅为 `BOOTSTRAP_VALIDATED`。

需要显式重建来源索引时使用 `python scripts/refresh_reference_index.py`，随后审查 Git diff；校验失败时不要先重建索引来隐藏问题。

## 2 原始 Node 基线采集（仅研发工具）

在本项目新建独立 oracle 环境，固定原 npm `skia-canvas@3.0.8`。不要把其他 PPT 工作区作为依赖。采集器不自动安装包、不搜索旧目录、不接受其他版本。

PowerShell 示例：

```powershell
npm install --prefix .local/oracle --no-audit --no-fund skia-canvas@3.0.8
node tests/oracle/capture-node.mjs --module (Join-Path $PWD '.local/oracle/node_modules/skia-canvas') --out test-runs/oracle-win-001 --require-gpu
```

Linux 示例：

```shell
npm install --prefix .local/oracle --no-audit --no-fund skia-canvas@3.0.8
node tests/oracle/capture-node.mjs --module "$PWD/.local/oracle/node_modules/skia-canvas" --out test-runs/oracle-linux-001 --require-gpu
```

`--case rect-fractional,text-black` 可以只运行相关样例。每次 `--out` 必须是项目 `test-runs/` 下**不存在**的新目录；已有目录一律拒绝，不能覆盖证据。

采集内容：每例 `observations`、尺寸、readback RGBA、PNG、SHA-256、`.gpu/.engine`、Node/platform/native 指纹。结果为 `ORACLE_CAPTURED` 或 `INCOMPLETE`；指定 `--require-gpu` 时默认组报告非 GPU 会失败。CPU setter/构造 false 是显式诊断例，不能代替默认组。

注意 `.engine` 是公共状态，不是每一次 native 绘制分支的断点证明。构造 false 有旧版状态陷阱；GUI/异步/释放顺序也尚未覆盖。

## 3 场景协议

[fixtures/scenarios.json](fixtures/scenarios.json) 是测试驱动协议，不进入未来产品核心。资源引用用 `{"$ref":"g"}`；特殊数字用 `{"$number":"NaN"}`、`Infinity/-Infinity/-0`，undefined 用 `{"$undefined":true}`。普通 null 保持 null。

支持 `set/get/call/construct/loadImage/setPixels/sameRef`；`call` 可记录返回值 `save` 或保存资源 `id`，`observeError` 记录原 API 是否抛错及类型/消息，不先假设错误行为。真实 Python runner 消费已绑定范围的同一序列。`sameRef`仅用于观察两个资源是否同一对象（Node === / Python is），必须提供left/right，不进入产品API。

覆盖几何/曲线/SVG Path2D、变换/clip/save/resize、渐变、阴影/滤镜、混色/透明像素、文本指标/颜色/组合字符/CJK/RTL/emoji、图像 crop/smoothing/pattern、DOMMatrix/Point、部分错误/无效值及两种 CPU 相关诊断。

`tests/assets/checker.svg` 是本项目自行创建的 MIT 测试资产。字体当前用系统 `sans-serif`，标为 `system-unpinned`：能采集不等于 CJK/emoji 已正确找到字形。未来必须登记真实字体文件/face/哈希，确认 glyph fallback；缺资源不得宣称该类别已通过。完整覆盖按 [API 契约](../docs/API_COMPATIBILITY.md) 的逐方法清单补齐。

## 4 精确比较两份标准记录

仅此步骤需要 [requirements-test.txt](../requirements-test.txt) 中的 Pillow，作为 PNG 解码工具，不是未来渲染实现。

```shell
python -m pip install -r requirements-test.txt
python scripts/compare_runs.py test-runs/oracle-win-001 test-runs/oracle-win-002 --out test-runs/compare-001/result.json
```

比较 fixture 指纹/样例集合/同 host 环境/后端声明/JSON 观测值/readback 像素和 PNG 解码像素。比较失败返回非零；输出文件已存在也拒绝覆盖。JSON 数值没有 epsilon；布尔值不是数字；包含 alpha=0 的 RGB，不缩放、不裁剪、不补偿颜色。

工具成功只写 `MATCHED_RECORDS`，**不会写 `PARITY_PASSED`**，避免 A 与 A 自比较冒充 Python 验收。它也不取代完整字体 provenance、native trace、PNG 元数据语义、PDF/SVG 和人工审图。下一会话在 G0/G1 固定这些资源，G2 验证 A↔重建 B，再为 PyO3 增加 candidate runner 和相关回归；候选输出应使用同 schema 和 `CANDIDATE_CAPTURED`。

所有运行结果在 `.gitignore` 的 `test-runs/` 中；提交可再生成的 case、工具和准确总结，不把本机 node_modules/系统字体/用户素材提交到库。

## 5 公共API盘点和首批核心检查

```shell
npm ci --prefix tools/api-ledger --no-audit --no-fund
node scripts/inventory-public-api.mjs --check
node --test tests/contracts/api-ledger.test.mjs
python scripts/validate_core.py
```

`docs/public-api-ledger.json`是17个runtime export的408个声明/JS重载与accessor条目，不代表全部语义已审计。生成器只解析源码，不加载native；需要明确重新盘点时才省略`--check`，并审查diff。`validate_core.py`检查首批滤镜代码只增加说明、未迁移文件保持原字节、Node转发唯一core。当前另检查addColorStop原f32范围判断提取后未改动。

当前bootstrap有50项断言，Node ledger有6项断言；它们不证明Python/GPU验收。原函数体检查覆盖滤镜整文件、Page/GPU完整文件的受控分离及234个选定方法体、24段Context操作及Path2D受控操作/数据分配片段，含stop排序、Broken内容clone、设备排序与surface origin的负例。

## 6 固定oracle和环境指纹

`tools/oracle/package-lock.json`锁定研发oracle依赖，可在需要的OS安装：

```shell
npm ci --prefix tools/oracle --no-audit --no-fund
python scripts/capture_environment.py --out test-runs/NEW_ENV/environment.json
```

采集器增加`--environment test-runs/NEW_ENV/environment.json`可逐文件验证字体/config内容，将manifest副本与SHA保存在输出目录；比较器检查资源指纹变化和附件完整性。不同OS必须分别采集，Windows路径的manifest不能给Linux使用。只记录元数据，不复制字体，也不声称已验证每个glyph的fallback。

官方oracle现在还检查`docs/upstream-lock.json`中的native SHA。新构建必须显式使用`--role node-rebuild`，输出为`CANDIDATE_CAPTURED`，不能把包版本号相同当官方发布物。

`tests/fixtures/contracts.json`有5个初始默认值/错误/GPU状态契约，需普通和`SKIA_CANVAS_STRICT=1`两个独立进程。`filters.json`有16个滤镜/采样回归，`paints.json`有20个渐变/共享资源/texture/像素格式场景，`paint-svg.json`有2个无固有尺寸SVG pattern场景。通过`--fixtures`交给同一采集器；结构检查覆盖fixtures目录全部JSON，生产核心不读取它们。

`exports.json`另有7例Page/缓存/同步异步raw、resize/reset、多页索引、density/matte/colorType、MSAA错误、SVG和CPU↔GPU显式切换契约。它们不代表完整G8异步/编码验收。

## 7 开发用Node重建与共享core

未改造源码基线需独立新目录，不能编辑reference：

```shell
python scripts/prepare_node_baseline.py --out .local/node-baseline-NEW
```

该命令核验49个来源文件后原样复制，拒绝覆盖现有目录。随后在目标OS于这个开发目录安装锁定JS依赖并构建。Linux示例：

```shell
npm ci --ignore-scripts --no-audit --no-fund
cargo build --locked --release --features vulkan,window,freetype
```

开发用共享core Node在仓库根目录构建：

```shell
npm ci --prefix crates/node --ignore-scripts --no-audit --no-fund
cargo build --locked --release -p skia-canvas --features vulkan,window,freetype
cargo tree --locked -p canvas-core --features vulkan,freetype --edges normal,build
```

将构建所得`libskia_canvas.so`复制到对应开发包的`lib/skia.node`，以显式绝对`--module`路径和`--role node-rebuild`采集。Windows使用`vulkan,window`及对应DLL；本次Windows源码重建尚未验证。原生文件和node_modules均被Git忽略。

Rust工具链固定1.90.0。本机会话在WSL将工具链放于`.local/rust`，需要在该进程设置`CARGO_HOME`、`RUSTUP_HOME`和PATH；此路径不是生产依赖。构建缓存目录可由`CARGO_TARGET_DIR`指定。本次使用`.local/node-baseline/target`以复用Skia构建。

core可单独检查headless feature图与编译（仍启用真实Vulkan，而非CPU替代）：

```shell
cargo check --locked --release -p canvas-core --features vulkan,freetype
```

匹配的rust-skia官方预编译缓存会优先使用；没有此feature组合时按原构建机制编译Skia。Linux当前重建使用系统Fontconfig，尚未复现上游发行容器static-fontconfig patch，必须在provenance中保留这项差异。core已有paint/image、Page/缓存/导出/GPU、Canvas/Context/State、字体和布局；独立Rust绘制示例已运行，初始Python所有权与绑定已实现，Path扩展和语言参数解析尚未完整迁移。


## 8 独立Rust核心验证

`text-core.json`增加13例字体/布局契约；`core-smoke.json`定义独立Rust程序与Node共用的矩形、黑字和彩字场景。真实Python采集通过独立runner执行，不与Rust probe状态混淆。

```shell
cargo build --locked --release -p canvas-core --features vulkan,freetype --example core_gpu
python scripts/capture_core_probe.py --executable target/release/examples/core_gpu --environment test-runs/NEW_ENV/environment.json --out test-runs/NEW_CORE
python scripts/compare_runs.py test-runs/NODE_CORE_SMOKE test-runs/NEW_CORE --out test-runs/NEW_COMPARE/result.json
```

采集脚本当前只支持Linux x86_64，在空PATH下运行真实Rust程序并检查ldd无libnode/Neon；不会用空图冒充未实现API。它验证单线程独立核心，不验证Python GC、异步导出或完整公共契约。


## 9 真实Python wheel检查

Linux CPython3.13环境中构建：

```shell
maturin build --release --locked --interpreter python3.13 --compatibility linux
```

默认平台依赖启用原Vulkan/FreeType；无需靠手工feature才能保留GPU。新venv安装指定wheel后，从仓库外目录用空PATH执行：

```shell
/abs/venv/bin/python -I /abs/repo/scripts/capture_python.py --fixtures /abs/repo/tests/fixtures/python-core.json --environment /abs/repo/test-runs/ENV/environment.json --wheel /abs/exact.whl --out /abs/repo/test-runs/NEW_PYTHON
/abs/venv/bin/python -I -m unittest discover -s /abs/repo/tests/python -v
/abs/venv/bin/python -I /abs/repo/scripts/trace_python_gpu.py --out /abs/repo/test-runs/NEW_TRACE
```

采集器检查实际已安装文件与wheel字节相同、环境字体内容、无Node/Neon动态依赖；Python库不会读取fixture或加载开发oracle。`core-smoke.json`和`python-core.json`共8例分别对官方A、共享core Node B使用同一比较器，JSON/RGBA/解码PNG无容差。另有6项独立生命周期子进程测试，缺GPU直接失败。

trace需要GDB与未剥离的本地wheel符号。记录真实读回/PNG的Vulkan surface和Skia submit调用栈，检查全新CPU对照；不是驱动入口或Windows硬件GPU验收。


## 10 G4 当前路径

`current-path.json`有14例当前路径/曲线、数值变换、clip/命中、描边及错误。它与G3两个fixture共24例由真实Python wheel采集，对A/B精确比较；Node另分普通/STRICT进程。`path-adapter.json`有4例Node-only Path2D返回家族回归，不代表Python已绑定Path2D。

生命周期断言现有8项；原生路径trace可选择新场景：

```shell
/abs/venv/bin/python -I /abs/repo/scripts/trace_python_gpu.py --scene current-path --out /abs/repo/test-runs/NEW_PATH_TRACE
```

继续要求仓库外目录与空PATH。范围/限制见[本批报告](../docs/G4_CURRENT_PATH_REPORT.md)，初始Python完整JS coercion和DOM重载仍未验收。


## 11 独立Path2D与roundRect

`path2d.json`有10例独立路径/SVG/重载/布尔/插值/特效；`path2d-edge-cases.json`有2例fill-type副作用及f32溢出/负零。既有`path-adapter.json`4例现在也由真实Python采集。`roundrect.json`4例覆盖两种默认值、半径扩展/截断/忽略/错误和宽高符号顺序。与旧24例共44个Python场景，分别对A/B精确比较。

生命周期测试共14项。Native trace增加`--scene path2d`，仍要求仓库外目录、空PATH和真实已安装wheel。44项bootstrap用于来源/工具，不能作为渲染通过。具体范围与证据见[本批报告](../docs/G4_PATH2D_REPORT.md)。


## 12 CanvasGradient 与样式引用

`gradients.json`有12例线性/径向/锥形、重复stop/epsilon、共享修改、退化坐标、f32边界与错误顺序、直接构造、引用缓存/restore/无效CSS、跨Canvas及文字/描边。加上原44例，真实wheel共56个Python场景对官方A/同核B精确比较；新增Node场景也单独运行普通/STRICT模式。

生命周期测试共20项；原生trace增加`--scene gradients`。仍要求仓库外工作目录、空PATH、相同已安装wheel及真实默认Vulkan，不以CPU控制替代验收。46项bootstrap/6项ledger仅检查工具与来源。范围和未完成的完整coercion/跨平台验收见[渐变报告](../docs/G4_GRADIENT_REPORT.md)。


## 13 DOM 数值对象与矩阵重载

`dom-values.json`新增14例DOMPoint/DOMRect/DOMMatrix、6/16标量/序列/对象、透视、别名/flag、typed array、getTransform/状态栈/resize和Path重载。`dom-edges.json`另有4例null错误、native有限数值过滤、f32溢出和f64表达式顺序。合计74个真实Python场景分别对A/B精确比较，23项生命周期断言；两套新fixture的Node普通/STRICT分别采集。

测试资源表增加DOMPoint/DOMRect/DOMMatrix类，以普通call观察静态方法；它们不是生产指令协议。Python typed array使用标准库array('f')/array('d')。原生trace增加`--scene dom-values`，同样要求真实已安装wheel、仓库外工作目录和空PATH。

本批未改动Rust绘制core或Node源码，最终B复用上批验收的同一二进制，并核验Node/core源码指纹，没有伪造新构建日志。范围与未绑定CSS parser/矩阵操作见[DOM报告](../docs/G4_DOM_VALUES_REPORT.md)。


## 14 DOMMatrix 运算与 CSS parser

matrix-ops.json有18例运算/默认值/共享/flag/逆变换返回值，css-transform.json有14例CSS单位/语法/组合/错误，matrix-edges.json有4例typed/plain数组、undefined默认值、字符串阈值与原重载。共110个真实Python场景分别对A/B精确比较，25项生命周期断言；三组新Node fixture也分普通/STRICT。

Python undefined单例用于原JS undefined返回/缺省标记，与None/null分开。脚本check_installed_dom_math.py从实际已安装wheel对独立Node原始位串检查716×4次纯标量结果；它要求空PATH和仓库外工作目录。该检查与fixture/像素/native trace分开记录。validate_matrix_math.py检查原V8源码指纹，不是运行Node。原生trace增加`--scene matrix-ops`。

本批保留首轮toString数组类型差异和修复后的独立证据目录；不改变oracle或添加容差。范围和剩余coercion/宿主/平台验收见[矩阵报告](../docs/G4_MATRIX_REPORT.md)。


## 15 createProjection 与点坐标边界

projection.json新增16例原投影求解、basis/尺寸展开、状态/resize、Path/跨Canvas与真实绘制。projection-edges.json新增8例missing/null/undefined、奇数错误优先级、退化、非有限过滤、Rust字符串及嵌套数组。合计134个真实Python场景分别对A/B精确比较，28项生命周期断言；新Node场景分普通/STRICT。50项bootstrap/6项ledger单独检查来源与工具。

scripts/projection_extraction.py保留原矩形展开与Skia求解，Node/Python共用数字字符串解析；不是自制投影模型。原生trace增加`--scene projection`，仍要求仓库外目录、空PATH和实际安装wheel。原始失败fixture、修正记录协议/字体标签后的独立oracle与最终结果均保留。具体范围见[投影报告](../docs/G4_PROJECTION_REPORT.md)。


## 16 FontLibrary 注册、查询与 reset

font-library.json 14例、font-library-edges.json 8例覆盖系统/注册家族、别名/样式替换、变量字体元数据、原数组过滤空槽、重置快照、参数/文件错误与部分提交。共156个真实Python场景分别对A/B精确比较，32项生命周期断言。新Node场景分普通/STRICT进程；52项bootstrap/6项ledger只作为工具与来源检查。

资源表增加fontLibrary，字典字段与嵌套undefined由采集器如实序列化。系统字体只记录路径/指纹，不复制入wheel。原生trace增加`--scene font-library`；其中绘制使用默认字体，ctx.font/别名选择尚未绑定。仍要求仓库外目录、空PATH和同一已安装wheel。原版透明图层重复读回变化的独立探针与失败日志保留，未改core算法。范围见[字体库报告](../docs/G5_FONT_LIBRARY_REPORT.md)。


## 17 CSS font 与字体选择

font-css.json 22例、font-css-edges.json 10例覆盖原CSS单位/命名尺寸、行高、small-caps/weight/stretch、引号/括号/转义、缓存、非法值保留、注册alias/替换/reset、变量weight/width、save/restore/resize/outline/maxWidth与部分复杂脚本。共188个真实Python场景分别对A/B精确比较，36项生命周期；新Node组分普通/STRICT。54项bootstrap/6项ledger用于来源与工具，不能代替实际字体/像素验收。

check_installed_font_css.py用实际已安装wheel对原JS parser的300组描述符精确比较，独立于RGBA与标量Math检查；要求仓库外工作目录和空PATH。原生trace增加`--scene font-css`，实际注册alias并用ctx.font绘制。系统字体仅记录路径/指纹，分词原始依赖/通知在references/css与crates/python/vendor/css。范围与未完成项见[CSS字体报告](../docs/G5_FONT_CSS_REPORT.md)。


## 18 文本状态属性

text-state.json 27例、text-state-edges.json 12例覆盖9属性、默认值、align/baseline/direction、字距、wrap、hinting、stretch、variant/features、状态栈/resize/跨Canvas、原错误与普通coercion。共227个真实Python场景分别对A/B精确比较，40项生命周期；新Node组分普通/STRICT。56项bootstrap/6项ledger用于工具/来源。

check_installed_text_css.py以已安装wheel精确比较213组原JS parser值/错误，独立于原font parser300组、RGBA和标量Math。trace增加`--scene text-state`，使用实际文本状态和alias导出；仍要求仓库外cwd、空PATH和同一已安装wheel。旧重复观察标签与尾换行失败记录保留，修正后不使用容差。范围见[文本状态报告](../docs/G5_TEXT_STATE_REPORT.md)。


## 19 textDecoration

text-decoration.json 23例、text-decoration-edges.json 9例覆盖3类线、5种style、颜色/粗细/单位/字段顺序、原忽略/错误、字体变化、wrap/bidi/outline/stroke、状态栈/resize/跨Canvas与注册reset。共259个真实Python场景对A/B精确比较，44项生命周期；新Node组分普通/STRICT。58项bootstrap/6项ledger只用于工具/来源。

check_installed_text_css.py复用于独立227组装饰描述符，与既有font300/text213组分别留存。trace增加`--scene decoration`，使用真实颜色/粗细装饰和已安装wheel；继续要求仓库外cwd与空PATH。原currentColor忽略、none早退、from-font跳过字段及relative-unit错误未修复。范围见[文字装饰报告](../docs/G5_DECORATION_REPORT.md)。

## 21 TextMetrics 与所选字形诊断

最新范围见 [测量与字形报告](../docs/G5_METRICS_REPORT.md)。新增 text-metrics 24、text-metrics-edges 10、font-fallback 8 个场景；共301个真实Python场景对官方A和同核B，48项生命周期。通用 capture/compare 命令不变，三份fixture都单独采集默认与原版STRICT。

`scripts/audit_glyph_sources.py --role node --module <explicit crates/node> --fixtures <font-fallback.json> --environment <pinned environment.json> --out <fresh-dir>` 观察开发B；`--role python` 使用干净已安装wheel、仓库外cwd和空PATH。Node显式使用 /usr/local/bin/node，仅为开发工具；Python角色没有Node运行依赖。最后以 `--compare <B-dir> --fixtures <Python-dir> --oracle <official-A-dir> --out <fresh-dir>` 精确比较glyph/font记录和官方A公共metrics。

诊断只存glyph/字体元数据与四表SHA，不保存字体或表字节。音乐符号1个glyph0、emoji场景5个glyph0保持未覆盖；不把相同缺字图当完整字体通过。utf8Starts因当前上游visitor边界问题完全不读取，cluster来源仍待审计。`trace_python_gpu.py --scene metrics` 单独记录实际绘制的原生Vulkan路径。

## 22 G6 图像与像素大目标

范围见 [G6报告](../docs/G6_IMAGING_REPORT.md)。images30、pixels46、image-edges34、patterns11、textures6、image-formats11共138新场景；累计439个不同Python场景。按用户最新要求只对固定官方Node A作日常差分，不再每批重编开发Node B。新增6份fixture另以 SKIA_CANVAS_STRICT=1 分进程采集/比较；普通和STRICT不重复计为不同功能覆盖。

fixture 的 $bytes/$clamped/$assetBytes 只作跨语言输入协议，资产必须位于 tests/assets。合成PNG/raw/BMP/GIF/SVG与官方编码出的JPEG/WebP均按本项目MIT许可，清单另存。setPixels调用实际可变ImageData.data，drawCanvas与drawImage分别验证原vector和bitmap分支。

`scripts/check_imagery_loading.py --module <fixed official A> --out <fresh-dir>` 在仓库外cwd、空PATH的已安装wheel解释器运行，用自建loopback server比较18组加载/事件/异常与字节记录；Node仅为独立oracle进程。`trace_python_gpu.py --scene imaging` 用同一wheel验证实际Vulkan路径。64项生命周期和61项bootstrap检查分开记录。

## 23 G7 效果与混色大目标

范围见 [G7报告](../docs/G7_EFFECTS_REPORT.md)。effect-filters54、effect-shadows24、effect-composite42、effect-paths13、effect-edges98，共231新场景；累计670普通场景对官方A，G6/G7另369场景验STRICT，不重复计数。无需重编开发Node B。64项bootstrap与76项生命周期分别记录。

`tests/oracle/capture-effect-css.mjs <official-module> <inputs.json> <node.json>` 独立采集原css.filter；`scripts/check_installed_effect_css.py --inputs ... --node ... --out <fresh-dir>` 用仓库外、空PATH、实际安装wheel比较471组f64描述符/异常。此parser检查与JSON/RGBA/解码PNG差分独立。`trace_python_gpu.py --scene effects` 对同一wheel记录真实Vulkan绘制路径。

保留原重复kind文本/最后值/首次位置顺序；百分比先f64再除100，hue regex不含负号；STRICT的U+FE0F不能归一化。测试不调整RGB或alpha容差。


G8 多页与完整导出普通输入已迁移；范围、并发 Vulkan 初始化锁的来源和限制见 [G8 报告](../docs/G8_EXPORT_REPORT.md)。下一大目标为 G9 App/Window 与剩余公开项。G0 host/Sharp/极端输入及跨平台/字体/发布门禁继续保留；最终可用 wheel 字节与检查结果以 G8 最终记录为准。


G9 App/Window 与普通事件/会话已迁移；范围、真实 GUI GPU/像素证据和原版危险输入见 [G9 报告](../docs/G9_GUI_REPORT.md)。全部 408 条清单的归属和剩余项见 alpha-api-status.json（docs 下）。完整兼容、Node Sharp 互操作、G0/G4/G5 与平台/发布门禁仍保留。


2026-10-28 构造与参数大目标：Canvas options/尺寸重置、独立 CanvasRenderingContext2D(Canvas)、当前路径/Path2D 数值参数、rect/基础变换、描边数字、dash、命中与 gradient 的普通 primitive/array 参数计数、转换、异常与 STRICT 读取已迁移。新增 1429 个不同场景，连同旧场景共 2114 普通/1813 STRICT；11 种 STRICT 环境值另验；117 项 wheel 生命周期、70 项 bootstrap。实际最终 wheel 与检查以 [构造与参数报告](../docs/G0_G4_ARGUMENT_REPORT.md) 和 `test-runs/20261028-contracts-final-1` 为准。文本绘制等其余参数、完整 host/subclass/proxy/valueOf/EventEmitter/Sharp、G5 字形/emoji 与平台/发布仍待完成。

新增 contract-canvas / contract-geometry / contract-path / contract-gradients / contract-hit / contract-env fixture；用相同 capture-node.mjs/capture_python.py 和 compare_runs.py 做 JSON、raw RGBA、解码 PNG 精确比较。`construct` 支持 CanvasRenderingContext2D；测试协议的 `ifRef` 仅在先前构造已抛错时跳过依赖该结果的后续观察，构造错误自身仍保存并比较。原生 trace 增加 `--scene contracts`，通过实际安装 wheel 的独立 Context 和数值参数产生原 GPU surface/submit。`tests/python/test_contracts.py` 覆盖独立 Context 页隔离、尺寸、父对象回收、跨线程释放/owner 退出等。
