//! Copy to the clipboard and paste into VRChat: the window of the app (by process name, or a title
//! containing it) is brought to the front for a moment, the text is copied and Ctrl+V is sent to it,
//! then the window that had the focus gets it back. arboard for the clipboard, Win32 for the focus and keys.
//! The app name (AppName: a Steam app OpenVR lists) comes from OpenVR, with the overlay's session.
use crate::platform::is_steamvr_running;
use std::sync::{mpsc, Arc, Mutex};
use std::time::Duration;
use windows_sys::core::BOOL;
use crate::platform::process_name;
use windows_sys::Win32::Foundation::{HWND, LPARAM};
use windows_sys::Win32::System::Threading::{AttachThreadInput, GetCurrentThreadId};
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{
    keybd_event, SendInput, INPUT, INPUT_0, INPUT_MOUSE, KEYEVENTF_KEYUP, MOUSEINPUT, VK_CONTROL,
};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    BringWindowToTop, EnumWindows, GetForegroundWindow, GetWindowTextLengthW, GetWindowTextW, GetWindowThreadProcessId,
    IsIconic, IsWindowVisible, SetForegroundWindow, ShowWindow, SW_RESTORE,
};

const VK_V: u8 = 0x56;

/// Every visible top-level window, with its title and process id
fn windows() -> Vec<(HWND, String, u32)> {
    unsafe extern "system" fn collect(hwnd: HWND, lparam: LPARAM) -> BOOL {
        if IsWindowVisible(hwnd) == 0 {
            return 1;
        }
        let out = &mut *(lparam as *mut Vec<(HWND, String, u32)>);
        let len = GetWindowTextLengthW(hwnd);
        let mut title = vec![0u16; len as usize + 1];
        let n = GetWindowTextW(hwnd, title.as_mut_ptr(), title.len() as i32);
        let mut pid = 0;
        GetWindowThreadProcessId(hwnd, &mut pid);
        out.push((hwnd, String::from_utf16_lossy(&title[..n.max(0) as usize]), pid));
        1
    }
    let mut out = vec![];
    unsafe { EnumWindows(Some(collect), &mut out as *mut _ as LPARAM) };
    out
}

/// Windows with a title containing `substring` (case-insensitive, as `in title.lower()`)
pub fn find_windows_by_title(substring: &str) -> Vec<HWND> {
    let wanted = substring.to_lowercase();
    windows().into_iter().filter(|(_, title, _)| !title.is_empty() && title.to_lowercase().contains(&wanted)).map(|w| w.0).collect()
}

/// Windows of a process named `name`, with or without ".exe" (case-insensitive)
pub fn find_windows_by_process(name: &str) -> Vec<HWND> {
    let wanted = name.to_lowercase();
    let exe = format!("{wanted}.exe");
    windows().into_iter().filter(|(_, _, pid)| process_name(*pid).is_some_and(|n| { let n = n.to_lowercase(); n == wanted || n == exe }))
        .map(|w| w.0).collect()
}

/// Brings the window to the front (restored if minimized: a maximized one stays so), borrowing the
/// foreground thread's input. True only when it is the foreground window after
fn focus_window(hwnd: HWND) -> bool {
    unsafe {
        if IsIconic(hwnd) != 0 {
            ShowWindow(hwnd, SW_RESTORE);
        }
        // an input of our own (a mouse event that does nothing): Windows lets the process that sent the
        // last input set the foreground window, which a program in the background otherwise may not
        let nothing = INPUT { r#type: INPUT_MOUSE, Anonymous: INPUT_0 { mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: 0, time: 0, dwExtraInfo: 0 } } };
        SendInput(1, &nothing, std::mem::size_of::<INPUT>() as i32);
        let current = GetCurrentThreadId();
        let foreground = GetForegroundWindow();
        let foreground_thread = if foreground.is_null() { 0 } else { GetWindowThreadProcessId(foreground, std::ptr::null_mut()) };
        let attached = foreground_thread != 0 && foreground_thread != current
            && AttachThreadInput(current, foreground_thread, 1) != 0;
        BringWindowToTop(hwnd);
        SetForegroundWindow(hwnd);
        if attached {
            AttachThreadInput(current, foreground_thread, 0);
        }
        GetForegroundWindow() == hwnd
    }
}

/// Puts `text` on the clipboard (arboard retries while another program holds it)
pub fn copy(text: &str) -> bool {
    arboard::Clipboard::new().and_then(|mut c| c.set_text(text)).is_ok()
}

/// The text on the clipboard (None: none, or it could not be read)
pub fn text() -> Option<String> {
    arboard::Clipboard::new().and_then(|mut c| c.get_text()).ok()
}

/// Ctrl+V to the focused window
pub fn paste() {
    unsafe {
        keybd_event(VK_CONTROL as u8, 0, 0, 0);
        keybd_event(VK_V, 0, 0, 0);
        keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0);
        keybd_event(VK_CONTROL as u8, 0, KEYEVENTF_KEYUP, 0);
    }
}

