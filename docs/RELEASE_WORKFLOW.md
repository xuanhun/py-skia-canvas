# 构建与发行

当前支持目标为 CPython 3.13 Windows AMD64、Linux manylinux_2_28 x86_64。macOS、其他 ABI/架构未获得本轮验收。源码检查和 CI build 成功都不代表 GPU 发布验收。

用户追加的纯 CPU 门禁已独立执行，结果见 [CPU_RENDER_REPORT.md](CPU_RENDER_REPORT.md)。未来发布应同时附上 GPU 和 CPU 证据，并注明原版窗口/并行矢量序列限制；本轮使用的发行 wheel 字节没有改变。

源码发行物使用 `python scripts/build_sdist.py --out <新的输出目录>`。该工具只在临时源码包里离线修整 Maturin 缩减 workspace 后遗留的开发 Node lock 条目，保留所有生产依赖版本/来源/checksum，并精确比较 Windows/Linux 的依赖和 feature 树。它显式写入工作副本的原始字节，防止本机跨文件系统打包出现小文件 NUL 占位；不改仓库 Cargo.lock。源码包必须再从仓库外展开并以 `--locked` 实际构建。发布仍只使用已验收 wheel，源码构建的新 wheel 只作验证。

Windows 使用 `scripts/build_windows.ps1`；Linux 使用固定 digest 的 `tools/manylinux.Dockerfile`，挂载 Rust 1.90.0 的 CARGO_HOME/RUSTUP_HOME 后运行 `bash scripts/build_manylinux.sh`。Linux 第一次构建需要完整原 Skia 源码，再对其实际 FreeType 能力构建 Fontconfig 2.17.1。脚本不修改原字体匹配或绘图算法。工具链、下载库和字体清单必须随每次证据记录。

工作流 `build-wheels.yml` 只生成 unreviewed 候选。需要把同一候选分别装到仓库外的干净 Python 环境，清空 PATH 并使用 `-I`，对固定官方 Node A 运行差分、生命周期、实际 GPU surface/提交、GUI 和字体检查。硬件或字体缺失要记录缺少验收，不能静默 skip。

本地验收完成后，生成 `release-manifest.json`、同一 wheel 字节及证据 SHA 清单。`verify_release_bundle.py` 要求外部指定已审阅的 manifest SHA，检查两个平台的 ACCEPTED 状态、wheel SHA/大小、额外 wheel 与禁止负载。该校验防止传错包，不代替对证据的审阅。

外部操作需要用户授权。按 NEW_SESSION 的要求，本地未同步的工作先说明并获得授权后再 commit/push；不自动发布占位包。GitHub 仓库权限、protected environments 和 PyPI Trusted Publisher 分别核对。

授权后，将 reviewed-wheels.zip 原样上传到对应 GitHub Release。`stage-reviewed.yml` 以给定 archive/manifest SHA 下载并验证，生成 reviewed-wheels Actions artifact；不重新构建。`publish-reviewed.yml` 手工选择此 run id 和 TestPyPI/PyPI，重新核对相同 SHA 后仅上传验收 wheel。为 release-review、testpypi、pypi 配置受保护环境，并分别配置 Trusted Publisher。凭据不写入仓库或证据。

必须分别记录：GitHub Actions 实际 run、GitHub Release 可下载字节、TestPyPI 独立安装与 GPU 检查、PyPI 独立安装与 GPU 检查。发布后再次下载并确认 wheel SHA 与本地验收一致。不从包索引安装重编译的替代 wheel 冒充同一验收物。
