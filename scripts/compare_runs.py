"""Exact evidence comparator. Matching records never proves full implementation parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def json_differences(left, right, location: str = "$") -> list[str]:
    """Compare JSON values exactly; booleans are not numbers; tagged -0 stays distinct."""
    numeric = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    if numeric(left) and numeric(right):
        if not math.isfinite(left) or not math.isfinite(right):
            return [f"{location}: untagged non-finite number"]
        if any(isinstance(value, float) and value == 0 and math.copysign(1, value) < 0 for value in (left, right)):
            return [f"{location}: untagged negative zero"]
        return [] if left == right else [f"{location}: {left!r} != {right!r}"]
    if type(left) is not type(right):
        return [f"{location}: type {type(left).__name__} != {type(right).__name__}"]
    if isinstance(left, dict):
        differences = []
        for key in sorted(left.keys() | right.keys()):
            if key not in left or key not in right:
                differences.append(f"{location}.{key}: missing key")
            else:
                differences.extend(json_differences(left[key], right[key], f"{location}.{key}"))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{location}: length {len(left)} != {len(right)}"]
        return [difference for i, (a, b) in enumerate(zip(left, right))
                for difference in json_differences(a, b, f"{location}[{i}]")]
    return [] if left == right else [f"{location}: {left!r} != {right!r}"]


def rgba_difference(left: bytes, right: bytes, width: int, height: int) -> dict:
    """Count every changed channel/pixel, including RGB under alpha zero; no tolerance."""
    if len(left) != width * height * 4 or len(right) != len(left):
        raise ValueError("RGBA byte length does not match dimensions")
    changed_pixels = changed_channels = maximum = 0
    for offset in range(0, len(left), 4):
        changed = False
        for channel in range(4):
            difference = abs(left[offset + channel] - right[offset + channel])
            if difference:
                changed = True
                changed_channels += 1
                maximum = max(maximum, difference)
        changed_pixels += changed
    return {"changedPixels": changed_pixels, "changedChannels": changed_channels, "maxChannelDelta": maximum}


def read_artifact(directory: Path, descriptor: dict) -> bytes:
    """Read a run-local artifact and verify its saved length/hash before comparison."""
    path = (directory / descriptor["path"]).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError("Artifact escapes run directory")
    data = path.read_bytes()
    if len(data) != descriptor["bytes"] or hashlib.sha256(data).hexdigest() != descriptor["sha256"]:
        raise ValueError(f"Artifact integrity mismatch: {path.name}")
    return data


def decoded_png(data: bytes) -> tuple[tuple[int, int], bytes]:
    """Decode RGBA without resizing or applying gamma/ICC transforms (Pillow dev dependency)."""
    import io
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG":
            raise ValueError("Expected PNG artifact")
        image.load()
        return image.size, image.convert("RGBA").tobytes()


def compare_runs(left_dir: Path, right_dir: Path) -> dict:
    """Compare scoped records, backend declarations and both readback/PNG pixels."""
    left, right = [json.loads((p / "run.json").read_text(encoding="utf-8")) for p in (left_dir, right_dir)]
    issues = []
    for report in (left, right):
        if report.get("schema") != "py-skia-canvas-test-run/v1":
            raise ValueError("Unsupported run schema")
        if report.get("status") not in ("ORACLE_CAPTURED", "CANDIDATE_CAPTURED"):
            issues.append("Run is not completely captured")
    for directory, report in ((left_dir, left), (right_dir, right)):
        manifest = report.get("environment", {}).get("manifest")
        if manifest is not None:
            read_artifact(directory, manifest)
    if left["fixtureSha256"] != right["fixtureSha256"]:
        issues.append("Fixture hashes differ")
    for field in ("platform", "arch", "release", "host", "fontFamiliesSha256", "strict",
                  "fontFilesVerified", "fontResourcesSha256"):
        if left["environment"].get(field) != right["environment"].get(field):
            issues.append(f"Environment differs: {field}")
    groups = []
    for report in (left, right):
        mapping = {}
        for case in report["cases"]:
            if case["id"] in mapping:
                raise ValueError(f"Duplicate run case: {case['id']}")
            mapping[case["id"]] = case
        groups.append(mapping)
    first, second = groups
    if first.keys() != second.keys() or not first:
        issues.append("Case sets differ or are empty")
    results = []
    for case_id in sorted(first.keys() & second.keys()):
        a, b = first[case_id], second[case_id]
        entry = {"id": case_id, "differences": []}
        results.append(entry)
        if a.get("status") != "CAPTURED" or b.get("status") != "CAPTURED":
            entry["differences"].append("Case not captured")
            continue
        for field in ("mode", "width", "height", "pixelFormat", "backend", "fontPolicy", "observations", "artifactDimensions"):
            entry["differences"].extend(json_differences(a.get(field), b.get(field), f"$.{field}"))
        if (a["width"], a["height"]) != (b["width"], b["height"]):
            continue
        for kind in ("rgba", "png"):
            dimensions=tuple(a.get('artifactDimensions',{}).get(kind,(a['width'],a['height'])))
            x, y = [read_artifact(p, case["artifacts"][kind]) for p, case in ((left_dir, a), (right_dir, b))]
            if kind == "png":
                (size_a, x), (size_b, y) = decoded_png(x), decoded_png(y)
                if size_a != size_b or size_a != dimensions:
                    entry["differences"].append("PNG dimensions differ from run metadata")
                    continue
            metrics = rgba_difference(x, y, *dimensions)
            entry[kind] = metrics
            if metrics["changedPixels"]:
                entry["differences"].append(f"{kind}: {metrics['changedPixels']} changed pixels")
    matched = not issues and all(not item["differences"] for item in results)
    return {"schema": "py-skia-canvas-record-comparison/v1", "status": "MATCHED_RECORDS" if matched else "DIFFERENT_OR_INCOMPLETE",
            "issues": issues, "cases": results,
            "limitations": ["Scoped record equivalence only; not full API/Python/GPU certification.",
                            "Font file provenance, actual native trace and PNG metadata semantics require separate checks."]}


def main() -> None:
    """Write a new comparison JSON, refusing to overwrite existing evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out already exists; evidence must not be overwritten")
    result = compare_runs(args.left, args.right)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]), "report": str(args.out)}))
    raise SystemExit(0 if result["status"] == "MATCHED_RECORDS" else 1)


if __name__ == "__main__":
    main()
