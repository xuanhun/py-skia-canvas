use std::fs;
use std::path::Path as FilePath;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, OnceLock};
use rayon::prelude::*;
use skia_safe::{
  svg::{self, canvas::Flags},
  image::{BitDepth, CachingHint}, images, pdf,
  Canvas as SkCanvas, ClipOp, Color, ColorSpace, ColorType, AlphaType, Document, Surface,
  Image as SkImage, ImageInfo, Matrix, Path, Picture, PictureRecorder, Rect, IRect, Size, ISize,
  SurfaceProps, SurfacePropsFlags, PixelGeometry, jpeg_encoder, png_encoder, webp_encoder
};
use dashmap::DashMap;
use little_exif::{metadata::Metadata, exif_tag::ExifTag, filetype::FileExtension};
use crc::{Crc, CRC_32_ISO_HDLC};
const CRC32: Crc<u32> = Crc::<u32>::new(&CRC_32_ISO_HDLC);

use crate::gpu::RenderingEngine;

static CACHE: OnceLock<Arc<DashMap<usize, PageCache>>> = OnceLock::new();


pub mod audit;
//
// Deferred canvas (records drawing commands for later replay on an output surface)
//

pub struct PageRecorder{
  current: PictureRecorder,
  layers: Vec<Picture>,
  bounds: Rect,
  matrix: Matrix,
  clip: Option<Path>,
  surface: RecordingSurface,
  changed: bool,
  id: usize,
}

impl PageRecorder{
  /// Create an owned recorder for bounds in canvas units; allocate the original counter/cache entry and recording depth. No new errors; allocation may panic.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:42, skia-canvas 3.0.8; function body unchanged.
  pub fn new(bounds:Rect) -> Self {
    static COUNTER:AtomicUsize = AtomicUsize::new(1);
    let id = COUNTER.fetch_add(1, Ordering::Relaxed);
    PageCache::add(id);

    let mut rec = PictureRecorder::new();
    rec.begin_recording(bounds, true).save(); // start at depth 2

    PageRecorder{
      current:rec, layers:vec![], changed:false, matrix:Matrix::default(), clip:None, bounds, id,
      surface:RecordingSurface::default(),
    }
  }

  /// Borrow the current canvas for FnOnce and mark it changed; returns unit, never sends the recorder or callback to another thread.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:56, skia-canvas 3.0.8; function body unchanged.
  pub fn append<F>(&mut self, f:F)
    where F:FnOnce(&SkCanvas)
  {
    if let Some(canvas) = self.current.recording_canvas() {
      f(canvas);
      self.changed = true;
    }
  }

  /// Replace this recorder with the original fresh recorder for new canvas-unit bounds; drop the old cache entry in original order.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:65, skia-canvas 3.0.8; function body unchanged.
  pub fn set_bounds(&mut self, bounds:Rect){
    *self = PageRecorder::new(bounds);
  }

  /// Update canvas-unit bounds without clearing recordings; returns unit, with no new validation or errors.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:69, skia-canvas 3.0.8; function body unchanged.
  pub fn update_bounds(&mut self, bounds:Rect){
    self.bounds = bounds; // non-destructively update the size
  }

  /// Store and apply the borrowed recorder's unitless transform matrix; returns unit and retains the original save depth.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:73, skia-canvas 3.0.8; function body unchanged.
  pub fn set_matrix(&mut self, matrix:Matrix){
    self.matrix = matrix;
    if let Some(canvas) = self.current.recording_canvas() {
      canvas.set_matrix(&matrix.into());
    }
  }

  /// Clone original clip path in canvas units and restore the original matrix/clip stack; returns unit, no ownership transfer.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:80, skia-canvas 3.0.8; function body unchanged.
  pub fn set_clip(&mut self, clip:&Option<Path>){
    self.clip = clip.clone();
    self.restore();
  }

  /// Restore original recording depth, clip and matrix; no parameters or new errors, keeps this recorder on its owner thread.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:85, skia-canvas 3.0.8; function body unchanged.
  pub fn restore(&mut self){
    if let Some(canvas) = self.current.recording_canvas() {
      canvas.restore_to_count(1);
      canvas.save();
      if let Some(clip) = &self.clip{
        canvas.clip_path(clip, ClipOp::Intersect, true /* antialias */);
      }
      canvas.set_matrix(&self.matrix.into());
    }
  }

