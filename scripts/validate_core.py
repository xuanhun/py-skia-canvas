"""Check the first mechanical core extraction and retained upstream Node sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
if __package__:
    from .construction_extraction import core as construction_core,node as construction_node,arguments as argument_declarations
    from .gui_extraction import core_app as gui_core_app, node_app as gui_node_app, documented as gui_documented
    from .export_extraction import core_dispatch as export_dispatch, core_arguments as export_arguments, node_arguments as export_node_arguments, node_dispatch as export_node_dispatch, arguments_block as export_argument_block, dispatch_blocks as export_dispatch_blocks
    from .effects_extraction import core_operations as effects_core,node_operations as effects_node,core_arguments as effects_arguments,node_arguments as effects_node_arguments,definitions as effects_definitions,argument_definition as effects_argument_definition
    from .image_extraction import core_loading as image_loading,core_operations as image_operations,node_loading as node_image_loading,node_operations as node_image_operations
    from .decoration_extraction import definition as decoration_definition, core_module as decoration_core, node_module as decoration_node, node_reader as decoration_reader
    from .text_state_extraction import definitions as text_definitions, core_operations as text_core, node_operations as text_node, feature_data
    from .font_extraction import definition as font_definition, core_spec, node_spec
    from .validate_font_css import validate as validate_css
    from .font_library_extraction import load_definition, metadata_definition, core_loading, core_metadata, node_loading, node_metadata
    from .projection_extraction import projection as projection_fragment, number_string, node_number_string
    from .validate_matrix_math import validate as validate_math
    from .g4_extraction import blocks, core_operations, node_operations, wrap_paths
    from .path_extraction import definitions as path_definitions, core_operations as path_core, node_operations as path_node
else:
    from construction_extraction import core as construction_core,node as construction_node,arguments as argument_declarations
    from gui_extraction import core_app as gui_core_app, node_app as gui_node_app, documented as gui_documented
    from export_extraction import core_dispatch as export_dispatch, core_arguments as export_arguments, node_arguments as export_node_arguments, node_dispatch as export_node_dispatch, arguments_block as export_argument_block, dispatch_blocks as export_dispatch_blocks
    from effects_extraction import core_operations as effects_core,node_operations as effects_node,core_arguments as effects_arguments,node_arguments as effects_node_arguments,definitions as effects_definitions,argument_definition as effects_argument_definition
    from image_extraction import core_loading as image_loading,core_operations as image_operations,node_loading as node_image_loading,node_operations as node_image_operations
    from decoration_extraction import definition as decoration_definition, core_module as decoration_core, node_module as decoration_node, node_reader as decoration_reader
    from text_state_extraction import definitions as text_definitions, core_operations as text_core, node_operations as text_node, feature_data
    from font_extraction import definition as font_definition, core_spec, node_spec
    from validate_font_css import validate as validate_css
    from font_library_extraction import load_definition, metadata_definition, core_loading, core_metadata, node_loading, node_metadata
    from projection_extraction import projection as projection_fragment, number_string, node_number_string
    from validate_matrix_math import validate as validate_math
    from g4_extraction import blocks, core_operations, node_operations, wrap_paths
    from path_extraction import definitions as path_definitions, core_operations as path_core, node_operations as path_node

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path("references/upstream/skia-canvas-3.0.8")
ANGLE = "pub fn to_radians(degrees: f32) -> f32{\n  degrees / 180.0 * PI\n}\n"
ANGLE_FORWARD = "// The original implementation now lives in the unique language-neutral core.\n#[allow(unused_imports)] // Preserve the internal helper name while callers migrate.\npub use canvas_core::utils::to_radians;\n"
SHARED_HELPERS = ("to_radians", "to_degrees", "to_color_space", "to_color_type", "almost_equal", "almost_zero", "css_to_color", "to_matrix", "to_stroke_cap", "from_stroke_cap", "to_stroke_join", "from_stroke_join", "to_path_op", "to_filter_quality", "from_filter_quality", "to_repeat_mode", "to_blend_mode", "from_blend_mode", "to_1d_style", "from_1d_style")
PRESERVED = [
    *[("gradient.rs", name, 0, "canvas-core", 0) for name in ("get_stops", "get_colors", "add_stop", "shader", "add_color_stop", "is_opaque")],
    *[("texture.rs", name, 0, "canvas-core", 0) for name in ("default", "mix_into", "use_clip", "spacing", "to_color")],
    *[("pattern.rs", name, 0, "canvas-core", 0) for name in ("shader", "is_opaque")],
    ("image.rs", "default", 1, "canvas-core", 0),
    *[("image.rs", name, 0, "canvas-core", 0) for name in ("clone", "from_image_data", "size", "is_complete", "is_drawable", "snap_rects_to_bounds", "new", "image_info")],
    ("image.rs", "from_context", 0, "canvas-core", 0),
    *[("utils.rs", name, 0, "canvas-core", 0) for name in SHARED_HELPERS],
    *[("path.rs", name, 0, "canvas-core", 0) for name in ("default", "from", "scoot", "add_ellipse")],
]
PAGE_GPU_FILES = ("context/page.rs", "gpu/mod.rs", "gpu/vulkan/mod.rs", "gpu/vulkan/engine.rs", "gpu/vulkan/renderer.rs", "gpu/metal.rs")
# The frozen snapshot defines the complete function set for this mechanical move.
# Only the JS page-array argument reader remains in the Node adapter.
for _filename in PAGE_GPU_FILES:
    _source = (ROOT / UPSTREAM / "src" / _filename).read_text(encoding="utf-8")
    _counts = {}
    for _name in re.findall(r"(?m)^[ \t]*(?:pub )?fn (\w+)\b", _source):
        _index = _counts.get(_name, 0)
        _counts[_name] = _index + 1
        PRESERVED.append((_filename, _name, _index, "node" if _name == "pages_arg" else "canvas-core", _index))
PRESERVED=[entry for entry in PRESERVED if not(entry[0]=="gpu/vulkan/engine.rs" and entry[1] in {"status","with_context"})]
CONTEXT_FILES = ("context/mod.rs", "typography.rs", "font_library.rs", "canvas.rs")
TYPOGRAPHY_BINDINGS = {"font_arg", "font_features", "typeface_details", "decoration_arg", "opt_spacing_arg", "from_obj"}
for _filename in CONTEXT_FILES:
    _source = (ROOT / UPSTREAM / "src" / _filename).read_text(encoding="utf-8")
    _counts = {}
    for _name in re.findall(r"(?m)^[ \t]*(?:pub )?fn (\w+)\b", _source):
        _index = _counts.get(_name, 0)
        _counts[_name] = _index + 1
        if _filename == "context/mod.rs":
            if _name == "new" and _index == 1:
                continue  # Node-only Resource<T> unboxing is checked separately.
            _crate = "node" if _name == "value" else "canvas-core"
        elif _filename == "typography.rs":
            if _name in {"typeface_details", "font_arg", "decoration_arg"}:
                continue  # Controlled metadata/allocation split checked below.
            _crate = "node" if _name in TYPOGRAPHY_BINDINGS else "canvas-core"
        elif _filename == "font_library.rs":
            if _name in {"addFamily", "reset"}:
                continue  # Their original typed operations are split into core helpers.
            _crate = "node" if _name in {"get_families", "has", "family"} else "canvas-core"
        else:
            if _name not in {"new", "engine", "export_options"} or _name == "new" and _index > 0:
                continue
            _crate = "canvas-core"
        PRESERVED.append((_filename, _name, _index, _crate, _index))

GUI_FILES=('gui/window.rs','gui/window_mgr.rs','gui/event.rs','gui/app.rs')
for _filename in GUI_FILES:
    _source=(ROOT/UPSTREAM/'src'/_filename).read_text(encoding='utf-8');_counts={}
    for _name in re.findall(r'(?m)^[ \t]*(?:pub )?fn (\w+)\b',_source):
        _index=_counts.get(_name,0);_counts[_name]=_index+1
        if _filename=='gui/app.rs' and _name=='activate':continue
        _crate='node' if _filename=='gui/app.rs' and _name in {'register','dispatch_events'} else 'canvas-core'
        PRESERVED.append((_filename,_name,_index,_crate,_index))


def function_bodies(source: str, name: str) -> list[dict]:
    """Locate the selected ordinary Rust function bodies for exact source comparison.

    Returns owned text/line spans, skips trait declarations, and raises for
    unmatched braces. This is a narrow source guard, not a general Rust parser.
    Parameters are UTF-8-decoded source/name; no native objects or threading.
    """
    results = []
    pattern = r"(?m)^[ \t]*(?:pub )?fn " + re.escape(name) + r"\b"
    for match in re.finditer(pattern, source):
        opening = source.find("{", match.end())
        semicolon = source.find(";", match.end())
        if opening < 0 or 0 <= semicolon < opening:
            continue
        depth, end = 1, opening + 1
        while depth and end < len(source):
            # The selected bodies contain balanced format strings/comments; their
            # raw text is deliberately retained, including whitespace and comments.
            depth += (source[end] == "{") - (source[end] == "}")
            end += 1
        if depth:
            raise ValueError(f"Unbalanced selected function: {name}")
        results.append({"body": source[opening:end], "text": source[match.start():end] + "\n",
                        "line": source.count("\n", 0, match.start()) + 1})
    return results


def source_map(root: Path = ROOT) -> dict:
    """Fingerprint source/destination files without modifying them or invoking native code.

    Paths are repository relative, lengths are bytes. Returns owned metadata;
    I/O errors propagate. No threads/Skia objects. Source: frozen upstream manifest.
    """
    mappings = []
    sources = [p for p in (root / UPSTREAM).rglob("*") if p.is_file()]
    for source in sorted(sources):
        relative = source.relative_to(root / UPSTREAM)
        destination = root / "crates/node" / relative
        if destination.is_file():
            mode = {"src/filter.rs": "core-reexport", "src/utils.rs": "shared-helper-reexports",
                    "src/gradient.rs": "resource-adapter", "src/texture.rs": "resource-adapter",
                    "src/pattern.rs": "resource-adapter", "src/image.rs": "content-adapter",
                    "src/context/mod.rs": "context-dye-adapter", "src/context/api.rs": "context-boxing-adapter",
                    "src/canvas.rs": "canvas-boxing-adapter", "src/font_library.rs": "font-arguments-adapter",
                    "src/typography.rs": "typography-arguments-adapter",
                    "src/context/page.rs": "page-array-adapter", "src/gpu/mod.rs": "gpu-core-reexport",
                    "src/lib.rs": "resource-module-wiring",
                    "src/gui/app.rs":"gui-callback-adapter","src/gui/window.rs":"gui-core-reexport","src/gui/window_mgr.rs":"gui-core-reexport","src/gui/event.rs":"gui-core-reexport",
                    "src/path.rs": "path-core-adapter", "Cargo.toml": "manifest-wiring"}.get(relative.as_posix(), "retained-node-source")
            mappings.append((source, destination, mode))
    mappings.extend([(root / UPSTREAM / "src/filter.rs", root / "crates/canvas-core/src/filter.rs", "extracted-with-docs"),
                     (root / UPSTREAM / "src/utils.rs", root / "crates/canvas-core/src/utils.rs", "extracted-four-helpers"),
                     (root / UPSTREAM / "LICENSE", root / "crates/canvas-core/LICENSE", "license")])
    for filename in ("gradient.rs", "texture.rs", "pattern.rs", "image.rs"):
        mappings.append((root / UPSTREAM / "src" / filename, root / "crates/canvas-core/src" / filename, "extracted-core-resources"))
    for filename in PAGE_GPU_FILES:
        mappings.append((root / UPSTREAM / "src" / filename, root / "crates/canvas-core/src" / filename, "extracted-page-gpu"))
    for filename in GUI_FILES:
        mappings.append((root / UPSTREAM / "src" / filename, root / "crates/canvas-core/src" / filename, "extracted-gui-core"))
    for filename in CONTEXT_FILES:
        mappings.append((root / UPSTREAM / "src" / filename, root / "crates/canvas-core/src" / filename, "extracted-context-fonts"))
    mappings.append((root / UPSTREAM / "src/path.rs", root / "crates/canvas-core/src/path.rs", "extracted-path-primitives"))
    for filename in ("ieee754.cc", "ieee754.h", "overflowing-math.h", "LICENSE"):
        mappings.append((root / "references/math/node-v22.23.2" / filename,
                         root / "crates/python/vendor/v8" / (filename if filename == "LICENSE" else "src/base/" + filename),
                         "retained-language-math-source"))
    for source in sorted((root/'references/math/node-v22.23.2/numbers/src/base/numbers').iterdir()):
        mappings.append((source,root/'crates/python/vendor/v8-numbers/src/base/numbers'/source.name,'retained-language-math-source'))
    entries = []
    for source, destination, mode in mappings:
        entries.append({"source": source.relative_to(root).as_posix(), "destination": destination.relative_to(root).as_posix(),
                        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "destinationSha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "mode": mode})
    new_files = [{"path": name, "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
                 for name in ("crates/node/src/resource.rs", "crates/canvas-core/src/lib.rs", "crates/canvas-core/examples/core_gpu.rs", "crates/canvas-core/Cargo.toml", "Cargo.toml",
                              "crates/python/Cargo.toml", "crates/python/src/lib.rs", "crates/python/src/ownership.rs", "python/py_skia_canvas/__init__.py", "pyproject.toml",
                              "scripts/g4_extraction.py", "crates/canvas-core/src/context/operations.rs",
                              "scripts/path_extraction.py", "crates/canvas-core/src/path/operations.rs", "crates/python/src/path.rs", "python/py_skia_canvas/_path.py",
                              "crates/python/src/gradient.rs", "python/py_skia_canvas/_gradient.py", "python/py_skia_canvas/_geometry.py",
                              "python/py_skia_canvas/_matrix_ops.py", "python/py_skia_canvas/_transform.py", "crates/python/build.rs", "crates/python/src/dom_math.rs",
                              "crates/python/vendor/v8/wrapper.cpp", "crates/python/vendor/v8/src/base/macros.h", "crates/python/vendor/v8/src/base/build_config.h",
                              "crates/python/vendor/v8/src/base/base-export.h", "references/math/node-v22.23.2/source.json", "scripts/validate_matrix_math.py",
                              "scripts/projection_extraction.py", "crates/python/src/projection.rs",
                              "scripts/font_library_extraction.py", "crates/python/src/font_library.rs", "python/py_skia_canvas/_fonts.py",
                              "scripts/font_extraction.py", "crates/python/src/font.rs", "python/py_skia_canvas/_font_css.py",
                              "scripts/validate_font_css.py", "references/css/source.json",
                              "crates/python/vendor/css/LICENSE-parenthesis.txt", "crates/python/vendor/css/LICENSE-string-split-by.txt",
                              "references/css/string-split-by/index.js", "references/css/string-split-by/package.json", "references/css/string-split-by/readme.md",
                              "references/css/parenthesis/index.js", "references/css/parenthesis/package.json", "references/css/parenthesis/LICENSE",
                              "scripts/text_state_extraction.py", "crates/canvas-core/src/context/text_state.rs", "python/py_skia_canvas/_text_css_data.py",
                              "python/py_skia_canvas/_text_css.py", "python/py_skia_canvas/_text_state.py",
                              "scripts/decoration_extraction.py", "crates/canvas-core/src/typography/decoration.rs", "crates/python/src/decoration.rs",
                              "python/py_skia_canvas/_metrics.py", "python/py_skia_canvas/_text_api.py", "crates/canvas-core/src/typography/audit.rs",
                              "scripts/image_extraction.py","crates/canvas-core/src/image/loading.rs","crates/canvas-core/src/image/operations.rs",
                              "crates/python/src/imagery.rs","crates/python/src/shaders.rs","python/py_skia_canvas/_imagery.py","python/py_skia_canvas/_shaders.py",
                              "crates/canvas-core/src/gpu/audit.rs", "python/py_skia_canvas/_host.py", "python/py_skia_canvas/_http.py", "python/py_skia_canvas/_path_args.py",
                              "scripts/validate_number_source.py", "references/math/node-v22.23.2/numbers/source.json",
                              "scripts/construction_extraction.py","crates/canvas-core/src/canvas/construction.rs","crates/python/src/arguments.rs","python/py_skia_canvas/_arguments.py","python/py_skia_canvas/_argument_specs.py","python/py_skia_canvas/_canvas_api.py",
                              "scripts/gui_extraction.py","crates/canvas-core/src/gui/mod.rs","crates/python/src/gui.rs","python/py_skia_canvas/_gui.py","python/py_skia_canvas/_events.py",
                              "crates/canvas-core/src/gpu/vulkan/engine/initialization.rs","scripts/export_extraction.py","crates/canvas-core/src/canvas/exports.rs","crates/canvas-core/src/canvas/options.rs","crates/python/src/exports.rs","python/py_skia_canvas/_exports.py","crates/canvas-core/src/context/page/audit.rs",
                              "scripts/effects_extraction.py","crates/canvas-core/src/context/effects.rs","crates/canvas-core/src/filter/arguments.rs","crates/python/src/effects.rs","python/py_skia_canvas/_effects.py")]
    for p in sorted((root/'crates/python/vendor/v8-numbers').rglob('*')):
        if p.is_file() and '/src/base/numbers/' not in p.as_posix():new_files.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    for p in sorted((root/'references/math/node-v22.23.2/numbers').rglob('*')):
        if p.is_file() and '/src/base/numbers/' not in p.as_posix():new_files.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    for base in ('crates/skia-bindings','references/rust-skia-static'):
        for p in sorted((root/base).rglob('*')):
            if p.is_file() and p.relative_to(root/base).parts[0]!='skia':new_files.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    p=root/'scripts/validate_static_skia.py';new_files.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    p=root/'python/py_skia_canvas/_thread_lifetime.py';new_files.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    preserved = []
    for filename, name, original_index, crate, extracted_index in PRESERVED:
        if (filename=="typography.rs" and name=="layout") or (filename=="gpu/vulkan/engine.rs" and name=="surface"):continue
        original = function_bodies((root / UPSTREAM / "src" / filename).read_text(encoding="utf-8"), name)[original_index]
        migrated = function_bodies((root / "crates" / crate / "src" / filename).read_text(encoding="utf-8"), name)[extracted_index]
        preserved.append({"symbol": name, "source": f"src/{filename}:{original['line']}",
                          "destination": f"crates/{crate}/src/{filename}:{migrated['line']}",
                          "sourceBodySha256": hashlib.sha256(original["body"].encode()).hexdigest(),
                          "destinationBodySha256": hashlib.sha256(migrated["body"].encode()).hexdigest()})
    operations = blocks((root / UPSTREAM / "src/context/api.rs").read_text(encoding="utf-8"), function_bodies)
    fragments = [{"symbol": x["name"], "source": f"src/context/api.rs:{x['line']}", "destination": "crates/canvas-core/src/context/operations.rs",
                  "originalBlockSha256": hashlib.sha256(x["original"].encode()).hexdigest(),
                  "typedBlockSha256": hashlib.sha256(x["typed"].encode()).hexdigest(),
                  "changes": "Declared argument extraction and Neon error creation only; see scripts/g4_extraction.py"} for x in operations]
    paths = path_definitions((root / UPSTREAM / "src/path.rs").read_text(encoding="utf-8"), function_bodies)
    path_fragments = [{"symbol": x["name"], "source": f"src/path.rs:{x['line']}", "destination": "crates/canvas-core/src/path/operations.rs",
                      "sourceBlockSha256": hashlib.sha256(x["original"].encode()).hexdigest(), "typedBlockSha256": hashlib.sha256(x["typed"].encode()).hexdigest(),
                      "changes": "Declared argument/borrow/error/return allocation separation; see scripts/path_extraction.py"} for x in paths]
    return {"schema": "py-skia-canvas-core-source-map/v1", "commit": "042312a3f40b660b1d7dc0beba541486171bc5cc",
            "batch":"G0-G5-python-host",
            "staticFontconfigBuild":{"crate":"skia-bindings 0.88.0","source":"references/rust-skia-static/source.json","patch":"Original upstream static-fontconfig link order/system-link omission; Linux build-time prefix only","nativeVersionEvidence":"FcGetVersion=21701 in fixed official A"},
            "surfaceObservationFragment":{"source":"src/gpu/vulkan/engine.rs:surface","destination":"crates/canvas-core/src/gpu/vulkan/engine.rs:surface","changes":"Only inspect successful original non-null render_target result to record pixel dimensions in optional owner TLS diagnostics"},
            "layoutObservationFragment":{"source":"src/typography.rs:layout","destination":"crates/canvas-core/src/typography.rs:layout","changes":"Only optional owner-TLS same-Paragraph diagnostic observation before original return; original layout/paint/font decisions unchanged"}, "scope":"Original Canvas options and ordinary primitive float/count/bail boundary, independent direct Context constructor; all original draw/GUI functions retained",
            "constructionFragment":{"source":"src/canvas.rs:new","destination":"crates/canvas-core/src/canvas/construction.rs:construct","sourceBodySha256":hashlib.sha256(function_bodies((root/UPSTREAM/'src/canvas.rs').read_text(encoding='utf-8'),'new')[1]['body'].encode()).hexdigest(),"changes":"Typed field reader/error boxing separated, original SurfaceProps range/epsilon/gamma condition and order retained"},
            "guiLoopFragment":{"source":"src/gui/app.rs:activate inner channel callback","destination":"crates/canvas-core/src/gui/app.rs:activate","changes":"Neon channel/Promise scheduling remains Node adapter; same run_on_demand/pump_events branches and cadence, generic callback errors","sourceSha256":hashlib.sha256((root/UPSTREAM/'src/gui/app.rs').read_bytes()).hexdigest()},
            "initializationGuardFragments":[{"symbol":name,"source":"src/gpu/vulkan/engine.rs","destination":"crates/canvas-core/src/gpu/vulkan/engine.rs","sourceBodySha256":hashlib.sha256(function_bodies((root/UPSTREAM/'src/gpu/vulkan/engine.rs').read_text(encoding='utf-8'),name)[0]['body'].encode()).hexdigest(),"destinationBodySha256":hashlib.sha256(function_bodies((root/'crates/canvas-core/src/gpu/vulkan/engine.rs').read_text(encoding='utf-8'),name)[0]['body'].encode()).hexdigest(),"changes":"Only original VulkanContext::new call routed through initialization mutex; full original construction/selection/drawing bodies retained"} for name in ('status','with_context')],
            "exportFragments":[{"symbol":name,"source":"src/canvas.rs:"+symbol,"destination":"crates/canvas-core/src/canvas/exports.rs","sourceBlockSha256":hashlib.sha256(block.encode()).hexdigest()} for name,symbol,block in zip(("encode","write"),("toBufferSync/toBuffer","saveSync/save"),export_dispatch_blocks((root/UPSTREAM/'src/canvas.rs').read_text(encoding='utf-8'),function_bodies))]+[{"symbol":"export_options_arg","source":"src/utils.rs:export_options_arg","destination":"crates/canvas-core/src/canvas/options.rs","sourceBlockSha256":hashlib.sha256(export_argument_block((root/UPSTREAM/'src/utils.rs').read_text(encoding='utf-8'),function_bodies)['original'].encode()).hexdigest(),"typedBlockSha256":hashlib.sha256(export_argument_block((root/UPSTREAM/'src/utils.rs').read_text(encoding='utf-8'),function_bodies)['typed'].encode()).hexdigest()}],
            "effectsFragments":[{"symbol":d['name'],"source":f"src/context/api.rs:{d['line']}","destination":"crates/canvas-core/src/context/effects.rs","sourceBlockSha256":hashlib.sha256(d['original'].encode()).hexdigest(),"typedBlockSha256":hashlib.sha256(d['typed'].encode()).hexdigest()} for d in effects_definitions((root/UPSTREAM/'src/context/api.rs').read_text(encoding='utf-8'),function_bodies)],
            "diagnostics":{"source":"crates/canvas-core/src/typography/audit.rs","entry":"Typesetter::new/layout then original extended_visit","ownedValuesOnly":True,"temporaryTables":"head/name/cmap/OS2 hash transport; never persisted by runners","notRenderingPolicy":True},
            "decorationFragment": {"source":"src/typography.rs:509","destination":"crates/canvas-core/src/typography/decoration.rs",
                                   "sourceBlockSha256":hashlib.sha256(decoration_definition((root/UPSTREAM/'src/typography.rs').read_text(encoding='utf-8'),function_bodies)['original'].encode()).hexdigest(),
                                   "typedBlockSha256":hashlib.sha256(decoration_definition((root/UPSTREAM/'src/typography.rs').read_text(encoding='utf-8'),function_bodies)['typed'].encode()).hexdigest(),
                                   "changes":"Only string/optional-spacing field reads via typed reader; early return/validation/color/order/Through mode unchanged"},
            "textStateFragments": [{"symbol":x['name'],"source":"src/context/api.rs:"+str(x['line']),"destination":"crates/canvas-core/src/context/text_state.rs",
                                    "sourceBlockSha256":hashlib.sha256(x['original'].encode()).hexdigest(),"typedBlockSha256":hashlib.sha256(x['typed'].encode()).hexdigest(),
                                    "changes":"Only language reads/JS result allocation; original state statements and conversion order retained"}
                                   for x in text_definitions((root/UPSTREAM/'src/context/api.rs').read_text(encoding='utf-8'),function_bodies)],
            "fontSpecFragment": {"source":"src/typography.rs:285","destination":"crates/canvas-core/src/typography.rs:font_spec",
                                 "sourceBlockSha256":hashlib.sha256(font_definition((root/UPSTREAM/'src/typography.rs').read_text(encoding='utf-8'),function_bodies)['original'].encode()).hexdigest(),
                                 "typedBlockSha256":hashlib.sha256(font_definition((root/UPSTREAM/'src/typography.rs').read_text(encoding='utf-8'),function_bodies)['typed'].encode()).hexdigest(),
                                 "changes":"Only descriptor reads/JS result allocation separated; original enum casts, f32 line height ratio, empty-family guard retained"},
            "fontFragments": [{"symbol":item['name'],"source":file+':'+str(item['line']),"destination":"crates/canvas-core/src/font_library.rs",
                               "sourceBlockSha256":hashlib.sha256(item['original'].encode()).hexdigest(),
                               "typedBlockSha256":hashlib.sha256(item['typed'].encode()).hexdigest(),
                               "changes":"Original file read/decode and Typeface metadata; only JS allocation/error boundary separated"}
                              for item,file in [(load_definition((root/UPSTREAM/'src/font_library.rs').read_text(encoding='utf-8'),function_bodies),'src/font_library.rs'),
                                                (metadata_definition((root/UPSTREAM/'src/typography.rs').read_text(encoding='utf-8'),function_bodies),'src/typography.rs')]],
            "boundaryFragments": [{"symbol":item['name'],"source":file+':'+str(item['line']),"destination":destination,
                                    "sourceBlockSha256":hashlib.sha256(item['original'].encode()).hexdigest(),
                                    "typedBlockSha256":hashlib.sha256(item['typed'].encode()).hexdigest(),
                                    "changes":"Only language result/error allocation for projection; original numeric string branch retained verbatim"}
                                   for item,file,destination in [
                                    (projection_fragment((root/UPSTREAM/'src/context/api.rs').read_text(encoding='utf-8'),function_bodies),'src/context/api.rs','crates/canvas-core/src/context/operations.rs'),
                                    (number_string((root/UPSTREAM/'src/utils.rs').read_text(encoding='utf-8'),function_bodies),'src/utils.rs','crates/canvas-core/src/utils.rs')]],
            "languageAdapters": [{"source":"references/upstream/skia-canvas-3.0.8/lib/classes/typography.js:TextMetrics / context.js:toString/measureText",
                                  "destination":["python/py_skia_canvas/_metrics.py","python/py_skia_canvas/_text_api.py","python/py_skia_canvas/__init__.py"],
                                  "changes":"Shallow owned fields/readOnly initial keys, mutable child mappings, ordinary text coercion; original shared native number parsing/layout unchanged",
                                  "unbound":["Complete host/prototype/subclass contracts", "Other text-call parameter coercion"]},
                                 {"source":"references/upstream/skia-canvas-3.0.8/lib/classes/css.js:parseTextDecoration",
                                  "destination":["python/py_skia_canvas/_text_css.py","python/py_skia_canvas/_text_state.py"],
                                  "changes":"Original token priority/first whitespace replacement/typed descriptor, native shared color and validation rules unchanged",
                                  "unbound":["Complete host/subclass input contracts"]},
                                 {"source":"references/upstream/skia-canvas-3.0.8/lib/classes/css.js:parseFlexibleSize/parseStretch/parseVariant/featureMap/alternatesMap",
                                  "destination":["python/py_skia_canvas/_text_css.py","python/py_skia_canvas/_text_css_data.py","python/py_skia_canvas/_text_state.py"],
                                  "changes":"Original CSS value parser/tables/cache and ordinary JS truthiness, forward typed values to shared original core",
                                  "unbound":["Full host/proxy/custom prototype coercion"]},
                                 {"source":"references/upstream/skia-canvas-3.0.8/lib/classes/css.js:parseFont/parseSize/parseWeight",
                                  "destination":"python/py_skia_canvas/_font_css.py","changes":"Original language parser/cache and pinned splitter default algorithm port; no font selection/shaping algorithm",
                                  "tokenizerSources":"references/css/source.json","unbound":["Full host/prototype coercion", "other CSS typography setters"]},
                                 {"source":"references/upstream/skia-canvas-3.0.8/lib/classes/typography.js",
                                  "destination":"python/py_skia_canvas/_fonts.py", "symbols":["FontLibrary families/has/family/use/reset"],
                                  "changes":"Original signatures, filtered paths/undefined slots and mapping order; caller-thread core TLS, Python metadata snapshots",
                                  "unbound":["complete host/prototype coercion"]},
                                 {"source": "references/upstream/skia-canvas-3.0.8/lib/classes/geometry.js",
                                  "destination": ["python/py_skia_canvas/_geometry.py", "python/py_skia_canvas/_matrix_ops.py", "python/py_skia_canvas/_transform.py"],
                                  "symbols": ["DOMPoint", "DOMRect", "DOMMatrix values/operations/CSS/toString", "toSkMatrix", "fromSkMatrix"],
                                  "changes": "Numeric Python value facade port of original JS storage/defaults/formula order; array('f'/'d') typed arrays; no native rendering algorithms",
                                  "unbound": ["dump/inspect host console", "complete JS coercion"]},
                                 {"source": "references/math/node-v22.23.2/source.json", "destination": "crates/python/vendor/v8",
                                  "changes": "Original ieee754.cc/h and overflowing-math.h byte-identical, pure C ABI sin/cos/tan/atan2; no Node/V8 runtime; scalar language compatibility only"}],
            "functions": [
                {"source": "src/filter.rs", "symbols": ["LastFilter::match_scale", "Filter::default", "Filter::fmt", "Filter::new", "Filter::mix_into", "Filter::filters_for", "ImageFilter::sampling"],
                 "destination": "crates/canvas-core/src/filter.rs", "changes": "Documentation only; original bodies, symbols and imports retained"},
                {"source": "src/utils.rs:45", "symbols": ["to_radians"], "destination": "crates/canvas-core/src/utils.rs",
                 "changes": "Original function body retained; Node uses a re-export"}],
            "preservedBodies": preserved, "operationFragments": fragments, "pathFragments": path_fragments, "newFiles": new_files, "files": entries}


def validate(root: Path = ROOT) -> dict:
    """Verify file bytes, unchanged extracted bodies, and one implementation per migrated symbol.

    Returns errors as owned strings, no exception for ordinary mismatches. Filesystem
    failures propagate. Synchronous development check; no GPU/thread/ABI claims.
    """
    expected = json.loads((root / "crates/source-map.json").read_text(encoding="utf-8"))
    actual = source_map(root)
    errors = list(validate_math(root)["errors"]) + list(validate_css(root)["errors"])
    try:
        from .validate_number_source import validate as validate_numbers
    except ImportError:
        from validate_number_source import validate as validate_numbers
    errors += validate_numbers(root)
    try:
        from .validate_static_skia import validate as validate_static
    except ImportError:
        from validate_static_skia import validate as validate_static
    errors += validate_static(root)

    if expected != actual:
        errors.append("Source map differs; review the changed files instead of refreshing hashes automatically")
    for entry in actual["files"]:
        if entry["mode"] in {"retained-node-source", "license"} and entry["sourceSha256"] != entry["destinationSha256"]:
            errors.append(f"Unmigrated source changed: {entry['destination']}")
    original = (root / UPSTREAM / "src/filter.rs").read_text(encoding="utf-8")
    extracted = (root / "crates/canvas-core/src/filter.rs").read_text(encoding="utf-8")
    without_docs = "\n".join(line for line in extracted.splitlines() if not line.lstrip().startswith("///")) + "\n"
    if original+'\npub mod arguments;\n' != without_docs:
        errors.append("Filter extraction changed more than documentation")
    original_utils = (root / UPSTREAM / "src/utils.rs").read_text(encoding="utf-8")
    node_utils = (root / "crates/node/src/utils.rs").read_text(encoding="utf-8")
    expected_utils = original_utils.replace("use std::f32::consts::PI;\n", "").replace("use css_color::Rgba;\n", "").replace("Point, Color, RGB, Data", "Point, Color, Data")
    expected_utils = expected_utils.replace("use skia_safe::{PaintCap};\n", "").replace("use skia_safe::{PaintJoin};\n", "")
    expected_utils = expected_utils.replace("use skia_safe::{PathOp};\n", "")
    expected_utils = node_number_string(expected_utils,original_utils,function_bodies)
    color_format = function_bodies(original_utils, "color_to_css")[0]["body"]
    expected_utils = expected_utils.replace(color_format, '{\n  Ok(cx.string(canvas_core::utils::color_to_css_string(color)).upcast())\n}')
    core_utils = (root / "crates/canvas-core/src/utils.rs").read_text(encoding="utf-8")
    string_block=number_string(original_utils,function_bodies)['typed']
    if function_bodies(core_utils,'parse_number_string')[0]['body']!='{\n'+string_block+'}':
        errors.append('Original numeric string parsing changed')
    if function_bodies(core_utils, "color_to_css_string")[0]["body"] != color_format.replace("Ok(cx.string(css).upcast())", "css"):
        errors.append("Original color string formatting changed")
    fill_body = function_bodies(original_utils, "fill_rule_arg_or")[0]["body"]
    fill_block = fill_body[fill_body.rindex("  match mode.as_str()"):fill_body.rfind("}")]
    expected_utils = expected_utils.replace(fill_block, "  canvas_core::utils::fill_rule(&mode, &err_msg).or_else(|e| cx.throw_type_error(e))\n")
    if function_bodies(core_utils, "fill_rule")[0]["body"] != "{\n" + fill_block.replace("cx.throw_type_error(&err_msg)", "Err(err_msg.clone())") + "}":
        errors.append("Original fill-rule selection changed")
    for name in SHARED_HELPERS:
        function = function_bodies(original_utils, name)[0]["text"]
        forwarding = ANGLE_FORWARD if name == "to_radians" else f"pub use canvas_core::utils::{name};\n"
        if name in {"almost_equal", "almost_zero"}:
            forwarding = "#[allow(unused_imports)] // Keep the original internal name while adapters migrate.\n" + forwarding
        if name in {"to_degrees", "to_stroke_join"}:
            forwarding = "#[allow(unused_imports)] // Preserve the original helper name during adapter migration.\n" + forwarding
        if name == "to_path_op":
            forwarding = "#[allow(unused_imports)] // Preserve helper while all consumers migrate to the core.\n" + forwarding
        expected_utils = expected_utils.replace(function, forwarding)
    expected_utils=effects_node_arguments(expected_utils,original_utils,function_bodies)
    expected_utils=export_node_arguments(expected_utils,original_utils,function_bodies)
    if node_utils != expected_utils:
        errors.append("Node utils changed beyond the original shared helper re-exports")
    for entry in actual["preservedBodies"]:
        if entry["sourceBodySha256"] != entry["destinationBodySha256"]:
            errors.append(f"Original method body changed: {entry['symbol']} ({entry['destination']})")
    source_gradient = (root / UPSTREAM / "src/gradient.rs").read_text(encoding="utf-8")
    stop_body = function_bodies(source_gradient, "addColorStop")[0]["body"]
    stop_block = stop_body[stop_body.index("  if offset <"):stop_body.index("  if let Some(color)")]
    core_gradient = (root / "crates/canvas-core/src/gradient.rs").read_text(encoding="utf-8")
    if function_bodies(core_gradient, "validate_offset")[0]["body"] != "{\n" + stop_block.replace("cx.throw_range_error(", "Err(") + "  Ok(())\n  }":
        errors.append("Original gradient offset validation changed")
    expected_stop = stop_body.replace(stop_block, "  CanvasGradient::validate_offset(offset).or_else(|e| cx.throw_range_error(e))?;\n\n")
    node_gradient = (root / "crates/node/src/gradient.rs").read_text(encoding="utf-8")
    if function_bodies(node_gradient, "addColorStop")[0]["body"] != expected_stop:
        errors.append("Node color-stop adapter changed beyond shared range validation")
    for filename in PAGE_GPU_FILES:
        original = (root / UPSTREAM / "src" / filename).read_text(encoding="utf-8")
        extracted = (root / "crates/canvas-core/src" / filename).read_text(encoding="utf-8")
        without_docs = "\n".join(line for line in extracted.splitlines() if not line.lstrip().startswith("///")) + "\n"
        if filename == "context/page.rs":
            without_docs=without_docs.replace("pub mod audit;\n","",1)
            for line in ("use neon::prelude::*;\n", "use crate::canvas::BoxedCanvas;\n", "use crate::context::BoxedContext2D;\n"):
                original = original.replace(line, "")
            start = original.index("pub fn pages_arg(")
            end = original.index("\nfn pdf_document", start)
            original = original[:start] + original[end:]
        if filename=="gpu/mod.rs":
            without_docs=without_docs.replace("pub mod audit;\n","",1)
            without_docs=without_docs.replace('#[cfg(all(target_os = "windows", feature = "vulkan"))]\npub fn release_current_thread() { vulkan::engine::VulkanEngine::release_current_thread(); }\n','',1)
        if filename=="gpu/vulkan/engine.rs":
            without_docs=without_docs.replace('    pub fn release_current_thread() {\n        VK_CONTEXT.with_borrow_mut(|context| { drop(context.take()); });\n    }\n\n','',1)
            without_docs=without_docs.replace(".inspect(|s| crate::gpu::audit::allocated(s.width(),s.height()))","",1)
            original=original.replace('thread_local!( static VK_CONTEXT: RefCell<Option<VulkanContext>> = const { RefCell::new(None) }; );','thread_local!( static VK_CONTEXT: RefCell<Option<VulkanContext>> = const { RefCell::new(None) }; );\nmod initialization;').replace('let context = VulkanContext::new()', 'let context = initialization::create()').replace('.or_else(|| VulkanContext::new().ok() )','.or_else(|| initialization::create().ok() )')
        if without_docs != original:
            errors.append(f"Page/GPU extraction changed more than documented binding separation: {filename}")
    node_page = (root / "crates/node/src/context/page.rs").read_text(encoding="utf-8")
    node_gpu = (root / "crates/node/src/gpu/mod.rs").read_text(encoding="utf-8")
    if "pub use canvas_core::context::page::*;" not in node_page or "static CACHE" in node_page:
        errors.append("Node page adapter must use the unique core recorder/cache/export implementation")
    if "pub use canvas_core::gpu::*;" not in node_gpu or "enum RenderingEngine" in node_gpu:
        errors.append("Node GPU adapter must use the unique core engine implementation")
    for filename in CONTEXT_FILES:
        original = (root / UPSTREAM / "src" / filename).read_text(encoding="utf-8")
        extracted = (root / "crates/canvas-core/src" / filename).read_text(encoding="utf-8")
        without_docs = "\n".join(line for line in extracted.splitlines() if not line.lstrip().startswith("///")) + "\n"
        if filename == "context/mod.rs":
            original = original.replace("pub mod page;", "pub mod page;\npub mod operations;\npub mod text_state;\npub mod effects;")
            for removed in ("use neon::prelude::*;\n", "pub mod api;\n", "pub type BoxedContext2D = JsBox<RefCell<Context2D>>;\nimpl Finalize for Context2D {}\n"):
                original = original.replace(removed, "")
            for typename in ("Gradient", "Pattern", "Texture"):
                original = original.replace(f"Canvas{typename}, BoxedCanvas{typename}", f"Canvas{typename}")
            upstream_context = (root / UPSTREAM / "src/context/mod.rs").read_text(encoding="utf-8")
            for name, index in (("new", 1), ("value", 0)):
                original = original.replace(function_bodies(upstream_context, name)[index]["text"], "")
            for typename in ("Context2D", "State"):
                start = original.index(f"pub struct {typename}{{")
                end = original.index("\n}", start)
                block = re.sub(r"(?m)^  (?!pub )([a-z_]+:)", r"  pub \1", original[start:end])
                original = original[:start] + block + original[end:]
        elif filename == "typography.rs":
            without_docs=without_docs.replace("    audit::record_layout(&mut paragraph, self, offset);\n", "",1)
            upstream_typography = original
            original = original.replace('use crate::context::State;','use crate::context::State;\npub mod decoration;\npub mod audit;')
            spec_without_docs = '\n'.join(line for line in core_spec(original,function_bodies).splitlines() if not line.lstrip().startswith('///'))+'\n'
            without_docs = without_docs.removesuffix(spec_without_docs)
            for name in TYPOGRAPHY_BINDINGS:
                original = original.replace(function_bodies(upstream_typography, name)[0]["text"], "")
            original = original.replace("use neon::prelude::*;\n", "").replace("use crate::utils::*;\n", "")
            original = original.replace("TextAlign, TextDecoration, TextDecorationMode, TextDecorationStyle, TextDirection, TextStyle,", "TextAlign, TextDirection, TextStyle,")
        elif filename == "font_library.rs":
            original = original[:original.index("//\n// Javascript Methods")]
            start = original.index('#[cfg(target_os = "windows")]\nuse allsorts::{')
            end = original.index("};\n", start) + 3
            original = original[:start] + original[end:]
            original = original.replace("use neon::prelude::*;\n", "").replace("use crate::utils::*;\n", "").replace(", typeface_details", "")
            for name in ("families", "family_details", "add_typeface"):
                original = original.replace("  fn " + name + "(", "  pub fn " + name + "(")
            without_docs = without_docs[:without_docs.index("\nimpl FontLibrary {\n")]
        else:
            original = original.split("//\n// -- Javascript Methods", 1)[0]
            for removed in ("use neon::prelude::*;\n", "use skia_safe::SurfaceProps;\n", "use serde_json::json;\n", "use crate::utils::*;\n", "pub type BoxedCanvas = JsBox<RefCell<Canvas>>;\nimpl Finalize for Canvas {}\n", "use std::cell::RefCell;\n"):
                original = original.replace(removed, "")
            original = original.replace("{ExportOptions, pages_arg}", "{ExportOptions}").replace("  engine: Option<", "  pub engine: Option<")
        if filename=="canvas.rs":original+="\npub mod exports;\npub mod options;\npub mod construction;\n"
        if without_docs != original:
            errors.append(f"Context/font extraction changed more than binding visibility/import separation: {filename}")
    original_layout=function_bodies((root/UPSTREAM/'src/typography.rs').read_text(encoding='utf-8'),'layout')[0]['body']
    actual_layout=function_bodies((root/'crates/canvas-core/src/typography.rs').read_text(encoding='utf-8'),'layout')[0]['body']
    if actual_layout.replace('    audit::record_layout(&mut paragraph, self, offset);\n','',1)!=original_layout:errors.append('Original layout changed beyond same-Paragraph observation')
    original_surface=function_bodies((root/UPSTREAM/'src/gpu/vulkan/engine.rs').read_text(encoding='utf-8'),'surface')[0]['body']
    actual_surface=function_bodies((root/'crates/canvas-core/src/gpu/vulkan/engine.rs').read_text(encoding='utf-8'),'surface')[0]['body']
    if actual_surface.replace('.inspect(|s| crate::gpu::audit::allocated(s.width(),s.height()))','',1)!=original_surface:errors.append('Original method body changed: surface (beyond result observation)')
    core_fonts = (root / "crates/canvas-core/src/font_library.rs").read_text(encoding="utf-8")
    upstream_fonts = (root / UPSTREAM / "src/font_library.rs").read_text(encoding="utf-8")
    upstream_typography = (root / UPSTREAM / "src/typography.rs").read_text(encoding="utf-8")
    core_typography=(root/'crates/canvas-core/src/typography.rs').read_text(encoding='utf-8')
    if (root/'crates/canvas-core/src/typography/decoration.rs').read_text(encoding='utf-8') != decoration_core(upstream_typography,function_bodies):
        errors.append('Original decoration argument fragment changed')
    node_decoration=(root/'crates/node/src/typography.rs').read_text(encoding='utf-8')
    expected_decoration=decoration_node(upstream_typography,upstream_typography,function_bodies)
    if function_bodies(node_decoration,'decoration_arg')[0]['body'] != function_bodies(expected_decoration,'decoration_arg')[0]['body'] or decoration_reader(upstream_typography,function_bodies) not in node_decoration:
        errors.append('Node decoration field reader changed')
    if function_bodies(core_typography,'font_spec')[0]['body'] != function_bodies(core_spec(upstream_typography,function_bodies),'font_spec')[0]['body']:
        errors.append('Original typed FontSpec packing changed')
    node_typography=(root/'crates/node/src/typography.rs').read_text(encoding='utf-8')
    if function_bodies(node_typography,'font_arg')[0]['body'] != function_bodies(node_spec(upstream_typography,upstream_typography,function_bodies),'font_arg')[0]['body']:
        errors.append('Node font descriptor reads changed')
    for name, generated in [("load_typeface", core_loading(upstream_fonts,function_bodies)),
                            ("typeface_metadata", core_metadata(upstream_typography,function_bodies))]:
        if function_bodies(core_fonts,name)[0]['body'] != function_bodies(generated,name)[0]['body']:
            errors.append(f"Original font {name} fragment changed")
    for file,name,generated in [("font_library.rs","addFamily",node_loading(upstream_fonts,upstream_fonts,function_bodies)),
                                ("typography.rs","typeface_details",node_metadata(upstream_typography,upstream_typography,function_bodies))]:
        node_source=(root/'crates/node/src'/file).read_text(encoding='utf-8')
        if function_bodies(node_source,name)[0]['body'] != function_bodies(generated,name)[0]['body']:
            errors.append(f"Node font {name} allocation boundary changed")
    if function_bodies(core_fonts, "reset")[0]["body"] != "{\n    self.fonts.clear();\n    self.collection = None;\n    self.collection_cache.drain();\n  }":
        errors.append("Original font reset operations changed")
    if function_bodies(core_fonts, "new_from_data")[0]["body"] != "{\n    self.mgr.new_from_data(bytes, None)\n  }":
        errors.append("Original font byte decode call changed")
    original_dye = function_bodies((root / UPSTREAM / "src/context/mod.rs").read_text(encoding="utf-8"), "new")[1]["body"]
    expected_dye = original_dye.replace(".borrow().clone()", ".borrow().0.clone()")
    node_context = (root / "crates/node/src/context/mod.rs").read_text(encoding="utf-8")
    if function_bodies(node_context, "new")[0]["body"] != expected_dye:
        errors.append("Node Dye adapter changed beyond typed core Resource unboxing")
    upstream_api = (root / UPSTREAM / "src/context/api.rs").read_text(encoding="utf-8")
    if (root/'crates/canvas-core/src/context/effects.rs').read_text(encoding='utf-8')!=effects_core(upstream_api,function_bodies):errors.append('Original effect state fragments changed')
    if (root/'crates/canvas-core/src/filter/arguments.rs').read_text(encoding='utf-8')!=effects_arguments(original_utils,function_bodies):errors.append('Original FilterSpec packing changed')
    if (root/'crates/canvas-core/src/context/text_state.rs').read_text(encoding='utf-8') != text_core(upstream_api,function_bodies):
        errors.append('Original text-state operation fragments changed')
    if (root/'python/py_skia_canvas/_text_css_data.py').read_text(encoding='utf-8') != feature_data((root/UPSTREAM/'lib/classes/css.js').read_text(encoding='utf-8')):
        errors.append('Original CSS font feature tables changed')
    if (root / "crates/canvas-core/src/context/operations.rs").read_text(encoding="utf-8") != core_operations(upstream_api, function_bodies):
        errors.append("Original context operation fragments changed")
    expected_api = upstream_api.replace("Dye, page::ExportOptions", "Dye, DyeBindings, page::ExportOptions").replace(
        "RefCell::new(Context2D::new())", "RefCell::new(crate::resource::Resource(Context2D::new()))")
    expected_api = text_node(wrap_paths(node_operations(expected_api, upstream_api, function_bodies)), upstream_api, function_bodies)
    diagnostic=function_bodies((root/'crates/node/src/context/api.rs').read_text(encoding='utf-8'),'debugGlyphs')[0]['text']
    expected_api=expected_api.replace(function_bodies(expected_api,'measureText')[0]['text'],function_bodies(expected_api,'measureText')[0]['text']+'\n'+diagnostic,1)
    # Comments are part of the controlled diagnostic insertion, not original API bodies.
    diagnostic_comment='''/// Development diagnostic only: original measurement-layout visitor, same owner.
/// UTF-8 text/canvas-unit width ->owned JSON; transient font table bytes must only
/// be hashed/discarded by audit runner. No public Context JS method is added.
'''
    expected_api=expected_api.replace(diagnostic,diagnostic_comment+diagnostic,1)
    upstream_image=(root/UPSTREAM/'src/image.rs').read_text(encoding='utf-8')
    expected_api=node_image_operations(expected_api,upstream_image,upstream_api,function_bodies)
    expected_api=effects_node(expected_api,upstream_api,function_bodies)
    for name,expected in [('loading.rs',image_loading(upstream_image,upstream_api,function_bodies)),('operations.rs',image_operations(upstream_image,upstream_api,function_bodies))]:
        if (root/'crates/canvas-core/src/image'/name).read_text(encoding='utf-8')!=expected:errors.append('Original image extraction changed: '+name)
    actual_image=(root/'crates/node/src/image.rs').read_text(encoding='utf-8')
    original_decode=function_bodies(upstream_image,'set_data')[0]['body']
    decode_start=original_decode.index('  if let Some(raw_info)');decode_end=original_decode.index('  Ok(cx.boolean')
    expected_decode=original_decode[:decode_start]+'  let raw_info = opt_image_info_arg(&mut cx, 2)?;\n  this.decode(data, raw_info);\n\n'+original_decode[decode_end:]
    for name in ('get_src','set_src','get_width','get_height','get_complete','pixels','new','set_data'):
        expected=expected_decode if name=='set_data' else function_bodies(upstream_image,name)[-1 if name=='new' else 0]['body']
        if name=='new':expected=expected.replace('RefCell::new(Image::default())','RefCell::new(Resource(Image::default()))')
        if function_bodies(actual_image,name)[0]['body']!=expected:errors.append('Node image adapter changed beyond declared decode forwarding: '+name)
    if 'pub struct Image{' in actual_image or 'pub use canvas_core::image::Image;' not in actual_image:errors.append('Node Image must share the unique core resource')
    if (root / "crates/node/src/context/api.rs").read_text(encoding="utf-8") != expected_api:
        errors.append("Node context adapter changed beyond declared operations and boxing")
    upstream_path = (root / UPSTREAM / "src/path.rs").read_text(encoding="utf-8")
    prefix, tail = upstream_path.split("//\n// -- Javascript Methods", 1)
    expected_path = prefix.replace("use std::cell::RefCell;\n", "").replace("use neon::prelude::*;\n", "").replace(
        "pub type BoxedPath2D = JsBox<RefCell<Path2D>>;\nimpl Finalize for Path2D {}\n", "")
    expected_path = expected_path.replace("use crate::utils::*;", "use crate::utils::*;\npub mod operations;")
    actual_path = (root / "crates/canvas-core/src/path.rs").read_text(encoding="utf-8")
    if "\n".join(line for line in actual_path.splitlines() if not line.lstrip().startswith("///")) + "\n" != expected_path:
        errors.append("Original Path2D primitives changed")
    expected_node_path = upstream_path[:upstream_path.index("pub type BoxedPath2D")] + "pub use canvas_core::path::Path2D;\npub type BoxedPath2D = JsBox<RefCell<crate::resource::Resource<Path2D>>>;\n\n//\n// -- Javascript Methods" + tail
    if (root / "crates/node/src/path.rs").read_text(encoding="utf-8") != path_node(wrap_paths(expected_node_path), upstream_path, function_bodies):
        errors.append("Node Path2D changed beyond declared core forwarding and boxing")
    if (root / "crates/canvas-core/src/path/operations.rs").read_text(encoding="utf-8") != path_core(upstream_path, function_bodies):
        errors.append("Original Path2D operation fragments changed")
    if ANGLE not in (root / "crates/canvas-core/src/utils.rs").read_text(encoding="utf-8"):
        errors.append("Original angle arithmetic/order is missing from core")
    upstream_canvas=(root/UPSTREAM/'src/canvas.rs').read_text(encoding='utf-8')
    if (root/'crates/canvas-core/src/canvas/exports.rs').read_text(encoding='utf-8')!=export_dispatch(upstream_canvas,function_bodies):errors.append('Original export dispatch changed')
    if (root/'crates/canvas-core/src/canvas/options.rs').read_text(encoding='utf-8')!=export_arguments(original_utils,function_bodies):errors.append('Original export options packing changed')
    before_canvas=upstream_canvas[:upstream_canvas.index('pub type BoxedCanvas')].replace('use crate::context::page::{ExportOptions, pages_arg};','use crate::context::page::pages_arg;').rstrip()+'\nuse crate::resource::Resource;\npub use canvas_core::canvas::Canvas;\npub type BoxedCanvas = JsBox<RefCell<Resource<Canvas>>>;\n\n'+upstream_canvas[upstream_canvas.index('// -- Javascript Methods'):]
    before_canvas=before_canvas.replace('RefCell::new(Canvas::new(text_contrast as f64, text_gamma as f64, !gpu_enabled))','RefCell::new(Resource(Canvas::new(text_contrast as f64, text_gamma as f64, !gpu_enabled)))')
    if (root/'crates/node/src/canvas.rs').read_text(encoding='utf-8')!=construction_node(export_node_dispatch(before_canvas,upstream_canvas,function_bodies),upstream_canvas,function_bodies):errors.append('Node export adapter changed beyond shared dispatch forwarding')
    source_gui=(root/UPSTREAM/'src/gui/app.rs').read_text(encoding='utf-8')
    if (root/'crates/canvas-core/src/gui/app.rs').read_text(encoding='utf-8')!=gui_core_app(source_gui,function_bodies):errors.append('Original GUI loop/cadence changed beyond language scheduling separation')
    if (root/'crates/node/src/gui/app.rs').read_text(encoding='utf-8')!=gui_node_app(source_gui,function_bodies):errors.append('Node GUI callback adapter changed beyond loop delegation')
    for filename in ('window.rs','window_mgr.rs','event.rs'):
        source=(root/UPSTREAM/'src/gui'/filename).read_text(encoding='utf-8')
        if (root/'crates/canvas-core/src/gui'/filename).read_text(encoding='utf-8')!=gui_documented(source,filename):errors.append('Original GUI native body changed: '+filename)
        expected='//! Compatibility namespace: original GUI implementation lives only in canvas-core.\npub use canvas_core::gui::'+filename[:-3]+'::*;\n'
        if (root/'crates/node/src/gui'/filename).read_text(encoding='utf-8')!=expected:errors.append('Node GUI must reexport original unique core: '+filename)
    if (root/'crates/canvas-core/src/canvas/construction.rs').read_text(encoding='utf-8')!=construction_core(upstream_canvas,function_bodies):errors.append('Original Canvas construction validation changed')
    if (root/'python/py_skia_canvas/_argument_specs.py').read_text(encoding='utf-8')!=argument_declarations(root/UPSTREAM/'src',function_bodies):errors.append('Original float argument declarations changed')
    node_filter = (root / "crates/node/src/filter.rs").read_text(encoding="utf-8")
    if "pub use canvas_core::filter::*;" not in node_filter or "impl " in node_filter:
        errors.append("Node must use the shared filter implementation")
    for path in (root / "crates/canvas-core/src").rglob("*.rs"):
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in ("neon::", "JsBox", "FunctionContext", "unsafe impl Send", "unsafe impl Sync")):
            errors.append(f"Language/thread boundary violation: {path.relative_to(root)}")
    return {"status": "CORE_EXTRACTION_CHECKED" if not errors else "INCOMPLETE", "errors": errors,
            "scope": "Mechanical source checks only; build, GPU, Python and release require separate evidence"}


def main() -> None:
    """Validate, or record the initial map once; never overwrite an existing source map."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-initial-map", action="store_true")
    args = parser.parse_args()
    if args.record_initial_map:
        with (ROOT / "crates/source-map.json").open("x", encoding="utf-8") as output:
            json.dump(source_map(), output, indent=2)
            output.write("\n")
    result = validate()
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
