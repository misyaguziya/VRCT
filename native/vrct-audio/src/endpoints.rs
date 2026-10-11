//! Audio endpoint changes and activity, in place of pycaw / comtypes (device_manager.Client and
//! active_endpoint_tracker.py).
//!
//! `DeviceWatcher` calls back when an endpoint is added, removed, changes state or the default
//! changes (IMMNotificationClient). `ActiveEndpointTracker` polls every output's peak level
//! (IAudioMeterInformation) every 250 ms and names the one that is playing, with the same window and
//! hysteresis as the Python version (`Selector`).
use std::collections::VecDeque;
use std::sync::mpsc;
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};
use windows::core::{implement, PCWSTR};
use windows::Win32::Devices::FunctionDiscovery::PKEY_Device_FriendlyName;
use windows::Win32::Foundation::PROPERTYKEY;
use windows::Win32::Media::Audio::Endpoints::IAudioMeterInformation;
use windows::Win32::Media::Audio::{
    eCapture, eRender, EDataFlow, ERole, IMMDevice, IMMDeviceEnumerator, IMMNotificationClient, IMMNotificationClient_Impl,
    MMDeviceEnumerator, DEVICE_STATE, DEVICE_STATE_ACTIVE,
};
use windows::Win32::System::Com::{CoCreateInstance, CoInitializeEx, CoUninitialize, CLSCTX_ALL, COINIT_MULTITHREADED, STGM_READ};

/// The peaks seen in the last WINDOW_SEC decide; another endpoint takes over only after being
/// SWITCH_RATIO times louder for SWITCH_HOLD_SEC; below SILENT_THRESHOLD counts as silent
pub const POLL_INTERVAL: Duration = Duration::from_millis(250);
const WINDOW_SEC: f64 = 3.0;
const SILENT_THRESHOLD: f64 = 0.001;
const SWITCH_RATIO: f64 = 2.0;
const SWITCH_HOLD_SEC: f64 = 1.0;

/// _update_history / _decide_selected: the selection from peak levels over time (no COM)
#[derive(Default)]
pub struct Selector {
    /// per endpoint name, in the order first seen: (time, peak)
    history: Vec<(String, VecDeque<(f64, f64)>)>,
    switch_candidate: Option<(String, f64)>,
    pub current: Option<String>,
}

impl Selector {
    /// `peaks` in the order the endpoints were listed; `now` in seconds
    pub fn update(&mut self, peaks: &[(String, f64)], now: f64) -> Option<String> {
        for (name, peak) in peaks {
            let i = match self.history.iter().position(|(n, _)| n == name) {
                Some(i) => i,
                None => {
                    self.history.push((name.clone(), VecDeque::new()));
                    self.history.len() - 1
                }
            };
            let history = &mut self.history[i].1;
            history.push_back((now, *peak));
            while history.front().is_some_and(|(t, _)| *t < now - WINDOW_SEC) {
                history.pop_front();
            }
        }
        self.history.retain(|(name, _)| peaks.iter().any(|(n, _)| n == name));
        let selected = self.decide(now);
        self.current = selected.clone();
        selected
    }

    fn decide(&mut self, now: f64) -> Option<String> {
        let rolling: Vec<(&str, f64)> =
            self.history.iter().map(|(n, h)| (n.as_str(), h.iter().map(|p| p.1).fold(0.0, f64::max))).collect();
        let selected = self.current.clone();
        // the first loudest, as Python's max()
        let mut best: Option<(&str, f64)> = None;
        for &(name, peak) in &rolling {
            if peak > SILENT_THRESHOLD && best.is_none_or(|b| peak > b.1) {
                best = Some((name, peak));
            }
        }
        let Some((best_name, best_peak)) = best else {
            // all silent: keep the selection
            self.switch_candidate = None;
            return selected;
        };
        let current_peak = selected.as_deref().and_then(|s| rolling.iter().find(|(n, _)| *n == s)).map(|r| r.1);
        let Some(current_peak) = current_peak else {
            // nothing selected, or the selected one is gone
            self.switch_candidate = None;
            return Some(best_name.into());
        };
        if selected.as_deref() == Some(best_name) {
            self.switch_candidate = None;
            return selected;
        }
        if best_peak >= current_peak * SWITCH_RATIO {
            match &self.switch_candidate {
                Some((name, since)) if name == best_name => {
                    if now - since >= SWITCH_HOLD_SEC {
                        self.switch_candidate = None;
                        return Some(best_name.into());
                    }
                }
                _ => self.switch_candidate = Some((best_name.into(), now)),
            }
            return selected;
        }
        self.switch_candidate = None;
        selected
    }
}

