//! The overlay's frames against a made-up SteamVR: where the head and the controllers are, their
//! buttons, and the overlays as SteamVR would place them (the laser's hit computed from each
//! overlay's place, width and texture). Textures are made on D3D11's software device (WARP).
//! The VR view's window is never looked for (update_panel is not run), so no input reaches a window.
use super::*;
use crate::pose::Vec3;
use crate::vr::{VrOverlay, VrRenderModels, VrSystem};
use std::cell::RefCell;
use std::rc::Rc;
use vrct_openvr::{ComponentState, ControllerModeState, ControllerState, Error, HmdMatrix34, IntersectionParams,
                  IntersectionResults, TextureBounds, TrackedDevicePose};
use windows::Win32::Graphics::Direct3D::D3D_DRIVER_TYPE_WARP;

const HEAD: u32 = vrct_openvr::TRACKED_DEVICE_INDEX_HMD;
const LEFT: u32 = 1;
const RIGHT: u32 = 2;
const GRIP: u64 = 1 << vrct_openvr::BUTTON_GRIP;
const TRIGGER: u64 = 1 << vrct_openvr::BUTTON_STEAMVR_TRIGGER;

#[derive(Default)]
struct Shown {
    key: String,
    visible: bool,
    width: f64,
    alpha: f64,
    /// the device it follows (None: the room) and its place there
    place: Option<(Option<u32>, Mat4)>,
    texture: (u32, u32),
    bounds: Option<TextureBounds>,
}

#[derive(Default)]
struct Steam {
    poses: HashMap<u32, Mat4>,
    buttons: HashMap<u32, ControllerState>,
    overlays: Vec<Shown>,
}

impl Steam {
    fn world(&self, o: &Shown) -> Option<Mat4> {
        match o.place? {
            (None, m) => Some(m),
            (Some(device), m) => Some(pose::mul(self.poses.get(&device)?, &m)),
        }
    }
}

#[derive(Clone)]
struct SteamVr(Rc<RefCell<Steam>>);

fn ok() -> Result<(), Error> {
    Ok(())
}

impl SteamVr {
    fn with(&self, handle: u64, f: impl FnOnce(&mut Shown)) -> Result<(), Error> {
        f(&mut self.0.borrow_mut().overlays[handle as usize - 1]);
        ok()
    }
}

fn hmd(m: &Mat4) -> HmdMatrix34 {
    to_hmd(&pose::top(m))
}

fn from_hmd(m: &HmdMatrix34) -> Mat4 {
    pose::homogeneous(&m.map(|r| r.map(f64::from)))
}

impl VrSystem for SteamVr {
    fn device_to_absolute_tracking_pose(&self, _origin: i32, _predicted_seconds: f32) -> Vec<TrackedDevicePose> {
        let steam = self.0.borrow();
        (0..vrct_openvr::MAX_TRACKED_DEVICE_COUNT as u32).map(|i| match steam.poses.get(&i) {
            Some(m) => TrackedDevicePose { device_to_absolute_tracking: hmd(m), pose_is_valid: true, device_is_connected: true,
                                           ..Default::default() },
            None => TrackedDevicePose::default(),
        }).collect()
    }
    fn tracked_device_index_for_controller_role(&self, role: i32) -> u32 {
        match role {
            vrct_openvr::CONTROLLER_ROLE_LEFT_HAND => LEFT,
            vrct_openvr::CONTROLLER_ROLE_RIGHT_HAND => RIGHT,
            _ => vrct_openvr::TRACKED_DEVICE_INDEX_INVALID,
        }
    }
    fn controller_state(&self, index: u32) -> Option<ControllerState> {
        let steam = self.0.borrow();
        steam.poses.contains_key(&index).then(|| steam.buttons.get(&index).copied().unwrap_or_default())
    }
    fn poll_next_event(&self) -> Option<vrct_openvr::Event> {
        None
    }
    fn string_tracked_device_property(&self, _index: u32, _property: u32) -> String {
        String::new()
    }
    fn tracked_device_activity_level(&self, _index: u32) -> i32 {
        vrct_openvr::ACTIVITY_USER_INTERACTION
    }
    fn is_tracked_device_connected(&self, index: u32) -> bool {
        self.0.borrow().poses.contains_key(&index)
    }
    fn dxgi_output_info(&self) -> i32 {
        0
    }
}

