//! The VRChat frame for OCR (models/ocr/ocr_capture*.py): SteamVR's mirror of the headset's left
//! eye (D3D11, through the shared OpenVR session) while SteamVR runs and VRChat is its scene,
//! otherwise VRChat's own window (PrintWindow, so windows on top of it do not show). Frames are BGR.
use crate::platform::{is_steamvr_running, process_name};
use std::ffi::c_void;
use std::time::{Duration, Instant};
use vrct_ocr::cv::Img;
use vrct_openvr::{ApplicationType, Session, EYE_LEFT};
use windows::core::Interface;
use windows::Win32::Graphics::Direct3D::D3D_DRIVER_TYPE_UNKNOWN;
use windows::Win32::Graphics::Direct3D11::{
    D3D11CreateDevice, ID3D11Device, ID3D11DeviceContext, ID3D11Resource, ID3D11ShaderResourceView, ID3D11Texture2D,
    D3D11_CPU_ACCESS_READ, D3D11_CREATE_DEVICE_FLAG, D3D11_MAPPED_SUBRESOURCE, D3D11_MAP_READ, D3D11_SDK_VERSION,
    D3D11_SHADER_RESOURCE_VIEW_DESC, D3D11_TEXTURE2D_DESC, D3D11_USAGE_STAGING,
};
use windows::Win32::Graphics::Dxgi::{CreateDXGIFactory, IDXGIFactory};
use windows::Win32::Graphics::Dxgi::Common::DXGI_FORMAT;
use windows_sys::Win32::Foundation::{HWND, LPARAM, RECT};
use windows_sys::Win32::Graphics::Gdi::{
    CreateCompatibleBitmap, CreateCompatibleDC, DeleteDC, DeleteObject, GetDIBits, GetWindowDC, ReleaseDC, SelectObject,
    BITMAPINFO, BITMAPINFOHEADER, DIB_RGB_COLORS,
};
use windows_sys::Win32::Storage::Xps::{PrintWindow, PRINT_WINDOW_FLAGS};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetWindowRect, GetWindowTextLengthW, GetWindowTextW, GetWindowThreadProcessId, IsIconic, IsWindowVisible,
};

const STEAMVR_RECHECK: Duration = Duration::from_secs(5);
const PW_RENDERFULLCONTENT: PRINT_WINDOW_FLAGS = 2;

/// 4-byte pixels in rows of `pitch` bytes to BGR (cv2.cvtColor BGRA2BGR / RGBA2BGR)
fn to_bgr(raw: &[u8], width: usize, pitch: usize, bgra: bool) -> Vec<u8> {
    let height = raw.len() / pitch;
    let mut out = vec![0u8; width * height * 3];
    for (row, dst) in raw.chunks_exact(pitch).zip(out.chunks_exact_mut(width * 3)) {
        let pixels = row[..width * 4].chunks_exact(4).zip(dst.chunks_exact_mut(3));
        if bgra {
            pixels.for_each(|(p, o)| o.copy_from_slice(&p[..3]));
        } else {
            pixels.for_each(|(p, o)| {
                o[0] = p[2];
                o[1] = p[1];
                o[2] = p[0];
            });
        }
    }
    out
}

// ---------------------------------------------------------------- the window (ocr_capture_hwnd.py)

