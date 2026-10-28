# G4 第三批：CanvasGradient 与样式引用

日期：2026-10-27。兼容基线仍为 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 版本为 0.1.0a4，未上传或发布。

## 实现

已绑定 CanvasGradient 直接构造、Context 的 createLinearGradient/createRadialGradient/createConicGradient、addColorStop 和 fillStyle/strokeStyle 渐变赋值。坐标/半径为 canvas unit，锥形角度为弧度；所有绘制、stop 排序、重复 stop 的 epsilon 比较、shader、颜色舍入、opaque 优化和状态栈都使用唯一 Rust core。

没有给 radial 构造新增负半径错误，没有捕获创建时 Context 的矩阵，也没有把空 stop shader 改为自定义透明输出。这些行为均对照固定原版。offset 先按原位置转为 f32，再做原范围检查，因此略大于 1 的 f64 可能舍入为合法的 1；极小负数也可能成为 -0。范围检查先于颜色解析，缺省/空颜色的已覆盖错误消息保持原样。

原 `addColorStop` 的范围检查提取为 core 的 `validate_offset`，Node/Python 共用；其余 gradient 核心函数体保持不变。Python 只做有限数值、CSS 字符串及对象包装；完整 JS 颜色对象 coercion 和所有非法参数/STRICT 契约仍待 G0 审计。

## 原样保留的 JS 引用缓存

原 JS 的 fillStyle/strokeStyle setter 另存 shader 对象引用；native getter 返回 null 时，JS 返回该引用。它不随 Rust State 的 save/restore 自动恢复：恢复绘制的 g1 后，getter 仍可能返回最后设置的 g2。无效 CSS setter 会清空 JS 引用，但 native gradient dye 仍保留，因此 getter 可以返回 null，而后续仍用该渐变绘制。

Python 复现这一独立语言引用缓存，不根据当前 Rust dye 重建 wrapper。reset/resize 也不主动清缓存；当 Rust State 返回 CSS 黑色时，getter 返回 CSS 值，但旧 Python 渐变仍按原规则被缓存持有，直到重新赋样式或 Context 回收。它不是重新实现绘图状态，也不以“修 bug”改变上游行为。测试分别检查对象身份和实际像素。

## 所有权

owner TLS registry 增加原 CanvasGradient；Python NativeGradient 只持资源 ID。样式赋值 clone 原 Rc ramp，未复制 stop、未移动 GPU context。来自不同 owner 的渐变在更改 Canvas State/缓存前拒绝；同线程跨 Canvas 共享与创建方 Canvas 回收后继续使用均已验证。异线程 GC 仍只入队 ID，owner 下一入口或退出回收；未添加 unsafe Send/Sync。

## 验证与证据

`test-runs/20261027-gradients-before` 保存变更前 44 项工具检查、源码/lock 快照和新 12 例 A↔B 对照。新场景包含重复/临近 epsilon stop、共享修改后的不同绘制快照、radial/conic、零/单 stop、退化/负半径、错误优先级和 f32 边界、直接构造、引用缓存恢复/无效 setter、跨 Canvas、描边与默认文字。

最终入口是 `test-runs/20261027-gradients-final/run.json`。实际 alpha4 wheel 共 56 个 Python 场景对固定官方 A 和最终同核 B：全部 JSON（含 sameRef 对象身份观察）、RGBA、解码 PNG 精确一致，无 epsilon，不隐藏 alpha=0 的 RGB。Node 新渐变场景另分普通/STRICT 进程；Python 的完整非有限/对象 coercion/STRICT 仍未验收。

46 项 bootstrap、6 项 ledger 用于工具与来源验证；真实 wheel 生命周期共 20 项，新增渐变异线程 GC 后原生 State 保留、cache/restore/reset 持有、owner 退出、跨 owner 拒绝、共享后创建方回收、解释器退出。原 327 个第三方 Cargo package 条目不变，Skia C++ 复用既有缓存。

最终 wheel 构建在 `20261027-gradients-wheel-final-build-linux`，Node 在 `20261027-gradients-node-build-linux`。干净 CPython 3.13.18 venv 位于仓库外，空 PATH/无 Node；安装内容与指定 wheel 逐文件核验，动态依赖不指向 Node/Neon、`.local` 或其他工作区。SHA 与构建来源分别记录，未混用先前候选。

`20261027-gradients-native-trace-linux` 通过同一 wheel 的锥形渐变填充、修改 stop 后描边捕获原 Vulkan surface 与 Skia submit 方法栈；新 CPU 对照单独验证。仍为 Mesa llvmpipe 软件 Vulkan，不代表 Windows 硬件 GPU、Metal 或驱动入口/实际尺寸 trace 已验收。

接口范围见 [渐变 API 状态](gradient-api-status.json)。本批不提升未完整审计的全局 ledger 条目，也不把局部精确匹配称作完整兼容/发布通过。

## 下一步

G4 剩余 DOMMatrix/DOMPoint/DOMRect、getTransform/currentTransform 和完整重载/coercion。字体、图像、其他效果、多页/异步及 App/Window 仍在 TASKS；Windows wheel/硬件 GPU、完整字体/native provenance、static-fontconfig/manylinux、许可证和发布验收继续单独完成。本批没有 commit/push 或发布操作。
