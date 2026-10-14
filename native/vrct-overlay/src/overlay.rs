//! VRCT's SteamVR overlays (models/overlay/overlay.py: Overlay): the log overlays ("small" /
//! "large": an image each, its colour, opacity, width, position following the headset, a hand or
//! fixed in the room, and the fade after the display duration) and the VR UI ("panel" the log
//! window, "launcher" the band on the wrist, "popup" the temporary window: regions of one captured
//! window, see panel.rs; grabbing, resizing, pointing, see vr_ui.rs).
//!
//! One thread owns everything OpenVR / D3D11 (callers send commands, applied at once): it waits
//! for SteamVR, joins the shared session as a background app, runs at 16 fps (60 while grabbing,
//! 30 while pointing at the VR UI) and closes everything when SteamVR quits, then waits for it
//! again. Stopping hands the state back, so a restart goes on from it.
//!
//! Images go to SteamVR as D3D11 textures (SetOverlayTexture, then Flush: SteamVR's copy is queued
//! on this device), not SetOverlayRaw, which keeps failing after ~190 calls (overlay.py).
use crate::image::Image;
use crate::layout::{self, Layout, PointerKind, Region, Tooltip, TooltipShown};
use crate::math::{position_transform, to_hmd, Mat34, Mat4, Tracker};
use crate::pose;
use crate::vr::{VrOverlay, VrRenderModels, VrSystem};
use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use vrct_openvr::{ApplicationType, Session, Texture};
use windows::core::Interface;
use windows::Win32::Graphics::Direct3D::D3D_DRIVER_TYPE_UNKNOWN;
use windows::Win32::Graphics::Direct3D11::{
    D3D11CreateDevice, ID3D11Device, ID3D11DeviceContext, ID3D11Texture2D, D3D11_BIND_SHADER_RESOURCE,
    D3D11_CREATE_DEVICE_FLAG, D3D11_SDK_VERSION, D3D11_SUBRESOURCE_DATA, D3D11_TEXTURE2D_DESC, D3D11_USAGE_DEFAULT,
};
use windows::Win32::Graphics::Dxgi::Common::{DXGI_FORMAT_R8G8B8A8_UNORM, DXGI_SAMPLE_DESC};
use windows::Win32::Graphics::Dxgi::{CreateDXGIFactory1, IDXGIFactory1};

const STEAMVR_POLL: Duration = Duration::from_secs(10);
const STOP_WAIT: Duration = Duration::from_secs(5);
pub(crate) const COLOR_NORMAL: [f32; 3] = [1.0, 1.0, 1.0];

/// A size's settings (OVERLAY_SMALL_LOG_SETTINGS and the like)
#[derive(Clone, Debug, PartialEq)]
pub struct Settings {
    /// x, y, z, x rotation, y rotation, z rotation
    pub position: [f64; 6],
    pub tracker: String,
    pub opacity: f64,
    /// the width in metres
    pub ui_scaling: f64,
    pub display_duration: f64,
    /// 0: never fades
    pub fadeout_duration: f64,
    /// the log window's size (logical px; "width" / "height" of OVERLAY_VR_PANEL_SETTINGS)
    pub panel_size: Option<(u32, u32)>,
}

/// The launcher's intro (only when the VR UI is turned on): Pending until it can first show,
/// Playing while it flies from in front of the eyes to the wrist
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Intro {
    Idle,
    Pending,
    Playing,
}

impl Intro {
    pub fn name(self) -> &'static str {
        match self {
            Intro::Idle => "idle",
            Intro::Pending => "pending",
            Intro::Playing => "playing",
        }
    }
}

/// What the overlay tells the app (overlay.py's callbacks)
#[derive(Clone, Debug, PartialEq)]
pub enum Event {
    /// layout_callback: the VR view should draw this layout
    Layout { layout: Layout, tooltip_epoch: u64 },
    /// pointer_callback: where the pointer is on the VR view (logical px), None off it
    Pointer(Option<(i32, i32)>),
    /// position_changed_callback: a window was moved / resized in VR (to save)
    Position { size: String, settings: Settings },
    /// panel_out_of_view_callback
    PanelOutOfView(bool),
    /// launcher_intro_callback
    LauncherIntro(Intro),
}

/// What callers can read at any time (the last the overlay thread published)
#[derive(Clone, Debug)]
pub struct Shared {
    pub settings: Vec<(String, Settings)>,
    /// connected to SteamVR with the overlays made
    pub initialized: bool,
    pub intro: Intro,
    pub layout: Layout,
    pub tooltip_epoch: u64,
}

pub(crate) enum Command {
    Image(String, Image),
    Opacity(String, f64, bool),
    UiScaling(String, f64),
    Position(String, [f64; 6], String),
    DisplayDuration(String, f64),
    FadeoutDuration(String, f64),
    VrWindows(bool, bool),
    VrPanelEnabled(bool),
    PanelLocked(bool),
    LauncherAutoHide(bool),
    LauncherDefaults(Settings),
    LauncherReset(bool),
    Anchor(String),
    RecallPanel,
    Tooltip(Tooltip),
    LayoutRendered((u32, u32)),
    Stop,
}

/// Overlay: the handle (any thread). start() / stop() the overlay thread; the updates queue up
/// while it is stopped.
pub struct Overlay {
    commands: Sender<Command>,
    log: Log,
    events: Events,
    thread: Option<std::thread::JoinHandle<Worker>>,
    idle: Option<Worker>,
    shared: Arc<Mutex<Shared>>,
}

