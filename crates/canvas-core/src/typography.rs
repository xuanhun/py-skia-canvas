#![allow(dead_code)]
#![allow(non_snake_case)]
use std::ops::Range;
use std::iter::zip;
use serde_json::{json, Value};
use skia_safe::{FontMetrics, Typeface, Paint, Point, Rect, Path as SkPath, Color};
use skia_safe::font_style::{FontStyle, Weight, Width, Slant};
use skia_safe::textlayout::{
  Decoration, FontCollection, Paragraph, ParagraphBuilder, ParagraphStyle, RectHeightStyle, RectWidthStyle,
  TextAlign, TextDirection, TextStyle,
};
use crate::font_library::FontLibrary;
use crate::context::State;
pub mod decoration;
pub mod audit;

//
// Text layout and metrics
//

const GALLEY:f32 = 100_000.0;

pub struct Typesetter{
  text: String,
  width: f32,
  baseline: Baseline,
  typefaces: FontCollection,
  char_style: TextStyle,
  graf_style: ParagraphStyle,
  text_decoration: DecorationStyle,
  text_wrap: bool,
}

impl Typesetter{
  /// Construct original Canvas/Context/typesetter/style key from typed inputs; preserve default dimensions, style/font selection and operation order. Dimensions/coordinates are canvas units unless documented as pixels.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:35, skia-canvas 3.0.8; original rendering body retained.
  pub fn new(state:&State, text: &str, width:Option<f32>) -> Self {
    let (char_style, graf_style, text_decoration, baseline, text_wrap) = state.typography();
    let typefaces = FontLibrary::with_shared(|lib|
      lib
        .set_hinting(graf_style.hinting_is_on())
        .fonts_for_style(&char_style)
    );
    let width = width.unwrap_or(GALLEY);
    let text = match text_wrap{
      true => text.to_string(),
      false => text.replace("\n", " ")
    };

    Typesetter{text, width, baseline, typefaces, char_style, graf_style, text_decoration, text_wrap}
  }

  /// Build/layout original SkParagraph from current text/style/paint and return paragraph/origin; width and origin in canvas units, original baseline/decoration/shaping retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:51, skia-canvas 3.0.8; original rendering body retained.
  pub fn layout(&self, paint:&Paint) -> (Paragraph, Point) {
    let mut char_style = self.char_style.clone();
    char_style.set_foreground_paint(paint);
    char_style.set_decoration(
      &self.text_decoration.for_layout(&char_style, paint.color())
    );

    // prevent SkParagraph from faking the font style if the match isn't the requested weight/slant
    let fams:Vec<String> = char_style.font_families().iter().map(|s| s.to_string()).collect();
    if let Some(matched) = self.typefaces.clone().find_typefaces(&fams, char_style.font_style()).first(){
      char_style.set_font_style(matched.font_style());
    }

    let mut paragraph_builder = ParagraphBuilder::new(&self.graf_style, &self.typefaces);
    paragraph_builder.push_style(&char_style);
    paragraph_builder.add_text(&self.text);

    let mut paragraph = paragraph_builder.build();
    paragraph.layout(self.width);

    let offset = Point::new(
      self.alignment_offset(),
      -paragraph.alphabetic_baseline(),
    );

    audit::record_layout(&mut paragraph, self, offset);
    (paragraph, offset)
  }

