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
    roles: Option<[u32; 2]>,
    poses: HashMap<u32, Mat4>,
    buttons: HashMap<u32, ControllerState>,
    overlays: Vec<Shown>,
    dashboard: bool,
    input_failure: bool,
    input_updates: Vec<Vec<u32>>,
    unavailable: HashSet<u32>,
    tip: Option<Mat4>,
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
    fn update_input(&self, pointing: &[u32]) -> Result<(), Error> {
        let mut steam = self.0.borrow_mut();
        steam.input_updates.push(pointing.to_vec());
        if steam.input_failure { Err(Error { code: 1, message: "test failure".into() }) } else { Ok(()) }
    }
    fn device_to_absolute_tracking_pose(&self, _origin: i32, _predicted_seconds: f32) -> Vec<TrackedDevicePose> {
        let steam = self.0.borrow();
        (0..vrct_openvr::MAX_TRACKED_DEVICE_COUNT as u32).map(|i| match steam.poses.get(&i) {
            Some(m) => TrackedDevicePose { device_to_absolute_tracking: hmd(m), pose_is_valid: true, device_is_connected: true,
                                           ..Default::default() },
            None => TrackedDevicePose::default(),
        }).collect()
    }
    fn tracked_device_index_for_controller_role(&self, role: i32) -> u32 {
        let hands = self.0.borrow().roles.unwrap_or([LEFT, RIGHT]);
        match role {
            vrct_openvr::CONTROLLER_ROLE_LEFT_HAND => hands[0],
            vrct_openvr::CONTROLLER_ROLE_RIGHT_HAND => hands[1],
            _ => vrct_openvr::TRACKED_DEVICE_INDEX_INVALID,
        }
    }
    // (no clicks reach the VR view here: no window to send them to)
    fn trigger_haptic_pulse(&self, _index: u32, _duration_us: u16) {}
    fn controller_state(&self, index: u32) -> Option<ControllerState> {
        let steam = self.0.borrow();
        (steam.poses.contains_key(&index) && !steam.unavailable.contains(&index)).then(|| steam.buttons.get(&index).copied().unwrap_or_default())
    }
    fn poll_next_event(&self) -> Option<vrct_openvr::Event> {
        None
    }
    fn string_tracked_device_property(&self, _index: u32, _property: u32) -> String {
        if self.0.borrow().tip.is_some() { "test-model".into() } else { String::new() }
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
    fn is_dashboard_visible(&self) -> bool { self.0.borrow().dashboard }
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
        self.0.borrow().tip.map(|tip| ComponentState { tracking_to_component_local: hmd(&tip), ..Default::default() })
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
               panel_size: None, locked: false }
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
        let (commands, received) = command_wait::channel();
        let events = Arc::new(Mutex::new(vec![]));
        let sink = events.clone();
        let sizes = sizes.into_iter().map(|(n, s)| (n.to_string(), s)).collect();
        let mut w = Worker::new(sizes, received, Arc::new(|_| {}), Arc::new(move |e| sink.lock().unwrap().push(e)));
        let steam = SteamVr(Rc::default());
        steam.0.borrow_mut().poses.insert(HEAD, translation([0.0, 1.6, 0.0]));
        let vr = Vr { overlay: Box::new(steam.clone()), system: Box::new(steam.clone()), render_models: Box::new(steam.clone()) };
        let (device, context) = warp();
        let mut run = Run::new(vr, device, context);
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
            Event::Position { size, settings, .. } => Some((size.clone(), settings.clone())),
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
fn a_grip_squeezed_during_the_other_hands_grab_does_not_grab_after_it() {
    let (mut r, at) = with_keyboard();
    r.hand(RIGHT, aiming(HAND_AT, at));
    r.hand(LEFT, aiming([-0.2, 1.2, -0.3], at));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("keyboard")));
    // the left hand grips (holding something in the game) while the right one has it
    r.buttons(LEFT, GRIP);
    r.frame(20);
    r.buttons(RIGHT, 0);
    r.frame(20);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
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
fn a_locked_log_is_not_grabbed_but_the_other_is() {
    let at = |x: f64| [x, LOG_AT[1], LOG_AT[2]];
    let place = |x: f64| settings("Playspace", [x, LOG_AT[1], -LOG_AT[2], 0.0, 0.0, 0.0], 0.4);
    let mut r = Rig::new(vec![("small", place(-0.5)), ("large", place(0.5))]);
    r.draw("small", 400, 200);
    r.draw("large", 400, 200);
    let (small, large) = (r.index("small"), r.index("large"));
    r.w.sizes[small].settings.locked = true;
    r.hand(RIGHT, aiming(HAND_AT, at(-0.5)));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    r.buttons(RIGHT, 0);
    r.frame(20);
    r.hand(RIGHT, aiming(HAND_AT, at(0.5)));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(large));
}

#[test]
fn the_last_lock_command_wins_while_stopped() {
    // update_locked(on) then update_locked(off) before the thread runs: what is applied at start is off
    let mut r = Rig::new(vec![("small", settings("Playspace", [0.0; 6], 0.4))]);
    r._commands.send(Command::Locked("small".into(), true)).unwrap();
    r._commands.send(Command::Locked("small".into(), false)).unwrap();
    while let Ok(c) = r.w.commands.try_recv() {
        r.w.apply_offline(c);
    }
    assert!(!r.w.sizes[r.index("small")].settings.locked);
}

