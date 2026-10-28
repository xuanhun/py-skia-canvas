//! Original Path2D operations mechanically separated from Neon.
#![allow(non_snake_case, unused_imports, unused_mut)]
use skia_safe::{Path, Point, Rect, RRect, Matrix, PathFillType, PathDirection, StrokeRec, PathEffect, trim_path_effect};
use skia_safe::path::{self, AddPathMode, Verb};
use super::Path2D;
use crate::utils::*;
use serde_json::{json, Value};

/// Original closePath; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:142.
pub fn closePath(this:&mut Path2D) -> () {
  this.path.close();
}

/// Original moveTo; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:150.
pub fn moveTo(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [x, y] = nums.as_slice(){
    this.path.move_to((*x, *y));
  }

}

/// Original lineTo; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:163.
pub fn lineTo(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [x, y] = nums.as_slice(){
    this.scoot(*x, *y);
    this.path.line_to((*x, *y));
  }

}

/// Original bezierCurveTo; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:177.
pub fn bezierCurveTo(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [cp1x, cp1y, cp2x, cp2y, x, y] = nums.as_slice(){
    this.scoot(*cp1x, *cp1y);
    this.path.cubic_to((*cp1x, *cp1y), (*cp2x, *cp2y), (*x, *y));
  }

}

/// Original quadraticCurveTo; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:191.
pub fn quadraticCurveTo(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [cpx, cpy, x, y] = nums.as_slice(){
    this.scoot(*cpx, *cpy);
    this.path.quad_to((*cpx, *cpy), (*x, *y));
  }

}

/// Original conicCurveTo; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:205.
pub fn conicCurveTo(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [p1x, p1y, p2x, p2y, weight] = nums.as_slice(){
    this.scoot(*p1x, *p1y);
    this.path.conic_to((*p1x, *p1y), (*p2x, *p2y), *weight);
  }

}

/// Original arc; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:219.
pub fn arc(this:&mut Path2D, nums:Vec<f32>, ccw:bool) -> () {
  if let [x, y, radius, start_angle, end_angle] = nums.as_slice(){
    this.add_ellipse((*x, *y), (*radius, *radius), 0.0, *start_angle, *end_angle, ccw);
  }

}

/// Original arcTo; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:233.
pub fn arcTo(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [x1, y1, x2, y2, radius] = nums.as_slice(){
    this.scoot(*x1, *y1);
    this.path.arc_to_tangent((*x1, *y1), (*x2, *y2), *radius);
  }

}

/// Original ellipse; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Result<(), &'static str>, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:247.
pub fn ellipse(this:&mut Path2D, nums:Vec<f32>, ccw:bool) -> Result<(), &'static str> {
  if let [x, y, x_radius, y_radius, rotation, start_angle, end_angle] = nums.as_slice(){
    if *x_radius < 0.0 || *y_radius < 0.0 {
      return Err("Radius value must be positive")
    }
    this.add_ellipse((*x, *y), (*x_radius, *y_radius), *rotation, *start_angle, *end_angle, ccw);
  }

  Ok(())
}

/// Original rect; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:264.
pub fn rect(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [x, y, w, h] = nums.as_slice(){
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    let direction = if w.signum() == h.signum(){ PathDirection::CW }else{ PathDirection::CCW };
    this.path.add_rect(rect, Some((direction, 0)));
  }

}

/// Original roundRect; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns (), retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:280.
pub fn roundRect(this:&mut Path2D, nums:Vec<f32>) -> () {
  if let [x, y, w, h] = &nums[..4]{
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    let radii:Vec<Point> = nums[4..].chunks(2).map(|xy| Point::new(xy[0], xy[1])).collect();
    let rrect = RRect::new_rect_radii(rect, &[radii[0], radii[1], radii[2], radii[3]]);
    let direction = if w.signum() == h.signum(){ PathDirection::CW }else{ PathDirection::CCW };
    this.path.add_rrect(rrect, Some((direction, 0)));
  }

}

/// Original simplify; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:332.
pub fn simplify(this:&mut Path2D, rule:PathFillType) -> Path2D {
  this.path.set_fill_type(rule);

  let new_path = Path2D{
    path:match this.path.simplify(){
      Some(simpler) => simpler,
      None => this.path.clone()
    }
  };

  new_path
}

/// Original unwind; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:350.
pub fn unwind(this:&mut Path2D) -> Path2D {
  this.path.set_fill_type(PathFillType::EvenOdd);

  let new_path = Path2D{
    path:match this.path.as_winding(){
      Some(rewound) => rewound,
      None => this.path.clone()
    }
  };

  new_path
}

/// Original offset; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:367.
pub fn offset(this:&Path2D, dx:f32, dy:f32) -> Path2D {
  let path = this.path.with_offset((dx, dy));
  Path2D{path}
}

/// Original transform; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:378.
pub fn transform(this:&Path2D, matrix:&Matrix) -> Path2D {
  let path = this.path.with_transform(&matrix);
  Path2D{path}
}

