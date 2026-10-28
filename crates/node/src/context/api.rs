#![allow(non_snake_case)]
use std::cell::RefCell;
use neon::prelude::*;
use skia_safe::{Matrix, PaintStyle, Rect, Size, Path};
use skia_safe::PaintStyle::{Fill, Stroke};

use super::{Context2D, BoxedContext2D, Dye, DyeBindings, page::ExportOptions};
use crate::canvas::BoxedCanvas;
use crate::path::Path2D;
use crate::image::{BoxedImage, Content};
use crate::filter::Filter;
use crate::typography::{
  font_arg, decoration_arg, font_features,
  opt_spacing_arg
};
use crate::utils::*;

//
// The js interface for the Context2D struct
//

pub fn new(mut cx: FunctionContext) -> JsResult<BoxedContext2D> {
  let this = RefCell::new(crate::resource::Resource(Context2D::new()));
  let parent = cx.argument::<BoxedCanvas>(1)?;
  let parent = parent.borrow();

  this.borrow_mut().reset_size((parent.width, parent.height));
  Ok(cx.boxed(this))
}

pub fn resetSize(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let parent = cx.argument::<BoxedCanvas>(1)?;
  let parent = parent.borrow();

  this.borrow_mut().reset_size((parent.width, parent.height));
  Ok(cx.undefined())
}

pub fn get_size(mut cx: FunctionContext) -> JsResult<JsArray> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let bounds = this.borrow().bounds;

  let array = JsArray::new(&mut cx, 2);
  let width = cx.number(bounds.size().width);
  let height = cx.number(bounds.size().height);
  array.set(&mut cx, 0, width)?;
  array.set(&mut cx, 1, height)?;
  Ok(array)
}

pub fn set_size(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;

  if let [width, height] = opt_float_args(&mut cx, 1..3).as_slice(){
    this.borrow_mut().resize((*width, *height));
  }
  Ok(cx.undefined())
}

pub fn reset(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let size = this.bounds.size();

  this.reset_size(size);
  Ok(cx.undefined())
}

//
// Grid State
//

pub fn save(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  this.push();
  Ok(cx.undefined())
}

pub fn restore(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  this.pop();
  Ok(cx.undefined())
}

pub fn transform(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::operations::transform(&mut this, opt_matrix_arg(&mut cx, 1));
  Ok(cx.undefined())
}

pub fn translate(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let xy = float_args_or_bail(&mut cx, &["x", "y"])?;
  canvas_core::context::operations::translate(&mut this, xy);
  Ok(cx.undefined())
}

pub fn scale(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let xy = float_args_or_bail(&mut cx, &["x", "y"])?;
  canvas_core::context::operations::scale(&mut this, xy);
  Ok(cx.undefined())
}

pub fn rotate(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let radians = float_arg_or_bail(&mut cx, 1, "angle")?;
  canvas_core::context::operations::rotate(&mut this, radians);
  Ok(cx.undefined())
}

pub fn resetTransform(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::operations::resetTransform(&mut this);
  Ok(cx.undefined())
}

pub fn createProjection(mut cx: FunctionContext) -> JsResult<JsArray> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let dst = points_arg(&mut cx, 1)?;
  let src = points_arg(&mut cx, 2)?;

  let projection = canvas_core::context::operations::createProjection(&this, dst, src).or_else(|e| cx.throw_type_error(e))?;
      let array = JsArray::new(&mut cx, 9);
      for i in 0..9 {
        let num = cx.number(projection[i as usize]);
        array.set(&mut cx, i as u32, num)?;
      }
      Ok(array)
}

// -- ctm property ----------------------------------------------------------------------

pub fn get_currentTransform(mut cx: FunctionContext) -> JsResult<JsArray> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow();

  let array = JsArray::new(&mut cx, 9);
  for i in 0..9 {
    let num = cx.number(this.state.matrix[i as usize]);
    array.set(&mut cx, i as u32, num)?;
  }
  Ok(array)
}

pub fn set_currentTransform(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::operations::set_currentTransform(&mut this, opt_matrix_arg(&mut cx, 1));
  Ok(cx.undefined())
}


//
// Bézier Paths
//

