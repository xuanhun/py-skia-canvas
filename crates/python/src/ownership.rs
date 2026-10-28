//! Python handles carry IDs only. Native Canvas/Context/Path2D/Gradient values never leave owner TLS.
//! Python may finalize on any thread: foreign drops enqueue IDs, not Skia objects.
use std::{cell::RefCell, collections::{HashMap,HashSet}, sync::{Arc, Mutex, OnceLock, atomic::{AtomicU64, AtomicUsize, Ordering}}, thread::{self, ThreadId}};
use canvas_core::{canvas::Canvas, context::Context2D, gpu::RenderingEngine, path::Path2D, gradient::CanvasGradient, image::Image, pattern::CanvasPattern, texture::CanvasTexture};
use pyo3::{prelude::*, exceptions::{PyRuntimeError, PyOverflowError}};

static NEXT_ID: AtomicU64 = AtomicU64::new(1);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PAGES: AtomicUsize = AtomicUsize::new(0);
enum DropRequest { Resource(u64), Page(u64,u64) }
type Pending = HashMap<ThreadId, Vec<DropRequest>>;
static PENDING: OnceLock<Mutex<Pending>> = OnceLock::new();

pub struct Entry {
    pub canvas: Canvas,
    pub context: Option<Context2D>,
    contexts:HashMap<u64,Context2D>,
    active_page:Option<u64>,
    latest_page:Option<u64>,
    next_page:u64,
    public_pages:HashSet<u64>,
}

impl Entry {
    /// Lazily create/reset the original context in canvas units; returns an owner-only borrow.
    /// No Python callbacks/errors. Upstream: context/api.rs:new; lib/classes/canvas.js:getContext.
pub fn context(&mut self) -> &mut Context2D {
        if self.context.is_none(){self.insert_page().expect("Implicit page ID exhausted");}
        self.context.as_mut().unwrap()
    }

    /// Own original Canvas and an empty owner-local page table; dimensions canvas units.
    /// Binding metadata only, no policy/errors/native object transfer. Source canvas.js #contexts.
    fn new(canvas:Canvas)->Self{Self{canvas,context:None,contexts:HashMap::new(),active_page:None,latest_page:None,next_page:0,public_pages:HashSet::new()}}

    /// Create original Context2D at current Canvas size, retain older pages on same owner.
    /// Returns metadata ID/OverflowError, no GPU object crosses a thread. Source newPage/API new.
    fn insert_page(&mut self)->PyResult<u64>{
        let id=self.next_page;self.next_page=id.checked_add(1).ok_or_else(||PyOverflowError::new_err("Canvas page IDs exhausted"))?;
        if let (Some(old),Some(context))=(self.active_page.take(),self.context.take()){self.contexts.insert(old,context);}
        let mut context=Context2D::new();context.reset_size((self.canvas.width,self.canvas.height));
        self.context=Some(context);self.active_page=Some(id);self.latest_page=Some(id);self.public_pages.insert(id);PAGES.fetch_add(1,Ordering::SeqCst);Ok(id)
    }

    /// Construct independent original Context at current Canvas dimensions, without
    /// joining public pages or changing current head. Canvas units; ID/OverflowError.
    /// Only binding metadata changes; source context.js:constructor/context/api.rs:new.
    fn insert_detached(&mut self)->PyResult<u64>{
        let id=self.next_page;self.next_page=id.checked_add(1).ok_or_else(||PyOverflowError::new_err("Canvas page IDs exhausted"))?;
        let mut context=Context2D::new();context.reset_size((self.canvas.width,self.canvas.height));
        self.contexts.insert(id,context);PAGES.fetch_add(1,Ordering::SeqCst);Ok(id)
    }

    /// Select fixed context or current head before a typed native operation. Moves are
    /// confined to the same owner TLS; no cloning/rendering or GPU context transfer.
    /// Unitless ID, None/RuntimeError; source canvas.js newest getContext/chronological pages.
    fn activate(&mut self,page:Option<u64>)->PyResult<()>{
        if let Some(target)=page.or(self.latest_page){
            if self.active_page!=Some(target){
                let selected=self.contexts.remove(&target).ok_or_else(||PyRuntimeError::new_err("Canvas page owner has released its resources"))?;
                if let (Some(old),Some(context))=(self.active_page.take(),self.context.take()){self.contexts.insert(old,context);}
                self.context=Some(selected);self.active_page=Some(target);
            }
        }else if let (Some(old),Some(context))=(self.active_page.take(),self.context.take()){
            self.contexts.insert(old,context);
        }Ok(())
    }