  /// Return original full JSON text metrics with original paragraph visits, line/run bounds, baselines and UTF-16 ranges; no tolerance/rounding added.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:79, skia-canvas 3.0.8; original rendering body retained.
  pub fn metrics(&self) -> Value {
    let (mut paragraph, origin) = self.layout(&Paint::default());
    let mut line_rects:Vec<Rect> = vec![]; // accumulate line rects to calculate full bounds

    // calculate baseline offsets (relative to line_metrics.baseline which reflects ctx.textBaseline setting)
    let shift = self.char_style.baseline_shift();
    let hang = Baseline::Hanging.get_offset(&self.char_style) - shift;
    let norm = Baseline::Alphabetic.get_offset(&self.char_style) - shift;
    let ideo = Baseline::Ideographic.get_offset(&self.char_style) - shift;

    // calculate bounds for each single-font block of glyphs on each line (and gather font info)
    struct TextRun{ line: usize, family: String, metrics: FontMetrics, bounds: Rect }
    let mut text_runs:Vec<TextRun> = vec![];
    paragraph.extended_visit(|line, visit|{
      if let Some(info) = visit{
        text_runs.push(TextRun{
          line,
          family: info.font().typeface().family_name(),
          metrics: info.font().metrics().1,
          bounds: zip(info.positions(), info.bounds())
            .filter(|(_, rect)| !rect.is_empty())
            .map(|(pt, rect)| rect.with_offset(*pt + info.origin() + origin - Point::new(0.0, norm)))
            .reduce(Rect::join2)
            .unwrap_or(Rect::new_empty())
        });
      }
    });

    // measure each line and add its layout rect to `line_rects`
    let lines = (0..paragraph.line_number()).filter_map(|ln|{
      // find the range of byte & char indices that are on this line (includes trailing whitespace if not wrapping)
      let text_range = paragraph.get_actual_text_range(ln, !self.text_wrap);
      let char_range = utf16_range(&self.text, &text_range);

      // calculate this line's vertical offsets relative to the typesetting origin
      let line_metrics = paragraph.get_line_metrics_at(ln)?;
      let half_leading = self.graf_style.strut_style().leading().max(0.0) * self.char_style.font_size() / 2.0;
      let baseline = line_metrics.baseline as f32 + origin.y - half_leading;
      let line_ascent = baseline - line_metrics.ascent as f32;
      let line_descent = baseline + line_metrics.descent as f32;

      // combine the glyph bounds of all single-font runs on this line (potentially omitting trailing spaces)
      let font_runs = text_runs.iter().filter(|r| r.line==ln).collect::<Vec<&TextRun>>();
      let text_bounds = font_runs.iter()
        .map(|run| run.bounds)
        .reduce(Rect::join2)
        .unwrap_or(Rect::new_empty());

      // calculate horizontal line bounds that include trailing whitespace for use in `actualBoundingBox`
      // (and compensate for the extra half-letterspace added to the start & end of each line)
      line_rects.push(
        paragraph
          .get_rects_for_range(char_range.clone(), RectHeightStyle::Tight, RectWidthStyle::Tight).iter()
          .map(|tb| {
            let Rect{top, bottom, ..} = text_bounds;
            let Rect{left, right, ..} = tb.rect.with_offset(origin);
            Rect::new(left, top, right - self.char_style.letter_spacing(), bottom)
          })
          .reduce(Rect::join2)
          .unwrap_or(text_bounds)
      );

      Some(json!({
        "x": text_bounds.left,
        "y": text_bounds.top,
        "width": text_bounds.width(),
        "height": text_bounds.height(),
        "baseline": baseline, // corresponds to the ctx.textBaseline selection
        "hangingBaseline": baseline - hang,
        "alphabeticBaseline": baseline - norm,
        "ideographicBaseline": baseline - ideo,
        "ascent": line_ascent,
        "descent": line_descent,
        "startIndex": char_range.start,
        "endIndex": char_range.end,
        "runs": font_runs.iter().map(|TextRun{family, metrics, bounds, ..}| {
          json!({
            "x": bounds.left,
            "y": bounds.top,
            "width": bounds.width(),
            "height": bounds.height(),
            "family": family,
            "ascent": baseline - norm + metrics.ascent,
            "descent": baseline - norm + metrics.descent,
            "capHeight": baseline - norm - metrics.cap_height,
            "xHeight": baseline - norm - metrics.x_height,
            "underline": metrics.underline_position().map(|ulH| baseline - norm + ulH ),
            "strikethrough": metrics.strikeout_position().map(|stH| baseline - norm + stH ),
          })
        }).collect::<Vec<Value>>()
      }))
    }).collect::<Vec<Value>>();

    // combine all the individual line measurements to find the `actualBoundingBox`
    let full_bounds = line_rects.into_iter()
      .reduce(Rect::join2)
      .unwrap_or(Rect::new_empty());

    // use line metrics to find maximal ascent/descent of all fonts on first line
    let (ascent, descent) = paragraph.get_line_metrics_at(0).map(|line|
      (norm + line.ascent as f32, line.descent as f32 - norm)
    ).unwrap_or_else(||{
      // or fall back to the first-matched font's metrics if measuring empty string
      let FontMetrics{ascent, descent, ..} = self.char_style.font_metrics();
      (norm - ascent, descent - norm)
    });

    json!({
      "width": full_bounds.right - full_bounds.left,
      "actualBoundingBoxLeft": -full_bounds.left,
      "actualBoundingBoxRight": full_bounds.right,
      "actualBoundingBoxAscent": -full_bounds.top,
      "actualBoundingBoxDescent": full_bounds.bottom,
      "fontBoundingBoxAscent": ascent,
      "fontBoundingBoxDescent": descent,
      "emHeightAscent": ascent,
      "emHeightDescent": descent,
      "hangingBaseline": hang,
      "alphabeticBaseline": norm,
      "ideographicBaseline": ideo,
      "lines": lines,
    })
  }