#[test]
fn a_lock_command_reaches_the_running_overlay() {
    let mut r = Rig::new(vec![("small", settings("Playspace", [0.0; 6], 0.4))]);
    let i = r.index("small");
    r._commands.send(Command::Locked("small".into(), true)).unwrap();
    r.w.wait(Duration::from_millis(1), Some(&mut r.run));
    assert!(r.w.sizes[i].settings.locked);
    assert!(r.w.shared.lock().unwrap().settings.iter().any(|(n, s)| n == "small" && s.locked));
    r._commands.send(Command::Locked("small".into(), false)).unwrap();
    r.w.wait(Duration::from_millis(1), Some(&mut r.run));
    assert!(!r.w.sizes[i].settings.locked);
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
    let mut r = Rig::new(vec![("panel", panel), ("launcher", settings("LeftHand", [0.0; 6], 0.2)),
                              ("keyboard", settings("Playspace", [0.0; 6], 0.6))]);
    r.hand(LEFT, translation(WRIST));
    r.run.panel.image_size = Some(r.w.layout.atlas);
    r.run.panel.layout_applied = Some((r.w.layout_gen, r.w.layout));
    r.run.set_launcher_intro(&mut r.w, Intro::Idle);
    r.w.vr_windows_wanted = (true, false, false);
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
fn a_press_ends_when_the_grip_is_pressed_and_the_held_trigger_is_no_new_press() {
    let mut r = vr_ui();
    aim_at_panel(&mut r);
    // the right hand holds a press on the VR view (as a held ← key)
    r.run.panel_input.insert(RIGHT, (true, Some((10, 10))));
    r.run.mouse_owner = Some(RIGHT);
    r.buttons(RIGHT, GRIP | TRIGGER);
    r.frame(0);
    assert_eq!(r.run.mouse_owner, None);
    assert!(!r.run.panel_input.contains_key(&RIGHT));
    assert!(r.run.trigger_blocked.contains(&RIGHT));
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
    r.w.vr_windows_wanted = (false, false, false);
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
    r.w.recall_requested = Some((Region::Panel, Instant::now()));
    r.frame(0);
    let expected = pose::position(&pose::recall_pose(&head));
    let got = pose::position(&r.world("panel"));
    assert!(pose::norm(pose::sub(got, expected)) < 1e-3, "{got:?} {expected:?}");
}

/// The log window turned into a subtitle form (fading, at its own place)
fn to_form(r: &mut Rig, form: &str, tracker: &str, locked: bool) {
    let pi = r.index("panel");
    let s = Settings { tracker: tracker.into(), fadeout_duration: 2.0, ..r.w.sizes[pi].settings.clone() };
    r.run.apply_panel_form(&mut r.w, form.into(), s, locked);
}

fn alpha_of(r: &Rig, size: &str) -> f64 {
    r.steam.0.borrow().overlays[r.run.handles[r.index(size)] as usize - 1].alpha
}

#[test]
fn a_locked_subtitle_is_not_pointed_at_and_leaves_the_input_to_the_game() {
    let mut r = vr_ui();
    to_form(&mut r, "single_line", "Playspace", true);
    aim_at_panel(&mut r);
    r.frame(0);
    assert_eq!(r.steam.0.borrow().input_updates.last(), Some(&vec![]));
    assert!(!r.shown("VRCT_pointer_dot"));
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    assert_eq!(r.w.pointer_notified, None);
}

#[test]
fn an_unlocked_subtitle_is_grabbed() {
    let mut r = vr_ui();
    to_form(&mut r, "multi_line", "Playspace", false);
    let pi = r.index("panel");
    r.run.show_panel(&mut r.w, pi);
    aim_at_panel(&mut r);
    r.frame(0);
    assert!(r.steam.0.borrow().input_updates.last().is_some_and(|hands| hands.contains(&RIGHT)));
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("panel")));
}

#[test]
fn changing_form_while_grabbed_saves_the_place_to_the_form_it_was_moved_in() {
    let mut r = vr_ui();
    aim_at_panel(&mut r);
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("panel")));
    r.events.lock().unwrap().clear();
    to_form(&mut r, "single_line", "HMD", true);
    assert_eq!(r.grabbed(), None);
    let forms: Vec<Option<String>> = r.events.lock().unwrap().iter().filter_map(|e| match e {
        Event::Position { form, .. } => Some(form.clone()),
        _ => None,
    }).collect();
    assert_eq!(forms, vec![Some("history".to_string())]);
    assert_eq!(r.w.panel_form, "single_line");
    // the new form's own place and lock (the settings never lock: the lock is panel_locked)
    let pi = r.index("panel");
    assert_eq!((r.w.sizes[pi].settings.tracker.as_str(), r.w.sizes[pi].settings.locked, r.w.panel_locked), ("HMD", false, true));
}

#[test]
fn a_changed_form_is_clear_until_shown_and_then_after_a_while_anyway() {
    let mut r = vr_ui();
    to_form(&mut r, "multi_line", "Playspace", false);
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    // a grip on it does not show the old picture either
    aim_at_panel(&mut r);
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    r.run.panel_hidden_since = Some(Instant::now() - Duration::from_secs(2));
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 1.0);
    assert!(r.run.panel_hidden_since.is_none());
}

#[test]
fn the_history_that_never_fades_is_clear_too_while_changing_form() {
    let mut r = vr_ui();
    let pi = r.index("panel");
    let s = r.w.sizes[pi].settings.clone();
    assert_eq!(s.fadeout_duration, 0.0);
    r.run.apply_panel_form(&mut r.w, "history".into(), s, false);
    r.frame(0);
    r.frame(20);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    r.run.show_panel(&mut r.w, pi);
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 1.0);
}

#[test]
fn recalling_a_subtitle_on_the_head_only_shows_it_where_it_is() {
    let mut r = vr_ui();
    let head = pose::pose_facing([0.0, 1.6, 0.0], [0.0, 1.6, 1.0], None);
    r.hand(HEAD, head);
    to_form(&mut r, "single_line", "HMD", true);
    let pi = r.index("panel");
    r.run.show_panel(&mut r.w, pi);
    let before = (r.w.sizes[pi].settings.clone(), r.world("panel"));
    // faded out
    r.w.sizes[pi].last_update = Instant::now() - Duration::from_secs(60);
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    r.events.lock().unwrap().clear();
    r.w.recall_requested = Some((Region::Panel, Instant::now()));
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 1.0);
    assert_eq!((r.w.sizes[pi].settings.clone(), r.world("panel")), before);
    assert!(r.positions().is_empty());
}

#[test]
fn a_subtitle_not_on_the_head_is_recalled_in_front_of_the_eyes_as_the_history() {
    let mut r = vr_ui();
    let head = pose::pose_facing([0.0, 1.6, 0.0], [0.0, 1.6, 1.0], None);
    r.hand(HEAD, head);
    to_form(&mut r, "multi_line", "LeftHand", true);
    r.w.recall_requested = Some((Region::Panel, Instant::now()));
    r.frame(0);
    let pi = r.index("panel");
    assert_eq!(r.w.sizes[pi].settings.tracker, "Playspace");
    let expected = pose::position(&pose::recall_pose(&head));
    let got = pose::position(&r.world("panel"));
    assert!(pose::norm(pose::sub(got, expected)) < 1e-3, "{got:?} {expected:?}");
}

#[test]
fn a_faded_subtitle_is_not_pointed_at_nor_woken_by_the_laser() {
    let mut r = vr_ui();
    to_form(&mut r, "multi_line", "Playspace", false);
    let pi = r.index("panel");
    r.run.show_panel(&mut r.w, pi);
    r.w.sizes[pi].last_update = Instant::now() - Duration::from_secs(60);
    aim_at_panel(&mut r);
    r.frame(0);
    r.frame(20);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    assert_eq!(r.steam.0.borrow().input_updates.last(), Some(&vec![]));
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
}

