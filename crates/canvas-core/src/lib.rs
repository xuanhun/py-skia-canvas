//! Shared rendering core extracted from skia-canvas 3.0.8, commit
//! 042312a3f40b660b1d7dc0beba541486171bc5cc.
//!
//! Extracted: filters, sampling, gradients, patterns, textures, Content/ImageData,
//! Canvas/Context/State, font library/layout/metrics, original numeric helpers,
//! Page/recording/cache/export, GPU backends, Path2D ellipse primitives and current-path
//! operations, SVG/Path2D boolean/effect/query operations. DOM/parameter adapters remain tracked separately.
//! Python bindings are in crates/python. No Node types/callbacks/runtime are dependencies here.

pub mod filter;
pub mod utils;
pub mod gradient;
pub mod image;
pub mod pattern;
pub mod texture;
pub mod context;
pub mod gpu;
pub mod canvas;
pub mod font_library;
pub mod typography;
pub mod path;

#[cfg(feature="window")]
pub mod gui;
