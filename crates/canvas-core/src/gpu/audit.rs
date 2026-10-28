//! Private owner-local native Vulkan surface evidence, never a backend selection policy.
use std::cell::RefCell;
use serde_json::{json,Value};
thread_local! {static ALLOCATIONS:RefCell<Option<Vec<[i32;2]>>>=const{RefCell::new(None)};}
/// Enable/end diagnostic native surface recording, returns owned dimensions/counts.
/// Pixel units, owner TLS only, no GPU/native object transfer. Original Vulkan surface
/// success path invokes allocated; CPU path never invokes it. No render decisions change.
pub fn capture(enabled:bool)->Value{ALLOCATIONS.with(|r|if enabled{*r.borrow_mut()=Some(Vec::new());json!(null)}else{let sizes=r.borrow_mut().take().unwrap_or_default();json!({"surfaces":sizes.len(),"sizes":sizes})})}
/// Record an actual non-null Skia Vulkan render_target result, pixel dimensions only.
/// Owner thread, no errors/return/native references; no-op outside explicit diagnostics.
pub fn allocated(width:i32,height:i32){ALLOCATIONS.with(|r|{if let Some(v)=r.borrow_mut().as_mut(){v.push([width,height]);}});}
