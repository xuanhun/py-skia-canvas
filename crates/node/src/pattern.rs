#![allow(non_snake_case)]
use std::cell::RefCell;
use neon::prelude::*;
use skia_safe::Matrix;
use crate::utils::*;
use crate::image::{BoxedImage, Content};
use crate::context::BoxedContext2D;
use crate::resource::Resource;
pub use canvas_core::pattern::CanvasPattern;
pub type BoxedCanvasPattern = JsBox<RefCell<Resource<CanvasPattern>>>;

// -- Javascript Methods --------------------------------------------------------------------------
//

/// Read boxed image/canvas size/repetition and box the shared core stamp; preserve original cloning, autosized flag and Neon errors.
/// Node-thread adapter only; JsBox contains Resource<T>, and state clones retain only the original core Rc.
/// Upstream: src/pattern.rs:60, skia-canvas 3.0.8. Rendering bodies retained.
pub fn from_image(mut cx: FunctionContext) -> JsResult<BoxedCanvasPattern> {
  let src = cx.argument::<BoxedImage>(1)?;
  let canvas_width = float_arg_or_bail(&mut cx, 2, "width")?;
  let canvas_height = float_arg_or_bail(&mut cx, 3, "height")?;
  let repeat = repetition_arg(&mut cx, 4)?;

  let src = src.borrow();
  let content = src.content.clone();
  let dims = src.content.size();
  let canvas_pattern = CanvasPattern::from_image(content, dims, src.autosized, canvas_width, canvas_height, repeat);
  let this = RefCell::new(Resource(canvas_pattern));
  Ok(cx.boxed(this))
}

/// Read JS ImageData/repetition and box the core stamp; data dimensions are pixels and original errors propagate.
/// Node-thread adapter only; JsBox contains Resource<T>, and state clones retain only the original core Rc.
/// Upstream: src/pattern.rs:85, skia-canvas 3.0.8. Rendering bodies retained.
pub fn from_image_data(mut cx: FunctionContext) -> JsResult<BoxedCanvasPattern> {
  let src = image_data_arg(&mut cx, 1)?;
  let repeat = repetition_arg(&mut cx, 2)?;
  let canvas_pattern = CanvasPattern::from_image_data(src, repeat);
  let this = RefCell::new(Resource(canvas_pattern));
  Ok(cx.boxed(this))
}

/// Borrow source context on its owner thread, record original vector snapshot/dimensions and box the core stamp; original fallback/errors remain.
/// Node-thread adapter only; JsBox contains Resource<T>, and state clones retain only the original core Rc.
/// Upstream: src/pattern.rs:98, skia-canvas 3.0.8. Rendering bodies retained.
pub fn from_canvas(mut cx: FunctionContext) -> JsResult<BoxedCanvasPattern> {
  let src = cx.argument::<BoxedContext2D>(1)?;
  let repeat = repetition_arg(&mut cx, 2)?;

  let mut ctx = src.borrow_mut();
  let dims = ctx.bounds.size();
  let matrix = Matrix::new_identity();
  let content = ctx.get_picture()
    .map(|picture| Content::Vector(picture, dims))
    .unwrap_or_default();

  let canvas_pattern = CanvasPattern::from_canvas(content, dims, repeat, matrix);
  let this = RefCell::new(Resource(canvas_pattern));
  Ok(cx.boxed(this))
}

/// Read original matrix argument, mutate the shared stamp and return JS undefined; original matrix/downcast errors remain.
/// Node-thread adapter only; JsBox contains Resource<T>, and state clones retain only the original core Rc.
/// Upstream: src/pattern.rs:115, skia-canvas 3.0.8. Rendering bodies retained.
pub fn setTransform(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedCanvasPattern>(0)?;
  let matrix = matrix_arg(&mut cx, 1)?;
  let this = this.borrow();

  this.set_transform(matrix);
  Ok(cx.undefined())
}

/// Return original core pattern representation as JS string; preserve Node/RefCell borrowing and errors.
/// Node-thread adapter only; JsBox contains Resource<T>, and state clones retain only the original core Rc.
/// Upstream: src/pattern.rs:125, skia-canvas 3.0.8. Rendering bodies retained.
pub fn repr(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedCanvasPattern>(0)?;
  let this = this.borrow();

  Ok(cx.string(this.repr()))
}
