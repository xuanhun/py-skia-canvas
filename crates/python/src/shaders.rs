//! Thin same-thread Pattern/Texture bindings; original shared core Rc/State semantics.
use pyo3::{prelude::*,exceptions::PyTypeError};
use skia_safe::{Matrix,Color};
use canvas_core::{pattern::CanvasPattern,texture::CanvasTexture,image::Content,context::Dye,utils};
use crate::{ownership::{NativeCanvas,NativeImage,NativePattern,NativeTexture,NativePath},imagery::data};

/// Original repetition enum reader, unitless ->tile modes/TypeError, owner-independent.
/// Source utils.rs:to_repeat_mode; no image/shader policy is duplicated.
fn repeat(value:&str)->PyResult<(skia_safe::TileMode,skia_safe::TileMode)>{utils::to_repeat_mode(value).ok_or_else(||PyTypeError::new_err("Expected `repetition` to be \"repeat\", \"repeat-x\", \"repeat-y\", or \"no-repeat\""))}

#[pymethods]
impl NativePattern {
    /// Create core pattern from image snapshot and target dimensions, all canvas units.
    /// Returns ID/original repetition/owner errors; source pattern.rs:from_image.
    /// Original SVG autosize and cloned content remain solely in CanvasPattern.
    #[staticmethod]
    fn image(image:&NativeImage,width:f32,height:f32,repetition:&str)->PyResult<Self>{
        let rep=repeat(repetition)?;
        let value=image.with(|i|Ok(CanvasPattern::from_image(i.content.clone(),i.content.size(),i.autosized,width,height,rep)))?;
        Self::create(value)
    }
    /// Snapshot original Canvas as vector pattern, canvas units; returns ID/owner errors.
    /// No GPU move; source pattern.rs:from_canvas and original Context2D::get_picture.
    #[staticmethod]
    fn canvas(canvas:&NativeCanvas,repetition:&str)->PyResult<Self>{
        let rep=repeat(repetition)?;
        let value=canvas.with(|e|{let ctx=e.context();let dims=ctx.bounds.size();let content=ctx.get_picture().map(|p|Content::Vector(p,dims)).unwrap_or_default();Ok(CanvasPattern::from_canvas(content,dims,rep,Matrix::new_identity()))})?;
        Self::create(value)
    }
    /// Copy owned ImageData bytes into original pattern, source dimensions pixels.
    /// Returns ID/owner/repetition errors; source pattern.rs:from_image_data.
    #[staticmethod]
    fn pixels(bytes:&[u8],width:f32,height:f32,color_type:&str,color_space:&str,repetition:&str)->PyResult<Self>{
        Self::create(CanvasPattern::from_image_data(data(bytes,width,height,color_type,color_space),repeat(repetition)?))
    }
    /// Replace shared stamp transform with original Skia matrix, unitless/canvas translation.
    /// Returns None/TypeError/owner errors; source pattern.rs:setTransform, no GPU transfer.
    fn transform(&self,values:Vec<f32>)->PyResult<()> {
        let m=utils::to_matrix(&values).ok_or_else(||PyTypeError::new_err("Expected a 3×3 matrix"))?;
        self.with(|p|{p.set_transform(m);Ok(())})
    }
    /// Assign original shared pattern to owner State; None/owner errors, no units.
    /// Rc remains owner-local; source Context Dye::new and fill/strokeStyle.
    fn apply(&self,canvas:&NativeCanvas,stroke:bool)->PyResult<()> {
        let p=self.with(|p|Ok(p.clone()))?;
        canvas.with(|e|{let c=e.context();if stroke{c.state.stroke_style=Dye::Pattern(p)}else{c.state.fill_style=Dye::Pattern(p)}Ok(())})
    }
    /// Original owned representation, unitless, owner errors; source pattern.rs:repr.
    fn kind(&self)->PyResult<String>{self.with(|p|Ok(p.repr()))}
}

#[pymethods]
impl NativeTexture {
    /// Create original texture; spacing/offset/line canvas units, angle radians.
    /// Owned path clone same thread, color original parser fallback BLACK, cap original
    /// validation. Returns ID/TypeError/owner errors; source texture.rs:new, no algorithms here.
    #[new]
    #[pyo3(signature=(path,color,line,cap,angle,outline,spacing,offset))]
    fn new(path:Option<&NativePath>,color:Option<&str>,line:f32,cap:&str,angle:f32,outline:bool,spacing:(f32,f32),offset:(f32,f32))->PyResult<Self>{
        let path=path.map(|p|p.snapshot()).transpose()?;
        let color=color.and_then(utils::css_to_color).unwrap_or(Color::BLACK);
        let cap=utils::to_stroke_cap(cap).ok_or_else(||PyTypeError::new_err("Expected \"butt\", \"square\", or \"round\" for `cap`"))?;
        Self::create(CanvasTexture::new(path,color,line,cap,angle,outline,spacing,offset))
    }
    /// Assign original Rc texture to same-owner State; unitless, None/owner errors.
    /// Source Context Dye::new/set_fillStyle/set_strokeStyle, no native values escape Python.
    fn apply(&self,canvas:&NativeCanvas,stroke:bool)->PyResult<()> {
        let p=self.with(|p|Ok(p.clone()))?;
        canvas.with(|e|{let c=e.context();if stroke{c.state.stroke_style=Dye::Texture(p)}else{c.state.fill_style=Dye::Texture(p)}Ok(())})
    }
    /// Original owned style label, owner errors; source texture.rs:repr, no units.
    fn kind(&self)->PyResult<String>{self.with(|p|Ok(p.repr().to_string()))}
}
