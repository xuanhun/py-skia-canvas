#![allow(dead_code)]
use std::cmp;
use core::ops::Range;
use neon::prelude::*;
use skia_safe::{ Path, Matrix, Point, Color, Data };

//
// meta-helpers
//

fn arg_num(o:usize) -> String{
  // let n = (o + 1) as i32; // we're working with zero-bounded idxs
  let n = o; // arg 0 is always self, so no need to increment the idx
  let ords = ["st","nd","rd"];
  let slot = ((n+90)%100-10)%10 - 1;
  let suffix = if (0..=2).contains(&slot) { ords[slot] } else { "th" };
  format!("{}{}", n, suffix)
}

// pub fn argv<'a>() -> Vec<Handle<'a, JsValue>>{
//   let list:Vec<Handle<JsValue>> = Vec::new();
//   list
// }

// pub fn clamp(val: f32, min:f64, max:f64) -> f32{
//   let min = min as f32;
//   let max = max as f32;
//   if val < min { min } else if val > max { max } else { val }
// }

#[allow(unused_imports)] // Keep the original internal name while adapters migrate.
pub use canvas_core::utils::almost_equal;

#[allow(unused_imports)] // Keep the original internal name while adapters migrate.
pub use canvas_core::utils::almost_zero;

#[allow(unused_imports)] // Preserve the original helper name during adapter migration.
pub use canvas_core::utils::to_degrees;

// The original implementation now lives in the unique language-neutral core.
#[allow(unused_imports)] // Preserve the internal helper name while callers migrate.
pub use canvas_core::utils::to_radians;

pub fn check_argc(cx: &mut FunctionContext, argc:usize) -> NeonResult<()>{
  match cx.len() >= argc {
    true => Ok(()),
    false => cx.throw_type_error("not enough arguments")
  }
}


// pub fn symbol<'a>(cx: &mut FunctionContext<'a>, symbol_name: &str) -> JsResult<'a, JsValue> {
//   let global = cx.global();
//   let symbol_ctor = global
//       .get(cx, "Symbol")?
//       .downcast::<JsObject, _>(cx)
//       .or_throw(cx)?
//       .get(cx, "for")?
//       .downcast::<JsFunction, _>(cx)
//       .or_throw(cx)?;

//   let symbol_label = cx.string(symbol_name);
//   let sym = symbol_ctor.call(cx, global, vec![symbol_label])?;
//   Ok(sym)
// }

//
// plain objects
//

pub fn opt_object_arg<'a>(cx: &mut FunctionContext<'a>, idx:usize) -> Option<Handle<'a, JsObject>>{
  match cx.argument_opt(idx) {
    Some(arg) => match arg.downcast::<JsObject, _>(cx) {
      Ok(obj) => Some(obj),
      Err(_e) => None
    },
    None => None
  }
}

pub fn object_arg<'a>(cx: &mut FunctionContext<'a>, idx:usize, attr:&str) -> NeonResult<Handle<'a, JsObject>>{
  match opt_object_arg(cx, idx){
    Some(val) => Ok(val),
    None => cx.throw_type_error(format!("Exptected an object for \"{}\"", attr))
  }
}

pub fn opt_object_for_key<'a>(cx: &mut FunctionContext<'a>, obj: &Handle<'a, JsObject>, attr:&str) -> Option<Handle<'a, JsObject>>{
  if let Some(val) = obj.get::<JsValue, _, _>(cx, attr).ok(){
    return val.downcast::<JsObject, _>(cx).ok()
  }
  None
}

pub fn object_for_key<'a>(cx: &mut FunctionContext<'a>, obj: &Handle<'a, JsObject>, attr:&str) -> NeonResult<Handle<'a, JsObject>>{
  match opt_object_for_key(cx, &obj, attr){
    Some(val) => Ok(val),
    None => cx.throw_type_error(format!("Exptected an object for \"{}\"", attr))
  }
}

//
// strings
//

pub fn strings_in(cx: &mut FunctionContext, vals: &[Handle<JsValue>]) -> Vec<String>{
  let mut strs:Vec<String> = Vec::new();
  for val in vals.iter() {
    if let Ok(txt) = val.downcast::<JsString, _>(cx){
      let val = txt.value(cx);
      strs.push(val);
    }
  }
  strs
}

