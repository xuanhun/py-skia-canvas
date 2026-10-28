//! Node-only callback/channel adapter; all native window/event/render algorithms in core.
use neon::prelude::*;
use serde_json::Value;
use std::{sync::{Arc,OnceLock},iter::zip};
use crate::context::{page::Page,BoxedContext2D};
use super::{window_mgr::WindowManager,window::WindowSpec};
pub use canvas_core::gui::app::LoopMode;
static RENDER_CALLBACK:OnceLock<Arc<Root<JsFunction>>>=OnceLock::new();
pub struct App;
impl App{
    pub fn register(callback:Root<JsFunction>){
        RENDER_CALLBACK.get_or_init(|| Arc::new(callback));
    }
    /// Forward original set_mode; same units/errors, owner loop only, no native transfer.
    pub fn set_mode(mode:LoopMode){canvas_core::gui::app::App::set_mode(mode)}
    /// Forward original set_fps; same units/errors, owner loop only, no native transfer.
    pub fn set_fps(fps:f32){canvas_core::gui::app::App::set_fps(fps)}
    /// Forward original open_window; same units/errors, owner loop only, no native transfer.
    pub fn open_window(spec:WindowSpec, page:Page){canvas_core::gui::app::App::open_window(spec,page)}
    /// Forward original close_window; same units/errors, owner loop only, no native transfer.
    pub fn close_window(token:u32){canvas_core::gui::app::App::close_window(token)}
    /// Forward original quit; same units/errors, owner loop only, no native transfer.
    pub fn quit(){canvas_core::gui::app::App::quit()}
    pub fn activate(channel:Channel, deferred:neon::types::Deferred){
        std::thread::spawn(move || {
            loop{
                // schedule a callback on the node event loop
                let keep_running = channel.send(move |mut cx| {

                    // define closure to relay events to js and receive canvas updates in return
                    let dispatch = |payload:Value, windows:Option<&mut WindowManager>| -> NeonResult<()>{
                        App::dispatch_events(&mut cx, payload, windows)
                    };

                    // run the winit event loop (either once or until all windows are closed depending on mode)
                    canvas_core::gui::app::App::activate(dispatch)
                }).join();

                match keep_running{
                    Ok(true) => continue,
                    _ => break
                }
            }

            // resolve the promise
            deferred.settle_with(&channel, move |mut cx| Ok(cx.undefined()) );
        });
    }
    fn dispatch_events(cx:&mut TaskContext, events:Value, window_mgr:Option<&mut WindowManager>) -> NeonResult<()>{
        // window_mgr is only present if it's time to collect updated canvas contents from js
        let is_render = window_mgr.is_some();

        // js callback is passed render flag & json-encoded event queue
        let mut call = match RENDER_CALLBACK.get(){
            None => return Ok(()),
            Some(callback)=> callback.to_inner(cx).call_with(cx),
        };
        call.arg(cx.boolean(is_render))
            .arg(cx.string(events.to_string()));

        match window_mgr{
            None => call.exec(cx)?, // if this is just a UI-event delivery, fire & forget

            Some(window_mgr) => {
                // for a full roundtrip, first pass events to js
                let response = call.apply::<JsValue, _>(cx)?
                    .downcast::<JsArray, _>(cx).or_throw(cx)?
                    .to_vec(cx)?;

                // then unpack the returned window specs & contexts
                let specs_json = response[0].downcast::<JsString, _>(cx).or_throw(cx)?.value(cx);
                let specs:Vec<WindowSpec> = serde_json::from_str(&specs_json)
                    .or_else(|err| cx.throw_error(format!("Malformed response from window event handler: {}", err)) )?;

                let contexts = response[1].downcast::<JsArray, _>(cx).or_throw(cx)?.to_vec(cx)?;
                let pages = contexts.iter().map(|boxed|
                    boxed.downcast::<BoxedContext2D, _>(cx).ok()
                        .map(|ctx| ctx.borrow().get_page())
                );

                // update each window with its new state & content
                zip(specs, pages)
                    .filter_map(|(spec, page)| page.map(|page| (spec, page) ))
                    .for_each(|(spec, page)| window_mgr.update_window(spec, page) );
            }
        };

        Ok(())
    }
}