impl VrOverlay for SteamVr {
    fn create_overlay(&self, key: &str, _name: &str) -> Result<u64, Error> {
        let mut steam = self.0.borrow_mut();
        steam.overlays.push(Shown { key: key.into(), alpha: 1.0, width: 1.0, ..Default::default() });
        Ok(steam.overlays.len() as u64)
    }
    fn destroy_overlay(&self, handle: u64) -> Result<(), Error> {
        self.with(handle, |o| o.visible = false)
    }
    fn show_overlay(&self, handle: u64) -> Result<(), Error> {
        self.with(handle, |o| o.visible = true)
    }
    fn hide_overlay(&self, handle: u64) -> Result<(), Error> {
        self.with(handle, |o| o.visible = false)
    }
    fn clear_overlay_texture(&self, handle: u64) -> Result<(), Error> {
        self.with(handle, |o| o.texture = (0, 0))
    }
    fn set_overlay_texture(&self, handle: u64, texture: &vrct_openvr::Texture) -> Result<(), Error> {
        let mut desc = Default::default();
        unsafe { ID3D11Texture2D::from_raw_borrowed(&texture.handle).unwrap().GetDesc(&mut desc) };
        self.with(handle, |o| o.texture = (desc.Width, desc.Height))
    }
    fn set_overlay_width_in_meters(&self, handle: u64, meters: f32) -> Result<(), Error> {
        self.with(handle, |o| o.width = meters as f64)
    }
    fn set_overlay_alpha(&self, handle: u64, alpha: f32) -> Result<(), Error> {
        self.with(handle, |o| o.alpha = alpha as f64)
    }
    fn set_overlay_color(&self, _handle: u64, _red: f32, _green: f32, _blue: f32) -> Result<(), Error> {
        ok()
    }
    fn set_overlay_sort_order(&self, _handle: u64, _order: u32) -> Result<(), Error> {
        ok()
    }
    fn set_overlay_transform_absolute(&self, handle: u64, _origin: i32, transform: &HmdMatrix34) -> Result<(), Error> {
        self.with(handle, |o| o.place = Some((None, from_hmd(transform))))
    }
    fn set_overlay_transform_tracked_device_relative(&self, handle: u64, device: u32, transform: &HmdMatrix34) -> Result<(), Error> {
        self.with(handle, |o| o.place = Some((Some(device), from_hmd(transform))))
    }
    fn set_overlay_texture_bounds(&self, handle: u64, bounds: &TextureBounds) -> Result<(), Error> {
        self.with(handle, |o| o.bounds = Some(*bounds))
    }
    /// Where the ray meets the overlay's rectangle (its height from the texture's shape), with
    /// SteamVR's UV: u across, v up from the centre in widths
    fn compute_overlay_intersection(&self, handle: u64, params: &IntersectionParams) -> Option<IntersectionResults> {
        let steam = self.0.borrow();
        let o = &steam.overlays[handle as usize - 1];
        let world = steam.world(o)?;
        let b = o.bounds.unwrap_or(TextureBounds { u_min: 0.0, v_min: 0.0, u_max: 1.0, v_max: 1.0 });
        let (tw, th) = (o.texture.0 as f64 * (b.u_max - b.u_min) as f64, o.texture.1 as f64 * (b.v_max - b.v_min) as f64);
        if tw <= 0.0 || th <= 0.0 {
            return None;
        }
        let height = o.width * th / tw;
        let source = params.source.map(f64::from);
        let direction = params.direction.map(f64::from);
        let normal = pose::axis(&world, 2);
        let denom = pose::dot(direction, normal);
        if denom.abs() < 1e-9 {
            return None;
        }
        let distance = pose::dot(pose::sub(pose::position(&world), source), normal) / denom;
        let point = pose::add(source, pose::scale(direction, distance));
        let local = pose::transform_point(&pose::inverse(&world), point);
        if distance <= 0.0 || local[0].abs() > o.width / 2.0 || local[1].abs() > height / 2.0 {
            return None;
        }
        Some(IntersectionResults {
            point: point.map(|v| v as f32),
            normal: normal.map(|v| v as f32),
            uvs: [(local[0] / o.width + 0.5) as f32, (local[1] / o.width + 0.5) as f32],
            distance: distance as f32,
        })
    }
}

