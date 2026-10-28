#![allow(clippy::upper_case_acronyms)]
pub mod audit;
/// Release the current Windows Vulkan owner before DLL thread-detach.
/// No arguments/units/errors or transfer; original TLS context destructor only.
/// Host lifetime adaptation, not a replacement rendering or device policy.
#[cfg(all(target_os = "windows", feature = "vulkan"))]
pub fn release_current_thread() { vulkan::engine::VulkanEngine::release_current_thread(); }
use skia_safe::{gpu::DirectContext, ImageInfo, Image, Rect, Matrix, Color, Surface, surfaces};
use serde_json::{json, Value};
use crate::context::page::{Page, ExportOptions};

#[cfg(feature = "metal")]
mod metal;
#[cfg(feature = "metal")]
use crate::gpu::metal::MetalEngine as Engine;
#[cfg(all(feature = "metal", feature = "window"))]
pub use crate::gpu::metal::MetalRenderer as Renderer;


#[cfg(feature = "vulkan")]
mod vulkan;
#[cfg(feature = "vulkan")]
use crate::gpu::vulkan::engine::VulkanEngine as Engine;
#[cfg(all(feature = "vulkan", feature = "window"))]
pub use crate::gpu::vulkan::renderer::VulkanRenderer as Renderer;

#[cfg(not(any(feature = "vulkan", feature = "metal")))]
struct Engine { }
#[cfg(not(any(feature = "vulkan", feature = "metal")))]
impl Engine {
    /// Return original optional backend API label; no inputs or GPU-context transfer, allocation of label retained.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:25, skia-canvas 3.0.8; function body unchanged.
    pub fn api() -> Option<String>{ None }
    /// Return original GPU availability decision based on status/probe; no CPU substitution for a GPU-required test is implied.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:26, skia-canvas 3.0.8; function body unchanged.
    pub fn supported() -> bool { false }
    /// Return original cached backend/device/driver/thread or manually-disabled status JSON; preserves probe and error labels, not a new native trace.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:27, skia-canvas 3.0.8; function body unchanged.
    pub fn status() -> Value { serde_json::json!({
        "renderer": "CPU",
        "api": Value::Null,
        "device": "CPU-based renderer (compiled without GPU support)",
        "error": Value::Null,
    })}
    // placeholders that match the GPU signatures (for the type-checker) but will never be called
    // (see the RenderingEngine methods for their inline implementation when in CPU mode)
    /// Create original surface for ImageInfo pixel dimensions and export options via selected backend; returns Surface or original String error; unavailable compile-time stubs retain original panic.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:35, skia-canvas 3.0.8; function body unchanged.
    pub fn make_surface(_info: &ImageInfo, _opts:&ExportOptions) -> Result<Surface, String>{ panic!() }
    /// Borrow original optional DirectContext inside callback on this thread; returns original unit result/error suppression, no ownership transfer.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:36, skia-canvas 3.0.8; function body unchanged.
    pub fn with_direct_context(_f:impl FnOnce(Option<&mut DirectContext>)){ panic!() }
}

#[derive(Copy, Clone, Debug)]
pub enum RenderingEngine{
    CPU,
    GPU,
}

impl Default for RenderingEngine {
    /// Choose original automatic engine or empty render cache; no inputs, GPU fallback/default policy and field values unchanged.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:46, skia-canvas 3.0.8; function body unchanged.
    fn default() -> Self {
        if Engine::supported() { Self::GPU } else { Self::CPU }
    }
}

#[allow(dead_code)]
impl RenderingEngine{
    /// Return original backend availability for requested CPU/GPU enum; no new validation, allocation or ownership transfer.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:53, skia-canvas 3.0.8; function body unchanged.
    pub fn selectable(&self) -> bool {
        match self {
            Self::GPU => Engine::supported(),
            Self::CPU => true
        }
    }

    /// Create original surface for ImageInfo pixel dimensions and export options via selected backend; returns Surface or original String error; unavailable compile-time stubs retain original panic.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:60, skia-canvas 3.0.8; function body unchanged.
    pub fn make_surface(&self, image_info: &ImageInfo, opts:&ExportOptions) -> Result<Surface, String>{
        match self {
            Self::GPU => Engine::make_surface(image_info, opts),
            Self::CPU => surfaces::raster(image_info, None, Some(&opts.surface_props()))
                .ok_or(format!("Could not allocate new {}×{} bitmap", image_info.width(), image_info.height()))
        }
    }