pub fn beginPath(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::operations::beginPath(&mut this);
  Ok(cx.undefined())
}

// -- primitives ------------------------------------------------------------------------

pub fn rect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "width", "height"])?;
  canvas_core::context::operations::rect(&mut this, nums);
  Ok(cx.undefined())
}

pub fn roundRect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args(&mut cx, &[
    "x", "y", "width", "height", "r1x", "r1y", "r2x", "r2y", "r3x", "r3y", "r4x", "r4y"
  ])?;
  canvas_core::context::operations::roundRect(&mut this, nums);
  Ok(cx.undefined())
}

pub fn arc(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "radius", "startAngle", "endAngle"])?;
  let ccw = bool_arg_or(&mut cx, 6, false);
  canvas_core::context::operations::arc(&mut this, nums, ccw);
  Ok(cx.undefined())
}

pub fn ellipse(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "xRadius", "yRadius", "rotation", "startAngle", "endAngle"])?;
  let ccw = bool_arg_or(&mut cx, 8, false);
  canvas_core::context::operations::ellipse(&mut this, nums, ccw).or_else(|e| cx.throw_range_error(e))?;
  Ok(cx.undefined())
}

// contour drawing ----------------------------------------------------------------------

pub fn moveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let xy = float_args_or_bail(&mut cx, &["x", "y"])?;
  canvas_core::context::operations::moveTo(&mut this, xy);
  Ok(cx.undefined())
}

pub fn lineTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let xy = float_args_or_bail(&mut cx, &["x", "y"])?;
  canvas_core::context::operations::lineTo(&mut this, xy);
  Ok(cx.undefined())
}

pub fn arcTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let coords = float_args_or_bail(&mut cx, &["x1", "y1", "x2", "y2"])?;
  let radius = float_arg_or_bail(&mut cx, 5, "radius")?;
  canvas_core::context::operations::arcTo(&mut this, coords, radius).or_else(|e| cx.throw_range_error(e))?;
  Ok(cx.undefined())
}

pub fn bezierCurveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let coords = float_args_or_bail(&mut cx, &["cp1x", "cp1y", "cp2x", "cp2y", "x", "y"])?;
  canvas_core::context::operations::bezierCurveTo(&mut this, coords);
  Ok(cx.undefined())
}

pub fn quadraticCurveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let coords = float_args_or_bail(&mut cx, &["cpx", "cpy", "x", "y"])?;
  canvas_core::context::operations::quadraticCurveTo(&mut this, coords);
  Ok(cx.undefined())
}


pub fn conicCurveTo(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let args = float_args_or_bail(&mut cx, &["cpx", "cpy", "x", "y", "weight"])?;
  canvas_core::context::operations::conicCurveTo(&mut this, args);
  Ok(cx.undefined())
}

pub fn closePath(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::operations::closePath(&mut this);
  Ok(cx.undefined())
}

// hit testing --------------------------------------------------------------------------

pub fn isPointInPath(cx: FunctionContext) -> JsResult<JsBoolean> {
  _is_in(cx, Fill)
}

pub fn isPointInStroke(cx: FunctionContext) -> JsResult<JsBoolean> {
  _is_in(cx, Stroke)
}

fn _is_in(mut cx: FunctionContext, style:PaintStyle) -> JsResult<JsBoolean> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let path = opt_skpath_arg(&mut cx, 1);
  let (rule_idx, mut target) = match path{
    Some(path) => (4, path),
    None => match cx.len(){
      5 => cx.throw_type_error("Expected a Path2D for 1st arg")?,
      _ => (3, this.path.clone())
    }
  };

  let rule = match style{
    Stroke => None,
    _ => Some(fill_rule_arg_or(&mut cx, rule_idx, "nonzero")?)
  };

  if let [x, y] = opt_float_args(&mut cx, 1..4).as_slice(){
    Ok(cx.boolean(this.hit_test_path(&mut target, (*x, *y), rule, style)))
  }else{
    check_argc(&mut cx, 3)?;
    Ok(cx.boolean(false))
  }

}

// masking ------------------------------------------------------------------------------

