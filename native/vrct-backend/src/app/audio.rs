//! The microphone and the speaker (controller.py / model.py's sessions): recording, energy,
//! the device lists and VRChat's mute sync.
use super::{current, App};
use crate::errors;
use crate::ipc::Reply;
use crate::osc::OscEvent;
use anyhow::{bail, Result};
use serde_json::{json, Value};

type Data = Option<Value>;

/// changeMicTranscriptStatus: the microphone pauses while VRChat mutes it (with mute sync on)
pub fn change_mic_transcript_status(_app: &App) -> Result<()> {
    bail!("P4-3b: the microphone session is not ported yet")
}

/// setMuteSelfStatus: VRChat's MuteSelf now
pub fn read_mute_self(app: &App) {
    *app.model.mic_mute_status.lock().unwrap() = app.model.osc.mute_self();
}

pub fn set_enable_vrc_mic_mute_sync(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("VRC_MIC_MUTE_SYNC") == json!(false) {
        if !app.model.osc.is_osc_query_enabled() {
            return Ok(errors::error("VRC_MIC_MUTE_SYNC_OSC_DISABLED", app.config.get("VRC_MIC_MUTE_SYNC")));
        }
        app.config.set("VRC_MIC_MUTE_SYNC", json!(true))?;
        read_mute_self(app);
        change_mic_transcript_status(app)?;
    }
    current(app, "VRC_MIC_MUTE_SYNC")
}

pub fn set_disable_vrc_mic_mute_sync(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("VRC_MIC_MUTE_SYNC") {
        app.config.set("VRC_MIC_MUTE_SYNC", json!(false))?;
        change_mic_transcript_status(app)?;
    }
    current(app, "VRC_MIC_MUTE_SYNC")
}

/// changeHandlerMute / changeHandlerAvatar (from the OSC receive thread: nothing that waits here)
pub fn on_osc_event(_app: &App, _event: OscEvent) {
    // P4-3b
}

/// _initVrcMicMuteSync: MuteSelf when VRChat is already up (else on its avatar change)
pub fn init_vrc_mic_mute_sync(app: &App) -> Result<()> {
    read_mute_self(app);
    if app.model.mic_mute_status.lock().unwrap().is_some() {
        change_mic_transcript_status(app)?;
    }
    Ok(())
}

/// The device manager's lists and the automatic selection (init)
pub fn init_devices(_app: &App) -> Result<()> {
    // P4-3b
    Ok(())
}

/// Controller.shutdown's audio part: the sessions stopped
pub fn shutdown(_app: &App) {
    // P4-3b
}
