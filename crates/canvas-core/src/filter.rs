#![allow(unused_mut)]
#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(dead_code)]
use std::fmt;
use skia_safe::{Paint, Matrix, Point, Color, MaskFilter, ImageFilter as SkImageFilter,
                BlurStyle, FilterMode, MipmapMode, SamplingOptions, TileMode, ColorSpace,
                image_filters, color_filters, table_color_filter};

use crate::utils::*;

#[derive(Clone, Debug)]
pub enum FilterSpec{
  Plain{name:String, value:f32},
  Shadow{offset:Point, blur:f32, color:Color},
}

#[derive(Clone, Debug)]
pub struct Filter {
  pub css: String,
  specs: Vec<FilterSpec>,
  _raster: Option<LastFilter>,
  _vector: Option<LastFilter>
}

#[derive(Clone, Debug)]
pub struct LastFilter {
  matrix: Matrix,
  mask: Option<MaskFilter>,
  image: Option<SkImageFilter>
}

impl LastFilter {
  /// Reuse this owned cache entry when matrix X/Y scales match exactly.
  /// Matrix components are unitless; returns a cloned entry or None, without errors.
  /// Call on the owner thread of the associated Skia paint; no context is moved.
  /// Upstream: src/filter.rs:34-40 (v3.0.8), unchanged body.
  fn match_scale(&self, matrix:Matrix) -> Option<Self> {
    if self.matrix.scale_x() == matrix.scale_x() && self.matrix.scale_y() == matrix.scale_y(){
      Some(self.clone())
    }else{
      None
    }
  }
}

impl Default for Filter{
  /// Construct the original "none" CSS filter with empty raster/vector caches.
  /// No inputs, errors or GPU allocation; returns an owned Filter for the paint owner.
  /// Upstream: src/filter.rs:44-46 (v3.0.8), unchanged body.
  fn default() -> Self {
    Filter{ css:"none".to_string(), specs:vec![], _raster:None, _vector:None }
  }
}

impl fmt::Display for Filter {
  /// Write the original CSS text to the borrowed formatter; propagates formatting errors.
  /// No units or ownership transfer; use on the Filter's owning thread.
  /// Upstream: src/filter.rs:50-52 (v3.0.8), unchanged body.
  fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
      write!(f, "{}", self.css)
  }
}

impl Filter {
  /// Own a copy of CSS text and already-parsed specs; does not perform CSS parsing.
  /// Plain values retain their upstream units; shadow offsets/blur are canvas units.
  /// Returns an owned, uncached Filter; no validation errors. Keep with its paint owner.
  /// Upstream: src/filter.rs:56-60 (v3.0.8), unchanged body.
  pub fn new(css:&str, specs:&[FilterSpec]) -> Self {
    let css = css.to_string();
    let specs = specs.to_vec();
    Filter{ css, specs, _raster:None, _vector:None }
  }