impl VrRenderModels for SteamVr {
    fn component_state(&self, _model: &str, _component: &str, _state: &ControllerState, _mode: &ControllerModeState)
                       -> Option<ComponentState> {
        None
    }
}

fn warp() -> (ID3D11Device, ID3D11DeviceContext) {
    let (mut device, mut context) = (None, None);
    unsafe {
        D3D11CreateDevice(None, D3D_DRIVER_TYPE_WARP, Default::default(), D3D11_CREATE_DEVICE_FLAG(0), None, D3D11_SDK_VERSION,
                          Some(&mut device), None, Some(&mut context)).unwrap();
    }
    (device.unwrap(), context.unwrap())
}

pub(super) fn settings(tracker: &str, position: [f64; 6], width: f64) -> Settings {
    Settings { position, tracker: tracker.into(), opacity: 1.0, ui_scaling: width, display_duration: 5.0, fadeout_duration: 0.0,
               panel_size: None }
}

fn translation(p: Vec3) -> Mat4 {
    let mut m = pose::IDENTITY;
    pose::set_position(&mut m, p);
    m
}

/// A controller at `from` whose laser (its -Z tilted up, as vr_ui does) goes through `at`
fn aiming(from: Vec3, at: Vec3) -> Mat4 {
    let behind = pose::sub(from, pose::sub(at, from));
    let laser = pose::pose_facing(from, behind, None);
    pose::mul(&laser, &pose::inverse(&pose::laser_tilt(12.0)))
}

/// The worker, its frames and the made-up SteamVR; the events the app would get
struct Rig {
    steam: SteamVr,
    w: Worker,
    run: Run<'static>,
    events: Arc<Mutex<Vec<Event>>>,
    _commands: Sender<Command>,
}

impl Rig {
    fn new(sizes: Vec<(&str, Settings)>) -> Rig {
        let (commands, received) = mpsc::channel();
        let events = Arc::new(Mutex::new(vec![]));
        let sink = events.clone();
        let sizes = sizes.into_iter().map(|(n, s)| (n.to_string(), s)).collect();
        let mut w = Worker::new(sizes, received, Arc::new(|_| {}), Arc::new(move |e| sink.lock().unwrap().push(e)));
        let steam = SteamVr(Rc::default());
        steam.0.borrow_mut().poses.insert(HEAD, translation([0.0, 1.6, 0.0]));
        let vr = Vr { overlay: Box::new(steam.clone()), system: Box::new(steam.clone()), render_models: Box::new(steam.clone()) };
        let (device, context) = warp();
        let mut run = Run::new(vr, device, context, &w);
        run.init(&mut w).unwrap();
        Rig { steam, w, run, events, _commands: commands }
    }

    fn index(&self, size: &str) -> usize {
        self.w.index(size).unwrap()
    }

    /// The size shows an opaque image (`width` x `height` px)
    fn draw(&mut self, size: &str, width: usize, height: usize) {
        let i = self.index(size);
        self.run.update_image(&mut self.w, i, Image::new(width, height, [255, 255, 255, 255]));
    }

    fn hand(&self, hand: u32, pose: Mat4) {
        self.steam.0.borrow_mut().poses.insert(hand, pose);
    }

    fn lose(&self, device: u32) {
        self.steam.0.borrow_mut().poses.remove(&device);
    }

    fn buttons(&self, hand: u32, pressed: u64) {
        self.steam.0.borrow_mut().buttons.entry(hand).or_default().button_pressed = pressed;
    }

    fn stick(&self, hand: u32, x: f32, y: f32) {
        self.steam.0.borrow_mut().buttons.entry(hand).or_default().axis[0] = [x, y];
    }

    /// One frame (all but the VR view's capture), after `ms`
    fn frame(&mut self, ms: u64) {
        std::thread::sleep(Duration::from_millis(ms));
        self.run.step(&mut self.w);
    }

    /// The size's place in the room as SteamVR shows it
    fn world(&self, size: &str) -> Mat4 {
        let handle = self.run.handles[self.index(size)];
        let steam = self.steam.0.borrow();
        steam.world(&steam.overlays[handle as usize - 1]).unwrap()
    }

