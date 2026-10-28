"""Mechanical image decode/layout/blit extraction descriptions; source tooling only.

All substitutions below remove language object reads/returns/borrow syntax. They do
not change SVG sizing, sampling, image selection, crop arithmetic or drawing policy.
"""

def definitions(image,api,bodies):
    """Return original/typed source fragments, canvas/pixel units; raises on source drift.

    Owned source text only, no native objects or thread work. Source image.rs:set_data,
    pixels; context/api.rs:_layout_rects/drawImage/drawCanvas/putImageData v3.0.8.
    """
    decode=bodies(image,'set_data')[0]['body'];decode=decode[decode.index('  if let Some(raw_info)'):decode.index('  Ok(cx.boolean')]
    typed=decode.replace('opt_image_info_arg(&mut cx, 2)?','raw_info').replace('this.','self.')
    layout=bodies(api,'_layout_rects')[0]['body'].replace('cx.throw_type_error(', 'Err(ImageError::Type(').replace('nums.len()))?', 'nums.len())))?').replace('cx.throw_range_error(', 'Err(ImageError::Range(').replace('intrinsic.height)),','intrinsic.height))),')
    draw=bodies(api,'drawImage')[0]['body'];draw=draw[draw.index('  if let Content::Bitmap'):draw.rindex('  Ok(cx.undefined())')]
    typed_draw=draw.replace('_layout_rects(&mut cx,','layout_rects(').replace('    let image = source.downcast::<BoxedImage, _>(&mut cx).unwrap();\n    let fit_to_canvas = image.borrow().autosized;','    let fit_to_canvas = autosized;').replace('this.borrow().bounds','this.bounds').replace('    let mut this = this.borrow_mut();\n','')
    vector=bodies(api,'drawCanvas')[0]['body'];vector=vector[vector.index('  if let Content::Vector'):vector.rfind('\n}')]
    typed_vector=vector.replace('_layout_rects(&mut cx,','layout_rects(').replace('this.borrow_mut().draw_picture','this.draw_picture').replace('Ok(cx.undefined())','Ok(())').replace('cx.throw_error(', 'Err(ImageError::Error(').replace('generate an image")','generate an image".to_string()))')
    put=bodies(api,'putImageData')[0]['body'];put=put[put.index('  let (src, dst)'):put.rindex('  Ok(cx.undefined())')]
    return dict(decode=decode,typedDecode=typed,layout=layout,draw=draw,typedDraw=typed_draw,vector=vector,typedVector=typed_vector,put=put)

def core_loading(image,api,bodies):
    """Generate original Image value/decode source; bytes/pixel dimensions, owner only.

    Text generator returns UTF-8 source; rejects drift via definitions. No runtime I/O.
    Original Image default/body retained; src visibility changes only for adapters.
    """
    d=definitions(image,api,bodies)
    struct=image[image.index('pub struct Image{'):image.index('\nimpl Default for Image')].replace('  src:String','  pub src:String')
    default=bodies(image,'default')[0]['text']
    return '''//! Original image.rs Image/decode, separated from Neon. All Skia objects owner-local.
use super::Content;
use crate::font_library::FontLibrary;
use skia_safe::{Data,ImageInfo,Rect,PictureRecorder,image::images,svg::{self,Length,LengthUnit}};
'''+struct+'\nimpl Default for Image{\n'+default+'\n}\nimpl Image{\n'+'''
/// Decode owned encoded/raw bytes using original bitmap->SVG order and sticky autosized flag.
/// raw_info dimensions pixels, content dimensions canvas units. Returns drawable bool;
/// invalid bytes store Broken, no synthesized image/errors. Fonts/Skia stay owner thread.
/// Source src/image.rs:set_data, v3.0.8; only Js buffer/info reads and return removed.
pub fn decode(&mut self,data:Data,raw_info:Option<ImageInfo>) -> bool {
'''+d['typedDecode']+'  self.content.is_drawable()\n}\n}\n'