pub type Log = Arc<dyn Fn(String) + Send + Sync>;
pub type Events = Arc<dyn Fn(Event) + Send + Sync>;

impl Overlay {
    /// The overlays for `sizes` (in this order: overlay keys "VRCT0", "VRCT1", ...), not started
    pub fn new(sizes: Vec<(String, Settings)>, log: Log, events: Events) -> Self {
        let (commands, received) = mpsc::channel();
        let worker = Worker::new(sizes, received, log.clone(), events.clone());
        let shared = worker.shared.clone();
        Self { commands, log, events, thread: None, idle: Some(worker), shared }
    }

    /// startOverlay: waits for SteamVR on its thread (nothing when already running)
    pub fn start(&mut self) {
        if let Some(thread) = &self.thread {
            if !thread.is_finished() {
                return;
            }
            self.idle = self.thread.take().and_then(|t| t.join().ok());
        }
        // a worker left behind by a stop that timed out: start over from what it published
        let mut worker = match self.idle.take() {
            Some(w) => w,
            None => return,
        };
        worker.stopped = false;
        self.thread = std::thread::Builder::new().name("overlay".into()).spawn(move || worker.run()).ok();
    }

    /// shutdownOverlay: closes the overlays and the session (waits up to 5 s for the thread; past
    /// that it is left behind, as overlay.py does)
    pub fn stop(&mut self) {
        let Some(thread) = self.thread.take() else { return };
        self.send(Command::Stop);
        let deadline = Instant::now() + STOP_WAIT;
        while !thread.is_finished() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(20));
        }
        if thread.is_finished() {
            self.idle = thread.join().ok();
        } else {
            let (commands, received) = mpsc::channel();
            self.commands = commands;
            let shared = self.shared.lock().unwrap().clone();
            let mut worker = Worker::new(shared.settings, received, self.log.clone(), self.events.clone());
            worker.shared = self.shared.clone();
            self.idle = Some(worker);
        }
        self.shared.lock().unwrap().initialized = false;
    }

    pub fn shared(&self) -> Shared {
        self.shared.lock().unwrap().clone()
    }

    /// Queued while stopped: the worker takes them when started
    fn send(&self, command: Command) {
        let _ = self.commands.send(command);
    }

    /// updateImage: the image shows at the size's opacity and its display duration starts
    pub fn update_image(&self, size: &str, image: Image) {
        self.send(Command::Image(size.into(), image));
    }

    /// clearImage
    pub fn clear_image(&self, size: &str) {
        self.update_image(size, Image::new(1, 1, [0; 4]));
    }

    /// updateOpacity (`with_fade`: as far as the fade has gone)
    pub fn update_opacity(&self, size: &str, opacity: f64, with_fade: bool) {
        self.send(Command::Opacity(size.into(), opacity, with_fade));
    }

    pub fn update_ui_scaling(&self, size: &str, ui_scaling: f64) {
        self.send(Command::UiScaling(size.into(), ui_scaling));
    }

    pub fn update_position(&self, size: &str, position: [f64; 6], tracker: &str) {
        self.send(Command::Position(size.into(), position, tracker.into()));
    }

    pub fn update_display_duration(&self, size: &str, seconds: f64) {
        self.send(Command::DisplayDuration(size.into(), seconds));
    }

    pub fn update_fadeout_duration(&self, size: &str, seconds: f64) {
        self.send(Command::FadeoutDuration(size.into(), seconds));
    }

    /// setVrWindows: whether the log window and the temporary window show
    pub fn set_vr_windows(&self, log: bool, popup: bool) {
        self.send(Command::VrWindows(log, popup));
    }

    /// setVrPanelEnabled: the VR UI as a whole (off: hidden, not captured)
    pub fn set_vr_panel_enabled(&self, enabled: bool) {
        self.send(Command::VrPanelEnabled(enabled));
    }

    /// panel_locked: the log window cannot be grabbed (scrolling and its bar still work)
    pub fn set_panel_locked(&self, locked: bool) {
        self.send(Command::PanelLocked(locked));
    }

    /// launcher_auto_hide: the launcher shows only while the wrist is looked at
    pub fn set_launcher_auto_hide(&self, enabled: bool) {
        self.send(Command::LauncherAutoHide(enabled));
    }

    /// launcher_defaults: the launcher's place, width and hand to go back to
    pub fn set_launcher_defaults(&self, settings: Settings) {
        self.send(Command::LauncherDefaults(settings));
    }

    /// requestLauncherReset (`keep_hand`: the automatic recovery, on the hand it is on)
    pub fn reset_launcher(&self, keep_hand: bool) {
        self.send(Command::LauncherReset(keep_hand));
    }

    /// requestAnchor: what the log window follows ("Playspace", "LeftHand", "RightHand", "HMD")
    pub fn request_anchor(&self, anchor: &str) {
        self.send(Command::Anchor(anchor.into()));
    }

    /// requestRecallPanel: the log window in front of the eyes
    pub fn recall_panel(&self) {
        self.send(Command::RecallPanel);
    }

    /// setTooltip (checked with layout::validate_tooltip)
    pub fn set_tooltip(&self, tooltip: Tooltip) {
        self.send(Command::Tooltip(tooltip));
    }

    /// setLayoutRendered: the VR view drew the layout of this log size
    pub fn set_layout_rendered(&self, panel_size: (u32, u32)) {
        self.send(Command::LayoutRendered(panel_size));
    }
}

