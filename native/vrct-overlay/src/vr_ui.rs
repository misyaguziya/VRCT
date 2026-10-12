//! Pointing, grabbing and resizing (overlay.py: updateGrab and what it calls), the launcher on the
//! wrist (shown when looked at, its intro, flying back), the log window's bar, anchor and recall,
//! and the temporary window's place.
//!
//! A controller's laser (from its tip, tilted up a little) points at the overlays: a dot shows
//! where; the trigger clicks and the stick scrolls the VR UI; pressing the grip grabs a window
//! (and with the trigger held, scales it by pushing / pulling the hand); the log window's corners
//! resize it. Grips also reach VRChat (an overlay cannot take input from it).
use crate::layout::{self, PointerKind, Region};
use crate::math::{Mat34, Mat4};
use crate::overlay::{Follow, Grab, GrabScale, Intro, Resize, Return, Run, Settings, Worker, COLOR_NORMAL};
use crate::pose::{self, Vec3, IDENTITY};
use std::time::{Duration, Instant};
use vrct_openvr::{ControllerState, IntersectionParams, TRACKED_DEVICE_INDEX_HMD, TRACKED_DEVICE_INDEX_INVALID};

const GRIP_MASK: u64 = 1 << vrct_openvr::BUTTON_GRIP;
const TRIGGER_MASK: u64 = 1 << vrct_openvr::BUTTON_STEAMVR_TRIGGER;
const HMD: Follow = Follow::Device(TRACKED_DEVICE_INDEX_HMD);
const POINTER_WIDTH_M: f64 = 0.0075;
// The pointer pops to this scale when a window is grabbed
const GRAB_POP_SCALE: f64 = 1.8;
const GRAB_POP_SEC: f64 = 0.12;
// Trigger held while grabbing: pushing the hand this far doubles the width (pulling halves it)
const SCALE_DOUBLING_M: f64 = 0.15;
const SCALE_ICON_THRESHOLD_M: f64 = 0.01;
const WIDTH_MIN_M: f64 = 0.05;
const WIDTH_MAX_M: f64 = 3.0;
// A hit on a clear part of a log image does not count unless something is drawn this near (px)
const HIT_MARGIN_PX: i64 = 12;
// The hand's shake smoothed while moving slowly
const GRAB_SMOOTH_TAU_SEC: f64 = 0.06;
const GRAB_SMOOTH_MAX_SPEED_M: f64 = 0.3;
// The launcher shows when its face turns to the head and the gaze is near, and hides with wider
// angles and a longer wait (no flicker at the edge, no showing on gestures)
const LAUNCHER_FACE_DEG: f64 = 45.0;
const LAUNCHER_GAZE_SHOW_DEG: f64 = 40.0;
const LAUNCHER_GAZE_HIDE_DEG: f64 = 45.0;
const LAUNCHER_HIDE_MARGIN_DEG: f64 = 10.0;
const LAUNCHER_SHOW_AFTER_SEC: f64 = 0.05;
const LAUNCHER_HIDE_AFTER_SEC: f64 = 0.3;
const LAUNCHER_FADE_SEC: f64 = 0.1;
// Not pressable when just shown (the wrist turned with a press)
const LAUNCHER_INPUT_DELAY_SEC: f64 = 0.2;
// The intro: in front of the eyes, then flying to the wrist (times as in VrLauncher.module.scss)
const INTRO_FRONT_SEC: f64 = 1.3;
const INTRO_FLY_SEC: f64 = 0.8;
const INTRO_FRONT_SCALE: f64 = 5.0;
const INTRO_FRONT_FOLLOW_PER_SEC: f64 = 8.0;
const LAUNCHER_INTRO_SEC: f64 = 4.8;
const LAUNCHER_RETURN_SEC: f64 = 0.3;
const FIRST_FRAME_WARN_SEC: f64 = 10.0;
// The temporary window: above the launcher, within this horizontal distance of the head
const POPUP_ABOVE_LAUNCHER_M: f64 = 0.18;
const POPUP_DISTANCE_RANGE_M: (f64, f64) = (0.45, 0.65);
// A recall asked for with the log closed waits this long for it to open
const RECALL_PENDING_SEC: f64 = 1.0;
// The bar under the log: fixed size (0.4 m per 900 px), this gap, shown after pointing at the
// log a while, hidden a while after, faded in / out
const TOOLBAR_M_PER_PX: f64 = 0.4 / 900.0;
const TOOLBAR_GAP_M: f64 = 0.012;
const TOOLBAR_SHOW_AFTER_SEC: f64 = 0.3;
const TOOLBAR_HIDE_AFTER_SEC: f64 = 2.0;
const TOOLBAR_FADE_SEC: f64 = 0.25;
// Moving the log onto a hand / the head brings it within these distances
const HAND_ANCHOR_MAX_DISTANCE_M: f64 = 0.5;
const HMD_ANCHOR_DISTANCE_RANGE_M: (f64, f64) = (0.4, 1.5);
// The stick as the wheel (per frame; WHEEL_DELTA = 120)
const PANEL_SCROLL_PER_FRAME: f64 = 60.0;
const PANEL_SCROLL_DEADZONE: f64 = 0.3;
// Off the VR view: a click there does not happen and the hover goes
const OUTSIDE_XY: (i32, i32) = (-1, -1);
const POINTER_NOTIFY_MIN_MOVE_PX: i32 = 4;
// The log's corner handles (logical px): inside and outside of each corner; their centre
const CORNER_INSIDE_PX: f64 = 56.0;
const CORNER_OUTSIDE_PX: f64 = 32.0;
const CORNER_HANDLE_CENTER_PX: i32 = 34;
// The resize frame in front of the log (on the same plane they flicker)
const GHOST_FRONT_M: f64 = 0.004;
// Look for a controller's tip again after this when it was not found
const TIP_RETRY_SEC: f64 = 5.0;
const LASER_PITCH_UP_DEG: f64 = 12.0;

pub(crate) const COLOR_POINTER: [f32; 3] = [0x61 as f32 / 255.0, 0xB4 as f32 / 255.0, 0xA7 as f32 / 255.0];
const COLOR_GRABBING: [f32; 3] = [0xB7 as f32 / 255.0, 0xDE as f32 / 255.0, 0xD8 as f32 / 255.0];

/// Where a laser meets an overlay (computeOverlayIntersection's results, or made up for a corner)
#[derive(Clone, Copy, Debug)]
pub(crate) struct Hit {
    pub point: Vec3,
    pub normal: Vec3,
    pub uv: (f64, f64),
    pub distance: f64,
}

/// What a laser points at: a size's overlay or the log's bar
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Target {
    Size(usize),
    Toolbar,
}

fn since(now: Instant, then: Instant) -> f64 {
    now.saturating_duration_since(then).as_secs_f64()
}

fn translation(x: f64, y: f64, z: f64) -> Mat4 {
    let mut m = IDENTITY;
    pose::set_position(&mut m, [x, y, z]);
    m
}