    /// Release one independently owned page on owner, unitless ID, no callbacks/errors.
    /// Original Context/recorder/cache drop in place. Root Canvas metadata can outlive pages.
    fn remove_page(&mut self,page:u64){
        let removed=if self.active_page==Some(page){self.active_page=None;self.context.take().is_some()}else{self.contexts.remove(&page).is_some()};
        if removed{PAGES.fetch_sub(1,Ordering::SeqCst);}
        self.public_pages.remove(&page);
        if self.latest_page==Some(page){self.latest_page=self.public_pages.iter().copied().max();}
    }}

impl Drop for Entry {
    /// Drop all remaining original contexts on owner; counters are diagnostic counts only.
    /// Binding lifetime accounting, no callbacks or context transfer, no new render policy.
    fn drop(&mut self){PAGES.fetch_sub(self.contexts.len()+usize::from(self.context.is_some()),Ordering::SeqCst);}
}

#[derive(Default)]
struct Registry { entries: HashMap<u64, Entry>, paths: HashMap<u64, Path2D>, gradients:HashMap<u64,CanvasGradient>, images:HashMap<u64,Image>, patterns:HashMap<u64,CanvasPattern>, textures:HashMap<u64,CanvasTexture> }

impl Registry {
    /// Drop all owned objects on their creating thread; no Python calls or GPU transfers.
    /// Binding ownership plumbing, not an upstream rendering function; no units/errors.
    fn clear(&mut self) {
        LIVE.fetch_sub(self.entries.len()+self.paths.len()+self.gradients.len()+self.images.len()+self.patterns.len()+self.textures.len(), Ordering::SeqCst);
        self.entries.clear();
        self.paths.clear();
        self.gradients.clear();
        self.images.clear();
        self.patterns.clear();
        self.textures.clear();
    }

    /// Remove one uniquely identified Canvas/Path2D/Gradient on its owner; plain ID input, no units/return.
    /// No Python callbacks, GPU/context transfer or new error policy; binding ownership only.
    fn remove(&mut self, id:u64) {
        if self.entries.remove(&id).is_some() || self.paths.remove(&id).is_some() || self.gradients.remove(&id).is_some() || self.images.remove(&id).is_some() || self.patterns.remove(&id).is_some() || self.textures.remove(&id).is_some() {
            LIVE.fetch_sub(1, Ordering::SeqCst);
        }
    }
}

impl Drop for Registry {
    /// Final owner cleanup, including metadata bucket removal; owner TLS only, no Python calls.
    fn drop(&mut self) {
        self.clear();
        pending().remove(&thread::current().id());
    }
}

struct GpuCleanup;
impl Drop for GpuCleanup {
    /// Registered after original GPU TLS initialization, so resources drop before its context.
    /// Binding-only owner cleanup; errors cannot invoke Python during TLS destruction.
    fn drop(&mut self) {
        let _ = REGISTRY.try_with(|registry| registry.borrow_mut().clear());
    }
}

thread_local! {
    static REGISTRY: RefCell<Registry> = RefCell::new(Registry::default());
    static GPU_CLEANUP: GpuCleanup = const { GpuCleanup };
}

/// Borrow ID-only deferred-drop metadata; poison recovery never touches native values.
/// No units, Python calls or rendering policy. Binding ownership implementation.
fn pending() -> std::sync::MutexGuard<'static, Pending> {
    PENDING.get_or_init(|| Mutex::new(HashMap::new())).lock().unwrap_or_else(|e| e.into_inner())
}

/// Drain foreign-thread finalizers on the current owner, returning local/global live counts.
/// Plain counts have no units; no Python callbacks. Must run outside a registry borrow.
pub fn drain() -> (usize, usize) {
    let ids = pending().get_mut(&thread::current().id()).map(std::mem::take).unwrap_or_default();
    let local = REGISTRY.with(|registry| {
        let mut registry = registry.borrow_mut();
        for id in ids {
            match id {DropRequest::Resource(id)=>registry.remove(id),DropRequest::Page(id,page)=>{if let Some(entry)=registry.entries.get_mut(&id){entry.remove_page(page);}}}
        }
        registry.entries.len()+registry.paths.len()+registry.gradients.len()+registry.images.len()+registry.patterns.len()+registry.textures.len()
    });
    (local, LIVE.load(Ordering::SeqCst))
}

