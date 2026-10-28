# 0.1.0a18 发布状态

2026-10-28，用户已授权继续执行源码同步、GitHub Actions、GitHub Release、TestPyPI 及 PyPI 发布流程。GitHub alpha Release 已公开；TestPyPI 未找到匹配的 Trusted Publisher，尚未在包索引上线。既有迁移和 CPU 报告保留其完成当时的历史状态；本文件记录后续发行状态。

## 已验收的发行物

首批范围为 CPython 3.13、Windows AMD64、Linux glibc 2.28+ x86_64。沿用 [迁移报告](COMPLETION_REPORT.md) 和 [CPU 报告](CPU_RENDER_REPORT.md) 中验收过的同一 wheel，不重新构建替代文件。

| 文件 | SHA256 |
| --- | --- |
| `py_skia_canvas-0.1.0a18-cp313-cp313-win_amd64.whl` | `9efce11f1340a9bfbb69387f0757abe1635b3ff45528ce07e69dc30771049b74` |
| `py_skia_canvas-0.1.0a18-cp313-cp313-manylinux_2_28_x86_64.whl` | `2e641429ceedaca260037abba217e13189a16a1168571fa430857e06b2734071` |

已审阅 GPU 包 `reviewed-wheels.zip` SHA256 为 `4884291b61d3143db7a681067abd223101b864b5baf1aa457a0a8e9b6136827c`，对应 manifest 为 `1489613964763c29de7884353744ceeb754e3853eb8ec8684815116af0491e29`。独立 CPU 补充包 `cpu-validation-0.1.0a18.zip` SHA256 为 `7ba80b8a642747de9a6f7b3800ba3b1b47fbf4865ff7b839d6e8b80e226a010d`。

Windows 默认并发 PDF/SVG 文件序列的原版非确定性限制继续保留；单线程诊断全部精确一致。无 GPU 时支持离屏渲染与导出，App/Window 屏幕呈现仍要求 GPU。macOS、其他 Python ABI 和架构未获得本轮验收。

## 外部门禁

| 门禁 | 当前状态 |
| --- | --- |
| 已验收 wheel 字节与来源 | 已完成，本轮复核未修改生产代码 |
| 源码提交与 GitHub 同步 | 已完成，发行来源提交 `8b5611dc7911d9ebc470c949a396807515690aac` |
| GitHub Actions 实际运行 | [40708692406](https://github.com/xuanhun/py-skia-canvas/actions/runs/40708692406) 全部通过，74 项 bootstrap 及来源/许可/API 门禁 |
| GitHub Release 下载与 SHA 复核 | [v0.1.0a18](https://github.com/xuanhun/py-skia-canvas/releases/tag/v0.1.0a18) 已公开，8 个文件由无认证公开 URL 重新下载并核对精确 SHA |
| GitHub Release 独立安装回验 | Windows/Linux 各 203 普通及 203 STRICT 差分、12 组实际 GPU 字形/表面观测、118 项 GPU 生命周期、23 项 CPU 测试通过；同一 wheel/native SHA |
| Actions reviewed-wheels 暂存 | [40709164905](https://github.com/xuanhun/py-skia-canvas/actions/runs/40709164905) 已通过；独立下载 artifact 后再次核对两端 wheel/manifest |
| TestPyPI 发布与独立安装/GPU 检查 | [40709439674](https://github.com/xuanhun/py-skia-canvas/actions/runs/40709439674) 返回 `invalid-publisher`，未找到匹配的 Trusted Publisher，尚未上传 |
| PyPI 发布与独立安装/GPU 检查 | 待 TestPyPI 回验及 PyPI Trusted Publisher |

Trusted Publisher 参数为仓库 owner `xuanhun`、仓库 `py-skia-canvas`、workflow `publish-reviewed.yml`；TestPyPI environment 为 `testpypi`，PyPI environment 为 `pypi`，项目名均为 `py-skia-canvas`。两个索引分别配置；无需向聊天或仓库提供 API token。

三个 GitHub 发布 environment 已配置仅允许 `main` 分支。首次 CI 记录为 [40707431974](https://github.com/xuanhun/py-skia-canvas/actions/runs/40707431974)：文件字节和全部指纹值均一致，差异仅在 Windows/Posix 路径排序；校验器现显式采用相同分量排序，未刷新来源 manifest 或 source-map。CI 同时显式安装锁定的 TypeScript 开发解析器，不引入生产运行时依赖。修复前后的独立记录保留在 `test-runs/20261028-ci-source-*`。

## 当前授权缺项和安装边界

TestPyPI 返回的是有效 GitHub OIDC 身份未匹配 publisher；GitHub CLI 登录不能代替包索引账号配置。请在 [TestPyPI Publishing](https://test.pypi.org/manage/account/publishing/) 与 [PyPI Publishing](https://pypi.org/manage/account/publishing/) 分别登记上述 Pending Publisher，完成后可重跑失败的 TestPyPI job，再进行独立安装/GPU/CPU 检查，最后发布正式 PyPI。不要把 GitHub Release 或暂存成功写成 PyPI 已上线。

Windows 未启用长路径支持时，过深的虚拟环境目录会令许可证文件路径超出系统 `MAX_PATH`，pip 明确失败。建议使用较短的环境目录；本轮不改变系统注册表或已验收 wheel 中的许可负载。首次失败见 `20261028-github-installed-1`；后续安装回验分别保留新目录。

公开 URL 安装回验使用当前独立环境指纹。Windows 14 个系统字体文件与前轮清单不同；Linux 指纹未变。原记录完整保留，当前 Node A 与 Python 共同消费新清单，不忽略资源变化。清单与差异见 `20261028-release-environment-*`、`20261028-index-publisher-diagnosis-1`。

GitHub Release 安装回验记录为 `20261028-github-installed-5`，独立复核为 `20261028-github-installed-review-2`。两端均从公开 Release URL 使用 pip 禁用缓存安装到仓库外的新 CPython 3.13 环境，在 `-I`、空 PATH 下检查实际安装的 native，未使用 Node/源码运行时 fallback。公开摘要为 Release 资产 `github-installation-verification-0.1.0a18.json`。这些用例是发行物安装后的独立子集复核，不累计为迁移覆盖的新用例，也不替代 TestPyPI/PyPI 安装门禁。