/// COM for the calling thread (multithreaded apartment), undone on drop
struct Com;

impl Com {
    fn init() -> Result<Self, String> {
        unsafe { CoInitializeEx(None, COINIT_MULTITHREADED) }.ok().map_err(|e| e.to_string())?;
        Ok(Com)
    }
}

impl Drop for Com {
    fn drop(&mut self) {
        unsafe { CoUninitialize() };
    }
}

fn enumerator() -> windows::core::Result<IMMDeviceEnumerator> {
    unsafe { CoCreateInstance(&MMDeviceEnumerator, None, CLSCTX_ALL) }
}

fn friendly_name(device: &IMMDevice) -> windows::core::Result<String> {
    let store = unsafe { device.OpenPropertyStore(STGM_READ)? };
    let value = unsafe { store.GetValue(&PKEY_Device_FriendlyName)? };
    Ok(value.to_string())
}

#[implement(IMMNotificationClient)]
struct Notifications(Arc<dyn Fn() + Send + Sync>);

impl IMMNotificationClient_Impl for Notifications_Impl {
    fn OnDeviceStateChanged(&self, _id: &PCWSTR, _state: DEVICE_STATE) -> windows::core::Result<()> {
        (self.0)();
        Ok(())
    }

    fn OnDeviceAdded(&self, _id: &PCWSTR) -> windows::core::Result<()> {
        (self.0)();
        Ok(())
    }

    fn OnDeviceRemoved(&self, _id: &PCWSTR) -> windows::core::Result<()> {
        (self.0)();
        Ok(())
    }

    fn OnDefaultDeviceChanged(&self, _flow: EDataFlow, _role: ERole, _id: &PCWSTR) -> windows::core::Result<()> {
        (self.0)();
        Ok(())
    }

    fn OnPropertyValueChanged(&self, _id: &PCWSTR, _key: &PROPERTYKEY) -> windows::core::Result<()> {
        Ok(())
    }
}

/// Calls `on_change` (from a COM thread: keep it short) while it lives
pub struct DeviceWatcher {
    stop: Option<mpsc::Sender<()>>,
    thread: Option<std::thread::JoinHandle<()>>,
}

impl DeviceWatcher {
    pub fn start(on_change: impl Fn() + Send + Sync + 'static) -> Result<Self, String> {
        let (ready_tx, ready_rx) = mpsc::channel();
        let (stop_tx, stop_rx) = mpsc::channel::<()>();
        let on_change: Arc<dyn Fn() + Send + Sync> = Arc::new(on_change);
        let thread = std::thread::Builder::new().name("audio-device-watcher".into()).spawn(move || {
            let registered = (|| -> Result<(Com, IMMDeviceEnumerator, IMMNotificationClient), String> {
                let com = Com::init()?;
                let enumerator = enumerator().map_err(|e| e.to_string())?;
                let client: IMMNotificationClient = Notifications(on_change).into();
                unsafe { enumerator.RegisterEndpointNotificationCallback(&client) }.map_err(|e| e.to_string())?;
                Ok((com, enumerator, client))
            })();
            match registered {
                Ok((com, enumerator, client)) => {
                    let _ = ready_tx.send(Ok(()));
                    let _ = stop_rx.recv();
                    let _ = unsafe { enumerator.UnregisterEndpointNotificationCallback(&client) };
                    drop((client, enumerator, com));
                }
                Err(e) => {
                    let _ = ready_tx.send(Err(e));
                }
            }
        }).map_err(|e| e.to_string())?;
        ready_rx.recv().map_err(|_| "the watcher thread ended".to_string())??;
        Ok(Self { stop: Some(stop_tx), thread: Some(thread) })
    }
}

impl Drop for DeviceWatcher {
    fn drop(&mut self) {
        drop(self.stop.take());
        if let Some(t) = self.thread.take() {
            let _ = t.join();
        }
    }
}

