//! Original utils.rs:export_options_arg typed field packing only.
use crate::{context::page::ExportOptions,utils::to_color_type};
use skia_safe::{Color,ColorType,ColorSpace};
pub trait ExportArgs {
    type Error;
    /// Owned original string field or original TypeError; no units/native refs.
    fn string(&mut self,name:&str)->Result<String,Self::Error>;
    /// Original bool field or TypeError; no units/native refs.
    fn flag(&mut self,name:&str)->Result<bool,Self::Error>;
    /// Original finite-f64 then f32 field; quality/density/text units, original TypeError.
    fn number(&mut self,name:&str)->Result<f32,Self::Error>;
    /// Original optional float, then core floor/as-usize for MSAA; no field error.
    fn optional_number(&mut self,name:&str)->Option<f32>;
    /// Original optional string field; no units/native objects or errors.
    fn optional_string(&mut self,name:&str)->Option<String>;
    /// Original optional CSS color after language toString; packed color/None, owner local.
    fn color(&mut self,name:&str)->Option<Color>;
}
/// Pack original ExportOptions in the original read order, no callback/render policy.
/// Returns owned options or original field error; f32 conversions stay in language reader.
/// Source utils.rs:export_options_arg v3.0.8; bounds/codec validation stays original core.
pub fn export_options_arg<A:ExportArgs>(args:&mut A)->Result<ExportOptions,A::Error>{
  let format = args.string("format")?;
  let quality = args.number("quality")?;
  let density = args.number("density")?;
  let jpeg_downsample = args.flag("downsample")?;
  let matte = args.color("matte");
  let msaa = args.optional_number("msaa")
    .map(|num| num.floor() as usize);
  let color_type = args.optional_string("colorType")
    .map(|mode| to_color_type(&mode)).unwrap_or(ColorType::RGBA8888);
  let text_contrast = args.number("textContrast")?;
  let text_gamma = args.number("textGamma")?;
  let outline = args.flag("outline")?;

  let color_space = ColorSpace::new_srgb();

  Ok(ExportOptions{
    format, quality, density, outline, matte, msaa, color_type, color_space, jpeg_downsample, text_contrast, text_gamma
  })
}
