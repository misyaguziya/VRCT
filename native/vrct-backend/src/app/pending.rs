//! Handlers not ported yet (this file goes when the last one is): 501 so the contract test lists them.
use super::App;
use crate::ipc::Reply;
use serde_json::{json, Value};

macro_rules! pending {
    ($($name:ident),* $(,)?) => {$(
        pub fn $name(_: &App, _: Option<Value>) -> anyhow::Result<Reply> {
            Ok(Reply { status: 501, result: json!(stringify!($name)) })
        }
    )*};
}

pending! {
    get_overlay_vr_launcher_hand,
    get_overlay_vr_panel_anchor,
    get_overlay_vr_panel_opacity,
    get_vr_panel_layout,
    recall_vr_panel_log,
    reset_vr_launcher,
    send_text_overlay,
    set_disable_overlay_large_log,
    set_disable_overlay_small_log,
    set_disable_overlay_vr_launcher_auto_hide,
    set_disable_overlay_vr_panel,
    set_disable_overlay_vr_panel_locked,
    set_disable_overlay_vr_tooltip,
    set_enable_overlay_large_log,
    set_enable_overlay_small_log,
    set_enable_overlay_vr_launcher_auto_hide,
    set_enable_overlay_vr_panel,
    set_enable_overlay_vr_panel_locked,
    set_enable_overlay_vr_tooltip,
    set_overlay_large_log_settings,
    set_overlay_small_log_settings,
    set_overlay_vr_launcher_hand,
    set_overlay_vr_panel_anchor,
    set_overlay_vr_panel_font_size,
    set_overlay_vr_panel_opacity,
    set_vr_panel_layout_rendered,
    set_vr_panel_tooltip,
    set_vr_panel_windows,
}