pub fn strings_at_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> NeonResult<Vec<String>>{
  let array:Handle<JsArray> = obj.get(cx, attr)?;
  let list = array.to_vec(cx)?;
  Ok(strings_in(cx, &list))
}

pub fn opt_string_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> Option<String>{
  obj.get(cx, attr).ok()
    .and_then(|val:Handle<JsValue>| val.downcast::<JsString, _>(cx).ok() )
    .map(|v| v.value(cx))
}

pub fn string_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> NeonResult<String>{
  let key = cx.string(attr);
  let val:Handle<JsValue> = obj.get(cx, key)?;
  match val.downcast::<JsString, _>(cx){
    Ok(s) => Ok(s.value(cx)),
    Err(_e) => cx.throw_type_error(format!("Exptected a string for \"{}\"", attr))
  }
}

pub fn opt_string_arg(cx: &mut FunctionContext, idx: usize) -> Option<String>{
  match cx.argument_opt(idx) {
    Some(arg) => match arg.downcast::<JsString, _>(cx) {
      Ok(v) => Some(v.value(cx)),
      Err(_e) => None
    },
    None => None
  }
}

pub fn string_arg_or(cx: &mut FunctionContext, idx: usize, default:&str) -> String{
  match opt_string_arg(cx, idx){
    Some(v) => v,
    None => String::from(default)
  }
}

pub fn string_arg(cx: &mut FunctionContext, idx: usize, attr:&str) -> NeonResult<String> {
  let exists = cx.len() > idx;
  match opt_string_arg(cx, idx){
    Some(v) => Ok(v),
    None => cx.throw_type_error(
      if exists { format!("Expected a string for `{}`", attr) }
      else { format!("not enough arguments: expected a string for `{}` as {} arg", attr, arg_num(idx)) }
    )
  }
}

pub fn strings_to_array<'a>(cx: &mut FunctionContext<'a>, strings: &[String]) -> JsResult<'a, JsArray> {
  let array = JsArray::new(cx, strings.len());
  for (i, val) in strings.iter().enumerate() {
    let num = cx.string(val.as_str());
    array.set(cx, i as u32, num)?;
  }
  Ok(array)
}

//
// bools
//

pub fn opt_bool_arg(cx: &mut FunctionContext, idx: usize) -> Option<bool>{
  match cx.argument_opt(idx) {
    Some(arg) => match arg.downcast::<JsBoolean, _>(cx) {
      Ok(v) => Some(v.value(cx)),
      Err(_e) => None
    },
    None => None
  }
}

pub fn bool_arg_or(cx: &mut FunctionContext, idx: usize, default:bool) -> bool{
  match opt_bool_arg(cx, idx){
    Some(v) => v,
    None => default
  }
}

pub fn bool_arg(cx: &mut FunctionContext, idx: usize, attr:&str) -> NeonResult<bool>{
  let exists = cx.len() > idx;
  match opt_bool_arg(cx, idx){
    Some(v) => Ok(v),
    None => cx.throw_type_error(
      if exists { format!("{} must be a boolean", attr) }
      else { format!("not enough arguments: expected a boolean for `{}` as {} arg", attr, arg_num(idx)) }
    )
  }
}

pub fn bool_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> NeonResult<bool>{
  let key = cx.string(attr);
  let val:Handle<JsValue> = obj.get(cx, key)?;
  match val.downcast::<JsBoolean, _>(cx){
    Ok(v) => Ok(v.value(cx) as bool),
    Err(_e) => cx.throw_type_error(format!("Exptected a boolean value for \"{}\"", attr))
  }
}

//
// floats
//


fn _as_double(cx: &mut FunctionContext, val:&Handle<JsValue>) -> Option<f64>{
  // emulate (some of) javascript's wildly permissive type coercion <https://www.w3schools.com/js/js_type_conversion.asp>
  val.downcast::<JsNumber, _>(cx).ok().map(|num|{
    num.value(cx) as f64
  }).or_else(||{
    // strings
    val.downcast::<JsString, _>(cx).ok().and_then(|txt|{
      let s = txt.value(cx);
      canvas_core::utils::parse_number_string(&s)
    })
  }).or_else(||{
    // booleans
    val.downcast::<JsBoolean, _>(cx).ok().map(|b| match b.value(cx) {
      true => 1.0,
      false => 0.0
    })
  }).or_else(||{
    // null
    val.downcast::<JsNull, _>(cx).ok().map(|_| 0.0)
  }).or_else(||{
    // arrays
    val.downcast::<JsArray, _>(cx).ok().and_then(|array|
      match array.len(cx) {
        0 => Some(0.0),
        1 => array.to_vec(cx).ok().and_then(|nums| _as_double(cx, &nums[0])),
        _ => None
      })
  }).and_then(|num| match num.is_finite(){
    true => Some(num),
    false => None
  })
}

