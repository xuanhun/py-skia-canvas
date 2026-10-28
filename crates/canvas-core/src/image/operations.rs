//! Original context/api.rs image operations. No language objects or matching policy.
#![allow(non_snake_case)]
use skia_safe::{Size,Rect,Matrix};
use crate::{context::Context2D,image::{Content,ImageData}};
#[derive(Debug)]
pub enum ImageError { Type(String), Range(String), Error(String) }
/// Original image operation; positions/size f32 canvas units, source pixels for bitmaps.
/// Typed owned input, returns original layout/unit or typed original arity/dimension error.
/// Owner thread only; no callbacks, GPU transfer or Send/Sync. Source context/api.rs v3.0.8.
pub fn layout_rects(intrinsic:Size,nums:&[f32])->Result<(Rect,Rect),ImageError> {
  let (src, dst) = match nums.len() {
    2 => ( Rect::from_xywh(0.0, 0.0, intrinsic.width, intrinsic.height),
           Rect::from_xywh(nums[0], nums[1], intrinsic.width, intrinsic.height) ),
    4 => ( Rect::from_xywh(0.0, 0.0, intrinsic.width, intrinsic.height),
           Rect::from_xywh(nums[0], nums[1], nums[2], nums[3]) ),
    8 => ( Rect::from_xywh(nums[0], nums[1], nums[2], nums[3]),
           Rect::from_xywh(nums[4], nums[5], nums[6], nums[7]) ),
    9.. => Err(ImageError::Type(format!("⚠️Expected 2, 4, or 8 coordinates (got {})", nums.len())))?,
    _ => Err(ImageError::Type(format!("not enough arguments: Expected 2, 4, or 8 coordinates (got {})", nums.len())))?
  };

  match intrinsic.is_empty(){
    true => Err(ImageError::Range(format!("Dimensions must be non-zero (got {}×{})", intrinsic.width, intrinsic.height))),
    false => Ok((src, dst))
  }
}
/// Original image operation; positions/size f32 canvas units, source pixels for bitmaps.
/// Typed owned input, returns original layout/unit or typed original arity/dimension error.
/// Owner thread only; no callbacks, GPU transfer or Send/Sync. Source context/api.rs v3.0.8.
pub fn drawImage(this:&mut Context2D,content:Content,autosized:bool,nums:&[f32])->Result<(),ImageError> {
  if let Content::Bitmap(img) = &content {
    let bounds_size = content.size();
    let (src, dst) = layout_rects( bounds_size, &nums)?;

    content.snap_rects_to_bounds(src, dst);
    this.draw_image(&img, &src, &dst);
  } else if let Content::Vector(pict, pict_size) = &content {
    let fit_to_canvas = autosized;
    let (mut src, mut dst) = layout_rects( *pict_size, &nums)?;

    // for SVG images with no intrinsic size, use the canvas size as a default scale
    if fit_to_canvas && nums.len() != 4 {
      let canvas_size = this.bounds.size();
      let canvas_min = canvas_size.width.min(canvas_size.height);
      let pict_min = pict_size.width.min(pict_size.height);

      if nums.len() == 2 {
        // if the user doesn't specify a size, proportionally scale to fit within canvas
        let factor = canvas_min / pict_min;
        dst = Rect::from_point_and_size((dst.x(), dst.y()), dst.size() * factor);
      } else if nums.len() == 8 {
        // if clipping out part of the source, map the crop coordinates as if the image is canvas-sized
        let factor = (pict_size.width / canvas_min, pict_size.height / canvas_min);
        (src, _) = Matrix::scale(factor).map_rect(src);
      }
    }

    content.snap_rects_to_bounds(src, dst);
    this.draw_picture(&pict, &src, &dst);
  }

  Ok(())
}
/// Original image operation; positions/size f32 canvas units, source pixels for bitmaps.
/// Typed owned input, returns original layout/unit or typed original arity/dimension error.
/// Owner thread only; no callbacks, GPU transfer or Send/Sync. Source context/api.rs v3.0.8.
pub fn drawCanvas(this:&mut Context2D,content:Content,nums:&[f32])->Result<(),ImageError> {
  if let Content::Vector(pict, size) = &content{
    let (src, dst) = layout_rects( *size, &nums)?;
    let (src, dst) = content.snap_rects_to_bounds(src, dst);
    this.draw_picture(&pict, &src, &dst);
    Ok(())
  }else{
    Err(ImageError::Error("Canvas's PictureRecorder failed to generate an image".to_string()))
  }
}
/// Original image operation; positions/size f32 canvas units, source pixels for bitmaps.
/// Typed owned input, returns original layout/unit or typed original arity/dimension error.
/// Owner thread only; no callbacks, GPU transfer or Send/Sync. Source context/api.rs v3.0.8.
pub fn putImageData(this:&mut Context2D,img_data:ImageData,x:f32,y:f32,mut dirty:Vec<f32>) {
  let (src, dst) = match dirty.as_mut_slice(){
    [dx, dy, dw, dh] => {
      // negative dimensions are valid, just shift the origin and absify
      if *dw < 0.0 { *dw *= -1.0; *dx -= *dw; }
      if *dh < 0.0 { *dh *= -1.0; *dy -= *dh; }
      (Rect::from_xywh(*dx, *dy, *dw, *dh), Rect::from_xywh(*dx + x, *dy + y, *dw, *dh))
    },
    _ => (
      Rect::from_xywh(0.0, 0.0, img_data.width, img_data.height),
      Rect::from_xywh(x, y, img_data.width, img_data.height)
  )};

  this.blit_pixels(img_data, &src, &dst);
}