/// The first visible window whose title is `substring`, else contains it (case-insensitive), else
/// whose process is named so (with or without ".exe")
fn find_window(substring: &str) -> Option<HWND> {
    struct Found {
        substring: String,
        exact: Vec<HWND>,
        partial: Vec<HWND>,
        by_process: Vec<HWND>,
    }
    unsafe extern "system" fn visit(hwnd: HWND, lparam: LPARAM) -> windows_sys::core::BOOL {
        let found = unsafe { &mut *(lparam as *mut Found) };
        if unsafe { IsWindowVisible(hwnd) } == 0 {
            return 1;
        }
        let len = unsafe { GetWindowTextLengthW(hwnd) };
        if len > 0 {
            let mut buf = vec![0u16; len as usize + 1];
            let n = unsafe { GetWindowTextW(hwnd, buf.as_mut_ptr(), buf.len() as i32) };
            let title = String::from_utf16_lossy(&buf[..n.max(0) as usize]);
            if title == found.substring {
                found.exact.push(hwnd);
                return 1;
            }
            if title.to_lowercase().contains(&found.substring.to_lowercase()) {
                found.partial.push(hwnd);
                return 1;
            }
        }
        let needle = found.substring.to_lowercase();
        let needle = needle.strip_suffix(".exe").unwrap_or(&needle).to_string();
        let mut pid = 0;
        unsafe { GetWindowThreadProcessId(hwnd, &mut pid) };
        let name = if pid == 0 { None } else { process_name(pid) };
        if let Some(name) = name {
            let name = name.to_lowercase();
            if name.strip_suffix(".exe").unwrap_or(&name) == needle {
                found.by_process.push(hwnd);
            }
        }
        1
    }
    let mut found = Found { substring: substring.into(), exact: vec![], partial: vec![], by_process: vec![] };
    unsafe { EnumWindows(Some(visit), &mut found as *mut Found as LPARAM) };
    found.exact.first().or(found.partial.first()).or(found.by_process.first()).copied()
}

fn window_size(hwnd: HWND) -> Option<(i32, i32)> {
    let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
    if unsafe { GetWindowRect(hwnd, &mut rect) } == 0 {
        return None;
    }
    let (w, h) = (rect.right - rect.left, rect.bottom - rect.top);
    (w > 0 && h > 0).then_some((w, h))
}

/// The window's own content (PrintWindow into a top-down 32-bit DIB), BGR
fn print_window(hwnd: HWND, width: i32, height: i32) -> Option<Img> {
    unsafe {
        let window_dc = GetWindowDC(hwnd);
        if window_dc.is_null() {
            return None;
        }
        let memory_dc = CreateCompatibleDC(window_dc);
        let bitmap = if memory_dc.is_null() { std::ptr::null_mut() } else { CreateCompatibleBitmap(window_dc, width, height) };
        let mut result = None;
        if !bitmap.is_null() {
            let old = SelectObject(memory_dc, bitmap);
            if PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT) != 0 {
                let mut info: BITMAPINFO = std::mem::zeroed();
                info.bmiHeader = BITMAPINFOHEADER {
                    biSize: size_of::<BITMAPINFOHEADER>() as u32,
                    biWidth: width,
                    biHeight: -height,
                    biPlanes: 1,
                    biBitCount: 32,
                    biCompression: 0,
                    ..std::mem::zeroed()
                };
                let mut bgra = vec![0u8; (width * height * 4) as usize];
                let rows = GetDIBits(memory_dc, bitmap, 0, height as u32, bgra.as_mut_ptr() as *mut c_void, &mut info, DIB_RGB_COLORS);
                if rows != 0 {
                    let w = width as usize;
                    result = Some(Img { w, h: height as usize, c: 3, data: to_bgr(&bgra, w, w * 4, true) });
                }
            }
            SelectObject(memory_dc, old);
            DeleteObject(bitmap);
        }
        if !memory_dc.is_null() {
            DeleteDC(memory_dc);
        }
        ReleaseDC(hwnd, window_dc);
        result
    }
}

/// HwndCapture: VRChat's window, None when it is missing, minimized or could not be read
pub struct HwndCapture {
    pub window_title: String,
    hwnd: Option<HWND>,
}

// the HWND is only an id here (it is not dereferenced)
unsafe impl Send for HwndCapture {}

impl HwndCapture {
    pub fn new(window_title: &str) -> Self {
        Self { window_title: window_title.into(), hwnd: None }
    }

    pub fn capture(&mut self) -> Option<Img> {
        let mut hwnd = self.hwnd.filter(|h| window_size(*h).is_some());
        if hwnd.is_none() {
            hwnd = find_window(&self.window_title);
            self.hwnd = hwnd;
        }
        let hwnd = hwnd?;
        if unsafe { IsIconic(hwnd) } != 0 {
            return None;
        }
        let Some((width, height)) = window_size(hwnd) else {
            self.hwnd = None;
            return None;
        };
        let frame = print_window(hwnd, width, height);
        if frame.is_none() {
            self.hwnd = None;
        }
        frame
    }
}

