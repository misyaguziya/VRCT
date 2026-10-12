//! Poses in the room for the VR UI (the module functions of models/overlay/overlay.py): where a
//! window goes when grabbed, recalled or opened, the launcher's intro flight, and the checks of
//! what the head sees. 4x4 row-major, SteamVR's standing space (metres, +Y up, the head looks at -Z).
use crate::math::{Mat34, Mat4};

pub type Vec3 = [f64; 3];

pub const IDENTITY: Mat4 = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]];

// The range of the distance from the eyes while grabbed (the stick and the arm change it)
pub const PUSH_PULL_DISTANCE_RANGE_M: (f64, f64) = (0.25, 2.5);
const PUSH_PULL_SPEED: f64 = 1.0;
const PUSH_PULL_DEADZONE: f64 = 0.5;
// The log is out of view past this angle from the gaze or this distance; coming back uses the
// inner values (no flicker at the edge)
const RECALL_OUT_OF_VIEW_DEG: (f64, f64) = (60.0, 50.0);
const RECALL_OUT_OF_VIEW_DISTANCE_M: (f64, f64) = (3.0, 2.7);
// A recalled log: this far ahead of the eyes, this much below them, aimed within this pitch
const RECALL_DISTANCE_M: f64 = 0.7;
const RECALL_BELOW_EYE_M: f64 = 0.1;
const RECALL_PITCH_RANGE_DEG: (f64, f64) = (-45.0, 20.0);
// The launcher's intro: shown this far ahead of the eyes
const INTRO_FRONT_DISTANCE_M: f64 = 0.7;
// The launcher is lost when this far from the wrist's place or outside these widths
pub const LAUNCHER_REACH_M: f64 = 0.15;
pub const LAUNCHER_WIDTH_RANGE_M: (f64, f64) = (0.12, 1.0);

