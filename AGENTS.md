# py-skia-canvas 开发约束

先读 `docs/NEW_SESSION.md`、`docs/IMPLEMENTATION_PLAN.md`、`docs/API_COMPATIBILITY.md` 和 `docs/TASKS.md`。本项目是通用 Canvas 库，不是 PPT 生成器。

- 兼容目标是固定版本的 Node `skia-canvas` 公共行为，首个基线 v3.0.8；保留原默认 GPU 策略。CPU 控制只作诊断，不能替换 GPU 验收。
- 复用公开 Rust/Skia 核心。只分离语言绑定，不能重写字体、shaping、布局、混色、绘图、Vulkan 设备选择或加样例补偿。未改造逻辑完整保留，不以临时实现替代。
- 核心只有一份，由开发用 Node 绑定和 Python 绑定共同消费；生产 Python wheel 不依赖 Node、Neon/N-API、skia-python、旧 Codex 包、其他工作区或 `.local`。
- `references/upstream` 是只读来源快照，不得从中动态 fallback 或把它当已去 Node 的 Rust crate。变更在未来 `crates/canvas-core` 的唯一工作副本进行，并保留来源映射。
- 公共 API 先保持 Node 命名和默认值；Python 惯用别名只能转发同一实现，不能复制策略。没有完成的绑定保留在任务清单，不用空对象、白图或假成功充数。
- 每个新增或迁移函数说明功能、参数、单位、返回值、异常、线程/所有权约束及上游位置。原函数改名不能伴随算法改写。
- 不得对线程局部 GPU 对象添加未经证明的 `unsafe impl Send/Sync`。不得用 Python 线程池搬动原 GPU context。对象生命周期和异步导出须独立验证。
- 每批按影响范围跑断言和原 Node 差分；变更前后均保留证据。JSON 数值和 RGBA 无容差；alpha 为零时 RGB 差异仍计数。PNG 字节相同不是唯一像素判断依据。
- 区分 `BOOTSTRAP_VALIDATED`、`ORACLE_CAPTURED`、真实 Python 实现检查、视觉审阅和发布验收。缺 GPU/字体/驱动是缺少对应验收，不能静默 skip 后称通过。
- 新证据写入独立的 `test-runs/<run-id>/`，不覆盖旧结果。第三方许可和系统字体文件不得混淆；不上传不明许可字体、用户文档、凭据或本机 node_modules。
- 发布必须使用实际验收过的同一 wheel 字节，固定版本、SHA 和来源。GitHub Actions 成功、GitHub Release、TestPyPI、PyPI 安装分别验证。
- 保留用户修改；当前启动资料的准备不授权自动 commit/push 或发布占位包。新会话按当时用户授权执行外部操作。