/// isFrameBlank: black / no signal (minimized VRChat): every 4th pixel each way, mean below 3 or
/// variance below 20
pub fn is_frame_blank(frame: Option<&Img>) -> bool {
    let Some(frame) = frame else { return true };
    let mut values = vec![];
    for y in (0..frame.h).step_by(4) {
        for x in (0..frame.w).step_by(4) {
            let p = (y * frame.w + x) * frame.c;
            values.extend(frame.data[p..p + frame.c].iter().map(|&v| v as f64));
        }
    }
    if values.is_empty() {
        return true;
    }
    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let var = values.iter().map(|v| (v - mean) * (v - mean)).sum::<f64>() / n;
    mean < 3.0 || var < 20.0
}

// ---------------------------------------------------------------- SteamVR's mirror (ocr_capture_d3d11.py / _openvr.py)

/// The compositor's mirror texture, copied through a CPU staging texture. Acquired once and read
/// every frame: releasing it each frame makes SteamVR serve stale frames (ValveSoftware/openvr#1888).
struct D3d11Mirror {
    context: ID3D11DeviceContext,
    _device: ID3D11Device,
    view: *mut c_void,
    texture: ID3D11Texture2D,
    staging: ID3D11Texture2D,
    width: u32,
    height: u32,
    bgra: bool,
}

impl D3d11Mirror {
    fn new(session: &Session, eye: i32) -> anyhow::Result<Self> {
        let adapter_index = session.system()?.dxgi_output_info();
        if adapter_index < 0 {
            anyhow::bail!("SteamVR did not return a DXGI adapter");
        }
        unsafe {
            let factory: IDXGIFactory = CreateDXGIFactory()?;
            let adapter = factory.EnumAdapters(adapter_index as u32)?;
            let (mut device, mut context) = (None, None);
            D3D11CreateDevice(&adapter, D3D_DRIVER_TYPE_UNKNOWN, Default::default(), D3D11_CREATE_DEVICE_FLAG(0), None,
                              D3D11_SDK_VERSION, Some(&mut device), None, Some(&mut context))?;
            let (device, context) = (device.unwrap(), context.unwrap());
            let view = session.compositor()?.mirror_texture_d3d11(eye, device.as_raw())?;
            let mirror = (|| -> anyhow::Result<Self> {
                // the view belongs to the compositor (released with ReleaseMirrorTextureD3D11)
                let srv = ID3D11ShaderResourceView::from_raw_borrowed(&view).unwrap();
                let resource: ID3D11Resource = srv.GetResource()?;
                let texture: ID3D11Texture2D = resource.cast()?;
                let mut desc = D3D11_TEXTURE2D_DESC::default();
                texture.GetDesc(&mut desc);
                // the compositor can expose a TYPELESS resource with a typed view
                let mut view_desc = D3D11_SHADER_RESOURCE_VIEW_DESC::default();
                srv.GetDesc(&mut view_desc);
                let view_format = view_desc.Format;
                if ![27, 28, 29, 87, 90, 91].contains(&desc.Format.0) || ![28, 29, 87, 91].contains(&view_format.0) {
                    anyhow::bail!("Unsupported DXGI format: {}", desc.Format.0);
                }
                if desc.SampleDesc.Count != 1 || desc.ArraySize != 1 || desc.MipLevels != 1 {
                    anyhow::bail!("expected a single-sample, single-mip 2D texture");
                }
                let staging_desc = D3D11_TEXTURE2D_DESC {
                    Format: DXGI_FORMAT(view_format.0),
                    Usage: D3D11_USAGE_STAGING,
                    BindFlags: 0,
                    CPUAccessFlags: D3D11_CPU_ACCESS_READ.0 as u32,
                    MiscFlags: 0,
                    ..desc
                };
                let mut staging = None;
                device.CreateTexture2D(&staging_desc, None, Some(&mut staging))?;
                Ok(Self {
                    context: context.clone(),
                    _device: device.clone(),
                    view,
                    texture,
                    staging: staging.unwrap(),
                    width: desc.Width,
                    height: desc.Height,
                    bgra: [87, 91].contains(&view_format.0),
                })
            })();
            if mirror.is_err() {
                session.compositor()?.release_mirror_texture_d3d11(view);
            }
            mirror
        }
    }

