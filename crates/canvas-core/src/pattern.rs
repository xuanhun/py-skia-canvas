#![allow(non_snake_case)]
use std::cell::RefCell;
use std::rc::Rc;
use skia_safe::{Shader, TileMode, Size, Rect, Matrix, FilterMode};

use crate::image::{Content, ImageData};
use crate::filter::ImageFilter;



pub struct Stamp{
  content: Content,
  dims:Size,
  repeat:(TileMode, TileMode),
  matrix:Matrix
}

#[derive(Clone)]
pub struct CanvasPattern{
  pub stamp:Rc<RefCell<Stamp>>
}

impl CanvasPattern{
  /// Return original bitmap/picture shader using borrowed shared stamp, repeat modes, unitless matrix and image sampling; returns None for non-drawable content.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:29, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn shader(&self, image_filter: ImageFilter) -> Option<Shader>{
    let stamp = self.stamp.borrow();

    match &stamp.content{
      Content::Bitmap(image) =>
        image.to_shader(stamp.repeat, image_filter.sampling(), None).map(|shader|
          shader.with_local_matrix(&stamp.matrix)
        ),
      Content::Vector(pict, ..) => {
        let tile_rect = Rect::from_size(stamp.dims);
        let shader = pict.to_shader(stamp.repeat, FilterMode::Linear, None, Some(&tile_rect));
        Some(shader.with_local_matrix(&stamp.matrix))
      },
      _ => None
    }
  }

  /// Return bitmap opacity; vector and other content remain false as upstream. No units or ownership transfer; RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:46, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn is_opaque(&self) -> bool{
    let stamp = self.stamp.borrow();

    match &stamp.content{
      Content::Bitmap(image) => image.is_opaque(),
      _ => false
    }
  }
}


impl CanvasPattern{
  /// Own cloned content/dimensions and repeat modes, preserving original SVG autosizing from canvas dimensions. Lengths are canvas units; returns shared pattern without new errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:60, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn from_image(content:Content, dims:Size, autosized:bool, canvas_width:f32, canvas_height:f32, repeat:(TileMode,TileMode)) -> Self {
    let mut matrix = Matrix::new_identity();
    if autosized && !dims.is_empty() {
      // Original SVG autosizing: fit the canvas' smallest dimension.
      let min_size = f32::min(canvas_width, canvas_height);
      let factor = (min_size / dims.width, min_size / dims.height);
      matrix.set_scale(factor, None);
    }
    let stamp = Stamp{content, dims, repeat, matrix};
    let canvas_pattern = CanvasPattern{ stamp:Rc::new(RefCell::new(stamp))};
    canvas_pattern
  }

  /// Consume pixel data and repeat modes into original shared stamp; dimensions are pixels, raster allocation failure retains original Loading fallback.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:85, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn from_image_data(src:ImageData, repeat:(TileMode,TileMode)) -> Self {
    let content = Content::from_image_data(src);
    let dims:Size = content.size().into();
    let matrix = Matrix::new_identity();
    let stamp = Stamp{content, dims, repeat, matrix};
    let canvas_pattern = CanvasPattern{ stamp:Rc::new(RefCell::new(stamp))};
    canvas_pattern
  }

  /// Own the original picture snapshot, dimensions (canvas units), repeat modes and matrix; returns shared pattern, no new validation/errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:98, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn from_canvas(content:Content, dims:Size, repeat:(TileMode,TileMode), matrix:Matrix) -> Self {
    let stamp = Stamp{content, dims, repeat, matrix};
    let canvas_pattern = CanvasPattern{ stamp:Rc::new(RefCell::new(stamp))};
    canvas_pattern
  }

  /// Replace shared stamp matrix (unitless transform); returns unit and retains original RefCell borrow panic conditions.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:115-122 (setTransform), skia-canvas 3.0.8; stamp mutation retained.
  pub fn set_transform(&self, matrix:Matrix) {
    let mut stamp = self.stamp.borrow_mut();
    stamp.matrix = matrix;
  }

  /// Return original content style and intrinsic dimensions as owned text; RefCell conflicts panic, no GPU ownership transfer.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/pattern.rs:125, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn repr(&self) -> String {
    let stamp = self.stamp.borrow();
    let style = match stamp.content{
      Content::Bitmap(..) => "Bitmap",
      _ => "Canvas"
    };
    format!("{} {}×{}", style, stamp.dims.width, stamp.dims.height)
  }
}
