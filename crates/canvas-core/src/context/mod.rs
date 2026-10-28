#![allow(dead_code)]
use std::cell::RefCell;
use skia_safe::{
  Canvas as SkCanvas, Paint, Path, PathOp, Image, Contains,
  Rect, IRect, Point, Size, Color, Color4f, ColorSpace, PathFillType,
  PaintStyle, BlendMode, ClipOp, PictureRecorder, Picture,
  images, image_filters, dash_path_effect, path_1d_path_effect,
  matrix::{ Matrix, TypeMask },
  textlayout::{ParagraphStyle, TextStyle, StrutStyle},
  canvas::SrcRectConstraint::Strict,
  path_utils::fill_path_with_paint,
  font_style::{FontStyle, Width},
};

pub mod page;
pub mod operations;
pub mod text_state;
pub mod effects;

use crate::utils::*;
use crate::font_library::FontLibrary;
use crate::typography::{Typesetter, FontSpec, Baseline, Spacing, DecorationStyle};
use crate::filter::{Filter, ImageFilter, FilterQuality};
use crate::gradient::{CanvasGradient};
use crate::pattern::{CanvasPattern};
use crate::texture::{CanvasTexture};
use crate::image::ImageData;
use crate::gpu::RenderingEngine;
use page::{PageRecorder, Page, ExportOptions};

const BLACK:Color = Color::BLACK;
const TRANSPARENT:Color = Color::TRANSPARENT;


pub struct Context2D{
  pub bounds: Rect,
  pub recorder: RefCell<PageRecorder>,
  pub state: State,
  pub stack: Vec<State>,
  pub path: Path,
}

#[derive(Clone)]
pub struct State{
  pub clip: Option<Path>,
  pub matrix: Matrix,
  pub paint: Paint,

  pub fill_style: Dye,
  pub stroke_style: Dye,
  pub shadow_blur: f32,
  pub shadow_color: Color,
  pub shadow_offset: Point,

  pub stroke_width: f32,
  pub line_dash_offset: f32,
  pub line_dash_list: Vec<f32>,
  pub line_dash_marker: Option<Path>,
  pub line_dash_fit: path_1d_path_effect::Style,

  pub global_alpha: f32,
  pub global_composite_operation: BlendMode,
  pub image_filter: ImageFilter,
  pub filter: Filter,

  pub font: String,
  pub font_variant: String,
  pub font_width: Width,
  pub font_hinting: bool,
  pub char_style: TextStyle,
  pub graf_style: ParagraphStyle,
  pub text_baseline: Baseline,
  pub letter_spacing: Spacing,
  pub word_spacing: Spacing,
  pub text_decoration: DecorationStyle,
  pub text_wrap: bool,
  pub line_height: Option<f32>,
}

impl Default for State {
  /// Construct original default State/spacing/decoration with the same font, paint, baseline and cache-related fields; returns owned value, no new validation/errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:82, skia-canvas 3.0.8; original rendering body retained.
  fn default() -> Self {
    let mut paint = Paint::default();
    paint
      .set_stroke_miter(10.0)
      .set_color(BLACK)
      .set_anti_alias(true)
      .set_stroke_width(1.0)
      .set_style(PaintStyle::Fill);

    let graf_style = ParagraphStyle::new();
    let mut char_style = TextStyle::new();
    char_style.set_font_size(10.0);

    State {
      clip: None,
      matrix: Matrix::new_identity(),

      paint,
      stroke_style: Dye::Color(BLACK),
      fill_style: Dye::Color(BLACK),
      stroke_width: 1.0,
      line_dash_offset: 0.0,
      line_dash_list: vec![],
      line_dash_marker: None,
      line_dash_fit: path_1d_path_effect::Style::Rotate,

      global_alpha: 1.0,
      global_composite_operation: BlendMode::SrcOver,
      image_filter: ImageFilter{ smoothing:true, quality:FilterQuality::Low },
      filter: Filter::default(),

      shadow_blur: 0.0,
      shadow_color: TRANSPARENT,
      shadow_offset: (0.0, 0.0).into(),

      font: "10px sans-serif".to_string(),
      font_variant: "normal".to_string(),
      font_width: Width::NORMAL,
      font_hinting: false,
      char_style,
      graf_style,
      text_baseline: Baseline::Alphabetic,
      letter_spacing: Spacing::default(),
      word_spacing: Spacing::default(),
      text_decoration: DecorationStyle::default(),
      text_wrap: false,
      line_height: None,
    }
  }
}