  /// Read crop (integer pixels) with original options/engine into owned unpremultiplied bytes; off-canvas stays zero, failures return original String error.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:96, skia-canvas 3.0.8; function body unchanged.
  pub fn get_pixels(&mut self, crop:IRect, opts:ExportOptions, engine:RenderingEngine) -> Result<Vec<u8>, String>{
    // return an empty buffer if the requested rect is entirely outside the canvas
    let dst_info = ImageInfo::new((crop.width(), crop.height()), opts.color_type.clone(), AlphaType::Unpremul, opts.color_space.clone());
    let mut dst_buffer: Vec<u8> = vec![0; dst_info.compute_min_byte_size()];
    if !self.bounds.intersects(Rect::from_irect(crop)){
      return Ok(dst_buffer)
    }

    let page = self.get_page();
    self.surface.update(&page, &opts, &engine);

    match self.surface.copy_pixels(&dst_info, crop, &mut dst_buffer){
      true => Ok(dst_buffer),
      false => Err(format!("Could not get image data (format: {:?})", dst_info.color_type()))
    }
  }

  /// Snapshot changed recordings into original Picture layers and resume the recorder; returns owned Page with original shared picture references.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:113, skia-canvas 3.0.8; function body unchanged.
  pub fn get_page(&mut self) -> Page{
    if self.changed {
      // store layer as a drawable (so copies are deduplicated) wrapped in a picture (so it can be sent to other threads)
      self.current
        .finish_recording_as_drawable()
        .and_then(|mut drawable|{
          let mut wrapper = PictureRecorder::new();
          wrapper.begin_recording(self.bounds, true).draw_drawable(&mut drawable, None);
          wrapper.finish_recording_as_picture(None)
        }).map(|pict|
          self.layers.push(pict)
        );

      // resume recording
      self.current.begin_recording(self.bounds, true);
      self.changed = false;
      self.restore();
    }

    Page{
      layers: self.layers.clone(),
      bounds: self.bounds,
      id: self.id,
    }
  }

  /// Snapshot the page and update original raster cache if valid for options/engine; returns Page, preserves materialization boundary.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:139, skia-canvas 3.0.8; function body unchanged.
  pub fn get_page_for_export(&mut self, opts:&ExportOptions, engine:&RenderingEngine) -> Page{
    // update the PageCache with the surface bitmap (if it's valid for this export)
    let page = self.get_page();
    if opts.is_raster(){
      if let Some(image) = self.surface.snapshot_if_valid(&page, &opts, &engine){
        PageCache::set(self.id, image, &opts, self.surface.depth);
      }
    }
    page
  }

  /// Return original deferred image for floored canvas dimensions or None; retains original picture/color-space references.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:150, skia-canvas 3.0.8; function body unchanged.
  pub fn get_image(&mut self) -> Option<SkImage>{
    let size = self.bounds.size().to_floor();
    self
      .get_page()
      .get_picture(None)
      .and_then(|pict| {
        images::deferred_from_picture(
          pict, size, None, None, BitDepth::U8, Some(ColorSpace::new_srgb()), None
        )
      })
  }
}

impl Drop for PageRecorder{
  /// Remove original cache entry for page ID; no return value. Original missing-ID unwrap panic and owner-thread destruction behavior are retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:164, skia-canvas 3.0.8; function body unchanged.
  fn drop(&mut self) {
    PageCache::drop(self.id);
  }
}


//
// Persistent GPU/CPU surface for caching intermediate results of getImageData()
//

pub struct RecordingSurface{
  surface: Option<Surface>,
  depth: usize,
  matte: Option<Color>,
  msaa: Option<usize>,
  gpu: Option<bool>,
  color_space: ColorSpace,
  density: f32,
}

impl Default for RecordingSurface{
  /// Create the original default recording surface/page/cache/export-options value; no inputs, original field values and allocation behavior retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:185, skia-canvas 3.0.8; function body unchanged.
  fn default() -> Self {
      Self{surface:None, depth:0, matte:None, msaa:None, gpu:None, color_space:ColorSpace::new_srgb(), density:0.0}
  }
}

impl RecordingSurface{

