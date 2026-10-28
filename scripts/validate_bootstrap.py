"""Validate starter documents/source inventory/fixtures, not a Python renderer."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from .refresh_reference_index import ROOT, build_indexes
except ImportError:
    from refresh_reference_index import ROOT, build_indexes

OPERATIONS = {"set", "get", "call", "construct", "loadImage", "setPixels", "sameRef", "delete"}
CONSTRUCTORS = {"CanvasRenderingContext2D", "Canvas", "Path2D", "DOMMatrix", "DOMPoint", "DOMRect", "ImageData", "CanvasGradient", "TextMetrics", "Image", "CanvasPattern", "CanvasTexture"}


def validate_fixtures(document: dict, root: Path = ROOT) -> list[str]:
    """Check test protocol shape, resource references and local asset containment."""
    errors = []
    if document.get("schema") != "py-skia-canvas-fixtures/v1":
        return ["Unsupported fixture schema"]
    seen = set()
    for case in document.get("cases", []):
        case_id = case.get("id", "")
        if not re.fullmatch(r"[a-z0-9-]+", case_id) or case_id in seen:
            errors.append(f"Invalid or duplicate case ID: {case_id}")
        seen.add(case_id)
        if case.get("mode") not in {"default", "cpu-setter", "constructor-false"}:
            errors.append(f"{case_id}: unknown mode")
        for key in ("width", "height"):
            value = case.get(key)
            if type(value) is not int or not 1 <= value <= 4096:
                errors.append(f"{case_id}: invalid {key}")
        if not case.get("group") or not case.get("ops"):
            errors.append(f"{case_id}: missing group or operations")
        resources, observations = {"canvas", "ctx", "fontLibrary", "DOMMatrix", "DOMPoint", "DOMRect","Path2D"}, set()

        def inspect(value):
            if isinstance(value, list):
                for item in value:
                    inspect(item)
            elif isinstance(value,dict) and '$assetBytes' in value:
                asset=(root/'tests/assets'/value['$assetBytes']).resolve()
                if not asset.is_relative_to((root/'tests/assets').resolve()) or not asset.is_file():errors.append(f'{case_id}: asset bytes must exist under tests/assets')
            elif isinstance(value, dict):
                if "$ref" in value and value["$ref"] not in resources:
                    errors.append(f"{case_id}: undeclared resource {value['$ref']}")
                if "$number" in value and value["$number"] not in {"NaN", "Infinity", "-Infinity", "-0"}:
                    errors.append(f"{case_id}: invalid number tag")
                for item in value.values():
                    inspect(item)

        for operation in case.get("ops", []):
            kind = operation.get("op")
            if kind not in OPERATIONS:
                errors.append(f"{case_id}: unknown operation {kind}")
            inspect(operation)
            if kind in {"set", "get", "call", "setPixels"} and operation.get("target") not in resources:
                errors.append(f"{case_id}: unknown target")
            if kind in {"set", "get", "call"} and not operation.get("name"):
                errors.append(f"{case_id}: missing method/property name")
            if "args" in operation and not isinstance(operation["args"], list):
                errors.append(f"{case_id}: args must be an array")
            if kind == "set" and "value" not in operation:
                errors.append(f"{case_id}: setter missing value")
            if kind == "sameRef" and not {"left", "right"} <= operation.keys():
                errors.append(f"{case_id}: sameRef missing operand")
            if kind == "construct" and operation.get("class") not in CONSTRUCTORS:
                errors.append(f"{case_id}: unapproved constructor")
            if kind == "loadImage":
                asset = (root / operation.get("path", "")).resolve()
                if not asset.is_relative_to((root / "tests/assets").resolve()) or not asset.is_file():
                    errors.append(f"{case_id}: image must exist under tests/assets")
            if kind == "setPixels":
                values = operation.get("values", [])
                if not values or any(type(v) is not int or not 0 <= v <= 255 for v in values):
                    errors.append(f"{case_id}: setPixels requires uint8 values")
            if "id" in operation:
                if operation["id"] in resources:
                    errors.append(f"{case_id}: duplicate resource {operation['id']}")
                resources.add(operation["id"])
            for key in ("save", "observeError"):
                if key in operation:
                    if operation[key] in observations:
                        errors.append(f"{case_id}: duplicate observation {operation[key]}")
                    observations.add(operation[key])
    if not seen:
        errors.append("Empty fixture set")
    return errors


def validate(root: Path = ROOT) -> dict:
    """Compare frozen fingerprints and check author-written local Markdown links."""
    errors = []
    expected_manifest, expected_api = build_indexes(root)
    for name, expected in (("source-manifest.json", expected_manifest), ("native-api-index.json", expected_api)):
        path = root / "references" / name
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != expected:
            errors.append(f"Source inventory mismatch: references/{name}; review, do not auto-regenerate")
    for entry in expected_manifest["files"]:
        path = Path(entry["path"])
        if path.suffix.lower() in {".dll", ".node", ".so", ".exe", ".ttf", ".otf", ".wasm"}:
            errors.append(f"Unexpected binary/font in reference snapshot: {path}")
    files = [root / "README.md", root / "AGENTS.md", root / "THIRD_PARTY_NOTICES.md"]
    files.extend((root / "docs").glob("*.md"))
    files.extend([root / "references/README.md", root / "references/history/README.md", root / "tests/README.md"])
    for path in files:
        if not path.is_file():
            errors.append(f"Missing document: {path.relative_to(root)}")
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not (path.parent / target).exists():
                errors.append(f"Broken link: {path.relative_to(root)} -> {target}")
    fixtures = json.loads((root / "tests/fixtures/scenarios.json").read_text(encoding="utf-8"))
    errors.extend(validate_fixtures(fixtures, root))
    for path in sorted((root / "tests/fixtures").glob("*.json")):
        if path.name=='events.json':
            events=json.loads(path.read_text(encoding='utf-8'));ids=[c.get('id') for c in events.get('cases',[])]
            if events.get('schema')!='py-skia-canvas-events/v1' or len(ids)!=len(set(ids)) or any(not isinstance(i,str) or not i.startswith('events-') for i in ids):errors.append('Invalid EventEmitter fixture')
            continue
        if path.name == "gui-cases.json":
            gui_fixture=json.loads(path.read_text(encoding="utf-8"));ids=[c["id"] for c in gui_fixture["cases"]]
            if gui_fixture.get('schema')!='py-skia-canvas-gui-cases/v1' or len(ids)!=len(set(ids)) or any(not re.fullmatch(r'gui-\d+',i) for i in ids):errors.append('Invalid GUI fixture')
            continue
        if path.name == "exports.json":
            export_fixture=json.loads(path.read_text(encoding="utf-8"))
            ids=[c["id"] for c in export_fixture["cases"]]
            if export_fixture.get("schema")!="py-skia-canvas-exports/v1" or len(ids)!=len(set(ids)) or any(not re.fullmatch(r"export-\d+",i) for i in ids):errors.append("Invalid exports fixture")
            continue
        if path.name != "scenarios.json":
            errors.extend(f"{path.name}: {error}" for error in validate_fixtures(json.loads(path.read_text(encoding="utf-8")), root))
    if not (root / "LICENSE").is_file():
        errors.append("Missing root license")
    return {"status": "BOOTSTRAP_VALIDATED" if not errors else "BOOTSTRAP_INVALID",
            "sourceFiles": len(expected_manifest["files"]), "nativeExports": len(expected_api["nativeExports"]),
            "publicExportNames": len(expected_api["publicExports"]), "starterCases": len(fixtures["cases"]),
            "errors": errors, "scope": "Source inventory, document links and test fixture structure only. No renderer/build/GPU/Python parity verdict."}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not result["errors"] else 1)