pub fn sub(a: Vec3, b: Vec3) -> Vec3 {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

pub fn add(a: Vec3, b: Vec3) -> Vec3 {
    [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
}

pub fn scale(a: Vec3, s: f64) -> Vec3 {
    [a[0] * s, a[1] * s, a[2] * s]
}

pub fn dot(a: Vec3, b: Vec3) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

pub fn cross(a: Vec3, b: Vec3) -> Vec3 {
    [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
}

pub fn norm(a: Vec3) -> f64 {
    dot(a, a).sqrt()
}

/// Column j of the rotation (0: x, 1: y, 2: z axis)
pub fn axis(m: &Mat4, j: usize) -> Vec3 {
    [m[0][j], m[1][j], m[2][j]]
}

pub fn position(m: &Mat4) -> Vec3 {
    axis(m, 3)
}

pub fn set_position(m: &mut Mat4, p: Vec3) {
    for (i, v) in p.into_iter().enumerate() {
        m[i][3] = v;
    }
}

pub fn mul(a: &Mat4, b: &Mat4) -> Mat4 {
    crate::math::mul(a, b)
}

pub fn homogeneous(m: &Mat34) -> Mat4 {
    [m[0], m[1], m[2], [0.0, 0.0, 0.0, 1.0]]
}

pub fn top(m: &Mat4) -> Mat34 {
    [m[0], m[1], m[2]]
}

/// np.linalg.inv of a rigid transform (every pose here is a rotation and a move)
pub fn inverse(m: &Mat4) -> Mat4 {
    let p = position(m);
    let row = |i: usize| {
        let r = axis(m, i);
        [r[0], r[1], r[2], -dot(r, p)]
    };
    [row(0), row(1), row(2), [0.0, 0.0, 0.0, 1.0]]
}

/// A pose from its axes and position
fn from_axes(x: Vec3, y: Vec3, z: Vec3, p: Vec3) -> Mat4 {
    [[x[0], y[0], z[0], p[0]], [x[1], y[1], z[1], p[1]], [x[2], y[2], z[2], p[2]], [0.0, 0.0, 0.0, 1.0]]
}

/// laserTilt: the laser turned up by `degrees` about the tip's X axis
pub fn laser_tilt(degrees: f64) -> Mat4 {
    let (s, c) = degrees.to_radians().sin_cos();
    let mut tilt = IDENTITY;
    tilt[1][1] = c;
    tilt[1][2] = -s;
    tilt[2][1] = s;
    tilt[2][2] = c;
    tilt
}

/// Where a controller's laser (its -Z) meets a plane (an overlay's +Z face)
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PlaneHit {
    /// from the plane's centre, metres (x right, y up)
    pub x: f64,
    pub y: f64,
    pub point: Vec3,
    pub distance: f64,
}

/// rayPlaneHit: unlike OpenVR's intersection, also outside the overlay and on its clear corners
pub fn ray_plane_hit(ray: &Mat4, plane: &Mat4) -> Option<PlaneHit> {
    let origin = position(ray);
    let direction = scale(axis(ray, 2), -1.0);
    let normal = axis(plane, 2);
    let denom = dot(direction, normal);
    if denom.abs() < 1e-6 {
        return None;
    }
    let distance = dot(sub(position(plane), origin), normal) / denom;
    if distance <= 0.0 {
        return None;
    }
    let point = add(origin, scale(direction, distance));
    let local = transform_point(&inverse(plane), point);
    Some(PlaneHit { x: local[0], y: local[1], point, distance })
}

pub fn transform_point(m: &Mat4, p: Vec3) -> Vec3 {
    let mut out = [0.0; 3];
    for (i, o) in out.iter_mut().enumerate() {
        *o = m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3];
    }
    out
}

/// popupPoseFacing: at `position`, its face (+Z) towards `target`, up along `up` (else the room's up)
pub fn pose_facing(position: Vec3, target: Vec3, up: Option<Vec3>) -> Mat4 {
    let z = sub(target, position);
    let length = norm(z);
    let z = scale(z, 1.0 / if length == 0.0 { 1.0 } else { length });
    let mut x = cross(up.unwrap_or([0.0, 1.0, 0.0]), z);
    if norm(x) < 1e-6 {
        x = [1.0, 0.0, 0.0];
    }
    let x = scale(x, 1.0 / norm(x));
    let y = cross(z, x);
    from_axes(x, y, z, position)
}

/// faceHead: at `position`, facing the head, up along the head's up
pub fn face_head(position: Vec3, head: &Mat4) -> Mat4 {
    pose_facing(position, self::position(head), Some(axis(head, 1)))
}

/// poseOnSphere: on the sphere of `radius` round the eyes, in the direction of `point`, facing the head
pub fn pose_on_sphere(point: Vec3, head: &Mat4, radius: f64) -> Mat4 {
    let head_pos = position(head);
    let mut direction = sub(point, head_pos);
    let mut length = norm(direction);
    if length < 1e-6 {
        direction = scale(axis(head, 2), -1.0);
        length = 1.0;
    }
    face_head(add(head_pos, scale(direction, radius / length)), head)
}

/// sphereRadius: the eyes-to-window distance while grabbed, scaled by how far the arm went out.
/// A window outside the range is not pulled into it at once, only moved towards it.
pub fn sphere_radius(base: f64, hand_start: f64, hand_now: f64) -> f64 {
    let (low, high) = PUSH_PULL_DISTANCE_RANGE_M;
    (base * hand_now / hand_start.max(0.05)).max(low.min(base)).min(high.max(base))
}

/// isOutOfView: `position` off the gaze (-Z) or too far. `was_out`: the last answer, so coming
/// back needs the inner thresholds.
pub fn is_out_of_view(head: &Mat4, position: Vec3, was_out: bool) -> bool {
    let (degrees, distance_limit) = if was_out {
        (RECALL_OUT_OF_VIEW_DEG.1, RECALL_OUT_OF_VIEW_DISTANCE_M.1)
    } else {
        (RECALL_OUT_OF_VIEW_DEG.0, RECALL_OUT_OF_VIEW_DISTANCE_M.0)
    };
    let direction = sub(position, self::position(head));
    let distance = norm(direction);
    if distance > distance_limit {
        return true;
    }
    if distance < 1e-6 {
        return false;
    }
    dot(scale(direction, 1.0 / distance), scale(axis(head, 2), -1.0)) < degrees.to_radians().cos()
}

/// recallPose: ahead along the gaze (pitch kept within RECALL_PITCH_RANGE_DEG), a little below
/// the eyes, facing the head
pub fn recall_pose(head: &Mat4) -> Mat4 {
    let head_pos = position(head);
    let gaze = scale(axis(head, 2), -1.0);
    let mut forward = [gaze[0], 0.0, gaze[2]];
    if norm(forward) < 1e-6 {
        // looking straight up or down: the head's up is ahead
        let up = axis(head, 1);
        forward = [up[0], 0.0, up[2]];
    }
    let length = norm(forward);
    let forward = scale(forward, 1.0 / if length == 0.0 { 1.0 } else { length });
    let (low, high) = RECALL_PITCH_RANGE_DEG;
    let pitch = gaze[1].clamp(-1.0, 1.0).asin().to_degrees().max(low).min(high).to_radians();
    let direction = add(scale(forward, pitch.cos()), [0.0, pitch.sin(), 0.0]);
    let p = add(head_pos, scale(direction, RECALL_DISTANCE_M));
    face_head([p[0], p[1] - RECALL_BELOW_EYE_M, p[2]], head)
}

/// _quaternionOf: a rotation matrix as a unit quaternion (w, x, y, z)
fn quaternion_of(m: &Mat4) -> [f64; 4] {
    let trace = m[0][0] + m[1][1] + m[2][2];
    let mut q = [0.0; 4];
    if trace > 0.0 {
        let s = 2.0 * (trace + 1.0).sqrt();
        q = [0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s];
    } else {
        // np.argmax: the first largest
        let mut i = 0;
        for k in 1..3 {
            if m[k][k] > m[i][i] {
                i = k;
            }
        }
        let (j, k) = ((i + 1) % 3, (i + 2) % 3);
        let s = 2.0 * (m[i][i] - m[j][j] - m[k][k] + 1.0).sqrt();
        q[0] = (m[k][j] - m[j][k]) / s;
        q[1 + i] = 0.25 * s;
        q[1 + j] = (m[j][i] + m[i][j]) / s;
        q[1 + k] = (m[k][i] + m[i][k]) / s;
    }
    let n = (q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]).sqrt();
    q.map(|v| v / n)
}

fn matrix_of(q: [f64; 4]) -> [[f64; 3]; 3] {
    let [w, x, y, z] = q;
    [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
    ]
}

/// introFrontPose: ahead along the gaze (pitch as it is), facing the head
pub fn intro_front_pose(head: &Mat4) -> Mat4 {
    face_head(sub(position(head), scale(axis(head, 2), INTRO_FRONT_DISTANCE_M)), head)
}

/// introFlightPose: `progress` (0..1) of the way from `front` to `target`: straight for the
/// position, slerp the short way round for the rotation (blending matrices spun the launcher
/// round when the two were nearly opposite)
pub fn intro_flight_pose(front: &Mat4, target: &Mat4, progress: f64) -> Mat4 {
    let a = quaternion_of(front);
    let mut b = quaternion_of(target);
    let mut d: f64 = (0..4).map(|i| a[i] * b[i]).sum();
    if d < 0.0 {
        b = b.map(|v| -v);
        d = -d;
    }
    let q: [f64; 4] = if d > 0.9995 {
        std::array::from_fn(|i| a[i] * (1.0 - progress) + b[i] * progress)
    } else {
        let theta = d.acos();
        let (wa, wb) = (((1.0 - progress) * theta).sin(), (progress * theta).sin());
        std::array::from_fn(|i| (wa * a[i] + wb * b[i]) / theta.sin())
    };
    let n = (q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]).sqrt();
    let r = matrix_of(q.map(|v| v / n));
    let p = add(scale(position(front), 1.0 - progress), scale(position(target), progress));
    [[r[0][0], r[0][1], r[0][2], p[0]], [r[1][0], r[1][1], r[1][2], p[1]], [r[2][0], r[2][1], r[2][2], p[2]], [0.0, 0.0, 0.0, 1.0]]
}

