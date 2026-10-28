#![allow(unused_imports)]
#![allow(dead_code)]
use std::cell::RefCell;
use neon::{prelude::*, types::buffer::TypedArray};
use skia_safe::{
  Image as SkImage, ImageInfo, ISize, ColorType, ColorSpace, AlphaType, Data, Size,
  FontMgr, Picture, PictureRecorder, Rect, image::images,
  svg::{self, Length, LengthUnit},
};
use crate::utils::*;
use crate::context::Context2D;
use crate::font_library::FontLibrary;

use crate::resource::Resource;
pub use canvas_core::image::Image;
pub type BoxedImage = JsBox<RefCell<Resource<Image>>>;

pub use canvas_core::image::{Content, ImageData};

//
// -- Javascript Methods --------------------------------------------------------------------------
//

pub fn new(mut cx: FunctionContext) -> JsResult<BoxedImage> {
  let this = RefCell::new(Resource(Image::default()));
  Ok(cx.boxed(this))
}

pub fn get_src(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedImage>(0)?;
  let this = this.borrow();

  Ok(cx.string(&this.src))
}

pub fn set_src(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedImage>(0)?;
  let mut this = this.borrow_mut();

  let src = cx.argument::<JsString>(1)?.value(&mut cx);
  this.src = src;
  Ok(cx.undefined())
}

pub fn set_data<'a>(mut cx: FunctionContext<'a>) -> NeonResult<Handle<'a, JsBoolean>> {
  let this = cx.argument::<BoxedImage>(0)?;
  let mut this = this.borrow_mut();
  let buffer = cx.argument::<JsBuffer>(1)?;
  let data = Data::new_copy(buffer.as_slice(&cx));

  let raw_info = opt_image_info_arg(&mut cx, 2)?;
  this.decode(data, raw_info);

  Ok(cx.boolean(this.content.is_drawable()))
}

pub fn get_width(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedImage>(0)?;
  let this = this.borrow();
  Ok(cx.number(this.content.size().width).upcast())
}

pub fn get_height(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedImage>(0)?;
  let this = this.borrow();
  Ok(cx.number(this.content.size().height).upcast())
}

pub fn get_complete(mut cx: FunctionContext) -> JsResult<JsBoolean> {
  let this = cx.argument::<BoxedImage>(0)?;
  let this = this.borrow();
  Ok(cx.boolean(this.content.is_complete()))
}

pub fn pixels(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedImage>(0)?;
  let this = this.borrow_mut();
  let (color_type, color_space) = image_data_settings_arg(&mut cx, 1);

  let info = ImageInfo::new(this.content.size().to_floor(), color_type, AlphaType::Unpremul, color_space);
  let mut pixels = cx.buffer(info.bytes_per_pixel() * (info.width() * info.height()) as usize)?;

  match &this.content{
    Content::Bitmap(image) => {
      match image.read_pixels(&info, pixels.as_mut_slice(&mut cx), info.min_row_bytes(), (0,0), skia_safe::image::CachingHint::Allow){
        true => Ok(pixels.upcast()),
        false => Ok(cx.undefined().upcast())
      }

    }
    _ => Ok(cx.undefined().upcast())
  }
}
