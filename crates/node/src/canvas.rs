#![allow(non_snake_case)]
use std::cell::RefCell;
use neon::prelude::*;
use skia_safe::SurfaceProps;
use serde_json::json;
use crate::utils::*;
use crate::context::page::pages_arg;
use crate::gpu;
use crate::resource::Resource;
pub use canvas_core::canvas::Canvas;
pub type BoxedCanvas = JsBox<RefCell<Resource<Canvas>>>;

// -- Javascript Methods --------------------------------------------------------------------------
//

struct CanvasFields<'a,'b>{cx:&'a mut FunctionContext<'b>,opts:Handle<'b,JsObject>}
impl canvas_core::canvas::construction::CanvasArgs for CanvasFields<'_, '_>{
  type Error=neon::result::Throw;
  fn number(&mut self,key:&str)->Option<f64>{opt_double_for_key(self.cx,&self.opts,key)}
  fn flag(&mut self)->NeonResult<bool>{bool_for_key(self.cx,&self.opts,"gpu")}
}
pub fn new(mut cx:FunctionContext)->JsResult<BoxedCanvas>{
  let opts=cx.argument::<JsObject>(1)?;
  let canvas=canvas_core::canvas::construction::construct(&mut CanvasFields{cx:&mut cx,opts}).or_else(|e|match e{
    canvas_core::canvas::construction::OptionsError::Range(msg)=>cx.throw_range_error(msg),
    canvas_core::canvas::construction::OptionsError::Field(e)=>Err(e),
  })?;
  Ok(cx.boxed(RefCell::new(Resource(canvas))))
}

pub fn get_width(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let width = this.borrow().width;
  Ok(cx.number(width as f64))
}

pub fn get_height(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let height = this.borrow().height;
  Ok(cx.number(height as f64))
}

pub fn set_width(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let width = float_arg_or_bail(&mut cx, 1, "size")?;
  if width < 0.0{
    cx.throw_range_error("⚠️Dimensions must be non-zero")?
  }
  this.borrow_mut().width = width;
  Ok(cx.undefined())
}

pub fn set_height(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let height = float_arg_or_bail(&mut cx, 1, "size")?;
  if height < 0.0{
    cx.throw_range_error("⚠️Dimensions must be non-zero")?
  }
  this.borrow_mut().height = height;
  Ok(cx.undefined())
}

pub fn get_engine(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let mut this = this.borrow_mut();
  Ok(cx.string(from_engine(this.engine())))
}

pub fn set_engine(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  if let Some(engine_name) = opt_string_arg(&mut cx, 1){
    if let Some(new_engine) = to_engine(&engine_name){
      if new_engine.selectable() {
        this.borrow_mut().gpu_disabled = matches!(new_engine, gpu::RenderingEngine::CPU);
        this.borrow_mut().engine = Some(new_engine)
      }
    }
  }

  Ok(cx.undefined())
}

pub fn get_engine_status(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let mut this = this.borrow_mut();

  let mut details = this.engine().status(this.gpu_disabled);
  details["textContrast"] = json!(this.text_contrast);
  details["textGamma"] = json!(this.text_gamma);
  Ok(cx.string(details.to_string()))
}

pub fn toBuffer(mut cx: FunctionContext) -> JsResult<JsPromise> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let options = export_options_arg(&mut cx, 2)?;
  let mut pages = pages_arg(&mut cx, 1, &options, &this)?;

  // ensure cached bitmaps are sendable to other thread
  pages.materialize(&this.borrow_mut().engine(), &options);

  let channel = cx.channel();
  let (deferred, promise) = cx.promise();
  rayon::spawn_fifo(move || {
    let result = {
      canvas_core::canvas::exports::encode(&pages, options)
    };

    deferred.settle_with(&channel, move |mut cx| {
      let data = result.or_else(|err| cx.throw_error(err))?;
      let buffer = JsBuffer::from_slice(&mut cx, &data)?;
      Ok(buffer)
    });
  });

  Ok(promise)
}

pub fn toBufferSync(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let options = export_options_arg(&mut cx, 2)?;
  let pages = pages_arg(&mut cx, 1, &options, &this)?;

  let encoded = {
    canvas_core::canvas::exports::encode(&pages, options)
  };

  match encoded{
    Ok(data) => {
      let buffer = JsBuffer::from_slice(&mut cx, &data)?;
      Ok(buffer.upcast::<JsValue>())
    },
    Err(msg) => cx.throw_error(msg)
  }
}

pub fn save(mut cx: FunctionContext) -> JsResult<JsPromise> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let name_pattern = string_arg(&mut cx, 2, "filePath")?;
  let sequence = !cx.argument::<JsValue>(3)?.is_a::<JsUndefined, _>(&mut cx);
  let padding = opt_float_arg(&mut cx, 3).unwrap_or(-1.0);
  let options = export_options_arg(&mut cx, 4)?;
  let mut pages = pages_arg(&mut cx, 1, &options, &this)?;

  // ensure cached bitmaps are sendable to other thread
  pages.materialize(&this.borrow_mut().engine(), &options);

  let channel = cx.channel();
  let (deferred, promise) = cx.promise();
  rayon::spawn_fifo(move || {
    let result = {
      canvas_core::canvas::exports::write(&pages, &name_pattern, padding, sequence, options)
    };

    deferred.settle_with(&channel, move |mut cx| match result{
      Err(msg) => cx.throw_error(format!("I/O Error: {}", msg)),
      _ => Ok(cx.undefined())
    });
  });

  Ok(promise)
}

pub fn saveSync(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedCanvas>(0)?;
  let name_pattern = string_arg(&mut cx, 2, "filePath")?;
  let sequence = !cx.argument::<JsValue>(3)?.is_a::<JsUndefined, _>(&mut cx);
  let padding = opt_float_arg(&mut cx, 3).unwrap_or(-1.0);
  let options = export_options_arg(&mut cx, 4)?;
  let pages = pages_arg(&mut cx, 1, &options, &this)?;

  let result = {
    canvas_core::canvas::exports::write(&pages, &name_pattern, padding, sequence, options)
  };

  match result{
    Ok(_) => Ok(cx.undefined()),
    Err(msg) => cx.throw_error(msg)
  }
}