impl Run<'_> {
    /// The tracked pose (standing), None when not valid; the room for Playspace
    pub fn pose_of(&self, follow: Follow) -> Option<Mat4> {
        match follow {
            Follow::Playspace => Some(IDENTITY),
            Follow::Device(TRACKED_DEVICE_INDEX_INVALID) => None,
            Follow::Device(index) => {
                let p = self.poses.get(index as usize).filter(|p| p.pose_is_valid)?;
                Some(pose::homogeneous(&p.device_to_absolute_tracking.map(|r| r.map(f64::from))))
            }
        }
    }

    fn controller_state(&self, hand: u32) -> Option<ControllerState> {
        self.vr.system.controller_state(hand)
    }

    /// tipOffset: the controller's tip (render model component "tip") seen from its pose. Quest
    /// controllers' tips point 37 degrees below their pose's -Z. Unknown (just turned on): the
    /// pose itself, looked up again later.
    fn tip_offset(&mut self, w: &Worker, hand: u32, now: Instant) -> Mat4 {
        if let Some((offset, retry)) = self.tip_offsets.get(&hand)
            && retry.is_none_or(|at| now < at)
        {
            return *offset;
        }
        let mut found = None;
        let name = self.vr.system.string_tracked_device_property(hand, vrct_openvr::PROP_RENDER_MODEL_NAME_STRING);
        if let Some(state) = self.controller_state(hand)
            && !name.is_empty()
            && let Some(c) = self.vr.render_models.component_state(&name, "tip", &state, &Default::default())
        {
            found = Some(pose::homogeneous(&c.tracking_to_component_local.map(|r| r.map(f64::from))));
        }
        if found.is_none() && !self.tip_offsets.contains_key(&hand) {
            (w.log)(format!("overlay: コントローラの先端の向きが分からないので、本体の向きで指します (device {hand})"));
        }
        let entry = match found {
            Some(offset) => (offset, None),
            None => (IDENTITY, Some(now + Duration::from_secs_f64(TIP_RETRY_SEC))),
        };
        self.tip_offsets.insert(hand, entry);
        entry.0
    }

    /// The laser's pose (the tip, tilted up); a grabbed window moves with it
    fn ray_of(&mut self, w: &Worker, hand: u32, now: Instant) -> Option<Mat4> {
        let p = self.pose_of(Follow::Device(hand))?;
        let tip = self.tip_offset(w, hand, now);
        Some(pose::mul(&pose::mul(&p, &tip), &pose::laser_tilt(LASER_PITCH_UP_DEG)))
    }

    /// The size's pose in the room (None while its tracker is not tracked)
    pub fn overlay_world_pose(&self, w: &Worker, index: usize) -> Option<Mat4> {
        let (_, follow) = self.tracker(&w.sizes[index].settings.tracker);
        let tracker_pose = self.pose_of(follow)?;
        Some(pose::mul(&tracker_pose, &pose::homogeneous(&self.relative(w, index))))
    }

    fn region_world_pose(&self, w: &Worker, target: Target) -> Option<Mat4> {
        match target {
            Target::Size(i) => self.overlay_world_pose(w, i),
            Target::Toolbar => {
                let tracker_pose = self.pose_of(self.toolbar_follow?)?;
                Some(pose::mul(&tracker_pose, &pose::homogeneous(&self.toolbar_relative?)))
            }
        }
    }

    fn target_region(&self, w: &Worker, target: Target) -> Option<Region> {
        match target {
            Target::Size(i) => w.sizes[i].region,
            Target::Toolbar => Some(Region::Toolbar),
        }
    }

    /// regionWidthM: the bar's width is fixed, the windows' are their settings'
    pub fn region_width_m(&self, w: &Worker, region: Region) -> f64 {
        match region {
            Region::Toolbar => w.layout.region(Region::Toolbar)[2] as f64 * TOOLBAR_M_PER_PX,
            _ => w.region_index(region).map_or(0.0, |i| w.sizes[i].settings.ui_scaling),
        }
    }

    fn intersect(&self, ray: &Mat4, handle: u64) -> Option<Hit> {
        let p = pose::position(ray);
        let d = pose::axis(ray, 2);
        let params = IntersectionParams {
            source: p.map(|v| v as f32),
            direction: d.map(|v| -v as f32),
            origin: vrct_openvr::TRACKING_UNIVERSE_STANDING,
        };
        let r = self.vr.overlay.compute_overlay_intersection(handle, &params)?;
        Some(Hit {
            point: r.point.map(f64::from),
            normal: r.normal.map(f64::from),
            uv: (r.uvs[0] as f64, r.uvs[1] as f64),
            distance: r.distance as f64,
        })
    }

    /// hasContentAt: something drawn near the hit (VR UI regions are opaque but their corners)
    fn has_content_at(&self, w: &Worker, index: usize, hit: &Hit) -> bool {
        let size = &w.sizes[index];
        let Some(image) = size.image.as_ref().filter(|_| size.region.is_none()) else { return true };
        let (x, y) = pose::uv_to_pixel(hit.uv.0, hit.uv.1, image.width, image.height);
        let (x, y) = (x as i64, y as i64);
        (y - HIT_MARGIN_PX..=y + HIT_MARGIN_PX).any(|py| (x - HIT_MARGIN_PX..=x + HIT_MARGIN_PX).any(|px| {
            (0..image.width as i64).contains(&px) && (0..image.height as i64).contains(&py)
                && image.data[(py as usize * image.width + px as usize) * 4 + 3] > 0
        }))
    }

    /// hitInsideRegion: SteamVR's hits on a cut-out overlay can fall outside what shows of it (the
    /// bar under the log hit the log too, in VR)
    fn hit_inside_region(&self, w: &Worker, target: Target, hit: &Hit) -> bool {
        let Some(region) = self.target_region(w, target).filter(|r| *r != Region::Tooltip) else { return true };
        let Some(pose) = self.region_world_pose(w, target) else { return true };
        let local = pose::transform_point(&pose::inverse(&pose), hit.point);
        let [_, _, rw, rh] = w.layout.region(region);
        let width_m = self.region_width_m(w, region);
        let height_m = width_m * rh as f64 / rw as f64;
        local[0].abs() <= width_m / 2.0 + 0.001 && local[1].abs() <= height_m / 2.0 + 0.001
    }

    /// pointingOverlay: the nearest overlay the laser hits (faded ones too, so a grip wakes them),
    /// not on clear parts nor outside a region
    fn pointing_overlay(&self, w: &Worker, ray: &Mat4) -> Option<(usize, Hit)> {
        let mut best: Option<(usize, Hit)> = None;
        for (i, size) in w.sizes.iter().enumerate() {
            if size.settings.opacity <= 0.0 || size.region.is_some_and(|r| self.hidden.contains(&r)) {
                continue;
            }
            if size.region == Some(Region::Launcher) && !self.launcher_interactive {
                continue;
            }
            let Some(hit) = self.intersect(ray, self.handles[i]) else { continue };
            if !self.has_content_at(w, i, &hit) || !self.hit_inside_region(w, Target::Size(i), &hit) {
                continue;
            }
            if best.is_none_or(|(_, b)| hit.distance < b.distance) {
                best = Some((i, hit));
            }
        }
        best
    }

    /// regionPixel: the hit as a pixel of the capture (from the overlay's pose and width: SteamVR's
    /// UV of a cut-out overlay is measured differently)
    fn region_pixel(&self, w: &Worker, region: Region, hit: &Hit, overlay_pose: &Mat4) -> Option<(i32, i32)> {
        let image = self.panel.image_size?;
        let local = pose::transform_point(&pose::inverse(overlay_pose), hit.point);
        let [_, _, rw, rh] = w.layout.region(region);
        let width_m = self.region_width_m(w, region);
        let height_m = width_m * rh as f64 / rw as f64;
        let fx = (local[0] / width_m + 0.5).clamp(0.0, 1.0);
        let fy = (0.5 - local[1] / height_m).clamp(0.0, 1.0);
        let [x0, y0, x1, y1] = w.layout.region_rect(region, image.0).map(|v| v as i32);
        Some(((x0 + (fx * (x1 - x0) as f64) as i32).min(x1 - 1), (y0 + (fy * (y1 - y0) as f64) as i32).min(y1 - 1)))
    }

    /// showPointer: at the hit (None hides it); + / - while scaling
    pub fn show_pointer(&self, hit: Option<&Hit>, color: [f32; 3], scale: f64, kind: PointerKind) {
        for &(other, handle, _) in &self.pointers {
            if other != kind || hit.is_none() {
                let _ = self.vr.overlay.hide_overlay(handle);
            }
        }
        let (Some(hit), Some(&(_, handle, _))) = (hit, self.pointers.iter().find(|p| p.0 == kind)) else { return };
        let m = crate::math::to_hmd(&pose::pointer_transform(hit.point, hit.normal));
        let width = POINTER_WIDTH_M * if kind == PointerKind::Dot { 1.0 } else { 2.0 } * scale;
        let _ = self.vr.overlay.set_overlay_transform_absolute(handle, vrct_openvr::TRACKING_UNIVERSE_STANDING, &m);
        let _ = self.vr.overlay.set_overlay_color(handle, color[0], color[1], color[2]);
        let _ = self.vr.overlay.set_overlay_width_in_meters(handle, width as f32);
        let _ = self.vr.overlay.show_overlay(handle);
    }

    pub fn hide_pointer(&self) {
        self.show_pointer(None, COLOR_NORMAL, 1.0, PointerKind::Dot);
    }

    /// setHighlight: the grabbed window tinted (None: all back to white)
    pub fn set_highlight(&self, w: &Worker, index: Option<usize>, color: [f32; 3]) {
        for i in 0..w.sizes.len() {
            let c = if Some(i) == index { color } else { COLOR_NORMAL };
            let _ = self.vr.overlay.set_overlay_color(self.handles[i], c[0], c[1], c[2]);
        }
    }

    /// Ends a grab, its tint and pointer
    fn drop_grab(&mut self, w: &Worker) {
        self.grabbing = None;
        self.grab_scale = None;
        self.set_highlight(w, None, COLOR_NORMAL);
        self.hide_pointer();
    }

    /// updateGrab: once a frame
    pub fn update_grab(&mut self, w: &mut Worker) -> anyhow::Result<()> {
        self.poses = self.vr.system.device_to_absolute_tracking_pose(vrct_openvr::TRACKING_UNIVERSE_STANDING, 0.0);
        let now = Instant::now();
        self.apply_vr_windows(w);
        self.update_launcher_visibility(w, now);
        self.update_launcher_intro_flight(w, now);
        self.update_launcher_return(w, now);
        self.update_toolbar_fade(now);
        if self.resizing.is_some() {
            self.update_resize(w, now);
            return Ok(());
        }
        if self.grabbing.is_some() {
            self.update_grabbed(w, now);
            return Ok(());
        }
        self.update_pointing(w, now);
        Ok(())
    }

    /// While a window is grabbed: it follows the laser (on the sphere round the eyes for windows
    /// fixed in the room or to the head), the stick moves it nearer / further, releasing saves it
    fn update_grabbed(&mut self, w: &mut Worker, now: Instant) {
        let Some(Grab { index, hand, mut hand_to_overlay }) = self.grabbing.as_ref().map(|g| Grab { ..*g }) else { return };
        let hand_pose = self.ray_of(w, hand, now);
        let (_, follow) = self.tracker(&w.sizes[index].settings.tracker);
        let tracker_pose = self.pose_of(follow);
        let (Some(hand_pose), Some(tracker_pose)) = (hand_pose, tracker_pose) else {
            // lost tracking (sleep, power off): a release cannot be seen either; keep where it showed
            self.drop_grab(w);
            if let Some(relative) = self.grab_last_relative {
                self.commit_position(w, index, &relative);
            }
            return;
        };
        self.notify_pointer(w, None);
        let state = self.controller_state(hand);
        let grip = state.is_some_and(|s| s.button_pressed & GRIP_MASK != 0);
        let trigger = state.is_some_and(|s| s.button_pressed & TRIGGER_MASK != 0);
        self.grip_prev.insert(hand, grip);
        if grip && trigger {
            self.update_grab_scale(w, index, &hand_pose, &tracker_pose, follow);
            self.grab_prev_time = now;
            self.grab_smoothed = None;
            self.grab_prev_target = None;
            return;
        }
        let head = self.pose_of(HMD);
        if let Some(scale) = self.grab_scale.take() {
            // scaling over: grab again where it was held, from the hand as it is now
            hand_to_overlay = pose::mul(&pose::inverse(&hand_pose), &scale.overlay_pose);
            self.grabbing = Some(Grab { index, hand, hand_to_overlay });
            if self.grab_radius.is_some()
                && let Some(head) = head
            {
                self.grab_radius = Some(pose::norm(pose::sub(pose::position(&scale.overlay_pose), pose::position(&head))));
                self.grab_hand_distance = pose::norm(pose::sub(pose::position(&hand_pose), pose::position(&head)));
            }
            self.hide_pointer();
        }
        // capped so a frame held up by a capture does not jump
        let dt = since(now, self.grab_prev_time).min(0.1);
        self.grab_prev_time = now;
        let on_sphere = self.grab_radius.is_some() && head.is_some();
        // the head lost for a moment: kept where it was (facing the hand would jump)
        let lost_head = self.grab_radius.is_some() && head.is_none() && self.grab_last_relative.is_some();
        let stick = state.map(|s| (s.axis[0][0] as f64, s.axis[0][1] as f64));
        if grip && on_sphere {
            self.grab_radius = self.grab_radius.map(|r| pose::push_pull_distance(r, stick, dt));
        } else if grip && !lost_head {
            hand_to_overlay = pose::push_pull(&hand_to_overlay, stick, dt);
            self.grabbing = Some(Grab { index, hand, hand_to_overlay });
        }
        let relative = match self.grab_last_relative.filter(|_| lost_head) {
            Some(last) => last,
            None => {
                let mut world = pose::mul(&hand_pose, &hand_to_overlay);
                if on_sphere && let (Some(head), Some(radius)) = (head, self.grab_radius) {
                    let hand_distance = pose::norm(pose::sub(pose::position(&hand_pose), pose::position(&head)));
                    let r = pose::sphere_radius(radius, self.grab_hand_distance, hand_distance);
                    world = pose::pose_on_sphere(pose::position(&world), &head, r);
                }
                let tracker_inverse = pose::inverse(&tracker_pose);
                let mut relative = self.smooth_grab(&pose::top(&pose::mul(&tracker_inverse, &world)), dt);
                if on_sphere && let Some(head) = head {
                    // smoothed a little behind, still facing the head
                    let smoothed = pose::position(&pose::mul(&tracker_pose, &pose::homogeneous(&relative)));
                    relative = pose::top(&pose::mul(&tracker_inverse, &pose::face_head(smoothed, &head)));
                }
                relative
            }
        };
        self.grab_last_relative = Some(relative);
        if grip {
            self.set_transform(w, index, follow, &relative);
            self.wake(w, index);
            let pop = (since(now, self.grab_started) / GRAB_POP_SEC).min(1.0);
            let hit = self.intersect(&hand_pose, self.handles[index]);
            self.show_pointer(hit.as_ref(), COLOR_POINTER, 1.0 + (GRAB_POP_SCALE - 1.0) * pop, PointerKind::Dot);
        } else {
            self.drop_grab(w);
            if trigger {
                self.trigger_blocked.insert(hand);
            }
            // released where it was smoothed to (no jump on release)
            self.set_transform(w, index, follow, &relative);
            self.commit_position(w, index, &relative);
        }
    }

    /// Pointing with both hands: the pointer, input to the VR UI, the corner to resize and a grip to grab
    fn update_pointing(&mut self, w: &mut Worker, now: Instant) {
        let mut pointer: Option<Hit> = None;
        let mut hover_xy: Option<(i32, i32)> = None;
        let mut pointing_log = false;
        let mut pointing_launcher = false;
        let panel = w.region_index(Region::Panel);
        for role in [vrct_openvr::CONTROLLER_ROLE_LEFT_HAND, vrct_openvr::CONTROLLER_ROLE_RIGHT_HAND] {
            let hand = self.vr.system.tracked_device_index_for_controller_role(role);
            let hand_pose = self.ray_of(w, hand, now);
            let grip = hand_pose.is_some() && self.controller_state(hand).is_some_and(|s| s.button_pressed & GRIP_MASK != 0);
            let mut target: Option<(Target, Hit)> = None;
            if let Some(ray) = &hand_pose {
                target = self.pointing_overlay(w, ray).map(|(i, hit)| (Target::Size(i), hit));
                let toolbar = match (self.toolbar, self.toolbar_visible) {
                    (Some(handle), true) => self.intersect(ray, handle).filter(|hit| self.hit_inside_region(w, Target::Toolbar, hit)),
                    _ => None,
                };
                if let Some(hit) = toolbar
                    && target.as_ref().is_none_or(|(_, t)| hit.distance < t.distance)
                {
                    target = Some((Target::Toolbar, hit));
                }
            }
            // a window on this hand moves with it only; the bar goes with the log
            if let Some((t, _)) = &target {
                let owner = match t {
                    Target::Toolbar => panel,
                    Target::Size(i) => Some(*i),
                };
                if let Some(owner) = owner
                    && self.tracker(&w.sizes[owner].settings.tracker).1 == Follow::Device(hand)
                {
                    target = None;
                }
            }
            let is_panel = |t: &Option<(Target, Hit)>| matches!(t, Some((Target::Size(i), _)) if Some(*i) == panel);
            pointing_log |= is_panel(&target) || matches!(target, Some((Target::Toolbar, _)));
            let mut corner = hand_pose.as_ref().and_then(|ray| self.panel_corner_at(w, hand, ray));
            // pointing at another window (the bar): it wins over the corner reaching outside the log
            if corner.is_some() && target.is_some() && !is_panel(&target) {
                corner = None;
            }
            let corner_before = self.corner_prev.get(&hand).copied().flatten();
            self.corner_prev.insert(hand, corner.map(|c| c.0));
            if corner.is_some() {
                pointing_log = true;
            }
            // the corner pointed at last frame wins (the laser shakes as the grip is squeezed)
            let grip_corner = corner_before.or(corner.map(|c| c.0));
            if grip && !self.grip_prev.get(&hand).copied().unwrap_or(false)
                && let Some(c) = grip_corner
            {
                self.grip_prev.insert(hand, true);
                self.start_resize(w, hand, c);
                return;
            }
            let target_index = match &target {
                Some((Target::Size(i), _)) => Some(*i),
                _ => None,
            };
            pointing_launcher |= target_index.is_some_and(|i| w.sizes[i].region == Some(Region::Launcher));
            let name = target.as_ref().map(|(t, _)| match t {
                Target::Toolbar => "toolbar".to_string(),
                Target::Size(i) => w.sizes[*i].name.clone(),
            });
            if self.debug_state.get(&hand) != Some(&(grip, name.clone())) {
                self.debug_state.insert(hand, (grip, name.clone()));
                (w.log)(format!("overlay grab: hand {hand} grip {grip} hit {name:?}"));
            }

            if hand_pose.is_some() && !grip {
                let mut xy = None;
                // while the size changes, what shows (the old layout) and the VR view (the new one)
                // differ: no input (a press could land on another button)
                if let Some((t, hit)) = &target
                    && let Some(region) = self.target_region(w, *t)
                    && self.panel.image_size.is_some()
                    && self.panel.layout_applied_is(w)
                    && let Some(overlay_pose) = self.region_world_pose(w, *t)
                {
                    xy = self.region_pixel(w, region, hit, &overlay_pose);
                }
                // no click or scroll on a corner handle, only its hover
                let state = self.controller_state(hand);
                self.handle_panel_input(hand, if corner.is_some() { None } else { xy }, state);
                let handle_xy = corner.and_then(|c| self.corner_handle_xy(w, c.0));
                if hover_xy.is_none() && handle_xy.is_some() {
                    hover_xy = handle_xy;
                } else if hover_xy.is_none()
                    && let (Some((x, y)), Some(image)) = (xy, self.panel.image_size)
                {
                    let scale = image.0 as f64 / w.layout.atlas.0 as f64;
                    hover_xy = Some(((x as f64 / scale).round_ties_even() as i32, (y as f64 / scale).round_ties_even() as i32));
                }
            }

            // on a corner (outside the log too): the pointer; a grip resizes (above)
            if let Some((_, hit)) = corner
                && !matches!(target, Some((Target::Toolbar, _)))
            {
                self.grip_prev.insert(hand, grip);
                pointer.get_or_insert(hit);
                continue;
            }
            // the bar cannot be grabbed: its buttons are clicks on the VR view
            if let Some((Target::Toolbar, hit)) = target {
                self.grip_prev.insert(hand, grip);
                pointer.get_or_insert(hit);
                continue;
            }
            let grip_pressed_now = grip && !self.grip_prev.get(&hand).copied().unwrap_or(false);
            self.grip_prev.insert(hand, grip);
            let (Some(index), Some((_, hit))) = (target_index, target) else { continue };
            if !grip_pressed_now {
                if !grip && self.is_visible(w, index) && pointer.is_none() {
                    pointer = Some(hit);
                }
                continue;
            }
            if Some(index) == panel && w.panel_locked {
                continue;
            }
            let (Some(overlay_pose), Some(ray)) = (self.overlay_world_pose(w, index), hand_pose) else { continue };
            // a grip wakes a faded one
            self.wake(w, index);
            self.grabbing = Some(Grab { index, hand, hand_to_overlay: pose::mul(&pose::inverse(&ray), &overlay_pose) });
            let head = self.pose_of(HMD);
            let tracker = w.sizes[index].settings.tracker.as_str();
            let on_sphere = (tracker == "Playspace" || tracker == "HMD") && head.is_some();
            self.grab_radius = None;
            if on_sphere && let Some(head) = head {
                self.grab_radius = Some(pose::norm(pose::sub(pose::position(&overlay_pose), pose::position(&head))));
                self.grab_hand_distance = pose::norm(pose::sub(pose::position(&ray), pose::position(&head)));
            }
            self.grab_last_relative = None;
            self.grab_started = now;
            self.grab_prev_time = now;
            self.grab_smoothed = None;
            self.grab_prev_target = None;
            self.show_pointer(Some(&hit), COLOR_POINTER, 1.0, PointerKind::Dot);
            self.set_highlight(w, Some(index), COLOR_GRABBING);
            return;
        }
        self.show_pointer(pointer.as_ref(), COLOR_POINTER, 1.0, PointerKind::Dot);
        self.notify_pointer(w, hover_xy);
        self.update_toolbar_visibility(w, now, pointing_log);
        self.launcher_pointed = pointing_launcher;
    }

    /// handlePanelInput: the trigger clicks, the stick scrolls, where the laser hits the VR view
    /// (xy in the capture's px; None: off it)
    fn handle_panel_input(&mut self, hand: u32, xy: Option<(i32, i32)>, state: Option<ControllerState>) {
        let (last_pressed, last_xy) = self.panel_input.get(&hand).copied().unwrap_or((false, None));
        let (Some(hwnd), Some(_), Some(state)) = (self.panel.hwnd, self.panel.image_size, state) else { return };
        let mut pressed = state.button_pressed & TRIGGER_MASK != 0;
        if self.trigger_blocked.contains(&hand) {
            if pressed {
                pressed = false;
            } else {
                self.trigger_blocked.remove(&hand);
            }
        }
        let Some((x, y)) = xy else {
            // off the VR view: released outside, so a press begun on a button does not click (no
            // mic turned on by mistake), and the hover goes
            if last_xy.is_some() {
                self.mouse.moved(hwnd, OUTSIDE_XY.0, OUTSIDE_XY.1, last_pressed);
                if last_pressed {
                    self.mouse.up(hwnd, OUTSIDE_XY.0, OUTSIDE_XY.1);
                    // coming back still pressed is not a new press (no repeated long presses)
                    self.trigger_blocked.insert(hand);
                }
            }
            self.panel_input.remove(&hand);
            return;
        };
        if xy != last_xy {
            self.mouse.moved(hwnd, x, y, pressed);
        }
        if pressed && !last_pressed {
            self.mouse.down(hwnd, x, y);
        } else if last_pressed && !pressed {
            self.mouse.up(hwnd, x, y);
        }
        let stick_y = state.axis[0][1] as f64;
        if stick_y.abs() > PANEL_SCROLL_DEADZONE {
            self.mouse.wheel(hwnd, x, y, (PANEL_SCROLL_PER_FRAME * stick_y) as i32);
        }
        self.panel_input.insert(hand, (pressed, xy));
    }

    /// notifyPointer: only when it moved (4 px or more)
    pub fn notify_pointer(&mut self, w: &mut Worker, xy: Option<(i32, i32)>) {
        let last = w.pointer_notified;
        if xy == last {
            return;
        }
        if let (Some(a), Some(b)) = (xy, last)
            && (a.0 - b.0).abs() < POINTER_NOTIFY_MIN_MOVE_PX && (a.1 - b.1).abs() < POINTER_NOTIFY_MIN_MOVE_PX
        {
            return;
        }
        w.pointer_notified = xy;
        // the tooltip is matched against the position told (the current one flickers at the edge)
        if self.tooltip_state.is_some() && !self.tooltip_target_matches(w, xy) {
            self.reset_tooltip_epoch(w, true);
        }
        w.emit(crate::overlay::Event::Pointer(xy));
    }

    // ------------------------------------------------------------------ scaling and resizing

    /// updateGrabScale: trigger held while grabbing: the window stays; pushing the hand widens it
    fn update_grab_scale(&mut self, w: &mut Worker, index: usize, hand_pose: &Mat4, tracker_pose: &Mat4, follow: Follow) {
        if self.grab_scale.is_none() {
            let Some(relative) = self.grab_last_relative else { return };
            self.grab_scale = Some(GrabScale {
                start: pose::position(hand_pose),
                forward: pose::scale(pose::axis(hand_pose, 2), -1.0),
                width: w.sizes[index].settings.ui_scaling,
                overlay_pose: pose::mul(tracker_pose, &pose::homogeneous(&relative)),
            });
        }
        let s = self.grab_scale.as_ref().unwrap();
        let pushed = pose::dot(pose::sub(pose::position(hand_pose), s.start), s.forward);
        let width = (s.width * 2f64.powf(pushed / SCALE_DOUBLING_M)).clamp(WIDTH_MIN_M, WIDTH_MAX_M);
        let relative = pose::top(&pose::mul(&pose::inverse(tracker_pose), &s.overlay_pose));
        self.update_ui_scaling(w, index, width);
        self.grab_last_relative = Some(relative);
        self.set_transform(w, index, follow, &relative);
        self.wake(w, index);
        let kind = if pushed > SCALE_ICON_THRESHOLD_M {
            PointerKind::Plus
        } else if pushed < -SCALE_ICON_THRESHOLD_M {
            PointerKind::Minus
        } else {
            PointerKind::Dot
        };
        let hit = self.intersect(hand_pose, self.handles[index]);
        self.show_pointer(hit.as_ref(), COLOR_POINTER, 1.0, kind);
    }

    /// panelCornerAt: the log's corner handle the laser points at ((x, y) +1 right / up, and the
    /// hit); none while locked, hidden or changing size, nor for the hand it is on
    fn panel_corner_at(&self, w: &Worker, hand: u32, ray: &Mat4) -> Option<((i8, i8), Hit)> {
        let pi = w.region_index(Region::Panel)?;
        if self.hidden.contains(&Region::Panel) || !w.vr_panel_enabled || w.panel_locked || !self.panel.layout_applied_is(w)
            || !self.is_visible(w, pi)
        {
            return None;
        }
        if self.tracker(&w.sizes[pi].settings.tracker).1 == Follow::Device(hand) {
            return None;
        }
        let pose = self.overlay_world_pose(w, pi)?;
        let hit = pose::ray_plane_hit(ray, &pose)?;
        let (width_px, height_px) = w.layout.panel_size();
        let m_per_px = w.sizes[pi].settings.ui_scaling / width_px as f64;
        let (half_w, half_h) = (width_px as f64 * m_per_px / 2.0, height_px as f64 * m_per_px / 2.0);
        let (inside, outside) = (CORNER_INSIDE_PX * m_per_px, CORNER_OUTSIDE_PX * m_per_px);
        for sx in [1i8, -1] {
            for sy in [1i8, -1] {
                // positive: outside the frame
                let dx = sx as f64 * hit.x - half_w;
                let dy = sy as f64 * hit.y - half_h;
                if !((-inside..=outside).contains(&dx) && (-inside..=outside).contains(&dy)) {
                    continue;
                }
                // inside the top right is the close button
                if (sx, sy) == (1, 1) && dx <= 0.0 && dy <= 0.0 {
                    continue;
                }
                return Some(((sx, sy), Hit { point: hit.point, normal: pose::axis(&pose, 2), uv: (0.0, 0.0), distance: hit.distance }));
            }
        }
        None
    }

    /// cornerHandleXY: the handle's centre on the VR view (logical px); the top right has none
    fn corner_handle_xy(&self, w: &Worker, corner: (i8, i8)) -> Option<(i32, i32)> {
        if corner == (1, 1) {
            return None;
        }
        let (width, height) = w.layout.panel_size();
        let (width, height) = (width as i32, height as i32);
        Some((
            if corner.0 < 0 { CORNER_HANDLE_CENTER_PX } else { width - CORNER_HANDLE_CENTER_PX },
            if corner.1 > 0 { CORNER_HANDLE_CENTER_PX } else { height - CORNER_HANDLE_CENTER_PX },
        ))
    }

    /// startResize: the grabbed corner moves, the opposite one stays
    fn start_resize(&mut self, w: &mut Worker, hand: u32, corner: (i8, i8)) {
        let Some(pi) = w.region_index(Region::Panel) else { return };
        let (_, follow) = self.tracker(&w.sizes[pi].settings.tracker);
        let (Some(tracker_pose), Some(pose)) = (self.pose_of(follow), self.overlay_world_pose(w, pi)) else { return };
        let (width_px, height_px) = w.layout.panel_size();
        let m_per_px = w.sizes[pi].settings.ui_scaling / width_px as f64;
        let (sx, sy) = (corner.0 as f64, corner.1 as f64);
        self.resizing = Some(Resize {
            hand, corner, m_per_px, follow,
            relative: pose::mul(&pose::inverse(&tracker_pose), &pose),
            pose,
            fixed: (-sx * width_px as f64 * m_per_px / 2.0, -sy * height_px as f64 * m_per_px / 2.0),
            size: (width_px, height_px),
            center: (0.0, 0.0),
        });
        self.set_toolbar_visible(w, false);
        self.notify_pointer(w, None);
        self.set_highlight(w, Some(pi), COLOR_GRABBING);
    }

    /// updateResize: the corner at the laser; only the new size's frame moves (no redraw)
    fn update_resize(&mut self, w: &mut Worker, now: Instant) {
        let hand = self.resizing.as_ref().unwrap().hand;
        let hand_pose = self.ray_of(w, hand, now);
        let state = self.controller_state(hand);
        let (Some(hand_pose), Some(_)) = (hand_pose, state.filter(|s| s.button_pressed & GRIP_MASK != 0)) else {
            self.finish_resize(w);
            return;
        };
        let follow = self.resizing.as_ref().unwrap().follow;
        let tracker_pose = self.pose_of(follow);
        let r = self.resizing.as_mut().unwrap();
        if let Some(tracker_pose) = tracker_pose {
            r.pose = pose::mul(&tracker_pose, &r.relative);
        }
        let Some(hit) = pose::ray_plane_hit(&hand_pose, &r.pose) else { return };
        let (sx, sy) = (r.corner.0 as f64, r.corner.1 as f64);
        let (fixed_x, fixed_y) = r.fixed;
        let wanted = (sx * (hit.x - fixed_x) / r.m_per_px, sy * (hit.y - fixed_y) / r.m_per_px);
        let (width_px, height_px) = layout::clamp_panel_size(wanted.0, wanted.1);
        let at_limit = (width_px as f64 - wanted.0).abs() > 1.0 || (height_px as f64 - wanted.1).abs() > 1.0;
        r.size = (width_px, height_px);
        r.center = (fixed_x + sx * width_px as f64 * r.m_per_px / 2.0, fixed_y + sy * height_px as f64 * r.m_per_px / 2.0);
        let pointer = Hit { point: hit.point, normal: pose::axis(&r.pose, 2), uv: (0.0, 0.0), distance: hit.distance };
        self.show_pointer(Some(&pointer), COLOR_POINTER, 1.0, PointerKind::Dot);
        self.show_resize_ghost(w, at_limit);
    }

    /// finishResize: the size and place saved; the window shows at it once captured so (applyLayout)
    fn finish_resize(&mut self, w: &mut Worker) {
        let Some(r) = self.resizing.take() else { return };
        self.set_highlight(w, None, COLOR_NORMAL);
        self.hide_pointer();
        let Some(pi) = w.region_index(Region::Panel) else { return };
        let undo = w.sizes[pi].settings.clone();
        // a px stays as long (wider: more characters a line, not larger ones)
        w.sizes[pi].settings.ui_scaling = r.m_per_px * r.size.0 as f64;
        self.set_panel_size(w, r.size.0 as f64, r.size.1 as f64);
        let center = translation(r.center.0, r.center.1, 0.0);
        self.commit_position(w, pi, &pose::top(&pose::mul(&r.relative, &center)));
        let applied = self.panel.layout_applied_is(w);
        self.resize_undo = if applied { None } else { Some(undo) };
        if applied {
            self.hide_resize_ghost(); // the size did not change
        }
    }

    fn show_resize_ghost(&mut self, w: &Worker, at_limit: bool) {
        let (Some(ghost), Some(r)) = (self.ghost, self.resizing.as_ref()) else { return };
        if !self.panel_ready {
            return;
        }
        let (width_px, height_px) = r.size;
        let key = (width_px / 4, height_px / 4, at_limit);
        let center = translation(r.center.0, r.center.1, GHOST_FRONT_M);
        let transform = pose::top(&pose::mul(&r.pose, &center));
        let width = width_px as f64 * r.m_per_px;
        if Some(key) != self.ghost_key {
            self.ghost_key = Some(key);
            if let Err(e) = self.set_ghost_image(&layout::ghost_image(width_px, height_px, at_limit)) {
                (w.log)(format!("overlay: 伸ばす枠を出せませんでした: {e}"));
            }
        }
        let _ = self.vr.overlay.set_overlay_transform_absolute(ghost, vrct_openvr::TRACKING_UNIVERSE_STANDING, &crate::math::to_hmd(&transform));
        let _ = self.vr.overlay.set_overlay_width_in_meters(ghost, width as f32);
        let _ = self.vr.overlay.show_overlay(ghost);
    }

    pub fn hide_resize_ghost(&self) {
        if let Some(ghost) = self.ghost {
            let _ = self.vr.overlay.hide_overlay(ghost);
        }
    }

    /// smoothGrab: the hand's shake smoothed while it moves slowly (in the tracker's space, so a
    /// window on a hand does not lag and wobble); fast moves are followed as they are
    fn smooth_grab(&mut self, target: &Mat34, dt: f64) -> Mat34 {
        let (previous, previous_target) = (self.grab_smoothed, self.grab_prev_target);
        self.grab_prev_target = Some(*target);
        let (Some(previous), Some(previous_target)) = (previous, previous_target) else {
            self.grab_smoothed = Some(*target);
            return *target;
        };
        if dt <= 0.0 {
            self.grab_smoothed = Some(*target);
            return *target;
        }
        // the speed of the hand itself (the smoothed place lags)
        let column = |m: &Mat34| [m[0][3], m[1][3], m[2][3]];
        let speed = pose::norm(pose::sub(column(target), column(&previous_target))) / dt;
        let alpha = if speed >= GRAB_SMOOTH_MAX_SPEED_M { 1.0 } else { 1.0 - (-dt / GRAB_SMOOTH_TAU_SEC).exp() };
        let mut smoothed = *target;
        for (i, row) in smoothed.iter_mut().enumerate() {
            row[3] = previous[i][3] + (target[i][3] - previous[i][3]) * alpha;
        }
        self.grab_smoothed = Some(smoothed);
        smoothed
    }

    /// commitPosition: the place (and width) moved to, saved through the app
    pub fn commit_position(&mut self, w: &mut Worker, index: usize, relative: &Mat34) {
        let base = crate::math::Tracker::from_name(&w.sizes[index].settings.tracker).base();
        let p = pose::matrix_to_position(&base, relative);
        w.sizes[index].settings.position = p.map(|v| pose::round_to(v, 4));
        let region = w.sizes[index].region;
        if region == Some(Region::Launcher) {
            let s = &w.sizes[index].settings;
            let distance = pose::norm([s.position[0], s.position[1], s.position[2]]);
            (w.log)(format!("overlay: ランチャーを放しました (distance_m {distance:.2}, width_m {:.3}, limit_m {})",
                            s.ui_scaling, pose::LAUNCHER_REACH_M));
            let xyz = [s.position[0], s.position[1], s.position[2]];
            // too far, small or large: back to the wrist of the hand it is on
            if w.launcher_defaults.is_some() && pose::launcher_out_of_reach(xyz, s.ui_scaling) {
                w.request_launcher_reset(true);
            }
        }
        if region == Some(Region::Panel) {
            // moved after a resize: not undone with it
            self.resize_undo = None;
        }
        self.notify_position(w, index);
    }

    /// notifyPosition: the place, width, tracker (and the log's size) to save
    pub fn notify_position(&self, w: &Worker, index: usize) {
        w.emit(crate::overlay::Event::Position { size: w.sizes[index].name.clone(), settings: w.sizes[index].settings.clone() });
    }

    // ------------------------------------------------------------------ the bar under the log

    /// placeToolbar: under the log; moved only while shown
    pub fn place_toolbar(&mut self, w: &Worker, follow: Follow, panel_relative: &Mat34) {
        let Some(pi) = w.region_index(Region::Panel) else { return };
        let [_, _, panel_w, panel_h] = w.layout.region(Region::Panel).map(f64::from);
        let [_, _, bar_w, bar_h] = w.layout.region(Region::Toolbar).map(f64::from);
        let panel_height_m = w.sizes[pi].settings.ui_scaling * panel_h / panel_w;
        let bar_height_m = self.region_width_m(w, Region::Toolbar) * bar_h / bar_w;
        let offset = translation(0.0, -(panel_height_m / 2.0 + TOOLBAR_GAP_M + bar_height_m / 2.0), 0.0);
        let relative = pose::top(&pose::mul(&pose::homogeneous(panel_relative), &offset));
        self.toolbar_relative = Some(relative);
        self.toolbar_follow = Some(follow);
        if self.toolbar_visible
            && let Some(handle) = self.toolbar
        {
            self.transform_handle(handle, follow, &relative);
        }
    }

    pub fn set_toolbar_visible(&mut self, w: &mut Worker, visible: bool) {
        let Some(handle) = self.toolbar else { return };
        if visible == self.toolbar_visible {
            return;
        }
        let Some(pi) = w.region_index(Region::Panel) else { return };
        if visible && self.pending[pi] {
            return;
        }
        if !visible {
            self.reset_tooltip_epoch(w, true);
        }
        self.toolbar_visible = visible;
        if visible {
            let (_, follow) = self.tracker(&w.sizes[pi].settings.tracker);
            let relative = self.relative(w, pi);
            self.place_toolbar(w, follow, &relative);
            // faded in from where it is
            let _ = self.vr.overlay.set_overlay_alpha(handle, self.toolbar_alpha as f32);
            let _ = self.vr.overlay.show_overlay(handle);
        }
        // hiding fades it first (update_toolbar_fade)
    }

    /// updateToolbarFade: towards shown / hidden over TOOLBAR_FADE_SEC, hidden once clear
    fn update_toolbar_fade(&mut self, now: Instant) {
        let Some(handle) = self.toolbar else { return };
        let dt = self.toolbar_faded_at.map_or(0.0, |at| since(now, at));
        self.toolbar_faded_at = Some(now);
        let target = if self.toolbar_visible { 1.0 } else { 0.0 };
        if self.toolbar_alpha == target {
            return;
        }
        let step = dt / TOOLBAR_FADE_SEC;
        self.toolbar_alpha = if target > self.toolbar_alpha { (self.toolbar_alpha + step).min(target) } else { (self.toolbar_alpha - step).max(target) };
        let _ = self.vr.overlay.set_overlay_alpha(handle, self.toolbar_alpha as f32);
        if self.toolbar_alpha == 0.0 && target == 0.0 {
            let _ = self.vr.overlay.hide_overlay(handle);
        }
    }

    /// hideToolbarNow: with the log, hidden at once
    fn hide_toolbar_now(&mut self, w: &mut Worker) {
        self.set_toolbar_visible(w, false);
        if let Some(handle) = self.toolbar
            && self.toolbar_alpha > 0.0
        {
            self.toolbar_alpha = 0.0;
            let _ = self.vr.overlay.hide_overlay(handle);
        }
    }

    /// updateToolbarVisibility: shown after pointing at the log (or the bar) a while, hidden a while after
    fn update_toolbar_visibility(&mut self, w: &mut Worker, now: Instant, pointing_log: bool) {
        if self.hidden.contains(&Region::Panel) || !w.vr_panel_enabled {
            self.toolbar_pointed_since = None;
            self.hide_toolbar_now(w);
            return;
        }
        if pointing_log {
            let pointed = *self.toolbar_pointed_since.get_or_insert(now);
            self.toolbar_last_pointed = Some(now);
            if since(now, pointed) >= TOOLBAR_SHOW_AFTER_SEC {
                self.set_toolbar_visible(w, true);
            }
        } else {
            self.toolbar_pointed_since = None;
            if self.toolbar_last_pointed.is_none_or(|at| since(now, at) >= TOOLBAR_HIDE_AFTER_SEC) {
                self.set_toolbar_visible(w, false);
            }
        }
    }

    // ------------------------------------------------------------------ the launcher

    /// headsetWorn (unknown counts as worn)
    fn headset_worn(&self) -> bool {
        let level = self.vr.system.tracked_device_activity_level(TRACKED_DEVICE_INDEX_HMD);
        [vrct_openvr::ACTIVITY_UNKNOWN, vrct_openvr::ACTIVITY_USER_INTERACTION, vrct_openvr::ACTIVITY_USER_INTERACTION_TIMEOUT].contains(&level)
    }

    /// updateLauncherVisibility: shown when the wrist is looked at, kept while pointed at
    fn update_launcher_visibility(&mut self, w: &mut Worker, now: Instant) {
        let dt = self.launcher_prev_time.map_or(0.0, |at| since(now, at).min(0.1));
        self.launcher_prev_time = Some(now);
        let Some(li) = w.region_index(Region::Launcher) else { return };
        if w.intro == Intro::Playing && self.launcher_intro_until.is_some_and(|until| now >= until) {
            self.set_launcher_intro(w, Intro::Idle);
        }
        let mut want = if !w.launcher_auto_hide {
            true
        } else if self.launcher_pointed || self.grabbing.as_ref().is_some_and(|g| g.index == li) {
            self.launcher_shown
        } else {
            match (self.pose_of(HMD), self.overlay_world_pose(w, li)) {
                (Some(head), Some(launcher)) if self.launcher_shown => pose::launcher_looks_visible(
                    &launcher, &head, LAUNCHER_FACE_DEG + LAUNCHER_HIDE_MARGIN_DEG, LAUNCHER_GAZE_HIDE_DEG),
                (Some(head), Some(launcher)) => pose::launcher_looks_visible(&launcher, &head, LAUNCHER_FACE_DEG, LAUNCHER_GAZE_SHOW_DEG),
                _ => self.launcher_shown,
            }
        };
        // shown through the intro and the flight back, wherever the eyes go
        if w.intro == Intro::Playing || self.launcher_return.is_some() {
            want = true;
        }
        // shown / hidden once it stays so a moment (at once when auto-hide was turned off)
        if want == self.launcher_shown {
            self.launcher_change_since = None;
        } else if !w.launcher_auto_hide {
            self.launcher_shown = true;
            self.launcher_shown_at = Some(now);
            self.launcher_change_since = None;
        } else {
            let changing = *self.launcher_change_since.get_or_insert(now);
            let wait = if want { LAUNCHER_SHOW_AFTER_SEC } else { LAUNCHER_HIDE_AFTER_SEC };
            if since(now, changing) >= wait {
                self.launcher_shown = want;
                self.launcher_change_since = None;
                if want {
                    self.launcher_shown_at = Some(now);
                }
            }
        }
        if w.intro == Intro::Pending && self.panel.last_raw.is_some() {
            // once the VR view was captured (else the intro is missed). With the headset on, in
            // front of the eyes and flying to the wrist; else on the wrist when it is looked at.
            // ponytail: last_raw is the transfer's dedup value, not proof the VR view has "playing";
            // over ~0.5 s late the intro's end is cut. A flag of its own if that shows in VR.
            if let Some(head) = self.pose_of(HMD)
                && self.headset_worn()
            {
                self.launcher_intro_front = Some(pose::intro_front_pose(&head));
            }
            if self.launcher_intro_front.is_some() || self.launcher_shown {
                self.launcher_intro_started = now;
                self.launcher_intro_tick = now;
                self.launcher_intro_until = Some(now + Duration::from_secs_f64(LAUNCHER_INTRO_SEC));
                self.set_launcher_intro(w, Intro::Playing);
            }
        }
        let target = if self.launcher_shown { 1.0 } else { 0.0 };
        let step = dt / LAUNCHER_FADE_SEC;
        self.launcher_alpha = if target > self.launcher_alpha { (self.launcher_alpha + step).min(target) } else { (self.launcher_alpha - step).max(target) };
        let was_interactive = self.launcher_interactive;
        self.launcher_interactive = self.launcher_alpha >= 1.0 && w.intro == Intro::Idle && self.launcher_return.is_none()
            && (!w.launcher_auto_hide || self.launcher_shown_at.is_none_or(|at| since(now, at) >= LAUNCHER_INPUT_DELAY_SEC));
        if was_interactive && !self.launcher_interactive {
            self.reset_tooltip_epoch(w, true);
        }
    }

    /// setLauncherIntro: told to the app when it changes
    pub fn set_launcher_intro(&mut self, w: &mut Worker, state: Intro) {
        if state == w.intro {
            return;
        }
        w.intro = state;
        if state == Intro::Pending {
            self.launcher_intro_logged.clear();
        }
        if state != Intro::Playing {
            self.end_launcher_intro_flight(w);
        }
        w.emit(crate::overlay::Event::LauncherIntro(state));
    }

    /// updateLauncherIntroFlight: in front of the eyes (following the gaze a little behind), then
    /// flying to the wrist, faster and faster, shrinking (fixed in the room while it flies)
    fn update_launcher_intro_flight(&mut self, w: &mut Worker, now: Instant) {
        let (Some(mut front), Some(li)) = (self.launcher_intro_front, w.region_index(Region::Launcher)) else { return };
        let elapsed = since(now, self.launcher_intro_started);
        if elapsed >= INTRO_FRONT_SEC + INTRO_FLY_SEC {
            self.end_launcher_intro_flight(w);
            return;
        }
        if elapsed < INTRO_FRONT_SEC {
            if let Some(head) = self.pose_of(HMD) {
                let follow = 1.0 - (-INTRO_FRONT_FOLLOW_PER_SEC * since(now, self.launcher_intro_tick)).exp();
                front = pose::intro_flight_pose(&front, &pose::intro_front_pose(&head), follow);
                self.launcher_intro_front = Some(front);
            }
            self.launcher_intro_tick = now;
        }
        // the wrist not tracked: waits here (the time limit above puts it back)
        let Some(target) = self.overlay_world_pose(w, li) else { return };
        let progress = ((elapsed - INTRO_FRONT_SEC) / INTRO_FLY_SEC).clamp(0.0, 1.0).powi(2);
        let pose = pose::intro_flight_pose(&front, &target, progress);
        let handle = self.handles[li];
        let _ = self.vr.overlay.set_overlay_transform_absolute(handle, vrct_openvr::TRACKING_UNIVERSE_STANDING, &crate::math::to_hmd(&pose::top(&pose)));
        // the scale shrinks by multiplying (linear shrinks all at the end)
        let width = self.region_width_m(w, Region::Launcher) * INTRO_FRONT_SCALE.powf(1.0 - progress);
        let _ = self.vr.overlay.set_overlay_width_in_meters(handle, width as f32);
    }

    /// endLauncherIntroFlight: back on the wrist at its width (hidden while the wrist is not connected)
    fn end_launcher_intro_flight(&mut self, w: &mut Worker) {
        if self.launcher_intro_front.take().is_none() {
            return;
        }
        let Some(li) = w.region_index(Region::Launcher) else { return };
        self.place(w, li);
        let width = w.sizes[li].settings.ui_scaling;
        self.update_ui_scaling(w, li, width);
        if self.pending[li] {
            self.launcher_shown = false;
            self.launcher_alpha = 0.0;
            // going on would put it in front again
            if w.intro == Intro::Playing {
                self.set_launcher_intro(w, Intro::Idle);
            }
        }
    }

    /// applyLauncherDefaults: the default place, angle, width and hand; `keep_hand` (the automatic
    /// recovery): only pulled within reach of the wrist it is on
    pub fn apply_launcher_defaults(&mut self, w: &mut Worker, keep_hand: bool) {
        let Some(li) = w.region_index(Region::Launcher) else { return };
        let s = &mut w.sizes[li].settings;
        if keep_hand {
            let (xyz, width) = pose::launcher_nearest_in_reach([s.position[0], s.position[1], s.position[2]], s.ui_scaling);
            s.position[..3].copy_from_slice(&xyz);
            s.ui_scaling = width;
            return;
        }
        if let Some(d) = &w.launcher_defaults {
            s.position = d.position;
            s.ui_scaling = d.ui_scaling;
            s.tracker = d.tracker.clone();
        }
    }

    /// updateLauncherReturn: from where it is to the wrist's default place, faster and faster
    fn update_launcher_return(&mut self, w: &mut Worker, now: Instant) {
        // waits for a grab, a resize or the intro to end (no mixing up the hands)
        let can_start = self.grabbing.is_none() && self.resizing.is_none() && self.launcher_intro_front.is_none();
        let li = w.region_index(Region::Launcher);
        if w.launcher_reset_requested && can_start {
            w.launcher_reset_requested = false;
            let keep_hand = std::mem::take(&mut w.launcher_reset_keep_hand);
            if self.launcher_return.is_some() {
                // asked again while flying: it goes on (no jump); the button's reset to the left hand
                // takes the settings now, the target follows them each frame
                if !keep_hand {
                    self.apply_launcher_defaults(w, false);
                }
            } else {
                let start = li.filter(|_| w.vr_panel_enabled).and_then(|li| self.overlay_world_pose(w, li));
                let width = self.region_width_m(w, Region::Launcher);
                self.apply_launcher_defaults(w, keep_hand);
                let Some(start) = start else {
                    self.finish_launcher_return(w);
                    return;
                };
                self.launcher_return = Some(Return { start, width, started: now });
            }
        }
        let (Some(ret), Some(li)) = (self.launcher_return.as_ref(), li) else { return };
        let elapsed = since(now, ret.started);
        let (start, start_width) = (ret.start, ret.width);
        // the wrist's place by the defaults (followed as the hand moves)
        let target = self.overlay_world_pose(w, li);
        let Some(target) = target.filter(|_| elapsed < LAUNCHER_RETURN_SEC) else {
            self.finish_launcher_return(w);
            return;
        };
        let progress = (elapsed / LAUNCHER_RETURN_SEC).powi(2);
        let pose = pose::intro_flight_pose(&start, &target, progress);
        let handle = self.handles[li];
        let _ = self.vr.overlay.set_overlay_transform_absolute(handle, vrct_openvr::TRACKING_UNIVERSE_STANDING, &crate::math::to_hmd(&pose::top(&pose)));
        let width_end = self.region_width_m(w, Region::Launcher);
        let _ = self.vr.overlay.set_overlay_width_in_meters(handle, (start_width * (width_end / start_width).powf(progress)) as f32);
    }

    /// finishLauncherReturn: the default place and width set, saved and told
    fn finish_launcher_return(&mut self, w: &mut Worker) {
        self.launcher_return = None;
        let Some(li) = w.region_index(Region::Launcher) else { return };
        self.place(w, li);
        let width = w.sizes[li].settings.ui_scaling;
        self.update_ui_scaling(w, li, width);
        if self.pending[li] {
            // the wrist not connected: it would stay behind, so hidden until it connects
            self.launcher_shown = false;
            self.launcher_alpha = 0.0;
        }
        self.notify_position(w, li);
    }

    // ------------------------------------------------------------------ the windows

    /// applyVrWindows: shown / hidden as asked; then the log's anchor, recall and out-of-view
    fn apply_vr_windows(&mut self, w: &mut Worker) {
        let wanted = [(Region::Panel, w.vr_windows_wanted.0), (Region::Popup, w.vr_windows_wanted.1), (Region::Launcher, true)];
        if !w.vr_panel_enabled {
            // off: not waiting for the VR view
            self.first_frame_wait_since = None;
        }
        for (region, wanted) in wanted {
            let Some(i) = w.region_index(region) else { continue };
            let wanted = wanted && w.vr_panel_enabled;
            if wanted && self.panel.image_size.is_none() {
                // never captured yet: no board without a picture; a hint in the log when it lasts
                let now = Instant::now();
                match self.first_frame_wait_since {
                    None => self.first_frame_wait_since = Some(now),
                    Some(at) if !self.first_frame_wait_logged && since(now, at) > FIRST_FRAME_WARN_SEC => {
                        self.first_frame_wait_logged = true;
                        (w.log)(format!("overlay: VR画面がまだ一度も撮れていないので、ランチャーを出せません (error: {:?})", self.panel.error));
                    }
                    _ => {}
                }
                continue;
            }
            let hidden = self.hidden.contains(&region);
            if wanted && hidden {
                if region == Region::Popup {
                    self.place_popup(w);
                }
                self.hidden.remove(&region);
                let _ = self.vr.overlay.show_overlay(self.handles[i]);
                // shown again: the VR view sent again too
                self.panel.last_raw = None;
                if region == Region::Panel {
                    self.place(w, i);
                    // left where it cannot be seen: in front of the eyes when opened
                    if self.is_panel_out_of_view(w) {
                        self.recall_panel(w);
                    }
                }
            } else if !wanted && !hidden {
                if matches!(region, Region::Panel | Region::Launcher) {
                    self.reset_tooltip_epoch(w, true);
                }
                self.hidden.insert(region);
                let _ = self.vr.overlay.hide_overlay(self.handles[i]);
                if region == Region::Panel {
                    self.set_toolbar_visible(w, false);
                    // the frame waiting for the new size goes too
                    self.hide_resize_ghost();
                    if self.resizing.take().is_some() {
                        self.set_highlight(w, None, COLOR_NORMAL);
                        self.hide_pointer();
                    }
                }
                if self.grabbing.as_ref().is_some_and(|g| g.index == i) {
                    self.drop_grab(w);
                }
            }
        }
        // not moved while grabbed (the grab sets its place this frame); recalled after release
        if self.grabbing.is_some() || self.resizing.is_some() {
            return;
        }
        if let Some(anchor) = w.requested_anchor.take()
            && w.region_index(Region::Panel).is_some()
        {
            self.set_anchor(w, &anchor);
        }
        if let Some(at) = w.recall_requested {
            if w.region_index(Region::Panel).is_some() && !self.hidden.contains(&Region::Panel) {
                w.recall_requested = None;
                self.recall_panel(w);
            } else if at.elapsed().as_secs_f64() > RECALL_PENDING_SEC {
                // the log was not opened
                w.recall_requested = None;
            }
        }
        let out = w.region_index(Region::Panel).is_some() && self.is_panel_out_of_view(w);
        w.notify_panel_out_of_view(out);
    }

    /// isPanelOutOfView: open and off the gaze (fixed in the room or to the head only: a hand can be raised)
    fn is_panel_out_of_view(&self, w: &Worker) -> bool {
        let Some(pi) = w.region_index(Region::Panel) else { return false };
        let tracker = w.sizes[pi].settings.tracker.as_str();
        if self.hidden.contains(&Region::Panel) || !(tracker == "Playspace" || tracker == "HMD") {
            return false;
        }
        match (self.pose_of(HMD), self.overlay_world_pose(w, pi)) {
            (Some(head), Some(world)) => pose::is_out_of_view(&head, pose::position(&world), w.panel_out_of_view),
            _ => false,
        }
    }

    /// recallPanel: in front of the eyes, fixed in the room, saved
    fn recall_panel(&mut self, w: &mut Worker) {
        let (Some(head), Some(pi)) = (self.pose_of(HMD), w.region_index(Region::Panel)) else { return };
        w.sizes[pi].settings.tracker = "Playspace".into();
        self.commit_position(w, pi, &pose::top(&pose::recall_pose(&head)));
        self.place(w, pi);
    }

    /// setAnchor: what the log follows, from where it shows now (brought nearer on a hand, to a
    /// fair distance on the head: far windows swing with the wrist)
    fn set_anchor(&mut self, w: &mut Worker, anchor: &str) {
        let Some(pi) = w.region_index(Region::Panel) else { return };
        let (_, follow) = self.tracker(anchor);
        let (Some(new_pose), Some(world)) = (self.pose_of(follow), self.overlay_world_pose(w, pi)) else {
            // the tracker is not found: the UI shows the switch, so it is told back
            self.notify_position(w, pi);
            return;
        };
        let mut relative = pose::mul(&pose::inverse(&new_pose), &world);
        let offset = pose::position(&relative);
        let distance = pose::norm(offset);
        let (low, high) = match anchor {
            "LeftHand" | "RightHand" => (0.0, HAND_ANCHOR_MAX_DISTANCE_M),
            "HMD" => HMD_ANCHOR_DISTANCE_RANGE_M,
            _ => (0.0, f64::INFINITY),
        };
        if distance > 1e-6 && !(low..=high).contains(&distance) {
            pose::set_position(&mut relative, pose::scale(offset, distance.clamp(low, high) / distance));
        }
        w.sizes[pi].settings.tracker = anchor.into();
        self.commit_position(w, pi, &pose::top(&relative));
        self.place(w, pi);
    }

    /// placePopup: above the launcher, facing the head, fixed in the room
    fn place_popup(&mut self, w: &mut Worker) {
        let (Some(head), Some(popup)) = (self.pose_of(HMD), w.region_index(Region::Popup)) else { return };
        let head_pos = pose::position(&head);
        let launcher = w.region_index(Region::Launcher).and_then(|li| self.overlay_world_pose(w, li));
        let mut p = match launcher {
            Some(l) => pose::add(pose::position(&l), [0.0, POPUP_ABOVE_LAUNCHER_M, 0.0]),
            // no launcher: in front of the head
            None => pose::add(head_pos, pose::scale(pose::axis(&head, 2), -POPUP_DISTANCE_RANGE_M.0)),
        };
        let horizontal = [p[0] - head_pos[0], 0.0, p[2] - head_pos[2]];
        let distance = pose::norm(horizontal);
        if distance > 1e-6 {
            let clamped = distance.clamp(POPUP_DISTANCE_RANGE_M.0, POPUP_DISTANCE_RANGE_M.1);
            p = pose::add(pose::add(head_pos, pose::scale(horizontal, clamped / distance)), [0.0, p[1] - head_pos[1], 0.0]);
        }
        let world = pose::face_head(p, &head);
        w.sizes[popup].settings.tracker = "Playspace".into();
        self.commit_position(w, popup, &pose::top(&world));
        self.place(w, popup);
    }

    /// onGrabError: the grab or resize ends (not failing the same way every frame)
    pub fn on_grab_error(&mut self, w: &mut Worker, error: anyhow::Error) {
        self.grabbing = None;
        if self.resizing.take().is_some() {
            self.hide_resize_ghost();
        }
        self.set_highlight(w, None, COLOR_NORMAL);
        self.hide_pointer();
        let message = error.to_string();
        if self.grab_error.as_deref() != Some(message.as_str()) {
            (w.log)(format!("overlay: {message}"));
            self.grab_error = Some(message);
        }
    }
}

impl Worker {
    /// requestLauncherReset (from the overlay thread itself)
    pub fn request_launcher_reset(&mut self, keep_hand: bool) {
        self.apply_request(crate::overlay::Command::LauncherReset(keep_hand));
    }
}

/// Settings kept with the undo of a resize: only the place, width and tracker go back
pub(crate) fn restore_place(settings: &mut Settings, undo: &Settings) {
    settings.position = undo.position;
    settings.ui_scaling = undo.ui_scaling;
    settings.tracker = undo.tracker.clone();
}
