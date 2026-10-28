#![allow(unused_mut)]
#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(non_snake_case)]
#![allow(dead_code)]
use std::cell::RefCell;
use std::f32::{EPSILON, consts::PI};
use neon::prelude::*;
use skia_safe::{Path, Point, PathFillType, PathDirection, PathBuilder, Rect, RRect, Matrix, PathOp, StrokeRec};
use skia_safe::{PathEffect, trim_path_effect};
use skia_safe::path::{self, AddPathMode, Verb};

use crate::utils::*;
use canvas_core::path::operations as path_ops;

pub use canvas_core::path::Path2D;
pub type BoxedPath2D = JsBox<RefCell<crate::resource::Resource<Path2D>>>;

//
// -- Javascript Methods --------------------------------------------------------------------------
//

pub fn new(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::new()))))
}

pub fn from_path(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let other_path = path2d_arg(&mut cx, 1)?;
  let value = path_ops::from_path(&other_path.borrow());
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(value))))
}

pub fn from_svg(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let svg_string = string_arg(&mut cx, 1, "svgPath")?;
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::from_svg(svg_string)))))
}

// Adds a path to the current path.
pub fn addPath(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let other = path2d_arg(&mut cx, 1)?;
  let matrix = opt_matrix_arg(&mut cx, 2).unwrap_or_else(
    Matrix::new_identity
  );

  // make a copy if adding a path to itself, otherwise use a ref
  if this.strict_equals(&mut cx, other){
    let src = other.borrow().path.clone();
    let mut dst = &mut this.borrow_mut().path;
    path_ops::addPath(dst, &src, &matrix);
  }else{
    let src = &other.borrow().path;
    let mut dst = &mut this.borrow_mut().path;
    path_ops::addPath(dst, src, &matrix);
  };

  Ok(cx.undefined())
}

// Causes the point of the pen to move back to the start of the current sub-path. It tries to draw a straight line from the current point to the start. If the shape has already been closed or has only one point, this function does nothing.
pub fn closePath(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();
  path_ops::closePath(&mut this);
  Ok(cx.undefined())
}

// Moves the starting point of a new sub-path to the (x, y) coordinates.
pub fn moveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y"])?;
  path_ops::moveTo(&mut this, nums);
  Ok(cx.undefined())
}

// Connects the last point in the subpath to the (x, y) coordinates with a straight line.
pub fn lineTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y"])?;
  path_ops::lineTo(&mut this, nums);
  Ok(cx.undefined())
}

// Adds a cubic Bézier curve to the path. It requires three points. The first two points are control points and the third one is the end point. The starting point is the last point in the current path, which can be changed using moveTo() before creating the Bézier curve.
pub fn bezierCurveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["cp1x", "cp1y", "cp2x", "cp2y", "x", "y"])?;
  path_ops::bezierCurveTo(&mut this, nums);
  Ok(cx.undefined())
}

// Adds a quadratic Bézier curve to the current path.
pub fn quadraticCurveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["cpx", "cpy", "x", "y"])?;
  path_ops::quadraticCurveTo(&mut this, nums);
  Ok(cx.undefined())
}

// Adds a conic-section curve to the current path.
pub fn conicCurveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["cpx", "cpy", "x", "y", "weight"])?;
  path_ops::conicCurveTo(&mut this, nums);
  Ok(cx.undefined())
}

// Adds an arc to the path which is centered at (x, y) position with radius r starting at startAngle and ending at endAngle going in the given direction by anticlockwise (defaulting to clockwise).
pub fn arc(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "radius", "startAngle", "endAngle"])?;
  let ccw = bool_arg_or(&mut cx, 6, false);
  path_ops::arc(&mut this, nums, ccw);
  Ok(cx.undefined())
}

// Adds a circular arc to the path with the given control points and radius, connected to the previous point by a straight line.
pub fn arcTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x1", "y1", "x2", "y2", "radius"])?;
  path_ops::arcTo(&mut this, nums);
  Ok(cx.undefined())
}

// Adds an elliptical arc to the path which is centered at (x, y) position with the radii radiusX and radiusY starting at startAngle and ending at endAngle going in the given direction by anticlockwise (defaulting to clockwise).
pub fn ellipse(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "xRadius", "yRadius", "rotation", "startAngle", "endAngle"])?;
  let ccw = bool_arg_or(&mut cx, 8, false);
  path_ops::ellipse(&mut this, nums, ccw).or_else(|e| cx.throw_range_error(e))?;
  Ok(cx.undefined())
}

// Creates a path for a rectangle at position (x, y) with a size that is determined by width and height.
pub fn rect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "width", "height"])?;
  path_ops::rect(&mut this, nums);
  Ok(cx.undefined())
}