impl Drop for Overlay {
    fn drop(&mut self) {
        self.stop();
    }
}

pub(crate) struct Size {
    pub name: String,
    pub region: Option<Region>,
    pub settings: Settings,
    pub last_update: Instant,
    pub fade_ratio: f64,
    /// the last image (hits on its clear parts do not count)
    pub image: Option<Image>,
}

/// What an overlay follows
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Follow {
    Playspace,
    Device(u32),
}

/// The thread's state kept across connections and restarts
pub(crate) struct Worker {
    pub sizes: Vec<Size>,
    commands: Receiver<Command>,
    pub log: Log,
    events: Events,
    pub shared: Arc<Mutex<Shared>>,
    pub stopped: bool,
    connect_failure_logged: bool,
    pub vr_panel_enabled: bool,
    pub panel_enabled_requests: VecDeque<bool>,
    pub panel_locked: bool,
    pub launcher_auto_hide: bool,
    pub launcher_defaults: Option<Settings>,
    pub launcher_reset_requested: bool,
    pub launcher_reset_keep_hand: bool,
    /// (log, popup) wanted shown
    pub vr_windows_wanted: (bool, bool),
    pub requested_anchor: Option<String>,
    pub recall_requested: Option<Instant>,
    pub tooltip_epoch: u64,
    pub tooltip_revision: u64,
    pub tooltip_requests: VecDeque<Tooltip>,
    /// the layout (follows the log's size) and its generation (a new one each change: what was
    /// captured, applied and fitted is told apart by it, as overlay.py does by identity)
    pub layout: Layout,
    pub layout_gen: u64,
    /// the log size the VR view last drew
    pub layout_rendered: (u32, u32),
    pub intro: Intro,
    pub panel_out_of_view: bool,
    pub pointer_notified: Option<(i32, i32)>,
}

/// A random tooltip epoch start in 1..2^47 (secrets.randbelow)
fn random_epoch() -> u64 {
    use std::hash::{BuildHasher, Hasher};
    let mut hasher = std::collections::hash_map::RandomState::new().build_hasher();
    hasher.write_u128(Instant::now().elapsed().as_nanos());
    hasher.finish() % ((1 << 47) - 1) + 1
}

impl Worker {
    fn new(sizes: Vec<(String, Settings)>, commands: Receiver<Command>, log: Log, events: Events) -> Self {
        let sizes: Vec<Size> = sizes.into_iter().map(|(name, settings)| Size {
            region: Region::from_name(&name).filter(|r| matches!(r, Region::Panel | Region::Launcher | Region::Popup)),
            name, settings, last_update: Instant::now(), fade_ratio: 1.0, image: None,
        }).collect();
        let panel = sizes.iter().find(|s| s.region == Some(Region::Panel)).and_then(|s| s.settings.panel_size)
            .unwrap_or(layout::PANEL_DEFAULT_SIZE);
        let (w, h) = layout::clamp_panel_size(panel.0 as f64, panel.1 as f64);
        let layout = Layout::new(w, h);
        let tooltip_epoch = random_epoch();
        let shared = Arc::new(Mutex::new(Shared {
            settings: sizes.iter().map(|s| (s.name.clone(), s.settings.clone())).collect(),
            initialized: false, intro: Intro::Idle, layout, tooltip_epoch,
        }));
        Self {
            sizes, commands, log, events, shared, stopped: false, connect_failure_logged: false,
            vr_panel_enabled: true, panel_enabled_requests: VecDeque::new(), panel_locked: false, launcher_auto_hide: true,
            launcher_defaults: None, launcher_reset_requested: false, launcher_reset_keep_hand: false,
            vr_windows_wanted: (false, false), requested_anchor: None, recall_requested: None,
            tooltip_epoch, tooltip_revision: 0, tooltip_requests: VecDeque::new(),
            layout, layout_gen: 0,
            // the VR view starts with the default layout
            layout_rendered: layout::PANEL_DEFAULT_SIZE,
            intro: Intro::Idle, panel_out_of_view: false, pointer_notified: None,
        }
    }

    pub fn index(&self, size: &str) -> Option<usize> {
        self.sizes.iter().position(|s| s.name == size)
    }

    pub fn region_index(&self, region: Region) -> Option<usize> {
        self.sizes.iter().position(|s| s.region == Some(region))
    }

    pub fn emit(&self, event: Event) {
        (self.events)(event);
    }

    /// What callers read: the settings and the state
    pub fn publish(&self, initialized: bool) {
        let mut shared = self.shared.lock().unwrap();
        shared.settings = self.sizes.iter().map(|s| (s.name.clone(), s.settings.clone())).collect();
        shared.initialized = initialized;
        shared.intro = self.intro;
        shared.layout = self.layout;
        shared.tooltip_epoch = self.tooltip_epoch;
    }

    /// The VR view's layout and the tooltip generation (getVrLayout) to the app
    pub fn notify_layout(&self) {
        self.emit(Event::Layout { layout: self.layout, tooltip_epoch: self.tooltip_epoch });
    }

