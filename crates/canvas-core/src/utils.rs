//! Original numeric helpers required by the extracted core; no language coercion.
use std::f32::consts::PI;
use skia_safe::{ColorSpace, ColorType, Color, RGB, Matrix, PaintCap, PaintJoin, PathFillType, PathOp};
use css_color::Rgba;

/// Convert degrees (f32) to radians (f32), preserving the original operation order.
///
/// No validation or errors; non-finite inputs propagate through IEEE arithmetic.
/// Takes/returns plain values, with no ownership or thread-affinity constraints.
/// Upstream: `src/utils.rs:45-47`, skia-canvas 3.0.8; used by hue-rotate filters.
pub fn to_radians(degrees: f32) -> f32{
  degrees / 180.0 * PI
}

/// Convert f32 radians to f32 degrees using the original arithmetic order; non-finite math propagates. No ownership/thread constraints or errors.
/// Upstream: src/utils.rs:41, skia-canvas 3.0.8; body unchanged.
pub fn to_degrees(radians: f32) -> f32{
  radians / PI * 180.0
}

/// Return original sRGB ColorSpace for the string input, including unknown-name fallback; owns a Skia reference, no new validation or errors.
/// Upstream: src/utils.rs:581, skia-canvas 3.0.8; body unchanged.
pub fn to_color_space(mode_name:&str) -> ColorSpace{
  match mode_name{
    // TODO: add display-p3 support
    "srgb" | _ => ColorSpace::new_srgb()
  }
}

/// Return original ColorType enum for all names/aliases; unknown names still map to RGBA8888. Unitless value, no allocation/errors/thread constraints.
/// Upstream: src/utils.rs:594, skia-canvas 3.0.8; body unchanged.
pub fn to_color_type(type_name: &str) -> ColorType {
  match type_name {
    "Alpha8" => ColorType::Alpha8,
    "RGB565" => ColorType::RGB565,
    "ARGB4444" => ColorType::ARGB4444,
    "RGBA1010102" => ColorType::RGBA1010102,
    "BGRA1010102" => ColorType::BGRA1010102,
    "RGB101010x" => ColorType::RGB101010x,
    "BGR101010x" => ColorType::BGR101010x,
    "Gray8" => ColorType::Gray8,
    "RGBAF16Norm" => ColorType::RGBAF16Norm,
    "RGBAF16" => ColorType::RGBAF16,
    "RGBAF32" => ColorType::RGBAF32,
    "R8G8UNorm" => ColorType::R8G8UNorm,
    "A16Float" => ColorType::A16Float,
    "R16G16Float" => ColorType::R16G16Float,
    "A16UNorm" => ColorType::A16UNorm,
    "R16G16UNorm" => ColorType::R16G16UNorm,
    "R16G16B16A16UNorm" => ColorType::R16G16B16A16UNorm,
    "SRGBA8888" => ColorType::SRGBA8888,
    "R8UNorm" => ColorType::R8UNorm,
    "N32" => ColorType::N32,
    "RGB888x"|"rgb" => ColorType::RGB888x,
    "BGRA8888"|"bgra" => ColorType::BGRA8888,
    "RGBA8888"|"rgba"|_ => ColorType::RGBA8888,
  }
}

/// Original f32 near-zero/equality predicate used by drawing geometry; values are canvas units.
/// Returns boolean, no allocation/errors or thread ownership. Upstream: src/utils.rs, v3.0.8; body unchanged.
pub fn almost_equal(a: f32, b: f32) -> bool{
  (a-b).abs() < 0.00001
}

/// Original f32 near-zero/equality predicate used by drawing geometry; values are canvas units.
/// Returns boolean, no allocation/errors or thread ownership. Upstream: src/utils.rs, v3.0.8; body unchanged.
pub fn almost_zero(a: f32) -> bool{
  a.abs() < 0.00001
}