  /// Return original paragraph outline path offset to supplied canvas-unit point; preserve per-line original SkParagraph path extraction.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:203, skia-canvas 3.0.8; original rendering body retained.
  pub fn path(&mut self, point:impl Into<Point>) -> SkPath {
    let (mut paragraph, mut origin) = self.layout(&Paint::default());
    let headroom = self.char_style.font_metrics().ascent + paragraph.alphabetic_baseline();
    let offset = self.baseline.get_offset(&self.char_style);
    origin += point.into();
    origin.y -= headroom - offset;

    let mut path = SkPath::new();
    for idx in 0..paragraph.line_number(){
      let (_skipped, line) = paragraph.get_path_at(idx);
      path.add_path(&line, origin, None);
    };
    path
  }

  /// Return original canvas-unit horizontal alignment/letterspacing offset with original LTR/RTL start/end mapping.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:218, skia-canvas 3.0.8; original rendering body retained.
  fn alignment_offset(&self) -> f32{
    // convert start/end to left/right depending on writing system
    let gravity = match (self.graf_style.text_direction(), self.graf_style.text_align()){
      (TextDirection::LTR, TextAlign::Start) | (TextDirection::RTL, TextAlign::End) => TextAlign::Left,
      (TextDirection::LTR, TextAlign::End) | (TextDirection::RTL, TextAlign::Start) => TextAlign::Right,
      (_, alignment) => alignment,
    };

    // `alignment_factor` shifts the entire line to left/right/center align it
    // `spacing_step` compensates for the letterspacing Paragraph adds before the line's first character
    let (alignment_factor, spacing_step) = match gravity{
      TextAlign::Left | TextAlign::Justify => (0.0, -0.5),
      TextAlign::Center => (-0.5, 0.5),
      TextAlign::Right => (-1.0, 1.0),
      _ => (0.0, 0.0) // start & end have already been remapped
    };

    alignment_factor * self.width + spacing_step * self.char_style.letter_spacing()
  }
}

//
// Convert utf-8 byte indices -> utf-16 codepoint indices
//
/// Convert original borrowed UTF-8 byte range to UTF-16 code-unit range, preserving original iteration and fallback arithmetic; returns owned Range<usize>.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:242, skia-canvas 3.0.8; original rendering body retained.
fn utf16_range(text:&str, byte_range:&Range<usize>) -> Range<usize>{
  let chars:Vec<(usize, usize)> = text.char_indices()
    .map(|(idx, c)| (idx, c.len_utf16()))
    .collect::<Vec<(usize, usize)>>();

  // find the char indices corresponding to the byte range endpoints
  let start = chars.iter().position(|(i, _)| *i >= byte_range.start).unwrap_or(0);
  let end = chars.iter().rposition(|(i, _)| *i < byte_range.end).map(|i| i + 1).unwrap_or(start);

  // sum up the number of utf-16 code units needed for all chars in the range
  let sum = |a,b|{a+b};
  let len = |&(_, len)|{len};
  let head = chars.iter().take(start).map(len).reduce(sum).unwrap_or(0);
  let tail = chars.iter().skip(start).take(end-start).map(len).reduce(sum).unwrap_or(head);
  head..head+tail
}