/// Original round; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:388.
pub fn round(this:&Path2D, radius:f32) -> Path2D {
  let bounds = this.path.bounds();
  let stroke_rec = StrokeRec::new_hairline();

  if let Some(rounder) = PathEffect::corner_path(radius){
    if let Some((path, _)) = rounder.filter_path(&this.path, &stroke_rec, bounds){
      return Path2D::from(path)
    }
  }

  Path2D{path:this.path.clone()}
}

/// Original trim; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:406.
pub fn trim(this:&Path2D, begin:f32, end:f32, invert:bool) -> Path2D {
  let bounds = this.path.bounds();
  let stroke_rec = StrokeRec::new_hairline();
  let mode = if invert{ trim_path_effect::Mode::Inverted }else{ trim_path_effect::Mode::Normal };

  if let Some(trimmer) = PathEffect::trim(begin, end, mode){
    if let Some((path, _)) = trimmer.filter_path(&this.path, &stroke_rec, bounds){
      return Path2D::from(path)
    }
  }

  Path2D{path:this.path.clone()}
}

/// Original jitter; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:427.
pub fn jitter(this:&Path2D, seg_len:f32, std_dev:f32, seed:u32) -> Path2D {
  let bounds = this.path.bounds();
  let stroke_rec = StrokeRec::new_hairline();

  if let Some(trimmer) = PathEffect::discrete(seg_len, std_dev, Some(seed)){
    if let Some((path, _)) = trimmer.filter_path(&this.path, &stroke_rec, bounds){
      return Path2D::from(path)
    }
  }

  Path2D{path:this.path.clone()}
}

/// Original op; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Result<Path2D, &'static str>, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:299.
pub fn op(this:&Path2D, other_path:&Path2D, op_name:&str) -> Result<Path2D, &'static str> {
  if let Some(path_op) = to_path_op(&op_name){
    let other = other_path;
    match this.path.op(&other.path, path_op) {
      Some(path) => Ok(Path2D{ path }),
      None => Err("path operation failed")
    }
  }else{
    Err("pathOp must be Difference, Intersect, Union, XOR, or Complement")
  }
}

/// Original interpolate; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Result<Path2D, &'static str>, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:316.
pub fn interpolate(this:&Path2D, other:&Path2D, weight:f32) -> Result<Path2D, &'static str> {
  // reverse path order since 0..1 = this..other is a less non-sensical mapping than the default
  if let Some(path) = other.path.interpolate(&this.path, weight){
    Ok(Path2D{ path })
  }else{
    Err("Can only interpolate between two Path2D objects with the same number of points and control points")
  }
}

/// Original new; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:102.
pub fn new() -> Path2D {
  let path = Path::new();
  Path2D{path}
}

/// Original from_path; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:107.
pub fn from_path(other_path:&Path2D) -> Path2D {
  let path = other_path.path.clone();
  Path2D{path}
}

/// Original from_svg; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Path2D, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:113.
pub fn from_svg(svg_string:String) -> Path2D {
  let path = Path::from_svg(svg_string).unwrap_or_default();
  Path2D{path}
}

/// Original set_d; geometry/lengths are f32 canvas units, angles radians, weights/trim fractions unitless.
/// Typed vectors require original arity; returns Result<(), &'static str>, retaining original fallback/error text.
/// Owner-thread Skia references only, no Send/Sync transfer. Upstream: src/path.rs:540.
pub fn set_d(this:&mut Path2D, svg_string:String) -> Result<(), &'static str> {
  if let Some(path) = Path::from_svg(svg_string){
    this.path.rewind();
    this.path.add_path(&path, (0,0), None);
    Ok(())
  }else{
    Err("Expected a valid SVG path string")
  }
}

/// Original edge-verb name mapping; unitless, returns owned name/None, no native ownership transfer.
/// Upstream: src/path.rs:from_verb; body unchanged.
pub fn from_verb(verb:Verb) -> Option<String>{
  let cmd = match verb{
    Verb::Move => "moveTo",
    Verb::Line => "lineTo",
    Verb::Quad => "quadraticCurveTo",
    Verb::Cubic => "bezierCurveTo",
    Verb::Conic => "conicCurveTo",
    Verb::Close => "closePath",
    _ => return None
  };
  Some(cmd.to_string())
}

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
  let mut weights = path::Iter::new(&this.path, false);
  let iter = path::Iter::new(&this.path, false);

  let mut edges = vec![];
  for (verb, points) in iter{
    weights.next();

    if let Some(edge) = from_verb(verb){
      let cmd = json!(edge);
      let mut segment = vec![Value::Null; 1 + points.len()];
      edge_set(&mut segment, 0, cmd);

      let at_point = if points.len()>1{ 1 }else{ 0 };
      for (i, pt) in points.iter().skip(at_point).enumerate() {
        let x = number_token(pt.x);
        let y = number_token(pt.y);
        edge_set(&mut segment, 1 + 2*i as u32, x);
        edge_set(&mut segment, 2 + 2*i as u32, y);
      }

      if verb==Verb::Conic{
        let weight = weights.conic_weight().unwrap();
        let weight = number_token(weight);
        edge_set(&mut segment, 5, weight);
      }

      edges.push(segment);
    }
  }

  edges
}

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