/// Parse CSS with the original css-color parser and alpha/channel rounding; invalid strings return None.
/// Inputs have no units; returns an owned Skia color value, no GPU affinity. Upstream: src/utils.rs:382.
pub fn css_to_color(css:&str) -> Option<Color> {
  css.parse::<Rgba>().ok().map(|Rgba{red, green, blue, alpha}|
    Color::from_argb(
      (alpha*255.0).round() as u8,
      (red*255.0).round() as u8,
      (green*255.0).round() as u8,
      (blue*255.0).round() as u8,
    )
  )
}

/// Format the original color getter string; RGB hex or original rounded alpha CSS.
/// No units/errors or GPU ownership; extracts only JS string allocation. Upstream: src/utils.rs:423.
pub fn color_to_css_string(color:&Color) -> String {
  let RGB {r, g, b} = color.to_rgb();
  let css = match color.a() {
    255 => format!("#{:02x}{:02x}{:02x}", r, g, b),
    _ => {
      let alpha = format!("{:.3}", color.a() as f32 / 255.0);
      let alpha = alpha.trim_end_matches('0');
      format!("rgba({}, {}, {}, {})", r, g, b, if alpha=="0."{ "0" } else{ alpha })
    }
  };
  css
}

/// Original to_matrix typed conversion; matrix coordinates in canvas units, style names unitless.
/// Returns original enum/matrix/string/None without new errors; no GPU ownership transfer. Upstream: src/utils.rs:450.
pub fn to_matrix(t:&[f32]) -> Option<Matrix>{
  match t.len(){
    6 => Some(Matrix::new_all(t[0], t[1], t[2], t[3], t[4], t[5], 0.0, 0.0, 1.0)),
    9 => Some(Matrix::new_all(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8])),
    _ => None
  }
}

/// Original to_stroke_cap typed conversion; matrix coordinates in canvas units, style names unitless.
/// Returns original enum/matrix/string/None without new errors; no GPU ownership transfer. Upstream: src/utils.rs:795.
pub fn to_stroke_cap(mode_name:&str) -> Option<PaintCap>{
  let mode = match mode_name.to_lowercase().as_str(){
    "butt" => PaintCap::Butt,
    "round" => PaintCap::Round,
    "square" => PaintCap::Square,
        _ => return None
  };
  Some(mode)
}

/// Original from_stroke_cap typed conversion; matrix coordinates in canvas units, style names unitless.
/// Returns original enum/matrix/string/None without new errors; no GPU ownership transfer. Upstream: src/utils.rs:805.
pub fn from_stroke_cap(mode:PaintCap) -> String{
  match mode{
    PaintCap::Butt => "butt",
    PaintCap::Round => "round",
    PaintCap::Square => "square",
  }.to_string()
}

/// Original to_stroke_join typed conversion; matrix coordinates in canvas units, style names unitless.
/// Returns original enum/matrix/string/None without new errors; no GPU ownership transfer. Upstream: src/utils.rs:814.
pub fn to_stroke_join(mode_name:&str) -> Option<PaintJoin>{
  let mode = match mode_name.to_lowercase().as_str(){
    "miter" => PaintJoin::Miter,
    "round" => PaintJoin::Round,
    "bevel" => PaintJoin::Bevel,
    _ => return None
  };
  Some(mode)
}

/// Original from_stroke_join typed conversion; matrix coordinates in canvas units, style names unitless.
/// Returns original enum/matrix/string/None without new errors; no GPU ownership transfer. Upstream: src/utils.rs:824.
pub fn from_stroke_join(mode:PaintJoin) -> String{
  match mode{
    PaintJoin::Miter => "miter",
    PaintJoin::Round => "round",
    PaintJoin::Bevel => "bevel",
  }.to_string()
}