//
// Font argument packing & unpacking
//
#[derive(Debug, Clone)]
pub struct FontSpec{
  pub families: Vec<String>,
  pub size: f32,
  pub line_height: Option<f32>,
  pub weight: Weight,
  pub width: Width,
  pub slant: Slant,
  pub features: Vec<(String, i32)>,
  pub variant: String,
  pub canonical: String
}

impl FontSpec{
  /// Clone original FontSpec replacing typed Width only; returns owned spec with original remaining fields and no validation/errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:276, skia-canvas 3.0.8; original rendering body retained.
  pub fn with_width(&self, width:Width) -> Self{
    Self{width, ..self.clone()}
  }

  /// Construct original FontStyle from typed weight/width/slant; unitless enum conversion, no font selection or errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:280, skia-canvas 3.0.8; original rendering body retained.
  pub fn style(&self) -> FontStyle{
    FontStyle::new(self.weight, self.width, self.slant)
  }
}




/// Return original integer variable weight steps/min/max from Typeface metadata, preserving tag conversion and step arithmetic/panics.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:344, skia-canvas 3.0.8; original rendering body retained.
pub fn typeface_wght_range(font:&Typeface) -> Vec<i32>{
  let mut wghts = vec![];
  if let Some(params) = font.variation_design_parameters(){
    for param in params {
      let chars = vec![param.tag.a(), param.tag.b(), param.tag.c(), param.tag.d()];
      let tag = String::from_utf8(chars).unwrap();
      let (min, max) = (param.min as i32, param.max as i32);
      if tag == "wght"{
        let mut val = min;
        while val <= max {
          wghts.push(val);
          val = val + 100 - (val % 100);
        }
        if !wghts.contains(&max){
          wghts.push(max);
        }
      }
    }
  }
  wghts
}

/// Map original case-insensitive style name to Slant with original Upright fallback; no shaping or allocation-policy changes.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:366, skia-canvas 3.0.8; original rendering body retained.
pub fn to_slant(slant_name:&str) -> Slant{
  match slant_name.to_lowercase().as_str(){
    "italic" => Slant::Italic,
    "oblique" => Slant::Oblique,
    _ => Slant::Upright
  }
}

/// Return original style name for typed Slant as owned string; no errors/ownership transfer of fonts.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:374, skia-canvas 3.0.8; original rendering body retained.
pub fn from_slant(slant:Slant) -> String{
  match slant {
    Slant::Upright => "normal",
    Slant::Italic => "italic",
    Slant::Oblique => "oblique",
  }.to_string()
}

/// Map original case-insensitive stretch name to Width with original NORMAL fallback; typed unitless value, no new validation.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:382, skia-canvas 3.0.8; original rendering body retained.
pub fn to_width(width_name:&str) -> Width{
  match width_name.to_lowercase().as_str(){
    "ultra-condensed" => Width::ULTRA_CONDENSED,
    "extra-condensed" => Width::EXTRA_CONDENSED,
    "condensed" => Width::CONDENSED,
    "semi-condensed" => Width::SEMI_CONDENSED,
    "semi-expanded" => Width::SEMI_EXPANDED,
    "expanded" => Width::EXPANDED,
    "extra-expanded" => Width::EXTRA_EXPANDED,
    "ultra-expanded" => Width::ULTRA_EXPANDED,
    _ => Width::NORMAL,
  }
}

