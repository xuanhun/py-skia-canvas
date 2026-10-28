//
// Font collection management
//
#![allow(non_snake_case)]
use std::sync::{OnceLock};
use std::cell::RefCell;
use std::fs;
use std::path::Path;
use std::collections::HashMap;

use skia_safe::{FontMgr, FontArguments, Typeface};
use skia_safe::font_style::{FontStyle, Slant};
use skia_safe::font_arguments::{VariationPosition, variation_position::Coordinate};
use skia_safe::textlayout::{FontCollection, TypefaceFontProvider, TextStyle};
use skia_safe::utils::OrderedFontMgr;

use crate::typography::{FontSpec, from_width, from_slant, typeface_wght_range};


thread_local!( static LIBRARY: OnceLock<RefCell<FontLibrary>> = const{ OnceLock::new() }; );

#[derive(PartialEq, Eq, Hash)]
pub struct CollectionKey{ families:String, weight:i32, slant:Slant }

impl CollectionKey{
  /// Construct original Canvas/Context/typesetter/style key from typed inputs; preserve default dimensions, style/font selection and operation order. Dimensions/coordinates are canvas units unless documented as pixels.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:36, skia-canvas 3.0.8; original rendering body retained.
  pub fn new(style: &TextStyle) -> Self {
    let families = style.font_families();
    let families = families.iter().collect::<Vec<&str>>().join(", ");
    let weight = *style.font_style().weight();
    let slant = style.font_style().slant();
    CollectionKey{ families, weight, slant }
  }
}

pub struct FontLibrary{
    mgr: FontMgr,
    collection: Option<FontCollection>,
    fonts: Vec<(Typeface, Option<String>)>,
    generics_cache: Vec<(Typeface, Option<String>)>,
    collection_cache: HashMap<CollectionKey, FontCollection>,
    collection_hinted: bool,
  }

impl FontLibrary{
  /// Invoke callback with original thread-local FontLibrary initialized once, including original fontconfig fallback detection; no global mutex or cross-thread migration.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:55, skia-canvas 3.0.8; original rendering body retained.
  pub fn with_shared<T, F>(f:F) -> T
    where F:FnOnce(&mut FontLibrary) -> T
  {
    LIBRARY.with(|lib_lock|{
      let shared_lib = lib_lock.get_or_init(||{
        // detect linux systems without a working fontconfig setup and use the fallback config in `lib/fonts` instead
        #[cfg(target_os = "linux")]
        {
          let has_config = fs::exists(Path::new("/etc/fonts/fonts.conf")).unwrap_or(false);
          let has_override = std::env::var_os("FONTCONFIG_PATH").is_some() || std::env::var_os("FONTCONFIG_FILE").is_some();
          if !(has_config || has_override){
            if let Some(mut fallback_config_path) = process_path::get_dylib_path(){
              fallback_config_path.set_file_name("fonts");
              std::env::set_var("FONTCONFIG_PATH", fallback_config_path);
            }
          }
        }

        RefCell::new(FontLibrary{
          mgr:FontMgr::default(), fonts:vec![], collection:None, collection_cache:HashMap::new(), collection_hinted:false, generics_cache:vec![]
        })
      });

      f(&mut shared_lib.borrow_mut())
    })
  }

  /// Lazily create/clone original FontCollection from original managers; returns owned Skia reference, no new fallback or error policy.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:82, skia-canvas 3.0.8; original rendering body retained.
  fn font_collection(&mut self) -> FontCollection{
    // lazily initialize font collection on first actual use
    if self.collection.is_none(){
      self.collection = Some(self.new_font_collection());
    };

    self.collection.as_ref().unwrap().clone()
  }

