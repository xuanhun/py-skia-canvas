"""Record real shared-core Vulkan surface/Skia queue-submit stacks in an installed wheel."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hits(log, begin, end):
    """Count native breakpoint markers within one scene phase; no pixels/units or native ownership."""
    block = log.split(begin, 1)[1].split(end, 1)[0]
    return {"surfaces": block.count("NATIVE_VULKAN_SURFACE_HIT"), "submissions": block.count("NATIVE_VULKAN_QUEUE_SUBMIT_HIT")}


def main():
    """Launch GDB with the active installed CPython/wheel; preserve fresh evidence or fail.

    Linux-only development trace; GPU objects stay on the scene's main thread.
    Requested dimensions are scene inputs, not decoded from optimized native registers.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scene", choices=("core", "current-path", "path2d", "gradients", "dom-values", "matrix-ops", "projection", "font-library", "font-css", "text-state", "decoration", "metrics", "imaging", "effects", "exports", "contracts"), default="core")
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() or output == ROOT / "test-runs" or not output.is_relative_to((ROOT / "test-runs").resolve()):
        parser.error("Use a fresh directory under test-runs")
    if os.environ.get("PATH") or Path.cwd().is_relative_to(ROOT):
        parser.error("Run outside workspace with empty PATH")
    from py_skia_canvas import _native
    native = Path(_native.__file__).resolve()
    if not native.is_relative_to(Path(sys.prefix).resolve()):
        parser.error("Trace requires installed wheel in this interpreter environment")
    output.mkdir(parents=True)
    scene = {"core":"python_gpu_scene.py", "current-path":"python_current_path_scene.py", "path2d":"python_path2d_scene.py", "gradients":"python_gradient_scene.py", "dom-values":"python_dom_scene.py", "matrix-ops":"python_matrix_scene.py", "projection":"python_projection_scene.py", "font-library":"python_font_library_scene.py", "font-css":"python_font_css_scene.py", "text-state":"python_text_state_scene.py", "decoration":"python_decoration_scene.py", "metrics":"python_metrics_scene.py", "imaging":"python_imaging_scene.py", "effects":"python_effects_scene.py", "exports":"python_exports_scene.py", "contracts":"python_contracts_scene.py"}[args.scene]
    for source, name in ((ROOT / "tests/native" / scene, "scene.py"), (ROOT / "tests/native/gpu.gdb", "commands.gdb")):
        shutil.copyfile(source, output / name)
    command = ["/usr/bin/gdb", "-nx", "-batch", "-x", str(output / "commands.gdb"), "--args", sys.executable, "-I", str(output / "scene.py")]
    with (output / "trace.log").open("xb") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    log = (output / "trace.log").read_text(encoding="utf-8")
    readback = hits(log, "TRACE_REAL_READBACK_BEGIN", "TRACE_REAL_READBACK_END")
    png = hits(log, "TRACE_REAL_PNG_BEGIN", "TRACE_REAL_PNG_END")
    control = hits(log, "TRACE_FRESH_CPU_CONTROL_BEGIN", "TRACE_FRESH_CPU_CONTROL_END")
    passed = result.returncode == 0 and "exited normally" in log and all(h["surfaces"] > 0 and h["submissions"] > 0 for h in (readback, png)) and not any(control.values())
    with (output / "run.json").open("x", encoding="utf-8") as stream:
        json.dump({"status": "NATIVE_VULKAN_PATH_OBSERVED" if passed else "INCOMPLETE", "argv": command, "exitCode": result.returncode,
                   "nativeSha256": hashlib.sha256(native.read_bytes()).hexdigest(),
                   "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "inputs": {"cwd": str(Path.cwd()), "runtimePathEmpty": True, "requestedSize": [300, 150], "scene": args.scene,
                              "sceneSha256": hashlib.sha256((output / "scene.py").read_bytes()).hexdigest()},
                   "phases": {"readback": readback, "png": png, "freshCpuControl": control},
                   "traceSha256": hashlib.sha256((output / "trace.log").read_bytes()).hexdigest(),
                   "limitations": ["Breakpoint is at Skia Vulkan queue-submit method, not driver vkQueueSubmit entry",
                                   "Optimized symbols do not expose native surface dimensions; requested dimensions recorded separately",
                                   "Linux software Vulkan only; not Windows/hardware-GPU/Metal/full-release acceptance"]}, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": passed, "phases": {"readback": readback, "png": png, "freshCpuControl": control}}))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
