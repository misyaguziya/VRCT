//! The VR UI's one captured window and the parts cut out of it (overlay.py: computeVrLayout,
//! regionRect / regionBounds, the mask; overlay_tooltip.py: the tooltip's request, its marker
//! and mask), and the small images drawn here (the pointer, the resize frame).
//!
//! The VR view (src-ui/views/vr, a hidden Tauri window) draws every window side by side;
//! each overlay shows its region of the one capture. Logical px; captures can be larger (DPI).
use crate::image::Image;
use serde_json::Value;

/// The launcher's width (logical px): the tooltip's button range and the layout's reference
pub const LAUNCHER_WIDTH_PX: u32 = 952;
/// The log window's size (logical px): its default and the range of a corner drag
pub const PANEL_DEFAULT_SIZE: (u32, u32) = (900, 700);
pub const PANEL_SIZE_RANGE: ((u32, u32), (u32, u32)) = ((600, 400), (1400, 1000));
/// Corner radius of each region (logical px): outside it the capture is clear
const PANEL_CORNER_RADIUS_PX: f64 = 24.0;

/// The windows of the VR view, in the order of overlay.py's VR_REGIONS
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Region {
    /// the log window (OVERLAY_VR_PANEL_SETTINGS)
    Panel,
    /// the band on the wrist
    Launcher,
    /// the one temporary window (language / VR settings), put by the launcher when opened
    Popup,
    /// the bar under the log (moves with it, never saved)
    Toolbar,
    Tooltip,
}

impl Region {
    pub const ALL: [Region; 5] = [Region::Panel, Region::Launcher, Region::Popup, Region::Toolbar, Region::Tooltip];

    /// The name in the settings and the layout ("panel", ...)
    pub fn name(self) -> &'static str {
        match self {
            Region::Panel => "panel",
            Region::Launcher => "launcher",
            Region::Popup => "popup",
            Region::Toolbar => "toolbar",
            Region::Tooltip => "tooltip",
        }
    }

    pub fn from_name(name: &str) -> Option<Region> {
        Region::ALL.into_iter().find(|r| r.name() == name)
    }
}

/// The capture's size and each region (x, y, w, h), logical px
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Layout {
    pub atlas: (u32, u32),
    pub regions: [[u32; 4]; 5],
}

impl Layout {
    /// computeVrLayout: the log at the top left, the launcher under it, the temporary window, the
    /// bar and the tooltip in a column on the right (past the launcher)
    pub fn new(width: u32, height: u32) -> Layout {
        let right_x = width.max(LAUNCHER_WIDTH_PX + 10) + 8;
        Layout {
            atlas: (right_x + 720, (height + 8 + 128).max(880)),
            regions: [
                [0, 0, width, height],
                [10, height + 8, LAUNCHER_WIDTH_PX, 128],
                [right_x, 0, 720, 640],
                [right_x, 656, 720, 96],
                [right_x, 760, 360, 120],
            ],
        }
    }

    pub fn region(&self, region: Region) -> [u32; 4] {
        self.regions[region as usize]
    }

    /// The log's size (what the layout follows)
    pub fn panel_size(&self) -> (u32, u32) {
        let [_, _, w, h] = self.region(Region::Panel);
        (w, h)
    }

    /// The largest layout: the textures are made to hold it
    pub fn max() -> Layout {
        let (w, h) = PANEL_SIZE_RANGE.1;
        Layout::new(w, h)
    }

    /// regionRect: (x0, y0, x1, y1) in a capture `image_width` px wide
    pub fn region_rect(&self, region: Region, image_width: u32) -> [u32; 4] {
        let scale = image_width as f64 / self.atlas.0 as f64;
        let [x, y, w, h] = self.region(region);
        [x, y, x + w, y + h].map(|v| round(v as f64 * scale))
    }

    /// regionBounds for a DirectX texture (v = 0 at the top), the capture taking `fu` x `fv` of it
    pub fn region_bounds(&self, region: Region, fu: f64, fv: f64) -> [f32; 4] {
        let (aw, ah) = (self.atlas.0 as f64, self.atlas.1 as f64);
        let [x, y, w, h] = self.region(region).map(f64::from);
        [x / aw * fu, (x + w) / aw * fu, y / ah * fv, (y + h) / ah * fv].map(|v| v as f32)
    }
}

/// Python's round() to an integer (ties to even)
fn round(value: f64) -> u32 {
    value.round_ties_even().max(0.0) as u32
}