pub fn clip(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let mut shift = 1;
  let path = opt_skpath_arg(&mut cx, 1);
  if path.is_some() { shift += 1; }
  else if cx.len() > 2{
    return cx.throw_type_error("Expected a Path2D for 1st arg")
  }
  let rule = fill_rule_arg_or(&mut cx, shift, "nonzero")?;

  this.clip_path(path, rule);
  Ok(cx.undefined())
}


//
// Fill & Stroke
//

pub fn fill(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let mut shift = 1;
  let path = opt_skpath_arg(&mut cx, 1);
  if path.is_some() { shift += 1; }
  else if cx.len() > 2{
    return cx.throw_type_error("Expected a Path2D for 1st arg")
  }
  let rule = fill_rule_arg_or(&mut cx, shift, "nonzero")?;

  this.draw_path(path, PaintStyle::Fill, Some(rule));
  Ok(cx.undefined())
}

pub fn stroke(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let path = opt_skpath_arg(&mut cx, 1);

  if path.is_none() && cx.len() >= 2{
    return cx.throw_type_error(format!("Expected a Path2D for 1st arg"))
  }

  this.borrow_mut().draw_path(path, PaintStyle::Stroke, None);
  Ok(cx.undefined())
}

pub fn fillRect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;

  let nums = float_args_or_bail(&mut cx, &["x", "y", "width", "height"])?;
  if let [x, y, w, h] = nums.as_slice() {
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    let path = Path::rect(rect, None);
    this.borrow_mut().draw_path(Some(path), PaintStyle::Fill, None);
  }
  Ok(cx.undefined())
}

pub fn strokeRect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;

  let nums = float_args_or_bail(&mut cx, &["x", "y", "width", "height"])?;
  if let [x, y, w, h] = nums.as_slice() {
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    let path = Path::rect(rect, None);
    this.borrow_mut().draw_path(Some(path), PaintStyle::Stroke, None);
  }
  Ok(cx.undefined())
}

pub fn clearRect(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  let nums = float_args_or_bail(&mut cx, &["x", "y", "width", "height"])?;
  if let [x, y, w, h] = nums.as_slice() {
    let rect = Rect::from_xywh(*x, *y, *w, *h);
    this.clear_rect(&rect);
  }
  Ok(cx.undefined())
}


// fill & stoke properties --------------------------------------------------------------

pub fn get_fillStyle(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow();
  let dye = this.state.fill_style.clone();
  dye.value(&mut cx)
}

pub fn set_fillStyle(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let arg = cx.argument::<JsValue>(1)?;

  if let Some(dye) = Dye::new(&mut cx, arg) {
    this.state.fill_style = dye;
  }
  Ok(cx.undefined())
}

pub fn get_strokeStyle(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow();
  let dye = this.state.stroke_style.clone();
  dye.value(&mut cx)
}

pub fn set_strokeStyle(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let arg = cx.argument::<JsValue>(1)?;

  if let Some(dye) = Dye::new(&mut cx, arg) {
    this.state.stroke_style = dye;
  }
  Ok(cx.undefined())
}

//
// Line Style
//

pub fn set_lineDashMarker(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let marker = opt_skpath_arg(&mut cx, 1);

  if marker.is_none(){
    let val = cx.argument::<JsValue>(1)?;
    if !(val.is_a::<JsNull, _>(&mut cx) || val.is_a::<JsNull, _>(&mut cx)){
      return cx.throw_type_error("Expected a Path2D object (or null)");
    }
  }

  this.borrow_mut().state.line_dash_marker = marker;
  Ok(cx.undefined())
}

pub fn get_lineDashMarker(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow();

  match &this.state.line_dash_marker{
    Some(marker) => Ok(cx.boxed(RefCell::new(crate::resource::Resource(Path2D{path:marker.clone()}))).upcast()),
    None => Ok(cx.null().upcast())
  }
}

pub fn set_lineDashFit(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let style = string_arg(&mut cx, 1, "fitStyle")?;

  canvas_core::context::effects::set_lineDashFit(&mut this.borrow_mut(), style);
  Ok(cx.undefined())
}

pub fn get_lineDashFit(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;

  let value = canvas_core::context::effects::get_lineDashFit(&this.borrow());
  Ok(cx.string(value))
}

