"""Source-only mechanical extraction of original Path2D operations from Neon.

Rendering never imports this module. Explicit substitutions remove language
allocation/argument/exception code while preserving original geometry statements.
"""
import re

PRIMITIVES = [
    ("closePath", "", "  this.path.close", "", False),
    ("moveTo", "nums:Vec<f32>", "  if let [x, y]", "nums", False),
    ("lineTo", "nums:Vec<f32>", "  if let [x, y]", "nums", False),
    ("bezierCurveTo", "nums:Vec<f32>", "  if let [cp1x", "nums", False),
    ("quadraticCurveTo", "nums:Vec<f32>", "  if let [cpx", "nums", False),
    ("conicCurveTo", "nums:Vec<f32>", "  if let [p1x", "nums", False),
    ("arc", "nums:Vec<f32>, ccw:bool", "  if let [x, y, radius", "nums, ccw", False),
    ("arcTo", "nums:Vec<f32>", "  if let [x1, y1", "nums", False),
    ("ellipse", "nums:Vec<f32>, ccw:bool", "  if let [x, y, x_radius", "nums, ccw", True),
    ("rect", "nums:Vec<f32>", "  if let [x, y, w, h]", "nums", False),
    ("roundRect", "nums:Vec<f32>", "  if let [x, y, w, h]", "nums", False),
]


def unbox(text, result=False):
    """Replace original Neon box allocation only; UTF-8 text in/out, no native objects/errors."""
    def replacement(match):
        value = match.group(1)
        return "Ok(" + value + ")" if result else value
    text = re.sub(r"Ok\(cx\.boxed\(RefCell::new\((Path2D\{[^{}]*\})\)\)\)", replacement, text)
    for value in ("Path2D::from(path)", "new_path"):
        text = text.replace("Ok(cx.boxed(RefCell::new(" + value + ")))", "Ok(" + value + ")" if result else value)
    return text


def definitions(original, bodies):
    """Describe original -> typed blocks with exact original locations; no runtime graphics.

    Types carry original f32 canvas units/radians and ownership. Raises on missing
    source markers. Language result allocation changes are declared here, not inferred.
    """
    rows = []
    def add(name, params, returns, raw, typed, binding, mutable=True):
        rows.append(dict(name=name, params=params, returns=returns, original=raw, typed=typed,
                         binding=binding, mutable=mutable, line=bodies(original,name)[0]["line"]))
    for name, params, start, call, fallible in PRIMITIVES:
        body = bodies(original,name)[0]["body"]
        raw = body[body.index(start):body.rindex("  Ok(cx.undefined())")]
        typed = raw.replace('return cx.throw_range_error("Radius value must be positive")', 'return Err("Radius value must be positive")')
        if fallible: typed += "  Ok(())\n"
        suffix = ".or_else(|e| cx.throw_range_error(e))?" if fallible else ""
        binding = "  path_ops::" + name + "(&mut this" + (", " + call if call else "") + ")" + suffix + ";\n"
        add(name, params, "Result<(), &'static str>" if fallible else "()", raw, typed, binding)
    for name, params, marker, args in [
        ("simplify", "rule:PathFillType", "  this.path.set_fill_type", "rule"),
        ("unwind", "", "  this.path.set_fill_type", ""),
        ("offset", "dx:f32, dy:f32", "  let path = this.path.with_offset", "dx, dy"),
        ("transform", "matrix:&Matrix", "  let path = this.path.with_transform", "&matrix"),
        ("round", "radius:f32", "  let bounds =", "radius"),
        ("trim", "begin:f32, end:f32, invert:bool", "  let bounds =", "begin, end, invert"),
        ("jitter", "seg_len:f32, std_dev:f32, seed:u32", "  let bounds =", "seg_len, std_dev, seed"),
    ]:
        body=bodies(original,name)[0]["body"]
        raw=body[body.index(marker):body.rfind("}")]
        typed=unbox(raw)
        mutable=name in {"simplify","unwind"}
        borrow="&mut this" if mutable else "&this"
        expression="path_ops::"+name+"("+borrow+(", "+args if args else "")+")"
        binding="  Ok(cx.boxed(RefCell::new(crate::resource::Resource("+expression+"))))\n"
        add(name,params,"Path2D",raw,typed,binding,mutable)
    for name, params, marker, args, err in [
        ("op", "other_path:&Path2D, op_name:&str", "  if let Some(path_op)", "&other_path.borrow(), &op_name", "throw_error"),
        ("interpolate", "other:&Path2D, weight:f32", "  // reverse path order", "&other, weight", "throw_type_error"),
    ]:
        body=bodies(original,name)[0]["body"];raw=body[body.index(marker):body.rfind("}")]
        typed=unbox(raw, result=True).replace("    let this = this.borrow();\n", "").replace("    let other = other_path.borrow();", "    let other = other_path;")
        typed=typed.replace("cx.throw_error(", "Err(").replace("cx.throw_type_error(", "Err(")
        if name=="op":
            prefix=body[:body.index(marker)]
            binding=prefix+"  let value = path_ops::op(&this.borrow(), &other_path.borrow(), &op_name).or_else(|e| cx.throw_error(e))?;\n  Ok(cx.boxed(RefCell::new(crate::resource::Resource(value))))\n"
        else:
            prefix=body[:body.index(marker)]
            binding=prefix+"  let value = path_ops::interpolate(&this, &other, weight).or_else(|e| cx.throw_type_error(e))?;\n  Ok(cx.boxed(RefCell::new(crate::resource::Resource(value))))\n"
        add(name,params,"Result<Path2D, &'static str>",raw,typed,binding,False)
    # Getter/constructor/setter geometry is tiny but shared, including original invalid SVG behavior.
    for name, params, returns, marker, tail, replacements, expression, mutable in [
        ("new", "", "Path2D", "  let path =", "", [], "path_ops::new()", False),
        ("from_path", "other_path:&Path2D", "Path2D", "  let path =", "", [("other_path.borrow()","other_path")], "path_ops::from_path(&other_path.borrow())", False),
        ("from_svg", "svg_string:String", "Path2D", "  let path =", "", [], "path_ops::from_svg(svg_string)", False),
        ("set_d", "svg_string:String", "Result<(), &'static str>", "  if let Some(path)", "", [("Ok(cx.undefined())","Ok(())"),("cx.throw_type_error(","Err(")], "", True),
    ]:
        body=bodies(original,name)[0]["body"];raw=body[body.index(marker):body.rfind("}")];typed=unbox(raw)
        for a,b in replacements: typed=typed.replace(a,b)
        if name=="set_d": binding="  path_ops::set_d(&mut this, svg_string).or_else(|e| cx.throw_type_error(e))?;\n  Ok(cx.undefined())\n"
        elif name=="from_path": binding="  let value = "+expression+";\n  Ok(cx.boxed(RefCell::new(crate::resource::Resource(value))))\n"
        else: binding="  Ok(cx.boxed(RefCell::new(crate::resource::Resource("+expression+"))))\n"
        add(name,params,returns,raw,typed,binding,mutable)
    return rows