#[derive(Clone, Copy, PartialEq)]
pub enum Flow {
    Render,
    Capture,
}

struct TrackerState {
    stop: bool,
    paused: bool,
    current: Option<String>,
}

/// Polls the endpoints of `flow` and calls `on_change` with the friendly name of the one playing
/// (None when nothing has played yet), from its own thread
pub struct ActiveEndpointTracker {
    state: Arc<(Mutex<TrackerState>, Condvar)>,
    thread: Option<std::thread::JoinHandle<()>>,
}

/// The peak of every active endpoint, with the meters kept between polls (one Activate per endpoint)
fn collect_peaks(enumerator: &IMMDeviceEnumerator, flow: Flow,
                 meters: &mut Vec<(String, String, IAudioMeterInformation)>) -> windows::core::Result<Vec<(String, f64)>> {
    let collection = unsafe { enumerator.EnumAudioEndpoints(if flow == Flow::Render { eRender } else { eCapture }, DEVICE_STATE_ACTIVE)? };
    let count = unsafe { collection.GetCount()? };
    let mut devices = vec![];
    for i in 0..count {
        let Ok(device) = (unsafe { collection.Item(i) }) else { continue };
        let Ok(id) = (unsafe { device.GetId() }) else { continue };
        let id = unsafe { id.to_string() }.unwrap_or_default();
        devices.push((id, device));
    }
    meters.retain(|(id, _, _)| devices.iter().any(|(d, _)| d == id));
    let mut peaks = vec![];
    for (id, device) in devices {
        let i = match meters.iter().position(|(m, _, _)| *m == id) {
            Some(i) => i,
            None => {
                let meter: windows::core::Result<IAudioMeterInformation> = unsafe { device.Activate(CLSCTX_ALL, None) };
                let (Ok(meter), Ok(name)) = (meter, friendly_name(&device)) else { continue };
                meters.push((id.clone(), name, meter));
                meters.len() - 1
            }
        };
        match unsafe { meters[i].2.GetPeakValue() } {
            Ok(p) => peaks.push((meters[i].1.clone(), p as f64)),
            // try again next time
            Err(_) => {
                meters.remove(i);
            }
        }
    }
    Ok(peaks)
}

impl ActiveEndpointTracker {
    pub fn start(flow: Flow, on_change: impl Fn(Option<String>) + Send + 'static) -> Self {
        let state = Arc::new((Mutex::new(TrackerState { stop: false, paused: false, current: None }), Condvar::new()));
        let s = state.clone();
        let thread = std::thread::Builder::new().name("active-endpoint-tracker".into()).spawn(move || {
            let Ok(_com) = Com::init() else { return };
            let Ok(enumerator) = enumerator() else { return };
            let started = Instant::now();
            let mut meters = vec![];
            let mut selector = Selector::default();
            let (lock, wake) = &*s;
            loop {
                {
                    let mut st = lock.lock().unwrap();
                    while st.paused && !st.stop {
                        st = wake.wait(st).unwrap();
                    }
                    if st.stop {
                        break;
                    }
                }
                if let Ok(peaks) = collect_peaks(&enumerator, flow, &mut meters) {
                    let before = selector.current.clone();
                    let selected = selector.update(&peaks, started.elapsed().as_secs_f64());
                    lock.lock().unwrap().current = selected.clone();
                    if selected != before {
                        on_change(selected);
                    }
                }
                let st = lock.lock().unwrap();
                let (st, _) = wake.wait_timeout_while(st, POLL_INTERVAL, |st| !st.stop).unwrap();
                if st.stop {
                    break;
                }
            }
        }).ok();
        Self { state, thread }
    }

    pub fn active_endpoint_name(&self) -> Option<String> {
        self.state.0.lock().unwrap().current.clone()
    }

    /// Polling waits (a recorder is being opened or closed)
    pub fn pause(&self) {
        self.state.0.lock().unwrap().paused = true;
    }

    pub fn resume(&self) {
        self.state.0.lock().unwrap().paused = false;
        self.state.1.notify_all();
    }
}

impl Drop for ActiveEndpointTracker {
    fn drop(&mut self) {
        self.state.0.lock().unwrap().stop = true;
        self.state.1.notify_all();
        if let Some(t) = self.thread.take() {
            let _ = t.join();
        }
    }
}
