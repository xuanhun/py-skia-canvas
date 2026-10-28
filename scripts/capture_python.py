"""Capture real installed-wheel outputs against shared fixtures. No renderer fallback."""
from __future__ import annotations
import argparse
import asyncio,inspect
from array import array
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # Explicit development helper under python -I.
from capture_core_probe import descriptor, encode_numbers, verify_environment

ROOT = Path(__file__).resolve().parents[1]


def observation(value):
    """Serialize complete metrics/readback data like Node; no numeric/pixel adjustment or ownership."""
    from py_skia_canvas import undefined
    if value is undefined:
        return {"$undefined": True}
    if type(value).__name__ == "DOMMatrix":
        value = {k:getattr(value,k) for k in ("a","b","c","d","e","f","is2D","isIdentity")}
    elif type(value).__name__ in {"DOMPoint", "DOMRect"}:
        keys = ("x","y","z","w") if type(value).__name__ == "DOMPoint" else ("x","y","width","height")
        value = {k:getattr(value,k) for k in keys}
    elif isinstance(value, array):
        value = list(value)
    elif hasattr(value, "_values"):
        value = dict(value._values)
    elif all(hasattr(value, key) for key in ("data", "width", "height")):
        value = {"data": list(value.data), "width": value.width, "height": value.height}
    elif isinstance(value, (bytes, bytearray)):
        value = list(value)
    if isinstance(value, dict):
        return {key:observation(item) for key,item in value.items()}
    if isinstance(value, (list,tuple)):
        return [observation(item) for item in value]
    return encode_numbers(value)


def decode(value, resources):
    """Resolve fixture-only resource references/numeric tags; no production rendering or fallback."""
    if isinstance(value, list):
        return [decode(v, resources) for v in value]
    if isinstance(value, dict):
        if '$bytes' in value:return bytes(value['$bytes'])
        if '$clamped' in value:
            from py_skia_canvas._imagery import _Pixels
            data=_Pixels(len(value['$clamped']));data.set([decode(x,resources) for x in value['$clamped']]);return data
        if '$assetBytes' in value:
            path=(ROOT/'tests/assets'/value['$assetBytes']).resolve()
            if not path.is_relative_to((ROOT/'tests/assets').resolve()):raise ValueError('Asset escape')
            return path.read_bytes()
        if "$ref" in value:
            return resources[value["$ref"]]
        if "$undefined" in value:
            from py_skia_canvas import undefined
            return undefined
        if "$number" in value:
            return {"NaN":float("nan"),"Infinity":float("inf"),"-Infinity":-float("inf"),"-0":-0.0}[value["$number"]]
        return {k:decode(v, resources) for k,v in value.items()}
    return value