impl State{
  /// Clone original character/paragraph/decoration/baseline/wrap state and apply original spacing, strut, line-height and hinting rules; sizes are canvas units, returns owned style tuple.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:134, skia-canvas 3.0.8; original rendering body retained.
  pub fn typography(&self) -> (TextStyle, ParagraphStyle, DecorationStyle, Baseline, bool) {
    let mut char_style = self.char_style.clone(); // use font size & style to calculate spacing
    char_style.set_word_spacing(self.word_spacing.in_px(char_style.font_size()));
    char_style.set_letter_spacing(self.letter_spacing.in_px(char_style.font_size()));
    char_style.set_baseline_shift(self.text_baseline.get_offset(&char_style));

    let mut graf_style = self.graf_style.clone(); // inherit align & ltr/rtl settings
    let font_families = char_style.font_families(); // consult proper metrics for height & leading defaults

    if self.text_wrap{
      // handle multi-line spacing
      let mut strut_style = StrutStyle::new();
      strut_style
        .set_font_families(&font_families.iter().collect::<Vec<_>>())
        .set_font_style(char_style.font_style())
        .set_font_size(char_style.font_size())
        .set_force_strut_height(true)
        .set_strut_enabled(true);

      // if lineHeight is unspecified leave letterspacing at -1 to use font's default spacing,
      // otherwise adjust strut's height & leading appropriately
      if let Some(height) = self.line_height{
        strut_style
          .set_leading((height - 1.0).max(0.0))
          .set_height(height.min(1.0))
          .set_height_override(true);
      }

      graf_style.set_strut_style(strut_style);
    }else{
      // omit anything that doesn't fit on a single line
      graf_style.set_max_lines(Some(1));
    }

    if !self.font_hinting{
      graf_style.turn_hinting_off();
    }

    ( char_style, graf_style, self.text_decoration.clone(), self.text_baseline, self.text_wrap )
  }

  /// Borrow original stroke/fill dye selected by paint style; returned reference is tied to State, no allocation/errors or ownership transfer.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:175, skia-canvas 3.0.8; original rendering body retained.
  fn dye(&self, style:PaintStyle) -> &Dye{
    if style == PaintStyle::Stroke{ &self.stroke_style }
    else{ &self.fill_style }
  }

  /// Borrow original texture only when the selected dye is Texture; returns optional reference tied to State, no new policy/errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:180, skia-canvas 3.0.8; original rendering body retained.
  fn texture(&self, style:PaintStyle) -> Option<&CanvasTexture>{
    match self.dye(style) {
      Dye::Texture(texture) => Some(texture),
      _ => None
    }
  }

}

impl Context2D{
  /// Construct original Canvas/Context/typesetter/style key from typed inputs; preserve default dimensions, style/font selection and operation order. Dimensions/coordinates are canvas units unless documented as pixels.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:190, skia-canvas 3.0.8; original rendering body retained.
  pub fn new() -> Self {
    let bounds = Rect::from_wh(300.0, 150.0);

    Context2D{
      bounds,
      recorder: RefCell::new(PageRecorder::new(bounds)),
      path: Path::new(),
      stack: vec![],
      state: State::default(),
    }
  }

  /// Map canvas-unit point through original inverse matrix, or return original zero fallback when singular; returns Point, no added validation.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:202, skia-canvas 3.0.8; original rendering body retained.
  pub fn in_local_coordinates(&mut self, x: f32, y: f32) -> Point{
    match self.state.matrix.invert(){
      Some(inverse) => inverse.map_point((x, y)),
      None => (x, y).into()
    }
  }

