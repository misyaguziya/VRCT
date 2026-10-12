//! The VR view's window (models/overlay/window_capture.py): Tauri's hidden "VRCT VR Panel" window,
//! kept off-screen. Its size follows the layout; it is captured with PrintWindow when
//! Windows.Graphics.Capture (vrct-graphics) has no frame of the right size yet, and mouse input
//! is posted to it (the OS cursor does not move).
use std::ffi::c_void;
use windows_sys::Win32::Foundation::{HWND, LPARAM, POINT, RECT};
use windows_sys::Win32::Graphics::Dwm::{DwmGetWindowAttribute, DWMWA_EXTENDED_FRAME_BOUNDS};
use windows_sys::Win32::Graphics::Gdi::{
    ClientToScreen, CreateCompatibleBitmap, CreateCompatibleDC, DeleteDC, DeleteObject, GetDIBits, GetWindowDC, ReleaseDC,
    SelectObject, BITMAPINFO, BITMAPINFOHEADER, DIB_RGB_COLORS,
};
use windows_sys::Win32::Storage::Xps::PrintWindow;
use windows_sys::Win32::UI::HiDpi::{GetDpiForWindow, SetThreadDpiAwarenessContext, DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    EnumChildWindows, FindWindowW, GetClassNameW, GetClientRect, GetWindowRect, IsIconic, IsWindow, PostMessageW, SetWindowPos,
    SWP_ASYNCWINDOWPOS, SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOZORDER, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_MOUSEMOVE, WM_MOUSEWHEEL,
};

pub const VR_PANEL_TITLE: &str = "VRCT VR Panel";
const PW_RENDERFULLCONTENT: u32 = 2;
const MK_LBUTTON: usize = 1;

/// (left, top, right, bottom) of the client area in a capture of the window
pub type ClientBox = (u32, u32, u32, u32);

/// A window handle that can cross threads (only ever passed back to Win32)
pub type Hwnd = isize;

fn h(hwnd: Hwnd) -> HWND {
    hwnd as HWND
}

fn wide(text: &str) -> Vec<u16> {
    text.encode_utf16().chain([0]).collect()
}

pub fn find_window(title: &str) -> Option<Hwnd> {
    let hwnd = unsafe { FindWindowW(std::ptr::null(), wide(title).as_ptr()) };
    (!hwnd.is_null()).then_some(hwnd as Hwnd)
}

pub fn is_window(hwnd: Hwnd) -> bool {
    unsafe { IsWindow(h(hwnd)) != 0 }
}

