//! Original JS argument/metadata conversion; shaping and styles are in core.
#![allow(non_snake_case)]
use neon::prelude::*;
use skia_safe::Typeface;
use crate::utils::*;
pub use canvas_core::typography::*;

/// Original Node argument/property conversion; sizes and errors retain source semantics, owner thread only.
pub fn font_arg(cx: &mut FunctionContext, idx: usize) -> NeonResult<Option<FontSpec>> {
  let arg = cx.argument::<JsValue>(idx)?;
  if arg.is_a::<JsNull, _>(cx){ return Ok(None) }

  let font_desc = cx.argument::<JsObject>(idx)?;
  let families = strings_at_key(cx, &font_desc, "family")?;
  let canonical = string_for_key(cx, &font_desc, "canonical")?;
  let variant = string_for_key(cx, &font_desc, "variant")?;
  let size = float_for_key(cx, &font_desc, "size")?;
  let weight = float_for_key(cx, &font_desc, "weight")?;
  let style = string_for_key(cx, &font_desc, "style")?;
  let stretch = string_for_key(cx, &font_desc, "stretch")?;
  let line_height = opt_float_for_key(cx, &font_desc, "lineHeight");

  let feat_obj:Handle<JsObject> = font_desc.get(cx, "features")?;
  let features = font_features(cx, &feat_obj)?;

  Ok(canvas_core::typography::font_spec(families,canonical,variant,size,weight,
                                         &style,&stretch,line_height,features))
}

/// Original Node argument/property conversion; sizes and errors retain source semantics, owner thread only.
pub fn font_features(cx: &mut FunctionContext, obj: &Handle<JsObject>) -> NeonResult<Vec<(String, i32)>>{
  let keys = obj.get_own_property_names(cx)?.to_vec(cx)?;
  let mut features:Vec<(String, i32)> = vec![];
  for key in strings_in(cx, &keys).iter() {
    match key.as_str() {
      "on" | "off" => strings_at_key(cx, obj, key)?.iter().for_each(|feat|{
        features.push( (feat.to_string(), if key == "on"{ 1 } else { 0 }) );
      }),
      _ => features.push( (key.to_string(), float_for_key(cx, obj, key)? as i32))
    }
  }
  Ok(features)
}

/// Original Node argument/property conversion; sizes and errors retain source semantics, owner thread only.
pub fn typeface_details<'a>(cx: &mut FunctionContext<'a>, filename:&str, font: &Typeface, alias:Option<String>) -> JsResult<'a, JsObject> {
  let (family, weight, slant, width) = canvas_core::font_library::typeface_metadata(font, alias);
  let filename = cx.string(filename);
  let family = cx.string(family);
  let weight = cx.number(weight);
  let slant = cx.string(slant);
  let width = cx.string(width);

  let dict = JsObject::new(cx);
  let attr = cx.string("family"); dict.set(cx, attr, family)?;
  let attr = cx.string("weight"); dict.set(cx, attr, weight)?;
  let attr = cx.string("style");  dict.set(cx, attr, slant)?;
  let attr = cx.string("width");  dict.set(cx, attr, width)?;
  let attr = cx.string("file");   dict.set(cx, attr, filename)?;
  Ok(dict)
}

/// Original Node argument/property conversion; sizes and errors retain source semantics, owner thread only.
pub fn decoration_arg(cx: &mut FunctionContext, idx: usize) -> NeonResult<Option<DecorationStyle>> {
  if let Some(deco) = opt_object_arg(cx, idx){
    let mut reader = NodeDecorationArgs{cx,deco};
    canvas_core::typography::decoration::decoration_style(&mut reader)
  }else{
    Ok(None)
  }
}

/// Original Node argument/property conversion; sizes and errors retain source semantics, owner thread only.
pub fn opt_spacing_arg<'a>(cx: &mut FunctionContext<'a>, idx:usize) -> NeonResult<Option<Spacing>>{
  match cx.argument::<JsValue>(idx)?.is_a::<JsNull, _>(cx){
    true => Ok(None),
    false => {
      let spacing = cx.argument::<JsObject>(idx)?;
      Spacing::from_obj(cx, &spacing)
    }
  }
}

/// Node-only object conversion for core Spacing; no spacing arithmetic is duplicated.
pub trait SpacingFromObject: Sized {
  fn from_obj(cx: &mut FunctionContext, spacing:&Handle<JsObject>) -> NeonResult<Option<Self>>;
}
impl SpacingFromObject for Spacing {
  /// Read original raw/unit/px fields and delegate to original core parse; original Neon errors propagate.
  fn from_obj(cx: &mut FunctionContext, spacing:&Handle<JsObject>) -> NeonResult<Option<Self>>{
    let raw_size = float_for_key(cx, &spacing, "size")?;
    let unit = string_for_key(cx, &spacing, "unit")?;
    let px_size = float_for_key(cx, &spacing, "px")?;
    Ok(Self::parse(raw_size, unit, px_size))
  }
}

/// Original decoration argument reads; no Context borrow, original Neon field errors.
struct NodeDecorationArgs<'a,'b> { cx:&'b mut FunctionContext<'a>, deco:Handle<'a,JsObject> }
impl<'a,'b> canvas_core::typography::decoration::DecorationArgs for NodeDecorationArgs<'a,'b> {
  type Error = neon::result::Throw;
  /// Read original owned string, unitless; source typography.rs:decoration_arg.
  fn string(&mut self,name:&str) -> Result<String,Self::Error> {
    string_for_key(self.cx,&self.deco,name)
  }
  /// Read optional raw-size/unit/px f32 fields in original order; same field errors.
  fn spacing(&mut self) -> Result<Option<Spacing>,Self::Error> {
    Ok(match opt_object_for_key(self.cx, &self.deco, "thickness"){
        Some(thickness) => Spacing::from_obj(self.cx, &thickness)?,
        _ => None
      })
  }
}
