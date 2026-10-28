# G7 大目标：滤镜、阴影、混色与线型效果

日期：2026-10-28。固定官方 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 0.1.0a14，未发布。日常验收直接 Python↔官方 A，不重编开发 Node B。

## 完成的迁移

已绑定 filter、shadowBlur/Color/OffsetX/OffsetY、globalCompositeOperation、lineDashFit；globalAlpha 的原有 typed 边界也接通原普通值转换/bail/STRICT 规则。共 8 个属性、16 个原 getter/setter 操作迁入唯一 core 的 context/effects.rs，Node/Python 共同转发。CSS filter 描述符由语言层解析，FilterSpec 的选择、颜色忽略、顺序与值打包复用原 utils.rs:filter_arg 的共享 lazy reader。没有另写模糊、阴影、颜色矩阵、混色或绘图算法。

支持原 blur、hue-rotate、brightness、contrast、grayscale、invert、opacity、saturate、sepia、drop-shadow 及其链。保留原规则：重复 kind 的 canonical 文本全部保留，实际值取最后一次，计算顺序保留第一次出现的位置；invalid token 可以忽略，完全无效表达式保留旧 filter；none 清空；显式 null/非字符串保留原 parser 异常。长度解析复用原 parseSize，em/% 使用原缺省 16px；hue-rotate 的 regex 不包含负号，不能擅自修成带符号角度。

CSS 数值先按原 JS f64 解析，再在原 native 边界转 f32。百分比须先转换成 JS Number 再除以 100，不能用 Python 大整数直接除法；471 组独立 parser 审计覆盖大整数和溢出，首轮差异及修正独立保留。canonical 顺序另作 owned 私有传输字段，避免 JSON map 排序改变 FilterSpec 顺序。

混色支持原全部 28 个名字，含 destination/clear 扩展；setter 同时保留原 State 与 Paint 更新。无效字符串忽略，非字符串 TypeError。阴影负 blur 忽略、偏移不作额外限制；globalAlpha 保留原 [0,1] 门禁、普通 primitive/array/string 转换及非有限 bail。STRICT 错误消息保留原 rustError substr(1) 后的 U+FE0F。lineDashFit 支持 move/turn/follow，和已绑定的 marker、dash offset/list 及 Path2D 特效共同验证。

文字、图像、渐变、pattern/texture、变换/clip、save/restore、resize/reset、重复相同 canonical 的缓存规则均保留原 core 流程。putImageData 继续绕过效果/混色/变换/clip。原 Filter::filters_for、render_to_canvas、paint_for_shadow、path effects、Vulkan 和全部绘图函数体未修改。逐项参数/单位/返回/异常/所有权及来源见 [效果 API 状态](effects-api-status.json)。

## 来源与生命周期

scripts/effects_extraction.py 逐项生成并校验原 state/FilterSpec 片段；新增 4 个原 enum helper 移到 core utils，完整原函数体检查从 234 增至 238。既有 Context24 个片段、其他来源约束继续检查。来源快照与 327 个第三方 Cargo 条目不变，无新依赖。

所有 parser 和字段读取在 Python 借用 Context 前完成，native 只收 owned 值，原 GPU/字体/filter cache 留在 owner TLS；没有 unsafe Send/Sync 或 GPU 线程池转移。新增 12 项生命周期检查覆盖 Canvas wrapper GC、跨线程读写拒绝、带 cache 的 owner 退出、restore/scale/rotation、错误保留、owned descriptor、图像/路径释放、blit 效果绕过、marker snapshot、resize/reset、共享 shader 和解释器退出，累计 76 项。64 项 bootstrap 含 paint/state 双更新、FilterSpec 顺序和 shadow blur 字段的篡改负例。

## 实际证据

修改前源码、lock 和 61 项 bootstrap 在 `20261028-effects-before`。真实旧 alpha13 wheel 在 54 个 filter 场景明确报未绑定 AttributeError，记录于 `20261028-effects-previous-filter-capture-linux` / `20261028-effects-previous-review`，没有把旧输出称为已实现。

新增 effect-filters54、effect-shadows24、effect-composite42、effect-paths13、effect-edges98，共 231 个独立场景；官方默认与 STRICT 均单独采集。首个候选 wheel 的 229 普通/229 STRICT 场景已精确匹配，旧 64 项生命周期通过。独立 parser 第一候选有 21 条大百分比转换/溢出差异；修正后 471 组全部匹配，新增后累计 76 项生命周期通过。失败结果不覆盖。

最终入口 `test-runs/20261028-effects-final-2/run.json`：同一 alpha14 wheel 在仓库外 cwd、空 PATH 的干净 CPython 3.13.18 venv 安装。累计 670 个不同普通 Python 场景精确对齐官方 A；G6/G7 的 369 个场景另验 STRICT，不重复计为独立功能覆盖。38 份普通、11 份 STRICT，共49份比较，JSON 数值、RGBA 和解码 PNG 无容差，alpha=0 的 RGB 仍计数。76 项生命周期、64 项 bootstrap、6 项 ledger、font/text/decoration parser300/213/227、effect parser471、2864 个标量位串及18组图像加载/事件分别存证。

最终构建 `20261028-effects-wheel-final-build-linux-2` 只重建 Rust/Python native，Skia C++ 复用既有已验证缓存；wheel/原 native/来源/依赖/素材 SHA 与清单固定保存。生产图无 Neon/N-API，wheel 不带 Node/字体/工作区运行依赖，开发 Node B 未重编。实际 PNG 单独视觉审阅。

`20261028-effects-native-trace-linux` 使用同一 wheel 组合图像滤镜、属性阴影、中间 Picture 混色、marker fit 和文字，readback/PNG 观察原 Vulkan surface 与 Skia submit；fresh CPU 控制另存。只是 Mesa llvmpipe 软件 Vulkan，不代表 Windows 硬件 GPU、Metal、driver vkQueueSubmit 或 native surface 尺寸验收。

## 后续

下一功能大目标为 G8 多页与完整导出/异步资源边界。完整 JS host/proxy/valueOf/prototype、极端或循环对象仍属 G0；G5 缺字、安全 cluster/实际绘制字体来源、G6 Sharp/全量 EventEmitter/网络选项、App/Window、Windows/Metal、static-fontconfig/manylinux、完整许可与发布仍保留。没有 commit、push 或上传。

最终另加两例孤立surrogate描述符，按原Neon JsString.value转换为U+FFFD后进入Rust；CSS parser本身保留原JS字符串。首个最终构建仍保留，但不作为最终验收字节；修正后的构建和全量验证分别在final-build-linux-2/final-2目录。
