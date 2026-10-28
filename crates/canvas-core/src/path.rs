#![allow(unused_mut)]
#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(non_snake_case)]
#![allow(dead_code)]
use std::f32::{EPSILON, consts::PI};
use skia_safe::{Path, Point, PathFillType, PathDirection, PathBuilder, Rect, RRect, Matrix, PathOp, StrokeRec};
use skia_safe::{PathEffect, trim_path_effect};
use skia_safe::path::{self, AddPathMode, Verb};

use crate::utils::*;
pub mod operations;


pub struct Path2D{
  pub path:Path
}

impl Default for Path2D {
  /// Original Path2D construction or ellipse/scoot operation; coordinates/radii in canvas units, angles in radians.
  /// Returns original owned path/unit; no new validation/errors. Retains original Skia ownership; owner-thread use.
  /// Upstream: src/path.rs (before Javascript Methods), skia-canvas 3.0.8; body unchanged.
  fn default() -> Self {
    Self{ path:Path::new() }
  }
}

impl From<PathBuilder> for Path2D{
  /// Original Path2D construction or ellipse/scoot operation; coordinates/radii in canvas units, angles in radians.
  /// Returns original owned path/unit; no new validation/errors. Retains original Skia ownership; owner-thread use.
  /// Upstream: src/path.rs (before Javascript Methods), skia-canvas 3.0.8; body unchanged.
  fn from(builder: PathBuilder) -> Self {
    Self{path:builder.into()}
  }
}

impl Path2D{
  /// Original Path2D construction or ellipse/scoot operation; coordinates/radii in canvas units, angles in radians.
  /// Returns original owned path/unit; no new validation/errors. Retains original Skia ownership; owner-thread use.
  /// Upstream: src/path.rs (before Javascript Methods), skia-canvas 3.0.8; body unchanged.
  pub fn scoot(&mut self, x: f32, y: f32){
    if self.path.is_empty(){
      self.path.move_to((x, y));
    }
  }

  /// Original Path2D construction or ellipse/scoot operation; coordinates/radii in canvas units, angles in radians.
  /// Returns original owned path/unit; no new validation/errors. Retains original Skia ownership; owner-thread use.
  /// Upstream: src/path.rs (before Javascript Methods), skia-canvas 3.0.8; body unchanged.
  pub fn add_ellipse(&mut self, origin:impl Into<Point>, radii:impl Into<Point>, rotation: f32, start_angle:f32, end_angle:f32, ccw:bool){
    let Point{x, y} = origin.into();
    let Point{x:x_radius, y:y_radius} = radii.into();

    // based off of CanonicalizeAngle in Chrome
    let tau = 2.0 * PI;
    let mut new_start_angle = start_angle % tau;
    if new_start_angle < 0.0 {
      new_start_angle += tau;
    }
    let delta = new_start_angle - start_angle;
    let start_angle = new_start_angle;
    let mut end_angle = end_angle + delta;

    // Originally based off of AdjustEndAngle in Chrome, but does not limit to 360 degree sweep.
    if !ccw && start_angle > end_angle {
      end_angle = start_angle + (tau - (start_angle - end_angle) % tau);
    }else if ccw && start_angle < end_angle {
      end_angle = start_angle - (tau - (end_angle - start_angle) % tau);
    }

    let oval = Rect::new(x - x_radius, y - y_radius, x + x_radius, y + y_radius);

    let mut rotated = Matrix::new_identity();
    rotated
      .pre_translate((x, y))
      .pre_rotate(to_degrees(rotation), None)
      .pre_translate((-x, -y));

    self.path.transform(&rotated.invert().unwrap());
    {
      // Based off of Chrome's implementation in
      // https://cs.chromium.org/chromium/src/third_party/blink/renderer/platform/graphics/path.cc
      // of note, can't use addArc or addOval because they close the arc, which
      // the spec says not to do (unless the user explicitly calls closePath).
      // This throws off points being in/out of the arc.

      // rounding degrees to 4 decimals eliminates ambiguity from f32 imprecision dealing with radians
      let mut sweep_deg = (to_degrees(end_angle - start_angle) * 10000.0).round() / 10000.0;
      let mut start_deg = (to_degrees(start_angle) * 10000.0).round() / 10000.0;

      // draw 360° ellipses in two 180° segments; trying to draw the full ellipse at once draws nothing.
      if sweep_deg >= 360.0 - EPSILON  {
        self.path.arc_to(oval, start_deg, 180.0, false);
        self.path.arc_to(oval, start_deg + 180.0, 180.0, false);
      }else if sweep_deg <= -360.0 + EPSILON {
        self.path.arc_to(oval, start_deg, -180.0, false);
        self.path.arc_to(oval, start_deg - 180.0, -180.0, false);
      }else{
        // Draw incomplete (< 360°) ellipses in a single arc.
        self.path.arc_to(oval, start_deg, sweep_deg, false);
      }
    }
    self.path.transform(&rotated);
  }
}

