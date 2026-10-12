//! The VR view's capture (overlay.py: updatePanel and what it calls; window_capture.GpuStream):
//! Windows.Graphics.Capture of the hidden window into a D3D11 texture (vrct-graphics), PrintWindow
//! while it has no frame of the right size, the mask (rounded regions, the tooltip, the launcher's
//! intro) composed on the GPU, one texture for every VR UI overlay with its region's bounds.
//! Changing the log's size: the window is resized, and the overlays switch once the VR view has
//! drawn the new layout and it was captured (retried, then undone, when it does not come).
//! The tooltip: the VR view draws it in its region with a marker of its generation; it shows once
//! captured with the marker of the request.
use crate::layout::{self, Layout, Region};
use crate::overlay::{Intro, Run, Worker};
use crate::vr_ui::restore_place;
use crate::window::{self, Hwnd, Printed};
use std::collections::HashSet;
use std::sync::mpsc::{self, Receiver};
use std::time::{Duration, Instant};
use vrct_graphics::capture::{self, Gpu};
use vrct_openvr::{Texture, TextureBounds};

// The window is resized again after this when it does not come to the new size, then undone
const LAYOUT_RETRY_SEC: f64 = 1.0;
const LAYOUT_GIVE_UP_SEC: f64 = 3.0;
// Captures while the VR UI is used (the hover and click show this late), and while not
const PANEL_CAPTURE_INTERVAL_SEC: f64 = 1.0 / 20.0;
const PANEL_IDLE_CAPTURE_INTERVAL_SEC: f64 = 1.0 / 4.0;
const PANEL_ACTIVE_HOLD_SEC: f64 = 1.0;
const PANEL_FIND_INTERVAL_SEC: f64 = 2.0;
// Windows.Graphics.Capture failing to start (just after the window was made: 0x80070057) or
// stopping: retried after n x this, PrintWindow until the next time the VR UI is turned on after
// this many
const STREAM_START_ATTEMPTS: u32 = 5;
const STREAM_RETRY_SEC: f64 = 1.0;
// No frame this long after starting: stopped (it can stop silently)
const GPU_FIRST_FRAME_TIMEOUT_SEC: f64 = 5.0;
// A capture taking this long is logged (the VRCT window may be hung)
const STALL_REPORT_SEC: f64 = 2.0;
// Capture or transfer failing this many times in a row stops capturing (not on one failure)
const PANEL_ERROR_LIMIT: u32 = 30;
const THREAD_PRIORITY_ABOVE_NORMAL: i32 = 1;

/// What was captured: a Windows.Graphics.Capture frame (in the GPU texture) or PrintWindow's bytes
#[derive(Clone, PartialEq)]
pub(crate) enum Frame {
    Gpu(u64),
    Printed(Vec<u8>),
}

pub(crate) struct Capture {
    frame: Frame,
    /// the whole frame's size and the client box in it
    size: (u32, u32),
    client: (u32, u32, u32, u32),
}

impl Capture {
    fn client_size(&self) -> (u32, u32) {
        (self.client.2 - self.client.0, self.client.3 - self.client.1)
    }
}

/// A capture asked for: done at once (Windows.Graphics.Capture), or PrintWindow on a thread of
/// its own (it returns only once the window has drawn: seconds when it hangs)
struct Job {
    layout_gen: u64,
    started: Instant,
    reported: bool,
    printing: Option<Receiver<Option<Printed>>>,
    result: Option<Option<Capture>>,
}

impl Job {
    fn done(&mut self) -> bool {
        if self.result.is_none()
            && let Some(rx) = &self.printing
        {
            match rx.try_recv() {
                Ok(printed) => {
                    self.result = Some(printed.map(|p| Capture { frame: Frame::Printed(p.data), size: p.size, client: p.client }));
                }
                Err(mpsc::TryRecvError::Disconnected) => self.result = Some(None),
                Err(mpsc::TryRecvError::Empty) => {}
            }
        }
        self.result.is_some()
    }
}

/// window_capture.GpuStream: Windows.Graphics.Capture of the window into the GPU texture
struct Stream {
    hwnd: Hwnd,
    started: Instant,
    /// the newest usable frame: its id and size
    latest: Option<(u64, (u32, u32))>,
    /// the newest frame is not the window's size (why take gave nothing)
    stale: bool,
    failed: bool,
    arrivals: u64,
}

impl Stream {
    fn start(gpu: &mut Gpu, hwnd: Hwnd) -> windows::core::Result<Stream> {
        gpu.start(hwnd)?;
        Ok(Stream { hwnd, started: Instant::now(), latest: None, stale: false, failed: false, arrivals: 0 })
    }

    /// Stopped (also when no frame came since it started: it can stop silently)
    fn closed(&self, gpu: &Gpu) -> bool {
        let no_frame = self.arrivals == 0 && self.started.elapsed().as_secs_f64() > GPU_FIRST_FRAME_TIMEOUT_SEC;
        self.failed || no_frame || !gpu.capturing()
    }

