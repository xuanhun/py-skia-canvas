# G5 第四批：textDecoration

日期：2026-10-28。固定 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 为 0.1.0a11，未发布。

## 实现

已绑定 `CanvasRenderingContext2D.textDecoration` getter/setter，默认 none。原 css.js:parseTextDecoration 按相同顺序处理 style、line、color、thickness、inherit 与保存的 str，保留 trim、只替换第一段空白、按空格拆分、子串匹配优先级及最后 token 覆盖。非字符串转空描述，按原规则清除装饰。getter 返回原核心保存的 CSS 字符串，不额外 canonicalize。

装饰参数选择逻辑从原 typography.rs:decoration_arg 机械迁入唯一 core 的 `typography/decoration.rs`，通过 typed DecorationArgs reader 读取字符串与可选 Spacing。Node reader 保留原字段访问/异常，Python reader 读取已拥有的 JSON 值。读取顺序、默认装饰早退、color.is_none 校验、from-font 跳过 thickness、原 Through mode 均保留。Python 不重复颜色、粗细、字体指标或装饰绘制算法。

已覆盖 underline/overline/line-through、solid/double/dotted/dashed/wavy、原 CSS 颜色、绝对尺寸、from-font/auto、字体变化、wrap/字距、baseline/bidi、fill/stroke/outline、渐变/变换/clip/maxWidth、状态栈/resize/跨 Canvas 与注册字体 reset。粗细 raw/px f64 先在原 Native 边界转换为 f32，再由原 Spacing 与 DecorationStyle::for_layout 相对原字体 underline thickness 计算；其公式、fallback 和 SkParagraph 绘制未重写。

保留原行为：活动线缺少有效显式颜色（包括 currentColor）时忽略赋值，保留先前装饰；none/未知 line 先恢复默认装饰，可绕过无效 thickness。活动线的 em/rem/%/ex/ch 会在原 px 字段校验时报错；from-font 则按原顺序跳过该字段读取。NaN size、无效颜色、substring token 和不规范空白的行为均按原版，未修正兼容基线。

逐项参数、单位、返回、错误和来源见 [装饰 API 状态](decoration-api-status.json)。G5 完整 TextMetrics/布局与 glyph/fallback/emoji 验收仍未完成。

## 来源与所有权

231 个完整原函数体、24 个已有 Context 片段、Path/FontSpec 等受控片段继续检查。完整体从 232 减至 231 是 decoration_arg 拆为语言读取与共享原逻辑；来源图新增 decorationFragment，文本状态共享片段从 18 增至 20。原 DecorationStyle::for_layout、字体、Typesetter、GPU 和绘制函数体保持不变。58 项 bootstrap 含 currentColor guard 和 Through mode 的篡改负例；327 个第三方 Cargo 条目不变，无新增运行依赖。

参数解析/字段读取在 Context 借用前完成；原 Node 的条件借用与 pending 异常行为不改动，Python 传播对应的原字段 TypeError。Context、字体和 GPU 留在 owner TLS，Python 仅保存 owned 字符串/数值描述，返回字符串为独立快照。新增 4 项真实 wheel 生命周期断言：Canvas GC 后状态/测量、外线程读写/错误输入拒绝、错误保留与 restore/resize/reset、带装饰的 owner 退出。共 44 项，没有 unsafe Send/Sync 或 GPU context 线程转移。

## 实际证据

`test-runs/20261028-decoration-before` 保存变更前 56 项 bootstrap、源码/lock/core 检查与 A↔迁移前 B。text-decoration.json 23 例、text-decoration-edges.json 9 例的原发布物、迁移前 Node 和原版 STRICT 独立采集；相关指标/JSON、RGBA、解码 PNG 精确比较。

候选 wheel 首轮 32 例及 227 组独立装饰 parser 描述符与原版精确一致，44 项生命周期通过。最终入口 `test-runs/20261028-decoration-final/run.json`：同一 alpha11 wheel 共 259 个 Python 场景分别对官方 A 和最终同核 B 的 JSON、RGBA、解码 PNG 精确一致，无容差，alpha=0 的 RGB 仍计数。Node 53 组、Python 48 组比较。44 项生命周期、58 项 bootstrap、6 项 ledger、font parser300/text parser213/decoration parser227 组与 716×4 标量位串分别存证。

最终 Node 构建 `20261028-decoration-node-final-build-linux`，wheel 构建 `20261028-decoration-wheel-final-build-linux`。Rust 重建，Skia C++ 复用已验证缓存。仓库外干净 CPython 3.13.18 venv、空 PATH、无 Node，安装并运行实际指定 wheel；生产图无 Neon/N-API，wheel 清单无 Node/JS 运行时或字体文件。系统字体只记录路径/指纹。

`20261028-decoration-native-trace-linux` 以同一 wheel 注册 mono alias，绘制带颜色/粗细的波浪下划线、换行和双上划线描边，restore/reset 后导出，观察原 Vulkan surface 与 Skia submit；fresh CPU 控制另存。仍是 Linux Mesa llvmpipe 软件 Vulkan，不是 Windows 硬件 GPU、Metal、driver 入口或 native surface 尺寸验收。

## 后续

继续完整 TextMetrics/布局、glyph/fallback 来源和 emoji 审计，随后推进 G6 Image/ImageData。完整 JS host/proxy/custom coercion、Python 子类/循环对象、极端/非有限数值契约及其余 API 仍属 G0；图像、效果、多页/异步、App/Window、Windows/Metal、static-fontconfig/manylinux、许可与发布继续保留。未 commit、push 或上传。
