# G4 第五批：DOMMatrix 运算与 CSS 变换

日期：2026-10-27。基线 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 为 0.1.0a6，未发布。

## 实现范围

已绑定 multiply/multiplySelf/preMultiplySelf、translate/translateSelf、scale/scaleSelf/scale3d/scale3dSelf、rotate/rotateSelf/rotateFromVector/rotateFromVectorSelf/rotateAxisAngle/rotateAxisAngleSelf、skew/skewSelf/skewX/skewXSelf/skewY/skewYSelf、flipX/flipY、inverse/invertSelf、setMatrixValue 和 toString。原 JS 的 4×4 循环顺序、每次 f64 +=、默认值、typeof 判断和新旧数组持有关系均保留；不使用新矩阵库、FMA 或 fsum 替换。

DOMMatrix 构造及 Context/Path2D 矩阵重载共用原 CSS parser，支持 matrix/matrix3d、translate/scale/rotate 的单轴与 3D 形式、skew/X/Y、px/数值/%、deg/rad/turn 和原单词初始化。原语法、单位、错误优先级、额外参数和 permissive parseFloat 行为进入独立场景。DOMMatrix 操作角度是度，Canvas context.rotate 仍为原弧度；坐标/原点为 canvas units，比例/轴向量无单位。

原源码的行为也完整保留：newInstance 会将 is2D 重置为 true；无操作 skew/零旋转轴返回的新对象可继续共享原数组；通常的 invertSelf 返回另一个矩阵而不改 self，奇异矩阵则修改 self 并返回 undefined；inverse 会先重置 is2D，因此与直接 3D invertSelf 不同。Python 新增单例 `undefined` 区分这一返回值和 None/null，测试协议按原标签保留，不把二者合并。

奇异逆变换的底层是普通 Array，其余常规结果为 Float64Array。Python 保留该类型区别，因此 toFloat64Array 在该状态返回 list；普通快照对应 array('d')。3D toString 的 Float64Array.map 会把回调字符串转回数值，普通数组则保留字符串；原 toFixed(12)/regex 与这次类型转换均保留，不通过调整 fixture 或数值容差消除差异。

## 原数学实现与来源

独立调查 `20261027-matrix-math-audit` 的 716 个输入显示，系统 Python libm 与当前 Node 的 sin/cos/tan/atan2 分别有 24/24/28/38 个不同的 f64 结果，因此没有把系统三角函数当作等价实现。

绑定静态复用 [Node 22.23.2 的原 V8 IEEE 数学源码](https://github.com/nodejs/node/blob/aa4c77582be995286fc6e00aaf530dc7ade102a9/deps/v8/src/base/ieee754.cc)，commit aa4c77582be995286fc6e00aaf530dc7ade102a9，V8 12.4.254.21-node.56。ieee754.cc/h 与 overflowing-math.h 保留原字节；冻结来源、URL/SHA 和工作副本位于 references/math/node-v22.23.2 与 crates/python/vendor/v8。仅导出四个 double→double 的纯数值入口，不包含 JS 引擎、Node/V8 runtime、回调或 GPU 数据。导出/宏/位拷贝 glue 单独记录，未改写原函数。

cc 1.2.38 已在原 Cargo.lock 内，本批只显式使用其构建依赖；327 个已有第三方包条目不变。C++ 禁止浮点 contraction 和 fast-math，实际编译器路径/参数另存 dom-math-build.txt；Skia C++ 缓存复用。V8 BSD 许可及 Sun fdlibm 原声明进入同一 wheel，发行级完整许可审核仍独立待办。

`scripts/validate_matrix_math.py` 核验冻结来源与工作副本字节，纳入 core 来源校验。实际最终安装 wheel 的 716×4 次标量比较记录在 `20261027-matrix-installed-math-linux`，与先前独立 Node 原始位串全部相同；这是一组有限的标量证据，不冒充全 IEEE 空间证明或像素验收。

## 实际证据

`20261027-matrix-before` 保存变更前 46 项 bootstrap、core/资料检查、关键源码/lock，以及三套新 fixture 对官方 A 和未变 Node B 的原始对照。matrix-ops.json 18 例、css-transform.json 14 例、matrix-edges.json 4 例；Node 分普通与 STRICT 进程。

最终结果入口 `test-runs/20261027-matrix-final-2/run.json`。最终 alpha6 wheel 共 110 个 Python 场景，对固定官方 A 与同核 B 的 JSON、RGBA、解码 PNG 全部精确一致，透明 RGB 仍计入；Node 共 33 组、Python 共 28 组比较。25 项真实 wheel 生命周期断言通过，新增 owner 退出后运算及无操作共享/随后分离；48 项 bootstrap 和 6 项 ledger 是另外的工具检查，含 V8 系数与浮点编译选项篡改负例。

最终 wheel 构建在 `20261027-matrix-wheel-final-build-linux`；仓库外的干净 CPython 3.13.18 venv 安装相同字节，在空 PATH/无 Node 下执行，并逐文件核验安装内容。Node/core 的 66 个文件与上批验收源码相同，复用既有同一 B 二进制，在 `20261027-matrix-node-reuse-linux-2` 记录；不声称重新构建 Node。

`20261027-matrix-native-trace-linux` 使用同一 wheel 的 CSS/rotate/skew/Path2D 组合，记录原 Vulkan surface/Skia submit 栈以及独立 CPU 控制。仍为 Linux Mesa llvmpipe 软件 Vulkan；不是 Windows 硬件 GPU、Metal、驱动 vkQueueSubmit 入口或实际 native 尺寸验收。

首轮候选 `20261027-matrix-candidate-linux` 保留 toString 的差异记录和输入快照：原矩阵数值及像素一致，但 Python 起初遗漏 3D Float64Array.map 的字符串→数值转换。修复按原数组类型进行，未修改 oracle、fixture 或容差。

首次最终工具检查 `20261027-matrix-final` 还发现新 V8 冻结文件未进入来源图，导致负例测试的独立临时工作副本缺文件；补齐四个原文件映射后，在新最终目录重新运行。同一 wheel 字节继续验收，未重新构建来替换证据。

## 尚未完成

本批覆盖原运算和 parser 的已测数值/部分原始值 profile，不代表所有 JS 对象/valueOf/代理/缺省/非法输入、全部 STRICT 契约或极端 Number 最短字符串表示已审计。dump/inspect 的 Node console/宿主对应、createProjection、DOM 非数值 coercion 等仍待逐项完成；toString 极端最短十进制边界继续列入 G0。逐方法状态见 [矩阵 API 状态](matrix-api-status.json)，不提升整个 ledger 为完整兼容。

字体、图像、其他效果、多页/异步、App/Window、Windows wheel/硬件 GPU、完整字体/driver provenance、static-fontconfig/manylinux、许可审核和发布仍在任务清单。未 commit/push 或上传。