// Creates a path for a rounded rectangle at position (x, y) with a size (w, h) and whose radii
// are specified in x/y pairs for top_left, top_right, bottom_right, and bottom_left
pub fn roundRect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args(&mut cx, &[
    "x", "y", "width", "height", "r1x", "r1y", "r2x", "r2y", "r3x", "r3y", "r4x", "r4y"
  ])?;
  path_ops::roundRect(&mut this, nums);
  Ok(cx.undefined())
}

// Applies a boolean operator to this and a second path, returning a new Path2D with their combination
pub fn op(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let other_path = path2d_arg(&mut cx, 1)?;
  let op_name = string_arg(&mut cx, 2, "pathOp")?;

  let value = path_ops::op(&this.borrow(), &other_path.borrow(), &op_name).or_else(|e| cx.throw_error(e))?;
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(value))))
}

pub fn interpolate(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let other = path2d_arg(&mut cx, 1)?;
  let weight = float_arg(&mut cx, 2, "weight")?;

  let this = this.borrow();
  let other = other.borrow();
  let value = path_ops::interpolate(&this, &other, weight).or_else(|e| cx.throw_type_error(e))?;
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(value))))
}

// Returns a path with only non-overlapping contours that describe the same area as the original path
pub fn simplify(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let rule = fill_rule_arg_or(&mut cx, 1, "nonzero")?;
  let mut this = this.borrow_mut();

  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::simplify(&mut this, rule)))))
}

// Returns a path that can be drawn with a nonzero fill but looks like the original drawn with evenodd
pub fn unwind(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let mut this = this.borrow_mut();

  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::unwind(&mut this)))))
}

// Returns a copy whose points have been shifted by (dx, dy)
pub fn offset(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let dx = float_arg(&mut cx, 1, "dx")?;
  let dy = float_arg(&mut cx, 2, "dy")?;

  let this = this.borrow();
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::offset(&this, dx, dy)))))
}

// Returns a copy whose points have been transformed by a given matrix
pub fn transform(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let matrix = matrix_arg(&mut cx, 1)?;

  let this = this.borrow();
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::transform(&this, &matrix)))))
}

// Returns a copy where every sharp junction to an arcTo-style rounded corner
pub fn round(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let radius = float_arg(&mut cx, 1, "radius")?;

  let this = this.borrow();
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::round(&this, radius)))))
}

// Clips a proportional segment out of the middle of the path (or the edges if invert=true)
pub fn trim(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let begin = float_arg_or_bail(&mut cx, 1, "begin")?;
  let end = float_arg_or_bail(&mut cx, 2, "end")?;
  let invert = bool_arg_or(&mut cx, 3, false);

  let this = this.borrow();
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::trim(&this, begin, end, invert)))))
}

// Discretizes the path at a fixed segment length then randomly offsets the points
pub fn jitter(mut cx: FunctionContext) -> JsResult<BoxedPath2D> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let seg_len = float_arg_or_bail(&mut cx, 1, "segmentLength")?;
  let std_dev = float_arg_or_bail(&mut cx, 2, "variance")?;
  let seed = float_arg_or(&mut cx, 3, 0.0) as u32;

  let this = this.borrow();
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(path_ops::jitter(&this, seg_len, std_dev, seed)))))
}

// Returns the computed `tight` bounds that contain all the points, control points, and connecting contours
pub fn bounds(mut cx: FunctionContext) -> JsResult<JsObject> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let this = this.borrow();

  let b = path_ops::bounds(&this);

  let js_object: Handle<JsObject> = cx.empty_object();
  let left = cx.number(b.left);
  let top = cx.number(b.top);
  let right = cx.number(b.right);
  let bottom = cx.number(b.bottom);
  let width = cx.number(b.width());
  let height = cx.number(b.height());

  js_object.set(&mut cx, "left", left)?;
  js_object.set(&mut cx, "top", top)?;
  js_object.set(&mut cx, "right", right)?;
  js_object.set(&mut cx, "bottom", bottom)?;
  js_object.set(&mut cx, "width", width)?;
  js_object.set(&mut cx, "height", height)?;
  Ok(js_object)
}

pub fn contains(mut cx: FunctionContext) -> JsResult<JsBoolean> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let x = float_arg(&mut cx, 1, "x")?;
  let y = float_arg(&mut cx, 2, "y")?;
  let this = this.borrow();

  Ok(cx.boolean(path_ops::contains(&this, x, y)))
}

pub use canvas_core::path::operations::from_verb;

pub fn edges(mut cx: FunctionContext) -> JsResult<JsArray> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let this = this.borrow();

  let rows = path_ops::edges(&this);
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
}

pub fn get_d(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let this = this.borrow();
  Ok(cx.string(path_ops::get_d(&this)))
}

pub fn set_d(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedPath2D>(0)?;
  let svg_string = string_arg(&mut cx, 1, "svgPath")?;
  let mut this = this.borrow_mut();

  path_ops::set_d(&mut this, svg_string).or_else(|e| cx.throw_type_error(e))?;
  Ok(cx.undefined())
}
