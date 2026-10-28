# G4 第六批：createProjection 与原数字字符串解析

日期：2026-10-28。固定 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 为 0.1.0a7，未发布。

## 实现

已绑定 CanvasRenderingContext2D.createProjection(quad, basis)。原 Context 依据 bounds、尺寸对或 left/top/right/bottom 展开坐标，再调用原 Skia Matrix::from_poly_to_poly。该段逻辑机械移入唯一 canvas-core，由开发 Node 与 Python 共同消费；只替换 JS 返回数组和错误对象的分配，未另写投影求解器。

quad 与 basis 坐标单位为 canvas units；返回独立 DOMMatrix，系数无单位、平移为 canvas units。省略/过滤为空的 basis 使用当时 Context bounds；不是创建 Canvas 时的固定快照。createProjection 不修改当前 CTM、路径或绘制状态，后续通过 setTransform/transform/Path2D 显式使用结果。

Python 保留原 [arg].flat() 的一层边界以及 points_arg 的过滤顺序。数字字符串、布尔/null、零/单元素嵌套数组按照原 _as_double 转换；不支持的对象/undefined/非有限 f64 被过滤，然后才转 f32 和检查偶数长度。有限 f64 转换后的 f32 溢出不额外过滤。原 Rust 空串、0x/0o/0b/u64 与 f64 字符串解析段也提取为共享 parse_number_string，Node/Python 调用同一函数，原 Native Node 的其余类型分支及有限性判断保持不变。

原来的边界行为均保留：三点输入可产生仿射投影，即使错误文字只写 2/4 点；错误消息中的数量为矩形展开后的点数；第一个参数的奇数长度错误先于第二个；部分零面积/退化输出会成功返回奇异矩阵。没有增加尺寸、有限性、可逆性或顶点顺序的额外规则。

## 所有权与来源检查

原 Context、路径、GPU 对象继续留在 owner TLS。Python 仅在借用 Context 前处理语言值，原求解器返回的 9 个 f32 转为自有 DOMMatrix 数据；没有 Python 回调处于 Context 借用期间，没有 unsafe Send/Sync 或 GPU context 跨线程移动。

新增 3 项真实 wheel 生命周期断言：owner 线程退出后继续使用投影、跨线程拒绝与错误后状态/PNG 保持、resize/Canvas GC 后快照独立。共 28 项生命周期检查。

来源图保持原 234 个完整函数体、24 个已有 Context 操作片段及 Path 片段，并新增投影和数字字符串两个受控边界片段。scripts/projection_extraction.py 列出允许替换的返回/错误分配；字符串解析语句保持原文本。新增 bounds 默认值与无符号进制解析的篡改负例。50 项 bootstrap、6 项 ledger 是工具/来源检查，不作为渲染通过的替代。

## 实际验证

`test-runs/20261028-projection-before` 保存变更前 48 项 bootstrap、core/资料检查、源码/lock 与原版 A↔变更前 B 证据。projection.json 的 16 例涵盖默认/显式 basis、矩形/四边形/三点、状态/resize、快照、Path/跨 Canvas、f32 舍入和渐变/clip/文本；projection-edges.json 的 8 例涵盖奇数数量、missing/undefined/null、展开后错误、退化、非有限过滤、Rust 字符串与嵌套数组转换。

两组最终官方基线分别为 `20261028-projection-original-linux-2`、`20261028-projection-edges-original-linux-2`，另有各自 STRICT 进程。最初 edge fixture 在“观察错误但实际成功”后漏存资源 ID，产生 Unknown target；失败记录和旧 fixture 保留，修正记录方式而未改 API 输入。文本场景 fontPolicy 标签也已修正为 system-unpinned，旧记录保留；字体/config 字节仍逐文件核验。

最终入口 `test-runs/20261028-projection-final/run.json`：实际 alpha7 wheel 共 134 个 Python 场景，分别对固定官方 A 和最终同核 B 的 JSON、RGBA、解码 PNG 精确一致，无容差，alpha=0 的 RGB 仍计入。Node 共 37 组、Python 共 32 组比较；28 项生命周期、既有 716×4 项标量位串检查另存证据。

Node 最终构建在 `20261028-projection-node-final-build-linux`，Python 在 `20261028-projection-wheel-final-build-linux`。本批 Node 也重新编译，不能复用迁移前 B 冒充新 core 验收；Skia C++ 缓存继续复用。327 个第三方 Cargo 包条目不变，生产依赖图无 Neon/N-API；干净 CPython 3.13.18 venv 位于仓库外，空 PATH/无 Node，实际安装文件与指定 wheel 逐文件一致。

`20261028-projection-native-trace-linux` 使用同一 wheel 的 createProjection、渐变绘制及 Path2D 投影，记录原 Vulkan surface 与 Skia submit 栈，CPU 控制单独验证。仍为 Linux Mesa llvmpipe 软件 Vulkan，不是 Windows 硬件 GPU、Metal、驱动入口或实际 native 尺寸验收。

## 后续

接口逐项状态见 [投影 API 状态](projection-api-status.json)。这些场景不是全部 JS 宿主/代理/循环对象/自定义 coercion 的完整契约；Python tuple 只转发同一数组处理，没有另一套投影策略。G4 其余参数契约、DOM 非数值/非法 setter、极端 Number 最短字符串、dump/inspect 的宿主对应仍归 G0。

继续 G0 参数语义审计与 G5 FontLibrary/字体绑定。图像、其他效果、多页/异步、App/Window、Windows wheel/硬件 GPU、完整字体/driver provenance、static-fontconfig/manylinux、许可审核和发布仍在 TASKS。未 commit/push 或上传。