  /// Apply cached/built effects to a borrowed paint using the current unitless matrix.
  /// `raster` chooses the original raster/vector blur policy. Returns the same paint borrow.
  /// May panic if upstream filter creation fails; no GPU context is sent between threads.
  /// Upstream: src/filter.rs:62-66 (v3.0.8), unchanged body.
  pub fn mix_into<'a>(&mut self, paint:&'a mut Paint, matrix:Matrix, raster:bool) -> &'a mut Paint {
    let filters = self.filters_for(matrix, raster);
    paint.set_image_filter(filters.image)
         .set_mask_filter(filters.mask)
  }

  /// Obtain/cache original Skia filters for unitless matrix scales and raster/vector mode.
  /// Returns an owned cache entry; panics on upstream creation failure. Mutates only self.
  /// Operate with the paint owner; no cross-thread GPU ownership is introduced.
  /// Upstream: src/filter.rs:68-196 (v3.0.8), unchanged body and mixing formulas.
  fn filters_for(&mut self, matrix:Matrix, raster:bool) -> LastFilter {
    let cached = match (raster, &self._raster, &self._vector) {
      (true, Some(cached), _) | (false, _, Some(cached)) => cached.match_scale(matrix),
      _ => None
    };

    cached.or_else(|| {
      let mut mask_filter = None;
      let image_filter = self.specs.iter().fold(None, |chain, next_filter|
        match next_filter {
          FilterSpec::Shadow{ offset, blur, color } => {
            let scale = Point{x:matrix.scale_x(), y:matrix.scale_y()};
            let point = (offset.x / scale.x, offset.y / scale.y);
            let sigma = (    blur / scale.x,     blur / scale.y);
            image_filters::drop_shadow(point, sigma, *color, ColorSpace::new_srgb(), chain, None)
          },
          FilterSpec::Plain{ name, value } => match name.as_ref() {
            "blur" => {
              if raster {
                let sigma_x = value / (2.0 * matrix.scale_x());
                let sigma_y = value / (2.0 * matrix.scale_y());
                image_filters::blur((sigma_x, sigma_y), TileMode::Decal, chain, None)
              } else {
                mask_filter = MaskFilter::blur(BlurStyle::Normal, *value, false);
                chain
              }
            },

            //
            // matrices and formulæ taken from: https://www.w3.org/TR/filter-effects-1/
            //
            "brightness" => {
              let amt = value.max(0.0);
              let color_matrix = color_filters::matrix_row_major(&[
                amt,  0.0,  0.0,  0.0, 0.0,
                0.0,  amt,  0.0,  0.0, 0.0,
                0.0,  0.0,  amt,  0.0, 0.0,
                0.0,  0.0,  0.0,  1.0, 0.0
              ], None);
              image_filters::color_filter(color_matrix, chain, None)
            },
            "contrast" => {
              let amt = value.max(0.0);
              let mut ramp = [0u8; 256];
              for (i, val) in ramp.iter_mut().take(256).enumerate() {
                let orig = i as f32;
                *val = (127.0 + amt * orig - (127.0 * amt )) as u8;
              }
              let table = Some(&ramp);
              if let Some(color_table) = color_filters::table_argb(None, table, table, table){
                image_filters::color_filter(color_table, chain, None)
              }else{
                chain
              }
            },
            "grayscale" => {
              let amt = 1.0 - value.clamp(0.0, 1.0);
              let color_matrix = color_filters::matrix_row_major(&[
                (0.2126 + 0.7874 * amt), (0.7152 - 0.7152  * amt), (0.0722 - 0.0722 * amt), 0.0, 0.0,
                (0.2126 - 0.2126 * amt), (0.7152 + 0.2848  * amt), (0.0722 - 0.0722 * amt), 0.0, 0.0,
                (0.2126 - 0.2126 * amt), (0.7152 - 0.7152  * amt), (0.0722 + 0.9278 * amt), 0.0, 0.0,
                 0.0,                     0.0,                      0.0,                    1.0, 0.0
              ], None);
              image_filters::color_filter(color_matrix, chain, None)
            },
            "invert" => {
              let amt = value.clamp(0.0, 1.0);
              let mut ramp = [0u8; 256];
              for (i, val) in ramp.iter_mut().take(256).enumerate().map(|(i,v)| (i as f32, v)) {
                let (orig, inv) = (i, 255.0-i);
                *val = (orig * (1.0 - amt) + inv * amt) as u8;
              }
              let table = Some(&ramp);
              if let Some(color_table) = color_filters::table_argb(None, table, table, table){
                image_filters::color_filter(color_table, chain, None)
              }else{
                chain
              }
            },
            "opacity" => {
              let amt = value.clamp(0.0, 1.0);
              let color_matrix = color_filters::matrix_row_major(&[
                1.0,  0.0,  0.0,  0.0,  0.0,
                0.0,  1.0,  0.0,  0.0,  0.0,
                0.0,  0.0,  1.0,  0.0,  0.0,
                0.0,  0.0,  0.0,  amt,  0.0
              ], None);
              image_filters::color_filter(color_matrix, chain, None)
            },
            "saturate" => {
              let amt = value.max(0.0);
              let color_matrix = color_filters::matrix_row_major(&[
                (0.2126 + 0.7874 * amt), (0.7152 - 0.7152 * amt), (0.0722 - 0.0722 * amt), 0.0, 0.0,
                (0.2126 - 0.2126 * amt), (0.7152 + 0.2848 * amt), (0.0722 - 0.0722 * amt), 0.0, 0.0,
                (0.2126 - 0.2126 * amt), (0.7152 - 0.7152 * amt), (0.0722 + 0.9278 * amt), 0.0, 0.0,
                 0.0,                     0.0,                     0.0,                    1.0, 0.0
              ], None);
              image_filters::color_filter(color_matrix, chain, None)
            },
            "sepia" => {
              let amt = 1.0 - value.clamp(0.0, 1.0);
              let color_matrix = color_filters::matrix_row_major(&[
                (0.393 + 0.607 * amt), (0.769 - 0.769 * amt), (0.189 - 0.189 * amt), 0.0, 0.0,
                (0.349 - 0.349 * amt), (0.686 + 0.314 * amt), (0.168 - 0.168 * amt), 0.0, 0.0,
                (0.272 - 0.272 * amt), (0.534 - 0.534 * amt), (0.131 + 0.869 * amt), 0.0, 0.0,
                 0.0,                   0.0,                   0.0,                  1.0, 0.0
              ], None);
              image_filters::color_filter(color_matrix, chain, None)
            },
            "hue-rotate" => {
              let cos = to_radians(*value).cos();
              let sin = to_radians(*value).sin();
              let color_matrix = color_filters::matrix_row_major(&[
                (0.213 + cos*0.787 - sin*0.213), (0.715 - cos*0.715 - sin*0.715), (0.072 - cos*0.072 + sin*0.928), 0.0, 0.0,
                (0.213 - cos*0.213 + sin*0.143), (0.715 + cos*0.285 + sin*0.140), (0.072 - cos*0.072 - sin*0.283), 0.0, 0.0,
                (0.213 - cos*0.213 - sin*0.787), (0.715 - cos*0.715 + sin*0.715), (0.072 + cos*0.928 + sin*0.072), 0.0, 0.0,
                 0.0,                             0.0,                             0.0,                            1.0, 0.0
              ], None);
              image_filters::color_filter(color_matrix, chain, None)
            },
            _ => chain
          }
        }
      );

      let filters = Some(LastFilter{matrix, mask:mask_filter, image:image_filter});
      if raster{ self._raster = filters.clone(); }
      else{ self._vector = filters.clone(); }
      filters
    }).expect("Could not create filter")
  }
}

#[derive(Copy, Clone)]
pub enum FilterQuality{
  None, Low, Medium, High
}

#[derive(Copy, Clone)]
pub struct ImageFilter {
  pub smoothing: bool,
  pub quality: FilterQuality
}

impl ImageFilter {
  /// Return original Skia sampling options for smoothing and quality (unitless enums).
  /// No allocation, validation errors, ownership transfer or GPU-context access.
  /// Upstream: src/filter.rs:213-221 (v3.0.8), unchanged body.
  pub fn sampling(&self) -> SamplingOptions {
    let quality = if self.smoothing { self.quality } else { FilterQuality::None };
    match quality {
      FilterQuality::None   => SamplingOptions::new(FilterMode::Nearest, MipmapMode::None),
      FilterQuality::Low    => SamplingOptions::new(FilterMode::Linear,  MipmapMode::Nearest),
      FilterQuality::Medium => SamplingOptions::new(FilterMode::Linear,  MipmapMode::Linear),
      FilterQuality::High   => SamplingOptions::new(FilterMode::Linear,  MipmapMode::Linear)
    }
  }

}

pub mod arguments;
