//! GPU-required development probe of the original shared Canvas/Context pipeline.
//! This executable contains no Node/Python adapter and is not a public API substitute.
use std::{env, fs, io::Write, path::Path};
use canvas_core::{canvas::Canvas, context::{Context2D, Dye}, font_library::FontLibrary, gpu::RenderingEngine};
use skia_safe::{Color, IRect, PaintStyle, Path as SkPath, Rect};
use serde_json::json;

/// Write owned probe bytes into a fresh output directory, refusing existing files.
/// Paths have no units, bytes remain unchanged; propagates I/O errors, no GPU/thread transfer.
fn write_new(directory: &Path, name: &str, bytes: &[u8]) -> std::io::Result<()> {
    fs::OpenOptions::new().write(true).create_new(true).open(directory.join(name))?.write_all(bytes)
}

/// Draw a fixed test scene through original core methods and require the default GPU enum.
/// Coordinates are canvas units, output is unpremultiplied RGBA/PNG plus exact metrics.
/// All Canvas/Context/GPU objects are created, used and dropped on this thread; errors fail the probe.
/// Scene calls correspond to upstream context/api.rs fillRect/fillText/measureText/getImageData.
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let argument = env::args().nth(1).ok_or("Usage: core_gpu NEW_OUTPUT_DIRECTORY")?;
    let output = Path::new(&argument);
    fs::create_dir(output)?;
    let families = FontLibrary::with_shared(|library| library.families());
    let mut canvas = Canvas::new(0.0, 1.4, false);
    canvas.width = 300.0;
    canvas.height = 150.0;
    let mut context = Context2D::new();
    context.reset_size((canvas.width, canvas.height));

    context.state.fill_style = Dye::Color(Color::WHITE);
    context.draw_path(Some(SkPath::rect(Rect::from_xywh(0.0, 0.0, 300.0, 150.0), None)), PaintStyle::Fill, None);
    context.state.fill_style = Dye::Color(Color::from_rgb(40, 120, 217));
    context.draw_path(Some(SkPath::rect(Rect::from_xywh(10.25, 11.75, 113.5, 63.25), None)), PaintStyle::Fill, None);
    let text = "Canvas AV fj";
    let metrics = context.measure_text(text, None);
    context.state.fill_style = Dye::Color(Color::BLACK);
    context.draw_text(text, 10.25, 100.5, None, PaintStyle::Fill);
    context.state.fill_style = Dye::Color(Color::from_rgb(0, 80, 255));
    context.draw_text(text, 10.25, 120.5, None, PaintStyle::Fill);

    let engine = canvas.engine();
    if !matches!(engine, RenderingEngine::GPU) {
        return Err(format!("GPU required, original default selected: {}", engine.status(false)).into());
    }
    let options = canvas.export_options();
    let rgba = context.get_pixels(IRect::from_xywh(0, 0, 300, 150), options.clone(), engine)?;
    let mut png_options = options;
    png_options.format = "png".to_string();
    png_options.outline = false; // Original public Canvas.toBuffer default; irrelevant to raster pixels.
    let page = context.get_page_for_export(&png_options, &engine);
    let png = page.encoded_as(png_options, engine)?;
    let mut status = engine.status(canvas.gpu_disabled);
    status["textContrast"] = json!(canvas.text_contrast);
    status["textGamma"] = json!(canvas.text_gamma);
    write_new(output, "core-gpu-smoke.rgba", &rgba)?;
    write_new(output, "core-gpu-smoke.png", &png)?;
    write_new(output, "core.json", serde_json::to_string_pretty(&json!({
        "schema": "py-skia-canvas-core-probe/v1", "width": 300, "height": 150,
        "backend": {"gpu": true, "engine": status, "evidence": "public-getters"},
        "observations": {"metrics": metrics}, "fontFamilies": families,
        "nativePath": "Default RenderingEngine::GPU passed directly to original Context2D::get_pixels / Page::encoded_as; GPU surface errors fail this process",
        "limitations": ["Typed core calls only; not Python binding, JS coercion, cross-thread GC or native queue trace acceptance"]
    }))?.as_bytes())?;
    println!("CORE_GPU_CAPTURED");
    Ok(())
}