#[test]
fn a_shown_subtitle_pointed_at_does_not_fade() {
    let mut r = vr_ui();
    to_form(&mut r, "multi_line", "Playspace", false);
    let pi = r.index("panel");
    r.run.show_panel(&mut r.w, pi);
    // its display time almost over
    r.w.sizes[pi].last_update = Instant::now() - Duration::from_millis(4900);
    aim_at_panel(&mut r);
    r.frame(0);
    assert!(r.w.sizes[pi].last_update.elapsed() < Duration::from_secs(1));
}

#[test]
fn a_capture_begun_before_the_new_content_does_not_count_and_the_next_one_shows_it() {
    let mut r = vr_ui();
    to_form(&mut r, "multi_line", "Playspace", false);
    let before = Instant::now();
    std::thread::sleep(Duration::from_millis(2));
    r.run.reveal_panel();
    // a PrintWindow begun before, sent a frame late (it may hold the new content)
    r.run.panel.last_raw = Some(crate::panel::Frame::Gpu(7));
    r.run.after_transfer(&mut r.w, before, true);
    assert!(r.run.panel.last_raw.is_none(), "the next capture of the same picture must be sent");
    assert!(r.run.panel_hidden_since.is_some());
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    r.run.after_transfer(&mut r.w, Instant::now(), true);
    assert!(r.run.panel_hidden_since.is_none() && r.run.panel_reveal_at.is_none());
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 1.0);
}

#[test]
fn a_new_line_shows_a_faded_subtitle_and_its_display_time_counts_from_then() {
    let mut r = vr_ui();
    to_form(&mut r, "single_line", "HMD", true);
    let pi = r.index("panel");
    r.run.show_panel(&mut r.w, pi);
    r.w.sizes[pi].last_update = Instant::now() - Duration::from_secs(60);
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    r.run.reveal_panel();
    // a capture not sent (the same picture): not yet
    r.run.after_transfer(&mut r.w, Instant::now(), false);
    r.frame(0);
    assert_eq!(alpha_of(&r, "panel"), 0.0);
    r.run.after_transfer(&mut r.w, Instant::now(), true);
    r.frame(20);
    assert_eq!(alpha_of(&r, "panel"), 1.0);
    assert!(r.w.sizes[pi].last_update.elapsed() < Duration::from_secs(1));
}

#[test]
fn a_subtitle_opened_again_waits_for_its_new_picture() {
    let mut r = vr_ui();
    to_form(&mut r, "multi_line", "Playspace", true);
    let pi = r.index("panel");
    r.run.show_panel(&mut r.w, pi);
    r.w.vr_windows_wanted = (false, false, false);
    r.frame(0);
    r.w.vr_windows_wanted = (true, false, false);
    r.frame(0);
    assert!(r.run.panel_hidden_since.is_some());
    assert_eq!(alpha_of(&r, "panel"), 0.0);
}

#[test]
fn a_subtitle_may_be_lower_than_the_history() {
    let mut r = vr_ui();
    let pi = r.index("panel");
    let low = Settings { panel_size: Some((1200, 180)), ..r.w.sizes[pi].settings.clone() };
    r.run.apply_panel_form(&mut r.w, "single_line".into(), low.clone(), true);
    assert_eq!(r.w.layout.panel_size(), (1200, 180));
    r.run.apply_panel_form(&mut r.w, "history".into(), low, false);
    assert_eq!(r.w.layout.panel_size(), (1200, 400));
}

#[test]
fn changing_form_drops_an_anchor_asked_for_the_form_before() {
    let mut r = vr_ui();
    r.w.requested_anchor = Some("LeftHand".into());
    to_form(&mut r, "single_line", "HMD", true);
    assert_eq!(r.w.requested_anchor, None);
}

#[test]
fn a_worker_made_again_after_a_stop_keeps_the_form_and_lock() {
    let mut r = vr_ui();
    to_form(&mut r, "single_line", "HMD", true);
    r.w.publish(false);
    let shared = r.w.shared.lock().unwrap().clone();
    let (_commands, received) = command_wait::channel();
    let again = Worker::from_shared(shared, received, Arc::new(|_| {}), Arc::new(|_| {}));
    assert_eq!((again.panel_form.as_str(), again.panel_locked, again.layout), ("single_line", true, r.w.layout));
}

#[test]
fn each_hand_pointing_at_the_vr_ui_shows_its_own_dot() {
    let mut r = vr_ui();
    aim_at_panel(&mut r);
    r.hand(LEFT, aiming([-0.2, 1.2, -0.3], PANEL_AT));
    r.frame(0);
    assert!(r.shown("VRCT_pointer_dot") && r.shown("VRCT_pointer_dot_other"));
    // one hand away: one dot
    r.hand(LEFT, aiming([-0.2, 1.2, -0.3], [-3.0, 1.2, 0.0]));
    r.frame(0);
    assert!(r.shown("VRCT_pointer_dot") && !r.shown("VRCT_pointer_dot_other"));
}

#[test]
fn the_keyboard_opens_and_is_recalled_in_front_of_the_eyes_facing_them() {
    let mut r = vr_ui();
    let head = pose::pose_facing([0.0, 1.6, 0.0], [0.0, 1.6, 1.0], None);
    r.hand(HEAD, head);
    let handle = r.run.handles[r.index("keyboard")];
    assert!(!r.steam.0.borrow().overlays[handle as usize - 1].visible);
    r.w.vr_windows_wanted = (true, false, true);
    r.frame(0);
    assert!(r.steam.0.borrow().overlays[handle as usize - 1].visible);
    let in_front = |r: &Rig, head: &Mat4| {
        let keyboard = r.world("keyboard");
        let at = pose::position(&keyboard);
        assert!(pose::norm(pose::sub(at, pose::position(&pose::recall_pose(head)))) < 1e-3, "{at:?}");
        // its face (+z) toward the eyes
        let to_eyes = pose::sub(pose::position(head), at);
        let face = pose::axis(&keyboard, 2);
        assert!(face.iter().zip(to_eyes).map(|(a, b)| a * b).sum::<f64>() / pose::norm(to_eyes) > 0.99, "{face:?}");
    };
    in_front(&r, &head);
    // turned away, then recalled: in front again
    let turned = pose::pose_facing([0.0, 1.6, 0.0], [1.0, 1.6, 0.0], None);
    r.hand(HEAD, turned);
    r.w.recall_requested = Some((Region::Keyboard, Instant::now()));
    r.frame(0);
    in_front(&r, &turned);
    assert!(r.w.recall_requested.is_none());
    r.w.vr_windows_wanted = (true, false, false);
    r.frame(0);
    assert!(!r.steam.0.borrow().overlays[handle as usize - 1].visible);
}