  /// Test original engine toggle and density-scaled pixel dimensions; returns boolean and borrows the existing surface on its owner thread.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:192, skia-canvas 3.0.8; function body unchanged.
  fn is_surface_stale(&mut self, page:&Page, opts:&ExportOptions, engine:&RenderingEngine) -> bool{
    let gpu_toggled = self.gpu != Some(matches!(engine, RenderingEngine::GPU));
    let page_size = page.scaled_dimensions(opts.density);
    let resized = self.surface.as_mut().map(|surface|{
      surface.image_info().dimensions() != page_size
    }).unwrap_or(true);

    gpu_toggled || resized
  }

  /// Compare original density, matte, MSAA and color space; returns boolean, with no validation, allocation or errors.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:202, skia-canvas 3.0.8; function body unchanged.
  fn is_config_stale(&self, opts:&ExportOptions) -> bool{
    self.density != opts.density ||
    self.matte != opts.matte ||
    self.msaa != opts.msaa ||
    self.color_space != opts.color_space
  }

  /// Apply original cache invalidation/replay for page/options/engine; density is pixels per canvas unit. Surface allocation failure is retained as None.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:209, skia-canvas 3.0.8; function body unchanged.
  pub fn update(&mut self, page:&Page, opts:&ExportOptions, engine:&RenderingEngine){
    // check for anything that would invalidate the previous contents
    let reconfigure = self.is_config_stale(&opts);
    let recreate = self.is_surface_stale(&page, &opts, &engine);

    // start from scratch if invalidated
    if reconfigure || recreate{
      self.gpu = Some(matches!(engine, RenderingEngine::GPU));
      self.color_space = opts.color_space.clone();
      self.density = opts.density;
      self.matte = opts.matte;
      self.msaa = opts.msaa;
      self.depth = 0;

      // only allocate a new surface if the dimensions (size * density) have changed or engine switched
      if recreate{
        let page_size = page.scaled_dimensions(opts.density);
        let img_info = ImageInfo::new_n32_premul(page_size, opts.color_space.clone());
        self.surface = engine.make_surface(&img_info, &opts).ok();
      }
    }

    if let Some(surface) = self.surface.as_mut(){
      let canvas = surface.canvas();
      let (cache_image, cache_depth) = PageCache::get(page.id, &opts, page.depth());

      if let Some(image) = cache_image{
        // use the cached bitmap as the background (if present)
        canvas.draw_image(image, (0,0), None);
        self.depth = cache_depth;
      }else if self.depth==0 {
        // otherwise, fill the canvas if requested
        canvas.clear(self.matte.unwrap_or(Color::TRANSPARENT));
      }


      // only add new layers to surface
      canvas.scale((self.density, self.density));

      // draw newly added layers
      for pict in page.layers.iter().skip(self.depth){
        pict.playback(canvas);
      }
      self.depth = page.layers.len();
    }
  }

  /// Return owned Skia image snapshot only for the original valid nonempty surface; options/dimensions/cache depth rules remain unchanged.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:256, skia-canvas 3.0.8; function body unchanged.
  pub fn snapshot_if_valid(&mut self, page:&Page, opts:&ExportOptions, engine:&RenderingEngine) -> Option<SkImage>{
    match !(self.is_config_stale(&opts) || self.is_surface_stale(&page, &opts, &engine) || self.depth==0){
      true => self.surface.as_mut().map(|surface| surface.image_snapshot()),
      false => None,
    }
  }

  /// Copy original integer-pixel crop into caller-owned output bytes using ImageInfo row layout; return success boolean without resizing/conversion.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:263, skia-canvas 3.0.8; function body unchanged.
  pub fn copy_pixels(&mut self, dst_info: &ImageInfo, src: IRect, pixels: &mut [u8]) -> bool{
    self.surface.as_mut().map(|surface|{
      surface.read_pixels(dst_info, pixels, dst_info.min_row_bytes(), (src.x(), src.y()))
    }).unwrap_or(false)
  }
}


//
// Image generator for a single drawing context
//

#[derive(Debug, Clone)]
pub struct Page{
  pub id: usize,
  pub bounds: Rect,
  pub layers: Vec<Picture>,
}