/// Original fill-rule selection after language string/default extraction; no units.
/// Returns original rule or owned original error message; no GPU ownership or thread transfer.
/// Upstream: src/utils.rs:fill_rule_arg_or final match; only Neon exception creation is separated.
pub fn fill_rule(mode:&String, err_msg:&String) -> Result<PathFillType, String> {
  match mode.as_str(){
    "nonzero" => Ok(PathFillType::Winding),
    "evenodd" => Ok(PathFillType::EvenOdd),
    _ => Err(err_msg.clone())
  }
}

/// Original path-op name/alias conversion; unitless, returns enum/None, no native ownership or new errors.
/// Upstream: src/utils.rs:to_path_op; body unchanged.
pub fn to_path_op(op_name:&str) -> Option<PathOp> {
  let op = match op_name.to_lowercase().as_str() {
    "difference" => PathOp::Difference,
    "intersect" => PathOp::Intersect,
    "union" => PathOp::Union,
    "xor" => PathOp::XOR,
    "reversedifference" | "complement" => PathOp::ReverseDifference,
    _ => return None
  };
  Some(op)
}

/// Original _as_double string branch, unitless f64 parsing with original prefix/u64 rules.
/// Empty string ->0; errors ->None. NaN/Infinity may be parsed and are filtered by caller
/// before original f32 cast. Stateless/any thread, no Python/Node/Skia ownership.
/// Upstream: src/utils.rs:234; original statements retained verbatim.
pub fn parse_number_string(s:&str) -> Option<f64> {
      if let Some(s) = s.strip_prefix("0x"){
        u64::from_str_radix(s, 16).map(|i| i as f64).ok()
      }else if let Some(s) = s.strip_prefix("0o"){
        u64::from_str_radix(s, 8).map(|i| i as f64).ok()
      }else if let Some(s) = s.strip_prefix("0b"){
        u64::from_str_radix(s, 2).map(|i| i as f64).ok()
      }else if s.is_empty(){
        Some(0.0)
      }else{
        s.parse::<f64>().ok()
      }
}

use crate::filter::FilterQuality;
use skia_safe::{TileMode,TileMode::{Decal,Repeat}};

/// Original enum conversion, unitless string/enum, returns original value/None.
/// No callbacks or resource ownership; any thread, no errors. Source src/utils.rs:to_filter_quality.
pub fn to_filter_quality(mode_name:&str) -> Option<FilterQuality>{
  let mode = match mode_name.to_lowercase().as_str(){
    "low" => FilterQuality::Low,
    "medium" => FilterQuality::Medium,
    "high" => FilterQuality::High,
    _ => return None
  };
  Some(mode)
}


/// Original enum conversion, unitless string/enum, returns original value/None.
/// No callbacks or resource ownership; any thread, no errors. Source src/utils.rs:from_filter_quality.
pub fn from_filter_quality(mode:FilterQuality) -> String{
  match mode{
    FilterQuality::Low => "low",
    FilterQuality::Medium => "medium",
    FilterQuality::High => "high",
    _ => "low"
  }.to_string()
}


/// Original enum conversion, unitless string/enum, returns original value/None.
/// No callbacks or resource ownership; any thread, no errors. Source src/utils.rs:to_repeat_mode.
pub fn to_repeat_mode(repeat:&str) -> Option<(TileMode, TileMode)> {
  let mode = match repeat.to_lowercase().as_str() {
    "repeat" | "" => (Repeat, Repeat),
    "repeat-x" => (Repeat, Decal),
    "repeat-y" => (Decal, Repeat),
    "no-repeat" => (Decal, Decal),
    _ => return None
  };
  Some(mode)
}


use skia_safe::{BlendMode,path_1d_path_effect};