def core_operations(original, bodies):
    """Emit unique typed Path2D geometry; only Node allocation/borrow/error adapters are removed.

    Geometry uses original canvas units/f32/radians, errors retain messages. Core
    values stay on their owner thread; this source utility allocates text only.
    """
    text='''//! Original Path2D operations mechanically separated from Neon.
#![allow(non_snake_case, unused_imports, unused_mut)]
use skia_safe::{Path, Point, Rect, RRect, Matrix, PathFillType, PathDirection, StrokeRec, PathEffect, trim_path_effect};
use skia_safe::path::{self, AddPathMode, Verb};
use super::Path2D;
use crate::utils::*;
use serde_json::{json, Value};
'''
    for row in definitions(original,bodies):
        name=row['name'];params=row['params']
        if name not in {'new','from_path','from_svg'}:
            params=('this:&mut Path2D' if row['mutable'] else 'this:&Path2D')+(', '+params if params else '')
        text+=f'''
/// Original {name}; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns {row['returns']}, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:{row['line']}.
pub fn {name}({params}) -> {row['returns']} {{
{row['typed']}}}
'''
    fromverb=bodies(original,'from_verb')[0]['text'].replace('fn from_verb','pub fn from_verb',1)
    text+='\n/// Original edge-verb name mapping; unitless, returns owned name/None, no native ownership transfer.\n/// Upstream: src/path.rs:from_verb; body unchanged.\n'+fromverb
    edge=bodies(original,'edges')[0]['body'];edge=edge[edge.index('  let mut weights'):edge.index('  let verbs =')]
    edge=edge.replace('let cmd = cx.string(edge);','let cmd = json!(edge);').replace('let segment = JsArray::new(&mut cx, 1 + points.len());','let mut segment = vec![Value::Null; 1 + points.len()];')
    edge=edge.replace('cx.number(pt.x)','number_token(pt.x)').replace('cx.number(pt.y)','number_token(pt.y)').replace('cx.number(weight)','number_token(weight)')
    edge=re.sub(r'segment.set\(&mut cx, ([^,]+), (\w+)\)\?;',r'edge_set(&mut segment, \1, \2);',edge)
    text+='''
/// Preserve original JS Number values across typed JSON allocation, including non-finite values.
/// Input f32 coordinates/weights, returns owned number/tag; no rounding or native ownership.
pub fn number_token(n:f32) -> Value {
    if n.is_finite() { json!(n) }
    else { json!({"$number": if n.is_nan() { "NaN" } else if n.is_sign_positive() { "Infinity" } else { "-Infinity" }}) }
}
/// Grow/set an original language array slot; index is unitless, values owned JSON tokens.
/// Only data allocation changes; original edge row index arithmetic stays at each call site.
fn edge_set(row:&mut Vec<Value>, index:u32, value:Value) {
    let index=index as usize;
    if row.len()<=index { row.resize(index+1, Value::Null); }
    row[index]=value;
}
/// Return original dense edge rows; coordinates/f32 weights are unchanged, verb names unitless.
/// Owner-only, owned JSON data, original iterator/weight/skip/index order. Upstream: src/path.rs:edges.
pub fn edges(this:&Path2D) -> Vec<Vec<Value>> {
'''+edge+'  edges\n}\n'
    text+='''
/// Append original borrowed path with matrix (including original self-add snapshot in adapters).
/// Canvas-unit geometry, returns unit; owner-only. Upstream: src/path.rs:addPath two equivalent branches.
pub fn addPath(dst:&mut Path, src:&Path, matrix:&Matrix) {
    dst.add_path_matrix(src, matrix, AddPathMode::Append);
}
/// Original tight bounds in canvas units; returns owned Rect, no new errors. Owner-only.
/// Upstream: src/path.rs:bounds, compute_tight_bounds call unchanged.
pub fn bounds(this:&Path2D) -> Rect { this.path.compute_tight_bounds() }
/// Original point containment; canvas units, returns bool, owner-only. Upstream: src/path.rs:contains.
pub fn contains(this:&Path2D, x:f32, y:f32) -> bool { this.path.contains((x,y)) }
/// Original SVG serialization; returns owned string, no units/new errors, owner-only. Upstream: src/path.rs:get_d.
pub fn get_d(this:&Path2D) -> String { this.path.to_svg() }
'''
    return text