/// Drop original resources on the live creating Windows Python thread, followed
/// by its original Vulkan context, before OS loader-lock TLS destructors run.
/// Unitless, idempotent; old ID handles subsequently raise owner-resource errors.
/// No native object crosses a thread and no Python callback runs during clear.
#[cfg(target_os = "windows")]
pub fn release_current_thread() {
    REGISTRY.with(|registry| registry.borrow_mut().clear());
    pending().remove(&thread::current().id());
    canvas_core::gpu::release_current_thread();
}

/// Initialize the original owner-thread DirectContext before registering cleanup TLS.
/// Uses upstream RenderingEngine::with_direct_context without transferring or replacing it.
/// No units/return; call before any GPU-producing readback/export, including error paths.
pub fn arm_gpu_cleanup(engine: RenderingEngine) {
    if matches!(engine, RenderingEngine::GPU) {
        engine.with_direct_context(|_| ());
        GPU_CLEANUP.with(|_| ());
    }
}

#[pyclass(frozen, module = "py_skia_canvas._native")]
pub struct NativeCanvas { owner:ThreadId,id:u64,life:Arc<ResourceLease>,page:Option<Arc<PageLease>> }
struct ResourceLease { owner:ThreadId,id:u64 }
struct PageLease { owner:ThreadId,id:u64,page:u64,_root:Arc<ResourceLease> }

#[pyclass(frozen, module = "py_skia_canvas._native")]
pub struct NativePath { handle: NativeCanvas }

#[pyclass(frozen, module = "py_skia_canvas._native")]
pub struct NativeGradient { handle:NativeCanvas }

impl NativeCanvas {
    /// Register owned original Canvas on this thread; dimensions are canvas units.
    /// Returns a transferable ID handle; ID exhaustion raises OverflowError, native data stays TLS.
    pub fn create(canvas: Canvas) -> PyResult<Self> {
        Self::register(|registry,id| { registry.entries.insert(id, Entry::new(canvas)); })
    }

    /// Create a fixed-page ID-only handle sharing the root metadata lease; original
    /// Context remains owner TLS and drops independently of sibling wrappers. Unitless
    /// ID, returns handle/owner/overflow error. Source Canvas.newPage and weak parent contract.
    pub fn new_page(&self)->PyResult<Self>{
        let page=self.with_registry("Canvas",|r|r.entries.get_mut(&self.id).ok_or_else(||PyRuntimeError::new_err("Canvas owner has released its resources"))?.insert_page())?;
        Ok(Self{owner:self.owner,id:self.id,life:self.life.clone(),page:Some(Arc::new(PageLease{owner:self.owner,id:self.id,page,_root:self.life.clone()}))})
    }

    /// Create independently leased original Context not in Canvas.pages; no native values
    /// leave owner TLS. Returns metadata handle/owner/ID errors. Source public Context ctor.
    pub fn detached_context(&self)->PyResult<Self>{
        let page=self.with_registry("Canvas",|r|r.entries.get_mut(&self.id).ok_or_else(||PyRuntimeError::new_err("Canvas owner has released its resources"))?.insert_detached())?;
        Ok(Self{owner:self.owner,id:self.id,life:self.life.clone(),page:Some(Arc::new(PageLease{owner:self.owner,id:self.id,page,_root:self.life.clone()}))})
    }

