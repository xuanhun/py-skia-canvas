//! Original owned image content and ImageData, independent of language bindings.
use skia_safe::{Image as SkImage, ImageInfo, ColorType, ColorSpace, AlphaType, Data, Size, Picture, Rect, image::images};
use crate::context::Context2D;
use crate::utils::{to_color_space, to_color_type};

pub enum Content{
  Bitmap(SkImage),
  Vector(Picture, Size),
  Loading,
  Broken,
}

impl Default for Content{
  /// Return original Loading content with no input, allocation or errors. Broken cloning behavior remains unchanged.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:37, skia-canvas 3.0.8. Rendering bodies retained.
  fn default() -> Self {
      Content::Loading
  }
}

impl Clone for Content{
  /// Clone Skia image/picture ownership and size; other variants become Loading exactly as upstream. No GPU context is moved.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:43, skia-canvas 3.0.8. Rendering bodies retained.
  fn clone(&self) -> Self {
      match self{
        Content::Bitmap(img) => Content::Bitmap(img.clone()),
        Content::Vector(pict, size) => Content::Vector(pict.clone(), size.clone()),
        _ => Content::default()
      }
  }
}

impl Content{

  /// Consume original ImageData and create raster content with Unpremul info/minimum row bytes; failure returns Loading as upstream.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:60, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn from_image_data(image_data:ImageData) -> Self{
    let info = image_data.image_info();
    images::raster_from_data(&info, &image_data.buffer, info.min_row_bytes())
      .map(|image| Content::Bitmap(image) )
      .unwrap_or_default()
  }

  /// Return intrinsic dimensions in canvas units, or original empty size for non-drawable states; no ownership transfer/errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:67, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn size(&self) -> Size {
    match &self {
      Content::Bitmap(img) => img.dimensions().into(),
      Content::Vector(_, size) => *size,
      _ => Size::new_empty()
    }
  }

  /// Report original completion state (only Loading is incomplete); no allocation or errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:75, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn is_complete(&self) -> bool {
    match &self{
      Content::Loading => false,
      _ => true
    }
  }

  /// Report original drawable state (Bitmap/Vector only); no allocation or errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:82, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn is_drawable(&self) -> bool {
    match &self{
      Content::Loading | Content::Broken => false,
      _ => true
    }
  }

  /// Clip source to intrinsic bounds and adjust destination in canvas units using original arithmetic; returns both rects, non-finite math propagates.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:89, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn snap_rects_to_bounds(&self, mut src: Rect, mut dst: Rect) -> (Rect, Rect) {
    // Handle 'overdraw' of the src image where the crop coordinates are outside of its bounds
    // Snap the src rect to its actual bounds and shift/pad the dst rect to account for the
    // whitespace included in the crop.
    let scale_x = dst.width() / src.width();
    let scale_y = dst.height() / src.height();
    let size = self.size();

    if src.left < 0.0 {
      dst.left += -src.left * scale_x;
      src.left = 0.0;
    }

    if src.top < 0.0 {
      dst.top += -src.top * scale_y;
      src.top = 0.0;
    }

    if src.right > size.width{
      dst.right -= (src.right - size.width) * scale_x;
      src.right = size.width;
    }

    if src.bottom > size.height{
      dst.bottom -= (src.bottom - size.height) * scale_y;
      src.bottom = size.height;
    }

    (src, dst)
  }
}


#[derive(Debug)]
pub struct ImageData{
  pub width: f32,
  pub height: f32,
  pub buffer: Data,
  color_type: ColorType,
  color_space: ColorSpace,
}

impl ImageData{
  /// Own Skia Data plus f32 dimensions (pixels) and original color type/space strings; returns ImageData with upstream fallbacks, no new validation.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:132, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn new(buffer:Data, width:f32, height:f32, color_type:String, color_space:String) -> Self{
    let color_type = to_color_type(&color_type);
    let color_space = to_color_space(&color_space);
    Self{ buffer, width, height, color_type, color_space }
  }

  /// Return original Unpremul ImageInfo, casting f32 pixel dimensions at the original point; clone color-space ownership, no new validation/errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/image.rs:138, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn image_info(&self) -> ImageInfo{
    ImageInfo::new(
      (self.width as _, self.height as _),
      self.color_type,
      AlphaType::Unpremul,
      self.color_space.clone()
    )
  }
}




impl Content {
  /// Original owner-thread Context snapshot bridge; returns Picture/bitmap or Loading, canvas-unit bounds.
  /// No GPU context is moved; upstream src/image.rs:53-58, v3.0.8; body unchanged.
  pub fn from_context(ctx:&mut Context2D, use_vector:bool) -> Self{
    match use_vector{
      true => ctx.get_picture().map(|p| Content::Vector(p, ctx.bounds.size())),
      false => ctx.get_image().map(|i| Content::Bitmap(i)),
    }.unwrap_or_default()
  }
}

pub mod loading;
pub mod operations;
pub use loading::Image;
