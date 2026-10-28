# G5 第一批：FontLibrary 注册、查询与重置

日期：2026-10-28。固定 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 为 0.1.0a8，未发布。

## 实现范围

已绑定单例 `FontLibrary` 的 `families`、`has`、`family`、`use` 和 `reset`。`use` 保留文件路径、路径数组、别名与路径、别名映射三种原重载；返回文件/家族/weight/style/width 元数据。名称和路径为原字符串，weight 为原数值，无坐标单位。`family` 未找到时以及 `reset` 返回独立的 `undefined` 单例。

原文件读取、Windows WOFF/WOFF2 转换及解码失败回退、Typeface 元数据提取移到唯一 canvas-core，Node/Python 共用。字体匹配、注册替换、变量字体 weight 规则、collection/cache 失效与 reset 顺序保持原实现；没有重写字体算法。Python 只负责原 JS 签名、字符串边界、映射顺序、错误和返回数据。

保留 `has` 的大小写敏感成员查询、原 `family_details` 查询、同 alias/style 替换、空别名、按原顺序处理映射以及非字符串路径过滤。原 Node 数组按输入长度分配、有效字符串压到前面的行为保留，后部空槽返回 `undefined`。单个数组或映射后续加载失败时，前面的成功注册保留；未增加事务回滚。文件读取/解码错误映射到原 Error；参数错误及消息按已覆盖场景对齐。

`ctx.font` 的 CSS 解析及自定义别名的文字选择尚未绑定。新增场景中的文本是默认字体绘制烟雾检查；变量字体在本批仅验证家族元数据，不能据此声称变量字体 glyph/shaping 验收完成。

## 线程、所有权与来源

单例 facade 不持有字体或 GPU 对象，每次调用解析到调用线程的原 Rust TLS FontLibrary。各线程注册相互独立，返回值为独立 Python 元数据快照。Typeface、FontMgr、collection 和 cache 留在原线程；没有增加 unsafe Send/Sync、Python 线程池或 GPU context 转移。

新增 4 项真实 wheel 生命周期断言：调用线程隔离、部分失败后 reset 与已记录文字、不受 Canvas GC/快照修改影响的注册、线程退出与解释器退出。共 32 项。字体释放依赖原 TLS 生命周期；Canvas debug 计数不被当作字体对象计数。

来源映射记录 233 个完整原函数体、24 个已有 Context 操作片段、Path/投影片段及新增两个字体片段。原 `typeface_details` 改为共享值提取与 Node 分配边界，故完整体计数由 234 减至 233；原 Windows 两个 decode 函数体仍逐字保留。`scripts/font_library_extraction.py` 明确允许的分离，52 项 bootstrap 含 Windows fallback 和 alias 规则的篡改负例；这不是 Windows 运行验收。327 个第三方锁定包条目不变，Windows allsorts 依赖从现有 Node 图复用。

接口逐项参数、返回、异常、所有权及来源见 [FontLibrary API 状态](font-library-api-status.json)。

## 实际证据

变更前资料、源码和 lock 保存在 `test-runs/20261028-fontlib-before`，有 50 项 bootstrap 与原版 A↔变更前 B 比较。新 fixture `font-library.json` 14 例、`font-library-edges.json` 8 例；有效原版与 STRICT 基线为 `20261028-font-library-original-linux-2`、`20261028-font-library-original-strict-linux-2` 及对应 edges 目录。第一轮把 Ubuntu 变量字体路径误写为不存在的文件，失败与旧 fixture 保留；修正为已核验 manifest 中的实际路径，没有跳过测试。

初始 Python 采集脚本未支持元数据 dict 的字段读取，首轮结果保留为 INCOMPLETE；修正采集协议后 22 例对原版精确一致。首个生命周期版本假定透明图层连续读回稳定；专门原版/Python 探针证明三次结果分别逐字节相同，而相邻读回确有变化。保留原核心行为，把稳定性断言改用不透明背景；失败及修正后的 32 项检查日志保留。

最终入口为 `test-runs/20261028-fontlib-final/run.json`。实际 alpha8 wheel 共 156 个 Python 场景分别对官方 A 与最终共享核心 B 的 JSON、RGBA、解码 PNG 精确比较，无容差，alpha=0 的 RGB 仍计数。Node 41 组、Python 36 组比较；32 项生命周期、52 项 bootstrap、6 项 ledger 与 716×4 标量位串检查分别记录。

最终 Node 构建 `20261028-fontlib-node-final-build-linux`，wheel 构建 `20261028-fontlib-wheel-final-build-linux`；Rust 重新构建，继续复用已验过的 Skia C++ 缓存。仓库外干净 CPython 3.13.18 venv、空 PATH、无 Node，安装和运行指定 wheel。生产依赖无 Neon/N-API；wheel 清单检查不含 Node 模块或字体文件。

`20261028-fontlib-native-trace-linux` 用同一 wheel 注册/查询/reset，再导出已记录的默认文字和路径，观察真实原 Vulkan surface 与 Skia submit 栈；fresh CPU 控制单独记录。这是 Linux Mesa llvmpipe 软件 Vulkan 证据，不是自定义字体选择、Windows 硬件 GPU、Metal、driver 入口或 native 尺寸验收。

测试只使用已核验的系统字体路径及 SHA，未复制或打包字体字节。wheel 为 generic linux_x86_64，未标为 manylinux。

## 后续

继续 G5 原 CSS font parser、字体选择与文本状态，再验证自定义字体实际 glyph、完整 metrics/排版、CJK/RTL/组合字符/emoji。完整宿主/代理/原型/自定义 coercion、G4 参数契约、图像、其他效果、多页/异步、App/Window、Windows/Metal、static-fontconfig/manylinux、许可与发布验收继续保留在任务清单。未 commit、push 或上传。