    /// Waits up to `duration`, applying the commands that come. False once stopped.
    fn wait(&mut self, duration: Duration, mut run: Option<&mut Run>) -> bool {
        let deadline = Instant::now() + duration;
        loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            let command = match self.commands.recv_timeout(remaining) {
                Ok(command) => command,
                Err(RecvTimeoutError::Timeout) => return true,
                Err(RecvTimeoutError::Disconnected) => {
                    self.stopped = true;
                    return false;
                }
            };
            match run.as_deref_mut() {
                Some(run) => run.apply(self, command),
                None => self.apply_offline(command),
            }
            self.publish(run.is_some());
            if self.stopped {
                return false;
            }
        }
    }

    /// A command without SteamVR: the settings and requests only
    fn apply_offline(&mut self, command: Command) {
        match command {
            Command::Stop => self.stopped = true,
            Command::Opacity(name, v, _) => self.with(&name, |s| s.opacity = v),
            Command::UiScaling(name, v) => self.with(&name, |s| s.ui_scaling = v),
            Command::Position(name, position, tracker) => self.with(&name, |s| {
                s.position = position;
                s.tracker = tracker;
            }),
            Command::DisplayDuration(name, v) => self.with(&name, |s| s.display_duration = v),
            Command::FadeoutDuration(name, v) => self.with(&name, |s| s.fadeout_duration = v),
            // without SteamVR an image has nowhere to go (updateImage does nothing then)
            Command::Image(..) => {}
            other => self.apply_request(other),
        }
    }

    fn with(&mut self, name: &str, f: impl FnOnce(&mut Settings)) {
        if let Some(i) = self.index(name) {
            f(&mut self.sizes[i].settings);
        }
    }

    /// The requests that only set what the next frame does (both with and without SteamVR)
    pub(crate) fn apply_request(&mut self, command: Command) {
        match command {
            Command::VrWindows(log, popup) => self.vr_windows_wanted = (log, popup),
            Command::VrPanelEnabled(enabled) => self.panel_enabled_requests.push_back(enabled),
            Command::PanelLocked(locked) => self.panel_locked = locked,
            Command::LauncherAutoHide(enabled) => self.launcher_auto_hide = enabled,
            Command::LauncherDefaults(settings) => self.launcher_defaults = Some(settings),
            Command::LauncherReset(keep_hand) => {
                if self.launcher_defaults.is_none() {
                    (self.log)("overlay: ランチャーの初期値が未設定なので、初期に戻せません".into());
                    return;
                }
                // a reset already asked for that moves the hand too stays so
                self.launcher_reset_keep_hand = keep_hand && (self.launcher_reset_keep_hand || !self.launcher_reset_requested);
                self.launcher_reset_requested = true;
            }
            Command::Anchor(anchor) => {
                if ["Playspace", "LeftHand", "RightHand", "HMD"].contains(&anchor.as_str()) {
                    self.requested_anchor = Some(anchor);
                }
            }
            Command::RecallPanel => self.recall_requested = Some(Instant::now()),
            Command::Tooltip(tooltip) => self.tooltip_requests.push_back(tooltip),
            Command::LayoutRendered(size) => self.layout_rendered = size,
            _ => {}
        }
    }

    fn run(mut self) -> Self {
        (self.log)("overlay: SteamVR の起動を確かめています".into());
        while !self.stopped {
            // what was asked for while stopped
            while let Ok(command) = self.commands.try_recv() {
                self.apply_offline(command);
            }
            if self.stopped {
                break;
            }
            if !vrct_openvr::is_steamvr_running() {
                self.wait(STEAMVR_POLL, None);
                continue;
            }
            let session = match vrct_openvr::acquire(ApplicationType::Background) {
                Ok(s) => s,
                Err(e) => {
                    // SteamVR runs but the headset is not found yet: try again, logging once
                    if !self.connect_failure_logged {
                        self.connect_failure_logged = true;
                        (self.log)(format!("overlay: SteamVR につながりません。つながるまで確かめ直します: {e}"));
                    }
                    self.wait(STEAMVR_POLL, None);
                    continue;
                }
            };
            self.connect_failure_logged = false;
            match self.connected(&session) {
                Ok(()) => (self.log)("overlay: 止めました".into()),
                Err(e) => {
                    (self.log)(format!("overlay: {e}"));
                    self.wait(STEAMVR_POLL, None);
                }
            }
            self.publish(false);
            // after it stops, nothing is shown as lost
            self.notify_panel_out_of_view(false);
        }
        self
    }

    pub fn notify_panel_out_of_view(&mut self, out_of_view: bool) {
        if out_of_view != self.panel_out_of_view {
            self.panel_out_of_view = out_of_view;
            self.emit(Event::PanelOutOfView(out_of_view));
        }
    }

    /// Creates the overlays and runs until SteamVR quits or the overlay is stopped
    fn connected(&mut self, session: &Session) -> anyhow::Result<()> {
        let system = session.system()?;
        let (device, context) = device(system.dxgi_output_info())?;
        let vr = Vr { overlay: Box::new(session.overlay()?), system: Box::new(system), render_models: Box::new(session.render_models()?) };
        let mut run = Run::new(vr, device, context, self);
        let result = run.init(self).map(|()| {
            (self.log)(format!("overlay: 起動しました (vr_panel: {})", run.panel_ready));
            self.publish(true);
            run.frames(self);
        });
        run.teardown(self);
        result
    }
}