  /// Invoke FnOnce with original RefCell recorder borrow on owner thread; return unit and retain original borrow-conflict panic behavior.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:209, skia-canvas 3.0.8; original rendering body retained.
  pub fn with_recorder<'a, F>(&'a self, f:F)
    where F:FnOnce(std::cell::RefMut<'a, PageRecorder>)
  {
    f(self.recorder.borrow_mut());
  }

  /// Append original borrowed SkCanvas callback to recorder without moving context/recorder; return unit, original borrow rules retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:215, skia-canvas 3.0.8; original rendering body retained.
  pub fn with_canvas<F>(&self, f:F)
    where F:FnOnce(&SkCanvas)
  {
    self.with_recorder(|mut recorder|{
      recorder.append(f);
    });
  }

  /// Apply original mutable matrix callback then record current transform; matrix is unitless, callback/borrow lifetimes remain local.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:223, skia-canvas 3.0.8; original rendering body retained.
  pub fn with_matrix<F>(&mut self, f:F)
    where F:FnOnce(&mut Matrix) -> &Matrix
  {
    f(&mut self.state.matrix);
    self.with_recorder(|mut recorder|{
      recorder.set_matrix(self.state.matrix);
    });
  }

  /// Replay original shadow/composite/drawing order for borrowed paint and callback; no new surfaces, blend formulas or errors are substituted.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:232, skia-canvas 3.0.8; original rendering body retained.
  pub fn render_to_canvas<F>(&self, paint:&Paint, f:F)
    where F:Fn(&SkCanvas, &Paint)
  {
    let render_shadow = |canvas:&SkCanvas, paint:&Paint|{
      if let Some(shadow_paint) = self.paint_for_shadow(paint){
        canvas.save();
        canvas.set_matrix(&Matrix::translate(self.state.shadow_offset).into());
        canvas.concat(&self.state.matrix);
        f(canvas, &shadow_paint);
        canvas.restore();
      }
    };

    match self.state.global_composite_operation{
      BlendMode::SrcIn | BlendMode::SrcOut |
      BlendMode::DstIn | BlendMode::DstOut |
      BlendMode::DstATop | BlendMode::Src =>{
        // for blend modes that affect regions of the canvas outside of the bounds of the object
        // being drawn, create an intermediate picture before drawing to the canvas
        let mut layer_paint = paint.clone();
        layer_paint.set_blend_mode(BlendMode::SrcOver);
        let mut layer_recorder = PictureRecorder::new();
        layer_recorder.begin_recording(self.bounds, true);
        if let Some(layer) = layer_recorder.recording_canvas() {
          // draw the dropshadow (if applicable)
          render_shadow(layer, &layer_paint);
          // draw normally
          layer.set_matrix(&self.state.matrix.into());
          f(layer, &layer_paint);
        }

        // transfer the picture contents to the canvas in a single operation, applying the blend
        // mode to the whole canvas (regardless of the bounds of the text/path being drawn)
        if let Some(pict) = layer_recorder.finish_recording_as_picture(None){
          self.with_canvas(|canvas| {
            canvas.save();
            canvas.set_matrix(&Matrix::new_identity().into());
            let mut blend_paint = Paint::default();
            blend_paint.set_anti_alias(true);
            blend_paint.set_blend_mode(self.state.global_composite_operation);
            canvas.draw_picture(&pict, None, Some(&blend_paint));
            canvas.restore();
          });
        }

      },
      _ => {
        self.with_canvas(|canvas| {
          // draw the dropshadow (if applicable)
          render_shadow(canvas, paint);
          // draw with the normal paint
          f(canvas, paint);
        });
      }
    };

  }

  /// Map original f32 coordinate pairs through current matrix; canvas units, owned Vec<Point>, original odd-length/index behavior retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:290, skia-canvas 3.0.8; original rendering body retained.
  pub fn map_points(&self, coords:&[f32]) -> Vec<Point>{
    // treat the flat array of floats as x/y pairs
    coords
      .chunks_exact(2)
      .map(|pair|
        self.state.matrix.map_point(Point::new(pair[0], pair[1]))
      )
      .collect()
  }

  /// Reset original bounds/path/stack/state/recorder to supplied dimensions in canvas units; preserve reset order and owned resources.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:300, skia-canvas 3.0.8; original rendering body retained.
  pub fn reset_size(&mut self, dims: impl Into<Size>) {
    // called by the canvas when .width or .height are assigned to
    self.bounds = Rect::from_size(dims);
    self.path = Path::default();
    self.stack = vec![];
    self.state = State::default();

    // erase any existing content
    self.with_recorder(|mut recorder| {
      recorder.set_bounds(self.bounds);
    });
  }

  /// Resize original bounds/recording non-destructively using supplied canvas-unit dimensions; return unit with original state retention.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:313, skia-canvas 3.0.8; original rendering body retained.
  pub fn resize(&mut self, dims: impl Into<Size>) {
    // non-destructively resize the canvas (via the canvas.resize() extension)
    self.bounds = Rect::from_size(dims);
    self.with_recorder(|mut recorder| {
      recorder.update_bounds(self.bounds);
    });
  }

  /// Clone original state onto save stack (including shared Rc dyes); no GPU context transfer, return unit with original allocation behavior.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:321, skia-canvas 3.0.8; original rendering body retained.
  pub fn push(&mut self){
    let new_state = self.state.clone();
    self.stack.push(new_state);
  }

  /// Restore original saved state/matrix/clip if present; returns unit and retains empty-stack behavior and shared-resource references.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:326, skia-canvas 3.0.8; original rendering body retained.
  pub fn pop(&mut self){
    // don't do anything if we're already back at the initial stack frame
    if let Some(old_state) = self.stack.pop(){
      self.state = old_state;

      self.with_recorder(|mut recorder|{
        recorder.set_matrix(self.state.matrix);
        recorder.set_clip(&self.state.clip);
      });
    }
  }

  /// Set original initial point for empty path using supplied canvas-unit point; returns unit without new geometry or errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:338, skia-canvas 3.0.8; original rendering body retained.
  pub fn scoot(&mut self, point:Point){
    // update initial point if first drawing command isn't a moveTo
    if self.path.is_empty(){
      self.path.move_to(point);
    }
  }

  /// Draw original optional path/style/fill-rule with original transform, opaque-clear optimization, texture stencil and paint order; canvas units, no geometry/shader rewrite.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:345, skia-canvas 3.0.8; original rendering body retained.
  pub fn draw_path(&mut self, path:Option<Path>, style:PaintStyle, rule:Option<PathFillType>){
    let mut path = path.unwrap_or_else(|| {
      // the current path has already incorporated its transform state
      let inverse = self.state.matrix.invert().unwrap_or_default();
      self.path.with_transform(&inverse)
    });
    path.set_fill_type(rule.unwrap_or(PathFillType::Winding));

    // if path will fill the whole canvas and paint/blend are fully opaque...
    if matches!(style, PaintStyle::Fill | PaintStyle::StrokeAndFill) &&
      matches!(&self.state.global_composite_operation, BlendMode::SrcOver | BlendMode::Src | BlendMode::Clear) &&
      self.state.fill_style.is_opaque() &&
      self.state.global_alpha == 1.0 &&
      self.state.clip.is_none() &&
      path.conservatively_contains_rect(self.bounds)
    {
      // ...erase existing vector content layers (but preserve CTM & clip path)
      self.with_recorder(|mut recorder|{
        recorder.set_bounds(self.bounds);
        recorder.set_matrix(self.state.matrix);
        recorder.set_clip(&self.state.clip);
      });
    }

    let paint = self.paint_for_drawing(style);
    self.render_to_canvas(&paint, |canvas, paint| {
      if let Some(tile) = self.state.texture(style){
        // SKIA PATH EFFECT BUG WORKAROUND:
        //
        // Simply mixing the PathEffect into the paint and drawing totally misjudges the boundaries of the
        // path being filled/stroked. Instead we'll create a path with the texture and a path with the
        // desired outline separately, then draw their overlap

        // paint containing the PathEffect
        let mut tile_paint = paint.clone();
        tile.mix_into(&mut tile_paint, self.state.global_alpha);

        // outline strokes on user path (if paint style is stroke) so we can use a fill operation below
        let mut stencil = Path::default();
        fill_path_with_paint(&path, paint, &mut stencil, None, None);

        // construct a rectangle significantly larger than the path + stroke area (1.5x seems to work?)
        let expanded_bounds = stencil.bounds().with_outset(tile.spacing() * 1.5);
        let enclosing_frame = Path::rect(expanded_bounds, None);

        if tile.use_clip(){
          // apply the user path as a clipping mask and fill the whole enclosing rect with tile pattern
          canvas.save();
          canvas.clip_path(&stencil, Some(ClipOp::Intersect), Some(true));
          canvas.draw_path(&enclosing_frame, &tile_paint);
          canvas.restore();
        }else{
          // create a path merging the the tile pattern outlines and the enclosing rectangle
          let mut textured_frame = Path::default();
          fill_path_with_paint(&enclosing_frame, &tile_paint, &mut textured_frame, None, None);

          // intersect the rectangular texture with the user path and fill with flat color
          let mut fill_paint = paint.clone();
          fill_paint.set_style(PaintStyle::Fill);
          if let Some(fill_path) = stencil.op(&textured_frame, PathOp::Intersect){
            canvas.draw_path(&fill_path, &fill_paint);
          }
        }
      }else{
        canvas.draw_path(&path, paint);
      }
    });
  }

  /// Intersect original transformed path with existing clip and preserve full-bounds optimization; canvas units and original fill-rule behavior, returns unit.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:414, skia-canvas 3.0.8; original rendering body retained.
  pub fn clip_path(&mut self, path: Option<Path>, rule:PathFillType){
    let mut clip = match path{
      Some(path) => path.with_transform(&self.state.matrix),
      None => self.path.clone()
    };
    clip.set_fill_type(rule);

    // update the clip with the intersection of the new path, unless it's larger than
    // the canvas itself in which case the whole clip is discarded
    self.state.clip = self.state.clip.as_ref()
      .unwrap_or(&Path::rect(self.bounds, None))
      .op(&clip, PathOp::Intersect)
      .and_then(|path| match path.conservatively_contains_rect(self.bounds){
        true => None,
        false => Some(path),
      });

    self.with_recorder(|mut recorder|{
      recorder.set_clip(&self.state.clip);
    });
  }

  /// Perform original fill/stroke hit test with original 0.3 precision and temporary fill-rule restoration; returns boolean, coordinates in canvas units.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:436, skia-canvas 3.0.8; original rendering body retained.
  pub fn hit_test_path(&mut self, path: &mut Path, point:impl Into<Point>, rule:Option<PathFillType>, style: PaintStyle) -> bool {
    let point = point.into();
    let point = self.in_local_coordinates(point.x, point.y);
    let rule = rule.unwrap_or(PathFillType::Winding);
    let prev_rule = path.fill_type();
    path.set_fill_type(rule);

    let is_in = match style{
      PaintStyle::Stroke => {
        let paint = self.paint_for_drawing(PaintStyle::Stroke);
        let precision = 0.3; // this is what Chrome uses to compute this
        let scale = Matrix::scale((precision, precision));

        let mut traced_path = Path::default();
        if fill_path_with_paint(path, &paint, &mut traced_path, None, Some(scale)){
          traced_path.contains(point)
        }else{
          path.contains(point)
        }
      },
      _ => path.contains(point)
    };

    path.set_fill_type(prev_rule);
    is_in
  }

  /// Clear original rect with original full-canvas reset/partial Clear blend behavior; borrowed canvas-unit rect, returns unit.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:463, skia-canvas 3.0.8; original rendering body retained.
  pub fn clear_rect(&mut self, rect:&Rect){
    match self.state.matrix.map_rect(rect).0.contains(self.bounds){

      // if rect fully encloses canvas, erase existing content (but preserve CTM & clip path)
      true =>  self.with_recorder(|mut recorder|{
        recorder.set_bounds(self.bounds);
        recorder.set_matrix(self.state.matrix);
        recorder.set_clip(&self.state.clip);
      }),

      // otherwise, paint over the specified region but preserve overdrawn vectors
      false => self.with_canvas(|canvas| {
        let mut paint = Paint::default();
        paint.set_anti_alias(true)
             .set_style(PaintStyle::Fill)
             .set_blend_mode(BlendMode::Clear);
        canvas.draw_rect(rect, &paint);
      })
    }
  }

  /// Replay original borrowed Picture using source/destination canvas-unit rect transform and clip; returns unit with original sampling/composite order.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:484, skia-canvas 3.0.8; original rendering body retained.
  pub fn draw_picture(&mut self, picture:&Picture, src_rect:&Rect, dst_rect:&Rect){
    let paint = self.paint_for_image();
    let mag = Point::new(dst_rect.width()/src_rect.width(), dst_rect.height()/src_rect.height());
    let mut matrix = Matrix::new_identity();
    matrix.pre_scale( (mag.x, mag.y), None )
      .pre_translate((dst_rect.x()/mag.x - src_rect.x(), dst_rect.y()/mag.y - src_rect.y()));

    self.render_to_canvas(&paint, |canvas, paint| {
      // only use paint if we need it for alpha, blend, shadow, or effect since otherwise
      // the SVG exporter will omit the picture altogether
      let paint = match (paint.as_blend_mode(), paint.alpha(), paint.image_filter()) {
        (Some(BlendMode::SrcOver), 255, None) => None,
        _ => Some(paint)
      };
      canvas.save();
      canvas.clip_rect(dst_rect, ClipOp::Intersect, true);
      canvas.draw_picture(&picture, Some(&matrix), paint);
      canvas.restore();
    });
  }

  /// Draw original borrowed Skia image using source/destination rects and original strict source constraint/paint; no resize/crop compensation added.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:505, skia-canvas 3.0.8; original rendering body retained.
  pub fn draw_image(&mut self, image:&Image, src_rect:&Rect, dst_rect:&Rect){
    let paint = self.paint_for_image();
    self.render_to_canvas(&paint, |canvas, paint| {
      let sampling = self.state.image_filter.sampling();
      canvas.draw_image_rect_with_sampling_options(image, Some((src_rect, Strict)), dst_rect, sampling, paint);
    });
  }

  /// Return original owned recorder Page snapshot; preserve original layer/cache ownership and RefCell borrow behavior.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:513, skia-canvas 3.0.8; original rendering body retained.
  pub fn get_page(&self) -> Page {
    self.recorder.borrow_mut().get_page()
  }

  /// Return original Page snapshot for options and engine, preserving original cache update/materialize boundary.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:517, skia-canvas 3.0.8; original rendering body retained.
  pub fn get_page_for_export(&self, opts:&ExportOptions, engine:&RenderingEngine) -> Page {
    self.recorder.borrow_mut().get_page_for_export(opts, engine)
  }

  /// Return original optional owned image from recorder; no new bitmap path, ownership or error policy.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:521, skia-canvas 3.0.8; original rendering body retained.
  pub fn get_image(&self) -> Option<Image> {
    self.recorder.borrow_mut().get_image()
  }

  /// Return original optional owned Picture from recorder; no replacement drawing model or new validation.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:525, skia-canvas 3.0.8; original rendering body retained.
  pub fn get_picture(&mut self) -> Option<Picture> {
    self.recorder.borrow_mut().get_page().get_picture(None)
  }

  /// Read original integer-pixel crop with options/engine into owned bytes; preserve RGBA/color/alpha/row layout and original String errors.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:529, skia-canvas 3.0.8; original rendering body retained.
  pub fn get_pixels(&mut self, crop:IRect, opts:ExportOptions, engine:RenderingEngine) -> Result<Vec<u8>, String>{
    self.recorder.borrow_mut().get_pixels(crop, opts, engine)
  }

  /// Consume original ImageData and draw original source/destination pixel rects using original reset/clip/transform rules; no premultiplication workaround.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:533, skia-canvas 3.0.8; original rendering body retained.
  pub fn blit_pixels(&mut self, image_data:ImageData, src_rect:&Rect, dst_rect:&Rect){
    // works just like draw_image in terms of src/dst rects, but clears the dst_rect and then draws
    // without clips, transforms, alpha, blend, or shadows
    let info = image_data.image_info();
    if let Some(bitmap) = images::raster_from_data(&info, image_data.buffer, info.min_row_bytes()) {
      self.push(); // cache matrix & clip in self.state
      self.with_canvas(|canvas| {
        let paint = Paint::default();
        let mut eraser = Paint::default();
        canvas.restore_to_count(1); // discard current matrix & clip
        eraser.set_blend_mode(BlendMode::Clear);
        canvas.draw_image_rect(&bitmap, Some((src_rect, Strict)), dst_rect, &eraser);
        canvas.draw_image_rect(&bitmap, Some((src_rect, Strict)), dst_rect, &paint);
      });
      self.pop(); // restore discarded matrix & clip
    }
  }

  /// Apply original parsed FontSpec and font-library style update, including line height/features/variant/width; sizes in canvas units, original invalid-style retention.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:551, skia-canvas 3.0.8; original rendering body retained.
  pub fn set_font(&mut self, spec: FontSpec){
    if let Some(new_style) = FontLibrary::with_shared(|lib|
      lib.update_style(&self.state.char_style, &spec)
    ){
      self.state.font = spec.canonical;
      self.state.font_variant = spec.variant.to_string();
      self.state.font_width = spec.width;
      self.state.char_style = new_style;
      self.state.line_height = spec.line_height;
    }
  }

  /// Store original variant/features and update character style using original font metadata; returns unit, no new shaping or fallback.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:563, skia-canvas 3.0.8; original rendering body retained.
  pub fn set_font_variant(&mut self, variant:&str, features:&[(String, i32)]){
    self.state.char_style.reset_font_features();
    for (feat, val) in features{
      self.state.char_style.add_font_feature(feat, *val);
    }
    self.state.font_variant = variant.to_string();
  }

  /// Update original font stretch using typed Width and existing style; no CSS parsing/validation duplication, returns unit.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:571, skia-canvas 3.0.8; original rendering body retained.
  pub fn set_font_width(&mut self, width:Width){
    let style = self.state.char_style.font_style();
    let font_style =  FontStyle::new(style.weight(), width, style.slant());
    self.state.char_style.set_font_style(font_style);
    self.state.font_width = width;
  }

  /// Draw original text with typesetter, x/y/maxWidth in canvas units and original fill/stroke paint, baseline and compositing; no layout/shaping rewrite.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:578, skia-canvas 3.0.8; original rendering body retained.
  pub fn draw_text(&mut self, text: &str, x: f32, y: f32, width: Option<f32>, style:PaintStyle){
    let paint = self.paint_for_drawing(style);
    let mut typesetter = Typesetter::new(&self.state, text, width);
    let origin = Point::new(x, y);

    if self.state.texture(style).is_some(){
      // if dye is a texture, convert text to path first
      self.draw_path(Some(typesetter.path(origin)), style, None);
    }else{
      self.render_to_canvas(&paint, |canvas, paint| {
        let (paragraph, offset) = typesetter.layout(paint);
        paragraph.paint(canvas, origin + offset);
      });
    }
  }

  /// Return original JSON metrics for text/optional canvas-unit width, including all original UTF-16 offsets and line/run fields; original shaping/font rules retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:594, skia-canvas 3.0.8; original rendering body retained.
  pub fn measure_text(&mut self, text: &str, width:Option<f32>) -> serde_json::Value{
    Typesetter::new(&self.state, text, width).metrics()
  }

  /// Return original Skia text outline path from typesetter for text/optional canvas-unit width; no glyph tracing replacement.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:598, skia-canvas 3.0.8; original rendering body retained.
  pub fn outline_text(&self, text:&str, width:Option<f32>) -> Path{
    Typesetter::new(&self.state, text, width).path((0.0, 0.0))
  }

  /// Clone/configure original paint, alpha, dye, dash, marker, filter and texture rules for paint style; returns owned Paint, original order preserved.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:602, skia-canvas 3.0.8; original rendering body retained.
  pub fn paint_for_drawing(&mut self, style:PaintStyle) -> Paint{
    let mut paint = self.state.paint.clone();
    self.state.filter.mix_into(&mut paint, self.state.matrix, false);
    self.state.dye(style).mix_into(&mut paint, self.state.global_alpha, self.state.image_filter);
    paint.set_style(style);

    if style==PaintStyle::Stroke && !self.state.line_dash_list.is_empty(){
      // if marker is set, apply the 1d_path_effect instead of the dash_path_effect
      let effect = match &self.state.line_dash_marker{
        Some(path) => {
          let marker = match path.is_last_contour_closed(){
            true => path.clone(),
            false => {
              let mut traced_path = Path::default();
              fill_path_with_paint(path, &paint, &mut traced_path, None, None);
              traced_path
            }
          };
          path_1d_path_effect::new(
            &marker,
            self.state.line_dash_list[0],
            self.state.line_dash_offset,
            self.state.line_dash_fit
          )
        }
        None => dash_path_effect::new(&self.state.line_dash_list, self.state.line_dash_offset)
      };

      paint.set_path_effect(effect);
    }

    paint
  }

  /// Return original owned image paint with original filter/current matrix/global alpha; no new color or sampling policy.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:636, skia-canvas 3.0.8; original rendering body retained.
  pub fn paint_for_image(&mut self) -> Paint {
    let mut paint = self.state.paint.clone();
    self.state.filter.mix_into(&mut paint, self.state.matrix, true)
      .set_alpha_f(self.state.global_alpha);
    paint
  }

  /// Return original optional shadow paint with original sigma/decomposed-scale handling; lengths in canvas units, original singular-scale behavior retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:643, skia-canvas 3.0.8; original rendering body retained.
  pub fn paint_for_shadow(&self, base_paint:&Paint) -> Option<Paint> {
    let State {shadow_color, mut shadow_blur, shadow_offset, ..} = self.state;
    if shadow_color.a() == 0 || (shadow_blur == 0.0 && shadow_offset.is_zero()){
      return None
    }

    // Per spec, sigma is exactly half the blur radius:
    // https://www.w3.org/TR/css-backgrounds-3/#shadow-blur
    shadow_blur *= 0.5;
    let mut sigma = Point::new(shadow_blur, shadow_blur);
    // Apply scaling from the current transform matrix to blur radius, if there is any of either.
    if self.state.matrix.get_type().contains(TypeMask::SCALE) && !almost_zero(shadow_blur) {
      // Decompose the matrix to just the scaling factors (matrix.scale_x/y() methods just return M11/M22 values)
      if let Some(scale) = self.state.matrix.decompose_scale(None) {
        if almost_zero(scale.width) {
          sigma.x = 0.0;
        } else {
          sigma.x /= scale.width as f32;
        }
        if almost_zero(scale.height) {
          sigma.y = 0.0;
        } else {
          sigma.y /= scale.height as f32;
        }
      }
    }
    let mut paint = base_paint.clone();
    paint.set_image_filter(image_filters::drop_shadow_only((0.0, 0.0), (sigma.x, sigma.y), shadow_color, ColorSpace::new_srgb(), None, None));
    Some(paint)
  }

}

