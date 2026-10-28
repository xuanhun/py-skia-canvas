"""Fingerprint local font/config resources without copying or redistributing font bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path: Path) -> dict:
    """Hash a local file in chunks; returns owned path/byte-count/SHA, propagating I/O errors.

    No font decoding, GPU objects or threads. Paths are absolute, sizes are bytes.
    Upstream counterpart: FontLibrary reads system font files; this is test evidence only.
    """
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while data := source.read(1024 * 1024):
            digest.update(data)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def capture() -> dict:
    """Inventory OS fonts/configs synchronously, raising on unavailable resources.

    Returns metadata only, never font bytes. Does not prove per-glyph fallback,
    licensing, Vulkan surface creation or Python parity. Linux uses fontconfig's
    visible file list; Windows includes machine and current-user font directories.
    """
    files, configs = set(), set()
    if platform.system() == "Windows":
        directories = [Path(os.environ["WINDIR"]) / "Fonts",
                       Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/Fonts"]
        for directory in directories:
            if directory.exists():
                files.update(p.resolve() for p in directory.rglob("*") if p.suffix.lower() in {".ttf", ".otf", ".ttc", ".otc"})
        policy = "Windows system and current-user font directories; external registered font paths not resolved"
        for name in ("dwrite.dll", "fontsub.dll"):
            path = Path(os.environ["WINDIR"]) / "System32" / name
            if path.exists():
                configs.add(path)
    else:
        result = subprocess.run(["fc-list", "--format=%{file}\\n"], check=True, capture_output=True, text=True)
        files.update(Path(name).resolve() for name in result.stdout.splitlines() if name)
        directory = Path("/etc/fonts")
        configs.update(p.resolve() for p in directory.rglob("*.conf") if p.is_file())
        policy = "fontconfig visible font file list and /etc/fonts configuration targets"
    if not files:
        raise ValueError("No font files found; resource acceptance is incomplete")
    fonts = [fingerprint(path) for path in sorted(files)]
    configuration = [fingerprint(path) for path in sorted(configs)]
    canonical = json.dumps({"fonts": fonts, "configuration": configuration}, sort_keys=True, separators=(",", ":"))
    return {"schema": "py-skia-canvas-environment/v1", "platform": platform.system(),
            "arch": platform.machine(), "fontFiles": fonts, "fontConfiguration": configuration,
            "fontResourcesSha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "fontPolicy": policy, "glyphFallbackVerified": False,
            "limitations": ["System fonts are fingerprinted, not copied; redistribution rights are not asserted.",
                            "Per-glyph fallback and externally registered Windows fonts remain unaudited.",
                            "No native Vulkan surface trace is supplied by this manifest."]}


def main() -> None:
    """Write a new run-local manifest; existing evidence or escaped paths are rejected."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    if not destination.is_relative_to((ROOT / "test-runs").resolve()):
        parser.error("--out must be inside this project's test-runs directory")
    if destination.exists():
        parser.error("--out already exists; evidence must not be overwritten")
    result = capture()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({"status": "FONT_FILES_FINGERPRINTED", "files": len(result["fontFiles"]),
                      "fontResourcesSha256": result["fontResourcesSha256"], "out": str(destination)}))


if __name__ == "__main__":
    main()