#[test]
fn keyboard_recall_waits_for_head_tracking_and_applies_once() {
    let (mut r, _) = with_keyboard();
    let before = r.world("keyboard");
    r.lose(HEAD);
    r.run.apply(&mut r.w, Command::Recall(Region::Keyboard));
    r.frame(0);
    assert!(r.w.recall_requested.is_some(), "an unavailable head must not consume recall");
    assert_eq!(r.world("keyboard"), before);
    assert!(r.positions().is_empty());
    let head = pose::pose_facing([1.0, 1.7, 0.0], [2.0, 1.7, 0.0], None);
    r.hand(HEAD, head);
    r.frame(0);
    assert!(r.w.recall_requested.is_none());
    let at = pose::position(&r.world("keyboard"));
    assert!(pose::norm(pose::sub(at, pose::position(&pose::recall_pose(&head)))) < 1e-3);
    assert_eq!(r.positions().len(), 1);
    r.frame(0);
    assert_eq!(r.positions().len(), 1, "the completed recall must not repeat");
}

#[test]
fn keyboard_recall_expires_before_moving_and_explicit_hide_cancels_it() {
    let (mut r, _) = with_keyboard();
    let before = r.world("keyboard");
    let head = pose::pose_facing([1.0, 1.7, 0.0], [2.0, 1.7, 0.0], None);
    r.hand(HEAD, head);
    r.w.recall_requested = Some((Region::Keyboard, Instant::now() - Duration::from_secs(2)));
    r.frame(0);
    assert!(r.w.recall_requested.is_none());
    assert_eq!(r.world("keyboard"), before, "expired requests must not jump to a new pose");
    assert!(r.positions().is_empty());
    r.run.apply(&mut r.w, Command::Recall(Region::Keyboard));
    r.run.apply(&mut r.w, Command::VrWindows(false, false, false));
    assert!(r.w.recall_requested.is_none(), "explicit hide cancels a pending recall");
    r.frame(0);
    assert!(r.run.hidden.contains(&Region::Keyboard));
    assert!(r.positions().is_empty());
}

#[test]
fn keyboard_recall_during_grab_waits_for_release_but_does_not_outlive_its_deadline() {
    for expired in [false, true] {
        let (mut r, at) = with_keyboard();
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.frame(0);
        r.buttons(RIGHT, GRIP);
        r.frame(0);
        assert_eq!(r.grabbed(), Some(r.index("keyboard")));
        r.hand(RIGHT, aiming(pose::add(HAND_AT, [0.3, 0.0, 0.0]), pose::add(at, [0.3, 0.0, 0.0])));
        r.frame(20);
        r.w.recall_requested = Some((Region::Keyboard, Instant::now() - if expired { Duration::from_secs(2) } else { Duration::ZERO }));
        r.frame(0);
        assert_eq!(r.w.recall_requested.is_none(), expired);
        assert_eq!(r.grabbed(), Some(r.index("keyboard")), "recall must not interrupt a grab");
        r.buttons(RIGHT, 0);
        r.frame(0);
        assert!(r.grabbed().is_none());
        let released = r.world("keyboard");
        r.events.lock().unwrap().clear();
        r.frame(0);
        assert!(r.w.recall_requested.is_none());
        if expired {
            assert_eq!(r.world("keyboard"), released);
            assert!(r.positions().is_empty());
        } else {
            let at = pose::position(&r.world("keyboard"));
            let head = translation([0.0, 1.6, 0.0]);
            assert!(pose::norm(pose::sub(at, pose::position(&pose::recall_pose(&head)))) < 1e-3);
            assert_eq!(r.positions().len(), 1);
        }
    }
}

#[test]
fn keyboard_open_waits_for_head_tracking_without_showing_the_old_position() {
    let mut r = vr_ui();
    let keyboard = r.index("keyboard");
    let handle = r.run.handles[keyboard];
    r.events.lock().unwrap().clear();
    r.lose(HEAD);
    // Recall may arrive before the UI's shown command; it must survive that ordering.
    r.run.apply(&mut r.w, Command::Recall(Region::Keyboard));
    r.frame(0);
    assert!(r.w.recall_requested.is_some());
    r.run.apply(&mut r.w, Command::VrWindows(false, false, true));
    r.frame(0);
    assert!(r.run.hidden.contains(&Region::Keyboard));
    assert!(!r.steam.0.borrow().overlays[handle as usize - 1].visible);
    assert!(r.positions().is_empty());
    let head = pose::pose_facing([1.0, 1.7, 0.0], [2.0, 1.7, 0.0], None);
    r.hand(HEAD, head);
    r.frame(0);
    assert!(!r.run.hidden.contains(&Region::Keyboard));
    assert!(r.steam.0.borrow().overlays[handle as usize - 1].visible);
    assert!(r.w.recall_requested.is_none());
    let at = pose::position(&r.world("keyboard"));
    assert!(pose::norm(pose::sub(at, pose::position(&pose::recall_pose(&head)))) < 1e-3);
    assert_eq!(r.positions().len(), 1, "opening and recall must share one placement");
}

#[test]
fn only_pointer_moves_of_4_px_or_more_are_told() {
    let mut r = vr_ui();
    let told = |r: &Rig| r.events.lock().unwrap().iter().filter(|e| matches!(e, Event::Pointer(..))).count();
    // (the left hand's laser may point at the log already)
    let before = told(&r);
    r.run.notify_pointer(&mut r.w, Some((100, 100)), None);
    r.run.notify_pointer(&mut r.w, Some((103, 102)), None);
    assert_eq!(told(&r) - before, 1);
    r.run.notify_pointer(&mut r.w, Some((104, 100)), None);
    assert_eq!(told(&r) - before, 2);
    r.run.notify_pointer(&mut r.w, None, None);
    assert_eq!(told(&r) - before, 3);
    // the other hand's moves count too
    r.run.notify_pointer(&mut r.w, Some((100, 100)), Some((300, 300)));
    r.run.notify_pointer(&mut r.w, Some((100, 100)), Some((310, 300)));
    assert_eq!(told(&r) - before, 5);
    assert!(matches!(r.events.lock().unwrap().last(), Some(Event::Pointer(Some((100, 100)), Some((310, 300))))));
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
    assert_eq!((w, h), crate::layout::clamp_panel_size(1e9, 1e9, 400));
}

/// The keyboard alone (no log), in front of the head; what it told meanwhile cleared
fn with_keyboard() -> (Rig, Vec3) {
    let mut r = vr_ui();
    r.hand(HEAD, pose::pose_facing([0.0, 1.6, 0.0], [0.0, 1.6, 1.0], None));
    r.w.vr_windows_wanted = (false, false, true);
    r.frame(0);
    r.events.lock().unwrap().clear();
    let at = pose::position(&r.world("keyboard"));
    (r, at)
}

