//! Owner-local image decoding/drawing/pixel bridges; sole rendering core, owned bytes only.
use pyo3::{prelude::*,types::PyBytes,exceptions::PyTypeError};
use skia_safe::{Data,ImageInfo,ColorSpace,AlphaType,ColorType,image::CachingHint};
use canvas_core::{image::{Image,Content,ImageData,operations::ImageError},utils};
use crate::{ownership::NativeImage,RangeError,Error};

/// Map original image exceptions after borrow, no units/native transfer. Source API errors.
pub fn error(e:ImageError)->PyErr {match e{ImageError::Type(e)=>PyTypeError::new_err(e),ImageError::Range(e)=>RangeError::new_err(e),ImageError::Error(e)=>Error::new_err(e)}}

/// Own a temporary original ImageData from copied language bytes. Pixel dimensions f32;
/// original color fallback retained. No Python callbacks, owner-local use, no errors.
pub fn data(bytes:&[u8],width:f32,height:f32,color_type:&str,color_space:&str)->ImageData {
    ImageData::new(Data::new_copy(bytes),width,height,color_type.to_string(),color_space.to_string())
}

#[pymethods]
impl NativeImage {
    /// Construct original Loading image in owner TLS; returns ID or exhaustion error.
    /// No units; original image.rs:Image::default. Native fonts/content never enter Python.
    #[new]
    fn new()->PyResult<Self>{Self::create(Image::default())}

    /// Decode encoded bytes or explicit raw RGBA info with original decode order.
    /// Dimensions pixels; returns drawable bool; failed data stores Broken. Owner errors
    /// propagate, no callbacks while borrowed. Source image.rs:set_data, shared Image::decode.
    #[pyo3(signature=(bytes,raw=None))]
    fn decode_bytes(&self,bytes:&[u8],raw:Option<(i32,i32,bool)>)->PyResult<bool>{
        let bytes=Data::new_copy(bytes);
        let info=raw.map(|(w,h,premul)|ImageInfo::new((w,h),ColorType::RGBA8888,if premul{AlphaType::Premul}else{AlphaType::Unpremul},ColorSpace::new_srgb()));
        self.with(|i|Ok(i.decode(bytes,info)))
    }

    /// Return width/height pixels, original complete, owned src; unitless bool/string.
    /// Owner-only, no native refs escape; source image.rs:get_width/height/complete/src.
    fn info(&self)->PyResult<(f32,f32,bool,String)>{self.with(|i|{let s=i.content.size();Ok((s.width,s.height,i.content.is_complete(),i.src.clone()))})}

    /// Set owned source label; returns unit, owner errors only. Source image.rs:set_src.
    fn source(&self,value:String)->PyResult<()> {self.with(|i|{i.src=value;Ok(())})}

    /// Read original bitmap pixels with requested color type; SVG/non-readable ->None.
    /// Returns owned bytes in original Unpremul layout; color space as original pixels
    /// caller default srgb. Owner-only; source image.rs:pixels, no drawing workaround.
    fn pixels<'py>(&self,py:Python<'py>,color_type:&str)->PyResult<Option<Bound<'py,PyBytes>>>{
        let bytes=self.with(|i|{
            let info=ImageInfo::new(i.content.size().to_floor(),utils::to_color_type(color_type),AlphaType::Unpremul,ColorSpace::new_srgb());
            let mut pixels=vec![0u8;info.bytes_per_pixel()*(info.width()*info.height()) as usize];
            match &i.content{Content::Bitmap(image)=>Ok(image.read_pixels(&info,&mut pixels,info.min_row_bytes(),(0,0),CachingHint::Allow).then_some(pixels)),_=>Ok(None)}
        })?;
        Ok(bytes.map(|v|PyBytes::new(py,&v)))
    }
}

