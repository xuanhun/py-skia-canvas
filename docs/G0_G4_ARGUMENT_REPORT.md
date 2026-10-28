# G0/G4 构造与普通数值参数契约

本批以固定官方 Node skia-canvas 3.0.8 A 为标准，完成一个构造与基础几何参数目标。原默认 GPU、共享 Rust/Skia 算法保持；未重编开发 Node B，未 commit/push/上传或发布。

## 本批实现

Canvas 的 options 解构、默认值、textContrast/textGamma 原数值读取和范围检查移到唯一 `canvas-core::canvas::construction`，Node/Python 均调用。原 gamma==4 的 f32 epsilon 调整及上游误用 contrast 检查 gamma 上界的条件原样保留，因此 gamma=10 仍接受。没有修正原 GPU constructor false 的状态/实际 renderer 不一致。原 width/height 的 JS Number 外层判断、native 有限数读取和仅重置当前页的次序由绑定保留；默认模式无效 native 数值仍重置当前页，STRICT 在重置前抛错。

官方实测 `new CanvasRenderingContext2D(canvas)` 会建立独立 Context，不加入 pages，也不成为 Canvas 当前页。Python 现调用原 Context2D::new/reset_size 实现相同入口。缺失、null、非 Canvas 参数保留原 TypeError。独立 Context 保持创建时尺寸，后续 Canvas resize 只重置其公开当前页。新的 public-page ID 集合只区分语言入口所有权，不修改原绘图/布局或设备选择。

当前路径、Path2D 原语、rect、translate/scale/rotate、lineWidth/miterLimit/lineDashOffset、setLineDash、contains/isPointInPath/isPointInStroke、三类 gradient 与 addColorStop 已使用相同普通参数读取。`_argument_specs.py` 从原 Rust 函数的参数名、位置、分段读取和 bail 标记生成；Context.arcTo 的四坐标后读 radius 与 Path.arcTo 一次读五参数的差异保留。缺参、额外参数、有限 f64 再 native f32、布尔 CCW、默认忽略和 STRICT 错误及其消息中的 U+FE0F 均对照原版。roundRect 保留原 JS radius 检查先于 native 坐标检查的顺序。命中测试的原四参数歧义、fillRule 优先读取和数值过滤行为保留；实际几何仍调用原 core。

STRICT 按原 Neon 的环境变量规则读取：去 ECMA 空白、转小写，0/false/off 关闭，其余非空值开启，原空字符串回到默认 0。统一入口同时修复先前 image facade 将 `false` 字符串误当开启的判断。有限值读取复用现有 Rust original utils 转换，Python 只处理语言参数边界。几何数值读取中的单元素自引用数组会使原版递归溢出；Python 明确 NotImplementedError，保留 G0 未支持项。

## 函数契约与来源

| 入口 | 参数与单位 | 返回与异常 | 所有权与原版位置 |
| --- | --- | --- | --- |
| Canvas / core construct | width/height 画布单位；contrast/gamma 无量纲；gpu truthy | Canvas；原 RangeError/TypeError；未知 options 忽略 | 新 owner TLS；canvas.js constructor、canvas.rs new |
| width/height / getContext | 尺寸画布单位；context 普通 loose '2d' | setter None；Context 或 None；STRICT TypeError | owner；canvas.js setters/getContext 与 canvas.rs setters |
| CanvasRenderingContext2D(Canvas) / context_handle | 有效 Canvas，创建时尺寸 | 独立 Context；无效参数 TypeError，foreign/ended owner RuntimeError | 仅 metadata handle 跨 Python；context.js constructor、Context2D::new/reset_size |
| _argument_double / required / read | ordinary primitive/array，f64，原参数名与序号 | 数值/list/None 或原计数/类型异常 | 不搬 native 对象；utils.rs _as_double/_float_args_at 与生成 spec 中行号 |
| command / rectangle / round_rect | 坐标和半径画布单位，角度弧度，conic weight 无量纲 | None；原 RangeError/TypeError 或默认 bail | owner；context/api.rs、path.rs、context.js/path.js/css.js radii |
| transform / stroke_number / line_dash | 平移/宽度/dash 画布单位，比例/miter 无量纲，角度弧度 | None；原异常/无效值忽略 | owner；context/api.rs 原对应函数 |
| contains / hit | 坐标画布单位，可选 Path/fillRule | bool；原计数/规则/参数异常 | 同 owner；path.rs contains、context/api.rs _is_in |
| gradient create / addColorStop | 坐标/半径画布单位、角度弧度、offset 0..1 | Gradient/None；原范围/颜色/参数错误 | owner；gradient.rs 与 JS gradient.js |

每个实际新增函数有源码注释。对象仍放在 owner TLS；跨线程只移动 ID/lease，析构投递原 owner 队列。没有新增 unsafe Send/Sync，也没有搬动 GPU context。独立 Context 不使父 Canvas 强引用存活，沿用原有 Python weak-parent profile；父对象回收后 canvas 为 None 的 Python 表示并不冒充完整 JS host 等价。

## 验收记录

变更前资料与官方探索在 `test-runs/20261028-contracts-before`。实际已验 alpha16 在新增 geometry 694 用例中有 501 项与官方不同，原始记录保留于 `20261028-contracts-previous-1`，不是只新增自比较。首轮新实现 1415 用例普通/STRICT 全对齐；补充构造/独立 Context 后为 1428，再加环境值 fixture 为 1429 个不同场景。

最终本地 alpha17 wheel、确切字节/SHA、干净 CPython3.13 venv、仓库外 cwd 与空 PATH 的记录在 `test-runs/20261028-contracts-final-1`。全量 2114 普通及 1813 STRICT 场景比较 JSON 数值、raw RGBA 和解码 PNG，所有通道无容差，alpha=0 的 RGB 也计差。11 种 STRICT 环境值另以独立进程比较；206 个导出用例普通/STRICT 分别比较 224 文件的字节、结构、XML、解码/栅格 RGBA。117 项实际 wheel 生命周期断言、70 项 bootstrap 与来源负控制另记，不替代真实 GPU 验收。

原生 contracts 场景分别在独立 Context 和公开当前页绘制，记录 Vulkan surface 与 Skia queue-submit 调用栈；fresh CPU 控制必须为零。GUI default Vulkan trace 和七个真实 X11 窗口 RGBA/输入场景继续回归。source-map 保留 294 个原完整函数体哈希，另明确原 Vulkan 初始化锁两片段与本批 Canvas 构造分离片段；327 个第三方包不变。最终数字以 run.json/verification.json 为准，完成记录之前不作发布验收。

本批只关闭列出的普通构造/几何数值契约。文本绘制等其他入口参数、host 对象与自定义 valueOf/toString/proxy/subclass、Sharp、完整 EventEmitter、G5 安全 cluster/实际字形/emoji 和 GUI 原危险 profile 仍待完成。Linux Mesa 软件 Vulkan/WSLg 的结果不能代表 Windows、Metal、硬件 GPU、manylinux/static-fontconfig、完整许可或发布通过。