/// A D3D11 device on SteamVR's adapter
fn device(adapter_index: i32) -> windows::core::Result<(ID3D11Device, ID3D11DeviceContext)> {
    unsafe {
        let factory: IDXGIFactory1 = CreateDXGIFactory1()?;
        let adapter = factory.EnumAdapters1(adapter_index.max(0) as u32)?;
        let (mut device, mut context) = (None, None);
        D3D11CreateDevice(&adapter, D3D_DRIVER_TYPE_UNKNOWN, Default::default(), D3D11_CREATE_DEVICE_FLAG(0), None,
                          D3D11_SDK_VERSION, Some(&mut device), None, Some(&mut context))?;
        Ok((device.unwrap(), context.unwrap()))
    }
}

/// The OpenVR interfaces while connected (SteamVR's, or the tests' made-up one)
pub(crate) struct Vr<'s> {
    pub overlay: Box<dyn VrOverlay + 's>,
    pub system: Box<dyn VrSystem + 's>,
    pub render_models: Box<dyn VrRenderModels + 's>,
}

/// A grabbed window: its size, the hand and the window seen from the hand
pub(crate) struct Grab {
    pub index: usize,
    pub hand: u32,
    pub hand_to_overlay: Mat4,
}

/// Scaling a grabbed window (trigger held): where the hand started, its forward, the width then,
/// and the window's pose held still
pub(crate) struct GrabScale {
    pub start: pose::Vec3,
    pub forward: pose::Vec3,
    pub width: f64,
    pub overlay_pose: Mat4,
}

/// Dragging a corner of the log window
pub(crate) struct Resize {
    pub hand: u32,
    pub corner: (i8, i8),
    pub m_per_px: f64,
    pub follow: Follow,
    pub relative: Mat4,
    pub pose: Mat4,
    /// the opposite corner, kept still (metres from the centre)
    pub fixed: (f64, f64),
    pub size: (u32, u32),
    pub center: (f64, f64),
}

/// The launcher flying back to the wrist: where from, its width then, since when
pub(crate) struct Return {
    pub start: Mat4,
    pub width: f64,
    pub started: Instant,
}

/// Everything that exists while connected
pub(crate) struct Run<'s> {
    pub vr: Vr<'s>,
    device: ID3D11Device,
    context: ID3D11DeviceContext,
    pub handles: Vec<u64>,
    /// the texture each overlay shows (kept until the next one)
    textures: Vec<Option<ID3D11Texture2D>>,
    /// waiting for the tracker (a controller) to connect
    pub pending: Vec<bool>,
    pub pointers: Vec<(PointerKind, u64, Option<ID3D11Texture2D>)>,
    pub toolbar: Option<u64>,
    pub ghost: Option<u64>,
    ghost_texture: Option<ID3D11Texture2D>,
    pub tooltip_handle: Option<u64>,
    pub vr_resources_tried: bool,
    /// VR UI windows not shown (they show once a capture came, see apply_vr_windows)
    pub hidden: HashSet<Region>,
    // grabbing
    pub grip_prev: HashMap<u32, bool>,
    pub grab_started: Instant,
    pub grabbing: Option<Grab>,
    pub grab_last_relative: Option<Mat34>,
    pub grab_scale: Option<GrabScale>,
    pub grab_prev_time: Instant,
    pub grab_smoothed: Option<Mat34>,
    pub grab_prev_target: Option<Mat34>,
    /// the eyes-to-window distance while a window fixed in the room / to the head is grabbed
    pub grab_radius: Option<f64>,
    pub grab_hand_distance: f64,
    pub grab_error: Option<String>,
    // the bar under the log
    pub toolbar_visible: bool,
    pub toolbar_alpha: f64,
    pub toolbar_faded_at: Option<Instant>,
    pub toolbar_pointed_since: Option<Instant>,
    pub toolbar_last_pointed: Option<Instant>,
    pub toolbar_relative: Option<Mat34>,
    pub toolbar_follow: Option<Follow>,
    // the launcher
    pub launcher_shown: bool,
    pub launcher_alpha: f64,
    pub launcher_interactive: bool,
    pub launcher_change_since: Option<Instant>,
    pub launcher_shown_at: Option<Instant>,
    pub launcher_pointed: bool,
    pub launcher_prev_time: Option<Instant>,
    pub launcher_intro_until: Option<Instant>,
    pub launcher_intro_started: Instant,
    pub launcher_intro_tick: Instant,
    pub launcher_intro_front: Option<Mat4>,
    pub launcher_intro_logged: HashSet<Intro>,
    pub launcher_return: Option<Return>,
    pub first_frame_wait_since: Option<Instant>,
    pub first_frame_wait_logged: bool,
    // the tooltip
    pub tooltip_state: Option<(u64, u64, TooltipShown)>,
    pub tooltip_ready: bool,
    pub tooltip_shown: bool,
    pub tooltip_manipulating: bool,
    // resizing
    pub resizing: Option<Resize>,
    pub corner_prev: HashMap<u32, Option<(i8, i8)>>,
    pub ghost_key: Option<(u32, u32, bool)>,
    /// the place and width before a resize, to go back to when the new size cannot be shown
    pub resize_undo: Option<Settings>,
    // input
    pub panel_input: HashMap<u32, (bool, Option<(i32, i32)>)>,
    /// hands whose trigger is ignored until released (no click after a grab)
    pub trigger_blocked: HashSet<u32>,
    pub mouse: crate::window::Mouse,
    /// each controller's tip seen from its pose, and when to look again
    pub tip_offsets: HashMap<u32, (Mat4, Option<Instant>)>,
    pub debug_state: HashMap<u32, (bool, Option<String>)>,
    // the VR view's capture (panel.rs)
    pub panel: crate::panel::Panel,
    /// the VR UI's capture is set up (overlay.py: self.gl)
    pub panel_ready: bool,
    /// this frame's tracked poses
    pub poses: Vec<vrct_openvr::TrackedDevicePose>,
}