fn _as_float(cx: &mut FunctionContext, val:&Handle<JsValue>) -> Option<f32>{
  _as_double(cx, val).map(|num| num as f32)
}

pub fn _float_args_at(cx: &mut FunctionContext, start:usize, names:&[&str], or_bail:bool) -> NeonResult<Vec<f32>>{
  let argc = cx.len() - start; // args start after the `this` reference
  if argc < names.len() {
    return cx.throw_type_error(format!("not enough arguments (missing: {})", names[argc..].join(", ")));
  }

  // emoji indicates that it will only throw in strict mode
  let prefix = if or_bail{ "⚠️" }else{ "" };

  let mut args:Vec<f32> = Vec::new();
  for (i, name) in names.iter().enumerate(){
    match opt_float_arg(cx, i+start){
      Some(v) => args.push(v),
      None => return cx.throw_type_error(
        format!("{}Expected a number for `{}` as {} arg", prefix, name, arg_num(i+start))
      )
    }
  }

  Ok(args)
}

pub fn opt_double_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> Option<f64>{
  obj.get(cx, attr).ok().and_then(|val| _as_double(cx, &val))
}

pub fn opt_float_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> Option<f32>{
  obj.get(cx, attr).ok().and_then(|val| _as_float(cx, &val))
}

pub fn float_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> NeonResult<f32>{
  match opt_float_for_key(cx, &obj, attr) {
    Some(num) => Ok(num),
    None => cx.throw_type_error(format!("Exptected a numerical value for \"{}\"", attr))
  }
}

pub fn floats_in(cx: &mut FunctionContext, vals: &[Handle<JsValue>]) -> Vec<f32>{
  vals.iter().filter_map(|val| _as_float(cx, val)).collect::<Vec<f32>>()
}

pub fn opt_float_arg(cx: &mut FunctionContext, idx: usize) -> Option<f32>{
  cx.argument_opt(idx).and_then(|val| _as_float(cx, &val))
}

pub fn float_arg_or(cx: &mut FunctionContext, idx: usize, default:f32) -> f32{
  match opt_float_arg(cx, idx){
    Some(v) => v,
    None => default as f32
  }
}

pub fn float_arg(cx: &mut FunctionContext, idx: usize, attr:&str) -> NeonResult<f32>{
  _float_args_at(cx, idx, &[attr], false)
    .map(|vec| vec.into_iter().nth(0).unwrap())
}


pub fn float_arg_or_bail(cx: &mut FunctionContext, idx: usize, attr:&str) -> NeonResult<f32>{
  _float_args_at(cx, idx, &[attr], true)
    .map(|vec| vec.into_iter().nth(0).unwrap())
}

pub fn floats_to_array<'a>(cx: &mut FunctionContext<'a>, nums: &[f32]) -> JsResult<'a, JsValue> {
  let array = JsArray::new(cx, nums.len());
  for (i, val) in nums.iter().enumerate() {
    let num = cx.number(*val);
    array.set(cx, i as u32, num)?;
  }
  Ok(array.upcast())
}

//
// float spreads
//

pub fn opt_float_args(cx: &mut FunctionContext, rng: Range<usize>) -> Vec<f32>{
  let end = cmp::min(rng.end, cx.len() as usize);
  let rng = rng.start..end;

  let mut args:Vec<f32> = Vec::new();
  for i in rng.start..end{
    if let Some(val) = opt_float_arg(cx, i){
      args.push(val);
    }
  }
  args
}

pub fn float_args(cx: &mut FunctionContext, names:&[&str]) -> NeonResult<Vec<f32>>{
  _float_args_at(cx, 1, names, false)
}

pub fn float_args_at(cx: &mut FunctionContext, start:usize, names:&[&str]) -> NeonResult<Vec<f32>>{
  _float_args_at(cx, start, names, false)
}

