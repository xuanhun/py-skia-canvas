//! Initial synchronous Python adapter. Rendering/layout remain in canvas-core.
//! Native methods accept typed values only; complete JS coercion/CSS/API coverage is pending.
#[cfg(not(any(target_os = "linux", target_os = "windows", target_os = "macos")))]
compile_error!("Python binding GPU features are not configured for this target");
use canvas_core::{context::Dye, font_library::FontLibrary, gpu::RenderingEngine, utils::{css_to_color, color_to_css_string}};
use pyo3::{prelude::*, exceptions::{PyRuntimeError, PyNotImplementedError, PyTypeError}, types::PyBytes};
mod dom_math;
use skia_safe::{PaintStyle, Path, Rect};
use serde_json::json;
mod ownership;
mod path;
mod gradient;
mod projection;
mod font_library;
mod font;
mod decoration;
mod imagery;
mod shaders;
mod effects;
mod exports;
mod gui;
mod arguments;
use canvas_core::context::effects as effect_ops;
use imagery::{data,error};
use canvas_core::image::{Content,operations};
use ownership::{NativeCanvas, NativePath, NativeGradient, NativeImage, NativePattern, NativeTexture, arm_gpu_cleanup};
use canvas_core::context::operations as ops;
use canvas_core::{context::text_state as text_ops,typography::Spacing};
use canvas_core::utils;
pyo3::create_exception!(_native, RangeError, pyo3::exceptions::PyValueError);
pyo3::create_exception!(_native, Error, pyo3::exceptions::PyRuntimeError);

#[pymethods]
impl NativeCanvas {
    /// Private same-Paragraph draw observation toggle, owner TLS only; JSON owned values.
    /// No units/native transfer; actual layout hook records UTF16 ranges/fonts/positions.
    /// Source original draw_text ->Typesetter::layout, diagnostics do not replace drawing.
    fn audit_draw_capture(&self,enabled:bool)->PyResult<String>{self.with(|_|Ok(canvas_core::typography::audit::capture(enabled).to_string()))}
    /// Private native Vulkan render_target success counter, pixel sizes/owned JSON.
    /// Owner only; actual CPU controls stay zero, no backend/format/device changes.
    /// Source original VulkanContext::surface, result-only diagnostic tap.
    fn audit_surface_capture(&self,enabled:bool)->PyResult<String>{self.with(|_|Ok(canvas_core::gpu::audit::capture(enabled).to_string()))}
    /// Independent original Context handle at Canvas size, canvas units, owner/ID errors.
    /// Does not add to public pages or replace head; source context.js constructor.
    fn context_handle(&self)->PyResult<Self>{self.detached_context()}
    /// Original context bounds in canvas units, owned f32 pair; owner errors propagate.
    /// Source context/api.rs:get_size, used by Window.page; no GPU object transfer.
    fn context_size(&self)->PyResult<(f32,f32)>{self.with(|e|{let s=e.context().bounds.size();Ok((s.width,s.height))})}

    /// Store original global Canvas dimensions without resetting head; logical canvas units.
    /// Original Window.page/resize bypass public resetting setters; owner only, None/errors.
    /// Source gui.js:page setter/resize dispatch and canvas.rs:set_width/set_height.
    fn gui_canvas_size(&self,width:f32,height:f32)->PyResult<()>{self.with(|e|{e.canvas.width=width;e.canvas.height=height;Ok(())})}

    /// Resize original selected context without clearing contents; canvas units, None/errors.
    /// Source context/api.rs:set_size ->Context2D::resize, owner TLS only.
    fn gui_context_size(&self,width:f32,height:f32)->PyResult<()>{self.with(|e|{e.context().resize((width,height));Ok(())})}
    /// New fixed page handle, canvas-unit dimensions inherited; owner/ID errors propagate.
    /// Original Context remains owner TLS; source canvas.js:newPage/context/api.rs:new.
    fn page_handle(&self)->PyResult<Self>{self.new_page()}

    /// Original selected-page synchronous export; bytes/None and original Error.
    /// Options JSON primitives, path native units, padding digits; owner-only snapshot.
    /// Source canvas.rs:toBufferSync/saveSync; dispatch implemented once in core.
    #[pyo3(signature=(pages,options,file=None,padding=-1.0,sequence=false))]
    fn export_sync<'py>(&self,py:Python<'py>,pages:Vec<PyRef<'_,NativeCanvas>>,options:&str,file:Option<String>,padding:f32,sequence:bool)->PyResult<Option<Bound<'py,PyBytes>>>{exports::synchronous(self,py,pages,options,file,padding,sequence)}

