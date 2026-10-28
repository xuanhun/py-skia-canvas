# 0.1.0a18 发布状态

2026-10-28，用户已授权继续执行源码同步、GitHub Actions、GitHub Release、TestPyPI 及 PyPI 发布流程。当前为发布进行中，尚未在包索引上线。既有迁移和 CPU 报告保留其完成当时的历史状态；本文件记录后续发行状态。

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
| 源码提交与 GitHub 同步 | 准备中 |
| GitHub Actions 实际运行 | 待源码同步 |
| GitHub Release 下载与 SHA 复核 | 待 CI |
| TestPyPI 发布与独立安装/GPU 检查 | 待该索引的 Trusted Publisher 配置和授权 |
| PyPI 发布与独立安装/GPU 检查 | 待 TestPyPI 回验及 PyPI Trusted Publisher |

Trusted Publisher 参数为仓库 owner `xuanhun`、仓库 `py-skia-canvas`、workflow `publish-reviewed.yml`；TestPyPI environment 为 `testpypi`，PyPI environment 为 `pypi`，项目名均为 `py-skia-canvas`。两个索引分别配置；无需向聊天或仓库提供 API token。
