use serde_json::json;
use serde_json::{Map, Value};
use winit::{
    dpi::{LogicalSize, LogicalPosition},
    event_loop::ActiveEventLoop,
    event::WindowEvent,
    window::WindowId,
};

use crate::utils::css_to_color;
use crate::context::page::Page;
use super::window::{Window, WindowSpec};

#[derive(Default)]
pub struct WindowManager {
    windows: Vec<Window>,
    last: Option<LogicalPosition<f32>>,
}

impl WindowManager {

    /// Execute original add window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:22, skia-canvas 3.0.8; body retained.
    pub fn add(&mut self, event_loop:&ActiveEventLoop, spec:WindowSpec, page:Page) {
        let mut window = Window::new(event_loop, spec, &page);

        // make sure mouse events use canvas-relative coordinates (in case win size doesn't match)
        window.update_fit();

        // cascade the windows based on the position of the most recently opened
        let dpr = window.handle.scale_factor();
        if let Ok(auto_loc) = window.handle.outer_position().map(|pt| pt.to_logical::<f32>(dpr)){
            if let Ok(inset) = window.handle.inner_position().map(|pt| pt.to_logical::<f32>(dpr)){
                let delta = inset.y - auto_loc.y;
                let reference = self.last.unwrap_or(auto_loc);
                let (left, top) = ( window.spec.left.unwrap_or(reference.x), window.spec.top.unwrap_or(reference.y) );

                window.handle.set_outer_position(LogicalPosition::new(left, top));
                window.handle.set_visible(true);

                window.spec.left = Some(left);
                window.spec.top = Some(top);
                self.last = Some(LogicalPosition::new(left + delta, top + delta));
            }
        }

        self.windows.push( window );
    }

    /// Execute original remove window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:48, skia-canvas 3.0.8; body retained.
    pub fn remove(&mut self, window_id:&WindowId){
        self.windows.retain(|win| win.id() != *window_id);
    }

    /// Execute original remove_by_token window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:52, skia-canvas 3.0.8; body retained.
    pub fn remove_by_token(&mut self, token:u32){
        self.windows.retain(|win| win.spec.id != token);
    }

    /// Execute original remove_all window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:56, skia-canvas 3.0.8; body retained.
    pub fn remove_all(&mut self){
        self.windows.clear();
    }
    /// Execute original update_window window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:59, skia-canvas 3.0.8; body retained.
    pub fn update_window(&mut self, mut spec:WindowSpec, page:Page){
        if let Some(win) = self.windows.iter_mut().find(|win| win.spec.id == spec.id){
            if spec.width != win.spec.width || spec.height != win.spec.height {
                win.set_size(LogicalSize::new(spec.width as u32, spec.height as u32));
            }

            if let (Some(left), Some(top)) = (spec.left, spec.top){
                if spec.left != win.spec.left || spec.top != win.spec.top {
                    win.set_position(LogicalPosition::new(left as i32, top as i32));
                }
            }

            if spec.title != win.spec.title {
                win.set_title(&spec.title);
            }

            if spec.visible != win.spec.visible {
                win.set_visible(spec.visible);
            }

            if spec.fullscreen != win.spec.fullscreen {
                win.set_fullscreen(spec.fullscreen);
                win.sieve.go_fullscreen(spec.fullscreen);
            }

            if spec.resizable != win.spec.resizable {
                win.set_resizable(spec.resizable);
            }

            if spec.borderless != win.spec.borderless {
                win.set_borderless(spec.borderless);
            }

            if spec.cursor != win.spec.cursor {
                win.set_cursor(&spec.cursor);
            }

            if spec.fit != win.spec.fit {
                win.set_fit(spec.fit);
            }

            if spec.background != win.spec.background {
                if let Some(color) = css_to_color(&spec.background) {
                    win.set_background(color);
                }else{
                    spec.background = win.spec.background.clone();
                }
            }

            win.set_page(page);

            win.spec = spec;
        }
    }

    /// Execute original find window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:114, skia-canvas 3.0.8; body retained.
    pub fn find<F>(&mut self, id:&WindowId, f:F) where F:FnMut(&mut Window){
        self.windows.iter_mut().find(|win| win.id() == *id).map(f);
    }

    /// Execute original has_ui_changes window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:118, skia-canvas 3.0.8; body retained.
    pub fn has_ui_changes(&self) -> bool {
        self.windows.iter().any(|win| !win.sieve.is_empty() )
    }

    /// Collect original UI events and window state; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:122, skia-canvas 3.0.8; body retained.
    pub fn get_ui_changes(&mut self) -> Value {
        let mut ui = Map::new();
        let mut state = Map::new();
        self.windows.iter_mut().for_each(|win|{
            // collect new UI events
            if !win.sieve.is_empty(){
                ui.insert(win.spec.id.to_string(), win.sieve.collect());
            }
            state.insert(win.spec.id.to_string(), json!(win.spec));

            // rerender frame from vector sources after using bitmap cache during resize
            win.redraw_if_resized();
        });
        json!({ "ui": ui, "state": state })
    }

    /// Collect original logical pixel window origins; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:138, skia-canvas 3.0.8; body retained.
    pub fn get_geometry(&mut self) -> Value {
        let mut positions = Map::new();
        self.windows.iter_mut().for_each(|win|{
            positions.insert(win.spec.id.to_string(), json!({"left":win.spec.left, "top":win.spec.top}));
        });
        json!({"geom":positions})
    }

    /// Execute original is_empty window/event operation; original arguments and return type retained.
    /// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.
    /// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.
    /// Upstream src/gui/window_mgr.rs:146, skia-canvas 3.0.8; body retained.
    pub fn is_empty(&self) -> bool {
        self.windows.len() == 0
    }
}