    /// Start original Rayon job now; owner materializes original snapshot before transfer.
    /// Returns awaitable's channel-only task/owner/type errors, parameters as export_sync.
    /// Source canvas.rs:toBuffer/save; no live GPU Context crosses threads.
    #[pyo3(signature=(pages,options,file=None,padding=-1.0,sequence=false))]
    fn export_start(&self,pages:Vec<PyRef<'_,NativeCanvas>>,options:&str,file:Option<String>,padding:f32,sequence:bool)->PyResult<exports::NativeExportTask>{exports::start(self,pages,options,file,padding,sequence)}
    /// Create original Canvas; units are canvas units, contrast/gamma are original numeric settings.
    /// Raises ID exhaustion; owns no Skia data itself. Source: canvas.rs:new and JS Canvas constructor.
    #[new]
    fn new(width: f32, height: f32, text_contrast: &Bound<'_,PyAny>, text_gamma: &Bound<'_,PyAny>, gpu_disabled: bool) -> PyResult<Self> {
        let mut canvas = canvas_core::canvas::construction::construct(&mut arguments::CanvasFields{contrast:text_contrast,gamma:text_gamma,gpu:!gpu_disabled}).map_err(arguments::error)?;
        canvas.width = width;
        canvas.height = height;
        Self::create(canvas)
    }

    /// Return original width/height in canvas units; owner access required, no GPU allocation.
    fn size(&self) -> PyResult<(f32, f32)> { self.with(|e| Ok((e.canvas.width, e.canvas.height))) }

    /// Store typed dimensions and reset existing context as original Canvas setters do.
    /// Canvas units; returns None, owner errors propagate. Source: JS Canvas width/height setters.
    fn set_size(&self, width: f32, height: f32) -> PyResult<()> {
        self.with(|e| {
            e.canvas.width = width;
            e.canvas.height = height;
            if let Some(context) = &mut e.context { context.reset_size((width, height)); }
            Ok(())
        })
    }

    /// Ensure original first context exists; owner-only, no units/return or substitute renderer.
    fn ensure_context(&self) -> PyResult<()> { self.with(|e| { e.context(); Ok(()) }) }

    /// Return selected original engine flag and status JSON, preserving constructor gpu:false quirk.
    /// No units; owner errors propagate. Source: canvas.rs:get_engine/get_engine_status.
    fn engine(&self) -> PyResult<(bool, String)> {
        self.with(|e| {
            let engine = e.canvas.engine();
            let mut status = engine.status(e.canvas.gpu_disabled);
            status["textContrast"] = json!(e.canvas.text_contrast);
            status["textGamma"] = json!(e.canvas.text_gamma);
            Ok((matches!(engine, RenderingEngine::GPU), status.to_string()))
        })
    }

    /// Apply original explicit engine setter/selectability rule; unitless bool, returns None.
    /// Owner only; unavailable GPU request preserves previous engine. Source: canvas.rs:set_engine.
    fn set_gpu(&self, enabled: bool) -> PyResult<()> {
        self.with(|e| {
            let engine = if enabled { RenderingEngine::GPU } else { RenderingEngine::CPU };
            if engine.selectable() {
                e.canvas.gpu_disabled = matches!(engine, RenderingEngine::CPU);
                e.canvas.engine = Some(engine);
            }
            Ok(())
        })
    }

    /// Dispatch original reset/push/pop state operations; returns None, unknown operations fail.
    /// Canvas units are inherited; no Python callbacks or thread transfer. Source: context/api.rs.
    fn state(&self, operation: &str) -> PyResult<()> {
        self.with(|e| {
            let context = e.context();
            match operation {
                "save" => context.push(), "restore" => context.pop(),
                "reset" => { let size = context.bounds.size(); context.reset_size(size); }
                _ => return Err(PyNotImplementedError::new_err(operation.to_string())),
            }
            Ok(())
        })
    }

    /// Get/set original solid fill/stroke CSS color using shared parser/formatter.
    /// Unitless CSS string; invalid string is ignored as upstream. Owner-only; returns current CSS.
    #[pyo3(signature = (stroke, value=None))]
    fn color(&self, stroke: bool, value: Option<&str>) -> PyResult<Option<String>> {
        self.with(|e| {
            let context = e.context();
            let dye = if stroke { &mut context.state.stroke_style } else { &mut context.state.fill_style };
            if let Some(color) = value.and_then(css_to_color) { *dye = Dye::Color(color); }
            match dye {
                Dye::Color(color) => Ok(Some(color_to_css_string(color))),
                _ => Ok(None), // Original JS shader-reference flag; facade owns the cached Python ref.
            }
        })
    }

    /// Assign original shared gradient clone to fill/stroke State; no units/return.
    /// Both resource owners checked before mutation; no ramp copy or context transfer.
    /// Source: context/mod.rs:Dye::new and context/api.rs:set_fillStyle/set_strokeStyle.
    fn gradient_style(&self, stroke:bool, gradient:&NativeGradient) -> PyResult<()> {
        let gradient=gradient.snapshot()?;
        self.with(|e| {
            let c=e.context();
            if stroke { c.state.stroke_style=Dye::Gradient(gradient); }
            else { c.state.fill_style=Dye::Gradient(gradient); }
            Ok(())
        })
    }

    /// Get/set original global alpha in [0,1]; invalid numeric range ignored, returns f32 value.
    /// Unitless; owner-only. Source: context/api.rs:get_globalAlpha/set_globalAlpha.
    #[pyo3(signature = (value=None))]
    fn alpha(&self, value: Option<f32>) -> PyResult<f32> {
        self.with(|e| {
            let context=e.context();
            if let Some(value)=value{effect_ops::set_globalAlpha(context,value);}
            Ok(effect_ops::get_globalAlpha(context))
        })
    }

    /// Draw original rect path or clear rect; coordinates/sizes are f32 canvas units.
    /// Returns None, owner errors propagate. Source: context/api.rs:fillRect/strokeRect/clearRect.
    fn rect(&self, kind: &str, x: f32, y: f32, width: f32, height: f32) -> PyResult<()> {
        self.with(|e| {
            let rect = Rect::from_xywh(x, y, width, height);
            let context = e.context();
            match kind {
                "clear" => context.clear_rect(&rect),
                "fill" | "stroke" => context.draw_path(Some(Path::rect(rect, None)), if kind == "fill" { PaintStyle::Fill } else { PaintStyle::Stroke }, None),
                _ => return Err(PyNotImplementedError::new_err(kind.to_string())),
            }
            Ok(())
        })
    }

    /// Apply original current-path operations using shared typed functions; f32 canvas units/radians.
    /// Vectors have fixed original method arity, ccw is unitless. Returns None; radius errors ->
    /// RangeError (ValueError subclass). Owner-only, no Python callbacks/Skia ownership transfer.
    /// Upstream: context/api.rs beginPath..closePath, mechanically shared in context/operations.rs.
    fn path_command(&self, kind: &str, mut values: Vec<f32>, ccw: bool) -> PyResult<()> {
        let arity = match kind {
            "beginPath" | "closePath" => 0, "moveTo" | "lineTo" => 2,
            "rect" | "quadraticCurveTo" => 4, "arc" | "arcTo" | "conicCurveTo" => 5,
            "bezierCurveTo" => 6, "ellipse" => 7, "roundRect" => 12,
            _ => return Err(PyNotImplementedError::new_err(kind.to_string())),
        };
        if values.len() != arity { return Err(PyTypeError::new_err("Invalid internal path argument count")); }
        self.with(|e| {
            let context = e.context();
            match kind {
                "beginPath" => ops::beginPath(context), "closePath" => ops::closePath(context),
                "moveTo" => ops::moveTo(context, values), "lineTo" => ops::lineTo(context, values),
                "rect" => ops::rect(context, values), "arc" => ops::arc(context, values, ccw),
                "roundRect" => ops::roundRect(context, values),
                "ellipse" => ops::ellipse(context, values, ccw).map_err(RangeError::new_err)?,
                "arcTo" => { let radius = values.pop().unwrap(); ops::arcTo(context, values, radius).map_err(RangeError::new_err)?; }
                "bezierCurveTo" => ops::bezierCurveTo(context, values),
                "quadraticCurveTo" => ops::quadraticCurveTo(context, values),
                "conicCurveTo" => ops::conicCurveTo(context, values),
                _ => unreachable!(),
            }
            Ok(())
        })
    }

    /// Snapshot original current matrix in Skia's row order; 9 owned f32 values,
    /// unitless coefficients/canvas-unit translation. Owner-only, RuntimeError if foreign.
    /// Source: context/api.rs:get_currentTransform original state.matrix[0..9] allocation loop.
    fn current_matrix(&self) -> PyResult<Vec<f32>> {
        self.with(|e| Ok((0..9).map(|i| e.context().state.matrix[i]).collect()))
    }

    /// Original owner-only projection; flattened primitive inputs in canvas units,
    /// returns 9 owned f32 terms or original TypeError. No state mutation/GPU move.
    /// Source: context/api.rs:createProjection; implementation stays in sole core.
    fn projection(&self,quad:&Bound<'_,PyAny>,basis:&Bound<'_,PyAny>) -> PyResult<Vec<f32>> {
        projection::projection(self,quad,basis)
    }

    /// Apply original transform/translate/scale/rotate/reset operations; f32 canvas units/radians.
    /// Matrix vector is original Skia row order, returns None; internal arity ->TypeError.
    /// Owner-only; upstream context/api.rs transforms, shared core keeps exact multiplication order.
    fn matrix(&self, kind: &str, values: Vec<f32>) -> PyResult<()> {
        // Original opt_matrix_arg accepts filtered lists of 6/9 terms, otherwise None.
        let arity = match kind { "set" | "transform" => values.len(), "translate" | "scale" => 2, "rotate" => 1, "reset" => 0, _ => return Err(PyNotImplementedError::new_err(kind.to_string())) };
        if values.len() != arity { return Err(PyTypeError::new_err("Invalid internal transform argument count")); }
        self.with(|e| {
            let context = e.context();
            match kind {
                "set" => ops::set_currentTransform(context, utils::to_matrix(&values)),
                "transform" => ops::transform(context, utils::to_matrix(&values)),
                "translate" => ops::translate(context, values), "scale" => ops::scale(context, values),
                "rotate" => ops::rotate(context, values[0]), "reset" => ops::resetTransform(context),
                _ => unreachable!(),
            }
            Ok(())
        })
    }

    /// Fill/stroke/clip original current path; rule strings are unitless, returns None.
    /// Invalid fill rules -> original TypeError message. Owner-only, no path/GPU transfer.
    /// Upstream: context/api.rs fill/clip/stroke and shared Context2D draw_path/clip_path.
    #[pyo3(signature = (kind, rule, path=None))]
    fn use_path(&self, kind: &str, rule: String, path:Option<PyRef<'_,NativePath>>) -> PyResult<()> {
        let explicit=path.is_some();
        let target=path.as_ref().map(|p| p.snapshot()).transpose()?;
        self.with(|e| {
            let context = e.context();
            if kind == "stroke" { context.draw_path(target, PaintStyle::Stroke, None); return Ok(()); }
            let error = format!("Expected `fillRule` to be \"nonzero\" or \"evenodd\" for {} arg", if explicit { "2nd" } else { "1st" });
            let rule = utils::fill_rule(&rule, &error).map_err(PyTypeError::new_err)?;
            match kind {
                "fill" => context.draw_path(target, PaintStyle::Fill, Some(rule)),
                "clip" => context.clip_path(target, rule),
                _ => return Err(PyNotImplementedError::new_err(kind.to_string())),
            }
            Ok(())
        })
    }

    /// Test original current-path fill/stroke hit at f32 canvas-unit coordinates; returns bool.
    /// Rule errors -> original TypeError, owner-only. Source: context/api.rs:_is_in; core handles
    /// inverse matrix, temporary fill type and original stroke precision, without adapter geometry.
    #[pyo3(signature = (x, y, stroke, rule, path=None))]
    fn hit_path(&self, x: f32, y: f32, stroke: bool, rule: String, path:Option<PyRef<'_,NativePath>>) -> PyResult<bool> {
        let explicit=path.is_some();
        let target=path.as_ref().map(|p| p.snapshot()).transpose()?;
        self.with(|e| {
            let context = e.context();
            let mut path = target.unwrap_or_else(|| context.path.clone());
            let rule = if stroke { None } else {
                let error = format!("Expected `fillRule` to be \"nonzero\" or \"evenodd\" for {} arg", if explicit { "4th" } else { "3rd" });
                Some(utils::fill_rule(&rule, &error).map_err(PyTypeError::new_err)?)
            };
            Ok(context.hit_test_path(&mut path, (x,y), rule, if stroke { PaintStyle::Stroke } else { PaintStyle::Fill }))
        })
    }

    /// Get/set original width/miter/dash offset; width/offset in canvas units, miter unitless.
    /// Returns f32 getter; invalid nonpositive width/miter ignored by shared core. Owner-only.
    /// Source: context/api.rs line style setters/getters; no GPU ownership transfer.
    #[pyo3(signature = (name, value=None))]
    fn stroke_number(&self, name: &str, value: Option<f32>) -> PyResult<f32> {
        self.with(|e| {
            let c = e.context();
            match name {
                "lineWidth" => { ops::set_lineWidth(c, value); Ok(c.state.paint.stroke_width()) }
                "miterLimit" => { ops::set_miterLimit(c, value); Ok(c.state.paint.stroke_miter()) }
                "lineDashOffset" => { if let Some(v)=value { ops::set_lineDashOffset(c,v); } Ok(c.state.line_dash_offset) }
                _ => Err(PyNotImplementedError::new_err(name.to_string())),
            }
        })
    }

    /// Get/set original cap/join style; unitless strings, returns canonical original name.
    /// Unknown names ignored; owner-only, no GPU transfer. Source: context/api.rs lineCap/lineJoin.
    #[pyo3(signature = (name, value=None))]
    fn stroke_name(&self, name: &str, value: Option<&str>) -> PyResult<String> {
        self.with(|e| {
            let c=e.context();
            match name {
                "lineCap" => { if let Some(v)=value { ops::set_lineCap(c,v); } Ok(utils::from_stroke_cap(c.state.paint.stroke_cap())) }
                "lineJoin" => { if let Some(v)=value { ops::set_lineJoin(c,v); } Ok(utils::from_stroke_join(c.state.paint.stroke_join())) }
                _ => Err(PyNotImplementedError::new_err(name.to_string())),
            }
        })
    }

    /// Get/set original line-dash intervals in canvas units; returns an owned f32 list.
    /// Original filtering/odd duplication/all-or-nothing update stay in core. Owner-only;
    /// vector extraction errors are Python TypeError. Source: context/api.rs set/getLineDash.
    #[pyo3(signature = (value=None))]
    fn line_dash(&self, value: Option<Vec<f32>>) -> PyResult<Vec<f32>> {
        self.with(|e| {
            let c=e.context();
            if let Some(values)=value { let length=values.len(); ops::setLineDash(c,values,length); }
            Ok(c.state.line_dash_list.clone())
        })
    }

    /// Return original text outline as owner-local Path2D; max width in canvas units.
    /// Owner errors propagate, no font/layout rewrite or GPU transfer. Source: API outlineText.
    #[pyo3(signature = (text, width=None))]
    fn outline(&self, text:&str, width:Option<f32>) -> PyResult<NativePath> {
        let _operation=canvas_core::typography::audit::operation("outlineText");
        let path=self.with(|e| Ok(e.context().outline_text(text,width)))?;
        NativePath::create(canvas_core::path::Path2D { path })
    }

    /// Get/set original dash marker; owner-only copied path, canvas-unit geometry.
    /// assign=true with no path clears marker; returns new path handle/None, ownership errors
    /// propagate. Source: API set_lineDashMarker/get_lineDashMarker, no path strategy changes.
    #[pyo3(signature = (assign=false, path=None))]
    fn marker(&self, assign:bool, path:Option<PyRef<'_,NativePath>>) -> PyResult<Option<NativePath>> {
        let target=path.as_ref().map(|p| p.snapshot()).transpose()?;
        let marker=self.with(|e| {
            if assign { e.context().state.line_dash_marker=target; return Ok(None); }
            Ok(e.context().state.line_dash_marker.clone())
        })?;
        marker.map(|path| NativePath::create(canvas_core::path::Path2D { path })).transpose()
    }

    /// Get/set original align/baseline/direction/stretch label, no coordinate units.
    /// None is getter/ignored invalid parsed stretch, return owned canonical string.
    /// Owner RuntimeError/unknown private name error; no callbacks or native transfer.
    /// Upstream context/api.rs:get/set textAlign/textBaseline/direction/fontStretch.
    #[pyo3(signature=(name,value=None))]
    fn text_name(&self,name:&str,value:Option<String>) -> PyResult<String> {
        self.with(|e| {
            let c=e.context();
            Ok(match name {
                "textAlign"=>{if let Some(v)=value{text_ops::set_textAlign(c,v)}text_ops::get_textAlign(c)},
                "textBaseline"=>{if let Some(v)=value{text_ops::set_textBaseline(c,v)}text_ops::get_textBaseline(c)},
                "direction"=>{if let Some(v)=value{text_ops::set_direction(c,v)}text_ops::get_direction(c).to_string()},
                "fontStretch"=>{if let Some(v)=value{text_ops::set_fontStretch(c,v)}text_ops::get_fontStretch(c)},
                _=>return Err(PyNotImplementedError::new_err(name.to_string())),
            })
        })
    }

    /// Get/set original fontHinting/textWrap boolean; unitless, returns bool.
    /// Caller supplies JS !! conversion, owner-only/no native transfer, unknown private
    /// names error. Source context/api.rs:get/set_fontHinting/get/set_textWrap.
    #[pyo3(signature=(name,value=None))]
    fn text_flag(&self,name:&str,value:Option<bool>) -> PyResult<bool> {
        self.with(|e| {
            let c=e.context();
            Ok(match name {
                "fontHinting"=>{if let Some(v)=value{text_ops::set_fontHinting(c,v)}text_ops::get_fontHinting(c)},
                "textWrap"=>{if let Some(v)=value{text_ops::set_textWrap(c,v)}text_ops::get_textWrap(c)},
                _=>return Err(PyNotImplementedError::new_err(name.to_string())),
            })
        })
    }

    /// Get/set original letter/word Spacing from original raw/unit/px f32 fields.
    /// Returns original Rust spacing string, units CSS/canvas px or raw suffix.
    /// Native fonts/GPU remain owner TLS; no callback during borrow. Private malformed
    /// arguments ->TypeError, owner errors propagate. Source typography.rs:Spacing and
    /// context/api.rs:get/set_letterSpacing/wordSpacing, same current-em-size operation.
    #[pyo3(signature=(name,raw=None,unit=None,px=None))]
    fn text_spacing(&self,name:&str,raw:Option<f32>,unit:Option<String>,px:Option<f32>) -> PyResult<String> {
        let spacing=match (raw,unit,px){
            (None,None,None)=>None,
            (Some(raw),Some(unit),Some(px))=>Spacing::parse(raw,unit,px),
            _=>return Err(PyTypeError::new_err("Invalid internal parsed spacing")),
        };
        self.with(|e| {
            let c=e.context();
            Ok(match name {
                "letterSpacing"=>{text_ops::set_letterSpacing(c,spacing);text_ops::get_letterSpacing(c)},
                "wordSpacing"=>{text_ops::set_wordSpacing(c,spacing);text_ops::get_wordSpacing(c)},
                _=>return Err(PyNotImplementedError::new_err(name.to_string())),
            })
        })
    }

    /// Get/set original fontVariant string plus feature JSON (unitless tags/i32 values).
    /// Returns owned current variant. Parsed fields/JSON decode before owner borrow,
    /// no callbacks or font/GPU transfer. Errors owner RuntimeError/private TypeError.
    /// Upstream context/api.rs:get/set_fontVariant, typography.rs:font_features.
    #[pyo3(signature=(value=None,features=None))]
    fn text_variant(&self,value:Option<String>,features:Option<&str>) -> PyResult<String> {
        let features=features.map(|s| {
            let d=serde_json::from_str(s).map_err(|_|PyTypeError::new_err("Invalid internal parsed variant"))?;
            font::features(&d)
        }).transpose()?;
        self.with(|e| {
            let c=e.context();
            if let (Some(value),Some(features))=(value,features){text_ops::set_fontVariant(c,value,features);}
            Ok(text_ops::get_fontVariant(c))
        })
    }

    /// Get/set original decoration through shared lazy argument reader and state operation.
    /// Descriptor strings/features unitless, thickness original CSS/canvas units; returns
    /// owned original CSS string. Owner/field TypeErrors propagate; parse before Context
    /// borrow, no callbacks or font/GPU transfer. Source context/api.rs:textDecoration and
    /// typography.rs:decoration_arg. None is getter/ignored invalid parsed style.
    #[pyo3(signature=(descriptor=None))]
    fn text_decoration(&self,descriptor:Option<&str>) -> PyResult<String> {
        let style=descriptor.map(decoration::decode).transpose()?.flatten();
        self.with(|e| {
            let c=e.context();
            if let Some(style)=style{text_ops::set_textDecoration(c,style);}
            Ok(text_ops::get_textDecoration(c))
        })
    }

    /// Get/apply original parsed font on owner Context; JSON fields from original CSS
    /// facade, size/leading CSS px. None is original ignored null/getter, returns canonical
    /// string. Owner RuntimeError/private-descriptor TypeError; no callbacks during borrow.
    /// Upstream: context/api.rs:get_font/set_font, Context2D::set_font unchanged in core.
    #[pyo3(signature=(descriptor=None))]
    fn font(&self,descriptor:Option<&str>) -> PyResult<String> {
        let spec=descriptor.map(font::decode).transpose()?.flatten();
        self.with(|e| {
            let c=e.context();
            if let Some(spec)=spec { c.set_font(spec); }
            Ok(c.state.font.clone())
        })
    }

    /// Draw original selected-font text; x/y/maxWidth are f32 canvas units, width absent is None.
    /// Returns None; owner-only, original shaping/layout. Source: context/api.rs:_draw_text.
    #[pyo3(signature = (text, x, y, stroke, width=None))]
    fn text(&self, text: &str, x: f32, y: f32, stroke: bool, width: Option<f32>) -> PyResult<()> {
        let _operation=canvas_core::typography::audit::operation(if stroke {"strokeText"}else{"fillText"});
        self.with(|e| { e.context().draw_text(text, x, y, width, if stroke { PaintStyle::Stroke } else { PaintStyle::Fill }); Ok(()) })
    }

    /// Return complete original JSON metrics; width is optional f32 canvas units, offsets are UTF-16.
    /// Owner-only; JSON becomes Python values after registry borrow ends. Source: Context2D::measure_text.
    #[pyo3(signature = (text, width=None))]
    fn measure(&self, text: &str, width: Option<f32>) -> PyResult<String> {
        self.with(|e| Ok(e.context().measure_text(text, width).to_string()))
    }

    /// Private diagnostic: original measurement-layout glyph/font observations.
    /// Text UTF-8, width canvas units; returns owned JSON, owner errors propagate.
    /// Temporary table bytes are diagnostic transport only; runners hash/discard,
    /// no borrowed visitor/font/GPU handle escapes. Source typography::audit::glyphs.
    #[pyo3(signature=(text,width=None))]
    fn audit_glyphs(&self,text:&str,width:Option<f32>) -> PyResult<String> {
        self.with(|e|Ok(canvas_core::typography::audit::glyphs(&e.context().state,text,width).to_string()))
    }

    /// Read original unpremultiplied RGBA at density=1 using original floor/negative crop rules.
    /// Input canvas units, output owned bytes copied after owner borrow. Original String errors -> RuntimeError.
    /// Source: context/api.rs:getImageData; export settings expansion remains pending.
    fn pixels<'py>(&self, py: Python<'py>, x: f32, y: f32, width: f32, height: f32) -> PyResult<Bound<'py, PyBytes>> {
        let data = self.with(|e| {
            let (mut x, mut y, mut w, mut h) = (x.floor(), y.floor(), width.floor(), height.floor());
            if w < 0.0 { x += w; w *= -1.0; }
            if h < 0.0 { y += h; h *= -1.0; }
            let crop = Rect::from_point_and_size((x, y), (w, h)).round();
            let engine = e.canvas.engine();
            arm_gpu_cleanup(engine);
            let options = e.canvas.export_options();
            e.context().get_pixels(crop, options, engine).map_err(PyRuntimeError::new_err)
        })?;
        Ok(PyBytes::new(py, &data))
    }

    /// Encode current original page with public default options as PNG/raw owned bytes.
    /// No units; owner-only synchronous export, native errors -> RuntimeError, other bindings remain pending.
    fn encode<'py>(&self, py: Python<'py>, format: &str) -> PyResult<Bound<'py, PyBytes>> {
        if !matches!(format, "png" | "raw") { return Err(PyNotImplementedError::new_err("This initial binding supports synchronous png/raw only")); }
        let data = self.with(|e| {
            let engine = e.canvas.engine();
            arm_gpu_cleanup(engine);
            let mut options = e.canvas.export_options();
            options.format = format.to_string();
            options.outline = false;
            let page = e.context().get_page_for_export(&options, &engine);
            page.encoded_as(options, engine).map_err(PyRuntimeError::new_err)
        })?;
        Ok(PyBytes::new(py, &data))
    }
    /// Draw original bitmap/vector Image with original 2/4/8-coord layout/SVG autosize.
    /// Canvas units, returns None or original typed arity/dimension errors. Both owners
    /// checked; snapshot retained on this thread only. Source API drawImage/shared operations.
    fn draw_image_resource(&self,image:&NativeImage,coords:Vec<f32>)->PyResult<()> {
        let (content,auto)=image.with(|i|Ok((i.content.clone(),i.autosized)))?;
        self.with(|e|operations::drawImage(e.context(),content,auto,&coords).map_err(error))
    }

    /// Draw original same-thread Canvas snapshot, bitmap or drawCanvas vector branch.
    /// Canvas units, returns unit/original errors; snapshot before target borrow supports
    /// self-copy. Source Content::from_context and API drawImage/drawCanvas, no GPU move.
    fn draw_canvas_resource(&self,source:&NativeCanvas,coords:Vec<f32>,vector:bool)->PyResult<()> {
        let content=source.with(|e|{arm_gpu_cleanup(e.canvas.engine());Ok(Content::from_context(e.context(),vector))})?;
        self.with(|e|if vector{operations::drawCanvas(e.context(),content,&coords)}else{operations::drawImage(e.context(),content,false,&coords)}.map_err(error))
    }

    /// Draw/blit copied ImageData using original core; source size pixels, coords canvas units.
    /// dirty empty/full-four as original reader. Returns unit/original errors, owner-only,
    /// owned bytes copied before registry borrow. Source API drawImage/putImageData.
    fn draw_data(&self,bytes:&[u8],width:f32,height:f32,color_type:&str,color_space:&str,coords:Vec<f32>,blit:bool)->PyResult<()> {
        let image=data(bytes,width,height,color_type,color_space);
        self.with(|e|{
            if blit{operations::putImageData(e.context(),image,coords[0],coords[1],coords[2..].to_vec());Ok(())}
            else{operations::drawImage(e.context(),Content::from_image_data(image),false,&coords).map_err(error)}
        })
    }

    /// Original getImageData crop/export settings; width/height and positions canvas units,
    /// density unitless, output owned native color-layout bytes. Floor/negative rules retain
    /// original order. Owner-only; native export error ->Error, no callbacks/GPU transfer.
    /// Source context/api.rs:getImageData and image_data_export_arg.
    fn image_pixels<'py>(&self,py:Python<'py>,x:f32,y:f32,width:f32,height:f32,color_type:&str,color_space:&str,density:f32,matte:Option<&str>,msaa:Option<usize>)->PyResult<Bound<'py,PyBytes>> {
        let bytes=self.with(|e|{
            let (mut x,mut y,mut w,mut h)=(x.floor(),y.floor(),width.floor(),height.floor());
            if w<0.0{x+=w;w*= -1.0;}if h<0.0{y+=h;h*= -1.0;}
            let mut opts=e.canvas.export_options();opts.color_type=utils::to_color_type(color_type);opts.color_space=utils::to_color_space(color_space);opts.density=density;opts.matte=matte.and_then(utils::css_to_color);opts.msaa=msaa;
            let crop=Rect::from_point_and_size((x*density,y*density),(w*density,h*density)).round();
            let engine=e.canvas.engine();arm_gpu_cleanup(engine);
            e.context().get_pixels(crop,opts,engine).map_err(Error::new_err)
        })?;Ok(PyBytes::new(py,&bytes))
    }

    /// Get/set original smoothing flag and quality. Bool/string unitless, owner-only;
    /// invalid quality ignored, returns current values. Source API imageSmoothing*.
    #[pyo3(signature=(enabled=None,quality=None))]
    fn smoothing(&self,enabled:Option<bool>,quality:Option<String>)->PyResult<(bool,String)>{
        self.with(|e|{let f=&mut e.context().state.image_filter;
            if let Some(v)=enabled{f.smoothing=v;}if let Some(v)=quality{if let Some(q)=utils::to_filter_quality(&v){f.quality=q;}}
            Ok((f.smoothing,utils::from_filter_quality(f.quality)))
        })
    }

    /// Get/set original effect number with typed f32 input, canvas units except alpha.
    /// Returns original f32; validation/bail happens in facade before owner borrow.
    /// Owner-only/RuntimeError, no callbacks. Source context/api.rs shadow/globalAlpha.
    #[pyo3(signature=(name,value=None))]
    fn effects_number(&self,name:&str,value:Option<f32>)->PyResult<f32>{self.with(|e|{
        let c=e.context();
        Ok(match name{
            "globalAlpha"=>{if let Some(v)=value{effect_ops::set_globalAlpha(c,v)}effect_ops::get_globalAlpha(c)},
            "shadowBlur"=>{if let Some(v)=value{effect_ops::set_shadowBlur(c,v)}effect_ops::get_shadowBlur(c)},
            "shadowOffsetX"=>{if let Some(v)=value{effect_ops::set_shadowOffsetX(c,v)}effect_ops::get_shadowOffsetX(c)},
            "shadowOffsetY"=>{if let Some(v)=value{effect_ops::set_shadowOffsetY(c,v)}effect_ops::get_shadowOffsetY(c)},
            _=>return Err(PyTypeError::new_err("Unknown internal effect number")),
        })
    })}

    /// Get/set original composite or marker fit enum, string unitless. Returns owned
    /// original canonical name; invalid strings ignored by core, private name/owner errors.
    /// No callbacks/GPU transfers. Source context/api.rs globalCompositeOperation/lineDashFit.
    #[pyo3(signature=(name,value=None))]
    fn effects_name(&self,name:&str,value:Option<String>)->PyResult<String>{self.with(|e|{
        let c=e.context();
        Ok(match name{
            "globalCompositeOperation"=>{if let Some(v)=value{effect_ops::set_globalCompositeOperation(c,v)}effect_ops::get_globalCompositeOperation(c)},
            "lineDashFit"=>{if let Some(v)=value{effect_ops::set_lineDashFit(c,v)}effect_ops::get_lineDashFit(c)},
            _=>return Err(PyTypeError::new_err("Unknown internal effect name")),
        })
    })}

    /// Original shadow CSS color parse/ignore/format; string unitless, owned return.
    /// No color/shadow algorithm here; owner only, errors propagate. Source shadowColor.
    #[pyo3(signature=(value=None))]
    fn effects_color(&self,value:Option<&str>)->PyResult<String>{
        let color=value.and_then(css_to_color);
        self.with(|e|{let c=e.context();effect_ops::set_shadowColor(c,color);Ok(color_to_css_string(&effect_ops::get_shadowColor(c)))})
    }

    /// Read owned original CSS descriptor before borrow, use unique FilterSpec packer
    /// and original canonical equality/cache rule. Returns current CSS; TypeError/owner
    /// errors propagate. No callbacks or filter algorithm duplication. Source filter_arg/set_filter.
    #[pyo3(signature=(descriptor=None))]
    fn effects_filter(&self,descriptor:Option<&str>)->PyResult<String>{
        let parsed=descriptor.map(effects::decode).transpose()?;
        self.with(|e|{let c=e.context();if let Some((text,specs))=parsed{effect_ops::set_filter(c,text,specs);}Ok(effect_ops::get_filter(c))})
    }

}

