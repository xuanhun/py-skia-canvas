//! Original Canvas construction option validation, separated from language fields.
use super::Canvas;
use skia_safe::SurfaceProps;
pub enum OptionsError<E>{Range(String),Field(E)}
pub trait CanvasArgs{
    type Error;
    /// Optional original finite f64 conversion, unitless contrast/gamma, no native refs.
    fn number(&mut self,key:&str)->Option<f64>;
    /// Original bool field/error, no units or native refs; evaluated after range checks.
    fn flag(&mut self)->Result<bool,Self::Error>;
}
/// Validate and construct original Canvas (default 300x150 canvas units).
/// f64 contrast/gamma, GPU bool; returns original Canvas/range or reader error.
/// Original max-gamma equality adjustment and contrast-vs-max-gamma condition preserved.
/// Owner caller retains Canvas, no Send/Sync or GPU/context creation added.
/// Source canvas.rs:new v3.0.8; exact argument validation after typed field reads.
pub fn construct<A:CanvasArgs>(args:&mut A)->Result<Canvas,OptionsError<A::Error>>{
  let text_contrast = args.number("textContrast").unwrap_or(0.0);
  let (min_c, max_c) = (SurfaceProps::MIN_CONTRAST_INCLUSIVE as _, SurfaceProps::MAX_CONTRAST_INCLUSIVE as _);
  if text_contrast < min_c || text_contrast > max_c{
    return Err(OptionsError::Range(format!("Expected a number between {} and {} for `textContrast`", min_c, max_c)))
  }

  let mut text_gamma = args.number("textGamma").unwrap_or(1.4);
  let (min_g, max_g) = (SurfaceProps::MIN_GAMMA_INCLUSIVE as _, SurfaceProps::MAX_GAMMA_EXCLUSIVE as _);
  if text_gamma == max_g{ text_gamma -= f32::EPSILON as f64 }; // nudge down values right at the max
  if text_gamma < min_g || text_contrast > max_g{
    return Err(OptionsError::Range(format!("Expected a number between {} and {} for `textGamma`", min_g, max_g)))
  }

  let gpu_enabled = args.flag().map_err(OptionsError::Field)?;
  Ok(Canvas::new(text_contrast as f64, text_gamma as f64, !gpu_enabled))
}
