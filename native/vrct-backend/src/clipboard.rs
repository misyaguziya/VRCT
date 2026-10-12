//! Copy to the clipboard and paste into VRChat (models/clipboard/clipboard.py): the window whose
//! title (or process name) contains the app name is brought to the front, the text is copied and
//! Ctrl+V is sent to it. arboard for the clipboard (in place of `clip`), Win32 for the focus and keys.
//! The app name (AppName: a Steam app OpenVR lists) comes from OpenVR, with the overlay's session.
use crate::platform::is_steamvr_running;
use std::sync::{mpsc, Arc, Mutex};
use std::time::Duration;
use windows_sys::core::BOOL;
use crate::platform::process_name;
use windows_sys::Win32::Foundation::{HWND, LPARAM};
use windows_sys::Win32::System::Threading::{AttachThreadInput, GetCurrentThreadId};
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{keybd_event, KEYEVENTF_KEYUP, VK_CONTROL};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    BringWindowToTop, EnumWindows, GetForegroundWindow, GetWindowTextLengthW, GetWindowTextW, GetWindowThreadProcessId,
    SetForegroundWindow, ShowWindow, SW_RESTORE,
};

const VK_V: u8 = 0x56;

/// Every top-level window, with its title and process id
fn windows() -> Vec<(HWND, String, u32)> {
    unsafe extern "system" fn collect(hwnd: HWND, lparam: LPARAM) -> BOOL {
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

/// Windows of a process named `name` (case-insensitive)
pub fn find_windows_by_process(name: &str) -> Vec<HWND> {
    let wanted = name.to_lowercase();
    windows().into_iter().filter(|(_, _, pid)| process_name(*pid).is_some_and(|n| n.to_lowercase() == wanted)).map(|w| w.0).collect()
}

/// Restores the window and brings it to the front, borrowing the foreground thread's input
fn focus_window(hwnd: HWND) -> bool {
    unsafe {
        ShowWindow(hwnd, SW_RESTORE);
        let current = GetCurrentThreadId();
        let foreground = GetForegroundWindow();
        let foreground_thread = if foreground.is_null() { 0 } else { GetWindowThreadProcessId(foreground, std::ptr::null_mut()) };
        let attached = foreground_thread != 0 && foreground_thread != current
            && AttachThreadInput(current, foreground_thread, 1) != 0;
        BringWindowToTop(hwnd);
        let result = SetForegroundWindow(hwnd);
        if attached {
            AttachThreadInput(current, foreground_thread, 0);
        }
        result != 0
    }
}

/// Puts `text` on the clipboard (arboard retries while another program holds it)
pub fn copy(text: &str) -> bool {
    arboard::Clipboard::new().and_then(|mut c| c.set_text(text)).is_ok()
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

/// Clipboard.copy_and_paste: focus the window of `window_name` (by title, then by process name),
/// copy, and paste. False when the copy failed or no window took the focus (the text is copied).
pub fn copy_and_paste(message: &str, window_name: Option<&str>, log: &dyn Fn(String)) -> bool {
    let mut focused = false;
    if let Some(name) = window_name {
        log(format!("paste: attempting to focus window matching '{name}'"));
        focused = find_windows_by_title(name).into_iter().any(focus_window)
            || find_windows_by_process(name).into_iter().any(focus_window);
        if focused {
            std::thread::sleep(Duration::from_millis(200));
        } else {
            log(format!("copy_and_paste: could not focus a window matching '{name}'; copying only"));
        }
    }
    if !copy(message) {
        log("copy_and_paste: failed to copy to clipboard".into());
        return false;
    }
    if focused {
        paste();
    }
    focused
}

/// Clipboard's app_name: once SteamVR runs (looked for every 10 s), the name of the first Steam app
/// OpenVR lists (keys "steam.app.*"), through the shared session. Looked up once, as the Python
/// version does; None when it fails.
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
                    match steam_app_name() {
                        Ok(app) => *found.lock().unwrap() = app,
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

    pub fn get(&self) -> Option<String> {
        self.name.lock().unwrap().clone()
    }
}

fn steam_app_name() -> Result<Option<String>, vrct_openvr::Error> {
    let session = vrct_openvr::acquire(vrct_openvr::ApplicationType::Background)?;
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
