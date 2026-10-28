//! Original context/api.rs operations, separated from Neon argument/return handling.
#![allow(non_snake_case)]
use std::f32::consts::PI;
use skia_safe::{Matrix, Path, Point, Rect, RRect, PathDirection};
use skia_safe::path::AddPathMode::Extend;
use super::Context2D;
use crate::{path::Path2D, utils::*};

/// Original transform operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:92, skia-canvas 3.0.8; selected statements retained.
pub fn transform(this:&mut Context2D, matrix:Option<Matrix>) {
  if let Some(matrix) = matrix {
    this.with_matrix(|ctm| ctm.pre_concat(&matrix) );
  }
}

/// Original set_currentTransform operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:191, skia-canvas 3.0.8; selected statements retained.
pub fn set_currentTransform(this:&mut Context2D, matrix:Option<Matrix>) {
  if let Some(matrix) = matrix{
    this.with_matrix(|ctm| ctm.reset().pre_concat(&matrix) );
  }
}

/// Original translate operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:102, skia-canvas 3.0.8; selected statements retained.
pub fn translate(this:&mut Context2D, xy:Vec<f32>) {
  if let [dx, dy] = xy.as_slice(){
    this.with_matrix(|ctm| ctm.pre_translate((*dx, *dy)) );
  }
}

/// Original scale operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:113, skia-canvas 3.0.8; selected statements retained.
pub fn scale(this:&mut Context2D, xy:Vec<f32>) {
  if let [m11, m22] = xy.as_slice(){
    this.with_matrix(|ctm| ctm.pre_scale((*m11, *m22), None) );
  }
}

/// Original rotate operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:124, skia-canvas 3.0.8; selected statements retained.
pub fn rotate(this:&mut Context2D, radians:f32) {
  let degrees = radians / PI * 180.0;
  this.with_matrix(|ctm| ctm.pre_rotate(degrees, None) );
}

/// Original resetTransform operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:134, skia-canvas 3.0.8; selected statements retained.
pub fn resetTransform(this:&mut Context2D) {
  this.with_matrix(|ctm| ctm.reset() );
}

/// Original beginPath operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:206, skia-canvas 3.0.8; selected statements retained.
pub fn beginPath(this:&mut Context2D) {
  this.path = Path::new();
}

/// Original rect operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:216, skia-canvas 3.0.8; selected statements retained.
pub fn rect(this:&mut Context2D, nums:Vec<f32>) {
  if let [x, y, w, h] = nums.as_slice(){
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    let quad = this.state.matrix.map_rect_to_quad(rect);
    this.path.move_to(quad[0]);
    this.path.line_to(quad[1]);
    this.path.line_to(quad[2]);
    this.path.line_to(quad[3]);
    this.path.close();
  }
}

/// Original roundRect operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:233, skia-canvas 3.0.8; selected statements retained.
pub fn roundRect(this:&mut Context2D, nums:Vec<f32>) {
  if let [x, y, w, h] = &nums[..4]{
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    let radii:Vec<Point> = nums[4..].chunks(2).map(|xy| Point::new(xy[0], xy[1])).collect();
    let rrect = RRect::new_rect_radii(rect, &[radii[0], radii[1], radii[2], radii[3]]);
    let direction = if w.signum() == h.signum(){ PathDirection::CW }else{ PathDirection::CCW };

    let matrix = this.state.matrix;
    let path = Path::rrect(rrect, Some(direction));
    this.path.add_path(&path.with_transform(&matrix), (0,0), Extend);
  }

}

/// Original arc operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:254, skia-canvas 3.0.8; selected statements retained.
pub fn arc(this:&mut Context2D, nums:Vec<f32>, ccw:bool) {
  if let [x, y, radius, start_angle, end_angle] = nums.as_slice(){
    let matrix = this.state.matrix;
    let mut arc = Path2D::default();
    arc.add_ellipse((*x, *y), (*radius, *radius), 0.0, *start_angle, *end_angle, ccw);
    this.path.add_path(&arc.path.with_transform(&matrix), (0,0), Extend);
  }
}

/// Original ellipse operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:269, skia-canvas 3.0.8; selected statements retained.
pub fn ellipse(this:&mut Context2D, nums:Vec<f32>, ccw:bool) -> Result<(), &'static str> {
  if let [x, y, x_radius, y_radius, rotation, start_angle, end_angle] = nums.as_slice(){
    if *x_radius < 0.0 || *y_radius < 0.0 {
      return Err("Radius value must be positive")
    }
    let matrix = this.state.matrix;
    let mut arc = Path2D::default();
    arc.add_ellipse((*x, *y), (*x_radius, *y_radius), *rotation, *start_angle, *end_angle, ccw);
    this.path.add_path(&arc.path.with_transform(&matrix), (0,0), Extend);
  }
  Ok(())
}

/// Original moveTo operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:289, skia-canvas 3.0.8; selected statements retained.
pub fn moveTo(this:&mut Context2D, xy:Vec<f32>) {
  if let Some(dst) = this.map_points(&xy).first(){
    this.path.move_to(*dst);
  }
}

/// Original lineTo operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:300, skia-canvas 3.0.8; selected statements retained.
pub fn lineTo(this:&mut Context2D, xy:Vec<f32>) {
  if let Some(dst) = this.map_points(&xy).first(){
    this.scoot(*dst);
    this.path.line_to(*dst);
  }
}