pub fn float_args_or_bail(cx: &mut FunctionContext, names:&[&str]) -> NeonResult<Vec<f32>>{
  _float_args_at(cx, 1, names, true)
}

pub fn float_args_or_bail_at(cx: &mut FunctionContext, start:usize, names:&[&str]) -> NeonResult<Vec<f32>>{
  _float_args_at(cx, start, names, true)
}

//
// Colors
//


pub use canvas_core::utils::css_to_color;

pub fn color_in<'a>(cx: &mut FunctionContext<'a>, val: Handle<'a, JsValue>) -> Option<Color> {
  if val.is_a::<JsString, _>(cx) {
    let css = val.downcast::<JsString, _>(cx).unwrap().value(cx);
    return css_to_color(&css)
  }else{
    // for other objects, try calling their .toString() method (if it exists)
    let obj = val.downcast::<JsObject, _>(cx).ok()?;
    let attr = obj.get::<JsValue, _, _>(cx, "toString").ok()?;
    let to_string = attr.downcast::<JsFunction, _>(cx).ok()?;
    let result = to_string.call(cx, obj, vec![]).ok()?;
    let css = result.downcast::<JsString, _>(cx).ok()?.value(cx);
    css_to_color(&css)
  }
}

pub fn opt_color_arg(cx: &mut FunctionContext, idx: usize) -> Option<Color> {
  match cx.argument_opt(idx) {
    Some(arg) => color_in(cx, arg),
    _ => None
  }
}

pub fn opt_color_for_key(cx: &mut FunctionContext, obj: &Handle<JsObject>, attr:&str) -> Option<Color>{
  obj.get(cx, attr).ok()
    .and_then(|val|
      color_in(cx, val)
    )
}


pub fn color_to_css<'a>(cx: &mut FunctionContext<'a>, color:&Color) -> JsResult<'a, JsValue> {
  Ok(cx.string(canvas_core::utils::color_to_css_string(color)).upcast())
}

//
// Matrices
//

// pub fn matrix_in(cx: &mut FunctionContext, vals:&[Handle<JsValue>]) -> NeonResult<Matrix>{
//   // for converting single js-array args
//   let terms = floats_in(vals);
//   match to_matrix(&terms){
//     Some(matrix) => Ok(matrix),
//     None => cx.throw_error(format!("expected 6 or 9 matrix values (got {})", terms.len()))
//   }
// }

pub use canvas_core::utils::to_matrix;

// pub fn matrix_args(cx: &mut FunctionContext, rng: Range<usize>) -> NeonResult<Matrix>{
//   // for converting inline args (e.g., in Path.transform())
//   let terms = opt_float_args(cx, rng);
//   match to_matrix(&terms){
//     Some(matrix) => Ok(matrix),
//     None => cx.throw_error(format!("expected 6 or 9 matrix values (got {})", terms.len()))
//   }
// }

pub fn opt_matrix_arg(cx: &mut FunctionContext, idx: usize) -> Option<Matrix>{
  if let Some(arg) = cx.argument_opt(idx) {
    if let Ok(array) = arg.downcast::<JsArray, _>(cx) {
      if let Ok(vals) = array.to_vec(cx){
        let terms = floats_in(cx, &vals);
        return to_matrix(&terms)
      }
    }
  }
  None
}

pub fn matrix_arg(cx: &mut FunctionContext, idx:usize) -> NeonResult<Matrix> {
  match opt_matrix_arg(cx, idx){
    Some(v) => Ok(v),
    None => cx.throw_type_error("Expected a DOMMatrix")
  }
}

//
// Points
//

pub fn points_arg(cx: &mut FunctionContext, idx: usize) -> NeonResult<Vec<Point>>{
  let mut nums:Vec<f32> = vec![];
  if let Some(arg) = cx.argument_opt(idx) {
    if let Ok(array) = arg.downcast::<JsArray, _>(cx) {
      if let Ok(vals) = array.to_vec(cx){
        nums = floats_in(cx, &vals);
      }
    }
  }

  if nums.len() % 2 == 1{
    let which = if idx==1{ "first" }else if idx==2{ "second" }else{ "an" };
    cx.throw_type_error(
      format!("Lists of x/y points must have an even number of values (got {} in {} argument)", nums.len(), which)
    )
  }else{
    let points = nums
      .as_slice()
      .chunks_exact(2)
      .map(|pair| Point::new(pair[0], pair[1]))
      .collect();
    Ok(points)
  }
}


