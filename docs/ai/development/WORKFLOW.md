# 开发流程与最小差分教程

中文 | [English](WORKFLOW.en.md)

本页给出从问题复现到候选 wheel 验证的路径。首次进入先完成[开发指南](README.md)的必读要求。命令在仓库根目录执行，除明确标注的“外部工作目录”步骤。所有 `NEW_*` 路径均须由当前批次替换为未使用的名称。

## 1. 确认起点和工具

```shell
git status --short
python --version
rustc --version
cargo --version
node --version
```

运行时 ABI 是 CPython 3.13。开发构建固定 Rust 1.90.0、Maturin 1.9.6、PyO3 0.27.2、rust-skia 0.88.0；依赖以仓库锁文件为准。0.1.0a18 双平台最终对照使用 Node 22.23.2 与官方 `skia-canvas@3.0.8`。某些历史工具记录含更早的 Node 版本，不能因此更新上游快照或随意换 oracle。

安装构建依赖与测试解码工具的开发环境可执行：

```shell
python -m pip install maturin==1.9.6 -r requirements-test.txt
npm ci --prefix tools/oracle --no-audit --no-fund
npm ci --prefix tools/api-ledger --ignore-scripts --no-audit --no-fund
```

`tools/oracle/node_modules/skia-canvas` 是本命令安装的官方 A 的模块路径；`--module` 指向包目录而非 `.node` 文件。不同 OS 分别安装，不能把 Windows 原生文件复制给 Linux。源码快照用于定位，不是可替代官方 A 的可执行物。工具已可用时复用，不必重复安装或下载。

先跑资料和来源检查：

```shell
python scripts/validate_bootstrap.py
python scripts/validate_core.py
python scripts/validate_licenses.py
node scripts/inventory-public-api.mjs --check
node --test tests/contracts/api-ledger.test.mjs
```

失败时先查差异来源。不要自动刷新 reference/hash 来把失败变成通过。`refresh_reference_index.py` 和 ledger 重新生成只在有明确来源变更的任务里使用，并审阅 diff。

## 2. 定位和保存修改前证据

用 `rg` 搜索公共名称，再沿 facade → PyO3 → core → 上游映射查找：

```shell
rg -n "fillRect|fill_rect" python crates/python crates/canvas-core crates/source-map.json
rg -n "fillRect|fill_rect" references/upstream
```

把问题缩到一个可重复输入：参数、属性赋值、返回值/异常、图形及资源。先运行官方 A 与当前 wheel，保留修改前结果，然后再改代码。文字问题还要记录字体文件、face、glyph/fallback；公共 `engine` 只能说明状态，不能单独证明实际 native 绘制分支。

教程 fixture：[parity-smoke.json](../../../examples/development/parity-smoke.json)。它有两个小场景：小数坐标色块及像素读回；共享渐变及缺参数行为。Node 和 Python 消费完全相同 JSON。`$ref` 引用测试资源；`save` 记录返回值；`observeError` 记录是否抛错/类型/消息，不预设必须抛错。此 JSON 仅驱动测试，不进入产品代码。

## 3. 构建并隔离安装候选 wheel

修改 facade 也会改变 wheel 字节，须重打包并用新 wheel 验证。不要在发行版测试后再替换源码/二进制。

Windows 要求可用的 MSVC x64 工具链与 CPython 3.13；脚本查找 Visual Studio 并设置构建环境：

```powershell
./scripts/build_windows.ps1
```

构建结果在 `dist/`，保留准确文件名并立即记录 SHA：

```powershell
Get-FileHash -Algorithm SHA256 dist/NEW_CANDIDATE.whl
py -3.13 -m venv C:\venvs\canvas-candidate
C:\venvs\canvas-candidate\Scripts\python.exe -m pip install --no-deps dist/NEW_CANDIDATE.whl
```

替换 `NEW_CANDIDATE.whl` 为实际文件；venv 使用未占用的短路径。较深前缀在未启用长路径的 Windows 上可能导致许可证安装失败。当前 0.1.0a18 已发布，未来发行须使用新版本，不能重用同版本上传不同字节。

Linux 日常开发可用已配置的工具链执行 `maturin build --release --locked --interpreter python3.13 --out dist`；这只产生本机开发产物。可发布 manylinux wheel 必须使用固定[容器定义](../../../tools/manylinux.Dockerfile)和[构建脚本](../../../scripts/build_manylinux.sh)，按[发行流程](../../RELEASE_WORKFLOW.md)准备 Rust/Cargo 挂载及静态 Fontconfig。普通系统库构建不能靠改文件名变成已验收的 manylinux 产物。

在隔离环境安装对应 Linux wheel：

```shell
python3.13 -m venv /tmp/canvas-candidate
/tmp/canvas-candidate/bin/python -m pip install --no-deps /ABS/dist/NEW_CANDIDATE.whl
```

上述 `--no-deps` 是独立 wheel 验证，本库运行不需要 Node/npm/Rust。第一次构建可能按原机制编译 Skia；是否可用预编译缓存由固定 feature/平台决定。只写应用时完全不用这一步。

## 4. Windows：执行最小 GPU 差分

以下在 PowerShell 中运行。环境变量和路径均为当前教程进程局部设置，不改系统配置。替换 `$candidateWheel` 与 `$installedPython` 为上一节真实产物/解释器。

