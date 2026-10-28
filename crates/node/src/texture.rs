#![allow(non_snake_case)]
use std::cell::RefCell;
use neon::prelude::*;
use skia_safe::Color;
use crate::utils::*;
use crate::resource::Resource;
pub use canvas_core::texture::CanvasTexture;
pub type BoxedCanvasTexture = JsBox<RefCell<Resource<CanvasTexture>>>;

// -- Javascript Methods --------------------------------------------------------------------------
//

/// Read JS path/color/line/cap/radian angle/outline/spacing/offset; preserve original defaults and errors, return boxed core texture.
/// Node-thread adapter only; contained Rc sharing and RefCell/JsBox lifetime are preserved.
/// Upstream: src/texture.rs:93, skia-canvas 3.0.8. Rendering bodies retained.
pub fn new(mut cx: FunctionContext) -> JsResult<BoxedCanvasTexture> {
  let path = opt_skpath_arg(&mut cx, 1);
  let color = opt_color_arg(&mut cx, 2).unwrap_or(Color::BLACK);

  let line = match opt_float_arg(&mut cx, 3){
    Some(weight) => weight,
    None => cx.throw_type_error("Expected a number for `line`")?
  };

  let cap = match to_stroke_cap(&string_arg(&mut cx, 4, "cap")?){
    Some(style) => style,
    None => cx.throw_type_error("Expected \"butt\", \"square\", or \"round\" for `cap`")?
  };

  let angle = match opt_float_arg(&mut cx, 5){
    Some(theta) => theta,
    None => cx.throw_type_error("Expected a number for `angle`")?
  };

  let outline = bool_arg(&mut cx, 6, "outline")?;

  let scale = match opt_float_args(&mut cx, 7..9).as_slice(){
    [h, v] => (*h, *v),
    _ => cx.throw_type_error("Expected a number or array with 2 numbers for `spacing`")?
  };

  let shift = match opt_float_args(&mut cx, 9..11).as_slice(){
    [h, v] => (*h, *v),
    _ => cx.throw_type_error("Expected a number or array with 2 numbers for `offset`")?
  };

  let canvas_texture = CanvasTexture::new(path, color, line, cap, angle, outline, scale, shift);
  let this = RefCell::new(Resource(canvas_texture));
  Ok(cx.boxed(this))
}

/// Borrow boxed texture and return original style as JS string; errors propagate on the Node owner thread.
/// Node-thread adapter only; contained Rc sharing and RefCell/JsBox lifetime are preserved.
/// Upstream: src/texture.rs:130, skia-canvas 3.0.8. Rendering bodies retained.
pub fn repr(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedCanvasTexture>(0)?;
  let this = this.borrow();

  let style = this.repr();
  Ok(cx.string(style))
}