#[test]
fn a_locked_keyboard_is_not_grabbed() {
    let mut r = vr_ui();
    let head = pose::pose_facing([0.0, 1.6, 0.0], [0.0, 1.6, 1.0], None);
    r.hand(HEAD, head);
    r.w.vr_windows_wanted = (true, false, true);
    r.frame(0);
    let at = pose::position(&r.world("keyboard"));
    r.hand(RIGHT, aiming([0.2, 1.2, 0.2], at));
    r.w.keyboard_locked = true;
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    r.w.keyboard_locked = false;
    r.buttons(RIGHT, 0);
    r.frame(20);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    assert_eq!(r.grabbed(), Some(r.index("keyboard")));
}

#[test]
fn launcher_intro_invalidates_static_capture_without_opening_keyboard() {
    use crate::panel::Frame;
    for capture in [Frame::Gpu(1), Frame::Printed(vec![255; 4])] {
        let mut r = vr_ui();
        assert!(!r.w.vr_windows_wanted.2);
        for state in [Intro::Pending, Intro::Playing, Intro::Idle] {
            r.run.panel.last_raw = Some(capture.clone());
            r.run.set_launcher_intro(&mut r.w, state);
            assert!(r.run.panel.last_raw.is_none(), "state change must recompose the same capture");
            // Once that capture has been composed, an unchanged state must keep the cache.
            r.run.panel.last_raw = Some(capture.clone());
            r.run.set_launcher_intro(&mut r.w, state);
            assert!(r.run.panel.last_raw.as_ref() == Some(&capture));
            assert!(!r.w.vr_windows_wanted.2);
        }
    }
}


#[test]
fn holds_use_the_current_ray_with_one_update_per_frame() {
    let (mut r, at) = with_keyboard();
    r.hand(RIGHT, aiming(HAND_AT, at));
    let before = r.steam.0.borrow().input_updates.len();
    r.frame(0);
    let steam = r.steam.0.borrow();
    assert_eq!(steam.input_updates.len(), before + 1);
    assert!(steam.input_updates.last().unwrap().contains(&RIGHT));
}

#[test]
fn dashboard_cancels_and_recovery_requires_neutral_for_grab() {
    let (mut r, at) = with_keyboard();
    r.hand(RIGHT, aiming(HAND_AT, at));
    r.run.panel.hwnd = Some(0);
    r.run.panel.image_size = Some((1600, 1000));
    r.run.panel_input.insert(RIGHT, (true, Some((10, 10))));
    r.run.mouse_owner = Some(RIGHT);
    r.steam.0.borrow_mut().dashboard = true;
    r.frame(0);
    assert_eq!(r.run.mouse_owner, None);
    assert!(r.run.mouse.events.contains(&("up", -30000, -30000)));
    assert!(r.steam.0.borrow().input_updates.last().unwrap().is_empty());
    r.buttons(RIGHT, GRIP);
    r.steam.0.borrow_mut().dashboard = false;
    r.frame(0);
    assert_eq!(r.grabbed(), None);
    r.buttons(RIGHT, 0);
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(0);
    assert!(r.grabbed().is_some());
}

#[test]
fn tracking_loss_and_update_failure_cancel_without_a_release_click() {
    for lose_tracking in [true, false] {
        let (mut r, at) = with_keyboard();
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.run.panel.hwnd = Some(0);
        r.run.panel.image_size = Some((1600, 1000));
        r.run.panel_input.insert(RIGHT, (true, Some((10, 10))));
        r.run.mouse_owner = Some(RIGHT);
        if lose_tracking { r.steam.0.borrow_mut().poses.remove(&RIGHT); }
        else { r.steam.0.borrow_mut().input_failure = true; }
        r.frame(0);
        assert_eq!(r.run.mouse_owner, None);
        assert_eq!(r.run.mouse.events.iter().filter(|e| e.0 == "up").copied().collect::<Vec<_>>(),
                   vec![("up", -30000, -30000)]);
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.buttons(RIGHT, GRIP | TRIGGER);
        r.steam.0.borrow_mut().input_failure = false;
        r.frame(0);
        assert_eq!(r.grabbed(), None);
        assert_eq!(r.run.mouse_owner, None);
    }
}

#[test]
fn keyboard_overlap_cancels_before_handoff_and_old_hand_waits_for_neutral() {
  for (first, second) in [(LEFT, RIGHT), (RIGHT, LEFT)] {
    let mut r = vr_ui();
    r.run.panel.hwnd = Some(0);
    r.run.panel.image_size = Some((1600, 1000));
    let pressed = ControllerState { button_pressed: TRIGGER, ..Default::default() };
    let rest = ControllerState::default();
    r.run.handle_panel_input(first, Some((10, 10)), Some(pressed), true);
    r.run.handle_panel_input(second, Some((30, 10)), Some(pressed), true);
    assert_eq!(r.run.mouse_owner, Some(second));
    let actions: Vec<_> = r.run.mouse.events.iter().filter(|e| e.0 != "move").copied().collect();
    assert_eq!(actions, vec![("down", 10, 10), ("up", -30000, -30000), ("down", 30, 10)]);
    let before = r.run.mouse.events.len();
    r.run.handle_panel_input(first, Some((90, 10)), Some(pressed), true);
    r.run.handle_panel_input(first, None, Some(pressed), true);
    r.run.handle_panel_input(first, Some((90, 10)), Some(rest), true);
    assert_eq!(r.run.mouse_owner, Some(second));
    assert_eq!(r.run.mouse.events.len(), before);
    r.run.handle_panel_input(first, Some((90, 10)), Some(pressed), true);
    assert_eq!(r.run.mouse_owner, Some(first));
    r.run.handle_panel_input(first, None, Some(pressed), true);
    assert_eq!(r.run.mouse_owner, None);
    assert!(!r.run.mouse_owner_keyboard);
    let downs = r.run.mouse.events.iter().filter(|e| e.0 == "down").count();
    r.run.handle_panel_input(first, Some((90, 10)), Some(pressed), true);
    assert_eq!(r.run.mouse.events.iter().filter(|e| e.0 == "down").count(), downs);
  }
}

#[test]
fn leaving_the_panel_cancels_and_reentry_held_does_not_press() {
    let mut r = vr_ui();
    r.run.panel.hwnd = Some(0);
    r.run.panel.image_size = Some((1600, 1000));
    let pressed = ControllerState { button_pressed: TRIGGER, ..Default::default() };
    r.run.handle_panel_input(RIGHT, Some((10, 10)), Some(pressed), true);
    r.run.handle_panel_input(RIGHT, None, Some(pressed), true);
    r.run.handle_panel_input(RIGHT, Some((30, 10)), Some(pressed), true);
    assert_eq!(r.run.mouse_owner, None);
    assert!(r.run.mouse.events.contains(&("up", -30000, -30000)));
    assert_eq!(r.run.mouse.events.iter().filter(|e| e.0 == "down").count(), 1);
}


