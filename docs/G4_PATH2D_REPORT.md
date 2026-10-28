# G4 第二批：独立 Path2D 与圆角矩形

日期：2026-10-27。基线仍是 skia-canvas 3.0.8，本地 wheel 为 Linux x86_64 / CPython 3.13 的 0.1.0a3。尚未上传或发布。

## 实现范围

独立 Path2D 已绑定默认/SVG/复制构造、d/edges/bounds/contains、线段/曲线/圆弧/椭圆/矩形/roundRect、addPath（包括自追加）、五种布尔运算、interpolate、simplify/unwind、offset/transform、round/trim/jitter/points。Context 的 fill/stroke/clip、两种命中测试支持显式 Path2D；outlineText 和 lineDashMarker 也返回/消费真实路径。

原几何和特效语句机械迁入 `canvas-core/src/path/operations.rs`，Node 与 Python 共同调用。原插值的反向 Skia 操作数顺序、simplify/unwind 对源 fill type 的修改、特效失败时的原路径 clone、SVG setter 的 rewind/add 顺序和非法 SVG 构造默认行为均保留。无效构造 SVG 返回真实空 Skia path 是原版行为，不是未实现接口的占位输出。

edges 的原迭代器、权重同步、跳过起点和数组下标保持原顺序，只分离 Neon 数组/数字分配。非有限值用内部 Number token 跨 JSON 边界，在两个绑定恢复为原 Number/float；负零不归零。原 Node bounds 分配保持原 f32 计算，Python 返回同一 core Rect 的数值。

roundRect 保留 CSS `parseCornerRadii` 的截断、有限值先检查、负半径错误、1/2/3/4 扩展及负宽高交换顺序。Context 未提供半径时为 0；Path2D 未提供半径时原版忽略该调用。两者共用同一个 Python 参数适配器，Rust 使用原 RRect 路径操作。支持有限数值、数值数组和含 x/y 的字典；DOM 类、复杂对象/coercion 仍待审计。

六数值与六元素数组的矩阵排列由一个 Python helper 处理，矩阵计算和路径变换仍是原 Rust/Skia。trim 的有限数值/bool 重载按原 JS 在 f64 阶段规范化后才到原 f32 转换；没有 Python 路径裁剪或近似算法。全 JS coercion、宿主动态 effect 调用与 DOM/3D 矩阵仍未验收，不能把本批状态升级为完整公共 API 兼容。

## 生命周期

共享 owner TLS registry 增加真实 Path2D 集合。Python NativePath 只保存已有 ID handle；不持 Skia 值，不添加 unsafe Send/Sync。Canvas/Path 的创建、跨线程拒绝、ID 延迟回收、线程退出销毁复用同一机制。

显式路径在创建线程 clone 为原 Skia COW snapshot，随后才借用 Canvas；既避免 registry 重入，也保留绘制后修改源路径不改变已记录图形的行为。不同线程的路径禁止交给 Canvas。marker/outline/effect 等返回对象登记为真实独立资源，在 owner 上释放；异线程 GC 只传 ID。

生命周期测试扩到 14 项，新增纯 Path GC、异线程 Path GC 后 marker snapshot、owner 退出仍有 Path 引用、跨 owner 路径拒绝且 Canvas 不变、带 Path 的循环 GC、解释器带活动 Path 退出。仍只验证 Linux CPython 3.13；free-threaded Python、fork、多解释器及异步取消待办保留。

## 验证和证据

变更前 42 项工具断言及源码快照在 `20261027-path2d-before`；10 个新 Path2D 场景 A↔B 已在变更前精确对照。4 个 roundRect 场景也保留独立变更前 Node 对照。失败编译没有覆盖：首次 Node copy 构造的临时 borrow 生命周期、首次 Context roundRect 的 Point import 在各自目录记录后修复。

最终入口是 `test-runs/20261027-path2d-final/run.json`。实际 wheel 的 44 个 Python 场景分别对固定官方 A 和最终同核 B 精确比较全部 JSON、RGBA 和解码 PNG；包括 G4 原 24、Path2D 10、路径边界 2、既有 Path2D 返回家族 4 和 roundRect 4。边界场景覆盖源 fill-type 修改，以及有限 f64 到 f32 溢出/负零的 edges 与 bounds。alpha=0 的 RGB 仍计数，无容差。

Node 新 Path2D/边界/roundRect 在普通和 STRICT 独立进程对照。44 项 bootstrap、6 项 ledger 断言用于工具/源码验证，不替代真实 wheel 检查。原 327 个第三方 Cargo package 条目保持不变，Skia C++ 构建复用原缓存。

`crates/source-map.json` 覆盖 234 个完整原函数体、24 段 Context 操作和 Path2D 入口/数据分配的受控分离；完整文件由 `scripts/path_extraction.py` 从冻结来源推导校验。接口状态与适用范围见 [Path2D API 状态](path2d-api-status.json)，没有提升未审计的全局 ledger 条目。

最终 wheel 构建在 `20261027-path2d-wheel-final-build-linux`，Node 在 `20261027-path2d-node-accepted-build-linux`；安装在仓库外干净 CPython 3.13.18 venv。空 PATH、无 Node，包/native 文件与指定 wheel 字节匹配，ldd 不指向 Node/Neon、`.local` 或其他工作区。SHA 与构建来源分别保存，不混用早期候选 wheel。

`20261027-path2d-native-trace-linux` 使用最终同一 wheel 绘制独立路径、布尔/round 特效、显式 clip/fill/stroke，记录 Vulkan surface 与 Skia submit 方法栈；新 CPU 对照单独检查。设备仍为软件 Vulkan llvmpipe，断点不是驱动 vkQueueSubmit，优化符号未直接解码 surface 尺寸字段。

## 继续任务

G4 剩余 DOMMatrix/Point/Rect、getTransform/currentTransform、gradient 及全部重载/coercion 继续实现。G5 字体、G6 图像、其他效果/异步/多页/Window/App 未删项。Windows 硬件 Vulkan/wheel、Metal、字体 fallback、完整 native provenance、static-fontconfig/manylinux、许可证与发行验收尚未完成。

本批没有改变默认 GPU、兼容版本、字体/绘图/混色/设备选择，没有使用 Node/参考快照作为 Python runtime fallback，也没有 commit/push 或发布操作。
