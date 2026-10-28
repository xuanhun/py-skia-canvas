//! Original context/api.rs effect state, language reads/results removed only.
#![allow(non_snake_case)]
use super::Context2D;
use skia_safe::Color;
use crate::{utils::*,filter::{Filter,FilterSpec}};

/// Original set_globalAlpha operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1161 v3.0.8.
pub fn set_globalAlpha(this:&mut Context2D, num:f32)->() {
  if (0.0..=1.0).contains(&num){
    this.state.global_alpha = num;
  }
}

/// Original set_globalCompositeOperation operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1179 v3.0.8.
pub fn set_globalCompositeOperation(this:&mut Context2D, name:String)->() {
  if let Some(mode) = to_blend_mode(&name){
    this.state.global_composite_operation = mode;
    this.state.paint.set_blend_mode(mode);
  }
}

/// Original set_shadowBlur operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1219 v3.0.8.
pub fn set_shadowBlur(this:&mut Context2D, num:f32)->() {
  if num >= 0.0{
    this.state.shadow_blur = num;
  }
}

/// Original set_shadowColor operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1236 v3.0.8.
pub fn set_shadowColor(this:&mut Context2D, color:Option<Color>)->() {
  if let Some(color) = color{
    this.state.shadow_color = color;
  }
}

/// Original set_shadowOffsetX operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1257 v3.0.8.
pub fn set_shadowOffsetX(this:&mut Context2D, num:f32)->() {
  this.state.shadow_offset.x = num;
}

/// Original set_shadowOffsetY operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1264 v3.0.8.
pub fn set_shadowOffsetY(this:&mut Context2D, num:f32)->() {
  this.state.shadow_offset.y = num;
}

/// Original set_lineDashFit operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:566 v3.0.8.
pub fn set_lineDashFit(this:&mut Context2D, style:String)->() {
  if let Some(fit) = to_1d_style(&style){
    this.state.line_dash_fit = fit;
  }
}

/// Original set_filter operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1199 v3.0.8.
pub fn set_filter(this:&mut Context2D, filter_text:String, specs:Vec<FilterSpec>)->() {
    if filter_text != this.state.filter.to_string() {
      this.state.filter = Filter::new(&filter_text, &specs);
    }}

/// Original get_globalAlpha operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1155 v3.0.8.
pub fn get_globalAlpha(this:&Context2D)->f32 {
  this.state.global_alpha
}

/// Original get_globalCompositeOperation operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1172 v3.0.8.
pub fn get_globalCompositeOperation(this:&Context2D)->String {
  let mode = from_blend_mode(this.state.global_composite_operation);
  mode
}

/// Original get_shadowBlur operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1213 v3.0.8.
pub fn get_shadowBlur(this:&Context2D)->f32 {
  this.state.shadow_blur
}

/// Original get_shadowColor operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1229 v3.0.8.
pub fn get_shadowColor(this:&Context2D)->Color {
  let shadow_color = this.state.shadow_color;
  shadow_color
}

/// Original get_shadowOffsetX operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1245 v3.0.8.
pub fn get_shadowOffsetX(this:&Context2D)->f32 {
  this.state.shadow_offset.x
}

/// Original get_shadowOffsetY operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1251 v3.0.8.
pub fn get_shadowOffsetY(this:&Context2D)->f32 {
  this.state.shadow_offset.y
}

/// Original get_lineDashFit operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:576 v3.0.8.
pub fn get_lineDashFit(this:&Context2D)->String {
  let fit = from_1d_style(this.state.line_dash_fit);
  fit
}

/// Original get_filter operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:1193 v3.0.8.
pub fn get_filter(this:&Context2D)->String {
  this.state.filter.to_string()
}