/// clampPanelSize
pub fn clamp_panel_size(width: f64, height: f64) -> (u32, u32) {
    let ((min_w, min_h), (max_w, max_h)) = PANEL_SIZE_RANGE;
    (round(width.max(min_w as f64).min(max_w as f64)), round(height.max(min_h as f64).min(max_h as f64)))
}

/// Pillow's rounded_rectangle((x0, y0, x1, y1), radius) cover of pixel (x, y), inclusive corners,
/// no anti-aliasing (pixels at their integer coordinates, as Pillow places them)
fn in_rounded_rect(x: f64, y: f64, rect: [f64; 4], radius: f64) -> bool {
    let [x0, y0, x1, y1] = rect;
    if x < x0 || x > x1 || y < y0 || y > y1 {
        return false;
    }
    let r = radius.min((x1 - x0) / 2.0).min((y1 - y0) / 2.0);
    let cx = x.clamp(x0 + r, x1 - r);
    let cy = y.clamp(y0 + r, y1 - r);
    // fitted to Pillow 10's quarter circles (radius 6, 12, 24: the same pixels but a few)
    (x - cx).powi(2) + (y - cy).powi(2) <= r * r + 0.75 * r
}

fn fill_rounded_rect(mask: &mut [u8], width: u32, rect: [f64; 4], radius: f64) {
    let height = mask.len() as u32 / width.max(1);
    let (x0, x1) = (rect[0].max(0.0) as u32, (rect[2].max(0.0) as u32).min(width.saturating_sub(1)));
    let (y0, y1) = (rect[1].max(0.0) as u32, (rect[3].max(0.0) as u32).min(height.saturating_sub(1)));
    for y in y0..=y1 {
        for x in x0..=x1 {
            if in_rounded_rect(x as f64, y as f64, rect, radius) {
                mask[(y * width + x) as usize] = 255;
            }
        }
    }
}

/// atlasMaskArray: every region but the tooltip kept with rounded corners, the rest clear
/// (`size` is the capture's, width x height bytes)
pub fn mask(size: (u32, u32), layout: &Layout) -> Vec<u8> {
    let mut mask = vec![0u8; (size.0 * size.1) as usize];
    let scale = size.0 as f64 / layout.atlas.0 as f64;
    for region in Region::ALL {
        if region == Region::Tooltip {
            continue;
        }
        let [x0, y0, x1, y1] = layout.region_rect(region, size.0);
        let rect = [x0 as f64, y0 as f64, x1 as f64 - 1.0, y1 as f64 - 1.0];
        fill_rounded_rect(&mut mask, size.0, rect, round(PANEL_CORNER_RADIUS_PX * scale) as f64);
    }
    mask
}

/// Hover tooltips or keyboard focus
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TooltipMode {
    Hover,
    Focus,
}