impl<'s> Run<'s> {
    fn new(vr: Vr<'s>, device: ID3D11Device, context: ID3D11DeviceContext, w: &Worker) -> Self {
        let now = Instant::now();
        Run {
            vr, device, context, handles: vec![], textures: vec![], pending: vec![], pointers: vec![], toolbar: None, ghost: None,
            ghost_texture: None, tooltip_handle: None, vr_resources_tried: false, hidden: HashSet::new(),
            grip_prev: HashMap::new(), grab_started: now, grabbing: None, grab_last_relative: None, grab_scale: None,
            grab_prev_time: now, grab_smoothed: None, grab_prev_target: None, grab_radius: None, grab_hand_distance: 1.0,
            grab_error: None, toolbar_visible: false, toolbar_alpha: 0.0, toolbar_faded_at: None, toolbar_pointed_since: None,
            toolbar_last_pointed: None, toolbar_relative: None, toolbar_follow: None, launcher_shown: true, launcher_alpha: 1.0,
            launcher_interactive: true, launcher_change_since: None, launcher_shown_at: None, launcher_pointed: false,
            launcher_prev_time: None, launcher_intro_until: None, launcher_intro_started: now, launcher_intro_tick: now,
            launcher_intro_front: None, launcher_intro_logged: HashSet::new(), launcher_return: None, first_frame_wait_since: None,
            first_frame_wait_logged: false, tooltip_state: None, tooltip_ready: false, tooltip_shown: false,
            tooltip_manipulating: false, resizing: None, corner_prev: HashMap::new(), ghost_key: None, resize_undo: None,
            panel_input: HashMap::new(), trigger_blocked: HashSet::new(), mouse: Default::default(), tip_offsets: HashMap::new(),
            debug_state: HashMap::new(), panel: crate::panel::Panel::new(w), panel_ready: false, poses: vec![],
        }
    }

    /// overlay.init: the overlays (VR UI windows hidden until captured), the pointers, the VR UI's
    /// extra overlays if it is on, then each size's settings
    fn init(&mut self, w: &mut Worker) -> anyhow::Result<()> {
        self.reset_tooltip_epoch(w, true);
        if w.launcher_reset_requested && w.launcher_defaults.is_some() && w.region_index(Region::Launcher).is_some() {
            // asked for while not connected: the settings go back here
            let keep = w.launcher_reset_keep_hand;
            self.apply_launcher_defaults(w, keep);
            w.launcher_reset_requested = false;
            w.launcher_reset_keep_hand = false;
        }
        for i in 0..w.sizes.len() {
            let handle = self.vr.overlay.create_overlay(&format!("VRCT{i}"), &format!("VRCT{i}"))?;
            self.handles.push(handle);
            self.textures.push(None);
            self.pending.push(false);
            match w.sizes[i].region {
                // shown by apply_vr_windows once the VR view was captured (no blank board on the wrist)
                Some(region) => {
                    self.hidden.insert(region);
                }
                None => self.vr.overlay.show_overlay(handle)?,
            }
        }
        for kind in PointerKind::ALL {
            let key = format!("VRCT_pointer_{}", kind.name());
            let handle = self.vr.overlay.create_overlay(&key, &key)?;
            self.vr.overlay.set_overlay_sort_order(handle, 100)?;
            let texture = self.texture(handle, &layout::pointer_image(kind))?;
            self.pointers.push((kind, handle, Some(texture)));
        }
        // the VR UI's extra overlays only when it is on (no GPU work for subtitle-only users)
        self.vr_resources_tried = false;
        self.apply_vr_panel_enabled(w);
        self.set_launcher_intro(w, if w.vr_panel_enabled { Intro::Pending } else { Intro::Idle });
        // shown only once the wrist is looked at (not shown first, then hidden)
        self.launcher_shown = !w.launcher_auto_hide;
        self.launcher_alpha = if self.launcher_shown { 1.0 } else { 0.0 };
        self.launcher_interactive = self.launcher_shown && w.intro == Intro::Idle;
        for i in 0..w.sizes.len() {
            self.update_image(w, i, Image::new(1, 1, [0; 4]));
            self.vr.overlay.set_overlay_color(self.handles[i], 1.0, 1.0, 1.0)?;
            let s = w.sizes[i].settings.clone();
            self.update_ui_scaling(w, i, s.ui_scaling);
            self.update_position(w, i, s.position, &s.tracker);
        }
        Ok(())
    }