    fn shown(&self, key: &str) -> bool {
        self.steam.0.borrow().overlays.iter().any(|o| o.key == key && o.visible)
    }

    fn positions(&self) -> Vec<(String, Settings)> {
        self.events.lock().unwrap().iter().filter_map(|e| match e {
            Event::Position { size, settings } => Some((size.clone(), settings.clone())),
            _ => None,
        }).collect()
    }

    fn grabbed(&self) -> Option<usize> {
        self.run.grabbing.as_ref().map(|g| g.index)
    }
}

// A log window fixed in the room 1 m ahead at the height the right hand points to

const LOG_AT: Vec3 = [0.0, 1.2, -1.0];

fn room_log() -> Rig {
    let mut r = Rig::new(vec![("small", settings("Playspace", [LOG_AT[0], LOG_AT[1], -LOG_AT[2], 0.0, 0.0, 0.0], 0.4))]);
    r.draw("small", 400, 200);
    r
}

const HAND_AT: Vec3 = [0.2, 1.2, -0.3];

#[test]
fn pointing_shows_the_dot_and_a_grip_grabs_moves_and_saves_on_release() {
    let mut r = room_log();
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.frame(0);
    assert!(r.shown("VRCT_pointer_dot"));
    assert_eq!(r.grabbed(), None);

    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("small")));
    // the hand moves right (fast: followed at once, on the sphere round the eyes)
    r.hand(RIGHT, aiming(pose::add(HAND_AT, [0.3, 0.0, 0.0]), pose::add(LOG_AT, [0.3, 0.0, 0.0])));
    r.frame(20);
    let moved = pose::position(&r.world("small"));
    assert!(moved[0] > 0.2, "{moved:?}");

    r.buttons(RIGHT, 0);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    let saved = r.positions();
    assert_eq!(saved.len(), 1);
    assert_eq!(saved[0].0, "small");
    assert!(saved[0].1.position[0] > 0.2, "{:?}", saved[0].1.position);
    assert_eq!(r.w.sizes[r.index("small")].settings.position, saved[0].1.position);
}

#[test]
fn a_grip_held_before_pointing_does_not_grab() {
    let mut r = room_log();
    r.hand(RIGHT, aiming(HAND_AT, [2.0, 1.2, -1.0]));
    r.buttons(RIGHT, GRIP);
    r.frame(0);
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    // let go and squeeze again: now it grabs
    r.buttons(RIGHT, 0);
    r.frame(20);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("small")));
}

#[test]
fn a_clear_part_of_a_log_is_not_pointed_at_nor_grabbed() {
    let mut r = room_log();
    let i = r.index("small");
    r.run.update_image(&mut r.w, i, Image::new(400, 200, [0, 0, 0, 0]));
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.frame(0);
    assert!(!r.shown("VRCT_pointer_dot"));
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
}

#[test]
fn trigger_while_grabbing_scales_by_pushing_and_the_width_is_saved() {
    let mut r = room_log();
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    r.frame(20);
    let before = pose::position(&r.world("small"));
    r.buttons(RIGHT, GRIP | TRIGGER);
    r.frame(20);
    // pushed 0.15 m along the laser: twice as wide, the window held still
    let forward = pose::scale(pose::axis(&pose::mul(&aiming(HAND_AT, LOG_AT), &pose::laser_tilt(12.0)), 2), -1.0);
    r.hand(RIGHT, aiming(pose::add(HAND_AT, pose::scale(forward, 0.15)), LOG_AT));
    r.frame(20);
    let width = r.w.sizes[r.index("small")].settings.ui_scaling;
    assert!((width - 0.8).abs() < 1e-6, "{width}");
    assert!(pose::norm(pose::sub(pose::position(&r.world("small")), before)) < 1e-6);
    assert!(r.shown("VRCT_pointer_plus"));
    r.buttons(RIGHT, 0);
    r.frame(20);
    assert!((r.positions()[0].1.ui_scaling - 0.8).abs() < 1e-6);
}