//
// Image & ImageData
//

use crate::image::ImageData;
use neon::types::buffer::TypedArray;
use skia_safe::{ColorType, ColorSpace, ImageInfo, AlphaType};

pub fn opt_image_info_arg(cx: &mut FunctionContext, idx:usize) -> NeonResult<Option<ImageInfo>>{
  if let Some(raw_info) = opt_object_arg(cx, idx){
     Ok(Some(ImageInfo::new(
        (
          float_for_key(cx, &raw_info, "width")? as _,
          float_for_key(cx, &raw_info, "height")? as _
        ),
        ColorType::RGBA8888,
        match bool_for_key(cx, &raw_info, "premultiplied")?{
          false => AlphaType::Unpremul,
          true => AlphaType::Premul
        },
        ColorSpace::new_srgb(),
      )))
  }else{
    Ok(None)
  }
}

pub fn image_data_arg(cx: &mut FunctionContext, idx:usize) -> NeonResult<ImageData>{
  let obj = object_arg(cx, idx, "imageData")?;
  let width = float_for_key(cx, &obj, "width")?;
  let height = float_for_key(cx, &obj, "height")?;
  let color_type = string_for_key(cx, &obj, "colorType")?;
  let color_space = string_for_key(cx, &obj, "colorSpace")?;
  let js_buffer: Handle<JsBuffer> = obj.get(cx, "data")?;
  let buffer = Data::new_copy(js_buffer.as_slice(cx));

  Ok(ImageData::new(buffer, width, height, color_type, color_space))
}

pub fn image_data_settings_arg(cx: &mut FunctionContext, idx:usize) -> (ColorType, ColorSpace){
  match opt_object_arg(cx, idx){
    Some(obj) => {
      let color_type = opt_string_for_key(cx, &obj, "colorType").unwrap_or("rgba".to_string());
      let color_space = opt_string_for_key(cx, &obj, "colorSpace").unwrap_or("srgb".to_string());
      (to_color_type(&color_type), to_color_space(&color_space))
    }
    None => (ColorType::RGBA8888, ColorSpace::new_srgb())
  }
}

pub fn image_data_export_arg(cx: &mut FunctionContext, idx:usize) -> (ColorType, ColorSpace, Option<Color>, f32, Option<usize>){
  match opt_object_arg(cx, idx){
    Some(obj) => {
      let color_type = opt_string_for_key(cx, &obj, "colorType").unwrap_or("rgba".to_string());
      let color_space = opt_string_for_key(cx, &obj, "colorSpace").unwrap_or("srgb".to_string());
      let matte = opt_color_for_key(cx, &obj, "matte");
      let density = opt_float_for_key(cx, &obj, "density").unwrap_or(1.0);
      let msaa = opt_float_for_key(cx, &obj, "msaa").map(|n| n as usize);
      (to_color_type(&color_type), to_color_space(&color_space), matte, density, msaa)
    }
    None => (ColorType::RGBA8888, ColorSpace::new_srgb(), None, 1.0, None)
  }
}


pub use canvas_core::utils::to_color_space;

pub fn from_color_space(mode:ColorSpace) -> String{
  match mode {
    _ => "srgb"
  }.to_string()
}

pub use canvas_core::utils::to_color_type;

pub fn from_color_type(color_type: ColorType) -> String {
  match color_type {
    ColorType::Alpha8 => "Alpha8",
    ColorType::RGB565 => "RGB565",
    ColorType::ARGB4444 => "ARGB4444",
    ColorType::RGBA8888 => "RGBA8888",
    ColorType::RGB888x => "RGB888x",
    ColorType::BGRA8888 => "BGRA8888",
    ColorType::RGBA1010102 => "RGBA1010102",
    ColorType::BGRA1010102 => "BGRA1010102",
    ColorType::RGB101010x => "RGB101010x",
    ColorType::BGR101010x => "BGR101010x",
    ColorType::Gray8 => "Gray8",
    ColorType::RGBAF16Norm => "RGBAF16Norm",
    ColorType::RGBAF16 => "RGBAF16",
    ColorType::RGBAF32 => "RGBAF32",
    ColorType::R8G8UNorm => "R8G8UNorm",
    ColorType::A16Float => "A16Float",
    ColorType::R16G16Float => "R16G16Float",
    ColorType::A16UNorm => "A16UNorm",
    ColorType::R16G16UNorm => "R16G16UNorm",
    ColorType::R16G16B16A16UNorm => "R16G16B16A16UNorm",
    ColorType::SRGBA8888 => "SRGBA8888",
    ColorType::R8UNorm => "R8UNorm",
    _ => "unknown"
  }.to_string()
}

