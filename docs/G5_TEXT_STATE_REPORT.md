# G5 第三批：文本对齐、字距与字体状态

日期：2026-10-28。固定 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 为 0.1.0a10，未发布。

## 实现范围

已绑定 9 个属性的 getter/setter：textAlign、textBaseline、direction、letterSpacing、wordSpacing、fontStretch、fontVariant、fontHinting、textWrap。状态仍由唯一 canvas-core 的原 Context/State、TextStyle、ParagraphStyle 和 Typesetter 管理；Python 没有第二套文字排版、字距或 baseline 算法。

默认值分别为 start、alphabetic、ltr、0px、0px、normal、normal、false、false。alignment/baseline/direction 的大小写转换与未知名称忽略在原 Rust 规则中处理，非字符串仍按原错误报错。hinting/wrap 采用原 JS `!!value`：空数组/对象为 true，NaN/undefined/null/零/空字符串为 false。

CSS spacing、stretch、variant 按固定 css.js 的 parseFlexibleSize/parseStretch/parseVariant 及原 featureMap/alternatesMap 迁移，复用上一批锁定的原 tokenizer。字符串/feature tag、weight/flag 无坐标单位；spacing 的 raw/px f64 在原 Native 边界转换到 f32，原 Spacing::parse/in_px/to_string 与当前 font size 应用顺序保持不变，getter 使用原 Rust 格式化。独立 fontStretch/fontVariant 改变各自 state，不重新拼写 ctx.font canonical 字符串；后续 ctx.font 赋值仍按原规则更新相关状态。

保留已知原行为：em/rem/%/ex/ch spacing 在 Native px 字段校验时出错；fontVariant="normal" 的 JS 结果缺少 variant 字段，独立 setter 报错；未知 variant、参数化 alternate 的 clamping/NaN、重复 feature 顺序和普通 cache/prototype 键的所覆盖错误均依原版。没有修正这些原行为或引入新的 CSS 标准校验。

textWrap 的真正换行、双向文本、字距、baseline、font hinting、features、stretch、绘制/测量/outline、maxWidth、save/restore 和 resize 均走原核心。textDecoration 留待下一批。逐项参数、默认值、返回、异常、线程和来源见 [文本状态 API 状态](text-state-api-status.json)。

## 来源与所有权

`scripts/text_state_extraction.py` 保留原 getter/setter 的语句，仅分离 Neon 参数与 JS 返回分配，生成 18 个共享操作到 `context/text_state.rs`。开发 Node 和生产 Python 均调用它们。fontStretch 在 Node 中仍只在解析到字符串后借用 Context，未改变原条件借用顺序。

232 个完整原函数体、24 个已有 Context 片段、Path/FontSpec 等原受控片段保持检查；另增 18 个 textStateFragments。原 CSS features/alternates 字面表由原文件完整提取并验证，未手写删减。56 项 bootstrap 包含当前 em size 和完整 features 表的篡改负例；327 个第三方 Cargo 条目不变，没有新增运行依赖。

所有 native 状态、字体、Paragraph 与 GPU 对象仍在 owner TLS。Python 只解析自有值；进入 native 借用前检查字段/解码 JSON，不在借用期间执行 Python 回调。属性返回 owned 字符串/bool。新增 4 项真实 wheel 生命周期检查：Canvas GC 后的状态/测量、9 属性外线程读写拒绝、restore/resize/原错误保留、带文本状态的 owner 退出。共 40 项，没有 unsafe Send/Sync、GPU context 跨线程或 Python 线程池。

## 实际证据

`test-runs/20261028-textstate-before` 保存变更前 54 项 bootstrap、源码/lock/core 检查。text-state.json 27 例、text-state-edges.json 12 例，分别采集原版 A、迁移前 B 与原版 STRICT。首版 fixture 有重复观察标签，bootstrap 拒绝；旧 fixture/采集保留，只修改保存结果的标签，API 输入与绘制顺序不变。有效原版/迁移前基线为各 `20261028-text-state-*-linux-2` 与 `text-state-edges` 对应目录；迁移前 B 的 native SHA 核对上一批已验过的相同字节。

首轮候选正常 27 例精确一致；边界组出现 fontStretch 尾换行的 JSON 差异，即使 RGBA/PNG 像素相同仍判失败。原 JS 正则要求完整值；修正 Python 的末尾处理后，39 例和独立 213 组文本 parser/错误记录精确一致，旧失败证据保留，未改 oracle 或容差。修正候选的 40 项生命周期通过。

最终入口 `test-runs/20261028-textstate-final/run.json`。同一 alpha10 wheel 共 227 个 Python 场景分别对官方 A 和最终同核 B 的 JSON、RGBA、解码 PNG 精确一致，无容差，alpha=0 的 RGB 仍计数。Node 49 组、Python 44 组比较。40 项生命周期、56 项 bootstrap、6 项 ledger、原 300 组 font parser、213 组 text parser、716×4 标量位串检查分别保存。

最终 Node 构建 `20261028-textstate-node-final-build-linux`，wheel 构建 `20261028-textstate-wheel-final-build-linux`。Rust 重新构建，Skia C++ 复用已验证缓存。仓库外干净 CPython 3.13.18 venv、空 PATH、无 Node，安装实际指定 wheel；生产依赖不含 Neon/N-API，wheel 清单无 Node 模块/JS 运行时或字体文件。系统字体仍只记录路径/指纹。

`20261028-textstate-native-trace-linux` 使用同一 wheel 的 alias、center/middle/rtl、spacing、stretch、variant、hinting、wrap，绘制文字/描边，restore/reset 后导出，观察原 Vulkan surface 与 Skia submit；fresh CPU 控制单独验证。仍是 Linux Mesa llvmpipe 软件 Vulkan，不是 Windows 硬件 GPU、Metal、driver 入口或 native surface 尺寸验收。

## 后续

继续 textDecoration、完整 TextMetrics/布局/装饰、fallback/glyph 来源与 emoji 验收。完整 host/proxy/自定义 prototype/coercion、任意 Python 子类/循环对象、极端数字字符串与全部非有限/溢出输入仍属 G0；图像、效果、多页/异步、App/Window、Windows/Metal、static-fontconfig/manylinux、完整许可和发布仍未完成。未 commit、push 或上传。