/// pushPullDistance: the grabbing hand's stick up (further) or down (nearer), only when pushed
/// clearly up or down; outside the range only back towards it. `stick`: its (x, y), None without a state.
pub fn push_pull_distance(distance: f64, stick: Option<(f64, f64)>, dt: f64) -> f64 {
    let Some((x, y)) = stick else { return distance };
    if y.abs() < PUSH_PULL_DEADZONE || y.abs() < 2.0 * x.abs() {
        return distance;
    }
    let (low, high) = PUSH_PULL_DISTANCE_RANGE_M;
    let moved = distance * (1.0 + y * PUSH_PULL_SPEED * dt);
    if y > 0.0 { moved.min(high.max(distance)) } else { moved.max(low.min(distance)) }
}

/// pushPull: the window moved along the hand-to-window line by the stick
pub fn push_pull(hand_to_overlay: &Mat4, stick: Option<(f64, f64)>, dt: f64) -> Mat4 {
    let offset = position(hand_to_overlay);
    let distance = norm(offset);
    if distance < 1e-6 {
        return *hand_to_overlay;
    }
    let mut result = *hand_to_overlay;
    set_position(&mut result, scale(offset, push_pull_distance(distance, stick, dt) / distance));
    result
}

/// launcherLooksVisible: the launcher's face (+Z) towards the head within `face_deg`, and within
/// `gaze_deg` of the gaze (by the launcher's own axes: controllers' axes differ by model)
pub fn launcher_looks_visible(launcher: &Mat4, head: &Mat4, face_deg: f64, gaze_deg: f64) -> bool {
    let to_head = sub(position(head), position(launcher));
    let distance = norm(to_head);
    if distance < 1e-6 {
        return false;
    }
    let to_head = scale(to_head, 1.0 / distance);
    let face_cos = dot(axis(launcher, 2), to_head);
    let gaze_cos = dot(scale(axis(head, 2), -1.0), scale(to_head, -1.0));
    face_cos >= face_deg.to_radians().cos() && gaze_cos >= gaze_deg.to_radians().cos()
}