impl PartialEq for Page {
  /// Compare original page ID and layer depth only; returns boolean, does not compare rendered pixels or change ownership.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:283, skia-canvas 3.0.8; function body unchanged.
  fn eq(&self, other: &Self) -> bool {
    self.id == other.id &&
    self.depth() == other.depth()
  }
}

impl Default for Page {
  /// Create the original default recording surface/page/cache/export-options value; no inputs, original field values and allocation behavior retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:290, skia-canvas 3.0.8; function body unchanged.
  fn default() -> Self {
    Self{ id:0, bounds: skia_safe::Rect::new_empty(), layers:vec![] }
  }
}

impl Page{
  /// Return layer count as usize with no allocation, mutation or error.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:296, skia-canvas 3.0.8; function body unchanged.
  pub fn depth(&self) -> usize{
    self.layers.len()
  }

  /// Multiply canvas-unit bounds by density (pixels/unit) and floor at the original point; return integer pixel size without new validation.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:300, skia-canvas 3.0.8; function body unchanged.
  pub fn scaled_dimensions(&self, density:f32) -> ISize{
    Size::new(self.bounds.width() * density, self.bounds.height() * density).to_floor()
  }

  /// Replay original layers into an owned Picture, optionally clearing to matte first; return None if recording cannot finish.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:304, skia-canvas 3.0.8; function body unchanged.
  pub fn get_picture(&self, matte:Option<Color>) -> Option<Picture> {
    let mut compositor = PictureRecorder::new();
    let output = compositor.begin_recording(self.bounds, true);
    matte.map(|c| output.clear(c));
    self.layers.iter().for_each(|pict| pict.playback(output));
    compositor.finish_recording_as_picture(None)
  }

