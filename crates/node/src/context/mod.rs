//! Neon wrapper/value conversions only; Context2D/State and drawing live in core.
use std::cell::RefCell;
use neon::prelude::*;
use crate::utils::*;
use crate::resource::Resource;
use crate::gradient::BoxedCanvasGradient;
use crate::pattern::BoxedCanvasPattern;
use crate::texture::BoxedCanvasTexture;
pub use canvas_core::context::*;
pub mod api;
pub mod page;
pub type BoxedContext2D = JsBox<RefCell<Resource<Context2D>>>;

/// Node value conversion for core Dye; no rendering/state model is duplicated.
pub trait DyeBindings: Sized {
  fn new<'a>(cx: &mut FunctionContext<'a>, value: Handle<'a, JsValue>) -> Option<Self>;
  fn value<'a>(&self, cx: &mut FunctionContext<'a>) -> JsResult<'a, JsValue>;
}
impl DyeBindings for Dye {
  /// Preserve original Node shader downcasts/color conversion and JS return/error rules; owner thread only.
  fn new<'a>(cx: &mut FunctionContext<'a>, value: Handle<'a, JsValue>) -> Option<Self> {
    if let Ok(gradient) = value.downcast::<BoxedCanvasGradient, _>(cx){
      Some(Dye::Gradient(gradient.borrow().0.clone()) )
    }else if let Ok(pattern) = value.downcast::<BoxedCanvasPattern, _>(cx){
      Some(Dye::Pattern(pattern.borrow().0.clone()) )
    }else if let Ok(texture) = value.downcast::<BoxedCanvasTexture, _>(cx){
      Some(Dye::Texture(texture.borrow().0.clone()) )
    }else{
      color_in(cx, value).map(Dye::Color)
    }
  }

  /// Preserve original Node shader downcasts/color conversion and JS return/error rules; owner thread only.
  fn value<'a>(&self, cx: &mut FunctionContext<'a>) -> JsResult<'a, JsValue> {
    match self{
      Dye::Color(color) => color_to_css(cx, color),
      _ => Ok(cx.null().upcast()) // flag to the js context that it should use its cached pattern/gradient ref
    }
  }

}
