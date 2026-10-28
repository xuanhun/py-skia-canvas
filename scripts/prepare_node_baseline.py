"""Stage an unmodified Node source rebuild; not a production core or Python runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from .refresh_reference_index import ROOT, SNAPSHOT, build_indexes
except ImportError:
    from refresh_reference_index import ROOT, SNAPSHOT, build_indexes


def prepare(destination: Path, root: Path = ROOT) -> dict:
    """Copy verified source bytes into a new development directory below .local.

    Paths have no units. Returns an owned source map; raises ValueError for an
    altered source/escape and FileExistsError for existing output. Synchronous,
    no native objects, threads or GPU contexts. Upstream: the frozen manifest.
    This pre-extraction rebuild intentionally retains Neon and all GUI code.
    """
    destination = destination.resolve()
    local = (root / ".local").resolve()
    if not local.is_relative_to(root.resolve()) or not destination.is_relative_to(local) or destination == local:
        raise ValueError("Node baseline must be strictly below this project's .local directory")
    manifest, _ = build_indexes(root)
    frozen = json.loads((root / "references/source-manifest.json").read_text(encoding="utf-8"))
    if manifest != frozen:
        raise ValueError("Upstream fingerprints changed; refusing to stage an unverified rebuild")
    destination.mkdir(parents=True, exist_ok=False)
    snapshot = root / SNAPSHOT.relative_to(ROOT)
    entries = []
    for entry in manifest["files"]:
        source = root / entry["path"]
        relative = source.relative_to(snapshot)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Source changed during staging: {entry['path']}")
        with target.open("xb") as output:
            output.write(data)
        entries.append({"source": entry["path"], "destination": relative.as_posix(), "sha256": entry["sha256"]})
    report = {"schema": "py-skia-canvas-source-map/v1", "commit": manifest["commit"],
              "purpose": "Unmodified pre-extraction Node rebuild, not canvas-core", "files": entries}
    with (destination / "source-map.json").open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    return report


def main() -> None:
    """Stage a new explicit development destination; errors fail the command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = prepare(args.out)
    print(json.dumps({"status": "SOURCE_STAGED", "files": len(report["files"]), "out": str(args.out),
                      "scope": "No build, extraction or parity verdict"}))


if __name__ == "__main__":
    main()