#[test]
fn the_stick_pushes_a_grabbed_window_away() {
    let mut r = room_log();
    let head = [0.0, 1.6, 0.0];
    let distance = |r: &Rig| pose::norm(pose::sub(pose::position(&r.world("small")), head));
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    r.frame(20);
    let before = distance(&r);
    r.stick(RIGHT, 0.0, 1.0);
    for _ in 0..5 {
        r.frame(40);
    }
    r.stick(RIGHT, 0.0, 0.0);
    r.frame(40);
    assert!(distance(&r) > before + 0.1, "{before} -> {}", distance(&r));
}

#[test]
fn losing_the_hand_while_grabbing_keeps_the_window_where_it_showed() {
    let mut r = room_log();
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    r.frame(20);
    let shown = r.world("small");
    r.lose(RIGHT);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    assert_eq!(r.positions().len(), 1);
    assert!(pose::norm(pose::sub(pose::position(&r.world("small")), pose::position(&shown))) < 1e-6);
}

#[test]
fn a_window_on_a_hand_is_not_grabbed_by_that_hand() {
    // on the right hand, held up in front of the left one
    let mut r = Rig::new(vec![("small", settings("RightHand", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.3))]);
    r.draw("small", 300, 150);
    r.hand(RIGHT, translation([0.0, 1.2, -0.5]));
    r.frame(0);
    let at = pose::position(&r.world("small"));
    r.hand(RIGHT, translation([0.0, 1.2, -0.5]));
    r.hand(LEFT, aiming([-0.3, 1.2, 0.0], at));
    // the right hand's own laser does not take it, the left one does
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    r.buttons(LEFT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("small")));
}

#[test]
fn a_grip_wakes_a_faded_log() {
    let mut r = room_log();
    let i = r.index("small");
    r.w.sizes[i].settings.fadeout_duration = 1.0;
    r.w.sizes[i].settings.display_duration = 0.0;
    r.w.sizes[i].last_update = Instant::now() - Duration::from_secs(5);
    r.run.update(&mut r.w, i);
    let alpha = |r: &Rig| r.steam.0.borrow().overlays[r.run.handles[i] as usize - 1].alpha;
    assert_eq!(alpha(&r), 0.0);
    r.hand(RIGHT, aiming(HAND_AT, LOG_AT));
    r.buttons(RIGHT, GRIP);
    r.frame(0);
    assert_eq!(r.grabbed(), Some(i));
    assert_eq!(alpha(&r), 1.0);
}

// The VR UI: the log window fixed in the room, the launcher on the left wrist, the VR view
// captured once (its size known, the layout applied) and the intro over

const PANEL_AT: Vec3 = [0.0, 1.2, -1.0];
const WRIST: Vec3 = [-0.2, 1.0, -0.3];

fn vr_ui() -> Rig {
    let mut panel = settings("Playspace", [PANEL_AT[0], PANEL_AT[1], -PANEL_AT[2], 0.0, 0.0, 0.0], 0.6);
    panel.panel_size = Some((900, 700));
    let mut r = Rig::new(vec![("panel", panel), ("launcher", settings("LeftHand", [0.0; 6], 0.2))]);
    r.hand(LEFT, translation(WRIST));
    r.run.panel.image_size = Some(r.w.layout.atlas);
    r.run.panel.layout_applied = Some((r.w.layout_gen, r.w.layout));
    r.run.set_launcher_intro(&mut r.w, Intro::Idle);
    r.w.vr_windows_wanted = (true, false);
    r.frame(0);
    r
}

/// The head 0.4 m in front of the launcher's face, looking at it
fn look_at_launcher(r: &Rig) -> Mat4 {
    let launcher = r.world("launcher");
    let (at, face) = (pose::position(&launcher), pose::axis(&launcher, 2));
    let head = pose::add(at, pose::scale(face, 0.4));
    pose::pose_facing(head, pose::add(head, pose::sub(head, at)), None)
}