    /// The image as a new texture shown by the overlay `handle`
    pub fn texture(&self, handle: u64, image: &Image) -> anyhow::Result<ID3D11Texture2D> {
        let desc = D3D11_TEXTURE2D_DESC {
            Width: image.width as u32,
            Height: image.height as u32,
            MipLevels: 1,
            ArraySize: 1,
            Format: DXGI_FORMAT_R8G8B8A8_UNORM,
            SampleDesc: DXGI_SAMPLE_DESC { Count: 1, Quality: 0 },
            Usage: D3D11_USAGE_DEFAULT,
            BindFlags: D3D11_BIND_SHADER_RESOURCE.0 as u32,
            CPUAccessFlags: 0,
            MiscFlags: 0,
        };
        let init = D3D11_SUBRESOURCE_DATA { pSysMem: image.data.as_ptr().cast(), SysMemPitch: image.width as u32 * 4, SysMemSlicePitch: 0 };
        let mut texture = None;
        unsafe { self.device.CreateTexture2D(&desc, Some(&init), Some(&mut texture))? };
        let texture = texture.unwrap();
        let vr = Texture { handle: texture.as_raw(), texture_type: vrct_openvr::TEXTURE_TYPE_DIRECTX, color_space: vrct_openvr::COLOR_SPACE_GAMMA };
        self.vr.overlay.set_overlay_texture(handle, &vr)?;
        // SteamVR's copy is queued on this device's context
        unsafe { self.context.Flush() };
        Ok(texture)
    }

    /// The resize frame's image on its overlay
    pub fn set_ghost_image(&mut self, image: &Image) -> anyhow::Result<()> {
        if let Some(handle) = self.ghost {
            self.ghost_texture = Some(self.texture(handle, image)?);
        }
        Ok(())
    }

    /// updateImage: the image, the size's opacity, and its display duration starts
    pub fn update_image(&mut self, w: &mut Worker, index: usize, image: Image) {
        match self.texture(self.handles[index], &image) {
            Ok(texture) => self.textures[index] = Some(texture),
            Err(e) => (w.log)(format!("overlay: {} の画像を出せませんでした: {e}", w.sizes[index].name)),
        }
        w.sizes[index].image = Some(image);
        let opacity = w.sizes[index].settings.opacity;
        self.set_alpha(index, opacity);
        w.sizes[index].last_update = Instant::now();
    }

    pub fn set_alpha(&self, index: usize, alpha: f64) {
        let _ = self.vr.overlay.set_overlay_alpha(self.handles[index], alpha as f32);
    }

    /// updateOpacity
    pub fn update_opacity(&mut self, w: &mut Worker, index: usize, opacity: f64, with_fade: bool) {
        w.sizes[index].settings.opacity = opacity;
        let ratio = w.sizes[index].fade_ratio;
        match with_fade {
            true if ratio > 0.0 => self.set_alpha(index, ratio * opacity),
            true => {}
            false => self.set_alpha(index, opacity),
        }
    }

    /// updateUiScaling
    pub fn update_ui_scaling(&mut self, w: &mut Worker, index: usize, ui_scaling: f64) {
        w.sizes[index].settings.ui_scaling = ui_scaling;
        let _ = self.vr.overlay.set_overlay_width_in_meters(self.handles[index], ui_scaling as f32);
    }

    /// getTracker: the base the settings are relative to, and what it follows
    pub fn tracker(&self, name: &str) -> (Mat34, Follow) {
        let tracker = Tracker::from_name(name);
        let follow = match tracker {
            Tracker::Playspace => Follow::Playspace,
            Tracker::LeftHand => Follow::Device(self.vr.system.tracked_device_index_for_controller_role(vrct_openvr::CONTROLLER_ROLE_LEFT_HAND)),
            Tracker::RightHand => Follow::Device(self.vr.system.tracked_device_index_for_controller_role(vrct_openvr::CONTROLLER_ROLE_RIGHT_HAND)),
            Tracker::Hmd => Follow::Device(vrct_openvr::TRACKED_DEVICE_INDEX_HMD),
        };
        (tracker.base(), follow)
    }

    /// updatePosition: the settings, then the overlay relative to its tracker, or pending until it connects
    pub fn update_position(&mut self, w: &mut Worker, index: usize, position: [f64; 6], tracker: &str) {
        let s = &mut w.sizes[index].settings;
        s.position = position;
        s.tracker = tracker.into();
        let relative = position_transform(Tracker::from_name(tracker), position);
        let (_, follow) = self.tracker(tracker);
        let connected = match follow {
            Follow::Playspace => true,
            Follow::Device(d) => self.vr.system.is_tracked_device_connected(d),
        };
        if connected {
            self.set_transform(w, index, follow, &relative);
            self.pending[index] = false;
        } else {
            self.pending[index] = true;
        }
    }

    /// The size's own settings again (updatePosition with them)
    pub fn place(&mut self, w: &mut Worker, index: usize) {
        let s = w.sizes[index].settings.clone();
        self.update_position(w, index, s.position, &s.tracker);
    }

    /// setTransform: relative to `follow`; the log window takes its bar along
    pub fn set_transform(&mut self, w: &mut Worker, index: usize, follow: Follow, relative: &Mat34) {
        self.transform_handle(self.handles[index], follow, relative);
        if w.sizes[index].region == Some(Region::Panel) && self.toolbar.is_some() {
            self.place_toolbar(w, follow, relative);
        }
    }

    pub fn transform_handle(&self, handle: u64, follow: Follow, relative: &Mat34) {
        let m = to_hmd(relative);
        let _ = match follow {
            Follow::Playspace => self.vr.overlay.set_overlay_transform_absolute(handle, vrct_openvr::TRACKING_UNIVERSE_STANDING, &m),
            Follow::Device(d) => self.vr.overlay.set_overlay_transform_tracked_device_relative(handle, d, &m),
        };
    }