/// The window of `window_name` (by process name, then by title) to the front for `act` (the paste),
/// then the window that had the focus back. False when no window took the focus (`act` not done)
fn into_app(window_name: Option<&str>, log: &dyn Fn(String), act: impl FnOnce()) -> bool {
    let Some(name) = window_name else { return false };
    log(format!("paste: attempting to focus window matching '{name}'"));
    let previous = unsafe { GetForegroundWindow() };
    let Some(target) = find_windows_by_process(name).into_iter().chain(find_windows_by_title(name)).find(|&w| focus_window(w)) else {
        log(format!("paste: could not focus a window matching '{name}'"));
        return false;
    };
    // ponytail: fixed waits (the window taking the focus, then reading the keys before it is given back);
    // longer if VRChat misses pastes on a slow frame
    std::thread::sleep(Duration::from_millis(200));
    act();
    if !previous.is_null() && previous != target {
        std::thread::sleep(Duration::from_millis(200));
        if !focus_window(previous) {
            log("paste: could not give the focus back".into());
        }
    }
    true
}

/// Clipboard.copy_and_paste: copy, and paste into the window of `window_name` (by process name, then
/// by title). False when the copy failed or no window took the focus (the text is copied).
pub fn copy_and_paste(message: &str, window_name: Option<&str>, log: &dyn Fn(String)) -> bool {
    if !copy(message) {
        log("copy_and_paste: failed to copy to clipboard".into());
        return false;
    }
    into_app(window_name, log, paste)
}

/// Clipboard's app_name: once SteamVR runs (looked for every 10 s), the name of the first Steam app
/// OpenVR lists (keys "steam.app.*"), through the shared session; then again for each paste (`get`).
/// None until one is found.
pub struct AppName {
    name: Arc<Mutex<Option<String>>>,
    // dropped: the watching thread ends at once
    _stop: mpsc::Sender<()>,
}

impl AppName {
    pub fn watch(log: impl Fn(String) + Send + 'static) -> Self {
        let name = Arc::new(Mutex::new(None));
        let (stop, stopped) = mpsc::channel::<()>();
        let found = name.clone();
        std::thread::spawn(move || {
            log("Clipboard: VR monitor thread started.".into());
            loop {
                if is_steamvr_running() {
                    log("Clipboard: SteamVR detected. Setting up app info.".into());
                    match vrct_openvr::acquire(vrct_openvr::ApplicationType::Background).and_then(|session| steam_app_name(&session)) {
                        // (none listed: what a paste found meanwhile stays)
                        Ok(app) => if app.is_some() { *found.lock().unwrap() = app },
                        Err(e) => log(format!("Clipboard: Error setting up VR app name: {e}")),
                    }
                    break;
                }
                if stopped.recv_timeout(Duration::from_secs(10)) != Err(mpsc::RecvTimeoutError::Timeout) {
                    break;
                }
            }
            log("Clipboard: VR monitor thread ended.".into());
        });
        Self { name, _stop: stop }
    }

    /// The name for this paste: looked up again through the session already running (the overlay's),
    /// so an app installed after the first look is found. Never a VR_Init here (that waits on
    /// SteamVR, holding the paste up). Without an answer, the last one found
    pub fn get(&self) -> Option<String> {
        let session = if is_steamvr_running() { vrct_openvr::acquire_existing() } else { None };
        let found = session.and_then(|session| steam_app_name(&session).ok().flatten());
        let mut name = self.name.lock().unwrap();
        if found.is_some() {
            *name = found;
        }
        name.clone()
    }
}

fn steam_app_name(session: &vrct_openvr::Session) -> Result<Option<String>, vrct_openvr::Error> {
    let apps = session.applications()?;
    Ok((0..apps.application_count()).map(|i| apps.application_key_by_index(i)).find(|key| key.starts_with("steam.app"))
        .map(|key| apps.application_property_string(&key, vrct_openvr::APPLICATION_PROPERTY_NAME_STRING)))
}

#[cfg(test)]
mod tests {
    use super::*;

    // read-only: copy / paste would change the user's clipboard and type into their window
    #[test]
    fn finds_windows_without_touching_them() {
        assert!(!windows().is_empty());
        assert!(find_windows_by_title("no window has this title 0a9f3c").is_empty());
        assert!(find_windows_by_process("no-such-process-0a9f3c.exe").is_empty());
    }
}
