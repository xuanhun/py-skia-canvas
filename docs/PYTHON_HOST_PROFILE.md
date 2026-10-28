# Python 语言宿主对应

2026-10-28 用户已确认采用此方案：Canvas 绘图、默认 GPU、指标与像素按固定官方 skia-canvas 3.0.8 精确比较；语言宿主使用 Python 对应类型。独立 wheel 不依赖或启动 Node。

| Node 宿主 | Python 对应 |
| --- | --- |
| undefined / null | 导出的 undefined 单例 / None |
| Number / String / ordinary Array/Object | f64 语义数字、str、list/tuple、dict；显式 toString/valueOf 协议在字符串转换点调用 |
| Buffer / Uint8ClampedArray | bytes 与原有可写 clamped byte view；不共享 Node 进程内对象身份 |
| Promise | 可 await 的实际原生导出/加载结果；异步任务不搬动 GPU context |
| EventEmitter listener / warning | Python callable、同一 listener 实现、Python warning；OS/事件循环调度由对应 Python loop 承担 |
| URL / 文件路径 | urllib.parse URL 结果与 os.PathLike；标准 Python 网络传输，Node Agent/JS Proxy 本身不作为 Python 输入 |
| Sharp / Node Readable stream | 同名 toSharp 入口抛原缺少 Sharp 依赖 Error，不返回占位对象，也不引入 Node；用原 toBuffer/toFile 获取等价 Canvas 数据 |
| JS Proxy/Symbol/原型链反射与 console.inspect | Python 对象、属性/描述符、repr 与 callable 协议；不宣称提供 JavaScript runtime 的元对象身份 |
| 上游原生 panic/危险递归输入 | 明确的 Python 异常和保留的危险 profile 记录，不以崩溃或假成功满足 API |

这份宿主对应不允许改字体选择、shaping、布局、绘制、混色、Vulkan 设备/表面或用容差消除差异。每项实际完成/验收状态仍由源码清单和独立证据决定；此文件不把尚未通过的实现检查自动改为通过。
