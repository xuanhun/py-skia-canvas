//! Original decoration_arg decision/order, with language field access separated only.
use super::{DecorationStyle,Spacing};
use crate::utils::css_to_color;
use skia_safe::textlayout::{Decoration,TextDecoration,TextDecorationMode,TextDecorationStyle};

/// Typed field boundary for original decoration_arg. Names/styles/colors are strings,
/// thickness is original f32 Spacing. Errors are the adapter's original field errors.
/// No Context borrow is held while reading fields; implementations must retain their
/// language's original property/error rules. Upstream: src/typography.rs:509.
pub trait DecorationArgs {
    type Error;
    /// Read original named string field, returning owned text or original error; no units.
    fn string(&mut self,name:&str) -> Result<String,Self::Error>;
    /// Read optional thickness object in original raw-size/unit/px order, or None.
    /// Sizes are original f32 CSS/canvas units; errors propagate without changing state.
    fn spacing(&mut self) -> Result<Option<Spacing>,Self::Error>;
}

/// Original decoration selection/default/color/size guard and Through mode. Returns
/// owned DecorationStyle/None or reader error. CurrentColor handling and early default
/// are retained exactly; no font/layout/drawing or GPU changes. Called before borrowing
/// owner Context; no handles cross threads. Upstream: src/typography.rs:509.
pub fn decoration_style<R:DecorationArgs>(reader:&mut R) -> Result<Option<DecorationStyle>,R::Error> {
    let css = reader.string("str")?;

    let line = reader.string("line")?;
    let ty = match line.as_str(){
      "underline" => TextDecoration::UNDERLINE,
      "overline" => TextDecoration::OVERLINE,
      "line-through" => TextDecoration::LINE_THROUGH,
      "none" | _ => return Ok(Some(DecorationStyle::default()))
    };

    let line_style = reader.string("style")?;
    let style = match line_style.as_str(){
      "wavy" => TextDecorationStyle::Wavy,
      "dotted" => TextDecorationStyle::Dotted,
      "dashed" => TextDecorationStyle::Dashed,
      "double" => TextDecorationStyle::Double,
      "solid" | _ => TextDecorationStyle::Solid,
    };

    let color = match reader.string("color")?.as_str(){
      "currentColor" => None,
      color_str => css_to_color(&color_str),
    };

    let inherit = reader.string("inherit")?;
    let size = match inherit.as_str(){
      "from-font" => None,
      _ => reader.spacing()?
    };

    // if the setting is invalid, it should just be ignored
    if css.is_empty() || color.is_none(){ return Ok(None) }

    // As of skia_safe 0.78.2, `Gaps` mode is too buggy, with random breaks in places that don't have
    // descenders. It would be nice to enable this in a future release once it stabilizes…
    let mode = TextDecorationMode::Through;

    let decoration = Decoration{ ty, style, mode, ..Decoration::default() };
    Ok(Some(DecorationStyle{ decoration, size, color, css} ))
}
