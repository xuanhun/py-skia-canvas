//! Original image.rs Image/decode, separated from Neon. All Skia objects owner-local.
use super::Content;
use crate::font_library::FontLibrary;
use skia_safe::{Data,ImageInfo,Rect,PictureRecorder,image::images,svg::{self,Length,LengthUnit}};
pub struct Image{
  pub src:String,
  pub autosized:bool,
  pub content: Content,
}

impl Default for Image{
  fn default() -> Self {
    Image{ content:Content::Loading, autosized:false, src:"".to_string() }
  }

}
impl Image{

/// Decode owned encoded/raw bytes using original bitmap->SVG order and sticky autosized flag.
/// raw_info dimensions pixels, content dimensions canvas units. Returns drawable bool;
/// invalid bytes store Broken, no synthesized image/errors. Fonts/Skia stay owner thread.
/// Source src/image.rs:set_data, v3.0.8; only Js buffer/info reads and return removed.
pub fn decode(&mut self,data:Data,raw_info:Option<ImageInfo>) -> bool {
  if let Some(raw_info) = raw_info{
    // First, check for an optional dims argument and interpret the buffer as raw rgba if present
    self.content = match images::raster_from_data(&raw_info, data, raw_info.min_row_bytes()){
      Some(image) => Content::Bitmap(image),
      None => Content::Broken
    }
  }else if let Some(image) = images::deferred_from_encoded_data(&data, None){
    // Next, try interpreting the data as an encoded bitmap
    self.content = Content::Bitmap(image);
  }else if let Ok(mut dom) = svg::Dom::from_bytes(&data, FontLibrary::with_shared(|lib| lib.font_mgr())){
    // Finally, try parsing as SVG
    let root = dom.root();

    let mut size = root.intrinsic_size();
    if size.is_empty(){
      // flag that image lacks an intrinsic size so it will be drawn to match the canvas size
      // if dimensions aren't provided in the drawImage() call
      self.autosized = true;

      // If width or height attributes aren't defined on the root `<svg>` element, they will be reported as "100%".
      // If only one is defined, use it for both dimensions, and if both are missing use the aspect ratio to scale the
      // width vs a fixed height of 150 (i.e., Chrome's behavior)
      let Length{ value:width, unit:w_unit } = root.width();
      let Length{ value:height, unit:h_unit } = root.height();
      size = match ((width, w_unit), (height, h_unit)){
        // NB: only unitless numeric lengths are currently being handled; values in em, cm, in, etc. are ignored,
        // but perhaps they should be converted to px?
        ((100.0, LengthUnit::Percentage), (height, LengthUnit::Number)) => (*height, *height).into(),
        ((width, LengthUnit::Number),     (100.0,  LengthUnit::Percentage)) => (*width, *width).into(),
        _ => {
          let aspect = root.view_box().map(|vb| vb.width()/vb.height()).unwrap_or(1.0);
          (150.0 * aspect, 150.0).into()
        }
      };
    };

    // Save the SVG contents as a Picture (to be drawn later)
    let bounds = Rect::from_size(size);
    let mut compositor = PictureRecorder::new();
    dom.set_container_size(bounds.size());
    dom.render(compositor.begin_recording(bounds, true));
    self.content = match compositor.finish_recording_as_picture(None){
      Some(picture) => Content::Vector(picture, size),
      None => Content::Broken
    };
  }else{
    self.content = Content::Broken
  }

  self.content.is_drawable()
}
}