  /// Encode original Page/options/engine as raster/vector bytes; density, alpha, MSAA, PNG DPI/CRC and JPEG/WebP metadata rules stay unchanged. Original String errors/panics propagate.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:312, skia-canvas 3.0.8; function body unchanged.
  pub fn encoded_as(&self, options:ExportOptions, engine:RenderingEngine) -> Result<Vec<u8>, String> {
    if self.bounds.is_empty(){
      return Err("Width and height must be non-zero to generate an image".to_string())
    }

    let ExportOptions{ ref format, quality, density, matte, color_type, .. } = options;
    let size = self.bounds.size();
    let img_dims = self.scaled_dimensions(density);
    let img_info = ImageInfo::new_n32_premul(img_dims, Some(ColorSpace::new_srgb()));
    let img_quality = ((quality*100.0) as u32).clamp(0, 100);
    let img_scale = Matrix::scale((density, density)).into();

    match format.as_str(){
      "pdf" => {
        let mut pdf_bytes = Vec::new();
        let mut document = pdf_document(&mut pdf_bytes, quality, density).begin_page(size, None);
        let canvas = document.canvas();
        let picture = self.get_picture(matte).ok_or("Could not generate an image")?;
        canvas.draw_picture(&picture, None, None);
        document.end_page().close();
        Ok(pdf_bytes)
      }

      "svg" => {
        let canvas = svg::Canvas::new(Rect::from_size(size), options.svg_flags());
        let picture = self.get_picture(matte).ok_or("Could not generate an image")?;
        canvas.draw_picture(&picture, None, None);
        Ok(canvas.end().as_bytes().to_vec())
      }

      // handle bitmap formats using (potentially gpu-backed) rasterizer
      _ => {
        let mut surface = engine.make_surface(&img_info, &options)?;
        let canvas = surface.canvas();

        let (cache_image, cache_depth) = PageCache::get(self.id, &options, self.depth());
        if let Some(image) = cache_image{
          // use the cached bitmap as the background
          canvas.draw_image(image, (0,0), None);
        }else if let Some(color) = options.matte{
          // otherwise, fill the canvas if requested
          canvas.clear(color);
        }

        // draw newly added layers and cache the full-canvas bitmap
        canvas.set_matrix(&img_scale);
        for pict in self.layers.iter().skip(cache_depth){
          pict.playback(canvas);
        }

        // extract the results
        let context = &mut surface.direct_context();
        let image = surface.make_temporary_image().unwrap_or_else(|| surface.image_snapshot());

        // update cache
        if self.depth() > cache_depth{
          if rayon::current_thread_index().is_some(){
            // move bitmap off GPU if we're in a background thread and need to share
            image.make_non_texture_image(&mut surface.direct_context())
              .map(|raster| PageCache::set(self.id, raster, &options, self.depth()) );
          }else{
            PageCache::set(self.id, image.clone(), &options, self.depth());
          }
        }

        // handle image encoding
        match format.as_str(){
          "raw" => {
            let dst_info = ImageInfo::new(img_dims, color_type, AlphaType::Unpremul, Some(ColorSpace::new_srgb()));
            let mut buffer: Vec<u8> = vec![0; dst_info.compute_min_byte_size()];
            match surface.read_pixels(&dst_info, &mut buffer, dst_info.min_row_bytes(), (0,0)){
              true => Some(buffer),
              false => return Err(format!("Could not encode as {} ({:?})", format, color_type))
            }
          }

          "jpg" | "jpeg" => {
            let jpg_opts = jpeg_encoder::Options {
                quality: img_quality,
                downsample: match options.jpeg_downsample{
                  true => jpeg_encoder::Downsample::BothDirections,
                  false => jpeg_encoder::Downsample::No,
                },
                ..jpeg_encoder::Options::default()
            };

            jpeg_encoder::encode_image(context, &image, &jpg_opts).map(|data|{
              let mut bytes = data.as_bytes().to_vec();
              let [l, r] = (72 * density as u16).to_be_bytes();
              bytes.splice(13..18, [1, l, r, l, r].iter().cloned());
              bytes
            })
          }

          "png" => {
            let png_opts = png_encoder::Options::default();

            png_encoder::encode_image(context, &image, &png_opts).map(|data|{
              let mut bytes = data.as_bytes().to_vec();
              let mut digest = CRC32.digest();
              let [a, b, c, d] = ((72.0 * density * 39.3701) as u32).to_be_bytes();
              let phys = vec![
                b'p', b'H', b'Y', b's',
                a, b, c, d, // x-dpi
                a, b, c, d, // y-dpi
                1, // dots per meter
              ];
              digest.update(&phys);

              let length = 9u32.to_be_bytes().to_vec();
              let checksum = digest.finalize().to_be_bytes().to_vec();
              bytes.splice(33..33, [length, phys, checksum].concat());
              bytes
            })
          }

          "webp" => {
            let mut webp_opts = webp_encoder::Options::default();
            if img_quality == 100 {
                webp_opts.compression = webp_encoder::Compression::Lossless;
                webp_opts.quality = 75.0;
            } else {
                webp_opts.compression = webp_encoder::Compression::Lossy;
                webp_opts.quality = img_quality as _;
            }

            webp_encoder::encode_image(context, &image, &webp_opts).map(|data|{
              let mut bytes = data.as_bytes().to_vec();

              // toggle EXIF flag in VP8X chunk
              bytes[20] |= 1 << 3;

              // append EXIF chunk with DPI
              let dpi = (72.0 * density) as f64;
              let mut exif = Metadata::new();
              exif.set_tag( ExifTag::XResolution(vec![dpi.into()]) );
              exif.set_tag( ExifTag::YResolution(vec![dpi.into()]) );
              if let Ok(mut exif_bytes) = exif.as_u8_vec(FileExtension::WEBP){
                bytes.append(&mut exif_bytes);
              }

              // update file-length field in RIFF header
              let file_size = ((bytes.len() - 8) as u32).to_le_bytes();
              bytes.splice(4..8, file_size.iter().cloned());

              bytes
            })
          }
          _ => return Err(format!("Unsupported file format {}", format))
        }.ok_or(format!("Could not encode as {}", format))
      }
    }
  }

  /// Encode then write to the supplied path; owns returned bytes, borrows filename, returns original I/O/encode String error or unit success.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:466, skia-canvas 3.0.8; function body unchanged.
  pub fn write(&self, filename: &str, options:ExportOptions, engine:RenderingEngine) -> Result<(), String> {
    let path = FilePath::new(&filename);
    let data = self.encoded_as(options, engine)?;
    fs::write(path, data).map_err(|why|
      format!("{}: \"{}\"", why, path.display())
    )
  }