  /// Build original system/generic/user font collection and default family selection; preserve original font order and ownership.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:91, skia-canvas 3.0.8; original rendering body retained.
  fn new_font_collection(&mut self) -> FontCollection{
    let mut assets = TypefaceFontProvider::new();
    for (font, alias) in self.generics() {
      assets.register_typeface(font.clone(), alias.as_deref());
    }
    for (font, alias) in &self.fonts {
      assets.register_typeface(font.clone(), alias.as_deref());
    }

    let mut style_set = assets.match_family("system-ui");
    let default_fam = match style_set.count() > 1{
      true => style_set.match_style(FontStyle::default()),
      false => self.mgr.legacy_make_typeface(None, FontStyle::default())
    }.map(|f| f.family_name());

    let mut collection = FontCollection::new();
    collection.set_default_font_manager(self.mgr.clone(), default_fam.as_deref());
    collection.set_asset_font_manager(Some(assets.into()));
    collection
  }

  /// Borrow original cached generic-family mappings, using exactly the original platform stacks and style iteration; no substituted fonts are bundled.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:112, skia-canvas 3.0.8; original rendering body retained.
  fn generics(&mut self) -> &Vec<(Typeface, Option<String>)> {
    // set up generic font family mappings
    if self.generics_cache.is_empty(){
      let mut generics = vec![];
      let mut font_stacks = HashMap::new();
      font_stacks.insert("serif", vec!["Times", "Nimbus Roman", "Times New Roman", "Tinos", "Noto Serif", "Liberation Serif", "DejaVu Serif", "Source Serif Pro"]);
      font_stacks.insert("sans-serif", vec!["Avenir Next", "Avenir", "Helvetica Neue", "Helvetica", "Arial Nova", "Arial", "Inter", "Arimo", "Roboto", "Noto Sans", "Liberation Sans", "DejaVu Sans", "Nimbus Sans", "Clear Sans", "Lato", "Cantarell", "Arimo", "Ubuntu"]);
      font_stacks.insert("monospace", vec!["Cascadia Code", "Source Code Pro", "Menlo", "Consolas", "Monaco", "Liberation Mono", "Ubuntu Mono", "Roboto Mono", "Lucida Console", "Monaco", "Courier New", "Courier"]);
      font_stacks.insert("system-ui", vec!["Helvetica Neue", "Ubuntu", "Segoe UI", "Fira Sans", "Roboto", "DroidSans", "Tahoma"]);
      // see also: https://modernfontstacks.com | https://systemfontstack.com | https://www.ctrl.blog/entry/font-stack-text.html

      // Set up mappings for generic font names based on the first match found on the system
      for (generic_name, families) in font_stacks.into_iter() {
        let best_match = families.iter().find_map(|fam| {
          let mut style_set = self.mgr.match_family(fam);
          match style_set.count() > 0{
            true => Some(style_set),
            false => None
          }
        });

        let alias = Some(generic_name.to_string());
        if let Some(mut style_set) = best_match{
          for style_index in 0..style_set.count() {
            if let Some(font) = style_set.new_typeface(style_index){
              generics.push((font, alias.clone()));
            }
          }
        }
      }
      self.generics_cache = generics;
    }

    &self.generics_cache
  }

  /// Return original ordered union font manager with original system/generic/user fallback priority; retain original owned Skia references.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:148, skia-canvas 3.0.8; original rendering body retained.
  pub fn font_mgr(&mut self) -> FontMgr {
    // collect non-system fonts in a provider
    let mut dyn_mgr = TypefaceFontProvider::new();

    // add a sensible fallback as the first font so the default isn't just whatever is alphabetically first
    if let Some(fallback) = self.font_collection()
      .find_typefaces(&["system-ui", "sans-serif", "serif"], FontStyle::normal())
      .into_iter().nth(0){ dyn_mgr.register_typeface(fallback, None); }

    // add generic mappings & user-loaded fonts
    for (font, alias) in self.generics(){
      dyn_mgr.register_typeface(font.clone(), alias.as_deref());
    }
    for (font, alias) in &self.fonts{
      dyn_mgr.register_typeface(font.clone(), alias.as_deref());
    }

    // merge system & non-system fonts into single FontMgr
    let mut union_mgr = OrderedFontMgr::new();
    union_mgr.append(dyn_mgr); // generics & user-loaded fonts
    union_mgr.append(self.mgr.clone()); // system fonts
    union_mgr.into()
  }