    /// The current frame, BGR
    fn read(&self) -> anyhow::Result<Img> {
        unsafe {
            self.context.CopyResource(&self.staging, &self.texture);
            let mut mapped = D3D11_MAPPED_SUBRESOURCE::default();
            self.context.Map(&self.staging, 0, D3D11_MAP_READ, 0, Some(&mut mapped))?;
            let (w, h, pitch) = (self.width as usize, self.height as usize, mapped.RowPitch as usize);
            let frame = (|| {
                if mapped.pData.is_null() || pitch < w * 4 {
                    anyhow::bail!("invalid mapped pixels");
                }
                let raw = std::slice::from_raw_parts(mapped.pData as *const u8, pitch * h);
                Ok(Img { w, h, c: 3, data: to_bgr(raw, w, pitch, self.bgra) })
            })();
            self.context.Unmap(&self.staging, 0);
            frame
        }
    }

    fn close(self, session: &Session) {
        if let Ok(compositor) = session.compositor() {
            compositor.release_mirror_texture_d3d11(self.view);
        }
    }
}

/// OpenVRMirrorCapture: joins the shared session lazily; any failure releases everything so the
/// next tick reconnects (SteamVR restart)
#[derive(Default)]
pub struct OpenVrMirrorCapture {
    session: Option<Session>,
    mirror: Option<D3d11Mirror>,
    failure_logged: bool,
}

unsafe impl Send for OpenVrMirrorCapture {}

impl OpenVrMirrorCapture {
    fn log_failure(&mut self, message: &str, error: &dyn std::fmt::Display, log: &dyn Fn(String)) {
        if !self.failure_logged {
            self.failure_logged = true;
            log(format!("OCR: {message}: {error} (further failures are not logged until a frame is read)"));
        }
    }

    fn reset(&mut self) {
        if let (Some(mirror), Some(session)) = (self.mirror.take(), self.session.as_ref()) {
            mirror.close(session);
        }
        self.session = None;
    }

    /// VRChat is the app SteamVR presents: the last frame's renderer is the scene focus process
    fn is_vrchat_scene(session: &Session) -> anyhow::Result<bool> {
        let compositor = session.compositor()?;
        let renderer = compositor.last_frame_renderer();
        if renderer == 0 || renderer != compositor.current_scene_focus_process() {
            return Ok(false);
        }
        Ok(process_name(renderer).is_some_and(|n| n.to_lowercase() == "vrchat.exe"))
    }

    pub fn capture(&mut self, log: &dyn Fn(String)) -> Option<Img> {
        if self.mirror.is_none() {
            let opened = vrct_openvr::acquire(ApplicationType::Background).map_err(anyhow::Error::from)
                .and_then(|session| D3d11Mirror::new(&session, EYE_LEFT).map(|m| (session, m)));
            match opened {
                Ok((session, mirror)) => {
                    self.session = Some(session);
                    self.mirror = Some(mirror);
                }
                Err(e) => {
                    self.log_failure("could not open the OpenVR mirror texture", &e, log);
                    self.reset();
                    return None;
                }
            }
        }
        let session = self.session.as_ref()?;
        let frame = Self::is_vrchat_scene(session).and_then(|scene| match scene {
            true => self.mirror.as_ref().unwrap().read().map(Some),
            false => Ok(None),
        });
        match frame {
            Ok(Some(frame)) => {
                self.failure_logged = false;
                Some(frame)
            }
            Ok(None) => None,
            Err(e) => {
                self.log_failure("reading the OpenVR mirror texture failed", &e, log);
                self.reset();
                None
            }
        }
    }
}

