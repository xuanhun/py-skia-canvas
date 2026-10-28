//! Original text-state API operations; language argument/result allocation removed only.
#![allow(non_snake_case)]
use super::Context2D;
use crate::typography::*;
use skia_safe::textlayout::TextDirection;

/// Original set_textAlign statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:991, skia-canvas3.0.8.
pub fn set_textAlign(this:&mut Context2D, name:String) -> () {
  if let Some(mode) = to_text_align(&name){
    this.state.graf_style.set_text_align(mode);
  }
}

/// Original set_textBaseline statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1009, skia-canvas3.0.8.
pub fn set_textBaseline(this:&mut Context2D, name:String) -> () {
  if let Some(mode) = to_text_baseline(&name){
    this.state.text_baseline = mode;
  }
}

/// Original set_direction statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1030, skia-canvas3.0.8.
pub fn set_direction(this:&mut Context2D, name:String) -> () {
  let direction = match name.to_lowercase().as_str(){
    "ltr" => Some(TextDirection::LTR),
    "rtl" => Some(TextDirection::RTL),
    _ => None
  };

  if let Some(dir) = direction{
    this.state.graf_style.set_text_direction(dir);
  }
}

/// Original set_fontStretch statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:975, skia-canvas3.0.8.
pub fn set_fontStretch(this:&mut Context2D, stretch:String) -> () {
    this.set_font_width(to_width(&stretch));
}

/// Original set_letterSpacing statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1053, skia-canvas3.0.8.
pub fn set_letterSpacing(this:&mut Context2D, spacing:Option<Spacing>) -> () {
  if let Some(spacing) = spacing{
    let em_size = this.state.char_style.font_size();
    this.state.char_style.set_letter_spacing(spacing.in_px(em_size));
    this.state.letter_spacing = spacing;
  }
}

/// Original set_wordSpacing statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1071, skia-canvas3.0.8.
pub fn set_wordSpacing(this:&mut Context2D, spacing:Option<Spacing>) -> () {
  if let Some(spacing) = spacing{
    let em_size = this.state.char_style.font_size();
    this.state.char_style.set_word_spacing(spacing.in_px(em_size));
    this.state.word_spacing = spacing;
  }
}

/// Original set_fontHinting statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1091, skia-canvas3.0.8.
pub fn set_fontHinting(this:&mut Context2D, flag:bool) -> () {
  this.state.font_hinting = flag;
}

/// Original set_textWrap statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1123, skia-canvas3.0.8.
pub fn set_textWrap(this:&mut Context2D, flag:bool) -> () {
  this.state.text_wrap = flag;
}

/// Original set_fontVariant statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1105, skia-canvas3.0.8.
pub fn set_fontVariant(this:&mut Context2D, variant:String, features:Vec<(String,i32)>) -> () {
  this.set_font_variant(&variant, &features);
}

/// Original set_textDecoration statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1137, skia-canvas3.0.8.
pub fn set_textDecoration(this:&mut Context2D, deco_style:DecorationStyle) -> () {
      this.state.text_decoration = deco_style;
}

/// Original get_textAlign statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:984, skia-canvas3.0.8.
pub fn get_textAlign(this:&Context2D) -> String {
  let mode = from_text_align(this.state.graf_style.text_align());
  mode
}

/// Original get_textBaseline statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1002, skia-canvas3.0.8.
pub fn get_textBaseline(this:&Context2D) -> String {
  let mode = from_text_baseline(this.state.text_baseline);
  mode
}

/// Original get_direction statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1020, skia-canvas3.0.8.
pub fn get_direction(this:&Context2D) -> &'static str {
  let name = match this.state.graf_style.text_direction(){
    TextDirection::LTR => "ltr",
    TextDirection::RTL => "rtl",
  };
  name
}

/// Original get_fontStretch statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:969, skia-canvas3.0.8.
pub fn get_fontStretch(this:&Context2D) -> String {
  from_width(this.state.font_width)
}

/// Original get_letterSpacing statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1047, skia-canvas3.0.8.
pub fn get_letterSpacing(this:&Context2D) -> String {
  this.state.letter_spacing.to_string()
}

/// Original get_wordSpacing statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1065, skia-canvas3.0.8.
pub fn get_wordSpacing(this:&Context2D) -> String {
  this.state.word_spacing.to_string()
}

/// Original get_fontVariant statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1099, skia-canvas3.0.8.
pub fn get_fontVariant(this:&Context2D) -> String {
  this.state.font_variant.clone()
}

/// Original get_fontHinting statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1085, skia-canvas3.0.8.
pub fn get_fontHinting(this:&Context2D) -> bool {
  this.state.font_hinting
}

/// Original get_textWrap statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1117, skia-canvas3.0.8.
pub fn get_textWrap(this:&Context2D) -> bool {
  this.state.text_wrap
}

/// Original get_textDecoration statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:1131, skia-canvas3.0.8.
pub fn get_textDecoration(this:&Context2D) -> String {
  this.state.text_decoration.css.clone()
}