pub fn getLineDash(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let dashes = this.state.line_dash_list.clone();
  floats_to_array(&mut cx, &dashes)
}

pub fn setLineDash(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let arg = cx.argument::<JsValue>(1)?;
  if arg.is_a::<JsArray, _>(&mut cx) {
    let list = cx.argument::<JsArray>(1)?.to_vec(&mut cx)?;
    canvas_core::context::operations::setLineDash(&mut this, floats_in(&mut cx, &list), list.len());
  }else{
    cx.throw_type_error("Value is not a sequence")?
  }

  Ok(cx.undefined())
}


// line style properties  -----------------------------------------------------------

pub fn get_lineCap(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();

  let mode = this.state.paint.stroke_cap();
  let name = from_stroke_cap(mode);
  Ok(cx.string(name))
}

pub fn set_lineCap(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "lineCap")?;

  canvas_core::context::operations::set_lineCap(&mut this, &name);
  Ok(cx.undefined())
}

pub fn get_lineDashOffset(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();

  let num = this.state.line_dash_offset;
  Ok(cx.number(num))
}

pub fn set_lineDashOffset(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::operations::set_lineDashOffset(&mut this, float_arg_or_bail(&mut cx, 1, "lineDashOffset")?);
  Ok(cx.undefined())
}

pub fn get_lineJoin(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();

  let mode = this.state.paint.stroke_join();
  let name = from_stroke_join(mode);
  Ok(cx.string(name))
}

pub fn set_lineJoin(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "lineJoin")?;

  canvas_core::context::operations::set_lineJoin(&mut this, &name);
  Ok(cx.undefined())
}

pub fn get_lineWidth(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();

  let num = this.state.paint.stroke_width();
  Ok(cx.number(num))
}

pub fn set_lineWidth(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  canvas_core::context::operations::set_lineWidth(&mut this, opt_float_arg(&mut cx, 1));
  Ok(cx.undefined())
}

pub fn get_miterLimit(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();

  let num = this.state.paint.stroke_miter();
  Ok(cx.number(num))
}

pub fn set_miterLimit(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  canvas_core::context::operations::set_miterLimit(&mut this, opt_float_arg(&mut cx, 1));
  Ok(cx.undefined())
}


//
// Imagery
//

fn _layout_rects(cx: &mut FunctionContext, intrinsic:Size, nums:&[f32]) -> NeonResult<(Rect, Rect)> {
  canvas_core::image::operations::layout_rects(intrinsic, nums).or_else(|e| image_error(cx,e))
}

fn image_error<'a,T>(cx:&mut FunctionContext<'a>,error:canvas_core::image::operations::ImageError)->NeonResult<T> {
  match error {
    canvas_core::image::operations::ImageError::Type(e)=>cx.throw_type_error(e),
    canvas_core::image::operations::ImageError::Range(e)=>cx.throw_range_error(e),
    canvas_core::image::operations::ImageError::Error(e)=>cx.throw_error(e),
  }
}

pub fn drawImage(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let argc = cx.len() as usize;
  let source = cx.argument::<JsValue>(1)?;
  let arg_names = ["srcX", "srcY", "srcWidth", "srcHeight", "dstX", "dstY", "dstWidth", "dstHeight"];
  let nums = float_args_or_bail_at(&mut cx, 2, &arg_names[..argc-2])?;

  let content = {
    if let Ok(img) = source.downcast::<BoxedImage, _>(&mut cx){
      img.borrow().content.clone()
    }else if let Ok(ctx) = source.downcast::<BoxedContext2D, _>(&mut cx){
      Content::from_context(&mut ctx.borrow_mut(), false)
    }else if let Ok(image_data) = image_data_arg(&mut cx, 1){
      Content::from_image_data(image_data)
    }else{
      Content::default()
    }
  };

  let autosized=source.downcast::<BoxedImage,_>(&mut cx).ok().map(|i|i.borrow().autosized).unwrap_or(false);
  let result=canvas_core::image::operations::drawImage(&mut this.borrow_mut(),content,autosized,&nums);
  result.or_else(|e|image_error(&mut cx,e))?;
  Ok(cx.undefined())
}