    /// Borrow original optional DirectContext inside callback on this thread; returns original unit result/error suppression, no ownership transfer.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:68, skia-canvas 3.0.8; function body unchanged.
    pub fn with_direct_context(&self, f:impl FnOnce(Option<&mut DirectContext>)){
        match self {
            Self::GPU => Engine::with_direct_context(f),
            Self::CPU => f(None)
        }
    }

    /// Return original cached backend/device/driver/thread or manually-disabled status JSON; preserves probe and error labels, not a new native trace.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:75, skia-canvas 3.0.8; function body unchanged.
    pub fn status(&self, is_manually_disabled:bool) -> serde_json::Value {
        match is_manually_disabled{
            true => json!({
                "renderer":"CPU",
                "api": Engine::api(),
                "device": "CPU-based renderer (GPU manually disabled)",
                "driver": "N/A",
                "threads": rayon::current_num_threads()
            }),
            false=> Engine::status(),
        }
    }

    /// Return original optional window/GPU failure message; no parameters, preserves source availability policy.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:88, skia-canvas 3.0.8; function body unchanged.
    pub fn lacks_gpu_support(&self) -> Option<String> {
        match Engine::supported(){
            true => None,
            false => {
                let mut msg = vec!["No windowing support".to_string()];
                if let Some(Value::String(error)) = Engine::status().get("error"){
                    msg.push(error.to_string());
                }
                Some(msg.join(": "))
            }
        }
    }
}

#[allow(dead_code)]
pub struct RenderCache {
    image: Option<Image>,
    content: Rect,
    page: Page,
    matte: Color,
    dpr: f32,
    state: RenderState,
}

impl Default for RenderCache{
    /// Choose original automatic engine or empty render cache; no inputs, GPU fallback/default policy and field values unchanged.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:113, skia-canvas 3.0.8; function body unchanged.
    fn default() -> Self {
        Self{image:None, content:Rect::new_empty(), page:Page::default(), dpr:0.0, matte:Color::TRANSPARENT, state:RenderState::Clean}
    }
}

#[allow(dead_code)]
impl RenderCache{
    /// Validate original page/matte/device-pixel-ratio/clip cache, returning borrowed image/source/destination rectangles or None; lengths retain original canvas/pixel conventions.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:120, skia-canvas 3.0.8; function body unchanged.
    pub fn validate(&mut self, page:&Page, matte:Color, dpr:f32, clip:Rect) -> Option<(&Image, &Rect, Rect)>{
        if
            self.state == RenderState::Dirty ||
            self.page.id != page.id ||
            self.matte != matte ||
            self.dpr != dpr
        {
            *self = Self::default();
        }

        self.image.as_ref().map(|img| {
            let (dst, _) = Matrix::scale((dpr, dpr)).map_rect(clip);
            (img, &self.content, dst)
        })
    }

    /// Return original number of cached page layers as usize; no mutation, allocation, units or errors.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:136, skia-canvas 3.0.8; function body unchanged.
    pub fn depth(&self) -> usize {
        self.page.layers.len()
    }

    /// Own original image/page and update cache with matte/dpr/content; preserves resize/dirty policy, original clones and drop ordering.
    /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
    /// Upstream: src/gpu/mod.rs:140, skia-canvas 3.0.8; function body unchanged.
    pub fn update(&mut self, image:Image, page:&Page, matte:Color, dpr:f32, content:Rect){
        if self.state==RenderState::Resizing{
            // mark the framebuffer as needing a full redraw and skip updating cached image during resize
            self.state = RenderState::Dirty;
        }else{
            let state = RenderState::Clean;
            let (content, _) = skia_safe::Matrix::scale((dpr, dpr)).map_rect(content);
            *self = Self{image: Some(image), page:page.clone(), matte, dpr, content, state};
        }
    }
}

#[derive(Debug, PartialEq, Clone, Copy)]
pub enum RenderState{
    Clean,
    Dirty,
    Resizing
}
