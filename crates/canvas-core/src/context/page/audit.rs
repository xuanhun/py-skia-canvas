//! Read-only lifecycle evidence for the original private PageCache, never rendering policy.
use super::{PageCache,PageSequence,ExportOptions};
/// Count selected valid cached images and texture-backed images before/after original
/// materialize. Returns unitless (images,textures), borrowed on snapshot owner, no image
/// clones/callbacks/errors. Source page.rs:PageCache::is_valid/image, diagnostic only.
pub fn selected(pages:&PageSequence,options:&ExportOptions)->(usize,usize){
    let mut images=0;let mut textures=0;
    for page in &pages.pages{if let Some(cache)=PageCache::shared().get(&page.id){if cache.is_valid(options){if let Some(image)=&cache.image{images+=1;textures+=usize::from(image.is_texture_backed());}}}}
    (images,textures)
}