/// A tooltip request from the VR view (/run/vr_panel_tooltip), checked
#[derive(Clone, Debug, PartialEq)]
pub struct Tooltip {
    pub epoch: u64,
    pub revision: u64,
    /// None: hide
    pub shown: Option<TooltipShown>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct TooltipShown {
    /// Launcher or Toolbar
    pub region: Region,
    pub mode: TooltipMode,
    /// the button it belongs to (x, y, w, h in the region, logical px)
    pub button: [f64; 4],
    /// the bubble's (w, h)
    pub size: [f64; 2],
    pub arrow_x: f64,
}

fn finite_number(value: &Value) -> Option<f64> {
    let v = value.as_number()?.as_f64()?;
    (v.is_finite() && (-1e6..=1e6).contains(&v)).then_some(v)
}

fn int_in(value: Option<&Value>, max: u64) -> Option<u64> {
    let n = value?.as_number()?;
    // ints only (Python's type(value) is int): 5.0 is not one
    if n.is_f64() {
        return None;
    }
    n.as_u64().filter(|v| (1..=max).contains(v))
}

/// validate_tooltip: rejects malformed or out-of-range requests (the reason as the error)
pub fn validate_tooltip(data: &Value) -> Result<Tooltip, &'static str> {
    let object = data.as_object().ok_or("tooltip must be an object")?;
    let epoch = int_in(object.get("epoch"), (1 << 48) - 1).ok_or("epoch")?;
    let revision = int_in(object.get("revision"), (1 << 32) - 1).ok_or("revision")?;
    let visible = object.get("visible").and_then(Value::as_bool).ok_or("visible")?;
    if !visible {
        if object.len() != 3 {
            return Err("hidden payload");
        }
        return Ok(Tooltip { epoch, revision, shown: None });
    }
    const KEYS: [&str; 8] = ["epoch", "revision", "visible", "region", "button", "size", "arrow_x", "mode"];
    if object.keys().any(|k| !KEYS.contains(&k.as_str())) {
        return Err("unknown field");
    }
    let region = match object.get("region").and_then(Value::as_str) {
        Some("launcher") => Region::Launcher,
        Some("toolbar") => Region::Toolbar,
        _ => return Err("region or mode"),
    };
    let mode = match object.get("mode") {
        None => TooltipMode::Hover,
        Some(Value::String(s)) if s == "hover" => TooltipMode::Hover,
        Some(Value::String(s)) if s == "focus" => TooltipMode::Focus,
        _ => return Err("region or mode"),
    };
    let numbers = |key: &'static str, length: usize| -> Result<Vec<f64>, &'static str> {
        let values = object.get(key).and_then(Value::as_array).ok_or(key)?;
        if values.len() != length {
            return Err(key);
        }
        values.iter().map(|v| finite_number(v).ok_or(key)).collect()
    };
    let button: [f64; 4] = numbers("button", 4)?.try_into().unwrap();
    let size: [f64; 2] = numbers("size", 2)?.try_into().unwrap();
    let [x, y, w, h] = button;
    let (parent_w, parent_h) = if region == Region::Launcher { (LAUNCHER_WIDTH_PX as f64, 128.0) } else { (720.0, 96.0) };
    if x < 0.0 || y < 0.0 || w <= 0.0 || h <= 0.0 || x + w > parent_w || y + h > parent_h {
        return Err("button bounds");
    }
    if size[0] != 360.0 || !(1.0..=104.0).contains(&size[1]) {
        return Err("size bounds");
    }
    let arrow_x = object.get("arrow_x").and_then(finite_number).filter(|v| (12.0..=348.0).contains(v)).ok_or("arrow_x")?;
    Ok(Tooltip { epoch, revision, shown: Some(TooltipShown { region, mode, button, size, arrow_x }) })
}

/// marker_points: the marker's pixel row and its 80 sample columns in a capture `width` px wide
pub fn marker_points(width: u32, layout: &Layout) -> (u32, [u32; 80]) {
    let scale = width as f64 / layout.atlas.0 as f64;
    let [x, y, _, _] = layout.region(Region::Tooltip).map(f64::from);
    (round((y + 4.0) * scale), std::array::from_fn(|i| round((x + i as f64 * 4.0 + 2.0) * scale)))
}

/// marker_row_matches: one BGRA row against the 80 big-endian bits of epoch / revision
/// (white >= 224, black <= 31 in each of B, G, R)
pub fn marker_row_matches(row: &[u8], columns: &[u32; 80], epoch: u64, revision: u64) -> bool {
    let bits = ((epoch as u128) << 32) | revision as u128;
    columns.iter().enumerate().all(|(index, &px)| {
        let at = px as usize * 4;
        let Some(color) = row.get(at..at + 3) else { return false };
        if (bits >> (79 - index)) & 1 == 1 { color.iter().all(|&c| c >= 224) } else { color.iter().all(|&c| c <= 31) }
    })
}

/// tooltip_mask: the static mask plus the bubble's body and arrow (the marker stays clear)
pub fn tooltip_mask(size: (u32, u32), layout: &Layout, shown: &TooltipShown, mask: &mut [u8]) {
    let scale = size.0 as f64 / layout.atlas.0 as f64;
    let [x, y, _, _] = layout.region(Region::Tooltip).map(f64::from);
    let y = y + 8.0;
    let [w, h] = shown.size;
    let s = |v: f64| round(v * scale) as f64;
    fill_rounded_rect(mask, size.0, [s(x), s(y), s(x + w) - 1.0, s(y + h) - 1.0], s(12.0));
    let a = shown.arrow_x;
    let triangle = [(s(x + a - 6.0), s(y + h - 1.0)), (s(x + a + 6.0), s(y + h - 1.0)), (s(x + a), s(y + h + 6.0) - 1.0)];
    fill_triangle(mask, size, triangle);
}

