# G4 第四批：DOM 值对象与矩阵重载

日期：2026-10-27。固定 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 版本 0.1.0a5，未发布。

## 已绑定范围

DOMPoint 的数值字段、fromPoint、matrixTransform、toJSON；DOMRect 的数值字段、fromRect、原有边界 getter、toJSON。DOMMatrix 已绑定 6/16 标量/序列、同类拷贝和 matrix-like 对象构造、16 字段与 a/b/c/d/e/f 别名、is2D/isIdentity、fromMatrix/isMatrix3/isMatrix4、Float32/Float64 数组导入导出、clone、transformPoint、toJSON。

Context 的 currentTransform/getTransform 返回独立 DOMMatrix 快照，setter 转发同一 setTransform。setTransform/transform 和 Path2D.transform/addPath 接受同一 DOM 值/对象/6 或 16 元素输入；原 DOM↔Skia 元素映射、f64→f32 边界与矩阵连接仍保留原顺序。Python array('f')/array('d') 对应 Float32Array/Float64Array，并返回独立数组。坐标与平移为 canvas units，系数和齐次 w 无单位。

这些值对象来自上游 lib/classes/geometry.js 的 JS 包装层，适配为 Python 自有数据；未用新矩阵库替换绘制算法。点变换保留原表达式求值顺序和 2D 快路，不除以 w。唯一 Rust 渲染核心未改动，Node 源码也未改动。新增 native getter 仅按原 get_currentTransform 顺序读取 9 个 f32；没有把 GPU context 搬到 Python 对象。

## 保留的原行为

- DOMRect 的负宽高不做边界归一化，right=x+width、bottom=y+height。
- DOMMatrix 的 3D 字段置回原值后 is2D 仍可为 false，而 isIdentity 为 true；clone/fromMatrix 从数值重新判断 is2D。
- fromMatrix 的不完整对象使用六个别名默认值；不完整的 m11…m44 对象不会自动成为 4x4 矩阵。
- native floats_in 先过滤非有限 f64，再转 f32；Context 对无效剩余长度忽略更新，Path2D.transform 报原错误，Path2D.addPath 使用单位矩阵继续追加。过滤后恰剩 6 项时仍按原 6 项规则解释，不添加新的校验。
- getter/typed array/clone 都是独立值快照，修改它们不改变原 Canvas 状态。

## 所有权与验证

DOM 数据不含 Rust/Skia 句柄，无创建线程亲和；Canvas/Context/Path2D 的原 owner TLS 约束继续生效。新增 3 项真实 wheel 生命周期断言，验证 owner 线程退出后 DOM 快照在另一线程使用、foreign Context getter 拒绝而值快照可复制、resize/Canvas GC 后快照独立。共 23 项生命周期测试。

`test-runs/20261027-dom-values-before` 保存变更前 46 项 bootstrap、core/资料检查、源码/lock 快照和 14+4 例原版 A↔上批 B 比较。两套新 fixture 分别为 dom-values.json 的 14 例与 dom-edges.json 的 4 例；覆盖 signed rect、2D/3D/透视、对象默认值、别名、sticky flag、typed array、getter/状态栈/resize、Path 重载、错误、非有限过滤、f32 溢出和 f64 表达式顺序。原 A 另有 STRICT 进程。

最终结果入口 `test-runs/20261027-dom-values-final-2/run.json`：实际 alpha5 wheel 共 74 个 Python 场景分别对固定官方 A 和同核 B，JSON、RGBA、解码 PNG 全部精确一致，无容差，alpha=0 的 RGB 仍参与。Node 共 27 组比较，Python 共 22 组比较；46 项 bootstrap、6 项 ledger 单独作为工具/来源检查。

Python 从仓库外干净 CPython 3.13.18 venv 安装同一 wheel，空 PATH/无 Node，并核验安装文件与 wheel 字节。最终构建位于 `20261027-dom-values-wheel-final-build-linux-2`。Node+core 文件逐个核验与上批验收指纹相同后，复用 `20261027-gradients-node-build-linux` 的相同二进制，记录在 `20261027-dom-values-node-reuse-linux-2`；不冒充重新编译。327 个第三方 Cargo 条目不变，Skia C++ 缓存复用。

`20261027-dom-values-native-trace-linux-2` 记录同一 wheel 的 DOM 透视矩阵、渐变绘制和 Path2D 矩阵重载的真实 Vulkan surface/Skia submit 栈，CPU 对照独立。仍仅为 Linux Mesa llvmpipe 软件 Vulkan，不是驱动入口/实际 surface 尺寸、Windows 硬件 GPU 或 Metal 验收。

首次最终轮次 `20261027-dom-values-final` 精确差分发现 addPath 的无效 native 矩阵应使用单位矩阵，Python 曾误报 TypeError；相关 wheel、比较结果、源码快照和 INCOMPLETE 状态均保留。修复只改语言适配的原默认值，不改 fixture、原 core 或容差；第二轮对同一原版输入重新验收。

## 明确保留的待办

本批是数值 DOM profile，未绑定 CSS transform 字符串解析、矩阵乘法/平移/缩放/旋转/倾斜/翻转/求逆、setMatrixValue、toString/dump/inspect，以及全部 JS 非数值/缺省/null/undefined/host/proxy 对象契约。非空 CSS 构造直接报告 NotImplementedError，不产生占位矩阵。createProjection 也仍待绑定。接口逐项见 [DOM API 状态](dom-api-status.json)；不提升全局 ledger 为完整契约验收。

接下来继续 DOMMatrix 原操作与 CSS parser，再补 G0 完整重载/coercion。字体、图像、多页/异步、App/Window、Windows wheel、硬件 GPU、字体/驱动 provenance、static-fontconfig/manylinux、完整许可证和发布仍在任务清单。未 commit/push 或上传。
