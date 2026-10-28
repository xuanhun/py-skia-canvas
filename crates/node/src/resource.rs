//! Node-only ownership wrapper for core resources; Neon traits never enter canvas-core.
use std::ops::{Deref, DerefMut};
use neon::prelude::*;

/// Own a core value inside the original RefCell/JsBox lifetime on the Node thread.
/// Cloning delegates to T (including its original Rc sharing). No Send/Sync is added.
#[derive(Clone)]
pub struct Resource<T>(pub T);
impl<T: 'static> Finalize for Resource<T> {}

impl<T> Deref for Resource<T> {
    type Target = T;

    /// Borrow the contained value without conversion, allocation, errors or ownership transfer.
    /// Node adapter only; use on the JsBox owner thread. No upstream rendering counterpart.
    fn deref(&self) -> &T { &self.0 }
}

impl<T> DerefMut for Resource<T> {
    /// Mutably borrow the contained value; RefCell borrow checking remains at the call site.
    /// No allocation/ownership transfer; Node owner thread only. Adapter-only operation.
    fn deref_mut(&mut self) -> &mut T { &mut self.0 }
}
