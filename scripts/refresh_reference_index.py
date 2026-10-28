"""Deterministically index the frozen public source snapshot, never during validation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "references/upstream/skia-canvas-3.0.8"
COMMIT = "042312a3f40b660b1d7dc0beba541486171bc5cc"


def source_path_key(path: Path) -> tuple:
    """Return a platform-independent key matching the frozen inventory order.

    Path components are compared case-insensitively, then by original spelling
    for ties. This retains the Windows-generated manifest order on Linux;
    file bytes/hashes are never normalized. No I/O, native objects or threads.
    Source: this project's metadata inventory, not an upstream draw algorithm.
    """
    return tuple(part.lower() for part in path.parts), path.parts


def build_indexes(root: Path = ROOT) -> tuple[dict, dict]:
    """Return source hashes and native export locations without modifying the snapshot."""
    snapshot = root / SNAPSHOT.relative_to(ROOT)
    files = []
    for path in sorted(snapshot.rglob("*"), key=source_path_key):
        if path.is_file():
            data = path.read_bytes()
            files.append({"path": path.relative_to(root).as_posix(),
                          "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    source = snapshot / "src/lib.rs"
    text = source.read_text(encoding="utf-8")
    native = []
    for match in re.finditer(r'cx\.export_function\("([^"]+)",\s*([^\)]+)\)', text):
        name, function = match.groups()
        native.append({"name": name, "rustFunction": function.strip(),
                       "group": name.split("_", 1)[0],
                       "source": source.relative_to(root).as_posix(),
                       "line": text.count("\n", 0, match.start()) + 1,
                       "status": "inventoried",
                       "feature": "window" if name.startswith(("App_", "Window_")) else None})
    entry = (snapshot / "lib/index.js").read_text(encoding="utf-8")
    block = re.search(r"module\.exports\s*=\s*\{([^}]+)\}", entry, re.S)
    if not block or not native:
        raise ValueError("Upstream entry point no longer matches the pinned index parser")
    public = [name.strip() for name in block.group(1).split(",") if name.strip()]
    manifest = {"schema": "py-skia-canvas-source-manifest/v1",
                "repository": "https://github.com/samizdatco/skia-canvas",
                "tag": "v3.0.8", "commit": COMMIT,
                "selection": "Rust/JS source, lockfiles, licenses and selected build references; no binaries",
                "files": files}
    index = {"schema": "py-skia-canvas-native-api-index/v1", "commit": COMMIT,
             "warning": "Native entry points are not the full public API. Audit JS wrappers and index.d.ts separately.",
             "publicExports": public, "nativeExports": native}
    return manifest, index


def main() -> None:
    """Explicitly regenerate both indexes; reviewers must inspect the resulting diff."""
    manifest, index = build_indexes()
    for name, data in (("source-manifest.json", manifest), ("native-api-index.json", index)):
        (ROOT / "references" / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(manifest['files'])} files and {len(index['nativeExports'])} native exports.")


if __name__ == "__main__":
    main()