pub fn drawCanvas(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let argc = cx.len() as usize;
  let this = cx.argument::<BoxedContext2D>(0)?;
  let context = cx.argument::<BoxedContext2D>(1)?;
  let arg_names = ["srcX", "srcY", "srcWidth", "srcHeight", "dstX", "dstY", "dstWidth", "dstHeight"];
  let nums = float_args_or_bail_at(&mut cx, 2, &arg_names[..argc-2])?;

  let content = Content::from_context(&mut context.borrow_mut(), true);
  canvas_core::image::operations::drawCanvas(&mut this.borrow_mut(),content,&nums).or_else(|e|image_error(&mut cx,e))?;
  Ok(cx.undefined())
}

pub fn getImageData(mut cx: FunctionContext) -> JsResult<JsBuffer> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut x = float_arg(&mut cx, 1, "x")?.floor();
  let mut y = float_arg(&mut cx, 2, "y")?.floor();
  let mut w = float_arg(&mut cx, 3, "width")?.floor();
  let mut h = float_arg(&mut cx, 4, "height")?.floor();
  let (color_type, color_space, matte, density, msaa) = image_data_export_arg(&mut cx, 5);
  let parent = cx.argument::<BoxedCanvas>(6)?;
  let canvas = &mut parent.borrow_mut();

  // negative dimensions are valid, just shift the origin and absify
  if w < 0.0 { x += w; w *= -1.0; }
  if h < 0.0 { y += h; h *= -1.0; }

  let opts = ExportOptions{matte, density, msaa, color_type, color_space, ..canvas.export_options()};
  let crop = Rect::from_point_and_size((x*density, y*density), (w*density, h*density)).round();
  let engine = canvas.engine();

  let data = this.borrow_mut().get_pixels(crop, opts, engine).or_else(|e| cx.throw_error(e))?;
  let buffer = JsBuffer::from_slice(&mut cx, &data)?;

  Ok(buffer)
}

pub fn putImageData(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let img_data = image_data_arg(&mut cx, 1)?;

  // determine geometry
  let x = float_arg(&mut cx, 2, "dx")?;
  let y = float_arg(&mut cx, 3, "dy")?;
  let mut dirty = match cx.len(){
    5.. => float_args_at(&mut cx, 4, &["dirtyX", "dirtyY", "dirtyWidth", "dirtyHeight"])?,
    _ => [].to_vec()
  };
  canvas_core::image::operations::putImageData(&mut this,img_data,x,y,dirty);
  Ok(cx.undefined())
}

// -- image properties --------------------------------------------------------------

pub fn get_imageSmoothingEnabled(mut cx: FunctionContext) -> JsResult<JsBoolean> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  // Ok(cx.boolean(this.state.image_smoothing_enabled))
  Ok(cx.boolean(this.state.image_filter.smoothing))
}

pub fn set_imageSmoothingEnabled(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let flag = bool_arg(&mut cx, 1, "imageSmoothingEnabled")?;

  this.state.image_filter.smoothing = flag;
  Ok(cx.undefined())
}

pub fn get_imageSmoothingQuality(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let mode = from_filter_quality(this.state.image_filter.quality);
  Ok(cx.string(mode))
}

pub fn set_imageSmoothingQuality(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "imageSmoothingQuality")?;

  if let Some(mode) = to_filter_quality(&name){
    this.state.image_filter.quality = mode;
  }
  Ok(cx.undefined())
}

//
// Typography
//


pub fn fillText(cx: FunctionContext) -> JsResult<JsUndefined> {
  _draw_text(cx, Fill)
}

pub fn strokeText(cx: FunctionContext) -> JsResult<JsUndefined> {
  _draw_text(cx, Stroke)
}

fn _draw_text(mut cx: FunctionContext, style:PaintStyle) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let text = string_arg(&mut cx, 1, "text")?;
  let x = float_arg_or_bail(&mut cx, 2, "x")?;
  let y = float_arg_or_bail(&mut cx, 3, "y")?;
  let width = opt_float_arg(&mut cx, 4);

  // it's fine to include an ignored `undefined` but anything else is invalid
  if width.is_none() && cx.len() > 4 && !cx.argument::<JsValue>(4)?.is_a::<JsUndefined, _>(&mut cx){
    // emoji indicates that it will only throw in strict mode
    cx.throw_type_error("⚠️Expected a number for `width` as 4th arg")?
  }

  this.draw_text(&text, x, y, width, style);
  Ok(cx.undefined())
}


