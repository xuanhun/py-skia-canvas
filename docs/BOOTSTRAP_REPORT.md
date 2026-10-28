# 启动资料交接（2026-10-27）

## 范围

从用户提供的 `https://github.com/xuanhun/py-skia-canvas` 克隆；初始 main commit 为 `9f1a4ca731653e89da336f0b02130747cc555350`。保留原 LICENSE。当前只准备独立开发的启动资料，没有 Rust 核心拆分、Python 渲染模块、wheel 或 PyPI 发布；没有修改旧 PPT 生产代码。

已提供：详细架构与实现步骤、G0–G11 任务清单、API/语言契约、GPU/生命周期/发布门禁、可复制的新会话指令、历史诊断摘要，以及可执行 starter 工具。

## 来源核对

公开上游 `skia-canvas` v3.0.8，commit `042312a3f40b660b1d7dc0beba541486171bc5cc`，来源 checkout 为干净工作树。复制 49 个 Rust/JS/类型/构建参考文件，621,038 bytes；逐文件指纹见 [manifest](../references/source-manifest.json)。原生入口索引有 176 个导出函数、17 个 JS 顶层 export 名称，**不是 176 个完整公共 API 或已迁移项**。

没有复制系统字体、原生二进制、旧专有包、用户 PPT、凭据、node_modules 或旧仓库 `.local`。本轮测试显式指定既有开发工具和原 npm oracle 的位置，不将其路径写入新产品实现或自动发现逻辑；另一环境按 [测试说明](../tests/README.md) 在新仓库单独安装开发 oracle。

## 实际执行

| 检查 | 实际结果 | 能证明的范围 |
| --- | --- | --- |
| Python stdlib bootstrap 单测 | 22 项通过 | 资料校验、引用/资源约束、来源索引、精确比较器及负例 |
| `scripts/validate_bootstrap.py` | BOOTSTRAP_VALIDATED；49 文件/176 native/17 JS exports/29 cases；0 错误 | 文档链接、指纹、场景结构，无渲染实现结论 |
| Node 原包场景采集 | 两轮各 29/29 CAPTURED，状态 ORACLE_CAPTURED | 场景可执行、原包输出已记录 |
| 两轮 Node 记录比较 | MATCHED_RECORDS；29 例 JSON/readback/PNG 解码像素全部精确一致 | 同一原包重复采集稳定，不是 Python 对齐 |
| 原图抽查 | 查看矩形、线性渐变、pattern、emoji 4 图 | 可见非空绘制；不是完整文本/字体语义验收 |
| 证据覆盖保护 | 对已有采集目录重跑被拒绝，原 run.json 哈希未变 | 不覆盖此前证据 |

测试环境：Windows x64 `10.0.26200`，Node `v22.23.2`；原包 native SHA 与历史记录一致。默认组公开 getter 报告 Vulkan / NVIDIA GeForce RTX 5080 / NvidiaProprietary 595.95；显式 setter 例报告 CPU，构造 false 例重现 `.gpu=true` 而 `.engine.renderer=CPU` 的状态陷阱。未在本轮新增 native 断点/trace，不能把状态 getter 说成该证明。

本轮新场景没有在 Linux 执行；Linux 真 GPU 运行、字体文件指纹与 fallback 字形验证、重建 Node B、PyO3 candidate 均待后续执行。旧 Windows emoji **438 像素**问题没有在本轮被关闭。

## 本机原始证据

证据在 `test-runs/`，由 `.gitignore` 排除，不是假定 GitHub 上已有这些图片。换机器按同命令重新生成：

| 文件 | SHA-256 |
| --- | --- |
| `test-runs/bootstrap-oracle-win-001/run.json` | `f2b8941808fe7b8fe1153c792d392da8258f2245768db0d275577cd8ee696e18` |
| `test-runs/bootstrap-oracle-win-002/run.json` | `03bf23da45ccf8c3354d061d58162a72d9e619e9047dd9f9a87a9d19fb946ad4` |
| `test-runs/bootstrap-compare-win-001/result.json` | `3a2960192c025bfe21694ff0e1702dd28fad8e3af5a1aad4dd30be5a1a611605` |

## 下一步

在新仓库开启独立会话，使用 [NEW_SESSION.md](NEW_SESSION.md) 的完整启动指令，从 G0 公共 API、构建 provenance 与字体资源盘点开始。当前资料本地落盘；未自动 commit/push 或发布包。