  /// Return original sorted/deduplicated system and registered font family names as owned strings; no extra aliases or hidden substitutions.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:172, skia-canvas 3.0.8; original rendering body retained.
  pub fn families(&self) -> Vec<String>{
    let mut names:Vec<String> = self.mgr.family_names().collect();
    for (font, alias) in &self.fonts {
      names.push(match alias{
        Some(name) => name.clone(),
        None => font.family_name()
      })
    }
    names.sort();
    names.dedup();
    names
  }

  /// Return original weights/widths/slants, including original variable-weight metadata expansion and sort policy; no unit conversion or new font logic.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:185, skia-canvas 3.0.8; original rendering body retained.
  pub fn family_details(&self, family:&str) -> (Vec<f32>, Vec<String>, Vec<String>){
    // merge the system fonts and our dynamically added fonts into one list of FontStyles
    let mut dynamic = TypefaceFontProvider::new();
    for (font, alias) in &self.fonts{
      dynamic.register_typeface(font.clone(), alias.as_deref());
    }
    let std_mgr = self.mgr.clone();
    let dyn_mgr:FontMgr = dynamic.into();
    let mut std_set = std_mgr.match_family(family);
    let mut dyn_set = dyn_mgr.match_family(family);
    let std_styles = (0..std_set.count()).map(|i| std_set.style(i));
    let dyn_styles = (0..dyn_set.count()).map(|i| dyn_set.style(i));
    let all_styles = std_styles.chain(dyn_styles);

    // set up a collection to query for variable fonts who specify their weights
    // via the 'wght' axis rather than through distinct files with different FontStyles
    let mut var_fc = FontCollection::new();
    var_fc.set_default_font_manager(self.mgr.clone(), None);
    var_fc.set_asset_font_manager(Some(dyn_mgr));

    // pull style values out of each matching font
    let mut weights:Vec<i32> = vec![];
    let mut widths:Vec<String> = vec![];
    let mut styles:Vec<String> = vec![];
    all_styles.for_each(|(style, _name)| {
      widths.push(from_width(style.width()));
      styles.push(from_slant(style.slant()));
      weights.push(*style.weight());
      if let Some(font) = var_fc.find_typefaces(&[&family], style).first(){
        // for variable fonts, report all the 100× sizes they support within their wght range
        weights.append(&mut typeface_wght_range(font));
      }
    });

    // repackage collected values
    widths.sort_by(|a, b| a.replace("normal", "_").partial_cmp(&b.replace("normal", "_")).unwrap());
    widths.dedup();
    styles.sort_by(|a, b| a.replace("normal", "_").partial_cmp(&b.replace("normal", "_")).unwrap());
    styles.dedup();
    weights.sort_unstable();
    weights.dedup();
    let weights = weights.iter().map(|w| *w as f32 ).collect();
    (weights, widths, styles)
  }

  /// Register original owned Typeface/optional alias, replace same metadata entries and invalidate original collections; returns unit, original identity rules retained.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:230, skia-canvas 3.0.8; original rendering body retained.
  pub fn add_typeface(&mut self, font:Typeface, alias:Option<String>){
    // replace any previously added font with the same metadata/alias
    if let Some(idx) = self.fonts.iter().position(|(old_font, old_alias)|
      match alias.is_some(){
        true => old_alias == &alias,
        false => old_font.family_name() == font.family_name()
      } && old_font.font_style() == font.font_style()
    ){
      self.fonts.remove(idx);
    }

    // add the new typeface/alias and recreate the FontCollection to include it
    self.fonts.push((font, alias));
    self.collection = None;
    self.collection_cache.drain();
  }