pub fn measureText(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let text = string_arg(&mut cx, 1, "text")?;
  let width = opt_float_arg(&mut cx, 2);
  let text_metrics = this.measure_text(&text, width);
  Ok(cx.string(text_metrics.to_string()))
}

/// Development diagnostic only: original measurement-layout visitor, same owner.
/// UTF-8 text/canvas-unit width ->owned JSON; transient font table bytes must only
/// be hashed/discarded by audit runner. No public Context JS method is added.
pub fn debugGlyphs(mut cx:FunctionContext) -> JsResult<JsString> {
  let this=cx.argument::<BoxedContext2D>(0)?;
  let this=this.borrow_mut();
  let text=string_arg(&mut cx,1,"text")?;
  let width=opt_float_arg(&mut cx,2);
  let report=canvas_core::typography::audit::glyphs(&this.state,&text,width);
  Ok(cx.string(report.to_string()))
}

pub fn outlineText(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();

  let text = string_arg(&mut cx, 1, "text")?;
  let width = match cx.len(){
    3 => Some(float_arg_or_bail(&mut cx, 2, "width")?),
    _ => None
  };
  let path = this.outline_text(&text, width);
  Ok(cx.boxed(RefCell::new(crate::resource::Resource(Path2D{path}))).upcast())
}

// -- type properties ---------------------------------------------------------------

pub fn get_font(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  Ok(cx.string(this.state.font.clone()))
}

pub fn set_font(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  if let Some(spec) = font_arg(&mut cx, 1)?{
    this.set_font(spec);
  }
  Ok(cx.undefined())
}

pub fn get_fontStretch(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_fontStretch(&this);
  Ok(cx.string(value))
}

pub fn set_fontStretch(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  if let Some(stretch) = opt_string_arg(&mut cx, 1){
    let mut this = this.borrow_mut();
    canvas_core::context::text_state::set_fontStretch(&mut this, stretch);
  }
  Ok(cx.undefined())
}

pub fn get_textAlign(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_textAlign(&this);
  Ok(cx.string(value))
}

pub fn set_textAlign(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "textAlign")?;

  canvas_core::context::text_state::set_textAlign(&mut this, name);
  Ok(cx.undefined())
}

pub fn get_textBaseline(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_textBaseline(&this);
  Ok(cx.string(value))
}

pub fn set_textBaseline(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "textBaseline")?;

  canvas_core::context::text_state::set_textBaseline(&mut this, name);
  Ok(cx.undefined())
}

pub fn get_direction(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_direction(&this);
  Ok(cx.string(value))
}

pub fn set_direction(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "direction")?;

  canvas_core::context::text_state::set_direction(&mut this, name);
  Ok(cx.undefined())
}

pub fn get_letterSpacing(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_letterSpacing(&this);
  Ok(cx.string(value))
}

pub fn set_letterSpacing(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::text_state::set_letterSpacing(&mut this, opt_spacing_arg(&mut cx, 1)?);
  Ok(cx.undefined())
}

pub fn get_wordSpacing(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_wordSpacing(&this);
  Ok(cx.string(value))
}

pub fn set_wordSpacing(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();

  canvas_core::context::text_state::set_wordSpacing(&mut this, opt_spacing_arg(&mut cx, 1)?);
  Ok(cx.undefined())
}

// -- non-standard typography extensions --------------------------------------------

pub fn get_fontHinting(mut cx: FunctionContext) -> JsResult<JsBoolean> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_fontHinting(&this);
  Ok(cx.boolean(value))
}

pub fn set_fontHinting(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let flag = bool_arg(&mut cx, 1, "fontHinting")?;
  canvas_core::context::text_state::set_fontHinting(&mut this, flag);
  Ok(cx.undefined())
}

pub fn get_fontVariant(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_fontVariant(&this);
  Ok(cx.string(value))
}

