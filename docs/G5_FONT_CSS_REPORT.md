# G5 第二批：CSS font 与实际字体选择

日期：2026-10-28。固定 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 为 0.1.0a9，未发布。

## 实现

已绑定 `CanvasRenderingContext2D.font` getter/setter。getter 返回原核心保存的 canonical 字符串，setter 按固定 `lib/classes/css.js` 的 parseFont/parseSize/parseWeight 处理，再交给原 FontSpec、FontLibrary::update_style 与 Context2D::set_font。字体匹配、变量字体实例、Paragraph/shaping、布局、缓存、绘制和 GPU 算法均未重写。

CSS 解析是语言边界的原顺序迁移，保留原属性识别优先级、重复属性覆盖、引号/括号与转义分词、family 栈、尺寸前缀匹配、绝对/相对单位、命名尺寸、行高、small-caps 的 smcp/onum features，以及 cache 的普通 primitive/array 属性键行为。无效输入按原规则保留当前字体，不额外增加 CSS 标准校验。样式与尺寸为原 f64 语言值；原 Native 边界才转换到 f32，lineHeight 在 f32 转换后除以 size。单位为原 CSS px/canvas units；weight、style、stretch 与 features 无坐标单位。

原 Rust font_arg 的字段读取与 typed packing 分开：新增唯一 `typography::font_spec` 保留原 Weight/Slant/Width 转换、行高比例和空首家族规则，Node/Python 共用。Node 描述符读取、null 忽略与字段顺序保持原规则；Python private JSON 只传自有字段，在 Context 借用前完成解码，无 Python 回调处于借用期间。

`ctx.font` 选中的字体现在实际用于 fillText、strokeText、measureText 和 outlineText。注册 alias、regular/bold/italic、同 alias 替换与 reset、save/restore、Canvas resize、跨 Canvas、maxWidth、变换/渐变、Ubuntu 变量 weight/width、阿拉伯文/希伯来文/组合字符及 CJK 均有原版差分场景。这是固定资源/场景覆盖；未据此宣称完整 glyph fallback、全部复杂文本或 emoji 验收。

接口参数、返回、异常与来源见 [font API 状态](font-css-api-status.json)。fontStretch/fontVariant 独立 setter、baseline/align/direction、spacing、wrap、decoration 等完整文本状态在后续批次。

## 来源、许可与线程

分词算法来源为原版实际依赖 string-split-by 1.0.0 与 parenthesis 3.1.8，原 index.js/package.json/许可证据、npm resolved/integrity 及逐文件 SHA 追加保存在 `references/css`，没有修改 `references/upstream`。Python 移植保留其默认 bracket 顺序、flat 引用和 escape joining；不是重新设计的通用 CSS parser。衍生 MIT 通知包含在 wheel，无 npm/Node 运行依赖。

`scripts/font_extraction.py` 列出允许的字段/结果边界替换，来源映射保留 232 个完整原函数体和既有 24 个 Context 片段，新增一个 FontSpec 片段。完整体由 233 减至 232 是因为 font_arg 被拆成原读取与共享 typed packing；原 set_font/update_style/shaping 方法仍逐体检查。54 项 bootstrap 含行高比例和空家族规则的篡改负例；327 个第三方 Cargo 条目不变。

Canvas/Context、FontMgr、Typeface、Paragraph 和 GPU 仍在 owner TLS。CSS cache 只保存 Python 字符串/数字描述符，不持有 native 字体或 context；返回 font 字符串为独立值。新增 4 项真实 wheel 生命周期断言：选中字体与 Canvas GC、外线程 getter/有效与无效 setter 拒绝、save/restore/resize/非法值保留、带 alias 的 owner 线程退出。合计 36 项，没有 unsafe Send/Sync 或 GPU 线程池转移。

## 实际验证

`test-runs/20261028-fontcss-before` 保存变更前 52 项 bootstrap、core/资料检查、源码/lock 和 A↔变更前 B。font-css.json 22 例、font-css-edges.json 10 例，原发布物 A、变更前 B 及 A 的 STRICT 均独立采集，普通/STRICT 不合并冒充额外场景。核心改变后重新构建 B。

首个候选 32 例的 JSON、RGBA、解码 PNG 对官方 A 精确一致；另有 300 组原 JS parser 描述符对已安装 wheel 精确一致。生命周期首轮错误地在 Canvas GC 后调用要求 parent 的公开像素读取，失败原样保留；修正测试以检查已有契约允许的字体状态、测量、绘制，以及 GC 前的 PNG，36 项通过。没有修改弱引用或读回策略。

最终入口 `test-runs/20261028-fontcss-final/run.json`。同一 alpha9 wheel 共 188 个 Python 场景分别对固定官方 A 与最终同核 B 的 JSON、RGBA 和解码 PNG 精确一致，alpha=0 的 RGB 仍计入，无容差。Node 45 组、Python 40 组比较；36 项生命周期、54 项 bootstrap、6 项 ledger、300 组 parser 与 716×4 标量位串检查分别存证。

最终 Node 构建 `20261028-fontcss-node-final-build-linux`，wheel 构建 `20261028-fontcss-wheel-final-build-linux-2`。Rust 重新构建，Skia C++ 继续复用已验证缓存。仓库外干净 CPython 3.13.18 venv、空 PATH、无 Node，安装实际指定 wheel。生产 Cargo 图不含 Neon/N-API；wheel 清单检查无 Node 模块或 ttf/otf/woff 字体文件。测试只记录原系统字体路径与指纹，不分发字体。

`20261028-fontcss-native-trace-linux` 在同一 wheel 注册 mono alias，设置 small-caps/尺寸/行高，绘制渐变文字与描边，restore/reset 后导出，观察原 Vulkan surface 和 Skia submit。fresh CPU 控制独立记录；不是用 CPU 替代默认 GPU。这仍是 Linux Mesa llvmpipe 软件 Vulkan，不是 Windows 硬件 GPU、Metal、driver vkQueueSubmit 入口或 native surface 尺寸验收。

## 后续

继续 G5 其余文本状态、完整 TextMetrics/排版/装饰与字体 fallback 来源审计。CSS cache 的 prototype/host/proxy/自定义 coercion、极端 Number 最短字符串、Python 子类/循环对象不属于本批完整契约；其他 G0/G4 参数、图像、效果、多页/异步、App/Window、Windows/Metal wheel、static-fontconfig/manylinux、许可审核和发布仍保留。未 commit、push 或上传。
