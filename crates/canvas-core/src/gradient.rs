#![allow(non_snake_case)]
use std::cell::{RefCell};
use std::rc::Rc;
use skia_safe::{Shader, Color, Point, TileMode, Matrix};
use skia_safe::{gradient_shader, gradient_shader::GradientShaderColors::Colors};

use crate::utils::*;

enum Gradient{
  Linear{
    start:Point,
    end:Point,
    stops:Vec<f32>,
    colors:Vec<Color>,
  },
  Radial{
    start_point:Point,
    start_radius:f32,
    end_point:Point,
    end_radius:f32,
    stops:Vec<f32>,
    colors:Vec<Color>,
  },
  Conic{
    center:Point,
    angle:f32,
    stops:Vec<f32>,
    colors:Vec<Color>,
  }
}

impl Gradient{
  /// Borrow the sorted f32 offsets (normalized 0-1); no allocation/errors, borrow tied to self.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:34, skia-canvas 3.0.8. Rendering bodies retained.
  fn get_stops(&self) -> &Vec<f32>{
    match self{
      Gradient::Linear{stops, ..} => stops,
      Gradient::Radial{stops, ..} => stops,
      Gradient::Conic{stops, ..} => stops,
    }
  }

  /// Borrow Skia packed colors; no conversion/errors, borrow tied to self.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:42, skia-canvas 3.0.8. Rendering bodies retained.
  fn get_colors(&self) -> &Vec<Color>{
    match self{
      Gradient::Linear{colors, ..} => colors,
      Gradient::Radial{colors, ..} => colors,
      Gradient::Conic{colors, ..} => colors,
    }
  }

  /// Insert an offset/color using the original epsilon comparator; no unit conversion. NaN can panic; adapter validation is separate.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:50, skia-canvas 3.0.8. Rendering bodies retained.
  fn add_stop(&mut self, offset: f32, color:Color){
    let stops = self.get_stops();

    // insert the new entries at the right index to keep the vectors sorted
    let idx = stops.binary_search_by(|n| (n-f32::EPSILON).partial_cmp(&offset).unwrap()).unwrap_or_else(|x| x);
    match self{
      Gradient::Linear{colors, stops, ..} => { colors.insert(idx, color); stops.insert(idx, offset); },
      Gradient::Radial{colors, stops, ..} => { colors.insert(idx, color); stops.insert(idx, offset); },
      Gradient::Conic{colors, stops, ..} => { colors.insert(idx, color); stops.insert(idx, offset); },
    };
  }
}


#[derive(Clone)]
pub struct CanvasGradient{
  gradient:Rc<RefCell<Gradient>>
}

impl CanvasGradient{
  /// Build the original gradient shader from current shared stops; positions are canvas units. Returns owned shader or None; RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:72, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn shader(&self) -> Option<Shader>{
    match &*self.gradient.borrow(){
      Gradient::Linear{start, end, stops, colors} => {
        gradient_shader::linear((*start, *end), Colors(colors), Some(stops.as_slice()), TileMode::Clamp, None, None)
      },
      Gradient::Radial{start_point, start_radius, end_point, end_radius, stops, colors} => {
        gradient_shader::two_point_conical(
          *start_point, *start_radius,
          *end_point, *end_radius,
          Colors(colors), Some(stops.as_slice()),
          TileMode::Clamp, None, None)
      },
      Gradient::Conic{center, angle, stops, colors} => {
        let Point{x, y} = *center;
        let mut rotated = Matrix::new_identity();
        rotated
          .pre_translate((x, y))
          .pre_rotate(*angle, None)
          .pre_translate((-x, -y));

        gradient_shader::sweep(
          *center,
          Colors(colors),
          Some(stops.as_slice()),
          TileMode::Clamp,
          None, // angles
          None, // flags
          Some(&rotated), // local_matrix

        )
      }
    }
  }

  /// Mutate the shared ramp with normalized offset and packed color; returns unit. Retains original Rc aliasing and comparator panic conditions.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:106, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn add_color_stop(&mut self, offset: f32, color:Color){
    self.gradient.borrow_mut().add_stop(offset, color);
  }

  /// Report whether every stop has alpha=255; no parameters or allocation. RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:110, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn is_opaque(&self) -> bool{
    // true if all colors are 100% opaque
    let gradient = self.gradient.borrow();
    !gradient.get_colors().iter().any(|c| c.a() < 255)
  }
}


impl CanvasGradient{
  /// Own a shared empty linear ramp from start/end in canvas units. Returns a gradient; no validation or fallible result.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:121, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn linear(start:Point, end:Point) -> Self {
    let ramp = Gradient::Linear{ start, end, stops:vec![], colors:vec![] };
    let canvas_gradient = CanvasGradient{ gradient:Rc::new(RefCell::new(ramp)) };
    canvas_gradient
  }

  /// Own a shared empty radial ramp from centers/radii in canvas units. Returns a gradient; validation remains at the adapter.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:133, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn radial(start_point:Point, start_radius:f32, end_point:Point, end_radius:f32) -> Self {
    let bloom = Gradient::Radial{ start_point, start_radius, end_point, end_radius, stops:vec![], colors:vec![] };
    let canvas_gradient = CanvasGradient{ gradient:Rc::new(RefCell::new(bloom)) };
    canvas_gradient
  }

  /// Own a shared empty sweep ramp; theta is radians and center is in canvas units. Original radians-to-degrees order retained; returns a gradient.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:145, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn conic(theta:f32, center:Point) -> Self {
    let angle = to_degrees(theta);
    let sweep = Gradient::Conic{ center, angle, stops:vec![], colors:vec![] };
    let canvas_gradient = CanvasGradient{ gradient:Rc::new(RefCell::new(sweep)) };
    canvas_gradient
  }

  /// Return the original static style label without copying ramp contents; RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/gradient.rs:178, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn repr(&self) -> &'static str {
    let gradient = Rc::clone(&self.gradient);
    let style = match &*gradient.borrow(){
      Gradient::Linear{..} => "Linear",
      Gradient::Radial{..} => "Radial",
      Gradient::Conic{..} => "Conic",
    };
    style
  }
}

impl CanvasGradient {
  /// Validate original f32 stop offset after language coercion, before color parsing. Unitless 0..1,
  /// returns unit or original range error string. No ownership/thread transfer.
  /// Upstream: src/gradient.rs:addColorStop range block; only Neon exception allocation removed.
  pub fn validate_offset(offset:f32) -> Result<(), &'static str> {
  if offset < 0.0 || offset > 1.0{
    return Err("Color stop offsets must be between 0.0 and 1.0");
  }

  Ok(())
  }
}