/// A filled triangle, edges included (draw.polygon)
fn fill_triangle(mask: &mut [u8], size: (u32, u32), points: [(f64, f64); 3]) {
    let edge = |a: (f64, f64), b: (f64, f64), p: (f64, f64)| (b.0 - a.0) * (p.1 - a.1) - (b.1 - a.1) * (p.0 - a.0);
    let [p0, p1, p2] = points;
    let area = edge(p0, p1, p2);
    let (min_x, max_x) = (p0.0.min(p1.0).min(p2.0).max(0.0) as u32, p0.0.max(p1.0).max(p2.0).max(0.0) as u32);
    let (min_y, max_y) = (p0.1.min(p1.1).min(p2.1).max(0.0) as u32, p0.1.max(p1.1).max(p2.1).max(0.0) as u32);
    for y in min_y..=max_y.min(size.1.saturating_sub(1)) {
        for x in min_x..=max_x.min(size.0.saturating_sub(1)) {
            let p = (x as f64, y as f64);
            let (a, b, c) = (edge(p1, p2, p), edge(p2, p0, p), edge(p0, p1, p));
            let inside = if area >= 0.0 { a >= 0.0 && b >= 0.0 && c >= 0.0 } else { a <= 0.0 && b <= 0.0 && c <= 0.0 };
            if inside {
                mask[(y * size.0 + x) as usize] = 255;
            }
        }
    }
}

// The resize frame (RGBA): its outline, at a limit, and its fill
const GHOST_COLOR: [u8; 4] = [0xB7, 0xDE, 0xD8, 255];
const GHOST_LIMIT_COLOR: [u8; 4] = [0xCB, 0x94, 0x4F, 255];
const GHOST_FILL: [u8; 4] = [0x61, 0xB4, 0xA7, 40];

/// createGhostImage: the frame shown while a corner is dragged (the new size at 1/4)
pub fn ghost_image(width_px: u32, height_px: u32, at_limit: bool) -> Image {
    let (w, h) = (round(width_px as f64 / 4.0).max(8) as usize, round(height_px as f64 / 4.0).max(8) as usize);
    let mut image = Image::new(w, h, [0; 4]);
    let outer = [1.0, 1.0, w as f64 - 2.0, h as f64 - 2.0];
    let inner = [4.0, 4.0, w as f64 - 5.0, h as f64 - 5.0];
    let outline = if at_limit { GHOST_LIMIT_COLOR } else { GHOST_COLOR };
    for y in 0..h {
        for x in 0..w {
            let (px, py) = (x as f64, y as f64);
            let color = if in_rounded_rect(px, py, inner, 3.0) {
                GHOST_FILL
            } else if in_rounded_rect(px, py, outer, 6.0) {
                outline
            } else {
                continue;
            };
            image.data[(y * w + x) * 4..][..4].copy_from_slice(&color);
        }
    }
    image
}

/// The pointer's kinds: a dot, and + / - while scaling a grabbed window
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PointerKind {
    Dot,
    Plus,
    Minus,
}

impl PointerKind {
    pub const ALL: [PointerKind; 3] = [PointerKind::Dot, PointerKind::Plus, PointerKind::Minus];

    pub fn name(self) -> &'static str {
        match self {
            PointerKind::Dot => "dot",
            PointerKind::Plus => "plus",
            PointerKind::Minus => "minus",
        }
    }
}

/// createPointerImages: drawn white (the overlay colour tints it) with a black ring and sign
pub fn pointer_image(kind: PointerKind) -> Image {
    let mut image = Image::new(64, 64, [0; 4]);
    for y in 0..64 {
        for x in 0..64 {
            // the ellipse (4, 4, 59, 59) with a 5 px outline (squared distances from the centre,
            // fitted to Pillow 10's: the same pixels)
            let d2 = (x as f64 - 31.5).powi(2) + (y as f64 - 31.5).powi(2);
            if d2 > 777.5 {
                continue;
            }
            // lines 7 px wide: (18, 32) - (46, 32), and (32, 18) - (32, 46) for plus
            let horizontal = kind != PointerKind::Dot && (18..=46).contains(&x) && (29..=35).contains(&y);
            let vertical = kind == PointerKind::Plus && (18..=46).contains(&y) && (29..=35).contains(&x);
            let black = d2 > 532.5 || horizontal || vertical;
            image.data[(y * 64 + x) * 4..][..4].copy_from_slice(if black { &[0, 0, 0, 255] } else { &[255; 4] });
        }
    }
    image
}