  /// Append original page to the borrowed PDF document with optional matte; returns document with original writer lifetime or zero-size String error.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:474, skia-canvas 3.0.8; function body unchanged.
  fn append_to<'a>(&self, doc:Document<'a>, matte:Option<Color>) -> Result<Document<'a>, String>{
    if !self.bounds.is_empty(){
      let mut doc = doc.begin_page(self.bounds.size(), None);
      let canvas = doc.canvas();
      if let Some(picture) = self.get_picture(matte){
        canvas.draw_picture(&picture, None, None);
      }
      Ok(doc.end_page())
    }else{
      Err("Width and height must be non-zero to generate a PDF page".to_string())
    }
  }
}

//
// Container for a canvas's entire stack of page contexts
//

pub struct PageSequence{
  pub pages: Vec<Page>,
  pub engine: RenderingEngine
}

impl PageSequence{
  /// Own original ordered pages and rendering-engine selector; returns PageSequence without cloning a GPU context or adding validation.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:498, skia-canvas 3.0.8; function body unchanged.
  pub fn from(pages:Vec<Page>, engine:RenderingEngine) -> Self{
    PageSequence { pages, engine }
  }

  /// Borrow first original page; returns reference tied to self and retains empty-sequence index panic.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:502, skia-canvas 3.0.8; function body unchanged.
  pub fn first(&self) -> &Page {
    &self.pages[0]
  }

  /// Return original number of pages, with no units, allocation, validation or errors.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:506, skia-canvas 3.0.8; function body unchanged.
  pub fn len(&self) -> usize{
    self.pages.len()
  }

  /// Move original cached texture images to non-texture data before worker export when options are raster; invokes the owning thread's original context path.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:510, skia-canvas 3.0.8; function body unchanged.
  pub fn materialize(&mut self, engine:&RenderingEngine, options:&ExportOptions){
    if !options.is_raster(){ return }
    for page in self.pages.iter_mut(){
      PageCache::materialize(page.id, &engine, &options);
    }
  }

  /// Encode ordered original pages into owned PDF bytes using quality/density/matte; return original per-page/recording String error.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:517, skia-canvas 3.0.8; function body unchanged.
  pub fn as_pdf(&self, options:ExportOptions) -> Result<Vec<u8>, String>{
    let ExportOptions{ quality, density, matte, .. } = options;
    let mut pdf_bytes = Vec::new();
    self.pages
      .iter()
      .try_fold(pdf_document(&mut pdf_bytes, quality, density), |doc, page| page.append_to(doc, matte))
      .map(|doc| doc.close())?;
    Ok(pdf_bytes)
  }

  /// Write first page to supplied path with original options and engine; returns original encoding/I/O result without changing page selection.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:527, skia-canvas 3.0.8; function body unchanged.
  pub fn write_image(&self, pattern:&str, options:ExportOptions) -> Result<(), String>{
    self.first().write(pattern, options, self.engine)
  }

  #[allow(clippy::too_many_arguments)]
  /// Write original page sequence via Rayon using filename pattern/padding and options; padding is digits, density pixels/unit. Original errors, worker data and order retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:532, skia-canvas 3.0.8; function body unchanged.
  pub fn write_sequence(&self, pattern:&str, padding:f32, options:ExportOptions) -> Result<(), String>{
    let padding = match padding as i32{
      -1 => (1.0 + (self.pages.len() as f32).log10().floor()) as usize,
      pad => pad as usize
    };

    self.pages
      .par_iter()
      .enumerate()
      .try_for_each(|(pp, page)|{
        let folio = format!("{:0width$}", pp+1, width=padding);
        let filename = pattern.replace("{}", folio.as_str());
        page.write(&filename, options.clone(), self.engine)
      })
  }

  /// Write original multipage PDF bytes to path; returns original encoding/I/O String result, no change to document metadata policy.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:548, skia-canvas 3.0.8; function body unchanged.
  pub fn write_pdf(&self, path:&str, options:ExportOptions) -> Result<(), String>{
    let path = FilePath::new(&path);
    match self.as_pdf(options){
      Ok(document) => fs::write(path, document).map_err(|why|
        format!("{}: \"{}\"", why, path.display())
      ),
      Err(msg) => Err(msg)
    }
  }
}

//
// Cache for the last bitmap generated by a given Page
//