//
// Dye abstraction for Color / CanvasGradient / CanvasPattern
//

#[derive(Clone)]
pub enum Dye{
  Color(Color),
  Gradient(CanvasGradient),
  Pattern(CanvasPattern),
  Texture(CanvasTexture)
}

impl Dye{


  /// Return original dye opacity using underlying color/gradient/pattern policy; no allocation, tolerance or new ownership.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:708, skia-canvas 3.0.8; original rendering body retained.
  pub fn is_opaque(&self) -> bool{
    match self {
      Dye::Color(color) => Color4f::from(*color).is_opaque(),
      Dye::Gradient(gradient) => gradient.is_opaque(),
      Dye::Pattern(pattern) => pattern.is_opaque(),
      Dye::Texture(_) => false,
    }
  }

  /// Apply original dye to borrowed Paint using scalar alpha and original image sampling; preserves Color4f rounding, shader and texture policy.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/context/mod.rs:717, skia-canvas 3.0.8; original rendering body retained.
  pub fn mix_into(&self, paint: &mut Paint, alpha: f32, image_filter: ImageFilter){
    match self {
      Dye::Color(color) => {
        let mut color = Color4f::from(*color);
        color.a *= alpha;
        paint.set_color(color.to_color());
      },
      Dye::Gradient(gradient) =>{
        paint.set_shader(gradient.shader())
             .set_alpha_f(alpha);
      },
      Dye::Pattern(pattern) =>{
        paint.set_shader(pattern.shader(image_filter))
             .set_alpha_f(alpha);
      }
      Dye::Texture(texture) =>{
        paint.set_color(texture.to_color(alpha));
      }
    };
  }
}