  /// Clone/update original TextStyle only for usable FontSpec family matches; return optional style with original features, size and typeface selection.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:247, skia-canvas 3.0.8; original rendering body retained.
  pub fn update_style(&mut self, orig_style:&TextStyle, spec: &FontSpec) -> Option<TextStyle>{
    let mut style = orig_style.clone();

    // only update the style if a usable family name was specified
    self.font_collection()
      .find_typefaces(&spec.families, spec.style())
      .into_iter().nth(0)
      .map(|typeface| {
        style.set_typeface(typeface);
        style.set_font_families(&spec.families);
        style.set_font_style(spec.style());
        style.set_font_size(spec.size);
        style.reset_font_features();
        for (feat, val) in &spec.features{
          style.add_font_feature(feat, *val);
        }
        style
      })
  }

  /// Apply original hinting change/cache invalidation and return the same mutable library borrow; preserves original glyph-cache policy.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:267, skia-canvas 3.0.8; original rendering body retained.
  pub fn set_hinting(&mut self, hinting:bool) -> &mut Self{
    // skia's rasterizer cache doesn't take hinting into account, so manually invalidate if changed
    if hinting != self.collection_hinted{
      self.collection_hinted = hinting;
      self.collection_cache.iter_mut().for_each(|(_, fc)| fc.clear_caches());
      self.font_collection().clear_caches();
    }
    self
  }

  /// Return original cached/variable FontCollection for typed style, including original wght-minus-one instance rule; no algorithm or axis compensation change.
  /// Keep original owner-thread/Skia reference rules; no Send/Sync or Python thread-pool transfer is added.
  /// Upstream: src/font_library.rs:277, skia-canvas 3.0.8; original rendering body retained.
  pub fn fonts_for_style(&mut self, style: &TextStyle) -> FontCollection {
    let families = style.font_families();
    let families:Vec<&str> = families.iter().collect();
    let matches = self.font_collection().find_typefaces(&families, style.font_style());

    // if any of the matched typefaces is a variable font, create an instance that
    // matches the current weight settings and add it to a dynamic font mgr
    if matches.iter().any(|font| font.variation_design_parameters().is_some()){
      // memoize the generation of FontCollections for instanced variable fonts
      let key = CollectionKey::new(style);
      if let Some(collection) = self.collection_cache.get(&key){
        return collection.clone()
      }

      // collect any instantiated variable fonts in a TFP to be used as the 'dynamic'
      // font mgr (which is searched before the 'asset' or the 'default' mgr)
      let mut dynamic = TypefaceFontProvider::new();

      for font in matches.into_iter(){
        font.variation_design_parameters()
          .and_then(|params|{
            // find the weight axis
            params.into_iter().find(|param|{
              let chars = vec![param.tag.a(), param.tag.b(), param.tag.c(), param.tag.d()];
              let tag = String::from_utf8(chars).unwrap();
              tag == "wght"
            })
          }).and_then(|param|{
            // create an instance at the proper 'wght' for this weight
            // NB: currently setting the value to *one less* than what was requested
            //     to work around weird Skia behavior that returns something nonlinearly
            //     weighted in many cases (but not for ±1 of that value). This makes it so
            //     that n × 100 values will render correctly (and the bug will manifest at
            //     n × 100 + 1 instead)
            let weight = *style.font_style().weight() - 1;
            let value = (weight as f32).max(param.min).min(param.max);
            let coords = [ Coordinate { axis: param.tag, value } ];
            let v_pos = VariationPosition { coordinates: &coords };
            let args = FontArguments::new().set_variation_design_position(v_pos);
            font.clone_with_arguments(&args)
          }).map(|face|{
            // maintain the user-defined family alias (if applicable)
            let alias = self.fonts.iter().find_map(|(orig, alias)|
              if Typeface::equal(&font, orig){ alias.clone() }else{ None }
            );

            // add the font to the dynamic font mgr
            dynamic.register_typeface(face, alias.as_deref())
          });
      }

      let mut collection = self.new_font_collection();
      collection.set_dynamic_font_manager(Some(dynamic.into()));
      self.collection_cache.insert(key, collection.clone());
      collection
    }else{
      // if the matched font wasn't variable, then just return the standard collection
      self.font_collection()
    }
  }
}