/// Return original font-family list for development resource verification; owner TLS, no units.
/// Used by the public FontLibrary facade without transferring native fonts. Source: FontLibrary::families.
#[pyfunction]
fn _font_families() -> Vec<String> { FontLibrary::with_shared(|library| library.families()) }

/// Original optional text width: reuse _as_double primitive/array/string conversion,
/// finite f64 filtering then f32 cast, None for ignored invalid/undefined. Units canvas.
/// Stateless, no callbacks/native handles; source utils.rs:_as_float/opt_float_arg.
#[pyfunction]
fn _text_width(value:&Bound<'_,PyAny>) -> Option<f32> { projection::number(value).map(|n|n as f32) }

/// Drain ID finalizers and report (owner live, global live) counts for lifecycle tests only.
/// Does not move GPU objects; count units are resources. No public Canvas API policy.
#[pyfunction]
fn _debug_drain() -> (usize, usize) { ownership::drain() }

/// Windows host thread-exit hook, unitless/idempotent/owner-only, no native moves.
/// Called by a Python threading.local sentinel before DLL TLS teardown.
#[cfg(target_os = "windows")]
#[pyfunction]
fn _release_thread() { ownership::release_current_thread(); }

/// Actual original page count, diagnostic only, any thread, no native references/errors.
#[pyfunction]
fn _debug_pages()->usize{ownership::page_count()}

/// Register real initial native methods; no units/ownership transfer, propagates PyO3 registration errors.
#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    #[cfg(target_os = "windows")]
    module.add_function(wrap_pyfunction!(_release_thread,module)?)?;
    module.add_class::<NativeCanvas>()?;
    module.add_class::<exports::NativeExportTask>()?;
    module.add_function(wrap_pyfunction!(exports::_debug_export_jobs,module)?)?;
    module.add_function(wrap_pyfunction!(_debug_pages,module)?)?;
    module.add_class::<NativePath>()?;
    module.add_class::<NativeGradient>()?;
    module.add_class::<NativeImage>()?;
    module.add_class::<NativePattern>()?;
    module.add_class::<NativeTexture>()?;
    module.add("RangeError", module.py().get_type::<RangeError>())?;
    module.add("Error", module.py().get_type::<Error>())?;
    module.add_function(wrap_pyfunction!(_font_families, module)?)?;
    module.add_function(wrap_pyfunction!(_text_width, module)?)?;
    module.add_function(wrap_pyfunction!(arguments::_argument_double,module)?)?;
    module.add_function(wrap_pyfunction!(_debug_drain, module)?)?;
    module.add_function(wrap_pyfunction!(dom_math::_dom_math, module)?)?;
    module.add_function(wrap_pyfunction!(dom_math::_number_string,module)?)?;
    font_library::register(module)?;
    gui::register(module)?;
    Ok(())
}
