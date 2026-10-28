#![allow(non_snake_case)]
use std::cell::RefCell;
use std::rc::Rc;
use std::f32::consts::PI;
use skia_safe::{Path, Color, Color4f, Matrix, Paint, PaintStyle, PaintCap, Point};
use skia_safe::{line_2d_path_effect, path_2d_path_effect};


struct Texture{
  path: Option<Path>,
  color: Color,
  line: f32,
  cap: PaintCap,
  angle: f32,
  scale: (f32, f32),
  shift: (f32, f32),
}


impl Default for Texture {
  /// Create original black, unit-spaced, zero-angle line texture; returns an owned value with no validation/errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:25, skia-canvas 3.0.8. Rendering bodies retained.
  fn default() -> Self {
    Texture{path:None, color:Color::BLACK, line:1.0, cap:PaintCap::Butt, angle:0.0, scale:(1.0, 1.0), shift:(0.0, 0.0)}
  }
}

#[derive(Clone)]
pub struct CanvasTexture{
  texture:Rc<RefCell<Texture>>,
  outline: bool,
}

impl CanvasTexture{
  /// Borrow paint and apply the original tile effect; alpha is a scalar, shift/line/spacing are canvas units, angle is radians. Returns unit; RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:37, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn mix_into(&self, paint: &mut Paint, alpha:f32){
    let tile = self.texture.borrow();

    let mut matrix = Matrix::new_identity();
    matrix
      .pre_translate(tile.shift)
      .pre_rotate(180.0 * tile.angle / PI, None);

    match &tile.path {
      Some(path) => {
        let path = path.with_transform(&Matrix::rotate_rad(tile.angle));
        matrix.pre_scale(tile.scale, None);
        paint.set_path_effect(path_2d_path_effect::new(&matrix, &path));
      }
      None => {
        let scale = tile.scale.0.max(tile.scale.1);
        matrix.pre_scale((scale, scale), None);
        paint.set_path_effect(line_2d_path_effect::new(tile.line, &matrix));
      }
    };

    if tile.line > 0.0{
      paint.set_stroke_width(tile.line);
      paint.set_stroke_cap(tile.cap);
      paint.set_style(PaintStyle::Stroke);
    }else{
      paint.set_style(PaintStyle::Fill);
    }

    let mut color:Color4f = tile.color.into();
    color.a *= alpha;
    paint.set_color(color.to_color());
  }

  /// Return original inverse-outline clipping policy (boolean), with no parameters, allocation or errors.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:71, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn use_clip(&self) -> bool{
    !self.outline
  }

  /// Return original spacing as a Point in canvas units; retains shared texture ownership, RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:75, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn spacing(&self) -> Point {
    let tile = self.texture.borrow();
    tile.scale.into()
  }

  /// Multiply original packed color alpha by scalar alpha using Color4f; returns packed Color, preserving original rounding.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:80, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn to_color(&self, alpha:f32) -> Color {
    let tile = self.texture.borrow();
    let mut color:Color4f = tile.color.into();
    color.a *= alpha;
    color.to_color()
  }

}


impl CanvasTexture{
  /// Own path/color/line/cap/angle/outline/spacing/shift without revalidation. Lengths are canvas units, angle radians; returns Rc-shared texture.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:93, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn new(path:Option<Path>, color:Color, line:f32, cap:PaintCap, angle:f32, outline:bool, scale:(f32,f32), shift:(f32,f32)) -> Self {
    let texture = Texture{path, color, line, cap, angle, scale, shift};
    let canvas_texture = CanvasTexture{ texture:Rc::new(RefCell::new(texture)), outline };
    canvas_texture
  }

  /// Return original Path/Lines style label; no units/allocation, RefCell conflicts panic.
  /// Use on the resource's owner thread; no Send/Sync or GPU-context transfer is introduced.
  /// Upstream: src/texture.rs:130, skia-canvas 3.0.8. Rendering bodies retained.
  pub fn repr(&self) -> &'static str {
    let tile = self.texture.borrow();
    let style = if tile.path.is_some(){ "Path" }else{ "Lines" };
    style
  }
}
