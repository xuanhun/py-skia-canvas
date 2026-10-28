"""Capture the explicit Linux Rust core probe without a Node executable on PATH."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def descriptor(path: Path, base: Path) -> dict:
    """Return owned run-relative byte-count/SHA metadata; propagate I/O errors, no native objects."""
    data = path.read_bytes()
    return {"path": path.relative_to(base).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def encode_numbers(value):
    """Tag original -0/non-finite JSON floats like the Node harness; no numeric tolerance or rounding."""
    if isinstance(value, float):
        if math.isnan(value):
            return {"$number": "NaN"}
        if math.isinf(value):
            return {"$number": "Infinity" if value > 0 else "-Infinity"}
        if value == 0 and math.copysign(1, value) < 0:
            return {"$number": "-0"}
    if isinstance(value, list):
        return [encode_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: encode_numbers(item) for key, item in value.items()}
    return value


def verify_environment(path: Path) -> tuple[bytes, dict]:
    """Verify all original font/config bytes and canonical fingerprint; no font bytes are copied.

    Input path is explicit, sizes are bytes. Returns owned metadata or raises on
    changed/missing resources. Synchronous test helper, not a rendering runtime.
    """
    data = path.read_bytes()
    document = json.loads(data)
    if document.get("schema") != "py-skia-canvas-environment/v1" or not document.get("fontFiles"):
        raise ValueError("Invalid or empty font environment manifest")
    for item in document["fontFiles"] + document["fontConfiguration"]:
        content = Path(item["path"]).read_bytes()
        if len(content) != item["bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ValueError(f"Font/config resource changed: {item['path']}")
    canonical = json.dumps({"fonts": document["fontFiles"], "configuration": document["fontConfiguration"]},
                           sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode()).hexdigest() != document["fontResourcesSha256"]:
        raise ValueError("Font/config manifest fingerprint mismatch")
    return data, document


def main() -> None:
    """Run an explicit executable into fresh evidence; fail if no GPU/output or any dependency check fails.

    Linux-only development check. The probe owns/drops all native objects on its
    main thread; this helper never imports a renderer, Node, Neon or skia-python.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        parser.error("This probe currently validates Linux x86_64 only; other targets require their own executable/dependency checks")
    executable = args.executable.resolve(strict=True)
    output = args.out.resolve()
    runs = (ROOT / "test-runs").resolve()
    if not runs.is_relative_to(ROOT.resolve()) or not output.is_relative_to(runs) or output == runs or output.exists():
        parser.error("--out must be a new directory below this project's test-runs")
    font_bytes, fonts = verify_environment(args.environment.resolve(strict=True))
    environment = os.environ.copy()
    environment["PATH"] = ""
    environment.pop("SKIA_CANVAS_STRICT", None)
    if shutil.which("node", path=environment["PATH"]) is not None:
        parser.error("Node must not be discoverable on the probe PATH")
    command = [str(executable), str(output)]
    result = subprocess.run(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output.mkdir(parents=True, exist_ok=True)  # Preserve failed captures too; no existing evidence was accepted above.
    with (output / "process.log").open("xb") as log:
        log.write(result.stdout)
    if result.returncode:
        with (output / "run.json").open("x", encoding="utf-8") as stream:
            json.dump({"status": "INCOMPLETE", "argv": command, "exitCode": result.returncode}, stream, indent=2)
        raise SystemExit(result.returncode)
    linkage = subprocess.run(["/usr/bin/ldd", str(executable)], check=True, capture_output=True)
    with (output / "linkage.log").open("xb") as stream:
        stream.write(linkage.stdout)
    if b"libnode" in linkage.stdout.lower() or b"neon" in linkage.stdout.lower():
        raise ValueError("Node/Neon dependency present in the core executable")
    document = json.loads((output / "core.json").read_text(encoding="utf-8"))
    if document.get("schema") != "py-skia-canvas-core-probe/v1" or document["backend"]["gpu"] is not True or document["backend"]["engine"]["renderer"] != "GPU":
        raise ValueError("GPU required; Rust probe did not confirm the original GPU engine")
    with (output / "environment.json").open("xb") as stream:
        stream.write(font_bytes)
    fixture = ROOT / "tests/fixtures/core-smoke.json"
    font_names = sorted(document["fontFamilies"], key=lambda name: name.encode("utf-16-be", errors="surrogatepass"))
    font_names_json = json.dumps(font_names, ensure_ascii=False, separators=(",", ":")).encode()
    report = {
        "schema": "py-skia-canvas-test-run/v1", "role": "rust-core-candidate", "status": "CANDIDATE_CAPTURED",
        "fixtureSha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "implementation": {"name": "canvas-core", "version": "0.1.0", "executableSha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                           "nativePath": document["nativePath"]},
        "inputs": {"argv": command, "runtimePathEmpty": True, "exitCode": result.returncode,
                   "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "environment": {"platform": "linux", "arch": "x64", "release": platform.release(), "host": platform.node(),
                        "node": None, "strict": None, "fontFamiliesSha256": hashlib.sha256(font_names_json).hexdigest(),
                        "fontFilesVerified": True, "fontResourcesSha256": fonts["fontResourcesSha256"],
                        "manifest": descriptor(output / "environment.json", output)},
        "limitations": document["limitations"] + ["Linux software Vulkan baseline only; native queue trace and per-glyph fallback audit remain pending."],
        "cases": [{"id": "core-gpu-smoke", "group": "core-gpu-probe", "mode": "default", "status": "CAPTURED",
                   "width": document["width"], "height": document["height"], "pixelFormat": "RGBA8-unpremultiplied-readback",
                   "backend": encode_numbers(document["backend"]), "fontPolicy": "system-unpinned",
                   "observations": encode_numbers(document["observations"]),
                   "artifacts": {"rgba": descriptor(output / "core-gpu-smoke.rgba", output),
                                 "png": descriptor(output / "core-gpu-smoke.png", output)}}],
    }
    with (output / "run.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "role": report["role"], "runtimePathEmpty": True, "run": str(output / "run.json")}))


if __name__ == "__main__":
    main()