    /// The newest frame's client box into the texture when one came. Frames of an old size (or
    /// not copied whole) are dropped. Unchanged screens send no frames: the same one again.
    fn take(&mut self, gpu: &mut Gpu) -> anyhow::Result<Option<Capture>> {
        let bounds = window::frame_client_box(self.hwnd);
        self.stale = false;
        if let Some((frame_size, client)) = bounds
            && !self.failed
        {
            let polled = gpu.poll(client).inspect_err(|_| self.failed = true)?;
            if let Some(p) = polled {
                self.arrivals += 1;
                let copied_all = p.copied == (client.2 - client.0, client.3 - client.1);
                self.latest = (p.frame == frame_size && copied_all).then_some((p.frame_id, p.frame));
            }
        }
        let Some((id, size)) = self.latest else {
            // nothing usable yet: after a first frame, PrintWindow until the next one
            self.stale = self.arrivals > 0;
            return Ok(None);
        };
        match bounds {
            Some((frame_size, client)) if frame_size == size => Ok(Some(Capture { frame: Frame::Gpu(id), size, client })),
            _ => {
                self.stale = true;
                Ok(None)
            }
        }
    }
}

/// What the mask was made for: the capture's size, the layout, the tooltip's (epoch, revision)
type MaskKey = ((u32, u32), Layout, Option<(u64, u64)>);

/// The capture's state while connected
pub(crate) struct Panel {
    pub hwnd: Option<Hwnd>,
    last_find: Option<Instant>,
    last_capture: Option<Instant>,
    job: Option<Job>,
    stream: Option<Stream>,
    stream_unavailable: bool,
    stream_failures: u32,
    stream_retry_at: Option<Instant>,
    /// what was last sent (unchanged captures are not sent again); None sends the next one
    pub last_raw: Option<Frame>,
    last_change: Instant,
    /// the captured client size (physical px)
    pub image_size: Option<(u32, u32)>,
    errors: u32,
    pub error: Option<String>,
    stopped: bool,
    gpu: Option<Gpu>,
    /// textures SteamVR may still read: released at the end
    gpu_retired: Vec<Gpu>,
    gpu_failed: bool,
    mask_key: Option<MaskKey>,
    /// the layout the bounds are set for (its generation)
    pub layout_applied: Option<(u64, Layout)>,
    window_fitted: Option<u64>,
    /// the client size the window was resized to (physical px)
    window_size: Option<(u32, u32)>,
    layout_requested_at: Instant,
    layout_retried: bool,
    layout_logged: HashSet<&'static str>,
}

impl Panel {
    pub fn new(_w: &Worker) -> Panel {
        let now = Instant::now();
        Panel {
            hwnd: None, last_find: None, last_capture: None, job: None, stream: None, stream_unavailable: false,
            stream_failures: 0, stream_retry_at: None, last_raw: None, last_change: now, image_size: None, errors: 0,
            error: None, stopped: false, gpu: None, gpu_retired: vec![], gpu_failed: false, mask_key: None,
            layout_applied: None, window_fitted: None, window_size: None, layout_requested_at: now, layout_retried: false,
            layout_logged: HashSet::new(),
        }
    }

    /// The bounds are for the current layout
    pub fn layout_applied_is(&self, w: &Worker) -> bool {
        self.layout_applied.is_some_and(|(generation, _)| generation == w.layout_gen)
    }

    pub fn close_stream(&mut self) {
        if let (Some(_), Some(gpu)) = (self.stream.take(), self.gpu.as_mut()) {
            gpu.stop();
        }
    }

    /// After the overlays are gone (SteamVR no longer reads the textures)
    pub fn close_gpu(&mut self) {
        self.gpu = None;
        self.gpu_retired.clear();
    }

    fn texture(&self) -> Option<Texture> {
        let gpu = self.gpu.as_ref()?;
        Some(Texture { handle: gpu.texture_ptr() as *mut _, texture_type: vrct_openvr::TEXTURE_TYPE_DIRECTX, color_space: vrct_openvr::COLOR_SPACE_GAMMA })
    }
}

/// raiseThreadPriority: a little above normal (with OCR running, plain copies were several times slower)
pub(crate) fn raise_thread_priority() {
    use windows_sys::Win32::System::Threading::{GetCurrentThread, SetThreadPriority};
    unsafe { SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_ABOVE_NORMAL) };
}

fn secs(d: f64) -> Duration {
    Duration::from_secs_f64(d)
}

