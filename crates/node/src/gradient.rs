#![allow(non_snake_case)]
use std::cell::RefCell;
use neon::prelude::*;
use skia_safe::Point;
use crate::utils::*;
use crate::resource::Resource;
pub use canvas_core::gradient::CanvasGradient;
pub type BoxedCanvasGradient = JsBox<RefCell<Resource<CanvasGradient>>>;

// -- Javascript Methods --------------------------------------------------------------------------
//

/// Read original four JS coordinates (canvas units) and box the owned core linear ramp; original Neon errors propagate.
/// Node-thread adapter only. JsBox/RefCell ownership is unchanged except for the contained Resource<T> wrapper.
/// Upstream: src/gradient.rs:121, skia-canvas 3.0.8. Rendering bodies retained.
pub fn linear(mut cx: FunctionContext) -> JsResult<BoxedCanvasGradient> {
  let nums = &float_args(&mut cx, &["x1", "y1", "x2", "y2"])?[..4];
  let [x1, y1, x2, y2] = nums else{ panic!() };

  let start = Point::new(*x1, *y1);
  let end = Point::new(*x2, *y2);
  let canvas_gradient = CanvasGradient::linear(start, end);
  let this = RefCell::new(Resource(canvas_gradient));
  Ok(cx.boxed(this))
}

/// Read original six JS center/radius coordinates (canvas units) and box the core ramp; original Neon errors propagate.
/// Node-thread adapter only. JsBox/RefCell ownership is unchanged except for the contained Resource<T> wrapper.
/// Upstream: src/gradient.rs:133, skia-canvas 3.0.8. Rendering bodies retained.
pub fn radial(mut cx: FunctionContext) -> JsResult<BoxedCanvasGradient> {
  let nums = &float_args(&mut cx, &["x1", "y1", "r1", "x2", "y2", "r2"])?[..6];
  let [x1, y1, r1, x2, y2, r2] = nums else{ panic!() };

  let start_point = Point::new(*x1, *y1);
  let end_point = Point::new(*x2, *y2);
  let canvas_gradient = CanvasGradient::radial(start_point, *r1, end_point, *r2);
  let this = RefCell::new(Resource(canvas_gradient));
  Ok(cx.boxed(this))
}

/// Read original JS angle (radians) and center coordinates; box the core sweep ramp, preserving Neon errors.
/// Node-thread adapter only. JsBox/RefCell ownership is unchanged except for the contained Resource<T> wrapper.
/// Upstream: src/gradient.rs:145, skia-canvas 3.0.8. Rendering bodies retained.
pub fn conic(mut cx: FunctionContext) -> JsResult<BoxedCanvasGradient> {
  let nums = &float_args(&mut cx, &["theta", "x", "y"])?[..3];
  let [theta, x, y] = nums else{ panic!() };

  let center = Point::new(*x, *y);
  let canvas_gradient = CanvasGradient::conic(*theta, center);
  let this = RefCell::new(Resource(canvas_gradient));
  Ok(cx.boxed(this))
}

/// Read JS offset/color, retain original range/type errors, mutate shared core ramp, and return JS undefined.
/// Node-thread adapter only. JsBox/RefCell ownership is unchanged except for the contained Resource<T> wrapper.
/// Upstream: src/gradient.rs:157, skia-canvas 3.0.8. Rendering bodies retained.
pub fn addColorStop(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedCanvasGradient>(0)?;
  let mut this = this.borrow_mut();

  let offset = float_arg(&mut cx, 1, "offset")?;
  CanvasGradient::validate_offset(offset).or_else(|e| cx.throw_range_error(e))?;

  if let Some(color) = opt_color_arg(&mut cx, 2) {
    this.add_color_stop(offset, color);
  }else{
    return cx.throw_type_error(match cx.len(){
      3 => "Could not be parsed as a color",
      _ => "not enough arguments"
    })
  }

  Ok(cx.undefined())
}

/// Borrow the core resource and return its original style as a JS string; downcast/borrow errors remain unchanged.
/// Node-thread adapter only. JsBox/RefCell ownership is unchanged except for the contained Resource<T> wrapper.
/// Upstream: src/gradient.rs:178, skia-canvas 3.0.8. Rendering bodies retained.
pub fn repr(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedCanvasGradient>(0)?;
  let this = this.borrow();
  let style = this.repr();

  Ok(cx.string(style))
}