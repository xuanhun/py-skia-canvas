# 新会话启动指令

用户已于 2026-10-28 授权继续 alpha 发布流程；后续源码同步、CI、Release、TestPyPI/PyPI 的实际状态以 [RELEASE_STATUS.md](RELEASE_STATUS.md) 为准。下方“外部操作未授权”等表述是历史状态，不能覆盖本次授权。

最新追加要求：纯 CPU 验收见 [CPU_RENDER_REPORT.md](CPU_RENDER_REPORT.md)，其结论与默认 GPU 验收独立。所有原 Canvas 离屏任务已在无 GPU/无 Vulkan 环境测试；生产 wheel 未修改。不要将原版 App/Window 的 GPU 限制写成已支持 CPU 窗口，也不要隐去 Windows 并行矢量导出的继承限制。

> 2026-10-28 本批最新状态：G0–G9 在用户确认的 Python 宿主范围内已迁移并完成 Windows/Linux 本地 alpha 验收。先读 [本批交付报告](COMPLETION_REPORT.md) 和 [发行流程](RELEASE_WORKFLOW.md)；下面保留早期方案/记录，其中“尚待迁移”不覆盖最新报告。外部同步、Actions 实际执行、Release/TestPyPI/PyPI 仍需单独授权与验证。不要重装已可用工具链、重编 Node 或换掉已验收 wheel。


截至2026-10-28 已推进G0/G1、G2四批核心拆分及G3真实PyO3绑定与G4独立Path2D/roundRect/渐变/DOM值对象/运算/CSS/createProjection与矩阵重载/Linux CPython3.13 wheel；先读 [当前实现进度](PROGRESS_2026-10-27.md) 和 [最新构造与参数批次](G0_G4_ARGUMENT_REPORT.md)，不要重新创建或覆盖现有workspace。下方流程继续适用，但不再是只有启动资料的状态。

在独立会话打开本仓库 `C:\code\py-skia-canvas`。若在另一台机器，先clone `https://github.com/xuanhun/py-skia-canvas` 并确保启动资料已提交/同步；本次准备资料并不自动表示远端已更新。

将下面内容粘贴给新会话：