    /// Register an owned resource through an owner-local closure; returns only an ID handle.
    /// No units/Skia transfer; ID exhaustion raises OverflowError. Shared binding lifetime policy.
    fn register(insert:impl FnOnce(&mut Registry,u64)) -> PyResult<Self> {
        drain();
        let owner = thread::current().id();
        let id = NEXT_ID.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |id| id.checked_add(1))
            .map_err(|_| PyOverflowError::new_err("Canvas resource IDs exhausted"))?;
        pending().entry(owner).or_default();
        REGISTRY.with(|registry| insert(&mut registry.borrow_mut(),id));
        LIVE.fetch_add(1, Ordering::SeqCst);
        Ok(Self { owner,id,life:Arc::new(ResourceLease{owner,id}),page:None })
    }

    /// Run Rust-only work on the owner; borrowed native values cannot escape this callback.
    /// Raises RuntimeError for foreign access or released owner. No Python callbacks while borrowed.
    pub fn with<T>(&self, operation: impl FnOnce(&mut Entry) -> PyResult<T>) -> PyResult<T> {
        self.with_registry("Canvas", |registry| {
            let entry=registry.entries.get_mut(&self.id).ok_or_else(|| PyRuntimeError::new_err("Canvas owner has released its resources"))?;
            entry.activate(self.page.as_ref().map(|p|p.page))?;
            operation(entry)
        })
    }

    /// Enforce one owner/borrow policy for all owner-local resource types; returns Rust-owned results only.
    /// No units/Python callbacks; foreign or overlapping access raises RuntimeError.
    fn with_registry<T>(&self, name:&str, operation:impl FnOnce(&mut Registry)->PyResult<T>) -> PyResult<T> {
        if thread::current().id() != self.owner {
            return Err(PyRuntimeError::new_err(format!("{name} must be used on its creating thread")));
        }
        drain();
        REGISTRY.with(|registry| {
            let mut registry = registry.try_borrow_mut().map_err(|_| PyRuntimeError::new_err("Canvas resource is already in use"))?;
            operation(&mut registry)
        })
    }
}

impl NativePath {
    /// Register original owned Path2D on this thread; returns metadata-only Python handle.
    /// Canvas-unit path retained; ID exhaustion raises OverflowError. No Send/Sync assertions.
    pub fn create(path:Path2D) -> PyResult<Self> {
        Ok(Self { handle:NativeCanvas::register(|registry,id| { registry.paths.insert(id,path); })? })
    }

    /// Borrow an original path on its owner; returns Rust-owned values, no Python callbacks.
    /// Foreign/ended/overlapping access raises RuntimeError; geometry remains in core.
    pub fn with<T>(&self, operation:impl FnOnce(&mut Path2D)->PyResult<T>) -> PyResult<T> {
        self.handle.with_registry("Path2D", |registry| {
            let path=registry.paths.get_mut(&self.handle.id).ok_or_else(|| PyRuntimeError::new_err("Path2D owner has released its resources"))?;
            operation(path)
        })
    }

    /// Clone the original Skia path reference on its owner for same-thread use only.
    /// Canvas-unit geometry, returns owned COW path; owner errors propagate. Source: path.rs:from_path.
    pub fn snapshot(&self) -> PyResult<skia_safe::Path> { self.with(|p| Ok(p.path.clone())) }
}

impl NativeGradient {
    /// Register original shared ramp in owner TLS; geometry in canvas units, ID only in Python.
    /// Returns handle or ID exhaustion error, no Send/Sync assertions. Source: gradient.rs factories.
    pub fn create(gradient:CanvasGradient) -> PyResult<Self> {
        Ok(Self { handle:NativeCanvas::register(|registry,id| { registry.gradients.insert(id,gradient); })? })
    }

    /// Borrow original ramp on owner; returns Rust-owned results, no Python callbacks.
    /// Foreign/ended/overlapping use ->RuntimeError. Shared binding lifetime/ID policy only.
    pub fn with<T>(&self, operation:impl FnOnce(&mut CanvasGradient)->PyResult<T>) -> PyResult<T> {
        self.handle.with_registry("CanvasGradient", |registry| {
            let gradient=registry.gradients.get_mut(&self.handle.id).ok_or_else(|| PyRuntimeError::new_err("CanvasGradient owner has released its resources"))?;
            operation(gradient)
        })
    }

    /// Clone original Rc ramp reference for same-thread State storage; no stop copy or GPU move.
    /// Returns original CanvasGradient clone, owner errors propagate. Source: context/mod.rs:Dye::new.
    pub fn snapshot(&self) -> PyResult<CanvasGradient> { self.with(|g| Ok(g.clone())) }
}

impl Drop for ResourceLease {
    /// Release immediately on owner, otherwise queue only the ID if owner is still alive.
    /// Python GC may call this on any thread; GPU/Context values never enter this object or queue.
    fn drop(&mut self) {
        if thread::current().id() == self.owner {
            let removed = REGISTRY.try_with(|registry| {
                registry.try_borrow_mut().ok().map(|mut registry| {
                    registry.remove(self.id);
                }).is_some()
            }).unwrap_or(false);
            if removed { return; }
        }
        if let Some(ids) = pending().get_mut(&self.owner) { ids.push(DropRequest::Resource(self.id)); }
    }
}