    /// The size's place seen from its tracker (3x4)
    pub fn relative(&self, w: &Worker, index: usize) -> Mat34 {
        let s = &w.sizes[index].settings;
        position_transform(Tracker::from_name(&s.tracker), s.position)
    }

    /// update(size): fading after the display duration, the launcher faded while not looked at,
    /// else the opacity as it is
    fn update(&mut self, w: &mut Worker, index: usize) {
        let size = &mut w.sizes[index];
        let s = &size.settings;
        if s.fadeout_duration != 0.0 {
            let shown = size.last_update.elapsed().as_secs_f64();
            if shown > s.display_duration {
                size.fade_ratio = (1.0 - (shown - s.display_duration) / s.fadeout_duration).max(0.0);
                let alpha = size.fade_ratio * s.opacity;
                self.set_alpha(index, alpha);
            }
        } else if size.region == Some(Region::Launcher) && self.launcher_alpha < 1.0 {
            let alpha = s.opacity * self.launcher_alpha;
            self.set_alpha(index, alpha);
        } else {
            let opacity = s.opacity;
            self.update_opacity(w, index, opacity, false);
        }
    }

    /// Visible enough to point at (isVisible)
    pub fn is_visible(&self, w: &Worker, index: usize) -> bool {
        let s = &w.sizes[index].settings;
        s.opacity > 0.0 && (s.fadeout_duration == 0.0 || w.sizes[index].fade_ratio > 0.0)
    }

    /// wakeOverlay: no fade while grabbed
    pub fn wake(&mut self, w: &mut Worker, index: usize) {
        w.sizes[index].last_update = Instant::now();
        w.sizes[index].fade_ratio = 1.0;
        self.set_alpha(index, w.sizes[index].settings.opacity);
    }

    /// A command with SteamVR
    fn apply(&mut self, w: &mut Worker, command: Command) {
        let name = match &command {
            Command::Image(n, _) | Command::Opacity(n, ..) | Command::UiScaling(n, _) | Command::Position(n, ..)
            | Command::DisplayDuration(n, _) | Command::FadeoutDuration(n, _) => n.clone(),
            Command::Stop => {
                w.stopped = true;
                return;
            }
            _ => return w.apply_request(command),
        };
        let Some(i) = w.index(&name) else { return };
        match command {
            Command::Image(_, image) => self.update_image(w, i, image),
            Command::Opacity(_, opacity, with_fade) => self.update_opacity(w, i, opacity, with_fade),
            Command::UiScaling(_, scaling) => self.update_ui_scaling(w, i, scaling),
            Command::Position(_, position, tracker) => self.update_position(w, i, position, &tracker),
            Command::DisplayDuration(_, seconds) => w.sizes[i].settings.display_duration = seconds,
            Command::FadeoutDuration(_, seconds) => w.sizes[i].settings.fadeout_duration = seconds,
            _ => {}
        }
    }

    /// A frame but the VR view's capture: the VR UI on / off, the fades, the overlays whose tracker
    /// just connected, then the lasers (pointing, grabbing, resizing, the launcher)
    fn step(&mut self, w: &mut Worker) {
        self.apply_vr_panel_enabled(w);
        for i in 0..w.sizes.len() {
            self.update(w, i);
        }
        for i in 0..w.sizes.len() {
            if self.pending[i] {
                self.place(w, i);
            }
        }
        if let Err(e) = self.update_grab(w) {
            self.on_grab_error(w, e);
        } else {
            self.grab_error = None;
        }
    }

    /// mainloop: until SteamVR quits or the overlay is stopped
    fn frames(&mut self, w: &mut Worker) {
        crate::panel::raise_thread_priority();
        while !w.stopped {
            let started = Instant::now();
            while let Some(event) = self.vr.system.poll_next_event() {
                if event.event_type == vrct_openvr::EVENT_QUIT {
                    return;
                }
            }
            // the laser (pointer, hover) before the capture: it does not wait for it
            self.step(w);
            if let Err(e) = self.update_panel(w) {
                self.on_panel_error(w, e);
            }
            w.publish(true);
            // smooth while grabbing, quick while pointing at the VR UI
            let interval = if self.grabbing.is_some() || self.resizing.is_some() {
                Duration::from_secs_f64(1.0 / 60.0)
            } else if w.pointer_notified.is_some() {
                Duration::from_secs_f64(1.0 / 30.0)
            } else {
                Duration::from_secs_f64(1.0 / 16.0)
            };
            if !w.wait(interval.saturating_sub(started.elapsed()), Some(self)) {
                return;
            }
        }
    }

    /// teardown: the overlays go before their textures (SteamVR stops reading them first), the GPU
    /// capture after them
    fn teardown(&mut self, w: &mut Worker) {
        self.panel.close_stream();
        for &handle in self.handles.iter().chain(self.pointers.iter().map(|p| &p.1)).chain(self.toolbar.iter())
            .chain(self.ghost.iter()).chain(self.tooltip_handle.iter())
        {
            let _ = self.vr.overlay.destroy_overlay(handle);
        }
        self.textures.clear();
        self.pointers.clear();
        self.ghost_texture = None;
        self.panel.close_gpu();
        let _ = w;
    }
}

#[cfg(test)]
#[path = "overlay_tests.rs"]
mod tests;
