//! The recording devices now (device_manager.update with the Rust devices): the microphones by
//! host ("Windows WASAPI"), the speakers' loopbacks and the defaults, as one snapshot. With none,
//! the lists hold "NoHost" / "NoDevice" as in Python.
use crate::config::{DeviceLists, RUST_HOST_NAME};
use std::sync::{Mutex, OnceLock};

pub const NO_HOST: &str = "NoHost";
pub const NO_DEVICE: &str = "NoDevice";

#[derive(Clone, Debug, PartialEq)]
pub struct Snapshot {
    /// host -> its microphones, in order
    pub mic: Vec<(String, Vec<String>)>,
    pub default_mic: (String, String),
    pub speaker: Vec<String>,
    pub default_speaker: String,
}

impl Snapshot {
    fn empty() -> Self {
        Self {
            mic: vec![(NO_HOST.into(), vec![NO_DEVICE.into()])],
            default_mic: (NO_HOST.into(), NO_DEVICE.into()),
            speaker: vec![NO_DEVICE.into()],
            default_speaker: NO_DEVICE.into(),
        }
    }

    /// The microphones of `host` (getMicDevices().get(host))
    pub fn mic_devices(&self, host: &str) -> Option<&Vec<String>> {
        self.mic.iter().find(|(h, _)| h == host).map(|(_, d)| d)
    }

    pub fn lists(&self) -> DeviceLists {
        DeviceLists { mic: self.mic.clone(), speaker: self.speaker.clone() }
    }
}

fn current() -> &'static Mutex<Snapshot> {
    static SNAPSHOT: OnceLock<Mutex<Snapshot>> = OnceLock::new();
    SNAPSHOT.get_or_init(|| Mutex::new(read()))
}

fn read() -> Snapshot {
    let mut s = Snapshot::empty();
    match vrct_audio::devices::list() {
        Ok(d) => {
            let host = RUST_HOST_NAME.to_string();
            if let Some(default) = d.default_input.filter(|n| d.inputs.iter().any(|i| &i.name == n)) {
                s.default_mic = (host.clone(), default);
            }
            if !d.inputs.is_empty() {
                s.mic = vec![(host, d.inputs.into_iter().map(|i| i.name).collect())];
            }
            if let Some(default) = d.default_loopback.filter(|n| d.loopbacks.iter().any(|i| &i.name == n)) {
                s.default_speaker = default;
            }
            if !d.loopbacks.is_empty() {
                s.speaker = d.loopbacks.into_iter().map(|i| i.name).collect();
            }
        }
        Err(e) => crate::logs::error("list devices", &e),
    }
    s
}

pub fn snapshot() -> Snapshot {
    current().lock().unwrap().clone()
}

/// update(): the devices read again
pub fn update() -> Snapshot {
    let s = read();
    *current().lock().unwrap() = s.clone();
    s
}