```powershell
$repo = (Get-Location).Path
$run = Join-Path $repo 'test-runs/NEW_PARITY_WIN'
$fixture = Join-Path $repo 'examples/development/parity-smoke.json'
$manifest = Join-Path $run 'environment.json'
$candidateWheel = Join-Path $repo 'dist/NEW_CANDIDATE.whl'
$installedPython = 'C:\venvs\canvas-candidate\Scripts\python.exe'
$nodeExe = (Get-Command node).Source
$officialModule = Join-Path $repo 'tools/oracle/node_modules/skia-canvas'

python scripts/capture_environment.py --out $manifest
& $nodeExe tests/oracle/capture-node.mjs --module $officialModule --fixtures $fixture --environment $manifest --require-gpu --out (Join-Path $run 'node')
if ($LASTEXITCODE -ne 0) { throw 'Node capture failed' }

$savedTaskPath = $env:PATH
try {
    $env:PATH = ''
    Push-Location $env:TEMP
    try {
        & $installedPython -I (Join-Path $repo 'scripts/capture_python.py') --fixtures $fixture --environment $manifest --wheel $candidateWheel --backend gpu --out (Join-Path $run 'python')
        if ($LASTEXITCODE -ne 0) { throw 'Python capture failed' }
    } finally { Pop-Location }
} finally { $env:PATH = $savedTaskPath }

python scripts/compare_runs.py (Join-Path $run 'node') (Join-Path $run 'python') --out (Join-Path $run 'comparison.json')
if ($LASTEXITCODE -ne 0) { throw 'Records differ or are incomplete' }
```

开始前确认当前进程没有残留 `SKIA_CANVAS_STRICT` 或屏蔽 GPU 的 `VK_*` 设置；普通和 STRICT、GPU 和 CPU 要使用分开的新目录。`capture_environment --out` 是 **JSON 文件名**；其他 capture 的 `--out` 是新目录。

## 5. Linux：同样的最小 GPU 差分

在 Linux/WSL 内运行，路径使用 Linux 语法，字体 manifest 在本平台重新采集：

```bash
set -euo pipefail
repo="$PWD"
run="$repo/test-runs/NEW_PARITY_LINUX"
fixture="$repo/examples/development/parity-smoke.json"
manifest="$run/environment.json"
candidate_wheel="$repo/dist/NEW_CANDIDATE.whl"
installed_python=/tmp/canvas-candidate/bin/python
node_exe="$(command -v node)"
official_module="$repo/tools/oracle/node_modules/skia-canvas"

python3.13 scripts/capture_environment.py --out "$manifest"
"$node_exe" tests/oracle/capture-node.mjs --module "$official_module" --fixtures "$fixture" --environment "$manifest" --require-gpu --out "$run/node"
(
    cd /tmp
    env PATH= "$installed_python" -I "$repo/scripts/capture_python.py" --fixtures "$fixture" --environment "$manifest" --wheel "$candidate_wheel" --backend gpu --out "$run/python"
)
python3.13 scripts/compare_runs.py "$run/node" "$run/python" --out "$run/comparison.json"
```

Python capture 必须从仓库外工作目录、空 PATH、隔离模式运行。它验证实际导入来自已安装环境，检查 wheel 内包字节一致及 native 依赖；不会偷偷换成源码或 Node 实现。比较器输出 `MATCHED_RECORDS` 表示这两个场景的记录精确匹配，不代表完整 API 发布通过。

## 6. 普通、STRICT、CPU 与更大影响范围

普通模式不设置 `SKIA_CANVAS_STRICT`；STRICT 在 Node 与 Python 两个新进程中都设置 `SKIA_CANVAS_STRICT=1`，再使用新输出目录。覆盖无效参数时两个模式都需要。

CPU 诊断可以选择 `cpu-setter` fixture，或在独立进程屏蔽驱动后让默认模式自动回退，并要求实际 CPU。对上面两个默认场景，教程验收采用后一方式：

```text
Windows 子进程：
VK_DRIVER_FILES=C:/nonexistent-skia-driver.json
VK_ICD_FILENAMES=C:/nonexistent-skia-driver.json
VK_LOADER_DRIVERS_DISABLE=*

Linux 子进程：
VK_DRIVER_FILES=/nonexistent-skia-driver.json
VK_ICD_FILENAMES=/nonexistent-skia-driver.json
VK_LOADER_DRIVERS_DISABLE=*

Node capture 使用 --require-cpu
Python capture 使用 --backend cpu
```

环境屏蔽只作用于诊断子进程，不改驱动安装或系统默认值。它不等价于“没有 Vulkan 动态库”；后者必须在实际无库环境单独验证。CPU 结果不替换默认 GPU 门槛。完整 CPU matrix 配置和命令见 [tests/cpu](../../../tests/cpu/README.md)。

按改动增加 `tests/fixtures` 中相关场景、导出比较、生命周期、字体/原生路径观测。常用入口：

```shell
python scripts/capture_exports.py --help
python scripts/compare_exports.py --help
python scripts/audit_draw_sources.py --help
python scripts/trace_python_gpu.py --help
python scripts/run_cpu_matrix.py --help
```

查看帮助后按工具实际参数构造新 run；不省略必需资源。独立断言要能检测真实错误/边界，不写仅镜像实现或只检查对象存在的测试。

## 7. 收尾

审阅 `git diff`，确认原生逻辑、来源快照、默认策略与用户修改未被意外改变。新函数文档应有完整契约；来源映射和测试覆盖要随实现更新。报告使用测试实际生成的状态名、平台/后端和 wheel SHA；把未执行、缺资源与已接受限制明确写出。发布前继续[测试与发布验收](TESTING_AND_RELEASE.md)。