/// PrintWindow(PW_RENDERFULLCONTENT) of the whole window into a top-down BGRX buffer. It returns
/// only after the window has drawn (seconds when it hangs): call it off the overlay thread.
pub fn print_window(hwnd: Hwnd, width: i32, height: i32) -> Option<Vec<u8>> {
    let hwnd = h(hwnd);
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
                let mut data = vec![0u8; width as usize * height as usize * 4];
                if GetDIBits(memory_dc, bitmap, 0, height as u32, data.as_mut_ptr().cast(), &mut info, DIB_RGB_COLORS) != 0 {
                    result = Some(data);
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

/// captureWindowRaw: the whole window (BGRX), its size and the client box in it
pub struct Printed {
    pub data: Vec<u8>,
    pub size: (u32, u32),
    pub client: ClientBox,
}

/// captureWindowRaw: None when minimized or it cannot be captured
pub fn capture(hwnd: Hwnd) -> Option<Printed> {
    unsafe {
        if IsIconic(h(hwnd)) != 0 {
            return None;
        }
        let mut rect: RECT = std::mem::zeroed();
        GetWindowRect(h(hwnd), &mut rect);
        let (width, height) = (rect.right - rect.left, rect.bottom - rect.top);
        if width <= 0 || height <= 0 {
            return None;
        }
        let data = print_window(hwnd, width, height)?;
        // without the frame (a few px remain even undecorated): the box the input coordinates use
        let mut client: RECT = std::mem::zeroed();
        GetClientRect(h(hwnd), &mut client);
        let mut origin = POINT { x: 0, y: 0 };
        ClientToScreen(h(hwnd), &mut origin);
        let (left, top) = ((origin.x - rect.left).max(0) as u32, (origin.y - rect.top).max(0) as u32);
        Some(Printed { data, size: (width as u32, height as u32), client: (left, top, left + client.right as u32, top + client.bottom as u32) })
    }
}

/// _frameClientBox: the size of the window as Windows.Graphics.Capture sees it (its visible frame)
/// and the client box in it, physical px
pub fn frame_client_box(hwnd: Hwnd) -> Option<((u32, u32), ClientBox)> {
    unsafe {
        let old = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        let mut frame: RECT = std::mem::zeroed();
        let mut client: RECT = std::mem::zeroed();
        let mut origin = POINT { x: 0, y: 0 };
        let ok = DwmGetWindowAttribute(h(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS as u32, (&mut frame as *mut RECT).cast::<c_void>(),
                                       size_of::<RECT>() as u32) == 0;
        if ok {
            GetClientRect(h(hwnd), &mut client);
            ClientToScreen(h(hwnd), &mut origin);
        }
        SetThreadDpiAwarenessContext(old);
        if !ok {
            return None;
        }
        let (left, top) = ((origin.x - frame.left).max(0) as u32, (origin.y - frame.top).max(0) as u32);
        let size = ((frame.right - frame.left).max(0) as u32, (frame.bottom - frame.top).max(0) as u32);
        Some((size, (left, top, left + client.right as u32, top + client.bottom as u32)))
    }
}

/// resizeClient: the client area to `width` x `height` logical px (position kept). Returns the
/// client size to expect, physical px (the capture has it once the change is done). Does not wait
/// for the window (it may hang).
pub fn resize_client(hwnd: Hwnd, width: u32, height: u32) -> (u32, u32) {
    unsafe {
        let dpi = GetDpiForWindow(h(hwnd));
        let scale = if dpi == 0 { 1.0 } else { dpi as f64 / 96.0 };
        let mut rect: RECT = std::mem::zeroed();
        let mut client: RECT = std::mem::zeroed();
        GetWindowRect(h(hwnd), &mut rect);
        GetClientRect(h(hwnd), &mut client);
        let target = ((width as f64 * scale).round_ties_even() as i32, (height as f64 * scale).round_ties_even() as i32);
        if (client.right, client.bottom) != target {
            let frame_w = (rect.right - rect.left) - client.right;
            let frame_h = (rect.bottom - rect.top) - client.bottom;
            SetWindowPos(h(hwnd), std::ptr::null_mut(), 0, 0, target.0 + frame_w, target.1 + frame_h,
                         SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS);
        }
        (target.0 as u32, target.1 as u32)
    }
}

fn lparam(x: i32, y: i32) -> LPARAM {
    (((y & 0xFFFF) << 16) | (x & 0xFFFF)) as LPARAM
}

/// Posted mouse input. WebView2 takes it in a descendant (Chrome_RenderWidgetHostHWND), found once.
#[derive(Default)]
pub struct Mouse {
    target: Option<(Hwnd, Hwnd)>,
}

impl Mouse {
    fn target(&mut self, hwnd: Hwnd) -> HWND {
        if let Some((window, target)) = self.target
            && window == hwnd && is_window(target)
        {
            return h(target);
        }
        unsafe extern "system" fn visit(child: HWND, found: LPARAM) -> windows_sys::core::BOOL {
            let mut name = [0u16; 64];
            let length = unsafe { GetClassNameW(child, name.as_mut_ptr(), 64) }.max(0) as usize;
            if String::from_utf16_lossy(&name[..length]) == "Chrome_RenderWidgetHostHWND" {
                unsafe { *(found as *mut HWND) = child };
                return 0;
            }
            1
        }
        let mut found: HWND = std::ptr::null_mut();
        unsafe { EnumChildWindows(h(hwnd), Some(visit), (&mut found as *mut HWND) as LPARAM) };
        if found.is_null() {
            return h(hwnd);
        }
        self.target = Some((hwnd, found as Hwnd));
        found
    }

    pub fn moved(&mut self, hwnd: Hwnd, x: i32, y: i32, pressed: bool) {
        let target = self.target(hwnd);
        unsafe { PostMessageW(target, WM_MOUSEMOVE, if pressed { MK_LBUTTON } else { 0 }, lparam(x, y)) };
    }

    pub fn down(&mut self, hwnd: Hwnd, x: i32, y: i32) {
        let target = self.target(hwnd);
        unsafe { PostMessageW(target, WM_LBUTTONDOWN, MK_LBUTTON, lparam(x, y)) };
    }

    pub fn up(&mut self, hwnd: Hwnd, x: i32, y: i32) {
        let target = self.target(hwnd);
        unsafe { PostMessageW(target, WM_LBUTTONUP, 0, lparam(x, y)) };
    }

    /// WM_MOUSEWHEEL takes screen coordinates
    pub fn wheel(&mut self, hwnd: Hwnd, x: i32, y: i32, delta: i32) {
        let target = self.target(hwnd);
        let mut point = POINT { x, y };
        unsafe {
            ClientToScreen(target, &mut point);
            PostMessageW(target, WM_MOUSEWHEEL, ((delta as usize) & 0xFFFF) << 16, lparam(point.x, point.y));
        }
    }
}