#[test]
fn a_finger_resting_on_the_trigger_off_the_panel_still_presses_when_back() {
    let mut r = vr_ui();
    r.run.panel.hwnd = Some(0);
    r.run.panel.image_size = Some((1600, 1000));
    let mut resting = ControllerState::default();
    resting.axis[1][0] = 0.15;
    r.run.handle_panel_input(RIGHT, Some((10, 10)), Some(resting), true);
    r.run.handle_panel_input(RIGHT, None, Some(resting), true);
    r.run.handle_panel_input(RIGHT, Some((10, 10)), Some(resting), true);
    let click = ControllerState { button_pressed: TRIGGER, axis: [[0.0; 2], [1.0, 0.0], [0.0; 2], [0.0; 2], [0.0; 2]], ..Default::default() };
    r.run.handle_panel_input(RIGHT, Some((10, 10)), Some(click), true);
    assert_eq!(r.run.mouse.events.iter().filter(|e| e.0 == "down").count(), 1);
}

#[test]
fn after_the_dashboard_a_hand_walking_or_holding_something_types_again() {
    for held in [(0.5, 0), (0.0, GRIP)] {
        let (mut r, at) = with_keyboard();
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.run.panel.hwnd = Some(0);
        r.frame(0);
        r.steam.0.borrow_mut().dashboard = true;
        r.frame(0);
        r.steam.0.borrow_mut().dashboard = false;
        r.stick(RIGHT, held.0, 0.0);
        r.buttons(RIGHT, held.1);
        r.frame(0);
        assert!(!r.run.input_suspended.contains(&RIGHT), "{held:?}");
        // a grip held through it grabs nothing
        assert_eq!(r.grabbed(), None, "{held:?}");
        r.buttons(RIGHT, TRIGGER);
        r.frame(0);
        assert_eq!(r.run.mouse.events.iter().filter(|e| e.0 == "down").count(), 1, "{held:?}");
    }
}

#[test]
fn aim_snapshot_does_not_pull_a_large_move_back_to_the_old_key() {
    let mut r = vr_ui();
    r.run.panel.hwnd = Some(0);
    r.run.panel.image_size = Some((1600, 1000));
    let mut pulling = ControllerState::default();
    pulling.axis[1][0] = 0.2;
    r.run.handle_panel_input(RIGHT, Some((10, 10)), Some(pulling), true);
    pulling.button_pressed = TRIGGER;
    r.run.handle_panel_input(RIGHT, Some((50, 10)), Some(pulling), true);
    assert!(r.run.mouse.events.contains(&("down", 50, 10)));
}

#[test]
fn shutdown_cancels_a_held_key_and_releases_input_priority() {
    let mut r = vr_ui();
    r.run.panel.hwnd = Some(0);
    r.run.panel_input.insert(RIGHT, (true, Some((10, 10))));
    r.run.mouse_owner = Some(RIGHT);
    r.run.teardown(&mut r.w);
    assert_eq!(r.run.mouse_owner, None);
    assert!(r.run.mouse.events.contains(&("up", -30000, -30000)));
    assert!(r.steam.0.borrow().input_updates.last().unwrap().is_empty());
}


#[test]
fn restored_input_resolves_the_tip_without_caching_a_temporary_failure() {
    let (mut r, at) = with_keyboard();
    r.hand(RIGHT, aiming(HAND_AT, at));
    r.steam.0.borrow_mut().tip = Some(translation([0.0, 0.0, -0.02]));
    r.run.tip_offsets.clear();
    r.run.input_suspended.insert(RIGHT);
    r.frame(0);
    let (tip, retry) = r.run.tip_offsets.get(&RIGHT).unwrap();
    assert!(retry.is_none());
    assert!((tip[2][3] + 0.02).abs() < 1e-6);
}

#[test]
fn action_loss_while_grabbing_preserves_the_last_valid_position() {
    let (mut r, at) = with_keyboard();
    r.hand(RIGHT, aiming(HAND_AT, at));
    r.frame(0);
    r.buttons(RIGHT, GRIP);
    r.frame(20);
    r.frame(20);
    let shown = r.world("keyboard");
    r.steam.0.borrow_mut().unavailable.insert(RIGHT);
    r.hand(RIGHT, aiming(pose::add(HAND_AT, [0.4, 0.0, 0.0]), at));
    r.frame(20);
    assert_eq!(r.grabbed(), None);
    assert_eq!(r.positions().len(), 1);
    assert!(pose::norm(pose::sub(pose::position(&r.world("keyboard")), pose::position(&shown))) < 1e-6);
}

#[test]
fn role_changes_while_grabbing_save_once_and_wait_for_neutral() {
    for changed in [[RIGHT, LEFT], [LEFT, vrct_openvr::TRACKED_DEVICE_INDEX_INVALID]] {
        let (mut r, at) = with_keyboard();
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.frame(0);
        r.buttons(RIGHT, GRIP);
        r.frame(20);
        assert_eq!(r.grabbed(), Some(r.index("keyboard")));
        let moved_from = pose::add(HAND_AT, [0.3, 0.0, 0.0]);
        let moved_at = pose::add(at, [0.3, 0.0, 0.0]);
        r.hand(RIGHT, aiming(moved_from, moved_at));
        r.frame(20);
        let shown = r.world("keyboard");
        let last = r.run.grab_last_relative.unwrap();
        assert!(pose::position(&shown)[0] > 0.2);
        r.steam.0.borrow_mut().roles = Some(changed);
        // A new device pose in the same frame must not replace the last valid grab position.
        r.hand(RIGHT, aiming(pose::add(moved_from, [0.4, 0.0, 0.0]), moved_at));
        r.frame(0);
        assert_eq!(r.grabbed(), None);
        let saved = r.positions();
        assert_eq!(saved.len(), 1, "role change must persist the interrupted grab: {changed:?}");
        assert_eq!(saved[0].0, "keyboard");
        let expected = pose::matrix_to_position(&crate::math::Tracker::from_name("Playspace").base(), &last)
            .map(|v| pose::round_to(v, 4));
        assert_eq!(saved[0].1.position, expected);
        assert_eq!(r.w.sizes[r.index("keyboard")].settings.position, expected);
        assert!(pose::norm(pose::sub(pose::position(&r.world("keyboard")), pose::position(&shown))) < 1e-6);
        r.frame(0);
        assert_eq!(r.positions().len(), 1);
        // Restore the role with grip still held: no new grab until release, then a fresh press.
        r.steam.0.borrow_mut().roles = Some([LEFT, RIGHT]);
        r.hand(RIGHT, aiming(moved_from, pose::position(&shown)));
        r.frame(0);
        r.frame(0);
        assert_eq!(r.grabbed(), None);
        assert_eq!(r.positions().len(), 1);
        r.buttons(RIGHT, 0);
        r.frame(0);
        r.buttons(RIGHT, GRIP);
        r.frame(0);
        assert_eq!(r.grabbed(), Some(r.index("keyboard")));
    }
}

