"""Deterministic source guards for G4's typed boundary extraction; never renders.

Each selected block is retained verbatim except declared language argument/error
expressions. This module describes extraction, not a second Canvas implementation.
"""
import re
if __package__:
    from .projection_extraction import core_projection, node_projection
else:
    from projection_extraction import core_projection, node_projection

# name, typed arguments, block start, Node call, declared substitutions, Result return.
OPS = [
    ("transform", "matrix:Option<Matrix>", "  if let Some(matrix)", "opt_matrix_arg(&mut cx, 1)", [("opt_matrix_arg(&mut cx, 1)", "matrix")], False),
    ("set_currentTransform", "matrix:Option<Matrix>", "  if let Some(matrix)", "opt_matrix_arg(&mut cx, 1)", [("opt_matrix_arg(&mut cx, 1)", "matrix")], False),
    ("translate", "xy:Vec<f32>", "  if let [dx, dy]", "xy", [], False),
    ("scale", "xy:Vec<f32>", "  if let [m11, m22]", "xy", [], False),
    ("rotate", "radians:f32", "  let degrees =", "radians", [], False),
    ("resetTransform", "", "  this.with_matrix", "", [], False),
    ("beginPath", "", "  this.path =", "", [], False),
    ("rect", "nums:Vec<f32>", "  if let [x, y, w, h]", "nums", [], False),
    ("roundRect", "nums:Vec<f32>", "  if let [x, y, w, h]", "nums", [], False),
    ("arc", "nums:Vec<f32>, ccw:bool", "  if let [x, y, radius", "nums, ccw", [], False),
    ("ellipse", "nums:Vec<f32>, ccw:bool", "  if let [x, y, x_radius", "nums, ccw", [("return cx.throw_range_error(\"Radius value must be positive\")", "return Err(\"Radius value must be positive\")")], True),
    ("moveTo", "xy:Vec<f32>", "  if let Some(dst)", "xy", [], False),
    ("lineTo", "xy:Vec<f32>", "  if let Some(dst)", "xy", [], False),
    ("arcTo", "coords:Vec<f32>, radius:f32", "  if radius <", "coords, radius", [("return cx.throw_range_error(\"Radius value must be positive\")", "return Err(\"Radius value must be positive\")")], True),
    ("bezierCurveTo", "coords:Vec<f32>", "  if let [cp1, cp2, dst]", "coords", [], False),
    ("quadraticCurveTo", "coords:Vec<f32>", "  if let [cp, dst]", "coords", [], False),
    ("conicCurveTo", "args:Vec<f32>", "  if let [src, dst]", "args", [], False),
    ("closePath", "", "  this.path.close", "", [], False),
    ("set_lineCap", "name:&str", "  if let Some(mode)", "&name", [], False),
    ("set_lineJoin", "name:&str", "  if let Some(mode)", "&name", [], False),
    ("set_lineWidth", "num:Option<f32>", "  if let Some(num)", "opt_float_arg(&mut cx, 1)", [("opt_float_arg(&mut cx, 1)", "num")], False),
    ("set_miterLimit", "num:Option<f32>", "  if let Some(num)", "opt_float_arg(&mut cx, 1)", [("opt_float_arg(&mut cx, 1)", "num")], False),
    ("set_lineDashOffset", "num:f32", "  this.state.line_dash_offset", "float_arg_or_bail(&mut cx, 1, \"lineDashOffset\")?", [("float_arg_or_bail(&mut cx, 1, \"lineDashOffset\")?", "num")], False),
]


def blocks(original, bodies):
    """Return owned source/typed block descriptions; offsets are source characters, no native objects.

    Raises on missing/ambiguous markers. Uses the existing Rust body locator supplied
    by validate_core; all mutations remain explicit substitutions in OPS.
    """
    result = []
    for name, params, start, call, substitutions, fallible in OPS:
        function = bodies(original, name)[0]
        body = function["body"]
        block = body[body.index(start):body.rindex("  Ok(cx.undefined())")]
        typed = block
        for before, after in substitutions:
            assert before in typed, (name, before)
            typed = typed.replace(before, after)
        result.append({"name": name, "params": params, "original": block, "typed": typed,
                       "call": call, "fallible": fallible, "line": function["line"]})
    # Preserve the original numeric filtering, odd-list duplication, and all-or-nothing update.
    function = bodies(original, "setLineDash")[0]
    body = function["body"]
    block = body[body.index("    let mut intervals"):body.index("  }else{")]
    typed = block.replace("floats_in(&mut cx, &list)", "values").replace("list.len()", "length")
    result.append({"name": "setLineDash", "params": "values:Vec<f32>, length:usize", "original": block,
                   "typed": typed, "call": "floats_in(&mut cx, &list), list.len()", "fallible": False, "line": function["line"]})
    return result


def core_operations(original, bodies):
    """Generate the unique typed operations source from original blocks; UTF-8 text, no runtime work.

    Generated functions preserve original units/defaults/algorithm; only signatures,
    comments and declared language boundary substitutions change. No GPU/thread transfer.
    """
    output = """//! Original context/api.rs operations, separated from Neon argument/return handling.
#![allow(non_snake_case)]
use std::f32::consts::PI;
use skia_safe::{Matrix, Path, Point, Rect, RRect, PathDirection};
use skia_safe::path::AddPathMode::Extend;
use super::Context2D;
use crate::{path::Path2D, utils::*};
"""
    for item in blocks(original, bodies):
        args = (", " + item["params"]) if item["params"] else ""
        returns = " -> Result<(), &'static str>" if item["fallible"] else ""
        ending = "  Ok(())\n" if item["fallible"] else ""
        output += f'''
/// Original {item['name']} operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:{item['line']}, skia-canvas 3.0.8; selected statements retained.
pub fn {item['name']}(this:&mut Context2D{args}){returns} {{
{item['typed']}{ending}}}
'''
    return output + core_projection(original,bodies)


def node_operations(source, original, bodies):
    """Replace only selected operation blocks with shared-core calls; returns owned Node source.

    Neon validation/exception/return behavior stays in the adapter. Source-only utility,
    raises on missing blocks; no native execution or ownership transfer.
    """
    for item in blocks(original, bodies):
        args = (", " + item["call"]) if item["call"] else ""
        suffix = ".or_else(|e| cx.throw_range_error(e))?" if item["fallible"] else ""
        replacement = f"  canvas_core::context::operations::{item['name']}(&mut this{args}){suffix};\n"
        if item["name"] == "setLineDash":
            replacement = "  " + replacement
        assert item["original"] in source, item["name"]
        # Restrict to this function: simple identical operation blocks may occur elsewhere.
        fn = bodies(source, item["name"])[0]["text"]
        changed = fn.replace(item["original"], replacement, 1)
        source = source.replace(fn, changed, 1)
    source=node_projection(source,original,bodies)
    return source.replace("use std::f32::consts::PI;\n", "").replace("Point, RRect, Rect", "Rect").replace("Path, PathDirection};", "Path};").replace("use skia_safe::path::AddPathMode::{Extend};\n", "")


def wrap_paths(source):
    """Wrap core Path2D objects in existing Node Resource; only constructor boxing changes.

    Synchronous source transformation; no algorithm, units or runtime ownership transfer.
    """
    source = re.sub(r"RefCell::new\((Path2D\{[^{}]*\})\)", r"RefCell::new(crate::resource::Resource(\1))", source)
    source = source.replace("RefCell::new(new_path)", "RefCell::new(crate::resource::Resource(new_path))")
    return source.replace("RefCell::new(Path2D::from(path))", "RefCell::new(crate::resource::Resource(Path2D::from(path)))")