pub fn set_fontVariant(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let arg = cx.argument::<JsObject>(1)?;

  let variant = string_for_key(&mut cx, &arg, "variant")?;
  let feat_obj: Handle<JsObject> = arg.get(&mut cx, "features")?;
  let features = font_features(&mut cx, &feat_obj)?;
  canvas_core::context::text_state::set_fontVariant(&mut this, variant, features);
  Ok(cx.undefined())
}

pub fn get_textWrap(mut cx: FunctionContext) -> JsResult<JsBoolean> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_textWrap(&this);
  Ok(cx.boolean(value))
}

pub fn set_textWrap(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let flag = bool_arg(&mut cx, 1, "textWrap")?;
  canvas_core::context::text_state::set_textWrap(&mut this, flag);
  Ok(cx.undefined())
}

pub fn get_textDecoration(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::text_state::get_textDecoration(&this);
  Ok(cx.string(value))
}

pub fn set_textDecoration(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  if let Ok(arg) = decoration_arg(&mut cx, 1){
    if let Some(deco_style) = arg{
      let mut this = this.borrow_mut();
      canvas_core::context::text_state::set_textDecoration(&mut this, deco_style);
    }
  }

  Ok(cx.undefined())
}

//
// Effects
//

// -- compositing properties --------------------------------------------------------

pub fn get_globalAlpha(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::effects::get_globalAlpha(&this);
  Ok(cx.number(value))
}

pub fn set_globalAlpha(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let num = float_arg_or_bail(&mut cx, 1, "globalAlpha")?;

  canvas_core::context::effects::set_globalAlpha(&mut this, num);
  Ok(cx.undefined())
}

pub fn get_globalCompositeOperation(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::effects::get_globalCompositeOperation(&this);
  Ok(cx.string(value))
}

pub fn set_globalCompositeOperation(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let name = string_arg(&mut cx, 1, "globalCompositeOperation")?;

  canvas_core::context::effects::set_globalCompositeOperation(&mut this, name);
  Ok(cx.undefined())
}

// -- css3 filters ------------------------------------------------------------------

pub fn get_filter(mut cx: FunctionContext) -> JsResult<JsString> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::effects::get_filter(&this);
  Ok(cx.string(value))
}

pub fn set_filter(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  if !cx.argument::<JsValue>(1)?.is_a::<JsNull, _>(&mut cx) {
    let (filter_text, specs) = filter_arg(&mut cx, 1)?;
    canvas_core::context::effects::set_filter(&mut this, filter_text, specs);

  }
  Ok(cx.undefined())
}

// -- dropshadow properties ---------------------------------------------------------

pub fn get_shadowBlur(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::effects::get_shadowBlur(&this);
  Ok(cx.number(value))
}

pub fn set_shadowBlur(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  let num = float_arg_or_bail(&mut cx, 1, "shadowBlur")?;
  canvas_core::context::effects::set_shadowBlur(&mut this, num);
  Ok(cx.undefined())
}

pub fn get_shadowColor(mut cx: FunctionContext) -> JsResult<JsValue> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let shadow_color = canvas_core::context::effects::get_shadowColor(&this);
  color_to_css(&mut cx, &shadow_color)
}

pub fn set_shadowColor(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  canvas_core::context::effects::set_shadowColor(&mut this, opt_color_arg(&mut cx, 1));
  Ok(cx.undefined())
}

pub fn get_shadowOffsetX(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::effects::get_shadowOffsetX(&this);
  Ok(cx.number(value))
}

pub fn get_shadowOffsetY(mut cx: FunctionContext) -> JsResult<JsNumber> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let this = this.borrow_mut();
  let value = canvas_core::context::effects::get_shadowOffsetY(&this);
  Ok(cx.number(value))
}

pub fn set_shadowOffsetX(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  canvas_core::context::effects::set_shadowOffsetX(&mut this, float_arg_or_bail(&mut cx, 1, "shadowOffsetX")?);
  Ok(cx.undefined())
}

pub fn set_shadowOffsetY(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  let this = cx.argument::<BoxedContext2D>(0)?;
  let mut this = this.borrow_mut();
  canvas_core::context::effects::set_shadowOffsetY(&mut this, float_arg_or_bail(&mut cx, 1, "shadowOffsetY")?);
  Ok(cx.undefined())
}