#[derive(Debug, Clone)]
struct PageCache{
  image: Option<SkImage>,
  density: f32,
  matte: Option<Color>,
  msaa: Option<usize>,
  depth: usize,
}

impl Default for PageCache{
  /// Create the original default recording surface/page/cache/export-options value; no inputs, original field values and allocation behavior retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:573, skia-canvas 3.0.8; function body unchanged.
  fn default() -> Self {
    Self{image:None, depth:0, density:1.0, matte:None, msaa:None}
  }
}

impl PageCache{
  /// Borrow the original singleton Arc<DashMap> cache; ID keys are unitless. This does not make thread-local GPU contexts shareable.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:579, skia-canvas 3.0.8; function body unchanged.
  pub fn shared<'a>() -> &'a Arc<DashMap<usize, PageCache>>{
    CACHE.get_or_init(|| Arc::new(DashMap::new()))
  }

  /// Insert original empty cache under page ID; returns unit and preserves existing replacement/allocation behavior.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:583, skia-canvas 3.0.8; function body unchanged.
  pub fn add(id:usize){
    Self::shared().insert(id, PageCache::default());
  }

  /// Remove original cache entry for page ID; no return value. Original missing-ID unwrap panic and owner-thread destruction behavior are retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:587, skia-canvas 3.0.8; function body unchanged.
  pub fn drop(id:usize){
    Self::shared().remove(&id).unwrap();
  }

  /// Clone original image cache only when options and depth are valid; returns image/depth tuple or original (None,0) fallback.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:591, skia-canvas 3.0.8; function body unchanged.
  pub fn get(id:usize, opts:&ExportOptions, depth:usize) -> (Option<SkImage>, usize){
    Self::shared().get(&id).map(|cache|{
      match cache.is_valid(opts) && depth >= cache.depth{
        true => (cache.image.clone(), cache.depth),
        false => (None, 0)
      }
    })
    .unwrap_or((None, 0))
  }

  /// Update original cached owned image/options/depth only when invalid or newer; returns unit with unchanged Skia ownership rules.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:601, skia-canvas 3.0.8; function body unchanged.
  pub fn set(id:usize, image:SkImage, opts:&ExportOptions, depth:usize){
    Self::shared().get_mut(&id).map(|mut cache|{
      // save the bitmap if it's newer than the cached version, or is replacing an invaildated cache
      if !cache.is_valid(opts) || depth > cache.depth{
        *cache = Self{ image:Some(image), density:opts.density, matte:opts.matte, msaa:opts.msaa, depth}
      }
    });
  }

  /// Move original cached texture images to non-texture data before worker export when options are raster; invokes the owning thread's original context path.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:610, skia-canvas 3.0.8; function body unchanged.
  pub fn materialize(id:usize, engine:&RenderingEngine, options:&ExportOptions){
    Self::shared().get_mut(&id).map(|mut cache|{
      // nothing to be done if the image isn't currently in GPU memory
      // or if the options have changed (so the cache is invalid anyway)
      if let Some(ref img) = cache.image{
        if !cache.is_valid(options) || !img.is_texture_backed(){ return }
      }

      // otherwise move the image to main memory
      engine.with_direct_context(|context|
        cache.image = cache.image.as_ref().and_then(|img|
          img.make_non_texture_image(context)
        )
      );
    });
  }

  #[cfg(not(any(feature="metal", feature="vulkan")))]
  /// Read original image crop into borrowed destination pixels, with original CPU/GPU-context branch; returns optional success without moving the context.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:628, skia-canvas 3.0.8; function body unchanged.
  fn _blit<'a>( &self, _surface: &mut Surface, dst_info: &ImageInfo, src: IRect, pixels: &mut [u8], ) -> Option<bool>{
    self.image.as_ref().map(|image| image.read_pixels(
      &dst_info, pixels, dst_info.min_row_bytes(), (src.x(), src.y()), CachingHint::Allow
    ))
  }

  #[cfg(any(feature="metal", feature="vulkan"))]
  /// Read original image crop into borrowed destination pixels, with original CPU/GPU-context branch; returns optional success without moving the context.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:635, skia-canvas 3.0.8; function body unchanged.
  fn _blit<'a>( &self, surface: &mut Surface, dst_info: &ImageInfo, src: IRect, pixels: &mut [u8], ) -> Option<bool>{
    let context = &mut surface.direct_context();
    self.image.as_ref().map(|image| image.read_pixels_with_context(
      context, &dst_info, pixels, dst_info.min_row_bytes(), (src.x(), src.y()), CachingHint::Allow
    ))
  }

  /// Compare original density/matte/MSAA/image/raster policy; returns boolean, no allocation or new error.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:642, skia-canvas 3.0.8; function body unchanged.
  pub fn is_valid(&self, opts:&ExportOptions) -> bool{
    self.density == opts.density &&
    self.matte == opts.matte &&
    self.msaa == opts.msaa &&
    self.image.is_some() &&
    opts.is_raster()
  }
}