#[test]
fn the_launcher_shows_when_the_wrist_is_looked_at_and_hides_a_moment_after() {
    let mut r = vr_ui();
    assert!(!r.run.launcher_shown);
    let looking = look_at_launcher(&r);
    r.hand(HEAD, looking);
    r.frame(0);
    r.frame(70);
    assert!(r.run.launcher_shown);
    r.frame(110);
    assert_eq!(r.run.launcher_alpha, 1.0);
    // looking away: still there for a moment (no flicker), then gone
    let head = pose::position(&looking);
    r.hand(HEAD, pose::pose_facing(head, pose::position(&r.world("launcher")), None));
    r.frame(0);
    r.frame(150);
    assert!(r.run.launcher_shown);
    r.frame(200);
    assert!(!r.run.launcher_shown);
}

#[test]
fn without_auto_hide_the_launcher_is_always_shown() {
    let mut r = vr_ui();
    r.w.launcher_auto_hide = false;
    r.hand(HEAD, translation([0.0, 1.6, 0.0]));
    r.frame(0);
    assert!(r.run.launcher_shown);
}

#[test]
fn reset_flies_the_launcher_back_to_the_left_wrist_then_saves_the_defaults() {
    let mut r = vr_ui();
    let li = r.index("launcher");
    let defaults = settings("LeftHand", [0.05, -0.04, -0.01, 9.0, -22.0, -17.0], 0.2);
    r.w.launcher_defaults = Some(defaults.clone());
    r.hand(RIGHT, translation([0.3, 1.0, -0.3]));
    r.run.update_position(&mut r.w, li, [0.1, 0.1, 0.1, 0.0, 0.0, 0.0], "RightHand");
    r.w.launcher_auto_hide = false;
    r.frame(0);
    r.w.request_launcher_reset(false);
    r.frame(0);
    assert!(r.run.launcher_return.is_some());
    assert!(r.run.launcher_shown && !r.run.launcher_interactive);
    r.frame(350);
    assert!(r.run.launcher_return.is_none());
    let s = &r.w.sizes[li].settings;
    assert_eq!((s.position, s.tracker.as_str(), s.ui_scaling), (defaults.position, "LeftHand", 0.2));
    assert_eq!(r.positions().last().map(|p| p.0.as_str()), Some("launcher"));
    let handle = r.run.handles[li];
    assert_eq!(r.steam.0.borrow().overlays[handle as usize - 1].place.map(|p| p.0), Some(Some(LEFT)));
}

#[test]
fn a_launcher_let_go_too_far_comes_back_within_reach_of_the_same_wrist() {
    let mut r = vr_ui();
    let li = r.index("launcher");
    r.w.launcher_defaults = Some(settings("LeftHand", [0.05, -0.04, -0.01, 9.0, -22.0, -17.0], 0.2));
    let far = crate::math::position_transform(crate::math::Tracker::LeftHand, [0.5, 0.0, 0.0, 30.0, 0.0, 0.0]);
    r.run.commit_position(&mut r.w, li, &far);
    assert!(r.w.launcher_reset_requested);
    r.frame(0);
    r.frame(350);
    let s = &r.w.sizes[li].settings;
    assert_eq!(s.tracker, "LeftHand");
    assert!(pose::norm([s.position[0], s.position[1], s.position[2]]) <= pose::LAUNCHER_REACH_M + 1e-9, "{:?}", s.position);
    // the angle is kept (only pulled in)
    assert!((s.position[3] - 30.0).abs() < 1e-3, "{:?}", s.position);
}

fn aim_at_panel(r: &mut Rig) {
    r.hand(RIGHT, aiming([0.2, 1.2, -0.3], PANEL_AT));
}

#[test]
fn a_locked_log_window_is_not_grabbed() {
    let mut r = vr_ui();
    aim_at_panel(&mut r);
    r.w.panel_locked = true;
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    r.w.panel_locked = false;
    r.buttons(RIGHT, 0);
    r.frame(20);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("panel")));
}

#[test]
fn the_bar_shows_after_pointing_at_the_log_a_moment() {
    let mut r = vr_ui();
    aim_at_panel(&mut r);
    r.frame(0);
    assert!(!r.run.toolbar_visible);
    r.frame(350);
    assert!(r.run.toolbar_visible);
    assert!(r.shown("VRCT_toolbar"));
}

#[test]
fn closing_the_log_while_it_is_grabbed_lets_it_go() {
    let mut r = vr_ui();
    aim_at_panel(&mut r);
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("panel")));
    r.w.vr_windows_wanted = (false, false);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    let handle = r.run.handles[r.index("panel")];
    assert!(!r.steam.0.borrow().overlays[handle as usize - 1].visible);
}