def node_operations(source, original, bodies):
    """Emit only declared Node forwarding changes; no native execution, units or ownership transfer."""
    source=source.replace('use crate::utils::*;','use crate::utils::*;\nuse canvas_core::path::operations as path_ops;',1)
    for row in definitions(original,bodies):
        name=row['name'];fn=bodies(source,name)[0];body=fn['body']
        if name in {'op','interpolate'}:
            changed=row['binding']+'}'
        else:
            if name=='from_path': start=body.index('  let path =')
            elif name=='from_svg': start=body.index('  let path =')
            elif name=='new': start=body.index('  let path =')
            elif name in {'set_d','simplify','unwind','offset','transform','round','trim','jitter'}:
                marker=row['original'].splitlines()[0];start=body.index(marker)
            else: start=body.index(row['original'].splitlines()[0])
            end=body.rfind('}') if name in {'new','from_path','from_svg','set_d','simplify','unwind','offset','transform','round','trim','jitter'} else body.rindex('  Ok(cx.undefined())')
            changed=body[:start]+row['binding']+body[end:]
        source=source.replace(fn['text'],fn['text'].replace(body,changed),1)
    source=source.replace('dst.add_path_matrix(&src, &matrix, AddPathMode::Append);','path_ops::addPath(dst, &src, &matrix);').replace('dst.add_path_matrix(src, &matrix, AddPathMode::Append);','path_ops::addPath(dst, src, &matrix);')
    source=source.replace('let b = this.path.compute_tight_bounds();','let b = path_ops::bounds(&this);').replace('this.path.contains((x,y))','path_ops::contains(&this, x, y)').replace('this.path.to_svg()','path_ops::get_d(&this)')
    fn=bodies(source,'from_verb')[0]['text'];source=source.replace(fn,'pub use canvas_core::path::operations::from_verb;\n')
    fn=bodies(source,'edges')[0];body=fn['body'];start=body.index('  let mut weights')
    replacement='''  let rows = path_ops::edges(&this);
  let verbs = JsArray::new(&mut cx, rows.len());
  for (i, row) in rows.iter().enumerate() {
    let segment = JsArray::new(&mut cx, row.len());
    for (j, token) in row.iter().enumerate() {
      let value:Handle<JsValue> = match token {
        serde_json::Value::String(s) => cx.string(s).upcast(),
        serde_json::Value::Number(n) => cx.number(n.as_f64().unwrap()).upcast(),
        serde_json::Value::Object(o) if o.contains_key("$number") => {
          let n = match o["$number"].as_str().unwrap() { "NaN"=>f64::NAN, "Infinity"=>f64::INFINITY, _=>f64::NEG_INFINITY };
          cx.number(n).upcast()
        }
        _ => cx.undefined().upcast(),
      };
      segment.set(&mut cx, j as u32, value)?;
    }
    verbs.set(&mut cx, i as u32, segment)?;
  }
  Ok(verbs)
'''
    changed=body[:start]+replacement+'}';source=source.replace(fn['text'],fn['text'].replace(body,changed),1)
    return source