//
// ExportOptions
//

use crate::context::page::ExportOptions;

struct ExportFields<'a,'b>{cx:&'a mut FunctionContext<'b>,opts:Handle<'b,JsObject>}
impl canvas_core::canvas::options::ExportArgs for ExportFields<'_, '_>{
  type Error=neon::result::Throw;
  fn string(&mut self,name:&str)->Result<String,Self::Error>{string_for_key(self.cx,&self.opts,name)}
  fn flag(&mut self,name:&str)->Result<bool,Self::Error>{bool_for_key(self.cx,&self.opts,name)}
  fn number(&mut self,name:&str)->Result<f32,Self::Error>{float_for_key(self.cx,&self.opts,name)}
  fn optional_number(&mut self,name:&str)->Option<f32>{opt_float_for_key(self.cx,&self.opts,name)}
  fn optional_string(&mut self,name:&str)->Option<String>{opt_string_for_key(self.cx,&self.opts,name)}
  fn color(&mut self,name:&str)->Option<Color>{opt_color_for_key(self.cx,&self.opts,name)}
}

pub fn export_options_arg(cx:&mut FunctionContext,idx:usize)->NeonResult<ExportOptions>{
  let opts=opt_object_arg(cx,idx).unwrap();
  canvas_core::canvas::options::export_options_arg(&mut ExportFields{cx,opts})
}
//
// Path2D
//

use crate::path::{BoxedPath2D};

pub fn opt_skpath_arg(cx: &mut FunctionContext, idx:usize) -> Option<Path> {
  if let Some(arg) = cx.argument_opt(idx){
    if let Ok(arg) = arg.downcast::<BoxedPath2D, _>(cx){
      let arg = arg.borrow();
      return Some(arg.path.clone())
    }
  }
  None
}

pub fn path2d_arg<'a>(cx: &mut FunctionContext<'a>, idx: usize) -> NeonResult<Handle<'a, BoxedPath2D>>{
  if cx.len() <= idx {
    return cx.throw_type_error(format!("not enough arguments (missing: Path2D as {} arg)", arg_num(idx)));
  }

  match cx.argument::<JsValue>(idx)?.downcast::<BoxedPath2D, _>(cx){
    Ok(path_obj) => Ok(path_obj),
    Err(_) => cx.throw_type_error(format!("Expected a Path2D for {} arg", arg_num(idx)))
  }
}

//
// Filters
//

use crate::filter::{FilterSpec, FilterQuality};

struct FilterFields<'a,'b> { cx:&'a mut FunctionContext<'b>,arg:Handle<'b,JsObject>,obj:Option<Handle<'b,JsObject>> }
impl canvas_core::filter::arguments::FilterArgs for FilterFields<'_, '_> {
  type Error=neon::result::Throw;
  fn canonical(&mut self)->Result<String,Self::Error>{string_for_key(self.cx,&self.arg,"canonical")}
  fn names(&mut self)->Result<Vec<String>,Self::Error>{
    let obj:Handle<JsObject>=self.arg.get(self.cx,"filters")?;
    let keys=obj.get_own_property_names(self.cx)?.to_vec(self.cx)?;
    let names=strings_in(self.cx,&keys);self.obj=Some(obj);Ok(names)
  }
  fn shadow(&mut self,name:&str)->Result<(Vec<f32>,String),Self::Error>{
    let values=self.obj.unwrap().get::<JsArray,_,_>(self.cx,name)?;
    let nums=values.to_vec(self.cx)?;
    let dims=floats_in(self.cx,&nums);
    let color_str=values.get::<JsString,_,_>(self.cx,3)?.value(self.cx);
    Ok((dims,color_str))
  }
  fn number(&mut self,name:&str)->Result<f32,Self::Error>{Ok(self.obj.unwrap().get::<JsNumber,_,_>(self.cx,name)?.value(self.cx) as f32)}
}