/// Return original stretch string for typed Width, preserving unknown-width fallback; no font selection or errors.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:396, skia-canvas 3.0.8; original rendering body retained.
pub fn from_width(width:Width) -> String{
  match width {
    w if w == Width::ULTRA_CONDENSED => "ultra-condensed",
    w if w == Width::EXTRA_CONDENSED => "extra-condensed",
    w if w == Width::CONDENSED => "condensed",
    w if w == Width::SEMI_CONDENSED => "semi-condensed",
    w if w == Width::SEMI_EXPANDED => "semi-expanded",
    w if w == Width::EXPANDED => "expanded",
    w if w == Width::EXTRA_EXPANDED => "extra-expanded",
    w if w == Width::ULTRA_EXPANDED => "ultra-expanded",
    _ => "normal"
  }.to_string()
}

/// Map original alignment string to optional TextAlign; invalid names remain None, no new defaults.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:410, skia-canvas 3.0.8; original rendering body retained.
pub fn to_text_align(mode_name:&str) -> Option<TextAlign>{
  let mode = match mode_name.to_lowercase().as_str(){
    "left" => TextAlign::Left,
    "right" => TextAlign::Right,
    "center" => TextAlign::Center,
    "justify" => TextAlign::Justify,
    "start" => TextAlign::Start,
    "end" => TextAlign::End,
    _ => return None
  };
  Some(mode)
}

/// Return original alignment string for typed TextAlign; owned string, no rendering or font ownership change.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:423, skia-canvas 3.0.8; original rendering body retained.
pub fn from_text_align(mode:TextAlign) -> String{
  match mode{
    TextAlign::Left => "left",
    TextAlign::Right => "right",
    TextAlign::Center => "center",
    TextAlign::Justify => "justify",
    TextAlign::Start => "start",
    TextAlign::End => "end",
  }.to_string()
}

#[derive(Copy, Clone, Debug)]
pub enum Baseline{ Top, Hanging, Middle, Alphabetic, Ideographic, Bottom }

/// Map original baseline string to optional Baseline; invalid names remain None, no new defaults.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:437, skia-canvas 3.0.8; original rendering body retained.
pub fn to_text_baseline(mode_name:&str) -> Option<Baseline>{
  let mode = match mode_name.to_lowercase().as_str(){
    "top" => Baseline::Top,
    "hanging" => Baseline::Hanging,
    "middle" => Baseline::Middle,
    "alphabetic" => Baseline::Alphabetic,
    "ideographic" => Baseline::Ideographic,
    "bottom" => Baseline::Bottom,
    _ => return None
  };
  Some(mode)
}

/// Return original baseline label as owned string; no new metric conversion or errors.
/// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
/// Upstream: src/typography.rs:450, skia-canvas 3.0.8; original rendering body retained.
pub fn from_text_baseline(mode:Baseline) -> String{
  match mode{
    Baseline::Top => "top",
    Baseline::Hanging => "hanging",
    Baseline::Middle => "middle",
    Baseline::Alphabetic => "alphabetic",
    Baseline::Ideographic => "ideographic",
    Baseline::Bottom => "bottom",
  }.to_string()
}

impl Baseline{
  /// Compute original baseline offset from font metrics/baseline shift in canvas units; original 0.8 hanging rule retained, no metric rewrite.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:462, skia-canvas 3.0.8; original rendering body retained.
  pub fn get_offset(&self, style:&TextStyle) -> f32 {
    let FontMetrics{mut ascent, mut descent, ..} = style.font_metrics();
    ascent -= style.baseline_shift();  // offsets are defined relative to the alphabetic baseline, so
    descent -= style.baseline_shift(); // compensate for any other textBaseline setting

    // see TextMetrics::GetFontBaseline from Chromium for reference:
    // https://github.com/chromium/chromium/blob/main/third_party/blink/renderer/core/html/canvas/text_metrics.cc#L34
    match self {
      Baseline::Top => -ascent,
      Baseline::Hanging => -ascent * 0.8,
      Baseline::Middle => -(ascent + descent) / 2.0,
      Baseline::Alphabetic => 0.0,
      Baseline::Bottom | Baseline::Ideographic => -descent,
    }
  }
}

