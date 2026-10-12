//! Where an overlay goes (overlay.getBaseMatrix, the trackers' bases and overlay_utils.transform_matrix):
//! the tracker's base with the setting's move (x, y, -z) and rotation (Rz · Ry · Rx, degrees) after it.
//! 3x4 row-major, as SteamVR takes it.

pub type Mat34 = [[f64; 4]; 3];
pub type Mat4 = [[f64; 4]; 4];

pub fn mul(a: &Mat4, b: &Mat4) -> Mat4 {
    let mut out = [[0.0; 4]; 4];
    for i in 0..4 {
        for j in 0..4 {
            out[i][j] = (0..4).map(|k| a[i][k] * b[k][j]).sum();
        }
    }
    out
}

fn homogeneous(m: &Mat34) -> Mat4 {
    [m[0], m[1], m[2], [0.0, 0.0, 0.0, 1.0]]
}

/// Rz · Ry · Rx of the angles in degrees (euler_to_rotation_matrix)
fn rotation(degrees: [f64; 3]) -> Mat4 {
    let r = |a: f64| (std::f64::consts::PI / 180.0 * a).sin_cos();
    let ((sx, cx), (sy, cy), (sz, cz)) = (r(degrees[0]), r(degrees[1]), r(degrees[2]));
    let x = [[1.0, 0.0, 0.0, 0.0], [0.0, cx, -sx, 0.0], [0.0, sx, cx, 0.0], [0.0, 0.0, 0.0, 1.0]];
    let y = [[cy, 0.0, sy, 0.0], [0.0, 1.0, 0.0, 0.0], [-sy, 0.0, cy, 0.0], [0.0, 0.0, 0.0, 1.0]];
    let z = [[cz, -sz, 0.0, 0.0], [sz, cz, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]];
    mul(&z, &mul(&y, &x))
}

/// transform_matrix(base, translation, rotation)
pub fn transform(base: &Mat34, translation: [f64; 3], degrees: [f64; 3]) -> Mat34 {
    let mut t = rotation(degrees);
    for (i, v) in translation.into_iter().enumerate() {
        t[i][3] = v;
    }
    let m = mul(&homogeneous(base), &t);
    [m[0], m[1], m[2]]
}

/// getBaseMatrix: a rotation, at (x·z, y·z, -z)
pub fn base_matrix(x: f64, y: f64, z: f64, x_rotation: f64, y_rotation: f64, z_rotation: f64) -> Mat34 {
    let r = rotation([x_rotation, y_rotation, z_rotation]);
    [[r[0][0], r[0][1], r[0][2], x * z], [r[1][0], r[1][1], r[1][2], y * z], [r[2][0], r[2][1], r[2][2], -z]]
}

/// What an overlay follows
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Tracker {
    Hmd,
    LeftHand,
    RightHand,
    /// fixed in the room
    Playspace,
}

impl Tracker {
    /// The setting's name; anything else is the headset (getTracker)
    pub fn from_name(name: &str) -> Self {
        match name {
            "LeftHand" => Tracker::LeftHand,
            "RightHand" => Tracker::RightHand,
            "Playspace" => Tracker::Playspace,
            _ => Tracker::Hmd,
        }
    }

    /// The base the setting's position is relative to
    pub fn base(self) -> Mat34 {
        match self {
            Tracker::Hmd => base_matrix(0.0, -0.4, 1.0, 0.0, 0.0, 0.0),
            Tracker::LeftHand => base_matrix(0.3, 0.1, -0.31, -65.0, 165.0, 115.0),
            Tracker::RightHand => base_matrix(-0.3, 0.1, -0.31, -65.0, -165.0, -115.0),
            Tracker::Playspace => [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
        }
    }
}

/// The overlay's transform for a position setting (updatePosition)
pub fn position_transform(tracker: Tracker, position: [f64; 6]) -> Mat34 {
    let [x, y, z, rx, ry, rz] = position;
    transform(&tracker.base(), [x, y, -z], [rx, ry, rz])
}

pub fn to_hmd(m: &Mat34) -> vrct_openvr::HmdMatrix34 {
    m.map(|row| row.map(|v| v as f32))
}