/// Original arcTo operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:312, skia-canvas 3.0.8; selected statements retained.
pub fn arcTo(this:&mut Context2D, coords:Vec<f32>, radius:f32) -> Result<(), &'static str> {
  if radius < 0.0 {
    return Err("Radius value must be positive")
  }

  if let [src, dst] = this.map_points(&coords)[..2]{
    this.scoot(src);
    this.path.arc_to_tangent(src, dst, radius);
  }
  Ok(())
}

/// Original bezierCurveTo operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:329, skia-canvas 3.0.8; selected statements retained.
pub fn bezierCurveTo(this:&mut Context2D, coords:Vec<f32>) {
  if let [cp1, cp2, dst] = this.map_points(&coords)[..3]{
    this.scoot(cp1);
    this.path.cubic_to(cp1, cp2, dst);
  }
}

/// Original quadraticCurveTo operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:341, skia-canvas 3.0.8; selected statements retained.
pub fn quadraticCurveTo(this:&mut Context2D, coords:Vec<f32>) {
  if let [cp, dst] = this.map_points(&coords)[..2]{
    this.scoot(cp);
    this.path.quad_to(cp, dst);
  }
}

/// Original conicCurveTo operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:354, skia-canvas 3.0.8; selected statements retained.
pub fn conicCurveTo(this:&mut Context2D, args:Vec<f32>) {
  if let [src, dst] = this.map_points(&args[..4]).as_slice(){
    this.scoot(*src);
    this.path.conic_to((src.x, src.y), (dst.x, dst.y), args[4]);
  }
}

/// Original closePath operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:366, skia-canvas 3.0.8; selected statements retained.
pub fn closePath(this:&mut Context2D) {
  this.path.close();
}

/// Original set_lineCap operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:627, skia-canvas 3.0.8; selected statements retained.
pub fn set_lineCap(this:&mut Context2D, name:&str) {
  if let Some(mode) = to_stroke_cap(&name){
    this.state.paint.set_stroke_cap(mode);
  }
}

/// Original set_lineJoin operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:663, skia-canvas 3.0.8; selected statements retained.
pub fn set_lineJoin(this:&mut Context2D, name:&str) {
  if let Some(mode) = to_stroke_join(&name){
    this.state.paint.set_stroke_join(mode);
  }
}

/// Original set_lineWidth operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:682, skia-canvas 3.0.8; selected statements retained.
pub fn set_lineWidth(this:&mut Context2D, num:Option<f32>) {
  if let Some(num) = num{
    if num > 0.0 {
      this.state.paint.set_stroke_width(num);
      this.state.stroke_width = num;
    }
  }
}

/// Original set_miterLimit operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:702, skia-canvas 3.0.8; selected statements retained.
pub fn set_miterLimit(this:&mut Context2D, num:Option<f32>) {
  if let Some(num) = num{
    if num > 0.0 {
      this.state.paint.set_stroke_miter(num);
    }
  }
}

/// Original set_lineDashOffset operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:646, skia-canvas 3.0.8; selected statements retained.
pub fn set_lineDashOffset(this:&mut Context2D, num:f32) {
  this.state.line_dash_offset = num;
}

/// Original setLineDash operation after typed argument extraction; geometry is f32 canvas units,
/// rotations/ranges are radians, scale is unitless, styles are original strings. Vectors must have
/// the original API arity (validated by adapters); returns unit or original radius error string.
/// Owner thread only; retains original Context/Path/State ownership, with no Send/Sync changes.
/// Upstream: src/context/api.rs:590, skia-canvas 3.0.8; selected statements retained.
pub fn setLineDash(this:&mut Context2D, values:Vec<f32>, length:usize) {
    let mut intervals = values.iter().cloned()
      .filter(|n| *n >= 0.0 && n.is_finite())
      .collect::<Vec<f32>>();

    // only apply if all elements were actually numbers
    if length == intervals.len(){
      if intervals.len() % 2 == 1{
        intervals.append(&mut intervals.clone());
      }

      this.state.line_dash_list = intervals
    }
}

/// Original projection from coordinate basis to output quad, f32 canvas units.
/// Zero/one/two basis points expand using current bounds/size/edges; destination
/// one/two points expand as size/edges. Returns owned Skia Matrix or original error.
/// Does not modify Context/CTM; owner thread only, no GPU ownership transfer.
/// Upstream: src/context/api.rs:142; only JS allocation/error boundary changes.
pub fn createProjection(this:&Context2D, dst:Vec<Point>, src:Vec<Point>) -> Result<Matrix,String> {
  let basis:Vec<Point> = match src.len(){
    0 => this.bounds.to_quad().to_vec(), // use canvas dims
    1 => Rect::from_wh(src[0].x, src[0].y).to_quad().to_vec(), // implicit 0,0 origin
    2 => Rect::new(src[0].x, src[0].y, src[1].x, src[1].y).to_quad().to_vec(), // lf/top, rt/bot
    _ => src.clone(),
  };

  let quad:Vec<Point> = match dst.len(){
    1 => Rect::from_wh(dst[0].x, dst[0].y).to_quad().to_vec(), // implicit 0,0 origin
    2 => Rect::new(dst[0].x, dst[0].y, dst[1].x, dst[1].y).to_quad().to_vec(), // lf/top, rt/bot
    _ => dst.clone(),
  };

  match (Matrix::from_poly_to_poly(&basis, &quad), basis.len() == quad.len()){
    (Some(projection), true) => {
      Ok(projection)
    },
    _ => Err(format!(
      "Expected 2 or 4 x/y points for output quad (got {}) and 0, 1, 2, or 4 points for the coordinate basis (got {})",
      quad.len(), basis.len()
    ))
  }
}