#[derive(Clone, Debug)]
pub struct DecorationStyle{
  pub css: String,
  pub decoration: Decoration,
  pub size: Option<Spacing>,
  pub color: Option<Color>,
}


impl Default for DecorationStyle{
  /// Construct original default State/spacing/decoration with the same font, paint, baseline and cache-related fields; returns owned value, no new validation/errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:489, skia-canvas 3.0.8; original rendering body retained.
  fn default() -> Self {
    Self{decoration:Decoration::default(), size:None, color:None, css:"none".to_string()}
  }
}

impl DecorationStyle{
  /// Return original Decoration using text color and thickness relative to font metrics/em size; no new unit conversion or invalid-value policy.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:495, skia-canvas 3.0.8; original rendering body retained.
  pub fn for_layout(&self, style:&TextStyle, text_color:Color) -> Decoration{
    // convert `size` into a multiple of the current font's default thickness
    let em_size = style.font_size();
    let thickness = style.font_metrics()
      .underline_thickness()
      .unwrap_or(1.0);
    let thickness_multiplier = self.size.clone()
      .map(|size| size.in_px(em_size) / thickness)
      .unwrap_or(1.0);
    let color = self.color.unwrap_or(text_color);
    Decoration{thickness_multiplier, color, ..self.decoration}
  }
}


//
// Em-relative lengths (for text spacing & decoration thickness)
//
#[derive(Clone, Debug)]
pub struct Spacing{
  raw_size: f32,
  unit: String,
  px_size: f32,
}

impl Default for Spacing{
  /// Construct original default State/spacing/decoration with the same font, paint, baseline and cache-related fields; returns owned value, no new validation/errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:569, skia-canvas 3.0.8; original rendering body retained.
  fn default() -> Self {
    Self{raw_size:0.0, unit:"px".to_string(), px_size:0.0}
  }
}

impl Spacing{

  /// Return original optional spacing from raw size/unit/px value, preserving NaN rejection and em/rem branch; no CSS parser replacement.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:582, skia-canvas 3.0.8; original rendering body retained.
  pub fn parse(raw_size:f32, unit:String, px_size:f32) -> Option<Self>{
    let main_size = match unit.as_str(){
      "em" | "rem" => raw_size,
      _ => px_size
    };

    match main_size.is_nan(){
      false => Some(Self{raw_size, unit, px_size}),
      true => None
    }
  }

  /// Return original spacing in canvas units using em/rem times em size or stored px; original f32 operation order retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:594, skia-canvas 3.0.8; original rendering body retained.
  pub fn in_px(&self, em_size:f32) -> f32{
    match self.unit.as_str(){
      "em" | "rem" => self.raw_size * em_size,
      _ => self.px_size
    }
  }

  /// Return original raw-size/unit spacing string; original formatting retained, no rounding or normalization added.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/typography.rs:601, skia-canvas 3.0.8; original rendering body retained.
  pub fn to_string(&self) -> String{
    format!("{}{}", self.raw_size, self.unit)
  }
}


/// Pack original parsed font fields; size/line_height are f32 canvas units, weight
/// original numeric weight, remaining values unitless. Returns None for empty first
/// family, otherwise owned FontSpec. Adapters supply original parser fields/nonempty
/// family array; no callbacks/errors or Skia handles, usable before owner borrow.
/// Upstream: src/typography.rs:285 font_arg, only Neon field reads separated.
pub fn font_spec(families:Vec<String>, canonical:String, variant:String, size:f32,
                 weight:f32, style:&str, stretch:&str, line_height:Option<f32>,
                 features:Vec<(String,i32)>) -> Option<FontSpec> {

  let weight = Weight::from(weight as i32);
  let slant = to_slant(style);
  let width = to_width(stretch);
  let line_height = line_height
    .map(|pt_size| pt_size / size);


  match families[0] == ""{
    true => None, // silently fail if a family name was omitted (e.g., "bold 50px")
    false => Some(FontSpec{ families, size, line_height, weight, slant, width, features, variant, canonical})
  }
}
