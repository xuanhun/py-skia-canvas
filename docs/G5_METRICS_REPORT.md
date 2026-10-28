# G5 第五批：TextMetrics 与所选字形来源

日期：2026-10-28。兼容基线 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 0.1.0a12，未发布。

## 实现与边界

`measureText` 继续调用唯一 core 的原 Typesetter::new/layout/metrics；字体、shaping、换行、混排、baseline、run bounds 与绘制算法均未改写。本批补齐普通输入的 JS String 转换及可选 maxWidth：缺省为 undefined，null/布尔/数字/字符串/数组/普通对象按原包装处理；有限 f64 经原边界转 f32。宽度字符串复用已有原 Rust number parser，不换成 Python float 或 JS Number。额外参数忽略。fillText/strokeText/outlineText 的完整 coercion 不在本批完成范围。

TextMetrics 保留原浅拷贝构造：无参数/null 得到合法空值对象；mapping、数组、字符串的可枚举字段复制到顶层，字符串索引按 UTF-16 code unit。13 个标准返回字段及 lines/runs 数据由原 metrics 生成；初始顶层字段只读、不可删除，错误类别/消息与原版一致。后加字段可写可删，子列表/对象继续可修改并共享引用，不把整个结果递归冻结。Python 子对象为普通 list/dict，使用原键名；这保留浅复制的引用身份。值独立于 Context/Canvas，可在 owner 退出后和其他线程读取。

普通 measureText 转换、构造/字段规则和缺省已差分；host/proxy/valueOf、自定义原型、循环对象、保留私有名冲突、子类及极端浮点字符串仍属 G0。没有以空值对象替代尚未实现的原生测量。

新增私有开发诊断通过原 paragraph.extended_visit 观察所选 glyph ID、positions/bounds、family/PostScript/style/variation 和 head/name/cmap/OS/2 表身份。Node 开发 adapter 与 Python 都调用同一个 core observer，借用对象留在 owner 线程，仅返回 owned 值；没有更改字体匹配或绘制策略。表字节仅在审计进程内存中短暂传递并计算 SHA，证据不保存字体/表内容。四表 SHA/长度精确对应固定字体文件及 face index，文件本身另有完整 SHA；不是字体授权证明。

首轮观察曾读取 utf8Starts，精确比较暴露尾值不稳定。当前 Skia ParagraphImpl.cpp:extendedVisit 的 fClusterStart 分支只分配 context.size 项，而 skia-safe 0.88 的 utf8_starts() 形成 count+1 slice；最终 observer 完全不读取该字段，既不补造 cluster，也不修改 Skia。安全 cluster 源审计仍待完成；公共 TextMetrics 原 UTF-16 line/run 范围单独比较。首轮失败证据原样保留。

## 来源与所有权

231 个完整原函数体、24 个 Context 操作片段、20 个文本状态片段、既有 Path/FontSpec/decoration 受控逻辑继续校验。第三方 Cargo 327 条不变，无新依赖。新 observer 是追加的诊断模块，原 Typesetter/FontLibrary/GPU 函数体不变。Node 只加私有 native 诊断入口，公共 runtime exports 仍为 17，408 项原 ledger 不据此全部晋级。

4 项新增真实 wheel 生命周期检查覆盖 owner 退出后的测量、跨线程纯值/Context 拒绝、浅复制/错误保留/resize、空文本和私有 observer 的 owner 拒绝及 GC。共 48 项；没有 unsafe Send/Sync 或 GPU 线程转移。逐项参数、单位、返回、异常、所有权和来源见 [API 状态](metrics-api-status.json)。

## 证据

`20261028-metrics-before` 保存修改前 58 项 bootstrap、源码/lock/check。text-metrics 24 例、text-metrics-edges 10 例、font-fallback 8 例分别保存官方 A、修改前 B 和原版 STRICT 采集；A↔修改前 B 指标/JSON、RGBA 与解码 PNG 精确一致。首个 Node 构建的 FourByteTag 类型转换错误及首轮 cluster 失败不覆盖。

最终入口 `test-runs/20261028-metrics-final/run.json`：同一最终 alpha12 wheel 共 301 个 Python 场景分别对官方 A 和最终同核 B 精确比较；JSON 数值、RGBA 与解码 PNG 无容差，alpha=0 的 RGB 仍计数。Node 59 组、Python 54 组，共 113 组比较。58 项 bootstrap、6 项 ledger、48 项生命周期、font/text/decoration parser 各 300/213/227 组及 716×4 标量位串另行验证。

最终 Node/wheel 独立构建为 `20261028-metrics-node-final-build-linux` / `20261028-metrics-wheel-final-build-linux`。Rust 重建，Skia C++ 复用原已验证缓存；干净 CPython 3.13.18、仓库外 cwd、空 PATH、无 Node 安装同一 wheel。生产依赖无 Neon/N-API，wheel 不携带 Node、字体或其他工作区依赖。

`20261028-metrics-glyph-node-linux` / `20261028-metrics-glyph-python-linux` / `20261028-metrics-glyph-comparison-linux` 精确比较 8 个测量布局的 glyph/font 记录，并核对官方 A 的公共 metrics。所选 run 的字体四表全部唯一映射固定文件，覆盖拉丁、CJK、Arabic/Hebrew、缺失 family fallback、注册 mono alias、变量字体；music-astral 仍有 1 个 glyph0，emoji 场景仍有 5 个 glyph0。这两个场景是明确缺字，不能因与 A 同样输出方框就称完整通过。当前环境没有完整 color emoji 资源。

诊断来自 B/Python 的原测量布局，不是官方 A 私有 Typeface 的直接观察，也不是每个 GPU draw run 的字体来源证明。实际绘制仍另经 A/B/Python 像素比较。cluster 来源、完整 emoji/平台字形和许可审计未完成。

`20261028-metrics-native-trace-linux` 用同一 wheel 测量后绘制 CJK/RTL 多行文字并导出，记录原 Vulkan surface 和 Skia submit；fresh CPU 控制另存。仍是 Mesa llvmpipe 软件 Vulkan，不是硬件 GPU、Windows/Metal、driver vkQueueSubmit 入口或 native surface 尺寸验收。实际 PNG 的视觉审阅单独保存。

## 后续

继续 G0 文本绘制调用的 coercion 与 G5 安全 cluster/实际绘制字形来源、emoji 资源和平台审计；G6 Image/ImageData 尚未绑定完整公共契约。异步、多页、其余效果、App/Window、Windows/Metal、static-fontconfig/manylinux、完整许可和发布继续保留。没有 commit、push 或上传。