#[pyclass(frozen,module="py_skia_canvas._native")]
pub struct NativeImage { handle:NativeCanvas }
impl NativeImage {
    /// Register original owned Image in owner TLS; Python carries only IDs.
    /// Units inherited from resource (canvas/pixel), returns handle/ID exhaustion error.
    /// No GPU transfer or Send/Sync; binding ownership, original resource implementation.
    pub fn create(value:Image)->PyResult<Self>{Ok(Self{handle:NativeCanvas::register(|r,id|{r.images.insert(id,value);})?})}
    /// Borrow resource only on its creator; original units, owned result only.
    /// Foreign/ended/reentrant access ->RuntimeError; no Python callbacks under borrow.
    pub fn with<T>(&self,op:impl FnOnce(&mut Image)->PyResult<T>)->PyResult<T>{
        self.handle.with_registry("Image",|r|{
            let value=r.images.get_mut(&self.handle.id).ok_or_else(||PyRuntimeError::new_err("Image owner has released its resources"))?;
            op(value)
        })
    }
}

#[pyclass(frozen,module="py_skia_canvas._native")]
pub struct NativePattern { handle:NativeCanvas }
impl NativePattern {
    /// Register original owned CanvasPattern in owner TLS; Python carries only IDs.
    /// Units inherited from resource (canvas/pixel), returns handle/ID exhaustion error.
    /// No GPU transfer or Send/Sync; binding ownership, original resource implementation.
    pub fn create(value:CanvasPattern)->PyResult<Self>{Ok(Self{handle:NativeCanvas::register(|r,id|{r.patterns.insert(id,value);})?})}
    /// Borrow resource only on its creator; original units, owned result only.
    /// Foreign/ended/reentrant access ->RuntimeError; no Python callbacks under borrow.
    pub fn with<T>(&self,op:impl FnOnce(&mut CanvasPattern)->PyResult<T>)->PyResult<T>{
        self.handle.with_registry("CanvasPattern",|r|{
            let value=r.patterns.get_mut(&self.handle.id).ok_or_else(||PyRuntimeError::new_err("CanvasPattern owner has released its resources"))?;
            op(value)
        })
    }
}

#[pyclass(frozen,module="py_skia_canvas._native")]
pub struct NativeTexture { handle:NativeCanvas }
impl NativeTexture {
    /// Register original owned CanvasTexture in owner TLS; Python carries only IDs.
    /// Units inherited from resource (canvas/pixel), returns handle/ID exhaustion error.
    /// No GPU transfer or Send/Sync; binding ownership, original resource implementation.
    pub fn create(value:CanvasTexture)->PyResult<Self>{Ok(Self{handle:NativeCanvas::register(|r,id|{r.textures.insert(id,value);})?})}
    /// Borrow resource only on its creator; original units, owned result only.
    /// Foreign/ended/reentrant access ->RuntimeError; no Python callbacks under borrow.
    pub fn with<T>(&self,op:impl FnOnce(&mut CanvasTexture)->PyResult<T>)->PyResult<T>{
        self.handle.with_registry("CanvasTexture",|r|{
            let value=r.textures.get_mut(&self.handle.id).ok_or_else(||PyRuntimeError::new_err("CanvasTexture owner has released its resources"))?;
            op(value)
        })
    }
}

impl Drop for PageLease {
    /// Independent page release; foreign GC queues IDs only, never native Skia values.
    /// Unitless IDs, no callbacks/errors; original page/cache drop occurs on its owner.
    fn drop(&mut self){
        if thread::current().id()==self.owner {
            let removed=REGISTRY.try_with(|r|r.try_borrow_mut().ok().map(|mut r|{if let Some(e)=r.entries.get_mut(&self.id){e.remove_page(self.page);}}).is_some()).unwrap_or(false);
            if removed{return;}
        }
        if let Some(ids)=pending().get_mut(&self.owner){ids.push(DropRequest::Page(self.id,self.page));}
    }
}

/// Actual live original Context count, including independent page releases/owner exit.
/// Diagnostic counts, any thread, no native objects or ownership transfer.
pub fn page_count()->usize{PAGES.load(Ordering::SeqCst)}
