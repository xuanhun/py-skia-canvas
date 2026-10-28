#![allow(non_snake_case)]
use crate::context::page::{ExportOptions};
use crate::gpu;


pub struct Canvas{
  pub width: f32,
  pub height: f32,
  pub text_contrast: f64,
  pub text_gamma: f64,
  pub gpu_disabled: bool,
  pub engine: Option<gpu::RenderingEngine>,
}

impl Canvas{
  /// Construct original Canvas/Context/typesetter/style key from typed inputs; preserve default dimensions, style/font selection and operation order. Dimensions/coordinates are canvas units unless documented as pixels.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/canvas.rs:23, skia-canvas 3.0.8; original rendering body retained.
  pub fn new(text_contrast:f64, text_gamma:f64, gpu_disabled:bool) -> Self{
    Canvas{width:300.0, height:150.0, text_contrast, text_gamma, gpu_disabled, engine:None}
  }

  /// Lazily choose original automatic backend and return its enum; manually-disabled flag remains separate as upstream. No context ownership transfer or new error mapping.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/canvas.rs:27, skia-canvas 3.0.8; original rendering body retained.
  pub fn engine(&mut self) -> gpu::RenderingEngine{
    self.engine.get_or_insert_with(||
      gpu::RenderingEngine::default()
    ).clone()
  }

  /// Return original owned export options carrying f64-to-f32 text contrast/gamma at the original conversion point; no new validation or error.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/canvas.rs:33, skia-canvas 3.0.8; original rendering body retained.
  pub fn export_options(&self) -> ExportOptions{
    ExportOptions{text_contrast:self.text_contrast as _, text_gamma:self.text_gamma as _, ..Default::default()}
  }
}


pub mod exports;
pub mod options;
pub mod construction;