def core_operations(image,api,bodies):
    """Generate original layout/draw/blit fragments; typed errors replace Neon exceptions.

    Params/returns documented on generated functions; source text only, raises on drift.
    """
    d=definitions(image,api,bodies)
    header='''//! Original context/api.rs image operations. No language objects or matching policy.
#![allow(non_snake_case)]
use skia_safe::{Size,Rect,Matrix};
use crate::{context::Context2D,image::{Content,ImageData}};
#[derive(Debug)]
pub enum ImageError { Type(String), Range(String), Error(String) }
'''
    doc='''/// Original image operation; positions/size f32 canvas units, source pixels for bitmaps.
/// Typed owned input, returns original layout/unit or typed original arity/dimension error.
/// Owner thread only; no callbacks, GPU transfer or Send/Sync. Source context/api.rs v3.0.8.
'''
    return header+doc+'pub fn layout_rects(intrinsic:Size,nums:&[f32])->Result<(Rect,Rect),ImageError> '+d['layout']+'\n'+doc+'pub fn drawImage(this:&mut Context2D,content:Content,autosized:bool,nums:&[f32])->Result<(),ImageError> {\n'+d['typedDraw']+'  Ok(())\n}\n'+doc+'pub fn drawCanvas(this:&mut Context2D,content:Content,nums:&[f32])->Result<(),ImageError> {\n'+d['typedVector']+'\n}\n'+doc+'pub fn putImageData(this:&mut Context2D,img_data:ImageData,x:f32,y:f32,mut dirty:Vec<f32>) {\n'+d['put']+'}\n'

def node_loading(current,image,api,bodies):
    """Forward Node to unique core Image/decode; preserve pre-read order and original errors.

    Returns owned Node source; Resource wrapper implements Neon ownership only. No runtime.
    """
    current=current.replace('pub type BoxedImage = JsBox<RefCell<Image>>;\nimpl Finalize for Image {}','use crate::resource::Resource;\npub use canvas_core::image::Image;\npub type BoxedImage = JsBox<RefCell<Resource<Image>>>;')
    start=current.index('pub struct Image{');end=current.index('pub use canvas_core::image::',start)
    current=current[:start]+current[end:]
    current=current.replace('RefCell::new(Image::default())','RefCell::new(Resource(Image::default()))')
    body=bodies(current,'set_data')[0]['body'];d=definitions(image,api,bodies)
    current=current.replace(body,body.replace(d['decode'],'  let raw_info = opt_image_info_arg(&mut cx, 2)?;\n  this.decode(data, raw_info);\n\n'))
    return current

def node_operations(current,image,api,bodies):
    """Forward only original draw/layout/blit blocks to typed core, preserving Node readers.

    Returns owned source; no native work. Source drift raises from definitions/bodies.
    """
    d=definitions(image,api,bodies)
    body=bodies(current,'_layout_rects')[0]['body']
    errors='''
fn image_error<'a,T>(cx:&mut FunctionContext<'a>,error:canvas_core::image::operations::ImageError)->NeonResult<T> {
  match error {
    canvas_core::image::operations::ImageError::Type(e)=>cx.throw_type_error(e),
    canvas_core::image::operations::ImageError::Range(e)=>cx.throw_range_error(e),
    canvas_core::image::operations::ImageError::Error(e)=>cx.throw_error(e),
  }
}
'''
    current=current.replace(body,'{\n  canvas_core::image::operations::layout_rects(intrinsic, nums).or_else(|e| image_error(cx,e))\n}').replace('\npub fn drawImage(',errors+'\npub fn drawImage(',1)
    current=current.replace(d['draw'],'''  let autosized=source.downcast::<BoxedImage,_>(&mut cx).ok().map(|i|i.borrow().autosized).unwrap_or(false);
  let result=canvas_core::image::operations::drawImage(&mut this.borrow_mut(),content,autosized,&nums);
  result.or_else(|e|image_error(&mut cx,e))?;
''')
    current=current.replace(d['vector'],'''  canvas_core::image::operations::drawCanvas(&mut this.borrow_mut(),content,&nums).or_else(|e|image_error(&mut cx,e))?;
  Ok(cx.undefined())''')
    current=current.replace(d['put'],'  canvas_core::image::operations::putImageData(&mut this,img_data,x,y,dirty);\n')
    return current