impl FontLibrary {
  /// Decode original raw font bytes using this library's FontMgr; returns owned Typeface or None.
  /// Data is borrowed only for the call, kept on the original font-library owner thread.
  /// Upstream: src/font_library.rs:416 (addFamily), v3.0.8; same mgr.new_from_data call.
  pub fn new_from_data(&self, bytes:&[u8]) -> Option<Typeface> {
    self.mgr.new_from_data(bytes, None)
  }

  /// Clear original user fonts/collection/cache in the original order; return unit.
  /// Generic cache is deliberately retained as upstream; original owner thread only.
  /// Upstream: src/font_library.rs:443-445 (reset), v3.0.8; original three statements.
  pub fn reset(&mut self) {
    self.fonts.clear();
    self.collection = None;
    self.collection_cache.drain();
  }
}

/// Read/decode original font file, returning owned Typeface or original I/O/decode error.
/// filename is the caller's path string; no units or normalization. Windows WOFF/WOFF2
/// conversion and fallback are retained verbatim. Uses current thread's FontLibrary;
/// Typeface remains on its owner, no Send/Sync changes. Upstream: font_library.rs:381.
pub fn load_typeface(filename:&str) -> Result<Typeface,String> {
#[cfg(target_os = "windows")]
use allsorts::{
  binary::read::ReadScope,
  subset::whole_font,
  tables::FontTableProvider,
  woff::WoffFont,
  woff2::Woff2Font,
};

    let path = Path::new(&filename);
    let typeface = match fs::read(path){
      Err(why) => {
        return Err(format!("{}: \"{}\"", why, path.display()))
      },
      Ok(bytes) => {
        #[cfg(target_os = "windows")]
        let bytes = {
          fn decode_woff(bytes:&Vec<u8>) -> Option<Vec<u8>>{
            let woff = ReadScope::new(&bytes).read::<WoffFont>().ok()?;
            let tags = woff.table_tags()?;
            whole_font(&woff, &tags).ok()
          }

          fn decode_woff2(bytes:&Vec<u8>) -> Option<Vec<u8>>{
            let woff2 = ReadScope::new(&bytes).read::<Woff2Font>().ok()?;
            let tables = woff2.table_provider(0).ok()?;
            let tags = tables.table_tags()?;
            whole_font(&tables, &tags).ok()
          }

          match filename.to_ascii_lowercase(){
            name if name.ends_with(".woff") => decode_woff(&bytes),
            name if name.ends_with(".woff2") => decode_woff2(&bytes),
            _ => None
          }
        }.unwrap_or(bytes);

        FontLibrary::with_shared(|lib|
          lib.mgr.new_from_data(&bytes, None)
        )
      }
    };

    match typeface {
      Some(font) => Ok(font),
      None => {
        return Err(format!("Could not decode font data in {}", path.display()))
      }
    }
}

/// Return original (family, weight, style, width) values for a Typeface and optional alias.
/// Names are unitless strings, weight original numeric value. Returns owned metadata;
/// font stays on current owner, no callbacks/errors or matching policy changes.
/// Upstream: typography.rs:323 (typeface_details), JS allocations separated only.
pub fn typeface_metadata(font:&Typeface, alias:Option<String>) -> (String,f64,String,String) {
  let style = font.font_style();

  let family = match alias{
    Some(name) => name,
    None => font.family_name()
  };
  let weight = *style.weight() as f64;
  let slant = from_slant(style.slant());
  let width = from_width(style.width());

  (family,weight,slant,width)
}