impl Drop for OpenVrMirrorCapture {
    fn drop(&mut self) {
        self.reset();
    }
}

// ---------------------------------------------------------------- the facade (ocr_capture.py)

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Backend {
    None,
    Hwnd,
    OpenVrMirror,
}

impl Backend {
    fn name(self) -> &'static str {
        match self {
            Backend::None => "none",
            Backend::Hwnd => "hwnd",
            Backend::OpenVrMirror => "openvr_mirror",
        }
    }
}

/// OcrCapture: the SteamVR mirror while SteamVR runs (rechecked every 5 s), else the window;
/// when the mirror gives nothing (VRChat is not the scene) the window until the next recheck
pub struct OcrCapture {
    hwnd: HwndCapture,
    openvr: Option<OpenVrMirrorCapture>,
    backend: Backend,
    source: Backend,
    last_check: Option<Instant>,
}

impl OcrCapture {
    pub fn new(window_title: &str) -> Self {
        Self { hwnd: HwndCapture::new(window_title), openvr: None, backend: Backend::None, source: Backend::None, last_check: None }
    }

    pub fn backend(&self) -> Backend {
        self.backend
    }

    fn select_backend(&mut self) -> Backend {
        if self.last_check.is_some_and(|t| t.elapsed() < STEAMVR_RECHECK) {
            return self.backend;
        }
        self.last_check = Some(Instant::now());
        if is_steamvr_running() {
            self.openvr.get_or_insert_with(OpenVrMirrorCapture::default);
            self.backend = Backend::OpenVrMirror;
            return self.backend;
        }
        self.openvr = None;
        self.backend = Backend::Hwnd;
        self.backend
    }

    fn note_source(&mut self, backend: Backend, log: &dyn Fn(String)) {
        if self.source != backend {
            log(format!("OCR capture backend -> {}", backend.name()));
            self.source = backend;
        }
    }

    /// The current VRChat frame (BGR), None when there is none to read
    pub fn get(&mut self, log: &dyn Fn(String)) -> Option<Img> {
        let mut backend = self.select_backend();
        if backend == Backend::OpenVrMirror {
            if let Some(frame) = self.openvr.as_mut().and_then(|o| o.capture(log)) {
                // frame.min() == frame.max(): one value everywhere (stops at the first other value)
                if frame.data.iter().all(|&v| v == frame.data[0]) {
                    return None;
                }
                self.note_source(Backend::OpenVrMirror, log);
                return Some(frame);
            }
            self.backend = Backend::Hwnd;
            backend = Backend::Hwnd;
        }
        if backend == Backend::Hwnd {
            let frame = self.hwnd.capture();
            if is_frame_blank(frame.as_ref()) {
                return None;
            }
            self.note_source(Backend::Hwnd, log);
            return frame;
        }
        None
    }

    pub fn close(&mut self) {
        self.openvr = None;
        self.hwnd.hwnd = None;
        self.backend = Backend::None;
        self.source = Backend::None;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blank_frames() {
        let image = |f: &dyn Fn(usize) -> u8| Img { w: 64, h: 32, c: 3, data: (0..64 * 32 * 3).map(f).collect() };
        assert!(is_frame_blank(None));
        assert!(is_frame_blank(Some(&image(&|_| 0))));
        // bright but flat: variance 0
        assert!(is_frame_blank(Some(&image(&|_| 200))));
        assert!(!is_frame_blank(Some(&image(&|i| (i * 37 % 251) as u8))));
    }

    #[test]
    fn bgr_from_bgra_and_rgba_rows_with_padding() {
        // 2x2, pitch 12 (4 bytes of padding per row)
        let raw = [1, 2, 3, 9, 4, 5, 6, 9, 0, 0, 0, 0, 7, 8, 9, 9, 10, 11, 12, 9, 0, 0, 0, 0];
        assert_eq!(to_bgr(&raw, 2, 12, true), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
        assert_eq!(to_bgr(&raw, 2, 12, false), [3, 2, 1, 6, 5, 4, 9, 8, 7, 12, 11, 10]);
    }
}