impl Run<'_> {
    /// initVrResources: the bar, the resize frame, the tooltip and the capture (once a connection)
    pub fn init_vr_resources(&mut self, w: &mut Worker) {
        if self.vr_resources_tried {
            return;
        }
        self.vr_resources_tried = true;
        if let Err(e) = self.create_vr_overlays(w) {
            (w.log)(format!("overlay: VR UI のオーバーレイを作れませんでした: {e}"));
        }
        if w.sizes.iter().any(|s| s.region.is_some()) {
            self.init_panel_texture(w);
        }
    }

    fn create_vr_overlays(&mut self, w: &mut Worker) -> anyhow::Result<()> {
        let ov = &self.vr.overlay;
        if w.region_index(Region::Panel).is_some() {
            let toolbar = ov.create_overlay("VRCT_toolbar", "VRCT_toolbar")?;
            self.toolbar = Some(toolbar);
            ov.set_overlay_width_in_meters(toolbar, self.region_width_m(w, Region::Toolbar) as f32)?;
            ov.hide_overlay(toolbar)?;
            self.toolbar_visible = false;
            self.toolbar_alpha = 0.0;
            self.toolbar_faded_at = None;
            let ghost = ov.create_overlay("VRCT_resize_ghost", "VRCT_resize_ghost")?;
            self.ghost = Some(ghost);
            ov.set_overlay_sort_order(ghost, 50)?;
            ov.hide_overlay(ghost)?;
            self.ghost_key = None;
        }
        if w.region_index(Region::Launcher).is_some() || w.region_index(Region::Panel).is_some() {
            let tooltip = ov.create_overlay("VRCT_tooltip", "VRCT_tooltip")?;
            self.tooltip_handle = Some(tooltip);
            ov.set_overlay_sort_order(tooltip, 70)?;
            ov.hide_overlay(tooltip)?;
        }
        Ok(())
    }

    /// initPanelTexture: the capture starts afresh (the GPU texture is made once the window's size is known)
    fn init_panel_texture(&mut self, w: &mut Worker) {
        self.reset_tooltip_epoch(w, true);
        let p = &mut self.panel;
        p.last_raw = None;
        p.stopped = false;
        p.layout_applied = None;
        p.window_fitted = None;
        // the wait for the size counts from the start of capturing
        p.layout_requested_at = Instant::now();
        p.layout_retried = false;
        p.layout_logged.clear();
        p.job = None;
        p.close_stream();
        p.stream_unavailable = false;
        p.stream_failures = 0;
        p.stream_retry_at = None;
        self.panel_ready = true;
    }

    /// applyVrPanelEnabled: the on / off requests in order; turned on again, only the capture restarts
    pub fn apply_vr_panel_enabled(&mut self, w: &mut Worker) {
        let mut restart = false;
        while let Some(enabled) = w.panel_enabled_requests.pop_front() {
            if enabled && !w.vr_panel_enabled {
                restart = true;
            }
            if enabled != w.vr_panel_enabled {
                self.reset_tooltip_epoch(w, true);
                self.set_launcher_intro(w, if enabled { Intro::Pending } else { Intro::Idle });
            }
            w.vr_panel_enabled = enabled;
        }
        if w.vr_panel_enabled {
            // first turned on (init ran with it off)
            self.init_vr_resources(w);
        }
        if !restart || !w.vr_panel_enabled {
            return;
        }
        // the subtitles kept the overlay running: only the capture's stopped / failed state is reset
        // (the texture and the overlays stay; the old WebView's captures are not used)
        let now = Instant::now();
        let p = &mut self.panel;
        p.close_stream();
        p.job = None;
        p.hwnd = None;
        p.last_find = None;
        p.last_capture = None;
        p.window_fitted = None;
        p.window_size = None;
        p.stopped = false;
        p.errors = 0;
        p.error = None;
        p.stream_unavailable = false;
        p.stream_failures = 0;
        p.stream_retry_at = None;
        p.last_raw = None;
        p.last_change = now;
        if !p.layout_applied_is(w) {
            // the time it was off does not undo a resize at once
            p.layout_requested_at = p.layout_requested_at.max(now);
            p.layout_retried = false;
        }
    }

    /// updatePanel: the tooltip requests, then the capture to the overlays
    pub fn update_panel(&mut self, w: &mut Worker) -> anyhow::Result<()> {
        let now = Instant::now();
        let manipulating = self.grabbing.is_some() || self.resizing.is_some();
        if manipulating && !self.tooltip_manipulating {
            self.reset_tooltip_epoch(w, true);
        }
        self.tooltip_manipulating = manipulating;
        self.apply_tooltip_requests(w);
        self.update_tooltip(w);
        if !w.vr_panel_enabled || !self.panel_ready || self.panel.stopped {
            self.hide_tooltip();
            return Ok(());
        }
        let Some(capture) = self.collect_capture(w, now)? else { return Ok(()) };
        self.transfer_capture(w, capture, now)?;
        // a capture handled to the end
        self.panel.errors = 0;
        Ok(())
    }

    /// collectCapture: the capture asked for, when done (asking for the next at once)
    fn collect_capture(&mut self, w: &mut Worker, now: Instant) -> anyhow::Result<Option<Capture>> {
        let started_now = self.panel.job.is_none();
        if started_now {
            self.start_capture(w, now)?;
            if !self.panel.job.as_mut().is_some_and(Job::done) {
                return Ok(None);
            }
        } else {
            let job = self.panel.job.as_mut().unwrap();
            if !job.done() {
                if !job.reported && since(now, job.started) >= STALL_REPORT_SEC {
                    job.reported = true;
                    (w.log)(format!("overlay: VR画面の撮影に時間がかかっています (VRCT の画面が応答していない可能性) ({:.1} 秒)",
                                    since(now, job.started)));
                }
                return Ok(None);
            }
        }
        let job = self.panel.job.take().unwrap();
        if job.reported {
            let returned = Instant::now();
            (w.log)(format!("overlay: VR画面の撮影が戻りました ({:.1} 秒)", since(returned, job.started)));
            // the wait for a size counts again from here (not undone just after a hang)
            self.panel.layout_requested_at = self.panel.layout_requested_at.max(returned);
        }
        if !started_now {
            // the next capture now (not a frame just to collect it)
            self.start_capture(w, now)?;
        }
        if job.layout_gen != w.layout_gen {
            // the layout changed while capturing: wait for the next
            return Ok(None);
        }
        let result = job.result.flatten();
        if result.is_none() {
            self.log_layout(w, "no capture", String::new());
        }
        Ok(result)
    }

    /// panelCaptureInterval: short while the VR UI is used or just changed
    fn capture_interval(&self, w: &Worker, now: Instant) -> f64 {
        let active = w.pointer_notified.is_some() || self.grabbing.is_some() || self.resizing.is_some()
            || since(now, self.panel.last_change) < PANEL_ACTIVE_HOLD_SEC;
        if active { PANEL_CAPTURE_INTERVAL_SEC } else { PANEL_IDLE_CAPTURE_INTERVAL_SEC }
    }

    /// startCapture: once the interval passed: the window found and fitted to the layout, then a
    /// Windows.Graphics.Capture frame, else PrintWindow
    fn start_capture(&mut self, w: &mut Worker, now: Instant) -> anyhow::Result<()> {
        if self.panel.last_capture.is_some_and(|at| since(now, at) < self.capture_interval(w, now)) {
            return Ok(());
        }
        self.panel.last_capture = Some(now);
        if !self.panel.hwnd.is_some_and(window::is_window) {
            if self.panel.hwnd.take().is_some() {
                self.reset_tooltip_epoch(w, true);
            }
            if self.panel.last_find.is_some_and(|at| since(now, at) < PANEL_FIND_INTERVAL_SEC) {
                return Ok(());
            }
            self.panel.last_find = Some(now);
            self.panel.hwnd = window::find_window(window::VR_PANEL_TITLE);
            if self.panel.hwnd.is_none() {
                return Ok(());
            }
            self.reset_tooltip_epoch(w, true);
            // found again: made at the default size
            self.panel.window_fitted = None;
        }
        let hwnd = self.panel.hwnd.unwrap();
        // the window to the layout (at start and when the log's size changed)
        if self.panel.window_fitted != Some(w.layout_gen) {
            let size = window::resize_client(hwnd, w.layout.atlas.0, w.layout.atlas.1);
            self.panel.window_size = Some(size);
            self.panel.window_fitted = Some(w.layout_gen);
            self.log_layout(w, "resize", format!("target {size:?}"));
        }
        self.ensure_gpu(w);
        if self.panel.gpu.is_none() {
            return Ok(());
        }
        if self.panel_stream(w) {
            let p = &mut self.panel;
            let (stream, gpu) = (p.stream.as_mut().unwrap(), p.gpu.as_mut().unwrap());
            if let Some(capture) = stream.take(gpu)? {
                // capturing: occasional stops are counted afresh (not stuck on PrintWindow in long use)
                p.stream_failures = 0;
                p.job = Some(Job { layout_gen: w.layout_gen, started: now, reported: false, printing: None, result: Some(Some(capture)) });
                return Ok(());
            }
            if !stream.stale {
                // no frame yet
                return Ok(());
            }
            // the new size's frame has not come (it waits for the screen to change, up to 40 s
            // seen): PrintWindow until then
        }
        let (tx, rx) = mpsc::channel();
        // ponytail: a thread per capture (20 a second at most); a hung window leaves one behind per
        // off / on, ending when it draws
        std::thread::spawn(move || {
            let _ = tx.send(window::capture(hwnd));
        });
        self.panel.job = Some(Job { layout_gen: w.layout_gen, started: now, reported: false, printing: Some(rx), result: None });
        Ok(())
    }

    /// panelStream: Windows.Graphics.Capture of the window, (re)started; false: PrintWindow for now
    fn panel_stream(&mut self, w: &mut Worker) -> bool {
        let now = Instant::now();
        let p = &mut self.panel;
        if p.stream_unavailable || p.stream_retry_at.is_some_and(|at| now < at) {
            return false;
        }
        let hwnd = p.hwnd.unwrap();
        let same_window = p.stream.as_ref().is_some_and(|s| s.hwnd == hwnd);
        if same_window && !p.stream.as_ref().unwrap().closed(p.gpu.as_ref().unwrap()) {
            return true;
        }
        self.reset_tooltip_epoch(w, true);
        self.panel.close_stream();
        if same_window {
            // stopped on the same window: PrintWindow a while, then again
            self.stream_failed(w, "止まった");
            return false;
        }
        // the window was made again
        match Stream::start(self.panel.gpu.as_mut().unwrap(), hwnd) {
            Ok(stream) => {
                self.panel.stream = Some(stream);
                true
            }
            Err(e) => {
                (w.log)(format!("overlay: 画面キャプチャを始められません: {e}"));
                self.stream_failed(w, "始められない");
                false
            }
        }
    }

    /// streamFailed: retried with growing waits; past STREAM_START_ATTEMPTS, PrintWindow until turned on again
    fn stream_failed(&mut self, w: &Worker, reason: &str) {
        let p = &mut self.panel;
        p.stream_failures += 1;
        if p.stream_failures >= STREAM_START_ATTEMPTS {
            p.stream_unavailable = true;
            (w.log)(format!("overlay: 画面キャプチャが{reason}ので PrintWindow で撮ります (failures {})", p.stream_failures));
            return;
        }
        let wait = STREAM_RETRY_SEC * p.stream_failures as f64;
        p.stream_retry_at = Some(Instant::now() + secs(wait));
        (w.log)(format!("overlay: 画面キャプチャが{reason}ので、しばらく PrintWindow で撮って試し直します (failures {}, retry_in_sec {wait})",
                        p.stream_failures));
    }

    /// ensureGpu: the texture, once the window's size is known, large enough for the largest layout
    /// at its DPI (made once: no size change of what SteamVR holds)
    fn ensure_gpu(&mut self, w: &Worker) {
        let p = &mut self.panel;
        let Some(window_size) = p.window_size else { return };
        if p.gpu.is_some() || p.gpu_failed {
            return;
        }
        let scale = window_size.0 as f64 / w.layout.atlas.0 as f64;
        let (max_w, max_h) = Layout::max().atlas;
        let size = (((max_w as f64 * scale).round_ties_even() as u32).max(window_size.0),
                    ((max_h as f64 * scale).round_ties_even() as u32).max(window_size.1));
        let adapter = self.vr.system.dxgi_output_info().max(0) as u32;
        match Gpu::new(adapter, size.0, size.1) {
            Ok(gpu) => {
                p.gpu = Some(gpu);
                p.mask_key = None;
                p.close_stream();
                (w.log)(format!("overlay: VR画面を GPU で転送します (texture {size:?})"));
            }
            Err(e) => {
                p.gpu_failed = true;
                (w.log)(format!("overlay: VR画面の GPU のテクスチャを作れないので、VR UI を出せません: {e}"));
            }
        }
    }

    /// transferCapture: frames of the old size (or while the VR view still draws the old layout)
    /// are not used; unchanged ones are not sent
    fn transfer_capture(&mut self, w: &mut Worker, capture: Capture, now: Instant) -> anyhow::Result<()> {
        let size = capture.client_size();
        let window_fits = Some(size) == self.panel.window_size;
        let rendered = w.layout_rendered == w.layout.panel_size();
        if !window_fits {
            self.log_layout(w, "window size differs", format!("capture {size:?}, target {:?}", self.panel.window_size));
        } else if !rendered {
            self.log_layout(w, "waiting for render", format!("rendered {:?}", w.layout_rendered));
        }
        if !window_fits || !rendered {
            if !window_fits && self.panel.layout_applied_is(w) {
                // the size changed while shown (DPI): fitted again
                self.panel.window_fitted = None;
            } else if !window_fits {
                self.retry_or_revert_layout(w, now);
            }
            return Ok(());
        }
        if self.panel.last_raw.as_ref() == Some(&capture.frame) {
            return Ok(());
        }
        self.panel.last_raw = Some(capture.frame.clone());
        self.panel.last_change = now;
        self.transfer_gpu(w, &capture)
    }

    /// The VR UI overlays sharing the texture: the windows, the bar and the tooltip
    fn region_handles(&self, w: &Worker) -> Vec<(Region, u64)> {
        let mut handles: Vec<(Region, u64)> = [Region::Panel, Region::Launcher, Region::Popup].into_iter()
            .filter_map(|r| w.region_index(r).map(|i| (r, self.handles[i]))).collect();
        handles.extend(self.toolbar.map(|h| (Region::Toolbar, h)));
        handles.extend(self.tooltip_handle.map(|h| (Region::Tooltip, h)));
        handles
    }

    /// transferGpu: the capture composed with the mask on the GPU and given to every VR UI overlay
    fn transfer_gpu(&mut self, w: &mut Worker, capture: &Capture) -> anyhow::Result<()> {
        let size = capture.client_size();
        let texture_size = self.panel.gpu.as_ref().unwrap().size();
        if size.0 > texture_size.0 || size.1 > texture_size.1 {
            // the DPI went up: a larger texture (the old one released at the end: SteamVR may hold it)
            (w.log)(format!("overlay: VR画面のテクスチャを大きくします (image {size:?}, texture {texture_size:?})"));
            for (_, handle) in self.region_handles(w) {
                let _ = self.vr.overlay.clear_overlay_texture(handle);
            }
            let p = &mut self.panel;
            p.close_stream();
            p.gpu_retired.extend(p.gpu.take());
            p.window_size = Some(size);
            p.last_raw = None;
            p.layout_applied = None;
            p.job = None;
            return Ok(());
        }
        let state = self.tooltip_state.clone();
        let p = &mut self.panel;
        let gpu = p.gpu.as_mut().unwrap();
        if let Frame::Printed(raw) = &capture.frame {
            match gpu.upload(raw, capture.size, capture.client) {
                // the window changed size while printed: this frame only is dropped
                Err(capture::Error::Invalid(reason)) => {
                    (w.log)(format!("overlay: VR画面の撮影を捨てました: {reason}"));
                    return Ok(());
                }
                Err(e) => return Err(e.into()),
                Ok(_) => {}
            }
            // the texture was written over: the stream's frame is not composed again
            if let Some(stream) = p.stream.as_mut() {
                stream.latest = None;
            }
        }
        let mut tooltip_matches = false;
        if let Some((epoch, revision, _)) = &state {
            let (row, columns) = layout::marker_points(size.0, &w.layout);
            if row < size.1 {
                let pixels = gpu.read_row(row)?;
                tooltip_matches = layout::marker_row_matches(&pixels[..(size.0 as usize * 4).min(pixels.len())], &columns, *epoch, *revision);
            }
        }
        // the mask made and sent only when the layout, the size or the tooltip changed
        let key = (size, w.layout, state.as_ref().filter(|_| tooltip_matches).map(|(e, r, _)| (*e, *r)));
        if p.mask_key.as_ref() != Some(&key) {
            let mut mask = layout::mask(size, &w.layout);
            if tooltip_matches && let Some((_, _, shown)) = &state {
                layout::tooltip_mask(size, &w.layout, shown, &mut mask);
            }
            gpu.set_mask(&mask, size.0, size.1)?;
            p.mask_key = Some(key);
        }
        let intro = match w.intro {
            Intro::Idle => 0,
            Intro::Pending => 1,
            Intro::Playing => 2,
        };
        let rect = if intro == 0 { [0; 4] } else { w.layout.region_rect(Region::Launcher, size.0) };
        gpu.render(intro, (rect[0] as i32, rect[1] as i32, rect[2] as i32, rect[3] as i32))?;
        if !tooltip_matches {
            self.tooltip_ready = false;
            self.hide_tooltip_overlay();
        }
        if intro != 0 && self.launcher_intro_logged.insert(w.intro) {
            (w.log)(format!("overlay: launcher intro {} (GPU)", w.intro.name()));
        }
        let texture = self.panel.texture().unwrap();
        for (_, handle) in self.region_handles(w) {
            self.vr.overlay.set_overlay_texture(handle, &texture)?;
        }
        // SteamVR's copy is queued on this device: without a flush it shows with the next frame
        self.panel.gpu.as_ref().unwrap().flush();
        self.finish_transfer(w, size, tooltip_matches);
        Ok(())
    }

    /// finishTransfer: the bounds set again when the layout or the capture's size changed
    fn finish_transfer(&mut self, w: &mut Worker, size: (u32, u32), tooltip_matches: bool) {
        let changed = Some(size) != self.panel.image_size;
        self.panel.image_size = Some(size);
        if !self.panel.layout_applied_is(w) || changed {
            self.apply_layout(w);
        }
        self.tooltip_ready = tooltip_matches;
        self.update_tooltip(w);
    }

    /// applyLayout: each region's bounds (the capture is the top left part of the texture), and
    /// the log's width and place
    fn apply_layout(&mut self, w: &mut Worker) {
        let (fu, fv) = match (self.panel.gpu.as_ref().map(Gpu::size), self.panel.image_size) {
            (Some(t), Some(i)) => (i.0 as f64 / t.0 as f64, i.1 as f64 / t.1 as f64),
            _ => (1.0, 1.0),
        };
        for (region, handle) in self.region_handles(w) {
            // the tooltip's are set by update_tooltip
            if region == Region::Tooltip {
                continue;
            }
            let [u_min, u_max, v_min, v_max] = w.layout.region_bounds(region, fu, fv);
            let _ = self.vr.overlay.set_overlay_texture_bounds(handle, &TextureBounds { u_min, v_min, u_max, v_max });
        }
        if let Some(pi) = w.region_index(Region::Panel) {
            let width = w.sizes[pi].settings.ui_scaling;
            self.update_ui_scaling(w, pi, width);
            self.place(w, pi);
        }
        self.panel.layout_applied = Some((w.layout_gen, w.layout));
        self.resize_undo = None;
        let detail = format!("image {:?}, ui_scaling {:?}", self.panel.image_size,
                             w.region_index(Region::Panel).map(|i| w.sizes[i].settings.ui_scaling));
        self.log_layout(w, "applied", detail);
        if self.resizing.is_none() {
            self.hide_resize_ghost();
        }
    }

    /// retryOrRevertLayout: the window resized again, then the size undone when the new one is not captured
    fn retry_or_revert_layout(&mut self, w: &mut Worker, now: Instant) {
        if self.panel.layout_applied_is(w) {
            return;
        }
        let waited = since(now, self.panel.layout_requested_at);
        if waited >= LAYOUT_GIVE_UP_SEC {
            let fallback = self.panel.layout_applied.map_or(layout::PANEL_DEFAULT_SIZE, |(_, l)| l.panel_size());
            (w.log)(format!("overlay: VR画面が新しい大きさにならないので元に戻します (wanted {:?}, back_to {fallback:?})", w.layout.atlas));
            let pi = w.region_index(Region::Panel);
            if let (Some(undo), Some(pi)) = (self.resize_undo.take(), pi) {
                // back to the place and width before the resize (else it jumps at the old size)
                restore_place(&mut w.sizes[pi].settings, &undo);
            } else if let Some(pi) = pi {
                // a px stays as long
                w.sizes[pi].settings.ui_scaling *= fallback.0 as f64 / w.layout.panel_size().0 as f64;
            }
            self.set_panel_size(w, fallback.0 as f64, fallback.1 as f64);
            // not tried again if that does not fit either
            self.panel.layout_requested_at = now + secs(3600.0);
            if let Some(pi) = pi {
                self.notify_position(w, pi);
            }
        } else if waited >= LAYOUT_RETRY_SEC && !self.panel.layout_retried {
            self.panel.layout_retried = true;
            self.panel.window_fitted = None;
        }
    }

    /// setPanelSize: the log's size; the VR view gets the new layout, the overlays switch once captured
    pub fn set_panel_size(&mut self, w: &mut Worker, width: f64, height: f64) {
        let (width, height) = layout::clamp_panel_size(width, height);
        if let Some(pi) = w.region_index(Region::Panel) {
            w.sizes[pi].settings.panel_size = Some((width, height));
        }
        let new = Layout::new(width, height);
        if new == w.layout {
            return;
        }
        w.layout = new;
        w.layout_gen += 1;
        self.reset_tooltip_epoch(w, false);
        let p = &mut self.panel;
        p.last_raw = None;
        p.layout_requested_at = Instant::now();
        p.layout_retried = false;
        p.layout_logged.clear();
        w.notify_layout();
    }

    /// logLayout: each step of a size change once a layout (for checking in VR)
    fn log_layout(&mut self, w: &Worker, event: &'static str, detail: String) {
        if self.panel.layout_logged.insert(event) {
            (w.log)(format!("overlay layout: {event} (atlas {:?}) {detail}", w.layout.atlas));
        }
    }

    /// onPanelError: retried next frame; stops capturing only when it keeps failing
    pub fn on_panel_error(&mut self, w: &mut Worker, error: anyhow::Error) {
        self.panel.errors += 1;
        // every frame: logged once while the same error goes on
        let message = error.to_string();
        if self.panel.error.as_deref() != Some(message.as_str()) {
            (w.log)(format!("overlay: VR画面の撮影・転送に失敗しました: {message}"));
            self.panel.error = Some(message);
        }
        if self.panel.errors >= PANEL_ERROR_LIMIT && !self.panel.stopped {
            (w.log)(format!("overlay: VR画面の撮影が続けて失敗したので止めます (errors {})", self.panel.errors));
            self.reset_tooltip_epoch(w, true);
            self.panel.stopped = true;
            self.panel.close_stream();
        }
    }

    // ------------------------------------------------------------------ the tooltip

    /// resetTooltipEpoch: a new generation (requests of the old one are dropped), told with the layout
    pub fn reset_tooltip_epoch(&mut self, w: &mut Worker, notify: bool) {
        self.hide_tooltip();
        w.tooltip_epoch += 1;
        w.tooltip_revision = 0;
        if notify {
            w.notify_layout();
        }
    }

    pub fn hide_tooltip(&mut self) {
        self.tooltip_state = None;
        self.tooltip_ready = false;
        self.panel.last_raw = None;
        self.hide_tooltip_overlay();
    }

    fn hide_tooltip_overlay(&mut self) {
        if !self.tooltip_shown {
            return;
        }
        if let Some(handle) = self.tooltip_handle {
            self.tooltip_shown = false;
            let _ = self.vr.overlay.hide_overlay(handle);
        }
    }

    fn apply_tooltip_requests(&mut self, w: &mut Worker) {
        while let Some(t) = w.tooltip_requests.pop_front() {
            if t.epoch != w.tooltip_epoch || t.revision <= w.tooltip_revision {
                continue;
            }
            w.tooltip_revision = t.revision;
            self.hide_tooltip();
            if let Some(shown) = t.shown {
                self.tooltip_state = Some((t.epoch, t.revision, shown));
            }
        }
    }

    /// tooltipTargetMatches: the pointer on the tooltip's button (any place for keyboard focus)
    pub fn tooltip_target_matches(&self, w: &Worker, xy: Option<(i32, i32)>) -> bool {
        let Some((_, _, shown)) = &self.tooltip_state else { return false };
        if shown.mode == layout::TooltipMode::Focus {
            return true;
        }
        let Some((px, py)) = xy else { return false };
        let [rx, ry, _, _] = w.layout.region(shown.region).map(f64::from);
        let [x, y, bw, bh] = shown.button;
        let (px, py) = (px as f64, py as f64);
        rx + x <= px && px < rx + x + bw && ry + y <= py && py < ry + y + bh
    }

    /// updateTooltip: over its button, in front of the launcher or the bar, once captured
    fn update_tooltip(&mut self, w: &mut Worker) {
        let Some((_, _, shown)) = self.tooltip_state.clone() else { return };
        let parent = shown.region;
        let (available, visible) = match parent {
            Region::Launcher => (w.region_index(Region::Launcher).is_some(), self.launcher_interactive),
            _ => (w.region_index(Region::Panel).is_some(), self.toolbar_visible),
        };
        if !available || !visible || !w.vr_panel_enabled || !self.panel_ready || self.panel.stopped || self.hidden.contains(&parent)
            || (parent == Region::Toolbar && self.hidden.contains(&Region::Panel)) || self.grabbing.is_some() || self.resizing.is_some()
            || !self.panel.layout_applied_is(w) || !self.tooltip_target_matches(w, w.pointer_notified)
        {
            self.hide_tooltip();
            return;
        }
        let Some(handle) = self.tooltip_handle.filter(|_| self.tooltip_ready) else { return };
        let owner = w.region_index(if parent == Region::Toolbar { Region::Panel } else { parent });
        let (relative, follow) = match parent {
            Region::Toolbar => (self.toolbar_relative, self.toolbar_follow),
            _ => match owner {
                Some(i) => (Some(self.relative(w, i)), Some(self.tracker(&w.sizes[i].settings.tracker).1)),
                None => (None, None),
            },
        };
        let (Some(relative), Some(follow), Some(owner)) = (relative, follow, owner) else {
            self.hide_tooltip();
            return;
        };
        if follow == crate::overlay::Follow::Device(vrct_openvr::TRACKED_DEVICE_INDEX_INVALID) || self.pending[owner] {
            self.hide_tooltip();
            return;
        }
        let [_, _, pw, ph] = w.layout.region(parent).map(f64::from);
        let mpp = self.region_width_m(w, parent) / pw;
        let [x, y, bw_button, _] = shown.button;
        let [bw, bh] = shown.size;
        let center_x = (x + bw_button / 2.0).max(bw / 2.0 + 12.0).min(pw - bw / 2.0 - 12.0);
        let mut offset = crate::pose::IDENTITY;
        crate::pose::set_position(&mut offset, [(center_x - pw / 2.0) * mpp, (ph / 2.0 - y + 12.0 + (bh + 6.0) / 2.0) * mpp, 0.004]);
        let pose = crate::pose::top(&crate::pose::mul(&crate::pose::homogeneous(&relative), &offset));
        self.transform_handle(handle, follow, &pose);
        let _ = self.vr.overlay.set_overlay_width_in_meters(handle, (bw * mpp) as f32);
        let (Some(image), Some(texture_size)) = (self.panel.image_size, self.panel.gpu.as_ref().map(Gpu::size)) else { return };
        let [tx, ty, _, _] = w.layout.region(Region::Tooltip).map(f64::from);
        let scale = image.0 as f64 / w.layout.atlas.0 as f64;
        let (tw, th) = (texture_size.0 as f64, texture_size.1 as f64);
        let bounds = TextureBounds {
            u_min: (tx * scale / tw) as f32,
            u_max: ((tx + bw) * scale / tw) as f32,
            v_min: ((ty + 8.0) * scale / th) as f32,
            v_max: ((ty + 8.0 + bh + 6.0) * scale / th) as f32,
        };
        let _ = self.vr.overlay.set_overlay_texture_bounds(handle, &bounds);
        let _ = self.vr.overlay.show_overlay(handle);
        if !self.tooltip_shown
            && let Some(texture) = self.panel.texture()
        {
            // a texture given while hidden may not be used: given again when shown
            let _ = self.vr.overlay.set_overlay_texture(handle, &texture);
            self.panel.gpu.as_ref().unwrap().flush();
        }
        self.tooltip_shown = true;
    }
}

fn since(now: Instant, then: Instant) -> f64 {
    now.saturating_duration_since(then).as_secs_f64()
}