#[test]
fn role_change_during_scaling_saves_relative_pose_and_width_for_keyboard_and_wrist_launcher() {
    for size in ["keyboard", "launcher"] {
        let (mut r, _) = with_keyboard();
        r.w.launcher_auto_hide = false;
        r.frame(100);
        r.frame(100);
        let index = r.index(size);
        let at = pose::position(&r.world(size));
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.frame(0);
        r.events.lock().unwrap().clear();
        r.buttons(RIGHT, GRIP);
        r.frame(20);
        assert_eq!(r.grabbed(), Some(index), "{size}");
        // Move first, so saving the original settings would not pass this test.
        let moved_from = pose::add(HAND_AT, [0.03, 0.0, 0.0]);
        let moved_at = pose::add(at, [0.03, 0.0, 0.0]);
        let hand = aiming(moved_from, moved_at);
        r.hand(RIGHT, hand);
        r.frame(20);
        r.buttons(RIGHT, GRIP | TRIGGER);
        r.frame(20);
        let forward = pose::scale(pose::axis(&pose::mul(&hand, &pose::laser_tilt(12.0)), 2), -1.0);
        r.hand(RIGHT, aiming(pose::add(moved_from, pose::scale(forward, 0.15)), moved_at));
        r.frame(20);
        assert!(r.run.grab_scale.is_some());
        // (VRCT's launcher starts at 0.2 m in vr_ui(): doubled too)
        let width = if size == "keyboard" { 1.2 } else { 0.4 };
        assert!((r.w.sizes[index].settings.ui_scaling - width).abs() < 1e-6, "{size}");
        let tracker = r.w.sizes[index].settings.tracker.clone();
        let last = r.run.grab_last_relative.unwrap();
        let expected = pose::matrix_to_position(&crate::math::Tracker::from_name(&tracker).base(), &last)
            .map(|v| pose::round_to(v, 4));
        assert_ne!(expected, r.w.sizes[index].settings.position);
        assert!(r.positions().is_empty());

        r.steam.0.borrow_mut().roles = Some([RIGHT, LEFT]);
        r.hand(RIGHT, aiming(pose::add(moved_from, [0.4, 0.0, 0.0]), moved_at));
        r.frame(0);
        assert_eq!(r.grabbed(), None);
        assert!(r.run.grab_scale.is_none());
        let saved = r.positions();
        assert_eq!(saved.len(), 1, "{size}");
        assert_eq!(saved[0].0, size);
        assert_eq!(saved[0].1.tracker, tracker);
        assert_eq!(saved[0].1.position, expected);
        assert_eq!(r.w.sizes[index].settings.position, expected);
        assert!((saved[0].1.ui_scaling - width).abs() < 1e-6);
        r.frame(0);
        // A wrist launcher follows its newly assigned device; only its relative pose is retained.
        if size == "launcher" {
            let handle = r.run.handles[index];
            assert_eq!(r.steam.0.borrow().overlays[handle as usize - 1].place.unwrap().0, Some(RIGHT));
        }
        r.steam.0.borrow_mut().roles = Some([LEFT, RIGHT]);
        r.frame(0);
        r.frame(0); // apply the restored hand's pending transform
        let restored_at = pose::position(&r.world(size));
        r.hand(RIGHT, aiming(HAND_AT, restored_at));
        r.frame(0);
        assert_eq!(r.grabbed(), None);
        assert_eq!(r.positions().len(), 1);
        r.buttons(RIGHT, 0);
        r.frame(0);
        r.buttons(RIGHT, GRIP);
        r.frame(0);
        assert_eq!(r.grabbed(), Some(index), "{size}");
    }
}

#[test]
fn wrist_launcher_rebinds_after_its_role_is_missing_without_changing_settings() {
    let mut r = vr_ui();
    let li = r.index("launcher");
    let handle = r.run.handles[li];
    let position = r.w.sizes[li].settings.position;
    let width = r.w.sizes[li].settings.ui_scaling;
    r.events.lock().unwrap().clear();
    r.steam.0.borrow_mut().roles = Some([vrct_openvr::TRACKED_DEVICE_INDEX_INVALID, RIGHT]);
    r.frame(0);
    r.frame(0);
    assert!(r.run.pending[li]);
    r.hand(RIGHT, translation(WRIST));
    r.steam.0.borrow_mut().roles = Some([RIGHT, LEFT]);
    r.frame(0);
    r.frame(0);
    assert!(!r.run.pending[li]);
    assert_eq!(r.steam.0.borrow().overlays[handle as usize - 1].place.unwrap().0, Some(RIGHT));
    assert_eq!(r.w.sizes[li].settings.position, position);
    assert_eq!(r.w.sizes[li].settings.ui_scaling, width);
    assert!(r.positions().is_empty(), "rebinding alone must not save changed settings");
}

#[test]
fn command_wait_processes_stop_even_at_zero_and_does_not_drain_past_deadline() {
    for online in [false, true] {
        let mut rig = Rig::new(vec![]);
        rig._commands.send(Command::LaserPitch(3.0)).unwrap();
        rig._commands.send(Command::Stop).unwrap();
        assert!(rig.w.wait(Duration::ZERO, if online { Some(&mut rig.run) } else { None }));
        assert_eq!(rig.w.laser_pitch_up_deg, 3.0);
        assert!(!rig.w.stopped);
        assert!(!rig.w.wait(Duration::ZERO, if online { Some(&mut rig.run) } else { None }));
        assert!(rig.w.stopped);
    }
}

/// SteamVR's server ended without VREvent_Quit (killed, a crash): the frames end, as on a quit (the
/// worker then closes the connection)
#[test]
fn frames_end_when_the_steamvr_server_is_gone() {
    let mut r = Rig::new(vec![("small", settings("Playspace", [0.0; 6], 0.4))]);
    let mut server = std::process::Command::new("cmd").args(["/c", "ping -n 30 127.0.0.1 >nul"]).spawn().unwrap();
    r.run.server = vrct_openvr::ProcessWatch::open(server.id());
    assert!(r.run.server.is_some());
    server.kill().unwrap();
    server.wait().unwrap();
    // were the server not looked at, the frames would go on until this stop
    r._commands.send(Command::Stop).unwrap();
    r.run.frames(&mut r.w);
    assert!(!r.w.stopped);
}