pub fn filter_arg(cx: &mut FunctionContext, idx: usize) -> NeonResult<(String, Vec<FilterSpec>)> {
  let arg=cx.argument::<JsObject>(idx)?;
  canvas_core::filter::arguments::filter_arg(&mut FilterFields{cx,arg,obj:None})
}
pub use canvas_core::utils::to_filter_quality;

pub use canvas_core::utils::from_filter_quality;

//
// CanvasPattern
//

pub fn repetition_arg<'a>(cx: &mut FunctionContext<'a>, idx: usize) -> NeonResult<(TileMode, TileMode)>{
  let repetition = if cx.len() > idx && cx.argument::<JsValue>(idx)?.is_a::<JsNull, _>(cx){
    "".to_string() // null is a valid synonym for "repeat" (as is "")
  }else{
    string_arg(cx, idx, "repetition")?
  };

  match to_repeat_mode(&repetition){
    Some(mode) => Ok(mode),
    None => cx.throw_type_error("Expected `repetition` to be \"repeat\", \"repeat-x\", \"repeat-y\", or \"no-repeat\"")
  }
}

//
// Skia Enums
//

use skia_safe::{TileMode, TileMode::{Decal, Repeat}};
pub use canvas_core::utils::to_repeat_mode;

pub use canvas_core::utils::to_stroke_cap;

pub use canvas_core::utils::from_stroke_cap;

#[allow(unused_imports)] // Preserve the original helper name during adapter migration.
pub use canvas_core::utils::to_stroke_join;

pub use canvas_core::utils::from_stroke_join;


use skia_safe::{BlendMode};
pub use canvas_core::utils::to_blend_mode;

pub use canvas_core::utils::from_blend_mode;

#[allow(unused_imports)] // Preserve helper while all consumers migrate to the core.
pub use canvas_core::utils::to_path_op;

use skia_safe::path_1d_path_effect;
pub use canvas_core::utils::to_1d_style;

pub use canvas_core::utils::from_1d_style;

use skia_safe::PathFillType;

pub fn fill_rule_arg_or(cx: &mut FunctionContext, idx: usize, default: &str) -> NeonResult<PathFillType>{
  let err_msg = format!("Expected `fillRule` to be \"nonzero\" or \"evenodd\" for {} arg", arg_num(idx));

  // if arg is provided, verify that it's a string (if absent use default val)
  let mode = match cx.argument_opt(idx) {
    Some(arg) => match arg.downcast::<JsString, _>(cx) {
      Ok(v) => Ok(v.value(cx)),
      Err(_e) => cx.throw_type_error(&err_msg)
    },
    None => Ok(default.to_string())
  }?;


  canvas_core::utils::fill_rule(&mode, &err_msg).or_else(|e| cx.throw_type_error(e))
}

use crate::gpu::RenderingEngine;
pub fn to_engine(engine_name:&str) -> Option<RenderingEngine>{
  let mode = match engine_name.to_lowercase().as_str(){
    "gpu" => RenderingEngine::GPU,
    "cpu" => RenderingEngine::CPU,
    _ => return None
  };
  Some(mode)
}

pub fn from_engine(engine:RenderingEngine) -> String{
  match engine{
    RenderingEngine::GPU => "gpu",
    RenderingEngine::CPU => "cpu",
  }.to_string()
}

// pub fn blend_mode_arg(cx: &mut FunctionContext, idx: usize, attr: &str) -> NeonResult<BlendMode>{
//   let mode_name = string_arg(cx, idx, attr)?;
//   match to_blend_mode(&mode_name){
//     Some(blend_mode) => Ok(blend_mode),
//     None => cx.throw_error("blendMode must be SrcOver, DstOver, Src, Dst, Clear, SrcIn, DstIn, \
//                             SrcOut, DstOut, SrcATop, DstATop, Xor, Plus, Multiply, Screen, Overlay, \
//                             Darken, Lighten, ColorDodge, ColorBurn, HardLight, SoftLight, Difference, \
//                             Exclusion, Hue, Saturation, Color, Luminosity, or Modulate")
//   }
// }
