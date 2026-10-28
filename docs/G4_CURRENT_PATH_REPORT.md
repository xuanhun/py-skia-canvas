# G4 第一批：当前路径、数值变换、clip 和描边

日期：2026-10-27。兼容基线仍为 skia-canvas 3.0.8；本地 Python wheel 版本为 0.1.0a2，目标 Linux x86_64 / CPython 3.13。没有发布或上传。

## 共享实现

`crates/canvas-core/src/context/operations.rs` 从原 `context/api.rs` 提取 23 段操作。保留原函数名、语句顺序、f32 转换后的计算、当前点/scoot、矩阵乘法、路径变换、负半径检查、线宽/线型校验及奇数 dash 复制规则。Node 仅保留 Neon 参数/错误/返回处理，Python 调用同一函数。

原 `Path2D` 类型的构造、PathBuilder 转换、scoot 和 add_ellipse 迁到唯一 core。角度规范化、原 4 位小数舍入、整圆拆分、矩阵转换均保持原函数体。Node 的所有 Path2D 返回入口改用既有 Resource 包装；SVG/布尔运算/插值/特效等未提取部分仍完整保留在 Node，并没有当作 Python 已实现。

原 `to_matrix`、cap/join 双向转换及 fill-rule 选择也由 core 唯一实现。`scripts/g4_extraction.py` 登记每个原片段与允许的语言边界替换；`validate_core.py` 检查 233 个完整原函数体、23 段操作、整文件分离及 Node 转发。原参考快照未修改，第三方 Cargo package 327 项保持不变，仅本地 Python 包版本改为 alpha.2。

## Python 范围

新增 beginPath/closePath、moveTo/lineTo、rect、arc/ellipse/arcTo、三类 Bézier/conic、当前路径 fill/stroke/clip、isPointInPath/isPointInStroke、六数值 setTransform/transform、translate/scale/rotate/resetTransform、lineWidth/miterLimit/lineDashOffset、lineCap/lineJoin 与 get/setLineDash。

参数先保持有限数值/字符串子集。几何单位为 canvas unit，旋转/弧角为弧度，系数与 miter 为无量纲。Python 只排列六个矩阵元素到原 Skia 顺序，没有第二份矩阵乘法或路径算法。负 ellipse/arcTo 半径采用 `RangeError`（ValueError 子类）保留原错误消息；无效 fill rule 保留 TypeError 消息。原 `arc` 没有相同负半径检查，不能套用 ellipse 的规则。

方法级范围、来源和证据见 [本批 API 状态](g4-api-status.json)。状态仍是有限输入范围的部分契约测试，没有把整项 ledger 升为完全验证。

## 证据

变更前工具检查保存在 `20261027-g4-before`，当时执行 40 项 bootstrap 断言。`current-path.json` 14 例在变更前官方 A 与同核 Node B 精确一致；`path-adapter.json` 4 例同样保留变更前对照。失败的首轮 Node 编译保存在 `20261027-g4-node-build-linux`：两个 Path2D 局部变量返回入口漏包 Resource，之后修正。没有覆盖失败日志。另用 `current-path-flags.json` 两例发现初始 Python 真值转换与原 `bool_arg_or` 不同；差异原样保存在 `20261027-g4-flags-before-comparison`，最终按原规则仅接受实际布尔值，其余取 false。

最终证据入口为 `test-runs/20261027-g4-final/run.json`。当前路径 14 例包括曲线/隐式起点、超过整圆 sweep、旋转 ellipse、负半径错误、nonzero/evenodd 与命中测试、嵌套 clip/restore、路径构造中改变矩阵、奇异/负缩放矩阵、线型和非法范围。另 4 个 Node-only 场景覆盖 Path2D 构造/复制/自 addPath、simplify/unwind、布尔/插值/offset/transform、PathBuilder 特效返回及 outlineText/lineDashMarker 包装。

最终 Python 24 例（G3 原 8 + 当前路径 14 + CCW 参数 2）分别对官方 A 和最终同核 B 比较全部 JSON 指标、RGBA、解码 PNG。无容差，不隐藏 alpha=0 的 RGB。Node 当前路径及 CCW 参数在普通/STRICT 两个独立进程分别对照；Python 的完整非法参数/STRICT 行为尚未验收。

42 项 bootstrap 和 6 项 ledger 工具断言通过。真实安装 wheel 的生命周期测试扩为 8 项，新增路径/clip/状态栈的异线程 GC、异常恢复和 owner 退出；没有给 GPU 对象添加 Send/Sync 或让其进入 Python 线程池。

`20261027-g4-native-trace-linux` 使用同一已安装 wheel，绘制带变换的曲线、椭圆 clip 与 dash stroke，捕获原 Vulkan surface 和 Skia Vulkan submit 方法栈；全新 CPU 对照单独检查。请求尺寸为 300×150，原生优化符号未直接暴露实际尺寸字段；submit 断点仍是 Skia 方法入口，非驱动 vkQueueSubmit 入口。Linux 设备仍为软件 Vulkan llvmpipe。

最终 wheel 在 `20261027-g4-wheel-final-build-linux/wheels`，版本 0.1.0a2，SHA 与构建来源记在该目录的 `run.json` 和最终批次记录。外部 `/tmp` 中的干净 CPython 3.13.18 venv 安装指定字节，空 PATH、无 Node；安装文件与 wheel 内容逐个核验，动态依赖不指向 `.local` 或其他工作区。

## 保留任务

G4 尚未结束：公开 Path2D/DOMMatrix/DOMPoint/DOMRect、getTransform/currentTransform、roundRect 的 CSS radii 规范化、gradient 和相关重载仍待绑定。不得用空快照对象冒充 DOMMatrix，或把数值 transform 子集称作全部重载。

其余 JS coercion、缺省/undefined/null/non-finite/STRICT、字体、图像、异步、多页、App/Window 按原 TASKS 继续。Windows wheel/硬件 Vulkan、Metal、完整 native trace/字体 fallback、static-fontconfig/manylinux 与第三方许可/发布验收尚未关闭。本地软件 Vulkan 对照不代表跨平台或完整发行通过。

下一批从 G4 的 Path2D 独立对象、DOM 几何与 roundRect 规范化继续；保持相同源码核心与 GPU 基线。