def main():
    """Capture typed initial Python API; output/source paths have no units, failures remain evidence.

    Requires an installed wheel, empty PATH, no Node executable, same font/config bytes,
    and supported Windows/Linux x86-64. Each Canvas stays on its calling owner thread.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument('--backend', choices=('gpu','cpu'), default='gpu', help='Required actual rendering profile; default GPU gate is retained')
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() or not output.is_relative_to((ROOT / "test-runs").resolve()) or output == ROOT / "test-runs":
        parser.error("--out must be a fresh directory under test-runs")
    if platform.system() not in ("Linux", "Windows") or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("Installed-wheel capture validates Windows/Linux x86-64 only")
    if os.environ.get("PATH") or shutil.which("node") is not None:
        parser.error("Installed-wheel capture requires empty PATH and no discoverable Node")
    if Path.cwd().resolve().is_relative_to(ROOT):
        parser.error("Run installed-wheel capture with working directory outside the workspace")
    environment_bytes, fonts = verify_environment(args.environment.resolve(strict=True))
    import py_skia_canvas as api
    from py_skia_canvas import _native
    for module in (api, _native):
        if not Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):
            raise ValueError("Python implementation must come from the isolated environment's installed wheel")
    with zipfile.ZipFile(args.wheel) as wheel:
        members = wheel.namelist()
        for member in members:
            if member.startswith("py_skia_canvas/") and not member.endswith("/"):
                installed = Path(api.__file__).parent.parent / member
                if installed.read_bytes() != wheel.read(member):
                    raise ValueError(f"Installed bytes differ from tested wheel: {member}")
        if any(name.endswith(".node") or "node_modules/" in name or "/references/" in name for name in members):
            raise ValueError("Development Node/reference payload found in wheel")
    if platform.system() == 'Windows':
        from inspect_pe_imports import imports
        linkage = json.dumps({'peImports': imports(_native.__file__)}, indent=2).encode()
    else:
        linkage = subprocess.run(["/usr/bin/ldd", _native.__file__], check=True, capture_output=True).stdout
    if any(token in linkage.lower() for token in (b"libnode", b"neon", b".local", b"/mnt/c/code")):
        raise ValueError("Forbidden runtime dependency in Python extension")
    fixture_bytes = args.fixtures.read_bytes()
    fixtures = json.loads(fixture_bytes)
    output.mkdir(parents=True)
    (output / "environment.json").write_bytes(environment_bytes)
    (output / "linkage.log").write_bytes(linkage)
    font_names = sorted(_native._font_families(), key=lambda name: name.encode("utf-16-be", "surrogatepass"))
    report = {
        "schema": "py-skia-canvas-test-run/v1", "role": "python-wheel-candidate", "status": "INCOMPLETE",
        "fixtureSha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "implementation": {"name": "py-skia-canvas", "version": importlib.metadata.version("py-skia-canvas"),
                           "packagePath": api.__file__, "nativePath": _native.__file__,
                           "wheelSha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                           "nativeSha256": hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest()},
        "inputs": {"argv": sys.argv, "cwd": str(Path.cwd()), "runtimePathEmpty": True, "installedBytesMatchWheel": True,
                   "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "environment": {"platform": "win32" if platform.system() == "Windows" else "linux", "arch": "x64", "host": platform.node(), "release": '.'.join(map(str, sys.getwindowsversion()[:3])) if platform.system() == 'Windows' else platform.release(),
                        "python": platform.python_version(), "node": None, "strict": os.environ.get('SKIA_CANVAS_STRICT'),
                        "fontFamiliesSha256": hashlib.sha256(json.dumps(font_names, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
                        "fontFilesVerified": True, "fontResourcesSha256": fonts["fontResourcesSha256"],
                        "manifest": descriptor(output / "environment.json", output)},
        "limitations": ["Initial typed Python API scope only; complete JS coercion/CSS font/async/API coverage remains pending",
                        "Public GPU labels require separate native surface/queue evidence; release acceptance recorded separately"], "cases": [],
    }
    for case in fixtures["cases"]:
        entry = {key: case[key] for key in ("id", "group", "mode")}
        entry.update(status="INCOMPLETE", observations={})
        report["cases"].append(entry)
        try:
            if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in case["id"]) or not case["id"]:
                raise ValueError("Unsafe fixture case ID")
            canvas = api.Canvas(case["width"], case["height"], {"gpu": False} if case["mode"] == "constructor-false" else {})
            if case["mode"] == "cpu-setter":
                canvas.gpu = False
            ctx = canvas.getContext("2d")
            if args.backend == 'cpu':ctx._native.audit_surface_capture(True)
            resources = {"canvas": canvas, "ctx": ctx, "fontLibrary": api.FontLibrary, **{k:getattr(api,k) for k in ("DOMMatrix", "DOMPoint", "DOMRect","Path2D")}}
            for op in case["ops"]:
                if 'ifRef' in op and op['ifRef'] not in resources:continue
                target = resources[op["target"]] if "target" in op else None
                try:
                    if op["op"] == "set":
                        if isinstance(target, dict):
                            target[op["name"]] = decode(op["value"], resources)
                        else:
                            setattr(target, op["name"], decode(op["value"], resources))
                        value = None
                    elif op["op"] == "get":
                        key=op["name"]
                        if isinstance(target,dict):value=target.get(key,api.undefined)
                        elif isinstance(target,(list,tuple,bytes,bytearray)):
                            value=len(target) if key=='length' else target[int(key)] if key.isdecimal() and int(key)<len(target) else api.undefined
                        else:value=getattr(target,key,api.undefined)
                    elif op["op"] == "delete":
                        if isinstance(target,dict):target.pop(op["name"],None)
                        else:delattr(target,op["name"])
                        value=True
                    elif op["op"] == "call":
                        value = getattr(target, op["name"])(*decode(op.get("args", []), resources))
                        if inspect.isawaitable(value):value=asyncio.run(value)
                    elif op["op"] == "construct" and op["class"] in {"Path2D", "Canvas", "CanvasRenderingContext2D", "CanvasGradient", "DOMMatrix", "DOMPoint", "DOMRect", "TextMetrics", "Image", "ImageData", "CanvasPattern", "CanvasTexture"}:
                        value = getattr(api, op["class"])(*decode(op.get("args", []), resources))
                    elif op['op']=='loadImage':
                        path=(ROOT/op['path']).resolve()
                        if not path.is_relative_to((ROOT/'tests/assets').resolve()):raise ValueError('Asset escape')
                        value=asyncio.run(api.loadImage(str(path)))
                    elif op['op']=='setPixels':
                        target.data.set(op['values']);value=None
                    elif op["op"] == "sameRef":
                        left, right = decode(op["left"], resources), decode(op["right"], resources)
                        if isinstance(left, (str, bool, int, float)) or isinstance(right, (str, bool, int, float)):
                            raise ValueError("sameRef expects objects or null")
                        value = left is right
                    else:
                        raise NotImplementedError(f"Initial Python runner operation: {op['op']}")
                except Exception as error:
                    if "observeError" not in op:
                        raise
                    entry["observations"][op["observeError"]] = {"threw": True, "type": type(error).__name__, "message": str(error)}
                    continue
                if "observeError" in op:
                    entry["observations"][op["observeError"]] = {"threw": False}
                if "id" in op:
                    if op["id"] in resources:
                        raise ValueError("Duplicate fixture resource")
                    resources[op["id"]] = value
                if "save" in op:
                    entry["observations"][op["save"]] = observation(value)
            width, height = canvas.width, canvas.height
            rgba = bytes(ctx.getImageData(0, 0, width, height).data)
            png = canvas.toBufferSync("png")
            if width%1 or height%1:
                import math,struct
                entry['artifactDimensions']={'rgba':[math.floor(width),math.floor(height)],'png':list(struct.unpack('>II',png[16:24]))}
            if args.backend == 'cpu':
                audit=json.loads(ctx._native.audit_surface_capture(False));entry['nativeSurfaceAudit']=audit
                if canvas.gpu or canvas.engine['renderer']!='CPU' or audit['surfaces']:
                    raise RuntimeError('CPU required; GPU rendering was observed')
            if args.backend == 'gpu' and case["mode"] == "default" and (not canvas.gpu or canvas.engine["renderer"] != "GPU"):
                raise RuntimeError("GPU required; Python did not select original GPU engine")
            entry.update(width=width, height=height, backend={"gpu": canvas.gpu, "engine": encode_numbers(canvas.engine), "evidence": "public-getters"},
                         fontPolicy=case.get("fontPolicy", "not-requested"), pixelFormat="RGBA8-unpremultiplied-readback", artifacts={})
            for kind, data in (("rgba", rgba), ("png", png)):
                path = output / f"{case['id']}.{kind}"
                with path.open("xb") as stream:
                    stream.write(data)
                entry["artifacts"][kind] = descriptor(path, output)
            entry["status"] = "CAPTURED"
        except Exception as error:
            entry["error"] = {"type": type(error).__name__, "message": str(error)}
    if all(case["status"] == "CAPTURED" for case in report["cases"]):
        report["status"] = "CANDIDATE_CAPTURED"
    with (output / "run.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]), "run": str(output / "run.json")}))
    raise SystemExit(0 if report["status"] == "CANDIDATE_CAPTURED" else 1)


if __name__ == "__main__":
    main()