/// launcherOutOfReach: too far from the wrist, or too small / large, to be found again
pub fn launcher_out_of_reach(xyz: Vec3, width: f64) -> bool {
    let (low, high) = LAUNCHER_WIDTH_RANGE_M;
    !(norm(xyz) <= LAUNCHER_REACH_M && low <= width && width <= high)
}

/// launcherNearestInReach: the position pulled along the wrist-to-launcher line onto the reach,
/// rounded to 4 places, and the width within its range
pub fn launcher_nearest_in_reach(xyz: Vec3, width: f64) -> (Vec3, f64) {
    let distance = norm(xyz);
    let shrink = if distance > LAUNCHER_REACH_M { LAUNCHER_REACH_M / distance } else { 1.0 };
    let (low, high) = LAUNCHER_WIDTH_RANGE_M;
    (xyz.map(|v| round_to(v * shrink, 4)), width.max(low).min(high))
}

/// Python's round(value, digits): the exact binary value rounded in decimal
pub fn round_to(value: f64, digits: usize) -> f64 {
    format!("{value:.digits$}").parse().unwrap_or(value)
}

/// overlay_utils.matrix_to_position: (x, y, z, x rotation, y rotation, z rotation) of `relative`
/// seen from `base` (z negated and Rz · Ry · Rx in degrees, as transform_matrix builds it)
pub fn matrix_to_position(base: &Mat34, relative: &Mat34) -> [f64; 6] {
    let h = mul(&inverse(&homogeneous(base)), &homogeneous(relative));
    let r = |i: usize, j: usize| h[i][j];
    let sy = -r(2, 0);
    let (x, y, z) = if sy.abs() < 0.999999 {
        (r(2, 1).atan2(r(2, 2)), sy.asin(), r(1, 0).atan2(r(0, 0)))
    } else {
        // gimbal lock: x and z turn about the same axis, folded into z
        (0.0, std::f64::consts::FRAC_PI_2 * sy.signum(), (-r(0, 1)).atan2(r(1, 1)))
    };
    [h[0][3], h[1][3], -h[2][3], x.to_degrees(), y.to_degrees(), z.to_degrees()]
}

/// uvToPixel: computeOverlayIntersection's UV in the overlay image (v measured in widths from the centre)
pub fn uv_to_pixel(u: f64, v: f64, width: usize, height: usize) -> (usize, usize) {
    let x = u * width as f64;
    let y = height as f64 / 2.0 - (v - 0.5) * width as f64;
    let clamp = |value: f64, size: usize| (value.trunc().max(0.0) as usize).min(size - 1);
    (clamp(x, width), clamp(y, height))
}

/// showPointer's transform: at the hit (2 mm in front), its face along the normal, upright
pub fn pointer_transform(point: Vec3, normal: Vec3) -> Mat34 {
    let point = add(point, scale(normal, 0.002));
    let up = if normal[1].abs() < 0.99 { [0.0, 1.0, 0.0] } else { [1.0, 0.0, 0.0] };
    let x = cross(up, normal);
    let x = scale(x, 1.0 / norm(x));
    let y = cross(normal, x);
    top(&from_axes(x, y, normal, point))
}