#[test]
fn a_recalled_log_comes_in_front_of_the_eyes() {
    let mut r = vr_ui();
    let head = pose::pose_facing([0.0, 1.6, 0.0], [0.0, 1.6, 1.0], None);
    r.hand(HEAD, head);
    r.w.recall_requested = Some(Instant::now());
    r.frame(0);
    let expected = pose::position(&pose::recall_pose(&head));
    let got = pose::position(&r.world("panel"));
    assert!(pose::norm(pose::sub(got, expected)) < 1e-3, "{got:?} {expected:?}");
}

#[test]
fn only_pointer_moves_of_4_px_or_more_are_told() {
    let mut r = vr_ui();
    let told = |r: &Rig| r.events.lock().unwrap().iter().filter(|e| matches!(e, Event::Pointer(_))).count();
    // (the left hand's laser may point at the log already)
    let before = told(&r);
    r.run.notify_pointer(&mut r.w, Some((100, 100)));
    r.run.notify_pointer(&mut r.w, Some((103, 102)));
    assert_eq!(told(&r) - before, 1);
    r.run.notify_pointer(&mut r.w, Some((104, 100)));
    assert_eq!(told(&r) - before, 2);
    r.run.notify_pointer(&mut r.w, None);
    assert_eq!(told(&r) - before, 3);
}

/// The point on the log window `x`, `y` metres from its centre (right, up)
fn on_panel(x: f64, y: f64) -> Vec3 {
    pose::add(PANEL_AT, [x, y, 0.0])
}

const PANEL_HALF: (f64, f64) = (0.3, 0.3 * 700.0 / 900.0);

#[test]
fn dragging_a_corner_resizes_the_log_and_the_opposite_corner_stays() {
    let mut r = vr_ui();
    let pi = r.index("panel");
    let hand = [0.2, 1.2, -0.3];
    r.hand(RIGHT, aiming(hand, on_panel(-0.29, -0.225)));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert!(r.run.resizing.is_some());
    r.hand(RIGHT, aiming(hand, on_panel(-0.39, -0.3)));
    r.frame(20);
    assert!(r.shown("VRCT_resize_ghost"));
    r.buttons(RIGHT, 0);
    r.frame(20);
    assert!(r.run.resizing.is_none());
    let s = r.w.sizes[pi].settings.clone();
    let (width, height) = s.panel_size.unwrap();
    assert!(width > 1000 && height > 750, "{width}x{height}");
    // a px stays as long: the width in metres grows with it
    assert!((s.ui_scaling - 0.6 * width as f64 / 900.0).abs() < 1e-9);
    // the top right corner where it was
    let half = (s.ui_scaling / 2.0, s.ui_scaling * height as f64 / width as f64 / 2.0);
    let corner = [s.position[0] + half.0, s.position[1] + half.1];
    assert!((corner[0] - PANEL_HALF.0).abs() < 2e-3 && (corner[1] - (PANEL_AT[1] + PANEL_HALF.1)).abs() < 2e-3, "{corner:?}");
    assert_eq!(r.positions().last().map(|p| p.0.as_str()), Some("panel"));
}

#[test]
fn the_top_right_corner_inside_is_the_close_button_not_a_handle() {
    let mut r = vr_ui();
    r.hand(RIGHT, aiming([0.2, 1.2, -0.3], on_panel(0.29, 0.225)));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert!(r.run.resizing.is_none());
    assert_eq!(r.grabbed(), Some(r.index("panel")));
}

#[test]
fn resizing_stops_at_the_largest_size() {
    let mut r = vr_ui();
    let pi = r.index("panel");
    let hand = [0.2, 1.2, -0.3];
    r.hand(RIGHT, aiming(hand, on_panel(-0.29, -0.225)));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    r.hand(RIGHT, aiming(hand, on_panel(-3.0, -3.0)));
    r.frame(20);
    r.buttons(RIGHT, 0);
    r.frame(20);
    let (w, h) = r.w.sizes[pi].settings.panel_size.unwrap();
    assert_eq!((w, h), crate::layout::clamp_panel_size(1e9, 1e9));
}
