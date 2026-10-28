//! Original utils.rs:filter_arg packing; only language field reads abstracted.
use crate::{filter::FilterSpec,utils::css_to_color};
use skia_safe::Point;
pub trait FilterArgs {
    type Error;
    /// Read original canonical string, unitless; owned value or original field error.
    fn canonical(&mut self)->Result<String,Self::Error>;
    /// Read original own filter names/insertion order; owned strings, original field error.
    fn names(&mut self)->Result<Vec<String>,Self::Error>;
    /// Read original array/float filtering/color string in order; f32 CSS/canvas units.
    /// Returns owned values/original field error, never borrowed native objects.
    fn shadow(&mut self,name:&str)->Result<(Vec<f32>,String),Self::Error>;
    /// Read original JsNumber-as-f32; amount/degree/CSS units, original field error.
    fn number(&mut self,name:&str)->Result<f32,Self::Error>;
}
/// Original FilterSpec packing, lazy reader preserves error/field order and color ignore.
/// Returns owned canonical/specs; widths/offsets canvas units, hue degrees, plain amounts
/// unitless. Owner-native objects do not escape; source utils.rs:filter_arg v3.0.8.
pub fn filter_arg<A:FilterArgs>(args:&mut A)->Result<(String,Vec<FilterSpec>),A::Error> {
  let canonical=args.canonical()?;
  let names=args.names()?;
  let mut filters = vec![];
  for name in names {
    match name.as_str() {
      "drop-shadow" => {
        let (dims, color_str) = args.shadow(&name)?;
        if let Some(color) = css_to_color(&color_str) {
          filters.push(FilterSpec::Shadow{
            offset: Point::new(dims[0], dims[1]), blur: dims[2], color
          });
        }
      },
      _ => {
        let value = args.number(&name)?;
        filters.push(FilterSpec::Plain{
          name:name.to_string(), value
        })
      }
    }
  }
  Ok( (canonical, filters) )
}
