# Development workflow and minimal comparison tutorial

[中文](WORKFLOW.md) | English

From reproduction to candidate-wheel verification. Complete the [development guide](README.en.md) prerequisites first. Run commands at the repository root except the explicitly external-working-directory step. Replace every `NEW_*` path with a fresh name for your batch.

## 1. Confirm starting state and tools

```shell
git status --short
python --version
rustc --version
cargo --version
node --version
```

Runtime ABI: CPython 3.13. Pinned build tools/dependencies: Rust 1.90.0, Maturin 1.9.6, PyO3 0.27.2, rust-skia 0.88.0; repository lockfiles are authoritative. Final 0.1.0a18 comparisons used Node 22.23.2 with official `skia-canvas@3.0.8` on both platforms. Historical tool records may mention earlier Node versions; do not rewrite upstream snapshots or substitute the oracle on that basis.

In the development environment, install build tools and the test decoder when needed:

```shell
python -m pip install maturin==1.9.6 -r requirements-test.txt
npm ci --prefix tools/oracle --no-audit --no-fund
npm ci --prefix tools/api-ledger --ignore-scripts --no-audit --no-fund
```

The official A package directory is `tools/oracle/node_modules/skia-canvas`. `--module` names the package directory, not its `.node` file. Install independently per OS; do not copy a Windows native binary to Linux. Source snapshots are references, not executable substitutes for A. Reuse working tools rather than reinstalling unnecessarily.

Check documentation/provenance first:

```shell
python scripts/validate_bootstrap.py
python scripts/validate_core.py
python scripts/validate_licenses.py
node scripts/inventory-public-api.mjs --check
node --test tests/contracts/api-ledger.test.mjs
```

Investigate failures before changing references/hashes. Do not regenerate them merely to make checks green. Use `refresh_reference_index.py` and ledger regeneration only for explicit source-change tasks, with diff review.

## 2. Locate behavior and preserve pre-change evidence

Use `rg` to follow the public name through facade → PyO3 → core → upstream mapping:

```shell
rg -n "fillRect|fill_rect" python crates/python crates/canvas-core crates/source-map.json
rg -n "fillRect|fill_rect" references/upstream
```

Reduce the issue to repeatable parameters, assignments, return/exception, drawing, and resources. Capture official A and the current wheel before editing. Text issues also require actual font file/face/glyph/fallback records. Public `engine` state alone does not prove a native drawing branch.

Tutorial fixture: [parity-smoke.json](../../../examples/development/parity-smoke.json). It contains two small scenes: fractional rectangle/pixel readback, and shared gradient/missing-argument behavior. Node and Python consume identical JSON. `$ref` identifies a test resource, `save` records a return value, and `observeError` records whether/how an error occurred without assuming one must occur. This protocol never enters production code.

## 3. Build and isolate the candidate wheel

Facade changes also change wheel bytes: repackage and test the new wheel. Do not replace source/native files after artifact acceptance.

Windows requires MSVC x64 tools and CPython 3.13. The script locates Visual Studio and prepares its environment:

```powershell
./scripts/build_windows.ps1
```

Keep the exact wheel filename from `dist/` and record its SHA immediately:

```powershell
Get-FileHash -Algorithm SHA256 dist/NEW_CANDIDATE.whl
py -3.13 -m venv C:\venvs\canvas-candidate
C:\venvs\canvas-candidate\Scripts\python.exe -m pip install --no-deps dist/NEW_CANDIDATE.whl
```

Replace `NEW_CANDIDATE.whl` with the real filename. Use an unused short venv prefix; deep prefixes can fail license installation without Windows long-path support. Version 0.1.0a18 is already published; a future release needs a new version, never different bytes uploaded under the old version.

For ordinary Linux development, a configured toolchain can run `maturin build --release --locked --interpreter python3.13 --out dist`, producing a local development artifact. Publishable manylinux wheels must use the pinned [container](../../../tools/manylinux.Dockerfile) and [build script](../../../scripts/build_manylinux.sh). Follow the [release workflow](../../RELEASE_WORKFLOW.md) for Rust/Cargo mounts and static Fontconfig. Renaming a system-library build does not establish manylinux acceptance.

Install the Linux candidate in isolation:

```shell
python3.13 -m venv /tmp/canvas-candidate
/tmp/canvas-candidate/bin/python -m pip install --no-deps /ABS/dist/NEW_CANDIDATE.whl
```

`--no-deps` here verifies a standalone wheel; runtime needs no Node/npm/Rust. Initial builds may compile Skia through the original mechanism; cache eligibility depends on pinned features/platform. Application users skip this build step entirely.

## 4. Windows: minimal GPU comparison

Run in PowerShell. Variables are local to this tutorial process and do not change system settings. Replace `$candidateWheel` and `$installedPython` with actual paths from the previous step.

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

Before running, check that no old `SKIA_CANVAS_STRICT` or GPU-blocking `VK_*` settings remain. Normal/STRICT and GPU/CPU runs use separate new output directories. `capture_environment --out` is a **JSON filename**; the other captures' `--out` is a fresh directory.

## 5. Linux: the same minimal GPU comparison

Run inside Linux/WSL with Linux path syntax. Recapture the platform's font manifest:

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

Python capture requires an external working directory, empty PATH, and isolated mode. It verifies imports from the installed environment, exact package bytes against the wheel, and native dependencies. It never silently switches to source or Node. `MATCHED_RECORDS` means these two scenes match exactly, not that full API release acceptance is complete.

## 6. Normal, STRICT, CPU, and wider coverage

Unset `SKIA_CANVAS_STRICT` for normal runs. For STRICT, set `SKIA_CANVAS_STRICT=1` in both new Node/Python processes, with fresh output directories. Invalid-argument changes need both modes.

CPU diagnostics can use a `cpu-setter` fixture, or disable drivers in an isolated process and require actual CPU fallback. The two default scenes above were accepted using the latter:

```text
Windows child process:
VK_DRIVER_FILES=C:/nonexistent-skia-driver.json
VK_ICD_FILENAMES=C:/nonexistent-skia-driver.json
VK_LOADER_DRIVERS_DISABLE=*

Linux child process:
VK_DRIVER_FILES=/nonexistent-skia-driver.json
VK_ICD_FILENAMES=/nonexistent-skia-driver.json
VK_LOADER_DRIVERS_DISABLE=*

Node capture: --require-cpu
Python capture: --backend cpu
```

Driver blocking is child-process-only and changes neither installed drivers nor system defaults. It is not equivalent to having no Vulkan library; verify that separately in a genuinely library-less environment. CPU results never replace default GPU requirements. Full CPU matrix configuration/commands are in [tests/cpu](../../../tests/cpu/README.md).

Add relevant `tests/fixtures` scenes, export comparisons, lifecycle tests, and font/native observations based on impact. Common entry points:

```shell
python scripts/capture_exports.py --help
python scripts/compare_exports.py --help
python scripts/audit_draw_sources.py --help
python scripts/trace_python_gpu.py --help
python scripts/run_cpu_matrix.py --help
```

Read actual arguments, then create new runs without omitting required resources. Independent assertions should detect real errors/boundaries rather than merely mirror code or check object existence.

## 7. Finish the batch

Review `git diff` for unintended changes to native logic, snapshots, defaults, or user edits. Document full new-function contracts, source mapping, and coverage. Report actual status names, platforms/backends, and wheel SHA. Separate unexecuted/missing-resource checks and accepted limitations. Before release, continue with [testing and release acceptance](TESTING_AND_RELEASE.en.md).
