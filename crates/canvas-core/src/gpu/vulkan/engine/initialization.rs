//! Serialize loader/device initialization only; original VulkanContext::new body retained.
use super::VulkanContext;
use std::sync::Mutex;
static INITIALIZATION:Mutex<()>=Mutex::new(());
/// Construct original context on the calling thread, no units or native transfer.
/// Returns original context/String error; lock serializes concurrent library/instance/
/// device function loading only, then releases. Device choice, queues, Skia setup,
/// rendering, idle lifespan and Rayon concurrency are unchanged. No Send/Sync assertions.
/// Source engine.rs:VulkanContext::new, guarded after official A and Python both crashed
/// in concurrent device function loading; evidence 20261028-export-race-diagnosis.
pub(super) fn create()->Result<VulkanContext,String>{
    let _guard=INITIALIZATION.lock().unwrap_or_else(|e|e.into_inner());
    VulkanContext::new()
}