```text
请在 xuanhun/py-skia-canvas 实现独立的 Python Canvas 开源库并最终发布 pip wheel。

先完整阅读 AGENTS.md、README.md、docs/IMPLEMENTATION_PLAN.md、
docs/API_COMPATIBILITY.md、docs/TASKS.md、docs/TEST_AND_RELEASE.md、
references/README.md 和 references/history/README.md，再检查Git当前状态。

当前有Rust workspace和共享Canvas/Context/字体/paint/Page/GPU核心，独立Rust和Python绘制已对照Node；有本地Linux CPython3.13 alpha wheel，未发布。
先读docs/G0_G4_ARGUMENT_REPORT.md、docs/G9_GUI_REPORT.md和docs/PROGRESS_2026-10-27.md确认已有工作、证据与待办。不要把bootstrap检查、
Node采集、旧skia-python回归或CPU控制通过当作新库GPU兼容完成。

兼容基线固定 Node skia-canvas 3.0.8，源码commit
042312a3f40b660b1d7dc0beba541486171bc5cc。
用户已确认保留原默认GPU效果1:1，不能改为CPU-only，不能靠容差/像素补偿。
停止优先给skia-python补Vulkan的旧路线；不要依赖skia-python或混用它的对象。

方案是原Rust核心机械拆分为唯一canvas-core，由开发用Neon adapter和
生产PyO3 adapter共同调用；Python wheel运行不需要Node/Neon/N-API。
原绘图、字体、Vulkan、缓存和编码逻辑完整保留；不重写算法，不以临时实现顶上。
第三方fork仅作拆分参考，不替换原版Skia/色彩行为。

继续完成G0语义审计、G1原生GPU trace和资源确认；Linux原源码重建与
共享core与2114个普通Python场景、1813个STRICT场景及206个导出用例已对齐官方A；117项生命周期测试和Linux原生GPU路径trace已完成。
Canvas构造/尺寸、独立Context构造与普通几何参数/STRICT契约已补齐，接着完成G4/G0文本绘制等剩余参数与宿主契约，并推进G5安全cluster/实际绘制字形与emoji/平台审计，G6图像/像素/pattern/texture普通公共入口已完成迁移，G7效果/混色/marker fit已完成迁移，G8多页与完整导出/异步资源边界已迁移，G9 App/Window已迁移，接着闭合G0/G4剩余契约与G5字形/emoji；完整TextMetrics数据/浅只读构造与measureText普通输入转换已绑定，所选测量布局glyph与字体四表身份已核对但music/emoji仍缺字；9个文本状态属性和textDecoration已绑定；FontLibrary注册/查询/reset及ctx.font CSS解析/实际字体选择已绑定；原DOMMatrix运算/CSS parser和createProjection已绑定，不重复创建现有文件。
每批跑最小相关测试并保留原始指标、raw/PNG、差异图、实际backend、字体和源码指纹。
每个新增/迁移函数写功能、参数/单位、返回/异常、所有权和线程约束注释。
保留原默认GPU门禁；gpu:false构造参数在3.0.8会误导状态，setter才真CPU。

先运行：
python -m unittest discover -s tests/bootstrap -v
python scripts/validate_bootstrap.py
python scripts/validate_core.py
工具使用见tests/README.md。不要修改reference哈希来掩盖来源变化。

先完成可在Windows/Linux真实Vulkan GPU surface上绘制和导出的小闭环，
但完整目标还包括整个Node公共API。不要静默删掉Window/App、异步和扩展API的任务。
发布要固定wheel字节和SHA，验证干净环境、无Node和实际GPU后再上传。
GitHub仓库权限与PyPI Trusted Publisher分别核对，不复制凭据或发布空占位包。

每一批结束交接实际完成项、命令/结果、未关闭问题和下一步。
需要改变兼容基线、验收标准、默认后端或引入明显不同实现时先征求用户决定。
```

## 当前可用的工具

`scripts/refresh_reference_index.py`生成只读来源/native索引；`inventory-public-api.mjs`盘点JS/类型声明；`validate_bootstrap.py`检查资料；`validate_core.py`检查首批拆分保持原函数体；`capture_environment.py`记录系统字体指纹；`tests/oracle/capture-node.mjs`支持固定官方Node和显式`node-rebuild`角色；`compare_runs.py`精确比较。已有capture_python.py真实wheel采集、trace_python_gpu.py和tests/python生命周期断言。其余API、跨平台wheel、正式CI和发布workflow仍待完成。具体命令见tests/README.md。

若只有本地资料尚未push，先向用户说明并在获得授权后同步；不能声称新会话从GitHub能拿到未提交文件。

用户于2026-10-28明确调整日常验收：Python只与固定官方Node A保持一致，开发Node B不再每批重编/强制差分；共享唯一core和Node开发绑定架构保留。每次完成一个大的功能目标，并以实际wheel完成相关差分/生命周期/GPU验证后交接。


G8 多页与完整导出普通输入已迁移；范围、并发 Vulkan 初始化锁的来源和限制见 [G8 报告](G8_EXPORT_REPORT.md)。下一大目标为 G9 App/Window 与剩余公开项。G0 host/Sharp/极端输入及跨平台/字体/发布门禁继续保留；最终可用 wheel 字节与检查结果以 G8 最终记录为准。


G9 App/Window 与普通事件/会话已迁移；范围、真实 GUI GPU/像素证据和原版危险输入见 [G9 报告](G9_GUI_REPORT.md)。全部 408 条清单的归属和剩余项见 alpha-api-status.json（docs 下）。完整兼容、Node Sharp 互操作、G0/G4/G5 与平台/发布门禁仍保留。