#[test]
fn commands_arriving_repeatedly_do_not_extend_frame_wait() {
    let mut rig = Rig::new(vec![]);
    let (tx, rx) = command_wait::channel();
    rig.w.commands = rx;
    let producer = std::thread::spawn(move || {
        for _ in 0..100 {
            if tx.send(Command::LaserPitch(3.0)).is_err() { break; }
            std::thread::sleep(Duration::from_millis(10));
        }
    });
    let start = Instant::now();
    assert!(rig.w.wait(Duration::from_millis(100), Some(&mut rig.run)));
    // A broad watchdog, not a precision assertion: a reset timeout would run for >1 s.
    assert!(start.elapsed() < Duration::from_millis(800));
    drop(rig);
    producer.join().unwrap();
}

#[test]
fn scroll_history_clears_on_neutral_outside_tracking_loss_and_cancellation() {
    let mut r = Rig::new(vec![]);
    r.run.panel.hwnd = Some(0);
    r.run.panel.image_size = Some((100, 100));
    // First active sample starts timing separately for each hand, without wheel output.
    let mut active = ControllerState::default();
    active.axis[0][1] = 1.0;
    r.run.handle_panel_input(LEFT, Some((10, 10)), Some(active), true);
    r.run.handle_panel_input(RIGHT, Some((20, 10)), Some(active), true);
    assert_eq!(r.run.panel_scroll.len(), 2);
    r.run.handle_panel_input(LEFT, Some((10, 10)), Some(ControllerState::default()), true);
    assert!(!r.run.panel_scroll.contains_key(&LEFT));
    assert!(r.run.panel_scroll.contains_key(&RIGHT));
    r.run.handle_panel_input(RIGHT, None, Some(active), true);
    assert!(r.run.panel_scroll.is_empty());
    r.run.handle_panel_input(LEFT, Some((10, 10)), Some(active), true);
    r.run.handle_panel_input(LEFT, Some((10, 10)), None, true);
    assert!(r.run.panel_scroll.is_empty());
    r.run.handle_panel_input(RIGHT, Some((20, 10)), Some(active), true);
    r.run.release_all_presses();
    assert!(r.run.panel_scroll.is_empty());
    r.run.handle_panel_input(RIGHT, Some((20, 10)), Some(active), true);
    r.run.panel.hwnd = None;
    r.run.handle_panel_input(RIGHT, Some((20, 10)), Some(active), true);
    assert!(r.run.panel_scroll.is_empty());
}

#[test]
fn same_frame_release_precedes_other_hand_down_in_both_role_orders() {
    for (first, second) in [(LEFT, RIGHT), (RIGHT, LEFT)] {
        let (mut r, at) = with_keyboard();
        r.run.panel.hwnd = Some(0);
        r.hand(LEFT, aiming([-0.2, 1.2, -0.3], at));
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.frame(0);
        r.buttons(first, TRIGGER);
        r.frame(0);
        assert_eq!(r.run.mouse_owner, Some(first));
        r.run.mouse.events.clear();
        r.buttons(first, 0);
        r.buttons(second, TRIGGER);
        r.frame(0);
        assert_eq!(r.run.mouse_owner, Some(second));
        let actions: Vec<_> = r.run.mouse.events.iter().filter(|e| e.0 != "move").copied().collect();
        assert_eq!(actions.len(), 2, "{actions:?}");
        assert_eq!(actions[0].0, "up");
        assert_ne!((actions[0].1, actions[0].2), (-30000, -30000));
        assert_eq!(actions[1].0, "down");
    }
}

#[test]
fn launcher_origin_or_target_keeps_first_owner_protection() {
    for (first, second) in [(LEFT, RIGHT), (RIGHT, LEFT)] {
        for (first_keyboard, second_keyboard) in [(false, true), (true, false), (false, false)] {
            let mut r = vr_ui();
            r.run.panel.hwnd = Some(0);
            let pressed = ControllerState { button_pressed: TRIGGER, ..Default::default() };
            r.run.handle_panel_input(first, Some((10, 10)), Some(pressed), first_keyboard);
            // Moving from the launcher onto the keyboard cannot change the press's origin.
            r.run.handle_panel_input(first, Some((20, 10)), Some(pressed), true);
            r.run.handle_panel_input(second, Some((30, 10)), Some(pressed), second_keyboard);
            assert_eq!(r.run.mouse_owner, Some(first));
            assert_eq!(r.run.mouse_owner_keyboard, first_keyboard);
            assert!(r.run.trigger_blocked.contains(&second));
            assert!(!r.run.mouse.events.iter().any(|e| e.0 == "up"));
            r.run.release_all_presses();
            assert!(!r.run.mouse_owner_keyboard);
        }
    }
}

#[test]
fn handoff_owner_cancels_on_dashboard_or_tracking_loss_and_waits_for_neutral() {
    for dashboard in [false, true] {
        let (mut r, at) = with_keyboard();
        r.run.panel.hwnd = Some(0);
        r.hand(LEFT, aiming([-0.2, 1.2, -0.3], at));
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.frame(0);
        r.buttons(LEFT, TRIGGER);
        r.frame(0);
        r.buttons(RIGHT, TRIGGER);
        r.frame(0);
        assert_eq!(r.run.mouse_owner, Some(RIGHT));
        r.run.mouse.events.clear();
        if dashboard { r.steam.0.borrow_mut().dashboard = true; } else { r.lose(RIGHT); }
        r.frame(0);
        assert_eq!(r.run.mouse_owner, None);
        assert!(!r.run.mouse_owner_keyboard);
        assert!(r.run.mouse.events.contains(&("up", -30000, -30000)));
        r.steam.0.borrow_mut().dashboard = false;
        r.hand(RIGHT, aiming(HAND_AT, at));
        r.frame(0);
        assert_eq!(r.run.mouse_owner, None);
        assert!(!r.run.mouse.events.iter().any(|e| e.0 == "down"));
        r.buttons(RIGHT, 0);
        r.frame(0);
        r.buttons(RIGHT, TRIGGER);
        r.frame(0);
        assert_eq!(r.run.mouse_owner, Some(RIGHT));
    }
}

#[test]
fn launcher_taps_the_hand_when_touched_and_when_pressed() {
    let mut touching = std::collections::HashSet::new();
    let due = |touching: &mut std::collections::HashSet<u32>, on, was, now| crate::vr_ui::launcher_haptic_due(touching, LEFT, on, was, now);
    assert!(!due(&mut touching, false, false, false), "off the launcher");
    assert!(due(&mut touching, true, false, false), "the laser reaches it");
    assert!(!due(&mut touching, true, false, false), "staying on it");
    assert!(due(&mut touching, true, false, true), "pressed");
    assert!(!due(&mut touching, true, true, true), "held");
    assert!(!due(&mut touching, false, true, false), "left");
    assert!(due(&mut touching, true, false, false), "touching it again taps again");
}