//
// Helpers
//


/// Borrow output writer and return original PDF document using quality (0-1), density (pixels/unit), producer and DPI; returned document cannot outlive writer.
/// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
/// Upstream: src/context/page.rs:667, skia-canvas 3.0.8; function body unchanged.
fn pdf_document(buffer:&mut impl std::io::Write, quality:f32, density:f32) -> Document<'_>{
  pdf::new_document(buffer, Some(&pdf::Metadata {
    producer: "Skia Canvas <https://skia-canvas.org>".to_string(),
    encoding_quality: Some((quality*100.0) as i32),
    raster_dpi: Some(density * 72.0),
    ..Default::default()
  }))
}

#[derive(Clone, Debug, PartialEq)]
pub struct ExportOptions{
  pub format: String,
  pub quality: f32,
  pub density: f32,
  pub outline: bool,
  pub matte: Option<Color>,
  pub msaa: Option<usize>,
  pub color_type: ColorType,
  pub color_space: ColorSpace,
  pub jpeg_downsample: bool,
  pub text_contrast: f32,
  pub text_gamma: f32,
}

impl Default for ExportOptions{
  /// Create the original default recording surface/page/cache/export-options value; no inputs, original field values and allocation behavior retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:692, skia-canvas 3.0.8; function body unchanged.
  fn default() -> Self {
    Self{
      format:"raw".to_string(), quality:0.92, density:1.0, matte:None,
      jpeg_downsample:false, text_contrast:0.0, text_gamma:1.4, msaa:None,
      color_type:ColorType::RGBA8888, color_space:ColorSpace::new_srgb(), outline:true,
    }
  }
}

impl ExportOptions{
  /// Create original surface text props: Unknown geometry, stored contrast/gamma; returns owned props without new validation/errors.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:702, skia-canvas 3.0.8; function body unchanged.
  pub fn surface_props(&self) -> SurfaceProps{
    SurfaceProps::new_with_text_properties(
      SurfacePropsFlags::default(),
      PixelGeometry::Unknown,
      self.text_contrast,
      self.text_gamma,
    )
  }

  /// Return original optional CONVERT_TEXT_TO_PATHS flag from outline boolean; no allocation/errors or ownership transfer.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:711, skia-canvas 3.0.8; function body unchanged.
  pub fn svg_flags(&self) -> Option<skia_safe::svg::canvas::Flags>{
    match self.outline{
      true => Some(Flags::CONVERT_TEXT_TO_PATHS),
      _ => None
    }
  }

  /// Select original requested/default sample count from supported list (4 if available, else last); returns usize or original String error; empty-list panic retained.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:718, skia-canvas 3.0.8; function body unchanged.
  pub fn msaa_from(&self, valid_msaa:&Vec<usize>) -> Result<usize, String>{
    let samples = self.msaa.unwrap_or_else(||
      if valid_msaa.contains(&4){ 4 } // 4x is a good default if available
      else{ *valid_msaa.last().unwrap() }
    );
    match valid_msaa.contains(&samples){
      true => Ok(samples),
      false => Err(format!("{}x MSAA not supported by GPU (options: {:?})", samples, valid_msaa))
    }
  }

  /// Report original non-PDF/non-SVG format policy; returns boolean, no allocation/errors or ownership transfer.
  /// Original return/error and thread/ownership behavior is retained; this mechanical move adds no Send/Sync.
  /// Upstream: src/context/page.rs:729, skia-canvas 3.0.8; function body unchanged.
  pub fn is_raster(&self) -> bool{
    self.format!="pdf" && self.format!="svg"
  }
}
