//! Processes (models/process_check.py and psutil's name()): whether SteamVR / VRChat is running,
//! and the executable name of a process.
use windows_sys::Win32::Foundation::CloseHandle;
use windows_sys::Win32::System::Threading::{OpenProcess, QueryFullProcessImageNameW, PROCESS_QUERY_LIMITED_INFORMATION};

pub use vrct_openvr::{is_process_running, is_steamvr_running};

/// The executable's file name of a process (psutil.Process(pid).name())
pub fn process_name(pid: u32) -> Option<String> {
    unsafe {
        let process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
        if process.is_null() {
            return None;
        }
        let mut buf = [0u16; 1024];
        let mut len = buf.len() as u32;
        let ok = QueryFullProcessImageNameW(process, 0, buf.as_mut_ptr(), &mut len);
        CloseHandle(process);
        if ok == 0 {
            return None;
        }
        let path = String::from_utf16_lossy(&buf[..len as usize]);
        path.rsplit(['\\', '/']).next().map(String::from)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_this_process() {
        let me = process_name(std::process::id()).unwrap();
        assert!(me.to_lowercase().ends_with(".exe"));
        assert!(is_process_running(&me.to_uppercase()));
        assert!(!is_process_running("no-such-process-0a9f3c.exe"));
    }
}