/// Original enum conversion, unitless ->original enum/string/None, no new errors.
/// Owned plain values only, any thread. Source utils.rs:to_blend_mode v3.0.8.
pub fn to_blend_mode(mode_name:&str) -> Option<BlendMode>{
  let mode = match mode_name.to_lowercase().as_str(){
    "source-over" => BlendMode::SrcOver,
    "destination-over" => BlendMode::DstOver,
    "copy" => BlendMode::Src,
    "destination" => BlendMode::Dst,
    "clear" => BlendMode::Clear,
    "source-in" => BlendMode::SrcIn,
    "destination-in" => BlendMode::DstIn,
    "source-out" => BlendMode::SrcOut,
    "destination-out" => BlendMode::DstOut,
    "source-atop" => BlendMode::SrcATop,
    "destination-atop" => BlendMode::DstATop,
    "xor" => BlendMode::Xor,
    "lighter" => BlendMode::Plus,
    "multiply" => BlendMode::Multiply,
    "screen" => BlendMode::Screen,
    "overlay" => BlendMode::Overlay,
    "darken" => BlendMode::Darken,
    "lighten" => BlendMode::Lighten,
    "color-dodge" => BlendMode::ColorDodge,
    "color-burn" => BlendMode::ColorBurn,
    "hard-light" => BlendMode::HardLight,
    "soft-light" => BlendMode::SoftLight,
    "difference" => BlendMode::Difference,
    "exclusion" => BlendMode::Exclusion,
    "hue" => BlendMode::Hue,
    "saturation" => BlendMode::Saturation,
    "color" => BlendMode::Color,
    "luminosity" => BlendMode::Luminosity,
    _ => return None
  };
  Some(mode)
}


/// Original enum conversion, unitless ->original enum/string/None, no new errors.
/// Owned plain values only, any thread. Source utils.rs:from_blend_mode v3.0.8.
pub fn from_blend_mode(mode:BlendMode) -> String{
  match mode{
    BlendMode::SrcOver => "source-over",
    BlendMode::DstOver => "destination-over",
    BlendMode::Src => "copy",
    BlendMode::Dst => "destination",
    BlendMode::Clear => "clear",
    BlendMode::SrcIn => "source-in",
    BlendMode::DstIn => "destination-in",
    BlendMode::SrcOut => "source-out",
    BlendMode::DstOut => "destination-out",
    BlendMode::SrcATop => "source-atop",
    BlendMode::DstATop => "destination-atop",
    BlendMode::Xor => "xor",
    BlendMode::Plus => "lighter",
    BlendMode::Multiply => "multiply",
    BlendMode::Screen => "screen",
    BlendMode::Overlay => "overlay",
    BlendMode::Darken => "darken",
    BlendMode::Lighten => "lighten",
    BlendMode::ColorDodge => "color-dodge",
    BlendMode::ColorBurn => "color-burn",
    BlendMode::HardLight => "hard-light",
    BlendMode::SoftLight => "soft-light",
    BlendMode::Difference => "difference",
    BlendMode::Exclusion => "exclusion",
    BlendMode::Hue => "hue",
    BlendMode::Saturation => "saturation",
    BlendMode::Color => "color",
    BlendMode::Luminosity => "luminosity",
    _ => "source-over"
  }.to_string()
}


/// Original enum conversion, unitless ->original enum/string/None, no new errors.
/// Owned plain values only, any thread. Source utils.rs:to_1d_style v3.0.8.
pub fn to_1d_style(mode_name:&str) -> Option<path_1d_path_effect::Style>{
  let mode = match mode_name.to_lowercase().as_str(){
    "move" => path_1d_path_effect::Style::Translate,
    "turn" => path_1d_path_effect::Style::Rotate,
    "follow" => path_1d_path_effect::Style::Morph,
    _ => return None
  };
  Some(mode)
}


/// Original enum conversion, unitless ->original enum/string/None, no new errors.
/// Owned plain values only, any thread. Source utils.rs:from_1d_style v3.0.8.
pub fn from_1d_style(mode:path_1d_path_effect::Style) -> String{
  match mode{
    path_1d_path_effect::Style::Translate => "move",
    path_1d_path_effect::Style::Rotate => "turn",
    path_1d_path_effect::Style::Morph => "follow"
  }.to_string()
}

